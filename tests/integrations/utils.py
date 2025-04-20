import contextlib
from collections.abc import AsyncIterator


class PropagatedError(Exception):
    pass


class ExceptionPropagation:
    def __init__(self) -> None:
        self.exc: BaseException | None = None

    @contextlib.asynccontextmanager
    async def dependency(self) -> AsyncIterator[int]:
        try:
            yield 0
        except Exception as exc:
            self.exc = exc
            raise
