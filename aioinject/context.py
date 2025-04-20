from __future__ import annotations

import contextlib
import dataclasses
from types import TracebackType
from typing import TYPE_CHECKING, Final, Generic, Self, TypeVar

from aioinject.scope import BaseScope, next_scope


if TYPE_CHECKING:
    from aioinject import Container, Provider, SyncContainer
    from aioinject.extensions import ProviderExtension
    from aioinject.extensions.providers import ProviderInfo


__all__ = ["Context", "ProviderRecord", "SyncContext"]

T = TypeVar("T")


@dataclasses.dataclass(slots=True, kw_only=True)
class ProviderRecord(Generic[T]):
    provider: Provider[T]
    info: ProviderInfo[T]
    ext: ProviderExtension[Provider[T]]


ExecutionContext = dict[BaseScope, "Context | SyncContext"]


class Context:
    def __init__(
        self,
        scope: BaseScope,
        context: ExecutionContext,
        container: Container,
        cache: dict[type[object], object] | None = None,
    ) -> None:
        self.scope: Final = scope
        self.container: Final = container

        self._context = context.copy()
        self._context[scope] = self

        self.cache: dict[type[object], object] = (
            cache if cache is not None else {}
        )
        self.exit_stack = contextlib.AsyncExitStack()

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
            self._context
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


class SyncContext:
    def __init__(
        self,
        scope: BaseScope,
        context: ExecutionContext,
        container: SyncContainer,
        cache: dict[type[object], object] | None = None,
    ) -> None:
        self.scope: Final = scope
        self.container: Final = container

        self._context = context.copy()
        self._context[scope] = self

        self.cache: dict[type[object], object] = (
            cache if cache is not None else {}
        )
        self.exit_stack = contextlib.ExitStack()

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
            self._context
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
