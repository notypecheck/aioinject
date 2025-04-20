from __future__ import annotations

import dataclasses
import typing
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any

from aioinject._compilation.naming import make_dependency_name
from aioinject._types import is_generic_alias


if TYPE_CHECKING:
    from aioinject.container import Registry
    from aioinject.extensions.providers import Dependency


@dataclasses.dataclass(slots=True, kw_only=True)
class ProviderNode:
    type_: type[Any]
    dependencies: tuple[Dependency[object], ...]
    is_iterable: bool
    name: str

    def __hash__(self) -> int:
        return hash((self.type_, self.is_iterable, self.dependencies))


def _get_orig_bases(type_: type) -> tuple[type, ...] | None:
    return getattr(type_, "__orig_bases__", None)


def generic_args_map(type_: type[object]) -> dict[str, type[object]]:
    if is_generic_alias(type_):
        params: dict[str, Any] = {
            param.__name__: param
            for param in type_.__origin__.__parameters__  # type: ignore[attr-defined]
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
        if args_map and (
            generic_arguments := get_generic_arguments(inner_type)
        ):
            # This is a generic type, we need to resolve the type arguments
            # and pass them to the provider.
            resolved_args = tuple(
                args_map[arg.__name__] for arg in generic_arguments
            )
            result[dependency.name] = inner_type[resolved_args]
    return result


def resolve_dependencies(
    root: ProviderNode,
    registry: Registry,
) -> Iterator[ProviderNode]:
    stack = [root]
    yield root
    seen = set()
    while stack:
        node = stack.pop()
        providers = (
            registry.get_providers(node.type_)
            if node.is_iterable
            else (registry.get_provider(node.type_),)
        )

        for provider in providers:
            generic_args_map = get_generic_parameter_map(
                provider.info.actual_type, provider.info.dependencies
            )

            for dependency in provider.info.dependencies:
                dependency_type = generic_args_map.get(
                    dependency.name, dependency.type_
                )
                dependency_provider = registry.get_provider(dependency_type)

                dependency_args_map = get_generic_parameter_map(
                    dependency_type, dependency_provider.info.dependencies
                )

                dependency_name = make_dependency_name(dependency_type)
                dependency_node = ProviderNode(
                    name=dependency_name,
                    type_=dependency_type,
                    dependencies=tuple(
                        dep.with_type(
                            dependency_args_map.get(dep.name, dep.type_)
                        )
                        for dep in dependency_provider.info.dependencies
                    ),
                    is_iterable=False,
                )
                if dependency_node in seen:
                    continue

                seen.add(dependency_node)

                yield dependency_node
                stack.append(dependency_node)
