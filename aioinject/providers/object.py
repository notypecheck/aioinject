from collections.abc import Mapping
from typing import Any, TypeVar

from aioinject.extensions import ProviderExtension
from aioinject.extensions.providers import (
    CacheDirective,
    ProviderInfo,
    ResolveDirective,
)
from aioinject.providers import Provider
from aioinject.scope import BaseScope, Scope


_T = TypeVar("_T")


class Object(Provider[_T]):
    def __init__(self, obj: _T, type_: type[_T] | None = None) -> None:
        self.implementation = obj
        self.interface = type_

    def provide(
        self,
        kwargs: Mapping[str, Any],  # noqa: ARG002
    ) -> _T:
        return self.implementation

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.implementation=}, {self.interface=})"


class ObjectExtension(ProviderExtension[Object[Any]]):
    def __init__(self, default_scope: BaseScope = Scope.lifetime) -> None:
        self.default_scope = default_scope

    def supports_provider(self, provider: Object[object]) -> bool:
        return isinstance(provider, Object)

    def extract(
        self,
        provider: Object[_T],
        type_context: Mapping[str, Any],  # noqa: ARG002
    ) -> ProviderInfo[_T]:
        actual_type = type(provider.implementation)

        return ProviderInfo(
            interface=provider.interface or actual_type,
            actual_type=actual_type,
            dependencies=(),
            scope=self.default_scope,
            compilation_directives=(
                CacheDirective(),
                ResolveDirective(is_async=False, is_context_manager=False),
            ),
        )
