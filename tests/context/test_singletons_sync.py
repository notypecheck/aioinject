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
