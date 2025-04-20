from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, TypeVar

from aioinject._compilation.naming import (
    create_var_name,
    generate_factory_kwargs,
)
from aioinject._compilation.resolve import ProviderNode
from aioinject._compilation.util import Indent
from aioinject._types import CompiledFn
from aioinject.extensions.providers import (
    CacheDirective,
    CompilationDirective,
    ProviderInfo,
    ResolveDirective,
)
from aioinject.scope import BaseScope


if TYPE_CHECKING:
    from aioinject.container import Extensions, Registry
from aioinject.context import ProviderRecord


__all__ = ["CompilationParams", "compile_fn"]


@dataclasses.dataclass
class CompilationParams:
    root: ProviderNode
    nodes: list[ProviderNode]
    scopes: type[BaseScope]


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
        namespace[f"{create_var_name(node)}_provider"] = provider.provider
        namespace[f"{create_var_name(node)}_record"] = provider
        namespace[f"{create_var_name(node)}_type"] = node.type_

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
