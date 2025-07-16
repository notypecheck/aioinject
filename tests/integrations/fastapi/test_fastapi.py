import httpx
import pytest
from _pytest.fixtures import SubRequest
from starlette.testclient import TestClient


@pytest.fixture(
    params=[
        "/async-route",
        "/async-depends",
        "/asyncgen-depends",
    ]
)
async def route(request: SubRequest) -> str:
    return request.param


async def test_function_route(
    http_client: httpx.AsyncClient,
    provided_value: int,
    route: str,
) -> None:
    response = await http_client.get(route)
    assert response.status_code == httpx.codes.OK.value
    assert response.json() == {"value": provided_value}


async def test_can_inject_context(
    http_client: httpx.AsyncClient,
) -> None:
    """Should be able to inject Request and BackgroundTasks from context"""
    response = await http_client.get("/context-injection")
    assert response.status_code == httpx.codes.OK.value
    assert response.json() is True


async def test_websocket_route(
    starlette_http_client: TestClient,
    provided_value: int,
) -> None:
    with starlette_http_client.websocket_connect("/ws") as websocket:
        result = websocket.receive_json()
        assert result == {"value": provided_value}
