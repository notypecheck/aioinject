import dataclasses
from functools import partial

import pytest
import strawberry
from strawberry import Schema

import aioinject
from aioinject import Container, Injected
from aioinject.ext.strawberry import AioInjectExtension, inject
from tests.integrations.conftest import NumberService


@pytest.mark.parametrize("field_name", ["number", "numberWithInfo"])
async def test_schema_execute(
    schema: Schema, container: Container, field_name: str
) -> None:
    query = f"""
    query {{ {field_name} }}
    """

    result = await schema.execute(query=query, context_value={})
    assert not result.errors

    async with container.context() as ctx:
        number = await ctx.resolve(int)

    assert result.data == {field_name: number}


async def test_custom_context(container: Container) -> None:
    @dataclasses.dataclass
    class Context:
        aioinject_context: aioinject.Context | aioinject.SyncContext | None = (
            None
        )

    def setter(
        context: Context,
        aioinject_context: aioinject.Context | aioinject.SyncContext,
    ) -> None:
        context.aioinject_context = aioinject_context

    def getter(context: Context) -> aioinject.Context | aioinject.SyncContext:
        return context.aioinject_context  # type: ignore[return-value]

    custom_inject = partial(inject, context_getter=getter)

    @strawberry.type
    class Query:
        @strawberry.field
        @custom_inject
        async def number(self, service: Injected[NumberService]) -> int:
            return service.get_number()

    schema = Schema(
        query=Query,
        extensions=[AioInjectExtension(container, context_setter=setter)],
    )

    query = """
    query {
        number
    }
    """
    result = await schema.execute(query=query, context_value=Context())
    assert not result.errors

    async with container.context() as ctx:
        number = await ctx.resolve(int)
    assert result.data == {"number": number}
