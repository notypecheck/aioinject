from typing import NewType

from aioinject import Container, Object, Scoped


class _Interface:
    pass


class _A(_Interface):
    pass


class _Dependant:
    def __init__(self, interface: _Interface) -> None:
        self.interface = interface


async def test_ok() -> None:
    container = Container()
    container.register(Scoped(_A, interface=_Interface))
    container.register(Scoped(_Dependant))

    async with container.context() as context:
        result = await context.resolve(_Dependant)
        assert isinstance(result, _Dependant)
        assert isinstance(result.interface, _A)


async def test_object() -> None:
    container = Container()
    container.register(Object(_A(), interface=_Interface))
    container.register(Scoped(_Dependant))

    async with container.context() as context:
        result = await context.resolve(_Dependant)
        assert isinstance(result, _Dependant)
        assert isinstance(result.interface, _A)


async def test_object_newtype() -> None:
    A = NewType("A", str)
    B = NewType("B", str)

    container = Container()
    container.register(Object("A", A))
    container.register(Object("B", B))

    async with container.context() as context:
        a = await context.resolve(A)
        b = await context.resolve(B)
        assert a == "A"
        assert b == "B"


async def test_should_be_able_to_resolve_type_directly() -> None:
    container = Container()
    container.register(Scoped(_A, interface=_Interface))
    container.register(Scoped(_A))

    async with container.context() as context:
        assert await context.resolve(_A) is await context.resolve(_Interface)

    async with container.context() as context:
        assert await context.resolve(_Interface) is await context.resolve(_A)
