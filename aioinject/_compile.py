from __future__ import annotations

import dataclasses
import textwrap
import typing
from collections.abc import Awaitable, Callable, Iterator, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from aioinject._types import is_generic_alias
from aioinject.extensions.providers import (
    CacheDirective,
    CompilationDirective,
    Dependency,
    ProviderInfo,
    ResolveDirective,
)
from aioinject.scope import BaseScope


if TYPE_CHECKING:
    from aioinject.container import Extensions, Registry
from aioinject.context import ExecutionContext, ProviderRecord


__all__ = ["CompilationParams", "CompiledFn", "SyncCompiledFn", "compile_fn"]

_T_co = TypeVar("_T_co", covariant=True)


@dataclasses.dataclass(slots=True, kw_only=True)
class ProviderNode:
    type_: type[Any]
    dependencies: tuple[Dependency[object], ...]
    is_iterable: bool
    name: str

    def __hash__(self) -> int:
        return hash((self.type_, self.is_iterable, self.dependencies))


@dataclasses.dataclass
class CompilationParams:
    root: ProviderNode
    nodes: list[ProviderNode]
    scopes: type[BaseScope]


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


def make_dependency_name(type_: type[object]) -> str:
    args = typing.get_args(type_)
    if not args:
        return type_.__name__
    args_str = "_".join(arg.__name__ for arg in args)
    return f"{type_.__name__}_{args_str}"


