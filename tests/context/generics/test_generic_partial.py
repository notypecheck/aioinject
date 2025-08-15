from functools import partial
from typing import TypeVar

import pytest

from aioinject import Container, Singleton
from aioinject.errors import CannotDetermineReturnTypeError


T = TypeVar("T")


def get_settings(cls: type[T]) -> T:
    return cls()


class A:
    pass


class B:
    pass


async def test_ok() -> None:
    container = Container()
    for cls in (A, B):
        container.register(
            Singleton(partial(get_settings, cls), interface=cls)
        )

    async with container:
        assert isinstance(await container.root.resolve(A), A)
        assert isinstance(await container.root.resolve(B), B)


async def test_should_raise_err_without_interface() -> None:
    container = Container()
    provider = Singleton(partial(get_settings, A))
    with pytest.raises(CannotDetermineReturnTypeError):
        container.register(provider)
