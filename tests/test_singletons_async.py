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
