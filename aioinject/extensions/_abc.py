from __future__ import annotations

import typing
from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from typing import (
    TYPE_CHECKING,
    Any,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from aioinject._internal.type_sources import (
    ReturnTypeSource,
    TypeResolver,
)


if TYPE_CHECKING:
    from aioinject import Container, Context, SyncContainer, SyncContext
    from aioinject.context import ProviderRecord
    from aioinject.extensions.providers import ProviderInfo
from aioinject._types import T
from aioinject.providers import Provider


_TProvider_contra = TypeVar(
    "_TProvider_contra", bound=Provider[Any], contravariant=True
)


@runtime_checkable
class LifespanExtension(Protocol):
    def lifespan(
        self,
        container: Container,
    ) -> AbstractAsyncContextManager[None]: ...


@runtime_checkable
class LifespanSyncExtension(Protocol):
    def lifespan_sync(
        self,
        container: Container | SyncContainer,
    ) -> AbstractContextManager[None]: ...


@runtime_checkable
class OnInitExtension(Protocol):
    def on_init(
        self,
        container: Container | SyncContainer,
    ) -> None: ...


@typing.runtime_checkable
class ProviderExtension(Protocol[_TProvider_contra]):
    def supports_provider(self, provider: _TProvider_contra) -> bool: ...

    def extract(
        self,
        provider: _TProvider_contra,
        type_context: Mapping[str, type[object]],
        type_resolver: TypeResolver,
    ) -> ProviderInfo[Any]: ...


@runtime_checkable
class OnResolveExtension(Protocol):
    async def on_resolve(
        self,
        context: Context,
        provider: ProviderRecord[T],
        instance: T,
    ) -> None: ...


@runtime_checkable
class OnResolveSyncExtension(Protocol):
    def on_resolve_sync(
        self,
        context: SyncContext,
        provider: ProviderRecord[T],
        instance: T,
    ) -> None: ...


@runtime_checkable
class OnResolveContextExtension(Protocol):
    if TYPE_CHECKING:

        @property
        def enabled(self) -> bool: ...

    def on_resolve_context(
        self, provider: ProviderRecord[Any]
    ) -> AbstractAsyncContextManager[None]: ...


class TypeSourcesExtension:
    def __init__(
        self,
        return_type_sources: Sequence[ReturnTypeSource[Any]],
    ) -> None:
        self.sources = return_type_sources


Extension = (
    ProviderExtension[Any]
    | OnInitExtension
    | LifespanExtension
    | LifespanSyncExtension
    | OnResolveExtension
    | OnResolveSyncExtension
    | OnResolveContextExtension
    | TypeSourcesExtension
)
