import dependency_injector.containers
import dependency_injector.providers
import di
import di.executors
import dishka
import lagom
import punq  # type: ignore[import-untyped]
import rodi
import wireup
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
)
from benchmark.lib.bench import (
    BenchmarkCollection,
    BenchmarkContext,
    ProjectUrl,
)


COMMON_DEPENDENCIES = [
    Session,
    RepositoryA,
    RepositoryB,
    ServiceA,
    ServiceB,
    UseCase,
]

simple_benchmarks = BenchmarkCollection()


@simple_benchmarks.bench(name="aioinject")
async def benchmark_aioinject(context: BenchmarkContext) -> None:
    container = aioinject.SyncContainer()
    container.register(*(Scoped(svc) for svc in COMMON_DEPENDENCIES))

    with container.context() as ctx:
        ctx.resolve(UseCase)

    for _ in range(context.rounds):
        with context.round(), container.context() as ctx:
            ctx.resolve(UseCase)


@simple_benchmarks.bench(
    name="dishka",
    extras=(ProjectUrl("https://github.com/reagento/dishka"),),
)
async def benchmark_dishka(context: BenchmarkContext) -> None:
    provider = dishka.Provider(scope=dishka.Scope.REQUEST)
    for svc in COMMON_DEPENDENCIES:
        provider.provide(svc)

    container = dishka.make_container(provider)

    with container() as ctx:
        ctx.get(UseCase)

    for _ in range(context.rounds):
        with context.round(), container() as ctx:
            ctx.get(UseCase)


@simple_benchmarks.bench(name="python")
async def bench_python(context: BenchmarkContext) -> None:
    for _ in range(context.rounds):
        with context.round():
            session = Session()
            repo_a = RepositoryA(session=session)
            repo_b = RepositoryB(session=session)
            svc_a = ServiceA(repository=repo_a)
            svc_b = ServiceB(repository=repo_b)
            UseCase(service_a=svc_a, service_b=svc_b)


@simple_benchmarks.bench(
    name="rodi", extras=(ProjectUrl("https://github.com/Neoteroi/rodi"),)
)
async def benchmark_rodi(context: BenchmarkContext) -> None:
    container = rodi.Container()
    for svc in COMMON_DEPENDENCIES:
        container.add_scoped(svc)

    container.resolve(UseCase)

    for _ in range(context.rounds):
        with context.round():
            container.resolve(UseCase)


@simple_benchmarks.bench(
    name="adriangb/di", extras=(ProjectUrl("https://github.com/adriangb/di"),)
)
async def benchmark_di(context: BenchmarkContext) -> None:
    container = di.Container()
    solved = container.solve(
        Dependent(UseCase, scope="request"), scopes=["request"]
    )

    executor = di.executors.SyncExecutor()
    with container.enter_scope("request") as state:
        solved.execute_sync(executor=executor, state=state)

    for _ in range(context.rounds):
        with context.round(), container.enter_scope("request") as state:
            solved.execute_sync(executor=executor, state=state)


@simple_benchmarks.bench(
    name="dependency-injector",
    extras=(
        ProjectUrl("https://github.com/ets-labs/python-dependency-injector"),
    ),
)
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


@simple_benchmarks.bench(
    name="punq",
    max_iterations=5_000,
    extras=(ProjectUrl("https://github.com/bobthemighty/punq"),),
)
async def benchmark_punq(context: BenchmarkContext) -> None:
    container = punq.Container()
    for svc in COMMON_DEPENDENCIES:
        container.register(svc)
    container.resolve(UseCase)

    for _ in range(context.rounds):
        with context.round():
            container.resolve(UseCase)


@simple_benchmarks.bench(
    name="lagom", extras=(ProjectUrl("https://github.com/meadsteve/lagom"),)
)
async def benchmark_lagom(context: BenchmarkContext) -> None:
    container = lagom.Container()

    for _ in range(context.rounds):
        with context.round():
            container[UseCase]


@simple_benchmarks.bench(
    name="wireup", extras=(ProjectUrl("https://github.com/maldoinc/wireup"),)
)
async def benchmark_wireup(context: BenchmarkContext) -> None:
    container = wireup.create_sync_container(
        services=[
            wireup.service(svc, lifetime="scoped")
            for svc in COMMON_DEPENDENCIES
        ]
    )
    for _ in range(context.rounds):
        with context.round(), container.enter_scope() as ctx:
            ctx.get(UseCase)
