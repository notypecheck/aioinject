import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Router
from aiogram.types import TelegramObject

import aioinject
from aioinject._types import P, T
from aioinject.decorators import add_parameters_to_signature, base_inject


__all__ = ["AioInjectMiddleware", "inject"]


_ARG_NAME = "aioinject_context"


def inject(function: Callable[P, T]) -> Callable[P, T]:  # pragma: no cover
    signature = inspect.signature(function)
    existing_parameter = signature.parameters.get(_ARG_NAME)
    if not existing_parameter:
        add_parameters_to_signature(function, {_ARG_NAME: aioinject.Context})

    return base_inject(
        function,
        context_parameters=(),
        context_getter=lambda args, kwargs: kwargs.pop(_ARG_NAME)  # noqa: ARG005
        if not existing_parameter
        else kwargs[_ARG_NAME],
    )


class AioInjectMiddleware(BaseMiddleware):
    def __init__(self, container: aioinject.Container) -> None:
        self.container = container

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.container.context() as ctx:
            data[_ARG_NAME] = ctx
            return await handler(event, data)

    def add_to_router(self, router: Router) -> None:
        for observer in router.observers.values():
            observer.outer_middleware.register(middleware=self)
