from __future__ import annotations

import collections
import contextlib
import functools
import inspect
import sys
import types
import typing
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from inspect import isclass
from types import GenericAlias
from typing import (
    TYPE_CHECKING,
    Any,
    NamedTuple,
    ParamSpec,
    TypeAlias,
    TypeGuard,
    TypeVar,
)

from typing_extensions import Self

from aioinject.errors import CannotDetermineReturnTypeError
from aioinject.scope import BaseScope


if TYPE_CHECKING:
    from aioinject.context import Context, SyncContext

T = TypeVar("T")
P = ParamSpec("P")
T_co = TypeVar("T_co", covariant=True)

FactoryResult: TypeAlias = (
    T
    | collections.abc.Awaitable[T]
    | collections.abc.Coroutine[Any, Any, T]
    | collections.abc.Iterator[T]
    | collections.abc.AsyncIterator[T]
)
FactoryType: TypeAlias = type[T] | Callable[..., FactoryResult[T]]

_GENERATORS = {
    collections.abc.Generator,
    collections.abc.Iterator,
}
_ASYNC_GENERATORS = {
    collections.abc.AsyncGenerator,
    collections.abc.AsyncIterator,
}

ExecutionContext = dict[BaseScope, "Context | SyncContext"]

CompiledFn = Callable[[ExecutionContext, BaseScope], Awaitable[T_co]]
SyncCompiledFn = Callable[[ExecutionContext, BaseScope], T_co]


class UnwrappedAnnotation(NamedTuple):
    type: type[object]
    args: Sequence[object]


def get_return_annotation(
    ret_annotation: str,
    context: dict[str, Any],
) -> type[Any]:
    return eval(ret_annotation, context)  # noqa: S307


def _get_function_namespace(fn: Callable[..., Any]) -> dict[str, Any]:
    return getattr(sys.modules.get(fn.__module__, None), "__dict__", {})


def _guess_return_type(  # noqa: C901
    factory: FactoryType[T],
    type_context: Mapping[str, type[object]],
) -> type[T]:
    if isinstance(factory, functools.partial):
        factory = factory.func
    unwrapped = inspect.unwrap(factory)

    origin = typing.get_origin(factory)
    is_generic = origin and inspect.isclass(origin)
    if isclass(factory) or is_generic:
        return typing.cast("type[T]", factory)

    try:
        return_type = typing.get_type_hints(
            unwrapped, include_extras=True, localns=type_context
        )["return"]
    except KeyError as e:
        msg = f"Factory {factory.__qualname__} does not specify return type."
        raise CannotDetermineReturnTypeError(msg) from e
    except NameError:
        # handle future annotations.
        # functions might have dependecies in them
        # and we don't have the container context here so
        # we can't call _get_type_hints
        ret_annotation = unwrapped.__annotations__["return"]

        try:
            return_type = get_return_annotation(
                ret_annotation,
                context=_get_function_namespace(unwrapped),
            )
        except NameError as e:
            msg = f"Factory {factory.__qualname__} does not specify return type. Or it's type is not defined yet."
            raise CannotDetermineReturnTypeError(msg) from e
    if origin := typing.get_origin(return_type):
        args = typing.get_args(return_type)

        is_async_gen = (
            origin in _ASYNC_GENERATORS
            and inspect.isasyncgenfunction(unwrapped)
        )
        is_sync_gen = origin in _GENERATORS and inspect.isgeneratorfunction(
            unwrapped,
        )
        if is_async_gen or is_sync_gen:
            return_type = args[0]

    # Classmethod returning `typing.Self`
    if return_type == Self and (
        self_cls := getattr(factory, "__self__", None)
    ):
        if not inspect.isclass(self_cls):
            return self_cls.__class__
        return self_cls

    return return_type


_sentinel = object()


@contextlib.contextmanager
def remove_annotation(
    annotations: dict[str, Any],
    name: str,
) -> Iterator[None]:
    annotation = annotations.pop(name, _sentinel)
    yield
    if annotation is not _sentinel:
        annotations[name] = annotation


def unwrap_annotated(type_hint: Any) -> UnwrappedAnnotation:
    if typing.get_origin(type_hint) is not typing.Annotated:
        return UnwrappedAnnotation(type_hint, ())

    dep_type, *args = typing.get_args(type_hint)
    return UnwrappedAnnotation(dep_type, tuple(args))


def is_iterable_generic_collection(type_: Any) -> bool:
    if not (origin := typing.get_origin(type_)):
        return False

    is_collection = collections.abc.Iterable in inspect.getmro(
        origin
    ) or safe_issubclass(origin, collections.abc.Iterable)
    return bool(is_collection and typing.get_args(type_))


def is_generic_alias(type_: Any) -> TypeGuard[GenericAlias]:
    return isinstance(
        type_,
        types.GenericAlias | typing._GenericAlias,  # type: ignore[attr-defined] # noqa: SLF001
    ) and not is_iterable_generic_collection(type_)


def safe_issubclass(
    obj: type[object], typ: type[object] | tuple[type[object], ...]
) -> bool:
    try:
        return issubclass(obj, typ)
    except TypeError:
        return False


def get_generic_origin(generic: type[object]) -> type[object]:
    if is_generic_alias(generic):
        return typing.get_origin(generic)
    return generic
