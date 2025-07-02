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
