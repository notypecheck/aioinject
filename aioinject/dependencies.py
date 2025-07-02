from __future__ import annotations

import functools
import inspect
import itertools
import typing
from collections.abc import Iterator, Mapping
from inspect import isclass

from aioinject._types import (
    FactoryType,
    remove_annotation,
    unwrap_annotated,
)
from aioinject.extensions.providers import Dependency


def _typevar_map(
    source: FactoryType[object],
) -> tuple[type, Mapping[object, object]]:
    origin = typing.get_origin(source)
    if not isclass(source) and not origin:
        return source, {}  # type: ignore[return-value]

    resolved_source = origin or source
    typevar_map: dict[object, object] = {}
    for base in (source, *getattr(source, "__orig_bases__", [])):
        origin = typing.get_origin(base)
        if not origin:
            continue

        params = getattr(origin, "__parameters__", ())
        args = typing.get_args(base)
        typevar_map |= dict(zip(params, args, strict=False))

    return resolved_source, typevar_map  # type: ignore[return-value]


def _get_ignored_partial_params(
    dependant: functools.partial[object],
) -> Iterator[str]:
    yield from dependant.keywords.keys()

    signature = inspect.signature(dependant.func)
    for param in itertools.islice(
        signature.parameters.values(), len(dependant.args)
    ):
        yield param.name


def collect_parameters(
    dependant: FactoryType[object],
    type_context: Mapping[str, type[object]],
) -> typing.Iterable[Dependency[object]]:
    """Collect parameter list from a function or class"""

    ignored_keywords: set[str] = set()
    if isinstance(dependant, functools.partial):
        ignored_keywords.update(_get_ignored_partial_params(dependant))
        dependant = dependant.func

    source, typevar_map = _typevar_map(source=dependant)

    if inspect.isclass(source):
        source = source.__init__

    with remove_annotation(getattr(source, "__annotations__", {}), "return"):
        type_hints = typing.get_type_hints(
            source, include_extras=True, localns=type_context
        )

    for name, hint in type_hints.items():
        if name in ignored_keywords:
            continue

        dep_type, _ = unwrap_annotated(hint)
        dep_type = typevar_map.get(dep_type, dep_type)  # type: ignore[assignment]
        yield Dependency(
            name=name,
            type_=dep_type,
        )
