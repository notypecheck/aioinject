import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast

import grpc  # type: ignore[import-untyped]
import pytest
from _pytest.fixtures import SubRequest
from grpc import ServicerContext
from grpc.aio import Server  # type: ignore[import-untyped]

from aioinject import Container, Context, Injected, Scope
from aioinject.ext.grpcio import AioInjectInterceptor, inject


protos: Any
services: Any
protos, services = grpc.protos_and_services(
    str(
        Path(__file__).parent.joinpath("service.proto").relative_to(Path.cwd())
    )
)


@pytest.fixture(scope="session", autouse=True, params=["asyncio"])
def anyio_backend(request: SubRequest) -> str:
    return cast("str", request.param)


class Service(services.Service):  # type: ignore[misc]
    @inject
    async def Unary(
        self,
        request: protos.Request,
        context: ServicerContext,
        value: Injected[int],
        di_context: Injected[Context],
    ) -> protos.Response:
        assert di_context.scope is Scope.request
        return protos.Response(field=f"{request.field} {value}")

    @inject
    async def UnaryStream(
        self,
        request: protos.Request,
        context: ServicerContext,
        value: Injected[int],
        di_context: Injected[Context],
    ) -> AsyncIterator[protos.Response]:
        assert di_context.scope is Scope.request

        for i in range(10):
            yield protos.Response(field=f"{request.field} {value} {i}")

    @inject
    async def StreamUnary(
        self,
        request: AsyncIterator[protos.Request],
        context: ServicerContext,
        value: Injected[int],
        di_context: Injected[Context],
    ) -> protos.Response:
        assert di_context.scope == Scope.lifetime

        values = [message.field async for message in request]
        values.append(str(value))
        return protos.Response(field=" ".join(values))

    @inject
    async def StreamStream(
        self,
        request: AsyncIterator[protos.Request],
        context: ServicerContext,
        value: Injected[int],
        di_context: Injected[Context],
    ) -> AsyncIterator[protos.Response]:
        assert di_context.scope == Scope.lifetime

        async for message in request:
            yield protos.Response(field=f"{message.field} {value}")


@pytest.fixture
async def grpcio_server(container: Container) -> AsyncIterator[Server]:
    server = grpc.aio.server(interceptors=[AioInjectInterceptor(container)])
    services.add_ServiceServicer_to_server(Service(), server)
    server.add_insecure_port("localhost:50051")
    await server.start()
    yield server
    await server.stop(0)


@pytest.fixture
async def grpcio_client(
    grpcio_server: object,  # noqa: ARG001
) -> AsyncIterator[services.ServiceStub]:
    async with (
        grpc.aio.insecure_channel("localhost:50051") as channel,
    ):
        yield services.ServiceStub(channel)


async def test_unary_unary_ok(
    grpcio_client: services.ServiceStub, provided_value: int
) -> None:
    field = str(uuid.uuid4())
    response = await grpcio_client.Unary(protos.Request(field=field))
    assert response.field == f"{field} {provided_value}"


async def test_unary_stream_ok(
    grpcio_client: services.ServiceStub, provided_value: int
) -> None:
    field = str(uuid.uuid4())
    messages = [
        message
        async for message in grpcio_client.UnaryStream(
            protos.Request(field=field)
        )
    ]
    for number, message in enumerate(messages):
        assert message.field == f"{field} {provided_value} {number}"


async def test_stream_unary_ok(
    grpcio_client: services.ServiceStub, provided_value: int
) -> None:
    fields = [str(uuid.uuid4()) for _ in range(10)]
    call = grpcio_client.StreamUnary()
    for field in fields:
        await call.write(protos.Request(field=field))
    await call.done_writing()

    response = await call
    assert response.field == " ".join([*fields, str(provided_value)])


async def test_stream_stream_ok(
    grpcio_client: services.ServiceStub,
    provided_value: int,
) -> None:
    call = grpcio_client.StreamStream()
    for _ in range(10):
        field = str(uuid.uuid4())
        await call.write(protos.Request(field=field))
        response = await call.read()
        assert response.field == f"{field} {provided_value}"
