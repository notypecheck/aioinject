from collections.abc import Iterable

from aioinject import Container, Scoped


class _Interface:
    pass


class _A(_Interface):
    pass


class _B(_Interface):
    pass


async def test_ok() -> None:
    container = Container()
    container.register(Scoped(_A, interface=_Interface))
    container.register(Scoped(_B, interface=_Interface))

    async with container.context() as context:
        result = list(await context.resolve(Iterable[_Interface]))  # type: ignore[type-abstract]
        assert isinstance(result[0], _A)
        assert isinstance(result[1], _B)


async def test_iterable_and_regular_dependency() -> None:
    """Test if we can provide an iterable dependency and a regular one"""

    class Dependant:
        def __init__(
            self, iterable: list[_Interface], interface: _Interface
        ) -> None:
            self.iterable = iterable
            self.interface = interface

    container = Container()
    container.register(Scoped(_A, interface=_Interface))
    container.register(Scoped(_B, interface=_Interface))
    container.register(Scoped(Dependant))

    async with container.context() as context:
        instance = await context.resolve(Dependant)

        assert isinstance(instance.iterable[0], _A)
        assert isinstance(instance.iterable[1], _B)

        assert instance.iterable[1] is instance.interface
