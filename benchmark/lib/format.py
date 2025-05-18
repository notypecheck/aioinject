from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from benchmark.lib.bench import BenchmarkResult


def time_to_microsecond(delta: float) -> str:
    return f"{delta * 1_000_000:.3f}μs"


def time_to_ms(delta: float) -> str:
    return f"{delta * 1_000:.3f}ms"


def format_result(result: BenchmarkResult, row_template: str) -> str:
    total = time_to_ms(result.total)
    if result.extrapolated:
        total = (
            f"{time_to_ms(result.mean * result.params.rounds)} (extrapolated)"
        )

    return row_template.format(
        result.name,
        str(result.rounds),
        total,
        time_to_microsecond(result.mean),
        time_to_microsecond(result.median),
    )


def print_results(results: Sequence[BenchmarkResult]) -> None:
    row_template = "{:25} {:10} {:10} {:10} {:10}"
    print(  # noqa: T201
        row_template.format(
            "Name",
            "iterations",
            "total",
            "mean",
            "median",
            # "p95",
            # "p99",
        ),
    )
    for result in results:
        print(format_result(result, row_template))  # noqa: T201
