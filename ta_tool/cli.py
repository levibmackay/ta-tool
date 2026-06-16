from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .commands import debug, office, reply, rubric, stats, triage

app = typer.Typer(
    name="ta",
    help=(
        "TA Toolkit — CLI tools for Teaching Assistants.\n\n"
        "All commands accept [bold]--json[/bold] for machine-readable output "
        "and [bold]--verbose[/bold] for LLM diagnostics."
    ),
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command("build-rubric")
def build_rubric(
    assignment_file: Path = typer.Argument(
        ..., help="Path to the assignment description (.md or .txt)", exists=True
    ),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON instead of formatted table"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show LLM call details"),
) -> None:
    """Generate a structured grading rubric from an assignment description."""
    rubric.run(assignment_file, json_output=json_output, verbose=verbose)


@app.command("reply")
def reply_cmd(
    question: str = typer.Argument(..., help="The student's question (quote it)"),
    socratic: bool = typer.Option(
        False, "--socratic", help="Only ask guiding questions — do not provide any answers"
    ),
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Draft a TA reply to a student question from Canvas or email."""
    reply.run(question, socratic=socratic, json_output=json_output, verbose=verbose)


@app.command("triage")
def triage_cmd(
    submission_folder: Path = typer.Argument(
        ..., help="Folder containing student submissions (flat .py files or per-student subdirs)"
    ),
    required_functions: Optional[list[str]] = typer.Option(
        None,
        "--require-fn",
        help="Function name that must exist (repeat flag for multiple, e.g. --require-fn foo --require-fn bar)",
    ),
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Check all submissions for completeness, syntax errors, and missing required functions."""
    triage.run(
        submission_folder,
        required_functions=required_functions,
        json_output=json_output,
        verbose=verbose,
    )


@app.command("office-prep")
def office_prep(
    assignment_file: Path = typer.Argument(
        ..., help="Path to the assignment description", exists=True
    ),
    weaknesses: Optional[Path] = typer.Option(
        None,
        "--weaknesses",
        help="Text file listing known student weak areas from previous cohorts",
    ),
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Prepare explanations, confusion points, and a cheat sheet for office hours."""
    office.run(assignment_file, weaknesses_file=weaknesses, json_output=json_output, verbose=verbose)


@app.command("stats")
def stats_cmd(
    grades_file: Path = typer.Argument(
        ..., help="CSV file with student grades (needs a numeric total/score column)", exists=True
    ),
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Compute grade statistics and show distribution from a grades CSV."""
    stats.run(grades_file, json_output=json_output, verbose=verbose)


@app.command("debug")
def debug_cmd(
    code_file: Path = typer.Argument(
        ..., help="Path to the student's Python source file", exists=True
    ),
    json_output: bool = typer.Option(False, "--json"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Identify bugs in student code with teaching hints — does NOT rewrite the solution."""
    debug.run(code_file, json_output=json_output, verbose=verbose)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app()
