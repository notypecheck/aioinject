import contextlib
from collections.abc import AsyncIterator, Generator, Iterator
from typing import Any

import anyio
import pytest
from typing_extensions import Self

from aioinject import (
    Container,
    Context,
    Object,
    Provider,
    Scoped,
    Singleton,
    SyncContainer,
)
from aioinject.errors import ScopeNotFoundError
from aioinject.providers.context import FromContext
from aioinject.scope import CurrentScope, Scope


class _TestError(Exception):
    pass


class _Session:
    pass


class _Repository:
    def __init__(self, session: _Session) -> None:
        self.session = session


class _Service:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository


@pytest.fixture
def container() -> Container:
    container = Container()
    container.register(Scoped(_Session))
    container.register(Scoped(_Repository))
    container.register(Scoped(_Service))
    return container


def test_can_instantiate_context(container: Container) -> None:
    assert container.context()


async def test_provide_async() -> None:
    class Test:
        pass

    container = Container()
    container.register(Scoped(Test))
    async with container.context() as ctx:
        instance = await ctx.resolve(Test)
        assert isinstance(instance, Test)


class _AwaitableCls:
    def __init__(self) -> None:
        self.awaited = False

    def __await__(self) -> Generator[Any, None, None]:
        self.awaited = True
        return anyio.sleep(0).__await__()  # noqa: ASYNC115


async def _async_awaitable() -> _AwaitableCls:
    return _AwaitableCls()


def _sync_awaitable() -> _AwaitableCls:
    return _AwaitableCls()


@pytest.mark.parametrize(
    "provider",
    [
        Scoped(_async_awaitable),  # type: ignore[arg-type]
        Scoped(_sync_awaitable),  # type: ignore[arg-type]
        Singleton(_async_awaitable),  # type: ignore[arg-type]
        Singleton(_sync_awaitable),  # type: ignore[arg-type]
    ],
)
async def test_should_not_execute_awaitable_classes(
    provider: Provider[_AwaitableCls],
) -> None:
    container = Container()
    container.register(provider)

    async with container.context() as ctx:
        resolved = await ctx.resolve(_AwaitableCls)
        assert isinstance(resolved, _AwaitableCls)
        assert not resolved.awaited


async def test_singleton_contextmanager_error() -> None:
    call_number = 0

    @contextlib.asynccontextmanager
    async def raises_error() -> AsyncIterator[int]:
        nonlocal call_number
        call_number += 1
        if call_number == 1:
            raise _TestError
        yield 42

    container = Container()
    container.register(Singleton(raises_error))

    with pytest.raises(_TestError):
        async with container.context() as ctx:
            await ctx.resolve(int)

    async with container.context() as ctx:
        await ctx.resolve(int)


async def test_returns_self() -> None:
    class Class:
        def __init__(self, number: str) -> None:
            self.number = number

        @classmethod
        async def self_classmethod(cls, number: int) -> Self:
            return cls(number=str(number))

        @classmethod
        @contextlib.asynccontextmanager
        async def async_context_classmethod(
            cls,
            number: int,
        ) -> AsyncIterator[Self]:
            yield cls(number=str(number))

        @classmethod
        @contextlib.contextmanager
        def sync_context_classmethod(cls, number: int) -> Iterator[Self]:
            yield cls(number=str(number))

    for factory in (
        Class.self_classmethod,
        Class.async_context_classmethod,
        Class.sync_context_classmethod,
    ):
        container = Container()
        container.register(Object(42))
        container.register(Scoped(factory))

        async with container.context() as ctx:
            instance = await ctx.resolve(Class)
            assert instance.number == "42"


async def test_context_provider_async() -> None:
    container = Container()
    container.register(FromContext(_Session, scope=Scope.request))
    container.register(Scoped(_Repository))
    session = _Session()

    async with container.context({_Session: session}) as ctx:
        repo = await ctx.resolve(_Repository)
        assert repo.session is session


async def test_context_provider_sync() -> None:
    container = SyncContainer()
    container.register(FromContext(_Session, scope=Scope.request))
    container.register(Scoped(_Repository))
    session = _Session()

    with container.context({_Session: session}) as ctx:
        repo = ctx.resolve(_Repository)
        assert repo.session is session


async def test_latest_registered_interface_is_provided() -> None:
    container = SyncContainer()
    container.register(Object(42), Object(0))
    with container.context() as ctx:
        assert ctx.resolve(int) == 0


async def test_can_inject_context() -> None:
    class NeedsContext:
        def __init__(self, context: Context) -> None:
            self.context = context

    container = Container()
    container.register(Scoped(NeedsContext))
    container.register(FromContext(Context, scope=CurrentScope()))
    async with container.context() as ctx:
        obj = await ctx.resolve(NeedsContext)
        assert obj.context is ctx


async def test_context_injected_from_relevant_scopes() -> None:
    class A:
        def __init__(self, context: Context) -> None:
            self.context = context

    class B:
        def __init__(self, a: A, context: Context) -> None:
            self.a = a
            self.context = context

    container = Container()
    container.register(Singleton(A))
    container.register(Scoped(B))
    container.register(FromContext(Context, scope=CurrentScope()))

    async with container.context() as ctx:
        obj = await ctx.resolve(B)
        assert obj.context is ctx
        assert obj.a.context is container.root


async def test_invalid_scope() -> None:
    def fn() -> int:
        return 42

    container = Container()
    container.register(Scoped(fn))

    with pytest.raises(ScopeNotFoundError) as err_info:
        await container.root.resolve(int)
    assert (
        str(err_info.value)
        == "Requested scope Scope.request not found, current scope is Scope.lifetime"
    )
