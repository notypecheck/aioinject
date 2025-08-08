import dataclasses

from aioinject import Container, Object, Scoped, Singleton
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

    async with container.context() as ctx:
        assert await ctx.resolve(int) == 0


async def test_should_not_override_unrelated_providers() -> None:
    class A:
        pass

    @dataclasses.dataclass
    class B:
        a: A

    @dataclasses.dataclass
    class C:
        b: B

    container = Container()
    container.register(Singleton(A), Singleton(B), Singleton(C))
    testcontainer = TestContainer(container)

    a = await container.root.resolve(A)
    b = await container.root.resolve(B)
    c = await container.root.resolve(C)

    async with testcontainer.override(Singleton(B)):
        c_override = await container.root.resolve(C)
        assert c_override is not c
        assert c_override.b is not b
        assert c_override.b.a is a

        assert await container.root.resolve(A) is a
        assert await container.root.resolve(B) is not b

    assert await container.root.resolve(A) is a
    assert await container.root.resolve(B) is b
    assert await container.root.resolve(C) is c


async def test_override_scoped_with_singleton() -> None:
    class A:
        pass

    @dataclasses.dataclass
    class B:
        a: A

    container = Container()
    container.register(Singleton(A), Scoped(B))
    testcontainer = TestContainer(container)

    a = await container.root.resolve(A)

    async with testcontainer.override(Singleton(B)):
        b = await container.root.resolve(B)
        assert b.a is a
        assert b is await container.root.resolve(B)
        assert await container.root.resolve(A) is a

    assert await container.root.resolve(A) is a

    async with container.context() as ctx:
        b_scoped = await ctx.resolve(B)
        assert b_scoped is not b
        assert b.a is a


async def test_should_not_remove_unrelated_objects_from_cache() -> None:
    class A:
        pass

    class B:
        pass

    container = Container()
    container.register(Singleton(A), Singleton(B))
    testcontainer = TestContainer(container)

    async with testcontainer.override(Singleton(B)):
        a = await container.root.resolve(A)
        b = await container.root.resolve(B)

    assert await container.root.resolve(A) is a
    assert await container.root.resolve(B) is not b


async def test_interface() -> None:
    class A:
        pass

    container = Container()
    container.register(Singleton(A))
    testcontainer = TestContainer(container)

    a = await container.root.resolve(A)
    override = object()
    async with testcontainer.override(Object(override, interface=A)):
        a_new = await container.root.resolve(A)
        assert a_new is override

    assert await container.root.resolve(A) is a


async def test_should_remove_dependant_objects() -> None:
    class A:
        pass

    @dataclasses.dataclass
    class B:
        a: A

    @dataclasses.dataclass
    class C:
        b: B

    container = Container()
    container.register(Singleton(A), Singleton(B), Singleton(C))
    testcontainer = TestContainer(container)

    a_mock = A()
    async with testcontainer.override(Object(a_mock)):
        c_mocked = await container.root.resolve(C)

    c = await container.root.resolve(C)
    assert c is not c_mocked
    assert c.b.a is not a_mock
