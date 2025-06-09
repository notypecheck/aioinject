import pytest

from aioinject import Container, Scoped, Singleton
from aioinject.validation.errors import ValidationError
from aioinject.validation.rules import ScopeMismatchRule
from aioinject.validation.validate import validate_or_err


async def _make_str() -> str:
    return "42"


async def _make_int(s: str) -> int:
    return int(s)


def test_scope_mismatch() -> None:
    container = Container()
    container.register(Scoped(_make_str))
    container.register(Singleton(_make_int))

    with pytest.raises(ValidationError) as err_info:
        validate_or_err(container, (ScopeMismatchRule(),))

    assert str(err_info.value) == (
        "\n"
        "  scope-mismatch:\n"
        "    Provider(int) with scope Scope.lifetime depends on Provider(str) with scope Scope.request, which is lower"
    )
