from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from aiogram import BaseMiddleware, Router
from aiogram.types import TelegramObject

import aioinject
from aioinject import INJECTED, Container, Injected, Object
from aioinject.ext.aiogram import AioInjectMiddleware, inject


_NUMBER = 42


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(Object(_NUMBER))
    return container


async def test_handler(container: Container) -> None:
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


async def test_can_inject_into_middleware(container: Container) -> None:
    class CustomMiddleware(BaseMiddleware):
        @inject
        async def __call__(
            self,
            handler: Callable[  # noqa: ARG002
                [TelegramObject, dict[str, Any]], Awaitable[Any]
            ],
            event: TelegramObject,  # noqa: ARG002
            data: dict[str, Any],  # noqa: ARG002
            number: Injected[int] = INJECTED,
        ) -> Any:
            assert number is _NUMBER

    async def call_next(event: object, data: dict[str, Any]) -> None:
        await CustomMiddleware()(None, event, data)  # type: ignore[arg-type]

    middleware = AioInjectMiddleware(container=container)
    await middleware(handler=call_next, event=object(), data={})  # type: ignore[arg-type]


async def test_no_context_err() -> None:
    @inject
    async def handler(
        event: object,
        data: dict[str, Any],
    ) -> None:
        pass

    with pytest.raises(ValueError) as exc_info:  # noqa: PT011
        await handler(object(), {})

    assert (
        str(exc_info.value)
        == "Could not find aioinject context, did you forget to add AioinjectMiddleware?"
    )


def test_add_to_router() -> None:
    middleware = AioInjectMiddleware(container=Container())

    router = Router()
    middleware.add_to_router(router=router)

    for observer in router.observers.values():
        assert observer.outer_middleware[0] is middleware
