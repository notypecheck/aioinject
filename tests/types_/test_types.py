from collections.abc import Iterable, MutableSequence, Sequence

import pytest

from aioinject._types import is_iterable_generic_collection


@pytest.mark.parametrize(
    ("type_", "is_iterable"),
    [
        (str, False),
        (Iterable, False),
        (Iterable[str], True),
        (list[str], True),
        (Sequence[str], True),
        (MutableSequence[str], True),
    ],
)
def test_is_iterable_generic_collection(
    type_: object,
    is_iterable: bool,
) -> None:
    assert is_iterable_generic_collection(type_) is is_iterable