def sort_dependencies(
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


BODY = """
{async}def factory(scopes: "Mapping[BaseScope, Context]") -> "T":
{body}
    return {return_var_name}"""
PREPARE_SCOPE_CACHE = "{scope_name}_cache = scopes[{scope_name}].cache\n"

PREPARE_SCOPE_EXIT_STACK = (
    "{scope_name}_exit_stack = scopes[{scope_name}].exit_stack\n"
)
CHECK_CACHE = "if ({dependency}_instance := {scope_name}_cache.get({dependency}_type, NotInCache)) is NotInCache:\n"
CHECK_CACHE_STRICT = (
    "{dependency}_instance = {scope_name}_cache[{dependency}_type]\n"
)
CREATE_REGULAR_INSTANCE = (
    "{dependency}_instance = {await}{dependency}_provider.provide({kwargs})\n"
)
CREATE_CONTEXT_MANAGER_INSTANCE = "{dependency}_instance = {await}{scope_name}_exit_stack.{context_manager_method}({dependency}_provider.provide({kwargs}))\n"
STORE_CACHE = "{scope_name}_cache[{dependency}_type] = {dependency}_instance\n"
CALL_ON_RESOLVE_EXTENSION = (
    "for extension in registry.extensions.on_resolve:\n"
    "    await extension.on_resolve(context=scopes[{scope_name}], provider={dependency}_record, instance={dependency}_instance)\n"
)
CALL_SYNC_ON_RESOLVE_EXTENSION = (
    "for extension in registry.extensions.on_resolve_sync:\n"
    "     extension.on_resolve_sync(context=scopes[{scope_name}], provider={dependency}_record, instance={dependency}_instance)\n"
)

CompiledFn = Callable[[ExecutionContext], Awaitable[_T_co]]
SyncCompiledFn = Callable[[ExecutionContext], _T_co]


def create_var_name(dependency: ProviderNode) -> str:
    return dependency.name


def create_provider_name(dependency: ProviderNode) -> str:
    return f"{create_var_name(dependency)}_provider"


def create_type_name(dependency: ProviderNode) -> str:
    return f"{create_var_name(dependency)}_type"


def generate_factory_kwargs(dependencies: Sequence[Dependency[object]]) -> str:
    kwargs = {
        dependency.name: f"{make_dependency_name(dependency.type_)}_instance"
        for dependency in dependencies
    }
    joined = ", ".join(f'"{k}": {v}' for k, v in kwargs.items())
    return "{" + joined + "}"


class Indent:
    def __init__(self, char: str = " " * 4, indent: int = 0) -> None:
        self._char = char
        self.indent = indent

    def format(self, text: str) -> str:
        return textwrap.indent(text, self._char * self.indent)


TCompilationDirective = TypeVar(
    "TCompilationDirective", bound=CompilationDirective
)


def get_directive(
    info: ProviderInfo[Any], directive: type[TCompilationDirective]
) -> TCompilationDirective | None:
    return next(
        (
            d
            for d in info.compilation_directives
            if isinstance(d, directive) and d.is_enabled
        ),
        None,
    )


def _compile_provider(  # noqa: C901
    node: ProviderNode,
    provider: ProviderRecord[Any],
    extensions: Extensions,
    *,
    is_async: bool,
) -> list[str]:
    parts = []

    kwargs = generate_factory_kwargs(node.dependencies)
    indent = Indent(indent=1)

    cache_directive = get_directive(provider.info, CacheDirective)
    resolve_directive = get_directive(provider.info, ResolveDirective)

    common_context = {
        "dependency": create_var_name(node),
        "kwargs": kwargs,
        "scope_name": f"{provider.info.scope.name}_scope",
    }

    if cache_directive:
        if cache_directive.optional:
            parts.append(indent.format(CHECK_CACHE.format_map(common_context)))
            indent.indent += 1
        else:
            parts.append(
                indent.format(CHECK_CACHE_STRICT.format_map(common_context))
            )

    if resolve_directive:
        context = common_context | {
            "context_manager_method": "enter_async_context"
            if resolve_directive.is_async
            else "enter_context",
            "await": "await " if resolve_directive.is_async else "",
        }

        parts.append(
            indent.format(
                CREATE_REGULAR_INSTANCE
                if not resolve_directive.is_context_manager
                else CREATE_CONTEXT_MANAGER_INSTANCE
            ).format_map(context)
        )

    if cache_directive and cache_directive.optional:
        parts.append(indent.format(STORE_CACHE.format_map(common_context)))

    if resolve_directive:
        if is_async and extensions.on_resolve:
            parts.append(
                indent.format(
                    CALL_ON_RESOLVE_EXTENSION.format_map(common_context)
                )
            )

        if not is_async and extensions.on_resolve_sync:
            parts.append(
                indent.format(
                    CALL_SYNC_ON_RESOLVE_EXTENSION.format_map(common_context)
                )
            )

    return parts


def compile_fn(
    params: CompilationParams,
    registry: Registry,
    extensions: Extensions,
    *,
    is_async: bool,
) -> CompiledFn[Any]:
    namespace = {
        "NotInCache": object(),
        "registry": registry,
        **registry.type_context,
    }
    for node in params.nodes:
        provider = registry.get_provider(node.type_)
        namespace[f"{create_provider_name(node)}"] = provider.provider
        namespace[f"{create_var_name(node)}_record"] = provider
        namespace[f"{create_type_name(node)}"] = node.type_

    parts = []

    used_scopes = set()
    for node in params.nodes:
        provider = registry.get_provider(node.type_)
        used_scopes.add(provider.info.scope)

    for scope in used_scopes:
        indent = Indent(indent=1)
        parts.append(
            indent.format(
                PREPARE_SCOPE_CACHE.format_map(
                    {"scope_name": f"{scope.name}_scope"}
                )
            )
        )
        if any(
            directive.is_context_manager
            for node in params.nodes
            if (
                directive := get_directive(
                    registry.get_provider(node.type_).info, ResolveDirective
                )
            )
        ):
            parts.append(
                indent.format(
                    PREPARE_SCOPE_EXIT_STACK.format_map(
                        {"scope_name": f"{scope.name}_scope"}
                    )
                )
            )

    namespace.update({f"{scope.name}_scope": scope for scope in used_scopes})

    for node in params.nodes:
        provider = registry.get_provider(node.type_)
        parts.extend(
            _compile_provider(node, provider, extensions, is_async=is_async)
        )

    body = "".join(parts)
    return_var_name = create_var_name(params.root)
    result = BODY.format_map(
        {
            "body": body,
            "return_var_name": f"{create_var_name(params.root)}_instance",
            "async": "async " if is_async else "",
        }
    )
    localns: dict[str, Any] = {}
    compiled = compile(result, f"aioinject_{return_var_name}", "exec")
    exec(compiled, namespace, localns)  # noqa: S102
    return localns["factory"]
