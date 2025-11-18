import contextlib
from collections.abc import AsyncIterator

from aioinject import Container
from aioinject.providers.scoped import Singleton


async def test_should_close_singletons() -> None:
    shutdown = False

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal shutdown

        yield 42
        shutdown = True

    container = Container()
    container.register(Singleton(dependency))
    async with container:
        for _ in range(2):
            async with container.context() as ctx:
                assert await ctx.resolve(int) == 42  # noqa: PLR2004

        assert shutdown is False
    assert shutdown is True


async def test_root_context_should_close_singletons() -> None:
    open_count = 0
    closed_count = 0

    @contextlib.asynccontextmanager
    async def dependency() -> AsyncIterator[int]:
        nonlocal open_count, closed_count
        open_count += 1
        yield i
        closed_count += 1

    container = Container()
    container.register(Singleton(dependency))

    for i in range(1, 5 + 1):
        async with container:
            assert closed_count == i - 1
            assert await container.root.resolve(int) == i
            assert open_count == i
            assert closed_count == i - 1
        assert closed_count == i
