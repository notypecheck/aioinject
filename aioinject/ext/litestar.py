from __future__ import annotations

import contextlib
import inspect
import typing
from collections.abc import AsyncIterator, Callable
from typing import ParamSpec, TypeVar

from litestar import Litestar, Request
from litestar.config.app import AppConfig
from litestar.middleware import MiddlewareProtocol
from litestar.plugins import InitPluginProtocol
from litestar.types import ASGIApp, Receive, Scope, Send

from aioinject import Container
from aioinject.decorators import ContextParameter, base_inject


__all__ = ["AioInjectMiddleware", "AioInjectPlugin", "inject"]


_T = TypeVar("_T")
_P = ParamSpec("_P")

_CONTAINER_KEY = "__aioinject_container__"
_CONTEXT_KEY = "__aioinject_context__"

_REQUEST_PARAMETER_NAME = "request"


def inject(function: Callable[_P, _T]) -> Callable[_P, _T]:
    signature = inspect.signature(function)

    should_remove = (
        _REQUEST_PARAMETER_NAME not in signature.parameters
        or typing.get_origin(
            signature.parameters[_REQUEST_PARAMETER_NAME].annotation
        )
        is typing.Annotated
    )

    return base_inject(
        function=function,
        context_parameters=(
            ContextParameter(
                name=_REQUEST_PARAMETER_NAME,
                type_=Request,
                remove=should_remove,
            ),
        ),
        context_getter=lambda args, kwargs: kwargs[  # noqa: ARG005
            _REQUEST_PARAMETER_NAME
        ].scope[_CONTEXT_KEY],
    )


class AioInjectMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        app: Litestar = scope["app"]
        container: Container = app.state[_CONTAINER_KEY]

        async with container.root.context() as context:
            scope[_CONTEXT_KEY] = context  # type: ignore[literal-required]
            await self.app(scope, receive, send)


async def _after_exception(exception: BaseException, scope: Scope) -> None:
    if _CONTEXT_KEY in scope:
        await scope[_CONTEXT_KEY].__aexit__(  # type: ignore[literal-required]
            type(exception),
            exception,
            exception.__traceback__,
        )


class AioInjectPlugin(InitPluginProtocol):
    def __init__(self, container: Container) -> None:
        self.container = container

    @contextlib.asynccontextmanager
    async def _lifespan(
        self,
        _: Litestar,
    ) -> AsyncIterator[None]:
        async with self.container:
            yield

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.state[_CONTAINER_KEY] = self.container
        app_config.middleware.append(AioInjectMiddleware)
        app_config.lifespan.append(self._lifespan)
        app_config.after_exception.append(_after_exception)
        return app_config
