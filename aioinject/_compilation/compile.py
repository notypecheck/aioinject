from __future__ import annotations

import contextlib
import dataclasses
import linecache
import typing
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from aioinject._compilation.naming import (
    create_var_name,
    generate_factory_kwargs,
)
from aioinject._compilation.resolve import (
    AnyNode,
    FromContextNode,
    IterableNode,
    ProviderNode,
)
from aioinject._compilation.util import Indent
from aioinject._types import CompiledFn
from aioinject.errors import ScopeNotFoundError
from aioinject.extensions.providers import (
    CacheDirective,
    CompilationDirective,
    LockDirective,
    ProviderInfo,
    ResolveDirective,
)
from aioinject.scope import BaseScope, CurrentScope


if TYPE_CHECKING:
    from aioinject.container import Extensions, Registry


__all__ = ["CompilationParams", "compile_fn"]


@dataclasses.dataclass
class CompilationParams:
    root: AnyNode
    nodes: Sequence[AnyNode]
    scopes: type[BaseScope]


BODY = """
{async}def factory(scopes: "Mapping[BaseScope, Context]", current_scope: "BaseScope") -> "T":
{body}
    return {return_var_name}"""
PREPARE_SCOPE_CACHE = (
    "try:\n"
    "    {scope_name}_cache = scopes[{scope_name}].cache\n"
    "except KeyError as err:\n"
    '    err_msg = f"Requested scope {scope} not found, current scope is {{current_scope}}"\n'
    "    raise ScopeNotFoundError(err_msg)\n"
)

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
ACQUIRE_LOCK = "{async}with scopes[{scope_name}].lock:\n"
ACQUIRE_DOUBLE_CHECK_LOCK = (
    "{async}with scopes[{scope_name}].lock:\n"
    "    if ({dependency}_instance := {scope_name}_cache.get({dependency}_type, NotInCache)) is NotInCache:\n"
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
CALL_ON_RESOLVE_CONTEXT_EXTENSION = (
    "async with contextlib.AsyncExitStack() as cm:\n"
    "    for extension in registry.extensions.on_resolve_context:\n"
    "        await cm.enter_async_context(extension.on_resolve_context({dependency}_record))\n"
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


def _compile_provider_node(  # noqa: C901
    node: ProviderNode,
    extensions: Extensions,
    *,
    is_async: bool,
) -> list[str]:
    parts: list[str] = []

    kwargs = generate_factory_kwargs(node.dependencies)
    indent = Indent(indent=1)

    provider = node.provider

    cache_directive = get_directive(provider.info, CacheDirective)
    resolve_directive = get_directive(provider.info, ResolveDirective)
    lock_directive = get_directive(provider.info, LockDirective)

    common_context = {
        "dependency": node.name,
        "kwargs": kwargs,
        "scope_name": f"{provider.info.scope.name}_scope",
    }

    if cache_directive:
        if cache_directive.optional:
            parts.append(indent.format(CHECK_CACHE.format_map(common_context)))
            indent.indent += 1
        else:  # pragma: no cover
            parts.append(
                indent.format(CHECK_CACHE_STRICT.format_map(common_context))
            )

    if lock_directive:
        part = (
            ACQUIRE_LOCK if not cache_directive else ACQUIRE_DOUBLE_CHECK_LOCK
        )
        context = common_context | {"async": "async " if is_async else ""}
        parts.append(indent.format(part).format_map(context))
        indent.indent += 1 if not cache_directive else 2

    if resolve_directive:
        context = common_context | {
            "context_manager_method": "enter_async_context"
            if resolve_directive.is_async
            else "enter_context",
            "await": "await " if resolve_directive.is_async else "",
        }

        if extensions.on_resolve_context and is_async:
            parts.append(
                indent.format(CALL_ON_RESOLVE_CONTEXT_EXTENSION).format_map(
                    context
                )
            )
            indent.indent += 1

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


def _compile_iterable_node(
    node: IterableNode,
) -> list[str]:
    deps = ", ".join(f"{dep.name}_instance" for dep in node.dependencies)
    template = f"    {node.name}_instance = [{deps}]\n"
    return [template]


def _compile_from_context_node(node: FromContextNode) -> list[str]:
    scope = (
        "current_scope"
        if isinstance(node.scope, CurrentScope)
        else f"{node.scope.name}_scope"
    )
    name = create_var_name(node)
    return [f"    {name}_instance = scopes[{scope}].cache[{name}_type]\n"]


def _compile_node(
    node: AnyNode,
    extensions: Extensions,
    *,
    is_async: bool,
) -> list[str]:
    match node:
        case ProviderNode():
            return _compile_provider_node(node, extensions, is_async=is_async)
        case IterableNode():
            return _compile_iterable_node(node)
        case FromContextNode():
            return _compile_from_context_node(node)
        case _:  # pragma: no cover
            typing.assert_never(node)  # type: ignore[unreachable]


def compile_fn(  # noqa: C901
    params: CompilationParams,
    registry: Registry,
    extensions: Extensions,
    *,
    is_async: bool,
) -> CompiledFn[Any]:
    namespace = {
        "NotInCache": object(),
        "ScopeNotFoundError": ScopeNotFoundError,
        "registry": registry,
        "contextlib": contextlib,
        **registry.type_context,
    }
    namespace.update(
        {f"{scope.name}_scope": scope for scope in registry.scopes}
    )

    for node in params.nodes:
        match node:
            case ProviderNode():
                provider = node.provider
                namespace[f"{create_var_name(node)}_provider"] = (
                    provider.provider
                )
                namespace[f"{create_var_name(node)}_record"] = provider
                namespace[f"{create_var_name(node)}_type"] = node.type_
            case FromContextNode():
                namespace[f"{create_var_name(node)}_type"] = node.type_
            case IterableNode():
                pass
            case _:  # pragma: no cover
                typing.assert_never(node)  # type: ignore[unreachable]

    parts = []

    used_scopes = set()
    for node in params.nodes:
        match node:
            case ProviderNode():
                used_scopes.add(node.provider.info.scope)
            case IterableNode() | FromContextNode():
                pass
            case _:  # pragma: no cover
                typing.assert_never(node)  # type: ignore[unreachable]

    for scope in used_scopes:
        indent = Indent(indent=1)
        parts.append(
            indent.format(
                PREPARE_SCOPE_CACHE.format_map(
                    {"scope_name": f"{scope.name}_scope", "scope": scope}
                )
            )
        )
        if any(
            directive.is_context_manager
            for node in params.nodes
            if isinstance(node, ProviderNode)
            and (
                directive := get_directive(
                    node.provider.info, ResolveDirective
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

    for node in params.nodes:
        parts.extend(_compile_node(node, extensions, is_async=is_async))

    body = "".join(parts)
    return_var_name = create_var_name(params.root)
    module_src = BODY.format_map(
        {
            "body": body,
            "return_var_name": f"{create_var_name(params.root)}_instance",
            "async": "async " if is_async else "",
        }
    )
    source_filename = f"aioinject_{return_var_name}"
    linecache.cache[source_filename] = (
        len(module_src),
        None,
        module_src.splitlines(keepends=True),
        f"aioinject_{return_var_name}",
    )

    compiled = compile(module_src, source_filename, "exec")
    local_namespace: dict[str, Any] = {}
    exec(compiled, namespace, local_namespace)  # noqa: S102
    return local_namespace["factory"]
