from typing import Any

from aiogram import Router

import aioinject
from aioinject import Container, Object
from aioinject.ext.aiogram import AioInjectMiddleware


_NUMBER = 42


async def test_middleware() -> None:
    container = Container()
    container.register(Object(_NUMBER))

    middleware = AioInjectMiddleware(container=container)
    event_ = object()
    data_: dict[str, Any] = {}

    async def handler(
        event: object,
        data: dict[str, Any],
    ) -> None:
        assert event is event_
        assert data is data_
        assert isinstance(data["aioinject_context"], aioinject.Context)

    await middleware(handler=handler, event=event_, data=data_)  # type: ignore[arg-type]


def test_add_to_router() -> None:
    middleware = AioInjectMiddleware(container=Container())

    router = Router()
    middleware.add_to_router(router=router)

    for observer in router.observers.values():
        assert observer.outer_middleware[0] is middleware
