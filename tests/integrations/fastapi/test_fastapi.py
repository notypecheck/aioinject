import httpx
import pytest
from _pytest.fixtures import SubRequest


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
