from collections.abc import Sequence
from typing import Generic, TypeVar

from aioinject import Container, FromContext, Object, Scoped, Singleton
from aioinject.scope import CurrentScope
from aioinject.validation.rules import DEFAULT_RULES
from aioinject.validation.validate import validate_or_err


T = TypeVar("T")


class _Logger:
    pass


class _LoggerA(_Logger):
    pass


class _LoggerB(_Logger):
    pass


class _DBConnection:
    pass


class _Model:
    pass


class _Request:
    pass


class _Repository(Generic[T]):
    def __init__(
        self, model: type[T], connection: _DBConnection, req: _Request
    ) -> None:
        self._model = model
        self._connection = connection
        self._req = req


class Service:
    def __init__(
        self,
        repository: _Repository[_Model],
        loggers: Sequence[_Logger],
    ) -> None:
        self._repository = repository
        self._loggers = loggers


async def test_ok() -> None:
    container = Container()
    container.register(
        Singleton(_DBConnection),
        Scoped(_Repository),
        Scoped(Service),
        Object(_LoggerA(), interface=_Logger),
        Object(_LoggerB(), interface=_Logger),
        Object(_Model, interface=type[_Model]),  # type: ignore[arg-type]
        FromContext(_Request, scope=CurrentScope()),
    )

    validate_or_err(container, DEFAULT_RULES)

    async with container, container.context({_Request: _Request()}) as ctx:
        await ctx.resolve(Service)  # Assert that dependency could be resolved
