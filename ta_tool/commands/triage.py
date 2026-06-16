from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.file_utils import find_python_files, iter_submission_entries, load_text
from ..core.parser import check_syntax, extract_function_names

console = Console()

COMPLETE = "COMPLETE"
INCOMPLETE = "INCOMPLETE"
BROKEN = "BROKEN"

_STATUS_COLOR = {COMPLETE: "green", INCOMPLETE: "yellow", BROKEN: "red"}


@dataclass
class SubmissionResult:
    name: str
    status: str = ""
    python_files: list[str] = field(default_factory=list)
    syntax_errors: list[str] = field(default_factory=list)
    missing_functions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def run(
    submission_folder: Path,
    required_functions: Optional[list[str]],
    json_output: bool,
    verbose: bool,
) -> None:
    try:
        entries = iter_submission_entries(submission_folder)
    except NotADirectoryError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if not entries:
        console.print(f"[red]No submissions found in {submission_folder}[/red]")
        raise typer.Exit(1)

    required = required_functions or []
    results: list[SubmissionResult] = []

    for entry in entries:
        result = _check(entry, required)
        results.append(result)
        if verbose:
            color = _STATUS_COLOR.get(result.status, "white")
            console.print(f"  [{color}]{result.status}[/{color}]  {result.name}")

    summary = _summarise(results)

    if json_output:
        typer.echo(
            json.dumps(
                {"results": [asdict(r) for r in results], "summary": summary},
                indent=2,
            )
        )
        return

    _render(results, summary)


def _check(entry: Path, required_funcs: list[str]) -> SubmissionResult:
    py_files = find_python_files(entry)
    result = SubmissionResult(
        name=entry.name,
        python_files=[str(f) for f in py_files],
    )

    if not py_files:
        result.status = INCOMPLETE
        result.notes.append("No Python files found")
        return result

    syntax_errors: list[str] = []
    found_functions: set[str] = set()

    for py_file in py_files:
        try:
            source = load_text(py_file)
        except OSError as exc:
            syntax_errors.append(f"{py_file.name}: unreadable ({exc})")
            continue

        ok, err = check_syntax(source)
        if not ok:
            syntax_errors.append(f"{py_file.name}: {err}")
        else:
            found_functions.update(extract_function_names(source))

    result.syntax_errors = syntax_errors

    missing = [fn for fn in required_funcs if fn not in found_functions]
    result.missing_functions = missing

    if syntax_errors:
        result.status = BROKEN
    elif missing:
        result.status = INCOMPLETE
        result.notes.append(f"Missing: {', '.join(missing)}")
    else:
        result.status = COMPLETE

    return result


def _summarise(results: list[SubmissionResult]) -> dict:
    counts = {COMPLETE: 0, INCOMPLETE: 0, BROKEN: 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    return {"total": len(results), **counts}


def _render(results: list[SubmissionResult], summary: dict) -> None:
    console.print()

    table = Table(
        title="Submission Triage",
        show_header=True,
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Student", style="bold", min_width=20)
    table.add_column("Status", width=12)
    table.add_column(".py", width=4, justify="right")
    table.add_column("Issues")

    for r in results:
        color = _STATUS_COLOR.get(r.status, "white")
        issues = "; ".join(r.syntax_errors + r.notes) or "—"
        table.add_row(
            r.name,
            f"[{color}]{r.status}[/{color}]",
            str(len(r.python_files)),
            issues,
        )

    console.print(table)
    console.print()
    console.print(
        Panel(
            f"[green]Complete: {summary[COMPLETE]}[/green]   "
            f"[yellow]Incomplete: {summary[INCOMPLETE]}[/yellow]   "
            f"[red]Broken: {summary[BROKEN]}[/red]   "
            f"[dim](total: {summary['total']})[/dim]",
            title="Summary",
            expand=False,
        )
    )
    console.print()
