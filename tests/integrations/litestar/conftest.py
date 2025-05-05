from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from httpx import ASGITransport
from litestar import Controller, Litestar, Request, get, post

from aioinject import Container, FromContext, Injected, Scope
from aioinject.ext.litestar import AioInjectPlugin, inject
from tests.integrations.utils import ExceptionPropagation, PropagatedError


class LitestarController(Controller):
    @get("/exception-propagation")
    @inject
    async def exception_propagation(
        self, _: Injected[ExceptionPropagation]
    ) -> None:
        raise PropagatedError

    @get("/str")
    @inject
    async def str_route(self, value: Injected[str]) -> str:
        return value

    @post("/request-no-context")
    @inject
    async def request_context_1(self, request: Request[Any, Any, Any]) -> str:
        return (await request.body()).decode()

    @post("/request-context")
    @inject
    async def request_context_2(self, req: Injected[Request]) -> str:  # type: ignore[type-arg]
        return (await req.body()).decode()


@pytest.fixture
def app(container: Container) -> Litestar:
    container.register(FromContext(Request, scope=Scope.request))

    return Litestar(
        plugins=[AioInjectPlugin(container)],
        route_handlers=[LitestarController],
        debug=True,
    )


@pytest.fixture
async def http_client(app: Litestar) -> AsyncIterator[httpx.AsyncClient]:
    async with (
        app.lifespan(),
        httpx.AsyncClient(
            transport=ASGITransport(app),  # type: ignore[arg-type]
            base_url="http://test",
        ) as client,
    ):
        yield client
