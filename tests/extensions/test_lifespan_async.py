import contextlib
from collections.abc import AsyncIterator

from aioinject import Container, SyncContainer
from aioinject.extensions import LifespanExtension


class LifespanTestExtension(LifespanExtension):
    def __init__(self) -> None:
        self.open = False
        self.closed = False

    @contextlib.asynccontextmanager
    async def lifespan(
        self,
        _: Container,
    ) -> AsyncIterator[None]:
        self.open = True
        yield
        self.closed = True


async def test_lifespan_extension() -> None:
    extension = LifespanTestExtension()
    container = Container(extensions=[extension])
    assert not extension.closed
    assert not extension.open
    async with container:
        assert extension.open
        assert not extension.closed  # type: ignore[unreachable]
    assert extension.closed  # type: ignore[unreachable]


async def test_should_not_be_executed_by_sync_context() -> None:
    extension = LifespanTestExtension()
    container = SyncContainer(extensions=[extension])
    assert not extension.closed
    assert not extension.open
    with container:
        pass
    assert not extension.open
    assert not extension.closed
