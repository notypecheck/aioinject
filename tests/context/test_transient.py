from aioinject import Container, Transient


class A:
    pass


async def test_identity() -> None:
    class B:
        def __init__(self, a: A, b: A) -> None:
            self.a = a
            self.b = b

    container = Container()
    container.register(Transient(A))
    container.register(Transient(B))

    async with container.context() as ctx:
        b = await ctx.resolve(B)
        assert b.a is not b.b


async def test_identity_different_instances() -> None:
    class B:
        def __init__(self, a: A) -> None:
            self.a = a

    class C:
        def __init__(self, a: A, b: B) -> None:
            self.a = a
            self.b = b

    container = Container()
    container.register(Transient(A))
    container.register(Transient(B))
    container.register(Transient(C))

    async with container.context() as ctx:
        instance = await ctx.resolve(C)
        assert instance.a is not instance.b.a
