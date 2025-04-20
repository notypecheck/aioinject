import collections
import typing

import pytest

from aioinject import (
    Object,
    Provider,
    Scoped,
    Singleton,
    SyncContainer,
    SyncContext,
    Transient,
)
from aioinject._types import T
from aioinject.context import ProviderRecord
from aioinject.extensions import OnResolveSyncExtension


@typing.final
class _TestExtension(OnResolveSyncExtension):
    def __init__(self) -> None:
        self.type_counter: dict[type[object], int] = collections.defaultdict(
            int,
        )

    def on_resolve_sync(
        self,
        context: SyncContext,  # noqa: ARG002
        provider: ProviderRecord[T],
        instance: T,  # noqa: ARG002
    ) -> None:
        self.type_counter[provider.info.interface] += 1


@pytest.mark.parametrize(
    "provider",
    [
        Object(0),
        Scoped(int),
        Transient(int),
        Singleton(int),
    ],
)
def test_on_resolve(provider: Provider[int]) -> None:
    extension = _TestExtension()
    container = SyncContainer(extensions=(extension,))
    container.register(provider)

    with container.context() as ctx:
        for i in range(1, 10 + 1):
            number = ctx.resolve(int)
            assert number == 0
            assert extension.type_counter[int] == (
                i if isinstance(provider, Transient) else 1
            )
