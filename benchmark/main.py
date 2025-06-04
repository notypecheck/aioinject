import asyncio

from benchmark.benchmarks.context import context_benchmarks
from benchmark.benchmarks.simple import simple_benchmarks
from benchmark.lib.bench import Benchmark
from benchmark.lib.format import print_markdown_table


async def main() -> None:
    for collection in (simple_benchmarks, context_benchmarks):
        bench = Benchmark(
            benchmarks=collection.benchmarks,
        )
        results = await bench.run(rounds=[100_000])
        results = sorted(results, key=lambda result: result.mean)
        print_markdown_table(results)


if __name__ == "__main__":
    asyncio.run(main())
