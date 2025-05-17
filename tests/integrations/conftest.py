import random
import uuid
from typing import TypedDict

import pytest

import aioinject


@pytest.fixture
def provided_value() -> int:
    return random.randint(1, 1_000_000)


class NumberService:
    def __init__(self, value: int) -> None:
        self._value = value

    def get_number(self) -> int:
        return self._value


class ScopedNode(TypedDict):
    """A node with unique id per scope."""

    id: str


def get_node() -> ScopedNode:
    return {"id": uuid.uuid4().hex}


@pytest.fixture
def container(provided_value: int) -> aioinject.Container:
    container = aioinject.Container()
    container.register(aioinject.Object(provided_value))
    container.register(aioinject.Scoped(NumberService))
    container.register(aioinject.Scoped(get_node))
    return container
