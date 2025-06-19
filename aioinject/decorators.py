import dataclasses
import functools
import inspect
import typing
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Sequence,
)
from contextlib import nullcontext
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Generic,
    NamedTuple,
    TypeAlias,
)

from typing_extensions import TypeVar

from aioinject import Context, SyncContext
from aioinject._types import (
    P,
    T,
    remove_annotation,
    safe_issubclass,
    unwrap_annotated,
)
from aioinject.extensions.providers import Dependency


@dataclasses.dataclass(slots=True)
class Inject:
    pass


_F = TypeVar("_F", bound=Callable[..., Any])

if TYPE_CHECKING:
    Injected: TypeAlias = Annotated[T, Inject]

else:

    class Injected(Generic[T]):
        def __class_getitem__(cls, item: object) -> object:
            return Annotated[item, Inject]


def clear_wrapper(wrapper: _F, args: list[str]) -> _F:
    signature = inspect.signature(wrapper)
    new_params = tuple(
        p for p in signature.parameters.values() if p.name not in args
    )
    wrapper.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=new_params,
    )
    for name in args:
        del wrapper.__annotations__[name]
    return wrapper


def _find_inject_marker_in_annotated_args(
    args: Sequence[Any],
) -> Inject | None:
    for arg in args:
        if safe_issubclass(arg, Inject):
            return Inject()

        if isinstance(arg, Inject):
            return arg  # pragma: no cover
    return None


def collect_dependencies(
    dependant: typing.Callable[..., object],
) -> typing.Iterable[Dependency[object]]:
    with remove_annotation(dependant.__annotations__, "return"):
        type_hints = typing.get_type_hints(dependant, include_extras=True)

    for name, hint in type_hints.items():
        dep_type, args = unwrap_annotated(hint)
        inject_marker = _find_inject_marker_in_annotated_args(args)
        if inject_marker is None:
            continue

        yield Dependency(
            name=name,
            type_=dep_type,
        )


def add_parameters_to_signature(
    func: Callable[P, T],
    parameters: dict[str, type[object]],
) -> Callable[P, T]:
    signature = inspect.signature(func)

    existing_parameters = [
        param
        for param in signature.parameters.values()
        if param.name not in parameters
    ]
    kwargs_parameter = next(
        (
            param
            for param in existing_parameters
            if param.kind == inspect.Parameter.VAR_KEYWORD
        ),
        None,
    )
    if kwargs_parameter:
        existing_parameters.remove(kwargs_parameter)

    params = [
        *existing_parameters,
        *(
            inspect.Parameter(
                name=name,
                annotation=annotation,
                kind=inspect.Parameter.KEYWORD_ONLY,
            )
            for name, annotation in parameters.items()
        ),
    ]
    # Push **kwargs parameter to end of the function
    if kwargs_parameter is not None:
        params.append(kwargs_parameter)

    func.__signature__ = signature.replace(parameters=params)  # type: ignore[attr-defined]
    for name, annotation in parameters.items():
        func.__annotations__[name] = annotation
    return func


@dataclasses.dataclass(slots=True, kw_only=True)
class ContextParameter:
    type_: type[object]
    name: str
    remove: bool = True


ContextGetter = Callable[[tuple[Any, ...], dict[str, Any]], T]


def _add_context(
    context: Context | SyncContext,
    context_parameters: Sequence[ContextParameter],
    kwargs: dict[str, object],
) -> None:
    context.add_context(
        {
            parameter.type_: kwargs.pop(parameter.name)
            if parameter.remove
            else kwargs[parameter.name]
            for parameter in context_parameters
        }
    )


def _async_wrapper_factory(
    function: Callable[P, Awaitable[T]],
    context_parameters: Sequence[ContextParameter],
    context_getter: ContextGetter[Context],
    dependencies: Sequence[Dependency[object]],
    *,
    enter_context: bool,
) -> Callable[P, Awaitable[T]]:
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        context = context_getter(args, kwargs)
        async with (
            nullcontext(context) if not enter_context else context.context()
        ) as context:
            _add_context(context, context_parameters, kwargs)

            for dependency in dependencies:
                kwargs[dependency.name] = await context.resolve(
                    dependency.type_
                )
            return await function(*args, **kwargs)

    return wrapper


