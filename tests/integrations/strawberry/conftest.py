import pytest
from strawberry import Schema

from aioinject import Container
from aioinject.ext.strawberry import AioInjectExtension
from tests.integrations.strawberry.schema import Query


@pytest.fixture
async def schema(container: Container) -> Schema:
    return Schema(query=Query, extensions=[AioInjectExtension(container)])


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
