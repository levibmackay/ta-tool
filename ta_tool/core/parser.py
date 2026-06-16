from __future__ import annotations

import ast
import json
from typing import Optional


def check_syntax(source: str) -> tuple[bool, Optional[str]]:
    """Return (is_valid, error_message). error_message is None on success."""
    try:
        ast.parse(source)
        return True, None
    except SyntaxError as exc:
        return False, f"Line {exc.lineno}: {exc.msg}"


def extract_function_names(source: str) -> list[str]:
    """Return all top-level and nested function names defined in source."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def extract_class_names(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def strip_llm_fences(raw: str) -> str:
    """Remove markdown code fences that LLMs sometimes wrap JSON in."""
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    # drop opening fence (``` or ```json etc.) and closing fence if present
    start = 1
    end = -1 if lines[-1].strip() == "```" else len(lines)
    return "\n".join(lines[start:end]).strip()


def parse_json_response(raw: str) -> dict:
    """Strip fences and parse JSON, raising ValueError with context on failure."""
    cleaned = strip_llm_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        preview = cleaned[:200].replace("\n", " ")
        raise ValueError(
            f"LLM did not return valid JSON: {exc}\nPreview: {preview}"
        ) from exc
