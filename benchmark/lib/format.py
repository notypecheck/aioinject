from __future__ import annotations

from collections.abc import Sequence

from benchmark.lib.bench import BenchmarkResult, ProjectUrl


def time_to_microsecond(delta: float) -> str:
    return f"{delta * 1_000_000:.3f}μs"


def time_to_ms(delta: float) -> str:
    return f"{delta * 1_000:.3f}ms"


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
        print(row_template.format(*get_result_columns(result)))  # noqa: T201


def get_result_columns(result: BenchmarkResult) -> tuple[str, ...]:
    total = time_to_ms(result.total)
    if result.extrapolated:
        total = (
            f"{time_to_ms(result.mean * result.params.rounds)} (extrapolated)"
        )
    return (
        result.name,
        str(result.rounds),
        total,
        time_to_microsecond(result.mean),
        time_to_microsecond(result.median),
    )


def print_markdown_table(results: Sequence[BenchmarkResult]) -> None:
    for result in results:
        project_url = next(
            (e for e in result.benchmark.extras if isinstance(e, ProjectUrl)),
            None,
        )
        if project_url is None:
            continue

        result.name = f"[{result.name}]({project_url.url})"

    header = ("Name", "iterations", "total", "mean", "median")
    rows = [header, *(get_result_columns(result) for result in results)]
    cell_sizes = []
    for i in range(len(rows[0])):
        max_length = max(len(row[i]) for row in rows)
        cell_sizes.append(max_length)
    row_template = " | ".join(f"{{:{cell_size}}}" for cell_size in cell_sizes)
    row_template = f"| {row_template} |"

    formatted_header = row_template.format(*rows[0])
    print(formatted_header)  # noqa: T201
    underline = "|".join("-" * (cell_size + 2) for cell_size in cell_sizes)
    underline = f"|{underline}|"
    print(underline)  # noqa: T201
    for row in rows[1:]:
        print(row_template.format(*row))  # noqa: T201
