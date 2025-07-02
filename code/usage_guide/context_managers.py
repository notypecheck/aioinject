import contextlib
from collections.abc import Iterator

import aioinject
from aioinject import Scoped, Singleton


@contextlib.contextmanager
def singleton_dependency() -> Iterator[int]:
    print("Singleton Startup")
    yield 42
    print("Singleton Shutdown")


@contextlib.contextmanager
def scoped_dependency(number: int) -> Iterator[str]:
    print("Scoped Startup")
    yield str(number)
    print("Scoped Shutdown")


container = aioinject.SyncContainer()
container.register(Singleton(singleton_dependency))
container.register(Scoped(scoped_dependency))

with container:  # noqa: SIM117
    with container.context() as ctx:
        value = ctx.resolve(str)  # Singleton Startup, Scoped Startup
        print(repr(value))  # '42'
    # Scoped Shutdown
# Singleton Shutdown
