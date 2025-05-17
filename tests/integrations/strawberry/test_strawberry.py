import pytest
from strawberry import Schema

from aioinject import Container


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

    assert result.data
    assert result.data[field_name] == number
