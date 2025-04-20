from typing import cast

import pytest
from _pytest.fixtures import SubRequest


pytest_plugins = [
    "anyio",
]


@pytest.fixture(scope="session", autouse=True, params=["asyncio", "trio"])
def anyio_backend(request: SubRequest) -> str:
    return cast("str", request.param)
