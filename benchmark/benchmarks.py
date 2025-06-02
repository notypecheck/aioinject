import dependency_injector.containers
import dependency_injector.providers
import di
import di.executors
import dishka
import lagom
import punq  # type: ignore[import-untyped]
import rodi
from di import bind_by_type
from di.dependent import Dependent

import aioinject
from aioinject import Scoped
from benchmark.dependencies import (
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    Session,
    UseCase,
    create_session,
    create_session_cm,
)
from benchmark.lib.bench import BenchmarkContext, bench


@bench(name="aioinject")
async def benchmark_aioinject(context: BenchmarkContext) -> None:
    container = aioinject.Container()
    container.register(Scoped(create_session_cm))
    container.register(Scoped(RepositoryA))
    container.register(Scoped(RepositoryB))
    container.register(Scoped(ServiceA))
    container.register(Scoped(ServiceB))
    container.register(Scoped(UseCase))

    async with container.context() as ctx:
        await ctx.resolve(UseCase)

    for _ in range(context.rounds):
        with context.round():
            async with container.context() as ctx:
                await ctx.resolve(UseCase)


@bench(name="dishka")
async def benchmark_dishka(context: BenchmarkContext) -> None:
    provider = dishka.Provider(scope=dishka.Scope.REQUEST)
    provider.provide(create_session)
    provider.provide(RepositoryA)
    provider.provide(RepositoryB)
    provider.provide(ServiceA)
    provider.provide(ServiceB)
    provider.provide(UseCase)
    container = dishka.make_async_container(provider)

    async with container() as ctx:
        await ctx.get(UseCase)

    for _ in range(context.rounds):
        with context.round():
            async with container() as ctx:
                await ctx.get(UseCase)


@bench(name="python")
async def bench_python(context: BenchmarkContext) -> None:
    for _ in range(context.rounds):
        with context.round():
            async with create_session_cm() as session:
                repo_a = RepositoryA(session=session)
                repo_b = RepositoryB(session=session)
                svc_a = ServiceA(repository=repo_a)
                svc_b = ServiceB(repository=repo_b)
                UseCase(service_a=svc_a, service_b=svc_b)


@bench(name="rodi")
async def benchmark_rodi(context: BenchmarkContext) -> None:
    container = rodi.Container()
    container.add_scoped(Session)
    container.add_scoped(RepositoryA)
    container.add_scoped(RepositoryB)
    container.add_scoped(ServiceA)
    container.add_scoped(ServiceB)
    container.add_scoped(UseCase)

    container.resolve(UseCase)

    for _ in range(context.rounds):
        with context.round():
            container.resolve(UseCase)


@bench(name="adriangb/di")
async def benchmark_di(context: BenchmarkContext) -> None:
    container = di.Container()
    container.bind(
        bind_by_type(Dependent(create_session, scope="request"), Session)
    )
    solved = container.solve(
        Dependent(UseCase, scope="request"), scopes=["request"]
    )

    executor = di.executors.AsyncExecutor()
    async with container.enter_scope("request") as state:
        await solved.execute_async(executor=executor, state=state)

    for _ in range(context.rounds):
        with context.round():
            async with container.enter_scope("request") as state:
                await solved.execute_async(executor=executor, state=state)


@bench(name="dependency-injector")
async def benchmark_dependency_injector(context: BenchmarkContext) -> None:
    class Container(dependency_injector.containers.DeclarativeContainer):
        session = dependency_injector.providers.Factory(Session)
        repository_a = dependency_injector.providers.Factory(
            RepositoryA, session=session
        )
        repository_b = dependency_injector.providers.Factory(
            RepositoryB, session=session
        )
        service_a = dependency_injector.providers.Factory(
            ServiceA, repository=repository_a
        )
        service_b = dependency_injector.providers.Factory(
            ServiceB, repository=repository_b
        )
        use_case = dependency_injector.providers.Factory(
            UseCase, service_a=service_a, service_b=service_b
        )

    container = Container()

    container.use_case()

    for _ in range(context.rounds):
        with context.round():
            container.use_case()


@bench(name="punq", max_iterations=5_000)
async def benchmark_punq(context: BenchmarkContext) -> None:
    container = punq.Container()
    container.register(Session)
    container.register(RepositoryA)
    container.register(RepositoryB)
    container.register(ServiceA)
    container.register(ServiceB)
    container.register(UseCase)

    container.resolve(UseCase)

    for _ in range(context.rounds):
        with context.round():
            container.resolve(UseCase)


@bench(name="lagom")
async def benchmark_lagom(context: BenchmarkContext) -> None:
    # Note: not using lifetimes here with lagom

    container = lagom.Container()

    for _ in range(context.rounds):
        with context.round():
            container[UseCase]
