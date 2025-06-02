from typing import Any

import strawberry

from aioinject import Injected
from aioinject.ext.strawberry import inject
from tests.integrations.conftest import NumberService


@strawberry.type
class Query:
    @strawberry.field
    @inject
    async def number(self, service: Injected[NumberService]) -> int:
        return service.get_number()

    @strawberry.field
    @inject
    async def number_with_info(
        self, service: Injected[NumberService], info: strawberry.Info[Any, Any]
    ) -> int:
        assert info
        assert isinstance(info, strawberry.Info)
        return service.get_number()
