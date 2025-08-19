from __future__ import annotations

import functools
import inspect
import typing
from collections.abc import Callable, Iterator, Mapping, Sequence
from types import FunctionType, MethodType
from typing import (
    Any,
    Final,
    Protocol,
    TypeVar,
)

from typing_extensions import Self, TypeIs, override

from aioinject._types import (
    _ASYNC_GENERATORS,
    _GENERATORS,
    FactoryType,
    T,
    TypeContext,
    _get_function_namespace,
    get_generic_origin,
)
from aioinject.errors import CannotDetermineReturnTypeError


class ReturnTypeSource(Protocol[T]):
    def accepts(self, factory: Any) -> TypeIs[T]: ...

    def return_type(self, factory: T, type_context: TypeContext) -> object: ...


class ClassSource(ReturnTypeSource[type[object]]):
    def accepts(self, factory: Any) -> TypeIs[type[object]]:
        return inspect.isclass(get_generic_origin(factory))

    def return_type(
        self,
        factory: type[object],
        type_context: TypeContext,  # noqa: ARG002
    ) -> object:
        return factory


class FunctionSource(ReturnTypeSource[FunctionType | MethodType]):
    def accepts(self, factory: Any) -> TypeIs[FunctionType | MethodType]:
        return inspect.isfunction(factory) or inspect.ismethod(factory)

    def return_type(
        self,
        factory: FunctionType | MethodType,
        type_context: TypeContext,
    ) -> object:
        return _function_return_type(
            function=factory, type_context=type_context
        )


class FunctoolsPartialSource(ReturnTypeSource[functools.partial[object]]):
    @override
    def accepts(self, factory: Any) -> TypeIs[functools.partial[object]]:
        return isinstance(factory, functools.partial)

    @override
    def return_type(
        self,
        factory: functools.partial[object],
        type_context: TypeContext,
    ) -> object:
        return_type = _function_return_type(
            function=factory.func,
            type_context=type_context,
        )
        signature = inspect.signature(factory.func)
        generic_map: dict[object, object] = {}
        for k, v in _correlate_parameters(
            factory.args, factory.keywords, signature.parameters
        ):
            if typing.get_origin(k.annotation) is type:
                arg, *_ = typing.get_args(k.annotation)
                generic_map[arg] = v
            if isinstance(k.annotation, TypeVar):
                if inspect.isclass(v):
                    generic_map[k.annotation] = type[v]
                else:
                    generic_map[k.annotation] = type(v)

        return _substitute_generic_params(return_type, generic_map)


def _correlate_parameters(
    args: Sequence[object],
    kwargs: Mapping[str, object],
    parameters: Mapping[str, inspect.Parameter],
) -> Iterator[tuple[inspect.Parameter, object]]:
    for arg, parameter in zip(args, parameters.values(), strict=False):
        yield parameter, arg

    for kwarg, value in kwargs.items():
        if kwarg in parameters:
            yield parameters[kwarg], value


def _substitute_generic_params(
    param: object,
    generics: Mapping[object, object],
) -> object:
    if param in generics:
        return generics[param]

    if not (origin := typing.get_origin(param)):
        return param

    args = typing.get_args(param)
    return origin[tuple(_substitute_generic_params(p, generics) for p in args)]


def _function_return_annotation(
    function: Callable[..., object], type_context: TypeContext
) -> object:
    try:
        return typing.get_type_hints(
            function, include_extras=True, localns=type_context
        )["return"]
    except KeyError as e:
        msg = f"Factory {function.__qualname__} does not specify return type."
        raise CannotDetermineReturnTypeError(msg) from e
    except NameError:
        # handle future annotations.
        # functions might have dependencies in them
        # and we don't have the container context here so
        # we can't call _get_type_hints
        ret_annotation = function.__annotations__["return"]

        try:
            return eval(  # noqa: S307
                ret_annotation,
                _get_function_namespace(function),
            )
        except NameError as e:
            msg = f"Factory {function.__qualname__} does not specify return type. Or it's type is not defined yet."
            raise CannotDetermineReturnTypeError(msg) from e


def _function_return_type(
    function: Callable[..., object],
    type_context: TypeContext,
) -> object:
    unwrapped = inspect.unwrap(function)
    return_type = _function_return_annotation(
        function=unwrapped, type_context=type_context
    )
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
    # Classmethod or bound method returning `typing.Self`
    if return_type == Self and (
        self_cls := getattr(function, "__self__", None)
    ):
        if not inspect.isclass(self_cls):
            return_type = self_cls.__class__
        else:
            return_type = self_cls
    return return_type


class TypeResolver:
    def __init__(
        self, return_type_sources: Sequence[ReturnTypeSource[Any]]
    ) -> None:
        self.sources: Final = return_type_sources

    def return_type(
        self,
        factory: FactoryType[T],
        type_context: TypeContext,
    ) -> type[T]:
        for source in self.sources:
            if source.accepts(factory):
                return typing.cast(
                    "type[T]",
                    source.return_type(
                        factory=factory, type_context=type_context
                    ),
                )

        msg = f"Could not find appropriate dependency source handler, tried {self.sources}"
        raise ValueError(msg)
