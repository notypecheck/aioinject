from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from aioinject.context import ProviderRecord
from aioinject.extensions.providers import ProviderInfo


if TYPE_CHECKING:
    from aioinject import Container, Provider, SyncContainer
    from aioinject.container import Registry


def _dependant_providers(
    registry: Registry, root: ProviderRecord[object]
) -> Iterator[ProviderRecord[object]]:
    stack = [root]
    seen = []
    yield root
    while stack:
        provider = stack.pop()
        for provider_group in registry.providers.values():
            for dependant_provider in provider_group:
                if dependant_provider in seen:
                    continue
                dependant_types = [
                    dep.type_ for dep in dependant_provider.info.dependencies
                ]
                if (
                    provider.info.interface in dependant_types
                    or provider.info.type_ in dependant_types
                ):
                    yield dependant_provider
                    stack.append(dependant_provider)
                    seen.append(dependant_provider)


class _Override:
    def __init__(
        self, container: Container | SyncContainer, provider: Provider[object]
    ) -> None:
        self.container = container
        self.registry = container.registry
        self.provider = provider
        self.prev: list[ProviderRecord[Any]] | None = None
        self.prev_cache: dict[type[object], object] | None = None

        self.extension = self.registry.find_provider_extension(self.provider)
        self.info: ProviderInfo[Any] = self.extension.extract(
            self.provider,
            self.registry.type_context,
            self.registry._type_resolver,  # noqa: SLF001
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
        self.prev_cache = self.container.root.cache.copy()
        self.prev = self.registry.providers.get(self.info.interface)
        self._clear_provider(self.prev)

        self.registry.providers[self.info.interface] = [
            ProviderRecord(
                provider=self.provider,
                ext=self.extension,
                info=self.info,
            )
        ]

    def _exit(self) -> None:
        self._clear_provider(self.registry.providers[self.info.interface])
        if self.prev is not None:
            self.registry.providers[self.info.interface] = self.prev

        if self.prev_cache is not None:
            new_cache = self.container.root.cache
            self.container.root.cache = self.prev_cache
            self.container.root.cache.update(new_cache)

    def _clear_provider(
        self, providers: list[ProviderRecord[object]] | None
    ) -> None:
        if not providers:
            return  # pragma: no cover

        for provider in providers:
            for dependant in _dependant_providers(self.registry, provider):
                for typ in (dependant.info.type_, dependant.info.interface):
                    self.registry.compilation_cache.pop((typ, True), None)
                    self.registry.compilation_cache.pop((typ, False), None)
                    self.container.root.cache.pop(typ, None)


class TestContainer:
    __test__ = False  # pytest

    def __init__(self, container: Container | SyncContainer) -> None:
        self.container = container

    def override(self, provider: Provider[Any]) -> _Override:
        return _Override(self.container, provider)
