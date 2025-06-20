from aioinject import Container, Object


async def test_union() -> None:
    container = Container()
    container.register(Object(42, interface=int | str))  # type: ignore[arg-type]

    async with container.context() as ctx:
        assert await ctx.resolve(int | str) == 42  # type: ignore[arg-type]   # noqa: PLR2004


async def test_union_generic_arg() -> None:
    container = Container()
    container.register(Object([], interface=list[int | str]))

    async with container.context() as ctx:
        assert await ctx.resolve(list[int | str]) == []
