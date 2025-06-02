from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import threading
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from types import TracebackType
from typing import TYPE_CHECKING, Final, Generic

from typing_extensions import Self

from aioinject.scope import BaseScope, next_scope


if TYPE_CHECKING:
    from aioinject import Container, Provider, SyncContainer
    from aioinject.extensions import ProviderExtension
    from aioinject.extensions.providers import ProviderInfo

from aioinject._types import ExecutionContext, T


__all__ = ["Context", "ProviderRecord", "SyncContext"]


@dataclasses.dataclass(slots=True, kw_only=True)
class ProviderRecord(Generic[T]):
    provider: Provider[T]
    info: ProviderInfo[T]
    ext: ProviderExtension[Provider[T]]


class Context:
    def __init__(
        self,
        scope: BaseScope,
        context: ExecutionContext,
        container: Container,
        cache: dict[type[object], object] | None = None,
        lock_factory: Callable[
            [], AbstractAsyncContextManager[object]
        ] = asyncio.Lock,
    ) -> None:
        self.scope: Final = scope
        self.container: Final = container

        self._context = context.copy()
        self._context[scope] = self

        self.cache: dict[type[object], object] = (
            cache if cache is not None else {}
        )
        self.cache[type(self)] = self
        self.exit_stack = contextlib.AsyncExitStack()
        self.lock = lock_factory()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    async def resolve(self, /, type_: type[T]) -> T:
        return await self.container.registry.compile(type_, is_async=True)(
            self._context,
            self.scope,
        )

    def context(
        self,
        context: dict[type[object], object] | None = None,
    ) -> Context:
        return Context(
            context=self._context,
            scope=next_scope(self.container.scopes, self.scope),
            container=self.container,
            cache=context,
        )

    def add_context(
        self,
        context: dict[type[object], object],
    ) -> None:
        for key, value in context.items():
            self.cache[key] = value


class SyncContext:
    def __init__(
        self,
        scope: BaseScope,
        context: ExecutionContext,
        container: SyncContainer,
        cache: dict[type[object], object] | None = None,
        lock_factory: Callable[
            [], AbstractContextManager[object]
        ] = threading.Lock,
    ) -> None:
        self.scope: Final = scope
        self.container: Final = container

        self._context = context.copy()
        self._context[scope] = self

        self.cache: dict[type[object], object] = (
            cache if cache is not None else {}
        )
        self.cache[type(self)] = self
        self.exit_stack = contextlib.ExitStack()
        self.lock = lock_factory()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.exit_stack.__exit__(exc_type, exc_val, exc_tb)

    def resolve(self, /, type_: type[T]) -> T:
        return self.container.registry.compile(type_, is_async=False)(
            self._context,
            self.scope,
        )

    def context(
        self,
        context: dict[type[object], object] | None = None,
    ) -> SyncContext:
        return SyncContext(
            context=self._context,
            scope=next_scope(self.container.scopes, self.scope),
            container=self.container,
            cache=context,
        )

    def add_context(
        self,
        context: dict[type[object], object],
    ) -> None:  # pragma: no cover
        for key, value in context.items():
            self.cache[key] = value
