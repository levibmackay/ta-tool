from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.config import load_config
from ..core.file_utils import load_text
from ..core.llm import call_llm
from ..core.parser import parse_json_response

console = Console()

_SYSTEM = (
    "You are an experienced university grader designing rubrics. "
    "Always respond with valid JSON only — no prose, no markdown outside the JSON."
)

_PROMPT = """\
Assignment Description:
{assignment}

Design a detailed grading rubric for this assignment.

Rules:
- 4 to 6 grading categories (e.g. Correctness, Style, Efficiency, Completeness, Documentation, Testing)
- Total points must equal exactly 100
- For each category provide four performance levels: Excellent, Good, Okay, Poor
- Each level gets a point range and a concrete behavioural description

Respond with ONLY valid JSON using this exact structure:
{{
  "total_points": 100,
  "categories": [
    {{
      "name": "Category Name",
      "points": 30,
      "description": "One sentence describing what this category measures",
      "levels": {{
        "Excellent": {{"points_range": "28-30", "description": "..."}},
        "Good":      {{"points_range": "22-27", "description": "..."}},
        "Okay":      {{"points_range": "15-21", "description": "..."}},
        "Poor":      {{"points_range": "0-14",  "description": "..."}}
      }}
    }}
  ]
}}
"""

_LEVEL_ORDER = ["Excellent", "Good", "Okay", "Poor"]
_LEVEL_COLORS = {"Excellent": "green", "Good": "cyan", "Okay": "yellow", "Poor": "red"}


def run(assignment_file: Path, json_output: bool, verbose: bool) -> None:
    cfg = load_config()
    source = load_text(assignment_file)
    prompt = _PROMPT.format(assignment=source)
    raw = call_llm(prompt, mode="rubric", system_prompt=_SYSTEM, cfg=cfg, verbose=verbose)

    try:
        data = parse_json_response(raw)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if json_output:
        typer.echo(json.dumps(data, indent=2))
        return

    _render(data)


def _render(data: dict) -> None:
    console.print()
    console.print(
        Panel(
            f"[bold cyan]Grading Rubric[/bold cyan]   Total: {data.get('total_points', 100)} pts",
            expand=False,
        )
    )
    console.print()

    for cat in data.get("categories", []):
        table = Table(
            title=f"[bold]{cat['name']}[/bold]  ({cat['points']} pts)",
            show_header=True,
            header_style="bold magenta",
            show_lines=True,
            expand=False,
        )
        table.add_column("Level", width=12)
        table.add_column("Points", width=10, justify="center")
        table.add_column("Criteria", min_width=50)

        for level in _LEVEL_ORDER:
            info = cat.get("levels", {}).get(level, {})
            color = _LEVEL_COLORS.get(level, "white")
            table.add_row(
                f"[{color}]{level}[/{color}]",
                info.get("points_range", "—"),
                info.get("description", ""),
            )

        console.print(table)
        console.print(f"  [dim]{cat.get('description', '')}[/dim]\n")
