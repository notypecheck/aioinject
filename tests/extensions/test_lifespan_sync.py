import contextlib
from collections.abc import Iterator

from aioinject import Container, SyncContainer
from aioinject.extensions import LifespanSyncExtension


class LifespanTestExtension(LifespanSyncExtension):
    def __init__(self) -> None:
        self.open: bool = False
        self.closed: bool = False

    @contextlib.contextmanager
    def lifespan_sync(
        self,
        _: Container | SyncContainer,
    ) -> Iterator[None]:
        self.open = True
        yield
        self.closed = True


async def test_async() -> None:
    extension = LifespanTestExtension()
    container = Container(extensions=[extension])
    assert not extension.closed
    assert not extension.open
    async with container:
        assert extension.open
        assert not extension.closed  # type: ignore[unreachable]
    assert extension.closed  # type: ignore[unreachable]


async def test_sync() -> None:
    extension = LifespanTestExtension()
    container = SyncContainer(extensions=[extension])
    assert not extension.closed
    assert not extension.open
    with container:
        assert extension.open
        assert not extension.closed  # type: ignore[unreachable]
    assert extension.closed  # type: ignore[unreachable]
