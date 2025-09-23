from __future__ import annotations

import contextvars
from typing import TYPE_CHECKING

from grpc import (  # type: ignore[import-untyped]
    HandlerCallDetails,
    RpcMethodHandler,
    ServicerContext,
    stream_stream_rpc_method_handler,
    stream_unary_rpc_method_handler,
    unary_stream_rpc_method_handler,
    unary_unary_rpc_method_handler,
)
from grpc.aio import ServerInterceptor  # type: ignore[import-untyped]

from aioinject._types import (
    P,
    T,
)
from aioinject.decorators import base_inject


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from google.protobuf.message import Message  # type: ignore[import-untyped]

    from aioinject import Container, Context

__all__ = ["AioInjectInterceptor", "inject"]


def inject(function: Callable[P, T]) -> Callable[P, T]:
    return base_inject(
        function,
        context_parameters=(),
        context_getter=lambda args, kwargs: _context_var.get(),  # noqa: ARG005
    )


_context_var: contextvars.ContextVar[Context] = contextvars.ContextVar(
    "aioinject.grpcio.context"
)


class AioInjectInterceptor(ServerInterceptor):  # type: ignore[misc]
    def __init__(self, container: Container) -> None:
        self._container = container

    async def intercept_service(  # noqa: C901
        self,
        continuation: Callable[
            [HandlerCallDetails],
            Awaitable[RpcMethodHandler],
        ],
        handler_call_details: HandlerCallDetails,
    ) -> RpcMethodHandler:
        handler = await continuation(handler_call_details)
        deserializer = handler.request_deserializer
        serializer = handler.response_serializer

        if handler.unary_unary:

            async def unary_unary_behavior(
                request: Message, context: ServicerContext
            ) -> object:
                async with self._container.context() as di_context:
                    _context_var.set(di_context)
                    return await handler.unary_unary(request, context)

            return unary_unary_rpc_method_handler(
                behavior=unary_unary_behavior,
                request_deserializer=deserializer,
                response_serializer=serializer,
            )
        if handler.unary_stream:

            async def unary_stream_behavior(
                request: Message, context: ServicerContext
            ) -> AsyncIterator[object]:
                async with self._container.context() as di_context:
                    _context_var.set(di_context)
                    async for message in handler.unary_stream(
                        request, context
                    ):
                        yield message

            return unary_stream_rpc_method_handler(
                unary_stream_behavior,
                request_deserializer=deserializer,
                response_serializer=serializer,
            )
        if handler.stream_unary:

            async def stream_unary_behavior(
                request: AsyncIterator[Message], context: ServicerContext
            ) -> object:
                _context_var.set(self._container.root)
                return await handler.stream_unary(request, context)

            return stream_unary_rpc_method_handler(
                stream_unary_behavior,
                request_deserializer=deserializer,
                response_serializer=serializer,
            )

        if handler.stream_stream:

            async def stream_stream_behavior(
                request: AsyncIterator[Message], context: ServicerContext
            ) -> AsyncIterator[object]:
                _context_var.set(self._container.root)
                async for message in handler.stream_stream(request, context):
                    yield message

            return stream_stream_rpc_method_handler(
                stream_stream_behavior,
                request_deserializer=deserializer,
                response_serializer=serializer,
            )
        return handler  # pragma: no cover
