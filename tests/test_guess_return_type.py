import pytest

from aioinject._internal.type_sources import TypeResolver


def test_type_resolver() -> None:
    resolver = TypeResolver([])
    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        resolver.return_type(42, {})  # type: ignore[arg-type]

    assert (
        str(exc_info.value)
        == "Could not find appropriate dependency source handler, tried []"
    )
