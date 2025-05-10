from typing import Generic, TypeVar

from aioinject import Container, Object, Scoped


T = TypeVar("T")
K = TypeVar("K")


class A(Generic[T]):
    def __init__(self, t: T) -> None:
        self.t = t


class B(Generic[T, K]):
    def __init__(self, t: T, k: K) -> None:
        self.t = t
        self.k = k


class BSpecialized(B[K, int]):
    pass


class Nested(Generic[T]):
    def __init__(self, obj: BSpecialized[T]) -> None:
        self.obj = obj


async def test_unbound_generic() -> None:
    container = Container()
    container.register(Scoped(A))
    container.register(Object(42))
    container.register(Object("string"))

    async with container.context() as ctx:
        a_int = await ctx.resolve(A[int])
        a_str = await ctx.resolve(A[str])

        assert a_int is not a_str  # type: ignore[comparison-overlap]

        assert a_int.t == 42  # noqa: PLR2004
        assert a_str.t == "string"


async def test_override() -> None:
    container = Container()

    container.register(Scoped(lambda: A(0), interface=A[int]))

    container.register(Scoped(A))
    container.register(Object(42))
    container.register(Object("string"))

    async with container.context() as ctx:
        a = await ctx.resolve(A[int])
        assert a.t == 0

        a_str = await ctx.resolve(A[str])
        assert a_str.t == "string"


async def test_specialized_generic() -> None:
    container = Container()

    container.register(Scoped(BSpecialized))
    container.register(Scoped(str))
    container.register(Scoped(int))

    async with container.context() as ctx:
        obj = await ctx.resolve(BSpecialized[str])
        assert obj.t == ""
        assert obj.k == 0


async def test_nested() -> None:
    container = Container()

    container.register(Scoped(Nested))
    container.register(Scoped(BSpecialized))
    container.register(Scoped(str))
    container.register(Scoped(int))

    async with container.context() as ctx:
        obj = await ctx.resolve(Nested[str])
        assert obj.obj.t == ""
        assert obj.obj.k == 0
