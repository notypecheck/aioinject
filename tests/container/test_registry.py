from __future__ import annotations

import pytest

from aioinject import Container, Scoped


class A:
    def __init__(self, b: B) -> None: ...


class B:
    def __init__(self, a: A) -> None: ...


def test_cyclic_dependency() -> None:
    container = Container()
    container.register(Scoped(A), Scoped(B))
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        container.registry.compile(A, is_async=False)

    assert str(exc_info.value) == (
        "Could not resolve dependencies for type <class 'tests.container.test_registry.B'>\n"
        "  unresolved dependencies: [<class 'tests.container.test_registry.A'>]"
    )
