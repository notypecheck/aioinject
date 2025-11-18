from __future__ import annotations

import dataclasses
import functools
from typing import Any, ParamSpec, TypeVar

import strawberry
import uvicorn
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocket
from strawberry import Schema
from strawberry.asgi import GraphQL

import aioinject
from aioinject import Injected
from aioinject.ext.strawberry import AioInjectExtension
from aioinject.ext.strawberry import inject as base_inject


P = ParamSpec("P")
T = TypeVar("T")


def context_getter(
    context: Context,
) -> aioinject.Context | aioinject.SyncContext:
    return context.aioinject_context  # type: ignore[return-value]


def context_setter(
    context: Context,
    aioinject_context: aioinject.Context | aioinject.SyncContext,
) -> None:
    context.aioinject_context = aioinject_context


inject = functools.partial(base_inject, context_getter=context_getter)


@dataclasses.dataclass(slots=True, kw_only=True)
class Context:
    request: Request | WebSocket
    response: Response | WebSocket

    aioinject_context: aioinject.Context | aioinject.SyncContext | None = None


@strawberry.type
class Query:
    @strawberry.field
    @inject
    async def number(self, number: Injected[int]) -> int:
        return number


class MyGraphQL(GraphQL):
    async def get_context(
        self,
        request: Request | WebSocket,
        response: Response | WebSocket,
    ) -> Any:
        return Context(request=request, response=response)


def create_app() -> GraphQL[Any, Any]:
    container = aioinject.Container()
    container.register(aioinject.Object(42))

    schema = Schema(
        query=Query,
        extensions=[
            AioInjectExtension(
                container=container,
                context_setter=context_setter,
            ),
        ],
    )
    return MyGraphQL(schema=schema)


if __name__ == "__main__":
    uvicorn.run("main:create_app", factory=True, reload=True)
