import contextlib
from collections.abc import Iterator

from aioinject import SyncContainer
from aioinject.providers.scoped import Singleton


def test_should_close_singletons_sync() -> None:
    shutdown = False

    @contextlib.contextmanager
    def dependency() -> Iterator[int]:
        nonlocal shutdown
        yield 42
        shutdown = True

    container = SyncContainer()
    container.register(Singleton(dependency))
    with container:
        for _ in range(2):
            with container.context() as ctx:
                assert ctx.resolve(int) == 42  #  noqa: PLR2004

        assert shutdown is False
    assert shutdown is True


async def test_root_context_should_close_singletons() -> None:
    open_count = 0
    closed_count = 0

    @contextlib.contextmanager
    def dependency() -> Iterator[int]:
        nonlocal open_count, closed_count
        open_count += 1
        yield i
        closed_count += 1

    container = SyncContainer()
    container.register(Singleton(dependency))

    for i in range(1, 5 + 1):
        with container:
            assert closed_count == i - 1
            assert container.root.resolve(int) == i
            assert open_count == i
            assert closed_count == i - 1
        assert closed_count == i
