from collections.abc import Mapping
from typing import Any, final

import pytest
from pydantic_settings import BaseSettings

from aioinject import Container, Context, Scoped
from aioinject._types import FactoryResult, T
from aioinject.errors import ProviderNotFoundError
from aioinject.providers import Provider
from aioinject.providers.object import Object
from tests.testservices import AbstractImplA, AbstractImplB


@pytest.fixture
def container() -> Container:
    return Container()


def test_can_init(container: Container) -> None:
    assert container


def container_provider_mapping(
    container: Container,
) -> Mapping[type[object], list[Provider[object]]]:
    return {
        type_: [provider.provider for provider in providers]
        for type_, providers in container.registry.providers.items()
    }


def test_can_retrieve_context(container: Container) -> None:
    ctx = container.context()
    assert isinstance(ctx, Context)


def test_can_register_single(container: Container) -> None:
    provider = Scoped(AbstractImplA)
    container.register(provider)

    record = container.registry.providers[AbstractImplA][0]
    assert record.provider is provider
    assert record.info.interface is AbstractImplA
    assert record.info.type_ is AbstractImplA


def test_can_register_batch(container: Container) -> None:
    provider1 = Scoped(AbstractImplA)
    provider2 = Scoped(AbstractImplB)
    container.register(provider1, provider2)
    excepted = {AbstractImplA: [provider1], AbstractImplB: [provider2]}

    assert container_provider_mapping(container) == excepted


def test_register_unhashable_implementation(
    container: Container,
) -> None:
    class ExampleSettings(BaseSettings):
        value: list[str] = []

    container.register(Object([], interface=list[int]))
    container.register(Object(ExampleSettings(), interface=ExampleSettings))


def test_cant_register_multiple_providers_for_same_type(
    container: Container,
) -> None:
    container.register(Scoped(int))

    with pytest.raises(
        ValueError,
        match="^Provider for type <class 'int'> with same implementation already registered$",
    ):
        container.register(Scoped(int))


def test_can_retrieve_single_provider(container: Container) -> None:
    int_provider = Scoped(int)
    container.register(int_provider)
    assert container.registry.get_provider(int).provider is int_provider


def test_can_retrieve_multiple_providers(container: Container) -> None:
    int_providers = [
        Scoped(lambda: 1, int),
        Scoped(lambda: 2, int),
    ]
    container.register(*int_providers)
    assert len(container.registry.get_providers(int)) == len(int_providers)


def test_missing_provider() -> None:
    container = Container()
    with pytest.raises(ProviderNotFoundError) as exc_info:
        assert container.registry.get_provider(AbstractImplA)

    msg = f"Providers for type {AbstractImplA.__qualname__} not found"
    assert str(exc_info.value) == msg


def test_no_provider_extension() -> None:
    @final
    class CustomProvider(Provider[T]):
        implementation = int

        def provide(self, kwargs: dict[str, Any]) -> FactoryResult[T]:
            raise NotImplementedError

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}()"

    container = Container()
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        container.register(CustomProvider())

    assert (
        str(exc_info.value)
        == "ProviderExtension for provider CustomProvider() not found."
    )
