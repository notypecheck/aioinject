import pytest

from aioinject import (
    Container,
    Scoped,
    Singleton,
    SyncContainer,
    Transient,
)
from aioinject.validation.errors import ValidationError
from aioinject.validation.rules import (
    NoAsyncDependenciesInSyncContainerRule,
)
from aioinject.validation.validate import validate_or_err


async def _async_dep() -> int:
    return 42


@pytest.mark.parametrize("provider_cls", [Scoped, Singleton, Transient])
def test_sync_container_err(provider_cls: type[Scoped[int]]) -> None:
    container = SyncContainer()
    container.register(provider_cls(_async_dep))
    with pytest.raises(ValidationError) as err_info:
        validate_or_err(container, (NoAsyncDependenciesInSyncContainerRule(),))

    assert str(err_info.value) == (
        "\n  async-dependency:\n    Provider(int) is async"
    )


def test_async_container_ok() -> None:
    container = Container()
    container.register(Scoped(_async_dep))
    validate_or_err(container, (NoAsyncDependenciesInSyncContainerRule(),))