def _async_generator_wrapper_factory(
    function: Callable[P, AsyncIterator[T]],
    context_parameters: Sequence[ContextParameter],
    context_getter: ContextGetter[Context],
    dependencies: Sequence[Dependency[object]],
    *,
    enter_context: bool,
) -> Callable[P, AsyncIterator[T]]:
    async def wrapper(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> AsyncIterator[T]:
        context = context_getter(args, kwargs)
        async with (
            nullcontext(context) if not enter_context else context.context()
        ) as context:
            _add_context(context, context_parameters, kwargs)

            for dependency in dependencies:
                kwargs[dependency.name] = await context.resolve(
                    dependency.type_
                )
            async for result in function(*args, **kwargs):
                yield result

    return wrapper


def _sync_wrapper_factory(
    function: Callable[P, Awaitable[T]],
    context_parameters: Sequence[ContextParameter],
    context_getter: ContextGetter[SyncContext],
    dependencies: Sequence[Dependency[object]],
    *,
    enter_context: bool,
) -> Callable[P, object]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
        context = context_getter(args, kwargs)
        with (
            nullcontext(context) if not enter_context else context.context()
        ) as context:
            _add_context(context, context_parameters, kwargs)

            for dependency in dependencies:
                kwargs[dependency.name] = context.resolve(dependency.type_)
            return function(*args, **kwargs)

    return wrapper


def _sync_generator_wrapper_factory(
    function: Callable[P, Iterator[T]],
    context_parameters: Sequence[ContextParameter],
    context_getter: ContextGetter[SyncContext],
    dependencies: Sequence[Dependency[object]],
    *,
    enter_context: bool,
) -> Callable[P, Iterator[T]]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Iterator[T]:
        context = context_getter(args, kwargs)
        with (
            nullcontext(context) if not enter_context else context.context()
        ) as context:
            _add_context(context, context_parameters, kwargs)

            for dependency in dependencies:
                kwargs[dependency.name] = context.resolve(dependency.type_)

            yield from function(*args, **kwargs)

    return wrapper


class WrapperCacheKey(NamedTuple):
    is_async: bool
    is_generator: bool


_WRAPPERS = {
    WrapperCacheKey(is_async=True, is_generator=False): _async_wrapper_factory,
    WrapperCacheKey(
        is_async=True, is_generator=True
    ): _async_generator_wrapper_factory,
    WrapperCacheKey(is_async=False, is_generator=False): _sync_wrapper_factory,
    WrapperCacheKey(
        is_async=False, is_generator=True
    ): _sync_generator_wrapper_factory,
}


def base_inject(
    function: Callable[P, T],
    context_parameters: Sequence[ContextParameter],
    context_getter: ContextGetter[SyncContext | Context],
    *,
    enter_context: bool = False,
) -> Callable[P, T]:
    dependencies = list(collect_dependencies(function))

    is_async = inspect.iscoroutinefunction(
        function
    ) or inspect.isasyncgenfunction(function)
    is_generator = inspect.isgeneratorfunction(
        function
    ) or inspect.isasyncgenfunction(function)

    wrapper = _WRAPPERS[  # type: ignore[operator]
        WrapperCacheKey(is_async=is_async, is_generator=is_generator)
    ](
        function=function,
        context_parameters=context_parameters,
        enter_context=enter_context,
        dependencies=dependencies,
        context_getter=context_getter,
    )
    wrapper = functools.update_wrapper(wrapper=wrapper, wrapped=function)
    wrapper = clear_wrapper(
        wrapper,
        args=[dep.name for dep in dependencies],
    )
    return add_parameters_to_signature(
        wrapper, {p.name: p.type_ for p in context_parameters}
    )
