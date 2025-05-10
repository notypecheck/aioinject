from __future__ import annotations

import collections
import dataclasses
import inspect
import typing
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any, Generic

from aioinject._compilation.naming import make_dependency_name
from aioinject._types import T, is_generic_alias
from aioinject.context import ProviderRecord
from aioinject.errors import ProviderNotFoundError


if TYPE_CHECKING:
    from aioinject.container import Registry
from aioinject.extensions.providers import Dependency


def is_iterable_generic_collection(type_: Any) -> bool:
    if not (origin := typing.get_origin(type_)):
        return False

    return collections.abc.Iterable in inspect.getmro(origin) or issubclass(
        origin, collections.abc.Iterable
    )


@dataclasses.dataclass(slots=True, kw_only=True)
class BoundDependency(Generic[T]):
    name: str
    type_: type[T]
    provider: ProviderRecord[T]


@dataclasses.dataclass(slots=True, kw_only=True)
class ProviderNode:
    provider: ProviderRecord[object]
    type_: type[Any]
    dependencies: tuple[BoundDependency[object], ...]
    name: str

    def __hash__(self) -> int:
        return hash((self.name, False))


@dataclasses.dataclass(slots=True, kw_only=True)
class IterableNode:
    type_: type[Any]
    inner_type: type[Any]
    dependencies: tuple[BoundDependency[object], ...]
    name: str

    def __hash__(self) -> int:
        return hash((self.name, True))


AnyNode = ProviderNode | IterableNode


def _get_orig_bases(type_: type) -> tuple[type, ...] | None:
    return getattr(type_, "__orig_bases__", None)


def generic_args_map(type_: type[object]) -> dict[str, type[object]]:  # noqa: C901
    if is_generic_alias(type_):
        if not (parameters := getattr(type_.__origin__, "__parameters__", ())):
            return {}  # pragma: no cover

        params: dict[str, Any] = {
            param.__name__: param for param in parameters
        }
        return dict(zip(params, type_.__args__, strict=True))

    args_map = {}
    if orig_bases := _get_orig_bases(type_):
        # find the generic parent
        for base in orig_bases:
            if is_generic_alias(base):  # noqa: SIM102
                if params := {
                    param.__name__: param
                    for param in getattr(base.__origin__, "__parameters__", ())
                }:
                    args_map.update(
                        dict(zip(params, base.__args__, strict=True)),
                    )
    return args_map


def get_generic_arguments(type_: Any) -> list[typing.TypeVar] | None:
    """
    Returns generic arguments of given class, e.g. Class[T] would return [~T]
    """
    if is_generic_alias(type_):
        args = typing.get_args(type_)
        return [arg for arg in args if isinstance(arg, typing.TypeVar)]
    return None


def get_generic_parameter_map(
    provided_type: type[object],
    dependencies: Sequence[Dependency[Any]],
) -> dict[str, type[object]]:
    args_map = generic_args_map(provided_type)
    if not args_map:
        return {}

    result = {}
    for dependency in dependencies:
        inner_type = dependency.type_
        if dependency.type_.__name__ in args_map:
            result[dependency.name] = args_map[dependency.type_.__name__]

        if generic_arguments := get_generic_arguments(inner_type):
            # This is a generic type, we need to resolve the type arguments
            # and pass them to the provider.
            resolved_args = tuple(
                args_map[arg.__name__] for arg in generic_arguments
            )
            result[dependency.name] = inner_type[resolved_args]
    return result


def _resolve_provider_node_dependencies(
    type_: type[object], provider: ProviderRecord[object], registry: Registry
) -> tuple[BoundDependency[Any], ...]:
    generic_args_map = get_generic_parameter_map(
        provided_type=type_,
        dependencies=provider.info.dependencies,
    )

    dependencies = []
    for provider_dependency in provider.info.dependencies:
        is_iterable = is_iterable_generic_collection(provider_dependency.type_)

        bound_dependency_type = generic_args_map.get(
            provider_dependency.name, provider_dependency.type_
        )
        dependency_type = (
            provider_dependency.type_ if is_iterable else bound_dependency_type
        )

        dependency_provider = registry.get_provider(
            typing.get_args(bound_dependency_type)[0]
            if is_iterable
            else dependency_type
        )
        dependency_args_map = get_generic_parameter_map(
            bound_dependency_type, dependency_provider.info.dependencies
        )
        resolved_type = (
            dependency_args_map.get(
                provider_dependency.name,
                dependency_type
                if is_generic_alias(dependency_type)
                else dependency_provider.info.type_,
            )
            if not is_iterable
            else dependency_type
        )
        dependency = BoundDependency(
            type_=resolved_type,  # type: ignore[arg-type]
            name=provider_dependency.name,
            provider=dependency_provider,
        )
        dependencies.append(dependency)

    return tuple(dependencies)


def _resolve_node(type_: type[Any], registry: Registry) -> AnyNode:
    try:
        provider = registry.get_provider(type_)
    except ProviderNotFoundError:
        if not is_iterable_generic_collection(type_):  # pragma: no cover
            raise

        inner_type = typing.get_args(type_)[0]
        providers = registry.get_providers(inner_type)

        return IterableNode(
            type_=type_,
            inner_type=inner_type,
            name=make_dependency_name(type_),
            dependencies=tuple(
                BoundDependency(
                    name=make_dependency_name(provider.info.type_),
                    type_=provider.info.type_,
                    provider=provider,
                )
                for provider in providers
            ),
        )

    resolved_type = (
        provider.info.type_ if type_ == provider.info.interface else type_
    )
    return ProviderNode(
        type_=resolved_type,
        name=make_dependency_name(resolved_type),
        provider=provider,
        dependencies=_resolve_provider_node_dependencies(
            resolved_type, provider, registry
        ),
    )


def resolve_dependencies(  # noqa: C901
    root_type: type[Any],
    registry: Registry,
) -> Iterator[AnyNode]:
    stack = [_resolve_node(root_type, registry=registry)]
    seen = set()

    while stack:
        node = stack.pop()
        if node in seen:
            continue

        seen.add(node)
        yield node

        match node:
            case ProviderNode():
                provider = node.provider
                generic_args_map = get_generic_parameter_map(
                    node.type_, provider.info.dependencies
                )
                for dependency in provider.info.dependencies:
                    dependency_type = generic_args_map.get(
                        dependency.name, dependency.type_
                    )
                    stack.append(_resolve_node(dependency_type, registry))

            case IterableNode():
                providers = registry.get_providers(node.inner_type)
                for provider in providers:
                    node = ProviderNode(
                        provider=provider,
                        name=make_dependency_name(provider.info.type_),
                        type_=provider.info.type_,
                        dependencies=_resolve_provider_node_dependencies(
                            node.type_, provider, registry
                        ),
                    )
                    stack.append(node)
            case _:  # pragma: no cover
                typing.assert_never(node)
