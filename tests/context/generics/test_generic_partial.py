from functools import partial
from typing import TypeVar

from aioinject import Container, Singleton
from tests.testservices import A, Multi


T = TypeVar("T")


def get_instance(cls: type[T]) -> T:
    return cls()


def get_type(obj: T) -> type[T]:
    return type(obj)


def get_same(obj: T) -> T:
    return obj


def get_multi(a: A, b: T) -> Multi[A, T]:
    return Multi(a, b)


class ServiceA:
    pass


class ServiceB:
    pass


async def test_ok() -> None:
    container = Container()
    for cls in (ServiceA, ServiceB):
        container.register(
            Singleton(partial(get_instance, cls), interface=cls)
        )

    async with container:
        assert isinstance(await container.root.resolve(ServiceA), ServiceA)
        assert isinstance(await container.root.resolve(ServiceB), ServiceB)


async def test_should_handle_generics_1() -> None:
    container = Container()
    provider = Singleton(partial(get_instance, ServiceA))
    container.register(provider)
    assert isinstance(await container.root.resolve(ServiceA), ServiceA)


async def test_should_handle_generics_2() -> None:
    container = Container()
    provider = Singleton(partial(get_type, ServiceA()))
    container.register(provider)
    assert await container.root.resolve(type[ServiceA]) is ServiceA  # type: ignore[arg-type]


async def test_should_handle_generics_3() -> None:
    container = Container()
    provider = Singleton(partial(get_same, ServiceA))
    container.register(provider)
    assert await container.root.resolve(type[ServiceA]) is ServiceA  # type: ignore[arg-type]


async def test_multi_generic() -> None:
    container = Container()
    a = ServiceA()
    b = ServiceB()
    container.register(Singleton(partial(get_multi, a, b=b)))

    multi = await container.root.resolve(Multi[ServiceA, ServiceB])
    assert multi.a is a
    assert multi.b is b
