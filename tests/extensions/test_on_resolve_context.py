import contextlib
import dataclasses
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Final

import pytest

from aioinject import Container, Scoped, Singleton, SyncContainer, Transient
from aioinject.context import ProviderRecord
from aioinject.extensions import OnResolveContextExtension


def _now() -> datetime:
    return datetime.now()  # noqa: DTZ005


class _Singleton:
    pass


class _Repository:
    pass


@dataclasses.dataclass
class _Service:
    singleton: _Singleton
    now: datetime
    repository: _Repository


class _TestExtension(OnResolveContextExtension):
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled: Final = enabled
        self.provided: list[type[Any]] = []

    @contextlib.asynccontextmanager
    async def on_resolve_context(
        self, provider: ProviderRecord[Any]
    ) -> AsyncIterator[None]:
        yield
        self.provided.append(provider.info.interface)


@pytest.fixture
def extension() -> _TestExtension:
    return _TestExtension()


@pytest.fixture
def container(extension: OnResolveContextExtension) -> Container:
    container = Container(extensions=[extension])
    container.register(
        Transient(_now),
        Scoped(_Repository),
        Scoped(_Service),
        Singleton(_Singleton),
    )
    return container


async def test_executes_for_each_dependency_in_order(
    container: Container, extension: _TestExtension
) -> None:
    async with container.context() as ctx:
        await ctx.resolve(_Service)
        assert extension.provided == [
            _Singleton,
            datetime,
            _Repository,
            _Service,
        ]


async def test_does_not_execute_if_dependencies_are_cached(
    container: Container, extension: _TestExtension
) -> None:
    async with container.context() as ctx:
        await ctx.resolve(_Service)
        extension.provided.clear()

        await ctx.resolve(_Service)
        assert extension.provided == [datetime]


async def test_executes_once_for_singletons(
    container: Container, extension: _TestExtension
) -> None:
    async with container.context() as ctx:
        await ctx.resolve(_Service)
        assert _Singleton in extension.provided

    extension.provided.clear()

    async with container.context() as ctx:
        await ctx.resolve(_Service)
        assert _Singleton not in extension.provided


async def test_does_not_execute_if_disabled() -> None:
    extension = _TestExtension(enabled=False)
    container = Container(extensions=[extension])
    container.register(Scoped(int))

    async with container.context() as ctx:
        await ctx.resolve(int)
        assert not extension.provided


def test_async_extension_should_not_be_used_in_sync_container() -> None:
    container = SyncContainer(extensions=[_TestExtension()])
    container.register(Scoped(int))
    with container, container.context() as ctx:
        ctx.resolve(int)
