from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..core.config import load_config
from ..core.file_utils import load_text
from ..core.llm import call_llm
from ..core.parser import parse_json_response

console = Console()

_SYSTEM = (
    "You are an expert educator coaching a university TA before office hours. "
    "Be concise and practical. Respond with valid JSON only."
)

_PROMPT = """\
Assignment Description:
{assignment}

{weaknesses_block}

Prepare me for office hours by generating:

1. Top 5 explanations I should have ready — each with a topic name, a clear explanation, and a concrete example
2. Common confusion points students typically have about this assignment — each with the misconception and how to clarify it
3. A mini cheat sheet: 3-5 key concepts with a 1-2 sentence summary each

Respond with ONLY valid JSON:
{{
  "top_explanations": [
    {{"topic": "...", "explanation": "...", "example": "..."}}
  ],
  "confusion_points": [
    {{"confusion": "...", "clarification": "..."}}
  ],
  "cheat_sheet": [
    {{"concept": "...", "summary": "..."}}
  ]
}}
"""


def run(
    assignment_file: Path,
    weaknesses_file: Optional[Path],
    json_output: bool,
    verbose: bool,
) -> None:
    cfg = load_config()
    assignment = load_text(assignment_file)

    weaknesses_block = ""
    if weaknesses_file:
        content = load_text(weaknesses_file)
        weaknesses_block = f"Known student weak areas from previous classes:\n{content}\n"

    prompt = _PROMPT.format(assignment=assignment, weaknesses_block=weaknesses_block)
    raw = call_llm(prompt, mode="office", system_prompt=_SYSTEM, cfg=cfg, verbose=verbose)

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
    console.print(Panel("[bold cyan]Office Hours Preparation Guide[/bold cyan]", expand=False))

    # ── Top explanations ──────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Top 5 Explanations to Have Ready[/bold]"))
    for i, item in enumerate(data.get("top_explanations", [])[:5], 1):
        console.print(f"\n  [bold yellow]{i}. {item.get('topic', '')}[/bold yellow]")
        console.print(f"     {item.get('explanation', '')}")
        if example := item.get("example"):
            console.print(f"     [dim]Example: {example}[/dim]")

    # ── Confusion points ──────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Common Confusion Points[/bold]"))
    for item in data.get("confusion_points", []):
        console.print(f"\n  [red]✗ Students often think:[/red] {item.get('confusion', '')}")
        console.print(f"  [green]✓ Clarify by saying:[/green]  {item.get('clarification', '')}")

    # ── Cheat sheet ───────────────────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold]Quick-Reference Cheat Sheet[/bold]"))
    for item in data.get("cheat_sheet", []):
        console.print(f"\n  [bold cyan]{item.get('concept', '')}[/bold cyan]")
        console.print(f"  {item.get('summary', '')}")

    console.print()
