from __future__ import annotations

import collections
import typing
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Final, Literal, TypeAlias

from typing_extensions import Self

from aioinject._compilation import (
    CompilationParams,
    compile_fn,
)
from aioinject._compilation.resolve import (
    resolve_dependencies,
    sort_nodes,
)
from aioinject._types import CompiledFn, SyncCompiledFn, T, get_generic_origin
from aioinject.context import Context, ProviderRecord, SyncContext
from aioinject.errors import ProviderNotFoundError
from aioinject.extensions import (
    Extension,
    LifespanExtension,
    LifespanSyncExtension,
    OnInitExtension,
    OnResolveContextExtension,
    OnResolveExtension,
    OnResolveSyncExtension,
    ProviderExtension,
)
from aioinject.extensions.providers import ProviderInfo
from aioinject.providers import Provider
from aioinject.providers.context import ContextProviderExtension
from aioinject.providers.object import ObjectProviderExtension
from aioinject.providers.scoped import ScopedProviderExtension
from aioinject.scope import BaseScope, Scope, next_scope


__all__ = ["Container", "Extensions", "Registry", "SyncContainer"]

DEFAULT_EXTENSIONS = (
    ScopedProviderExtension(),
    ObjectProviderExtension(),
    ContextProviderExtension(),
)


class Extensions:
    def __init__(
        self,
        extensions: Sequence[Extension],
        default_extensions: Sequence[Extension] = DEFAULT_EXTENSIONS,
    ) -> None:
        self._extensions: Final = tuple((*extensions, *default_extensions))  # noqa: C409

        self.providers = [
            e for e in self._extensions if isinstance(e, ProviderExtension)
        ]
        self.on_init = [
            e for e in self._extensions if isinstance(e, OnInitExtension)
        ]
        self.lifespan = [
            e
            for e in self._extensions
            if isinstance(e, LifespanExtension | LifespanSyncExtension)
        ]
        self.lifespan_sync = [
            e for e in self._extensions if isinstance(e, LifespanSyncExtension)
        ]
        self.on_resolve = [
            e for e in self._extensions if isinstance(e, OnResolveExtension)
        ]
        self.on_resolve_sync = [
            e
            for e in self._extensions
            if isinstance(e, OnResolveSyncExtension)
        ]
        self.on_resolve_context = [
            e
            for e in self._extensions
            if isinstance(e, OnResolveContextExtension) and e.enabled
        ]


RegistryCacheKey: TypeAlias = tuple[type[object], bool]


class Registry:
    def __init__(
        self, scopes: type[BaseScope], extensions: Extensions
    ) -> None:
        self.scopes = scopes
        self.extensions = extensions
        self.providers: dict[type[Any], list[ProviderRecord[Any]]] = (
            collections.defaultdict(list)
        )
        self.type_context: Final[dict[str, type[object]]] = {}
        self.compilation_cache: Final[
            dict[RegistryCacheKey, CompiledFn[Any]]
        ] = {}

    def register(self, *providers: Provider[Any]) -> None:
        for provider in providers:
            self._register_one(provider)

    def find_provider_extension(
        self, provider: Provider[Any]
    ) -> ProviderExtension[Any]:
        for ext in self.extensions.providers:
            if ext.supports_provider(provider):
                return ext

        err_msg = f"ProviderExtension for provider {provider!r} not found."
        raise ValueError(err_msg)

    def _register_one(self, provider: Provider[T]) -> None:
        ext = self.find_provider_extension(provider)
        if ext.supports_provider(provider):
            info: ProviderInfo[T] = ext.extract(
                provider, type_context=self.type_context
            )
            if any(
                provider.implementation
                == existing_provider.provider.implementation
                for existing_provider in self.providers.get(info.interface, [])
            ):
                msg = (
                    f"Provider for type {info.interface} with same "
                    f"implementation already registered"
                )
                raise ValueError(msg)

            self.providers[info.interface].append(
                ProviderRecord(
                    provider=provider,
                    info=info,
                    ext=ext,
                )
            )
            if class_name := info.type_.__name__:
                self.type_context[class_name] = get_generic_origin(info.type_)

    def get_providers(self, type_: type[T]) -> Sequence[ProviderRecord[T]]:
        if providers := self.providers.get(type_):
            return providers

        # Default to non-generic alias provider if there's one
        if (origin := typing.get_origin(type_)) and (
            providers := self.providers.get(origin)
        ):
            return providers

        err_msg = f"Providers for type {type_.__name__} not found"
        raise ProviderNotFoundError(err_msg)

    def get_provider(self, type_: type[T]) -> ProviderRecord[T]:
        return self.get_providers(type_)[-1]

    @typing.overload
    def compile(
        self,
        type_: type[T],
        *,
        is_async: Literal[True],
    ) -> CompiledFn[T]: ...

    @typing.overload
    def compile(
        self,
        type_: type[T],
        *,
        is_async: Literal[False],
    ) -> SyncCompiledFn[T]: ...

    def compile(
        self,
        type_: type[T],
        *,
        is_async: bool,
    ) -> CompiledFn[T] | SyncCompiledFn[T]:
        key = (type_, is_async)
        if key not in self.compilation_cache:
            nodes = list(resolve_dependencies(root_type=type_, registry=self))
            nodes.reverse()
            result = tuple(sort_nodes(nodes))

            self.compilation_cache[key] = compile_fn(
                CompilationParams(
                    root=result[-1],
                    nodes=result,
                    scopes=self.scopes,
                ),
                registry=self,
                extensions=self.extensions,
                is_async=is_async,
            )
        return self.compilation_cache[key]


