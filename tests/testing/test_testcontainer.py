from aioinject import Container, Object, Scoped
from aioinject.testing import TestContainer


async def test_override() -> None:
    container = Container()
    container.register(Scoped(lambda: 0, interface=int))

    testcontainer = TestContainer(container)

    override = 42

    async with (
        container.context() as ctx,
        testcontainer.override(Object(override)),
    ):
        assert await ctx.resolve(int) is override

    async with container.context() as ctx:
        assert await ctx.resolve(int) == 0

    # Test sync override
    async with (
        container.context() as ctx,
    ):
        with testcontainer.override(Object(override)):
            assert await ctx.resolve(int) is override
