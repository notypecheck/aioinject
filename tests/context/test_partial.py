import functools
import random

from aioinject import Container, Scoped, Singleton
from aioinject._types import T


async def test_partial_kwargs() -> None:
    number_1 = random.randint(1, 1000)
    number_2 = random.randint(1, 1000)

    async def make_int_str() -> str:
        return f"{number_1}"

    async def fn(value: int, dependency: str) -> int:
        return value + int(dependency)

    container = Container()
    container.register(
        Scoped(functools.partial(fn, value=number_2)), Scoped(make_int_str)
    )
    async with container.context() as ctx:
        number = await ctx.resolve(int)
        assert number == number_1 + number_2


async def test_partial_args() -> None:
    async def fn(typ: type[T], dep: str) -> T:
        assert isinstance(dep, str)
        return typ()

    container = Container()
    container.register(
        Singleton(str), Scoped(functools.partial(fn, int), interface=int)
    )
    async with container.context() as ctx:
        number = await ctx.resolve(int)
        assert number == 0
