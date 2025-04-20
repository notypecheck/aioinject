import functools
import inspect
from collections.abc import Mapping
from typing import Any, TypeVar

from aioinject._types import FactoryType, _guess_return_type
from aioinject.dependencies import collect_parameters
from aioinject.errors import CannotDetermineReturnTypeError
from aioinject.extensions import ProviderExtension
from aioinject.extensions.providers import (
    CacheDirective,
    ProviderInfo,
    ResolveDirective,
)
from aioinject.providers import Provider
from aioinject.scope import BaseScope, Scope


_T = TypeVar("_T")


class Scoped(Provider[_T]):
    _DEFAULT_SCOPE = Scope.request
    cache_ok: bool = True

    def __init__(
        self,
        factory: FactoryType[_T],
        interface: type[_T] | None = None,
        scope: BaseScope | None = None,
    ) -> None:
        self.implementation = factory
        self.interface = interface
        self.scope = scope or self._DEFAULT_SCOPE

    def provide(self, kwargs: Mapping[str, Any]) -> object:
        return self.implementation(**kwargs)

    def __repr__(self) -> str:
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


class Singleton(Scoped[_T]):
    _DEFAULT_SCOPE = Scope.lifetime


class Transient(Scoped[_T]):
    _DEFAULT_SCOPE = Scope.lifetime
    cache_ok = False


class ScopedExtension(ProviderExtension[Scoped[Any]]):
    def supports_provider(self, provider: Scoped[object]) -> bool:
        return isinstance(provider, Scoped)

    def extract(
        self,
        provider: Scoped[_T],
        type_context: Mapping[str, type[object]],
    ) -> ProviderInfo[_T]:
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
            actual_type=actual_type,
            dependencies=dependencies,
            scope=provider.scope,
            compilation_directives=(
                CacheDirective(is_enabled=provider.cache_ok),
                ResolveDirective(
                    is_async=provider.is_async,
                    is_context_manager=provider.is_context_manager,
                ),
            ),
        )
