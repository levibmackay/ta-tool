from __future__ import annotations

import json
import statistics
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

console = Console()

_TOTAL_COLUMN_CANDIDATES = ["total", "score", "grade", "final", "Total", "Score", "Grade", "Final"]
_HISTOGRAM_BINS = 10
_BAR_WIDTH = 30


def run(grades_file: Path, json_output: bool, verbose: bool) -> None:
    try:
        import pandas as pd
    except ImportError:
        console.print("[red]pandas is required. Run: pip install pandas[/red]")
        raise typer.Exit(1)

    df = pd.read_csv(grades_file)
    numeric_cols = df.select_dtypes(include="number").columns.tolist()

    if not numeric_cols:
        console.print("[red]No numeric columns found in the CSV.[/red]")
        raise typer.Exit(1)

    total_col = next(
        (c for c in _TOTAL_COLUMN_CANDIDATES if c in numeric_cols),
        numeric_cols[-1],
    )
    scores = df[total_col].dropna().tolist()

    if verbose:
        console.print(f"[dim]Total column: {total_col!r}  |  Rows: {len(scores)}[/dim]")

    if len(scores) < 2:
        console.print("[red]Need at least 2 data points.[/red]")
        raise typer.Exit(1)

    overall = _compute(scores)
    question_cols = [c for c in numeric_cols if c != total_col]
    per_question = {col: _compute(df[col].dropna().tolist()) for col in question_cols}
    histogram = _histogram(scores)
    cluster = _cluster_insight(scores)

    result = {
        "total_column": total_col,
        "overall": overall,
        "per_question": per_question,
        "histogram": histogram,
        "clustering_insight": cluster,
    }

    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    _render(result)


# ── Computation helpers ────────────────────────────────────────────────────────

def _compute(values: list[float]) -> dict:
    if not values:
        return {}
    return {
        "count": len(values),
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
    }


def _histogram(scores: list[float], bins: int = _HISTOGRAM_BINS) -> list[dict]:
    lo, hi = min(scores), max(scores)
    if lo == hi:
        return [{"range": f"{lo:.0f}", "count": len(scores)}]

    width = (hi - lo) / bins
    buckets = []
    for i in range(bins):
        low = lo + i * width
        high = lo + (i + 1) * width
        count = sum(
            1 for s in scores
            if low <= s < high or (i == bins - 1 and s == high)
        )
        buckets.append({"range": f"{low:.0f}–{high:.0f}", "count": count})
    return buckets


def _cluster_insight(scores: list[float]) -> str:
    mean = statistics.mean(scores)
    stdev = statistics.stdev(scores)
    lo, hi = round(mean - stdev, 1), round(mean + stdev, 1)
    pct = round(100 * sum(1 for s in scores if lo <= s <= hi) / len(scores))
    return f"~{pct}% of students scored between {lo} and {hi}  (mean ± 1σ)"


# ── Rendering ─────────────────────────────────────────────────────────────────

def _render(data: dict) -> None:
    overall = data["overall"]
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Grade Statistics[/bold cyan]  —  column: [bold]{data['total_column']}[/bold]",
            expand=False,
        )
    )

    # Summary table
    summary_table = Table(show_header=True, header_style="bold magenta", show_lines=False)
    summary_table.add_column("Metric", style="bold", width=12)
    summary_table.add_column("Value", justify="right", width=10)
    for metric in ("count", "mean", "median", "min", "max", "stdev"):
        summary_table.add_row(metric.capitalize(), str(overall.get(metric, "—")))
    console.print(summary_table)

    # Histogram
    console.print()
    console.print(Rule("[bold]Score Distribution[/bold]"))
    max_count = max((b["count"] for b in data["histogram"]), default=1) or 1
    for bucket in data["histogram"]:
        bar_len = int(bucket["count"] / max_count * _BAR_WIDTH)
        bar = "█" * bar_len
        console.print(f"  {bucket['range']:>10}  {bar:<{_BAR_WIDTH}} {bucket['count']}")

    console.print()
    console.print(f"  [dim]{data['clustering_insight']}[/dim]")

    # Per-question hardest
    if data["per_question"]:
        console.print()
        console.print(Rule("[bold]Per-Question Breakdown  (sorted by avg score, hardest first)[/bold]"))

        q_table = Table(show_header=True, header_style="bold magenta")
        q_table.add_column("Question", style="bold")
        q_table.add_column("Mean", justify="right")
        q_table.add_column("Median", justify="right")
        q_table.add_column("Min", justify="right")
        q_table.add_column("Stdev", justify="right")

        sorted_qs = sorted(data["per_question"].items(), key=lambda kv: kv[1].get("mean", 0))
        for col, s in sorted_qs:
            q_table.add_row(col, str(s["mean"]), str(s["median"]), str(s["min"]), str(s["stdev"]))

        console.print(q_table)

        hardest = sorted_qs[0][0] if sorted_qs else "—"
        console.print(f"\n  [yellow]Hardest question (lowest avg): [bold]{hardest}[/bold][/yellow]")

    console.print()
