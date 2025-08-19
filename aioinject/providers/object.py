from __future__ import annotations

import inspect
import typing
from collections.abc import Mapping
from typing import Any, NewType

from aioinject._internal.type_sources import TypeResolver
from aioinject._types import T, is_generic_alias
from aioinject.extensions import ProviderExtension
from aioinject.extensions.providers import (
    CacheDirective,
    ProviderInfo,
    ResolveDirective,
)
from aioinject.providers import Provider
from aioinject.scope import BaseScope, Scope


class Object(Provider[T]):
    def __init__(self, obj: T, interface: type[T] | None = None) -> None:
        self.implementation = obj
        self.interface = interface

    def provide(
        self,
        kwargs: Mapping[str, Any],  # noqa: ARG002
    ) -> T:
        return self.implementation

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.__class__.__name__}({self.implementation=}, {self.interface=})"


class ObjectProviderExtension(ProviderExtension[Object[Any]]):
    def __init__(self, default_scope: BaseScope = Scope.lifetime) -> None:
        self.default_scope = default_scope

    def supports_provider(self, provider: Object[object]) -> bool:
        return isinstance(provider, Object)

    def extract(
        self,
        provider: Object[T],
        type_context: Mapping[str, Any],  # noqa: ARG002
        type_resolver: TypeResolver,  # noqa: ARG002
    ) -> ProviderInfo[T]:
        actual_type = typing.cast(
            "type[T]",
            type[provider.implementation]
            if inspect.isclass(provider.implementation)
            else type(provider.implementation),
        )
        if is_generic_alias(provider.interface) or isinstance(
            provider.interface, NewType
        ):
            actual_type = provider.interface  # type: ignore[assignment]

        return ProviderInfo(
            interface=provider.interface or actual_type,
            type_=actual_type,
            dependencies=(),
            scope=self.default_scope,
            compilation_directives=(
                CacheDirective(),
                ResolveDirective(is_async=False, is_context_manager=False),
            ),
        )
