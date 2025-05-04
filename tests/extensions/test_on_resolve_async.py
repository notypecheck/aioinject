import collections
import typing

import pytest

from aioinject import (
    Container,
    Context,
    Object,
    Provider,
    Scoped,
    Singleton,
    Transient,
)
from aioinject._types import T
from aioinject.context import ProviderRecord
from aioinject.extensions import OnResolveExtension


@typing.final
class _TestExtension(OnResolveExtension):
    def __init__(self) -> None:
        self.type_counter: dict[type[object], int] = collections.defaultdict(
            int,
        )

    async def on_resolve(
        self,
        context: Context,  # noqa: ARG002
        provider: ProviderRecord[T],
        instance: T,  # noqa: ARG002
    ) -> None:
        self.type_counter[provider.info.type_] += 1


@pytest.mark.parametrize(
    "provider",
    [
        Object(0),
        Scoped(int),
        Transient(int),
        Singleton(int),
    ],
)
async def test_on_resolve(provider: Provider[int]) -> None:
    extension = _TestExtension()
    container = Container(extensions=(extension,))
    container.register(provider)

    async with container, container.context() as ctx:
        for i in range(1, 10 + 1):
            number = await ctx.resolve(int)
            assert number == 0
            assert extension.type_counter[int] == (
                i if isinstance(provider, Transient) else 1
            )
