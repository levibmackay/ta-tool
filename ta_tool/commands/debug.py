from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax

from ..core.config import load_config
from ..core.file_utils import load_text
from ..core.llm import call_llm
from ..core.parser import check_syntax, parse_json_response

console = Console()

_SYSTEM = (
    "You are a university TA reviewing student code. "
    "You MUST NOT rewrite their code or provide a corrected implementation. "
    "Identify bugs, explain WHY each is a problem in plain English, and give directional hints only. "
    "Respond with valid JSON only."
)

_PROMPT = """\
Student's Python code ({filename}):
```python
{code}
```
{syntax_note}

Review this code as a teaching TA:
- Identify up to 3 of the most impactful bugs or logical errors
- For each: describe what it is, where it is (line / function), why it causes a problem, and give a directional hint
- Do NOT provide corrected code or a full rewrite
- Keep hints educational — guide the student to figure it out

Respond with ONLY valid JSON:
{{
  "bugs": [
    {{
      "location": "e.g. line 14 in bubble_sort()",
      "issue": "Plain-English description of the problem",
      "why_it_matters": "What breaks at runtime or why the logic is wrong",
      "hint": "A directional nudge — no solution code"
    }}
  ],
  "general_advice": "One or two sentences of overall feedback on the code"
}}
"""


def run(code_file: Path, json_output: bool, verbose: bool) -> None:
    cfg = load_config()
    source = load_text(code_file)

    ok, syntax_err = check_syntax(source)
    syntax_note = (
        f"\nNote: the file has a syntax error that must be fixed first: {syntax_err}\n"
        if not ok
        else ""
    )

    prompt = _PROMPT.format(
        filename=code_file.name,
        code=source,
        syntax_note=syntax_note,
    )
    raw = call_llm(prompt, mode="debug", system_prompt=_SYSTEM, cfg=cfg, verbose=verbose)

    try:
        data = parse_json_response(raw)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if json_output:
        typer.echo(json.dumps(data, indent=2))
        return

    _render(source, data, code_file.name, ok, syntax_err)


def _render(
    source: str,
    data: dict,
    filename: str,
    syntax_ok: bool,
    syntax_err: str | None,
) -> None:
    console.print()
    console.print(Panel(f"[bold cyan]Debug Analysis — {filename}[/bold cyan]", expand=False))

    if not syntax_ok:
        console.print(f"\n  [bold red]Syntax Error:[/bold red] {syntax_err}")
        console.print("  [dim]Fix the syntax error before running — analysis below may be incomplete.[/dim]")

    # Source listing
    console.print()
    console.print(Rule("[bold]Source Code[/bold]"))
    console.print(Syntax(source, "python", line_numbers=True, theme="monokai"))

    # Bug list
    bugs = data.get("bugs", [])
    console.print()
    if not bugs:
        console.print(Rule("[bold green]No bugs detected[/bold green]"))
    else:
        console.print(Rule(f"[bold red]Bugs Found — {len(bugs)}[/bold red]"))
        for i, bug in enumerate(bugs, 1):
            console.print(
                f"\n  [bold red]Bug {i}[/bold red]  [dim]@[/dim] "
                f"[yellow]{bug.get('location', 'unknown location')}[/yellow]"
            )
            console.print(f"  [bold]Issue:[/bold]          {bug.get('issue', '')}")
            console.print(f"  [bold]Why it matters:[/bold] {bug.get('why_it_matters', '')}")
            console.print(f"  [bold green]Hint:[/bold green]           {bug.get('hint', '')}")

    # General advice
    if advice := data.get("general_advice"):
        console.print()
        console.print(Rule("[bold]General Advice[/bold]"))
        console.print(f"\n  [dim]{advice}[/dim]")

    console.print()
