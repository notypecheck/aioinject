import asyncio

from benchmark.benchmarks import (
    bench_python,
    benchmark_aioinject,
    benchmark_dependency_injector,
    benchmark_di,
    benchmark_dishka,
    benchmark_lagom,
    benchmark_punq,
    benchmark_rodi,
)
from benchmark.lib.bench import Benchmark
from benchmark.lib.format import print_markdown_table, print_results


async def main() -> None:
    bench = Benchmark(
        benchmarks=[
            bench_python,
            benchmark_aioinject,
            benchmark_dishka,
            benchmark_rodi,
            benchmark_di,
            benchmark_dependency_injector,
            benchmark_punq,
            benchmark_lagom,
        ]
    )
    results = await bench.run(rounds=[100_000])
    print_results(results)
    print_markdown_table(results)


if __name__ == "__main__":
    asyncio.run(main())
