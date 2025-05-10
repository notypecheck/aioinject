from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from aioinject.context import ProviderRecord
from aioinject.extensions.providers import ProviderInfo


if TYPE_CHECKING:
    from aioinject import Container, Provider, SyncContainer


class _Override:
    def __init__(
        self, container: Container | SyncContainer, provider: Provider[object]
    ) -> None:
        self.container = container
        self.registry = container.registry
        self.provider = provider
        self.prev: list[ProviderRecord[Any]] | None = None

        self.extension = self.registry.find_provider_extension(self.provider)
        self.info: ProviderInfo[Any] = self.extension.extract(
            self.provider, self.registry.type_context
        )

    async def __aenter__(self) -> Self:
        self._enter()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._exit()

    def __enter__(self) -> Self:
        self._enter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._exit()

    def _enter(self) -> None:
        self._clear()

        self.prev = self.registry.providers.get(self.info.interface)

        self.registry.providers[self.info.interface] = [
            ProviderRecord(
                provider=self.provider,
                ext=self.extension,
                info=self.info,
            )
        ]

    def _exit(self) -> None:
        if self.prev is not None:
            self.registry.providers[self.info.interface] = self.prev

        self._clear()

    def _clear(self) -> None:
        self.registry.compilation_cache.clear()
        self.container.root.cache.clear()


class TestContainer:
    __test__ = False  # pytest

    def __init__(self, container: Container | SyncContainer) -> None:
        self.container = container

    def override(self, provider: Provider[Any]) -> _Override:
        return _Override(self.container, provider)