def _run_on_init_extensions(container: Container | SyncContainer) -> None:
    for extension in container.extensions.on_init:
        extension.on_init(container)


class _BaseContainer:
    def __init__(
        self,
        extensions: Sequence[Extension],
        default_extensions: Sequence[Extension],
        scopes: type[BaseScope] = Scope,
    ) -> None:
        self.scopes: Final = scopes
        self.extensions = Extensions(
            extensions=extensions, default_extensions=default_extensions
        )
        self.registry = Registry(
            scopes=self.scopes, extensions=self.extensions
        )

    def register(self, *providers: Provider[Any]) -> None:
        self.registry.register(*providers)


class Container(_BaseContainer):
    def __init__(
        self,
        extensions: Sequence[Extension] = (),
        default_extensions: Sequence[Extension] = DEFAULT_EXTENSIONS,
        scopes: type[BaseScope] = Scope,
    ) -> None:
        super().__init__(
            extensions=extensions,
            default_extensions=default_extensions,
            scopes=scopes,
        )
        self._root: Context | None = None
        _run_on_init_extensions(self)

    def context(
        self, context: dict[type[object], object] | None = None
    ) -> Context:
        return self.root.context(context=context)

    @property
    def root(self) -> Context:
        if not self._root:
            self._root = Context(
                scope=next_scope(self.scopes, None),
                context={},
                container=self,
            )
        return self._root

    async def __aenter__(self) -> Self:
        for extension in self.extensions.lifespan:
            if isinstance(extension, LifespanExtension):
                await self.root.exit_stack.enter_async_context(
                    extension.lifespan(self)
                )
            if isinstance(extension, LifespanSyncExtension):
                self.root.exit_stack.enter_context(
                    extension.lifespan_sync(self)
                )

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._root:
            await self._root.__aexit__(exc_type, exc_val, exc_tb)


class SyncContainer(_BaseContainer):
    def __init__(
        self,
        extensions: Sequence[Extension] = (),
        default_extensions: Sequence[Extension] = DEFAULT_EXTENSIONS,
        scopes: type[BaseScope] = Scope,
    ) -> None:
        super().__init__(
            extensions=extensions,
            default_extensions=default_extensions,
            scopes=scopes,
        )
        self._root: SyncContext | None = None
        _run_on_init_extensions(self)

    def __enter__(self) -> Self:
        for extension in self.extensions.lifespan_sync:
            self.root.exit_stack.enter_context(extension.lifespan_sync(self))

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._root:
            self._root.__exit__(exc_type, exc_val, exc_tb)

    @property
    def root(self) -> SyncContext:
        if not self._root:
            self._root = SyncContext(
                scope=next_scope(self.scopes, None),
                context={},
                container=self,
            )
        return self._root

    def context(
        self,
        context: dict[type[object], object] | None = None,
    ) -> SyncContext:
        return self.root.context(context=context)
