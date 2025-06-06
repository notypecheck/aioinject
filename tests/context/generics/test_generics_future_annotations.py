from __future__ import annotations

from typing import Generic

from aioinject import Container, Scoped
from aioinject._types import T


class TestGeneric(Generic[T]):
    pass


async def dependency() -> TestGeneric[int]:
    return TestGeneric()


async def dependant(_: TestGeneric[int]) -> int:
    return 42


async def test_provide_parametrized_generic() -> None:
    container = Container()
    container.register(Scoped(dependency), Scoped(dependant))
    async with container.context() as ctx:
        await ctx.resolve(int)
