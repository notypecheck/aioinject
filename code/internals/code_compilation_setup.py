import asyncio
import contextlib
from collections.abc import AsyncIterator
from datetime import datetime
from typing import NewType

from aioinject import (
    Container,
    Object,
    Scoped,
    Singleton,
    Transient,
)


class SingletonClient:
    pass


class DBConnection:
    pass


@contextlib.asynccontextmanager
async def setup_db_connection() -> AsyncIterator[DBConnection]:
    yield DBConnection()


Now = NewType("Now", datetime)


class Service:
    def __init__(
        self,
        now_a: Now,
        now_b: Now,
        int_object: int,
        connection: DBConnection,
        client: SingletonClient,
    ) -> None:
        self._now_a = now_a
        self._now_b = now_b
        self._int = int_object
        self._connection = connection
        self._client = client


async def main() -> None:
    container = Container()
    container.register(
        Singleton(SingletonClient),
        Scoped(setup_db_connection),
        Object(42),
        Transient(lambda: datetime.now(), interface=Now),  # noqa: DTZ005
        Scoped(Service),
    )

    async with container, container.context() as context:
        await context.resolve(Service)


if __name__ == "__main__":
    asyncio.run(main())
