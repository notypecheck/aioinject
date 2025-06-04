import di
import di.executors
import dishka
import wireup
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
from benchmark.lib.bench import (
    BenchmarkCollection,
    BenchmarkContext,
    ProjectUrl,
)


COMMON_DEPENDENCIES = [
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    UseCase,
]


context_benchmarks = BenchmarkCollection()


@context_benchmarks.bench(name="aioinject")
async def benchmark_aioinject(context: BenchmarkContext) -> None:
    container = aioinject.Container()
    container.register(Scoped(create_session_cm))
    container.register(*(Scoped(svc) for svc in COMMON_DEPENDENCIES))

    async with container.context() as ctx:
        await ctx.resolve(UseCase)

    for _ in range(context.rounds):
        with context.round():
            async with container.context() as ctx:
                await ctx.resolve(UseCase)


@context_benchmarks.bench(
    name="dishka", extras=(ProjectUrl("https://github.com/reagento/dishka"),)
)
async def benchmark_dishka(context: BenchmarkContext) -> None:
    provider = dishka.Provider(scope=dishka.Scope.REQUEST)
    provider.provide(create_session)
    for svc in COMMON_DEPENDENCIES:
        provider.provide(svc)

    container = dishka.make_async_container(provider)

    async with container() as ctx:
        await ctx.get(UseCase)

    for _ in range(context.rounds):
        with context.round():
            async with container() as ctx:
                await ctx.get(UseCase)


@context_benchmarks.bench(name="python")
async def bench_python(context: BenchmarkContext) -> None:
    for _ in range(context.rounds):
        with context.round():
            async with create_session_cm() as session:
                repo_a = RepositoryA(session=session)
                repo_b = RepositoryB(session=session)
                svc_a = ServiceA(repository=repo_a)
                svc_b = ServiceB(repository=repo_b)
                UseCase(service_a=svc_a, service_b=svc_b)


@context_benchmarks.bench(
    name="adriangb/di", extras=(ProjectUrl("https://github.com/adriangb/di"),)
)
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


@context_benchmarks.bench(
    name="wireup", extras=(ProjectUrl("https://github.com/maldoinc/wireup"),)
)
async def benchmark_wireup(context: BenchmarkContext) -> None:
    container = wireup.create_async_container(
        services=[
            wireup.service(create_session, lifetime="scoped"),
            *(
                wireup.service(svc, lifetime="scoped")
                for svc in COMMON_DEPENDENCIES
            ),
        ]
    )
    for _ in range(context.rounds):
        with context.round():
            async with container.enter_scope() as ctx:
                await ctx.get(UseCase)
