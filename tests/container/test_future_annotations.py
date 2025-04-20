from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from aioinject import Container, Scoped
from aioinject.errors import CannotDetermineReturnTypeError


async def test_deferred_dependencies() -> None:
    if TYPE_CHECKING:
        from decimal import Decimal

    def some_deferred_type() -> Decimal:
        from decimal import Decimal

        return Decimal("1.0")

    class DoubledDecimal:
        def __init__(self, decimal: Decimal) -> None:
            self.decimal = decimal * 2

    container = Container()

    def register_decimal_scoped() -> None:
        from decimal import Decimal

        container.register(Scoped(some_deferred_type, Decimal))

    register_decimal_scoped()
    container.register(Scoped(DoubledDecimal))
    async with container.context() as ctx:
        assert (await ctx.resolve(DoubledDecimal)).decimal == DoubledDecimal(
            some_deferred_type(),
        ).decimal


def test_provider_fn_deferred_dep_misuse() -> None:
    with pytest.raises(CannotDetermineReturnTypeError) as exc_info:
        from tests.container.mod_tests import (
            provider_fn_deferred_dep_misuse,  # noqa: F401
        )
    assert exc_info.match("Or it's type is not defined yet.")
