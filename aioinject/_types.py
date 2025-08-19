from __future__ import annotations

import collections
import contextlib
import inspect
import sys
import types
import typing
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
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

TypeContext = Mapping[str, type[object]]


class UnwrappedAnnotation(NamedTuple):
    type: type[object]
    args: Sequence[object]


def _get_function_namespace(fn: Callable[..., Any]) -> dict[str, Any]:
    return getattr(sys.modules.get(fn.__module__, None), "__dict__", {})


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
