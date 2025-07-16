from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING

from fastapi.background import BackgroundTasks
from fastapi.requests import Request
from fastapi.websockets import WebSocket

import aioinject.scope
from aioinject.decorators import ContextParameter, base_inject
from aioinject.extensions import OnInitExtension


if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from aioinject import Container, SyncContainer

from aioinject import FromContext
from aioinject._types import (
    P,
    T,
    safe_issubclass,
    unwrap_annotated,
)


__all__ = ["AioInjectMiddleware", "inject"]


def inject(function: Callable[P, T]) -> Callable[P, T]:
    signature = inspect.signature(function)
    existing_parameter = next(
        (
            param
            for param in signature.parameters.values()
            if safe_issubclass(
                unwrap_annotated(param.annotation).type, (Request, WebSocket)
            )
        ),
        None,
    )
    parameter_name = (
        existing_parameter.name if existing_parameter else "aioinject__request"
    )
    parameter_type = (
        unwrap_annotated(existing_parameter.annotation).type
        if existing_parameter
        else Request
    )

    return base_inject(
        function,
        context_parameters=(
            ContextParameter(
                name=parameter_name,
                type_=parameter_type,
                remove=existing_parameter is None,
            ),
            ContextParameter(
                name="aioinject__background_tasks", type_=BackgroundTasks
            ),
        ),
        context_getter=lambda args, kwargs: kwargs[  # noqa: ARG005
            parameter_name
        ].state.aioinject_context,
    )


class AioInjectMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        container: Container,
    ) -> None:
        self.app = app
        self.container = container

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        async with self.container.context() as context:
            if scope["type"] == "http":
                request = Request(scope=scope, receive=receive, send=send)
                request.state.aioinject_context = context
            if scope["type"] == "websocket":
                ws = WebSocket(scope=scope, receive=receive, send=send)
                ws.state.aioinject_context = context
            await self.app(scope, receive, send)


class FastAPIExtension(OnInitExtension):
    def on_init(
        self,
        container: Container | SyncContainer,
    ) -> None:
        container.register(
            FromContext(Request, scope=aioinject.scope.Scope.request)
        )
        container.register(
            FromContext(BackgroundTasks, scope=aioinject.scope.Scope.request)
        )
