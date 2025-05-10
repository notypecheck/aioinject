import contextlib
from collections.abc import AsyncIterator

from typing_extensions import Self


class PropagatedError(Exception):
    pass


class ExceptionPropagation:
    def __init__(self) -> None:
        self.exc: BaseException | None = None

    @contextlib.asynccontextmanager
    async def dependency(self) -> AsyncIterator[Self]:
        try:
            yield self
        except Exception as exc:
            self.exc = exc
            raise
