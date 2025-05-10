from collections.abc import Mapping
from typing import Any

from aioinject._types import T
from aioinject.extensions import ProviderExtension
from aioinject.extensions.providers import (
    CacheDirective,
    ProviderInfo,
)
from aioinject.providers.abc import Provider
from aioinject.scope import BaseScope


class FromContext(Provider[T]):
    def __init__(self, type_: type[T], scope: BaseScope) -> None:
        self.interface = type_
        self.implementation = type_
        self.scope = scope

    def provide(self, kwargs: dict[str, Any]) -> object:
        raise NotImplementedError


class ContextProviderExtension(ProviderExtension[FromContext[Any]]):
    def supports_provider(self, provider: Provider[Any]) -> bool:
        return isinstance(provider, FromContext)

    def extract(
        self,
        provider: FromContext[T],
        type_context: Mapping[str, type[object]],  # noqa: ARG002
    ) -> ProviderInfo[T]:
        return ProviderInfo(
            interface=provider.implementation,
            type_=provider.implementation,
            dependencies=(),
            scope=provider.scope,
            compilation_directives=(CacheDirective(optional=False),),
        )
