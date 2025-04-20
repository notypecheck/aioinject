from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import time
from collections.abc import AsyncIterator, Iterator
from datetime import timedelta

import dependency_injector.containers
import dependency_injector.providers
import dishka
import rodi

import aioinject


class Session:
    pass


@contextlib.asynccontextmanager
async def make_session() -> AsyncIterator[Session]:
    yield Session()


async def make_session_generator() -> AsyncIterator[Session]:
    yield Session()


def make_session_generator_sync() -> Iterator[Session]:
    yield Session()


class RepoA:
    def __init__(self, session: Session) -> None:
        self.session = session


class RepoB:
    def __init__(self, session: Session) -> None:
        self.session = session


class Service:
    def __init__(self, a: RepoA, b: RepoB) -> None:
        self.a = a
        self.b = b


@dataclasses.dataclass
class BenchmarkReport:
    name: str
    duration: timedelta


async def bench_python(iterations: int) -> BenchmarkReport:
    t = time.perf_counter()
    for _ in range(iterations):
        session = Session()
        Service(
            a=RepoA(session),
            b=RepoB(session),
        )
    duration = time.perf_counter() - t
    return BenchmarkReport(name="python", duration=timedelta(seconds=duration))


async def bench_dishka(iterations: int) -> BenchmarkReport:
    provider = dishka.Provider(scope=dishka.Scope.REQUEST)
    provider.provide(make_session_generator)
    provider.provide(RepoA)
    provider.provide(RepoB)
    provider.provide(Service)
    container = dishka.make_async_container(provider)

    for _ in range(100):
        async with container() as ctx:
            await ctx.get(Service)

    start = time.perf_counter()
    for _ in range(iterations):
        async with container() as ctx:
            await ctx.get(Service)
    duration = time.perf_counter() - start
    return BenchmarkReport(name="dishka", duration=timedelta(seconds=duration))


async def bench_aioinject(iterations: int) -> BenchmarkReport:
    container = aioinject.Container()
    container.register(aioinject.Scoped(make_session))
    container.register(aioinject.Scoped(RepoA))
    container.register(aioinject.Scoped(RepoB))
    container.register(aioinject.Scoped(Service))

    for _ in range(100):
        async with container.context() as ctx:
            await ctx.resolve(Service)

    start = time.perf_counter()
    for _ in range(iterations):
        async with container.context() as ctx:
            await ctx.resolve(Service)
    duration = time.perf_counter() - start
    return BenchmarkReport(
        name="aioinject", duration=timedelta(seconds=duration)
    )


async def bench_rodi(iterations: int) -> BenchmarkReport:
    container = rodi.Container()
    container.add_scoped(Session)
    container.add_scoped(RepoA)
    container.add_scoped(RepoB)
    container.add_scoped(Service)

    for _ in range(100):
        container.resolve(Service)

    start = time.perf_counter()
    for _ in range(iterations):
        container.resolve(Service)
    duration = time.perf_counter() - start
    return BenchmarkReport(name="rodi", duration=timedelta(seconds=duration))


async def bench_dependency_injector(iterations: int) -> BenchmarkReport:
    class Container(dependency_injector.containers.DeclarativeContainer):
        session = dependency_injector.providers.Factory(Session)
        repository_a = dependency_injector.providers.Factory(
            RepoA, session=session
        )
        repository_b = dependency_injector.providers.Factory(
            RepoB, session=session
        )
        service = dependency_injector.providers.Factory(
            Service, a=repository_a, b=repository_b
        )

    container = Container()

    for _ in range(100):
        container.service()

    start = time.perf_counter()
    for _ in range(iterations):
        container.service()

    duration = time.perf_counter() - start
    return BenchmarkReport(
        name="dependency-injector", duration=timedelta(seconds=duration)
    )


async def main() -> None:
    benchmarks = [
        bench_aioinject,
        bench_dishka,
        bench_rodi,
        bench_dependency_injector,
        bench_python,
    ]
    for iterations in [100_000]:
        print(f"Iterations: {iterations}")  # noqa: T201
        for bench in benchmarks:
            result = await bench(iterations=iterations)
            print(  # noqa: T201
                f"{result.name}: {result.duration.total_seconds() * 1000:.4f}ms"
            )


if __name__ == "__main__":
    asyncio.run(main())
