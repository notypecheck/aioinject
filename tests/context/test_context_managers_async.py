import contextlib
from collections.abc import AsyncIterator, Generator, Iterator
from types import TracebackType
from unittest.mock import MagicMock

import pytest

from aioinject import Container, Scoped, SyncContainer
from tests.context.test_context import _Session


class _SyncContextManager:
    def __init__(self) -> None:
        self.mock = MagicMock()

    def __enter__(self) -> None:
        self.mock.open()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.mock.close()


class _AsyncContextManager:
    def __init__(self) -> None:
        self.mock = MagicMock()

    async def __aenter__(self) -> None:
        self.mock.open()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.mock.close()


async def test_async_context_manager() -> None:
    mock = MagicMock()

    @contextlib.asynccontextmanager
    async def get_session() -> AsyncIterator[_Session]:
        mock.open()
        yield _Session()
        mock.close()

    container = Container()
    container.register(Scoped(get_session))
    async with container.context() as ctx:
        mock.open.assert_not_called()
        instance = await ctx.resolve(_Session)
        mock.open.assert_called_once()
        assert isinstance(instance, _Session)
    mock.close.assert_called_once()


async def test_async_context_would_use_sync_context_managers() -> None:
    mock = MagicMock()

    @contextlib.contextmanager
    def get_session() -> Generator[_Session, None, None]:
        mock.open()
        yield _Session()
        mock.close()

    container = Container()
    container.register(Scoped(get_session))
    async with container.context() as ctx:
        mock.open.assert_not_called()
        await ctx.resolve(_Session)
        mock.open.assert_called_once()
        mock.close.assert_not_called()
    mock.close.assert_called_once()


async def test_should_not_use_resolved_class_as_async_context_manager() -> (
    None
):
    container = Container()
    container.register(Scoped(_AsyncContextManager))
    async with container.context() as ctx:
        instance = await ctx.resolve(_AsyncContextManager)
        assert isinstance(instance, _AsyncContextManager)
    instance.mock.open.assert_not_called()
    instance.mock.close.assert_not_called()


def test_sync_context_manager_should_receive_exception() -> None:
    mock = MagicMock()

    class TestError(Exception):
        pass

    @contextlib.contextmanager
    def get_session() -> Iterator[_Session]:
        try:
            yield _Session()
        except TestError:
            mock.exception_happened()

    container = SyncContainer()
    container.register(Scoped(get_session))

    with (  # noqa: PT012
        pytest.raises(TestError),
        container.context() as ctx,
    ):
        session = ctx.resolve(_Session)
        assert isinstance(session, _Session)
        mock.exception_happened.assert_not_called()
        raise TestError

    mock.exception_happened.asssert_called_once()


def test_should_not_use_resolved_class_as_context_manager() -> None:
    container = SyncContainer()
    container.register(Scoped(_SyncContextManager))

    with container.context() as ctx:
        resolved = ctx.resolve(_SyncContextManager)
        resolved.mock.open.assert_not_called()
    resolved.mock.close.assert_not_called()


def test_shutdowns_context_manager() -> None:
    mock = MagicMock()

    @contextlib.contextmanager
    def get_session() -> Iterator[_Session]:
        yield _Session()
        mock.close()

    container = SyncContainer()
    container.register(Scoped(get_session))

    with container.context() as ctx:
        session = ctx.resolve(_Session)
        assert isinstance(session, _Session)
        mock.close.assert_not_called()

    mock.close.assert_called()
