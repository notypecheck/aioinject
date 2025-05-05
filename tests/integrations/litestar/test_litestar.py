import uuid
from collections.abc import Callable
from http import HTTPStatus

import httpx
import pytest

from aioinject import (
    Container,
    Object,
    Provider,
    Scoped,
    Singleton,
    Transient,
)
from tests.integrations.utils import ExceptionPropagation, PropagatedError


@pytest.mark.parametrize(
    ("provider_type", "should_propagate"),
    [
        (Singleton, False),
        (Scoped, True),
        (Transient, True),
    ],
)
async def test_error_propagation(
    http_client: httpx.AsyncClient,
    container: Container,
    provider_type: Callable[..., Provider[object]],
    should_propagate: bool,
) -> None:
    propagation = ExceptionPropagation()

    container.register(provider_type(propagation.dependency))

    assert propagation.exc is None

    response = await http_client.get("/exception-propagation")
    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    if should_propagate:
        assert isinstance(propagation.exc, PropagatedError)
    else:
        assert propagation.exc is None


async def test_ok(
    http_client: httpx.AsyncClient,
    container: Container,
) -> None:
    value = str(uuid.uuid4())
    container.register(Object(value))

    response = await http_client.get("/str")
    assert response.text == value


@pytest.mark.parametrize(
    "path",
    [
        "/request-no-context",
        "/request-context",
    ],
)
async def test_request_context(
    http_client: httpx.AsyncClient,
    path: str,
) -> None:
    value = str(uuid.uuid4())

    response = await http_client.post(path, content=value)
    assert response.text == value
