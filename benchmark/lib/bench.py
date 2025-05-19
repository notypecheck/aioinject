import contextlib
import dataclasses
import statistics
import time
from collections.abc import Awaitable, Callable, Iterator, Sequence
from typing import Final


BenchmarkedFunction = Callable[["BenchmarkContext"], Awaitable[None]]


class BenchmarkEntry:
    def __init__(
        self,
        func: BenchmarkedFunction,
        name: str,
        max_iterations: int | None,
    ) -> None:
        self.func = func
        self.name = name
        self.max_iterations = max_iterations

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


def bench(
    name: str,
    max_iterations: int | None = None,
) -> Callable[[BenchmarkedFunction], BenchmarkEntry]:
    def inner(func: BenchmarkedFunction) -> BenchmarkEntry:
        return BenchmarkEntry(func, name=name, max_iterations=max_iterations)

    return inner


class BenchmarkContext:
    def __init__(self, rounds: int) -> None:
        self.durations: list[float] = []
        self.rounds: Final = rounds

    @contextlib.contextmanager
    def round(self) -> Iterator[None]:
        start = time.perf_counter()
        yield
        elapsed = time.perf_counter() - start
        self.durations.append(elapsed)


@dataclasses.dataclass
class BenchmarkParameters:
    rounds: int


@dataclasses.dataclass
class BenchmarkResult:
    params: BenchmarkParameters

    name: str
    rounds: int
    mean: float
    median: float
    total: float

    extrapolated: bool


class Benchmark:
    def __init__(
        self,
        benchmarks: list[BenchmarkEntry],
    ) -> None:
        self.benchmarks = benchmarks

    async def run(
        self,
        rounds: Sequence[int],
    ) -> Sequence[BenchmarkResult]:
        results = []
        for benchmark in self.benchmarks:
            for iterations in rounds:
                benchmark_results = [
                    await self.run_benchmark(benchmark, iterations)
                    for _ in range(5)
                ]
                best_result = min(benchmark_results, key=lambda r: r.total)
                results.append(best_result)

        return results

    async def run_benchmark(
        self, benchmark: BenchmarkEntry, rounds: int
    ) -> BenchmarkResult:
        extrapolated = (
            benchmark.max_iterations < rounds
            if benchmark.max_iterations
            else False
        )
        actual_rounds = (
            min(benchmark.max_iterations, rounds)
            if extrapolated and benchmark.max_iterations
            else rounds
        )
        context = BenchmarkContext(rounds=actual_rounds)
        await benchmark.func(context)
        context.durations.sort()
        result = BenchmarkResult(
            params=BenchmarkParameters(rounds=rounds),
            name=benchmark.name,
            rounds=actual_rounds,
            mean=statistics.mean(context.durations),
            median=statistics.median(context.durations),
            total=sum(context.durations),
            extrapolated=extrapolated,
        )
        assert len(context.durations) == actual_rounds  # noqa: S101
        return result
