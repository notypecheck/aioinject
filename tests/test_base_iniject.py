import contextlib
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest

from aioinject import Container, Context, Injected, Scoped, SyncContainer
from aioinject.decorators import ContextParameter, base_inject


def context_getter(_: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
    return kwargs["context"]


class Dependency:
    def __init__(self) -> None:
        self.closed = False
        self.fn_done = False


@contextlib.asynccontextmanager
async def async_dependency() -> AsyncIterator[Dependency]:
    dependency = Dependency()
    try:
        yield dependency
    finally:
        dependency.closed = True


@pytest.fixture
async def async_container() -> Container:
    container = Container()
    container.register(Scoped(async_dependency))
    return container


@contextlib.contextmanager
def sync_dependency() -> Iterator[Dependency]:
    dependency = Dependency()
    try:
        yield dependency
    finally:
        dependency.closed = True


@pytest.fixture
def sync_container() -> SyncContainer:
    container = SyncContainer()
    container.register(Scoped(sync_dependency))
    return container


async def test_async(async_container: Container) -> None:
    async def fn(value: Injected[Dependency]) -> Dependency:
        value.fn_done = True
        return value

    fn = base_inject(
        fn,
        context_parameters=(
            ContextParameter(
                type_=Context,
                name="context",
            ),
        ),
        context_getter=context_getter,
    )

    async with async_container.context() as ctx:
        result = await fn(context=ctx)  # type: ignore[call-arg]
        assert isinstance(result, Dependency)
        assert result.fn_done
        assert not result.closed
    assert result.closed


async def test_async_iterator(async_container: Container) -> None:
    async def fn(value: Injected[Dependency]) -> AsyncIterator[Dependency]:
        yield value
        value.fn_done = True

    fn = base_inject(
        fn,
        context_parameters=(
            ContextParameter(
                type_=Context,
                name="context",
            ),
        ),
        context_getter=context_getter,
    )

    async with async_container.context() as ctx:
        iterator = aiter(fn(context=ctx))  # type: ignore[call-arg]
        result = await anext(iterator)
        assert isinstance(result, Dependency)
        assert not result.fn_done
        assert not result.closed

        with pytest.raises(StopAsyncIteration):
            await anext(iterator)
        assert result.fn_done
        assert not result.closed  # type: ignore[unreachable]

    assert result.closed  # type: ignore[unreachable]


def test_sync(sync_container: SyncContainer) -> None:
    def fn(value: Injected[Dependency]) -> Dependency:
        value.fn_done = True
        return value

    fn = base_inject(
        fn,
        context_parameters=(
            ContextParameter(
                type_=Context,
                name="context",
            ),
        ),
        context_getter=context_getter,
    )

    with sync_container.context() as ctx:
        result = fn(context=ctx)  # type: ignore[call-arg]
        assert isinstance(result, Dependency)
        assert result.fn_done
        assert not result.closed
    assert result.closed


def test_sync_iterator(sync_container: SyncContainer) -> None:
    def fn(value: Injected[Dependency]) -> Iterator[Dependency]:
        yield value
        value.fn_done = True

    fn = base_inject(
        fn,
        context_parameters=(
            ContextParameter(
                type_=Context,
                name="context",
            ),
        ),
        context_getter=context_getter,
    )

    with sync_container.context() as ctx:
        iterator = iter(fn(context=ctx))  # type: ignore[call-arg]
        result = next(iterator)
        assert isinstance(result, Dependency)
        assert not result.fn_done
        assert not result.closed

        with pytest.raises(StopIteration):
            next(iterator)
        assert result.fn_done
        assert not result.closed  # type: ignore[unreachable]

    assert result.closed  # type: ignore[unreachable]
