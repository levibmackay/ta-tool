from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..core.config import load_config
from ..core.llm import call_llm
from ..core.parser import parse_json_response

console = Console()

_SYSTEM = (
    "You are a friendly, knowledgeable university TA. "
    "Your role is to guide students toward understanding — never hand them complete solutions or full code. "
    "Always respond with valid JSON only."
)

_PROMPT_STANDARD = """\
A student sent this question:
\"\"\"{question}\"\"\"

Generate two things:
1. A warm, clear TA response that helps the student understand the concept without giving away the answer.
   - Use encouraging language
   - Point to the right direction without writing their code for them
2. A short hint (1-2 sentences), even more indirect than the response.

Respond with ONLY valid JSON:
{{
  "response": "...",
  "hint": "..."
}}
"""

_PROMPT_SOCRATIC = """\
A student sent this question:
\"\"\"{question}\"\"\"

Reply ONLY with 3 to 5 Socratic guiding questions that lead the student to discover the answer themselves.
- Do NOT answer the question
- Do NOT embed the answer in a hint
- Questions should build on each other

Respond with ONLY valid JSON:
{{
  "questions": ["question 1", "question 2", "question 3"]
}}
"""


def run(question: str, socratic: bool, json_output: bool, verbose: bool) -> None:
    cfg = load_config()

    if socratic:
        prompt = _PROMPT_SOCRATIC.format(question=question)
        mode = "socratic"
    else:
        prompt = _PROMPT_STANDARD.format(question=question)
        mode = "reply"

    raw = call_llm(prompt, mode=mode, system_prompt=_SYSTEM, cfg=cfg, verbose=verbose)

    try:
        data = parse_json_response(raw)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if json_output:
        typer.echo(json.dumps(data, indent=2))
        return

    _render(question, data, socratic)


def _render(question: str, data: dict, socratic: bool) -> None:
    console.print()
    console.print(Rule("[bold]Student Question[/bold]"))
    console.print(f'  [italic dim]"{question}"[/italic dim]\n')

    if socratic:
        console.print(Panel("[bold cyan]Socratic Guiding Questions[/bold cyan]", expand=False))
        console.print()
        for i, q in enumerate(data.get("questions", []), 1):
            console.print(f"  [yellow bold]{i}.[/yellow bold] {q}")
    else:
        console.print(Panel("[bold cyan]Suggested TA Response[/bold cyan]", expand=False))
        console.print()
        console.print(f"  {data.get('response', '')}")
        console.print()
        console.print(Panel("[bold yellow]Hint Version[/bold yellow]", expand=False))
        console.print()
        console.print(f"  [dim]{data.get('hint', '')}[/dim]")

    console.print()
