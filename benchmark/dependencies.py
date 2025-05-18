import contextlib
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends


class Session:
    pass


@contextlib.asynccontextmanager
async def create_session_cm() -> AsyncIterator[Session]:
    yield Session()


async def create_session() -> AsyncIterator[Session]:
    yield Session()


class RepositoryA:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_session)],
    ) -> None:
        self._session = session


class RepositoryB:
    def __init__(
        self,
        session: Annotated[Session, Depends(create_session)],
    ) -> None:
        self._session = session


class ServiceA:
    def __init__(
        self,
        repository: Annotated[RepositoryA, Depends()],
    ) -> None:
        self._repository = repository


class ServiceB:
    def __init__(
        self,
        repository: Annotated[RepositoryB, Depends()],
    ) -> None:
        self._repository = repository


class UseCase:
    def __init__(
        self,
        service_a: Annotated[ServiceA, Depends()],
        service_b: Annotated[ServiceB, Depends()],
    ) -> None:
        self._service_a = service_a
        self._service_b = service_b

    async def execute(self) -> int:
        return 42
