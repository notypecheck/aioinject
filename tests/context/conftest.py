import dataclasses

import pytest

from aioinject import Container, Scoped


class _A:
    pass


@dataclasses.dataclass
class _B:
    a: _A


@dataclasses.dataclass
class _C:
    b: _B


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(Scoped(_A))
    container.register(Scoped(_B))
    container.register(Scoped(_C))
    return container
