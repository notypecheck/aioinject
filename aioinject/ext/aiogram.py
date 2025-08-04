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


class _ContextGetter:
    def __init__(self, *, remove_from_args: bool) -> None:
        self.remove_from_args = remove_from_args

    def __call__(
        self, args: tuple[Any], kwargs: dict[str, Any]
    ) -> aioinject.Context:
        if _ARG_NAME in kwargs:  # pragma: no cover
            if self.remove_from_args:
                return kwargs.pop(_ARG_NAME)
            return kwargs[_ARG_NAME]

        # Try to find a dict-like looking object (in case it's a middleware)
        for arg in args:
            if not isinstance(arg, dict):
                continue
            if _ARG_NAME in arg:
                return arg[_ARG_NAME]

        msg = "Could not find aioinject context, did you forget to add AioinjectMiddleware?"
        raise ValueError(msg)


def inject(function: Callable[P, T]) -> Callable[P, T]:  # pragma: no cover
    signature = inspect.signature(function)
    existing_parameter = signature.parameters.get(_ARG_NAME)
    if not existing_parameter:
        add_parameters_to_signature(function, {_ARG_NAME: aioinject.Context})

    return base_inject(
        function,
        context_parameters=(),
        context_getter=_ContextGetter(remove_from_args=not existing_parameter),
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
