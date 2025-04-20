from __future__ import annotations

import collections
import typing
from collections.abc import Sequence
from types import TracebackType
from typing import Any, Final, Literal, Self, TypeAlias, TypeVar

from aioinject._compile import (
    CompilationParams,
    CompiledFn,
    ProviderNode,
    SyncCompiledFn,
    compile_fn,
    get_generic_parameter_map,
    sort_dependencies,
)
from aioinject._types import get_generic_origin
from aioinject.context import Context, ProviderRecord, SyncContext
from aioinject.extensions import (
    Extension,
    LifespanExtension,
    LifespanSyncExtension,
    OnInitExtension,
    OnResolveExtension,
    OnResolveSyncExtension,
    ProviderExtension,
)
from aioinject.extensions.providers import ProviderInfo
from aioinject.providers import Provider
from aioinject.providers.context import ContextProviderExtension
from aioinject.providers.object import ObjectExtension
from aioinject.providers.scoped import ScopedExtension
from aioinject.scope import BaseScope, Scope, next_scope


__all__ = ["Container", "Extensions", "Registry", "SyncContainer"]


T = TypeVar("T")

DEFAULT_EXTENSIONS = (
    ScopedExtension(),
    ObjectExtension(),
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
            e for e in self._extensions if isinstance(e, LifespanExtension)
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

    def _register_one(self, provider: Provider[T]) -> None:
        for ext in self.extensions.providers:
            if ext.supports_provider(provider):
                info: ProviderInfo[T] = ext.extract(
                    provider, type_context=self.type_context
                )
                if any(
                    provider.implementation
                    == existing_provider.provider.implementation
                    for existing_provider in self.providers.get(
                        info.interface, []
                    )
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
                if class_name := info.actual_type.__name__:
                    self.type_context[class_name] = get_generic_origin(
                        info.actual_type
                    )

                break
        else:
            raise ValueError

    def get_providers(self, type_: type[T]) -> Sequence[ProviderRecord[T]]:
        if providers := self.providers.get(type_):
            return providers

        err_msg = f"Providers for type {type_.__name__} not found"
        raise ValueError(err_msg)

    def get_provider(self, type_: type[T]) -> ProviderRecord[T]:
        return self.get_providers(type_)[0]

    @typing.overload
    def compile(
        self, type_: type[T], *, is_async: Literal[True]
    ) -> CompiledFn[T]: ...
    @typing.overload
    def compile(
        self, type_: type[T], *, is_async: Literal[False]
    ) -> SyncCompiledFn[T]: ...

    def compile(
        self, type_: type[T], *, is_async: bool
    ) -> CompiledFn[T] | SyncCompiledFn[T]:
        key = (type_, is_async)
        if key not in self.compilation_cache:
            provider = self.get_provider(type_)

            generic_args_map = get_generic_parameter_map(
                provided_type=provider.info.actual_type,
                dependencies=provider.info.dependencies,
            )
            root = ProviderNode(
                type_=type_,
                is_iterable=False,
                dependencies=tuple(
                    dep.with_type(generic_args_map.get(dep.name, dep.type_))
                    for dep in provider.info.dependencies
                ),
                name="root",
            )
            result = list(sort_dependencies(root, registry=self))
            result.reverse()
            self.compilation_cache[key] = compile_fn(
                CompilationParams(
                    root=root,
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
        if not self._root:
            self._root = Context(
                scope=next_scope(self.scopes, None),
                context={},
                container=self,
            )

        for extension in self.extensions.lifespan:
            await self.root.exit_stack.enter_async_context(
                extension.lifespan(self)
            )
        for sync_extension in self.extensions.lifespan_sync:
            self._root.exit_stack.enter_context(
                sync_extension.lifespan_sync(self)
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
        if not self._root:
            self._root = SyncContext(
                scope=next_scope(self.scopes, None),
                context={},
                container=self,
            )

        for extension in self.extensions.lifespan_sync:
            self._root.exit_stack.enter_context(extension.lifespan_sync(self))

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
