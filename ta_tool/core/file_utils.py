from __future__ import annotations

from pathlib import Path


def load_text(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return p.read_text(encoding="utf-8")


def find_python_files(path: Path) -> list[Path]:
    """Return all .py files under path (or path itself if it is a .py file)."""
    if path.is_dir():
        return sorted(path.rglob("*.py"))
    if path.suffix == ".py" and path.is_file():
        return [path]
    return []


def iter_submission_entries(folder: str | Path) -> list[Path]:
    """
    Return one entry per student submission.
    - If the folder contains subdirectories, each subdir is one submission.
    - Otherwise, treat each .py file in the folder as a flat submission.
    """
    root = Path(folder)
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")

    subdirs = [d for d in sorted(root.iterdir()) if d.is_dir()]
    if subdirs:
        return subdirs

    py_files = sorted(root.glob("*.py"))
    return py_files
