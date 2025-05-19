import functools
import inspect
from collections.abc import Mapping
from typing import Any

from aioinject._types import FactoryResult, FactoryType, T, _guess_return_type
from aioinject.dependencies import collect_parameters
from aioinject.errors import CannotDetermineReturnTypeError
from aioinject.extensions import ProviderExtension
from aioinject.extensions.providers import (
    CacheDirective,
    LockDirective,
    ProviderInfo,
    ResolveDirective,
)
from aioinject.providers import Provider
from aioinject.scope import BaseScope, Scope


class Scoped(Provider[T]):
    cache_ok: bool = True

    def __init__(
        self,
        factory: FactoryType[T],
        interface: type[T] | None = None,
        scope: BaseScope | None = None,
    ) -> None:
        self.implementation = factory
        self.interface = interface
        self.scope = scope

    def provide(self, kwargs: Mapping[str, Any]) -> FactoryResult[T]:
        return self.implementation(**kwargs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}({self.implementation=}, {self.interface=})"

    @functools.cached_property
    def is_async(self) -> bool:
        unwrapped = inspect.unwrap(self.implementation)
        return inspect.iscoroutinefunction(
            unwrapped
        ) or inspect.isasyncgenfunction(unwrapped)

    @functools.cached_property
    def is_context_manager(self) -> bool:
        unwrapped = inspect.unwrap(self.implementation)
        return inspect.isgeneratorfunction(
            unwrapped
        ) or inspect.isasyncgenfunction(unwrapped)


class Singleton(Scoped[T]):
    pass


class Transient(Scoped[T]):
    cache_ok = False


class ScopedProviderExtension(ProviderExtension[Scoped[Any]]):
    def __init__(
        self,
        default_singleton_scope: BaseScope = Scope.lifetime,
        default_scope: BaseScope = Scope.request,
    ) -> None:
        self._default_singleton_scope = default_singleton_scope
        self._default_scope = default_scope

    def supports_provider(self, provider: Scoped[object]) -> bool:
        return isinstance(provider, Scoped)

    def extract(
        self,
        provider: Scoped[T],
        type_context: Mapping[str, type[object]],
    ) -> ProviderInfo[T]:
        scope = (
            provider.scope
            if provider.scope is not None
            else (
                self._default_singleton_scope
                if isinstance(provider, Singleton)
                else self._default_scope
            )
        )

        dependencies = tuple(
            collect_parameters(
                dependant=provider.implementation,
                type_context=type_context,
            )
        )

        try:
            actual_type = _guess_return_type(
                provider.implementation, type_context=type_context
            )
        except CannotDetermineReturnTypeError:
            if not provider.interface:
                raise
            actual_type = provider.interface

        return ProviderInfo(
            interface=provider.interface or actual_type,
            type_=actual_type,
            dependencies=dependencies,
            scope=scope,
            compilation_directives=(
                CacheDirective(is_enabled=provider.cache_ok),
                ResolveDirective(
                    is_async=provider.is_async,
                    is_context_manager=provider.is_context_manager,
                ),
                LockDirective(is_enabled=isinstance(provider, Singleton)),
            ),
        )
