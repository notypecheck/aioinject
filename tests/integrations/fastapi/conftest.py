from collections.abc import AsyncIterator, Iterator
from typing import Annotated

import httpx
import pytest
from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.requests import Request
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from httpx import ASGITransport

import aioinject
from aioinject import Injected
from aioinject.ext.fastapi import AioInjectMiddleware, FastAPIExtension, inject


@inject
def dependency(number: Injected[int]) -> int:
    return number


@inject
async def async_dependency(number: Injected[int]) -> int:
    return number


@inject
def generator_dependency(number: Injected[int]) -> Iterator[int]:
    yield number


@inject
async def async_generator_dependency(
    number: Injected[int],
) -> AsyncIterator[int]:
    yield number


@pytest.fixture
def container(provided_value: int) -> aioinject.Container:
    container = aioinject.Container(extensions=[FastAPIExtension()])
    container.register(aioinject.Object(provided_value))
    return container


@pytest.fixture
def app(container: aioinject.Container) -> FastAPI:  # noqa: C901
    app_ = FastAPI()
    app_.add_middleware(AioInjectMiddleware, container=container)

    @app_.get("/async-route")
    @inject
    async def function_route(
        provided: Injected[int],
    ) -> dict[str, str | int]:
        return {"value": provided}

    @app_.get("/sync-depends")
    @inject
    async def route_with_depends(
        number: Annotated[int, Depends(dependency)],
    ) -> dict[str, str | int]:
        return {"value": number}

    @app_.get("/async-depends")
    @inject
    async def route_with_async_depends(
        number: Annotated[int, Depends(async_dependency)],
    ) -> dict[str, str | int]:
        return {"value": number}

    @app_.get("/gen-depends")
    @inject
    async def route_with_gen_depends(
        number: Annotated[int, Depends(generator_dependency)],
    ) -> dict[str, str | int]:
        return {"value": number}

    @app_.get("/asyncgen-depends")
    @inject
    async def route_with_async_gen_depends(
        number: Annotated[int, Depends(async_generator_dependency)],
    ) -> dict[str, str | int]:
        return {"value": number}

    @app_.websocket("/ws")
    @inject
    async def websocket_route(ws: WebSocket, provided: Injected[int]) -> None:
        await ws.accept()
        await ws.send_json({"value": provided})

    @app_.get("/context-injection")
    @inject
    async def context_injection_route(
        request: Injected[Request], background_tasks: Injected[BackgroundTasks]
    ) -> bool:
        return isinstance(request, Request) and isinstance(
            background_tasks, BackgroundTasks
        )

    return app_


@pytest.fixture
async def http_client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=ASGITransport(app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def starlette_http_client(app: FastAPI) -> AsyncIterator[TestClient]:
    with TestClient(app=app) as client:
        yield client
