"""Filesystem discovery helpers."""

from __future__ import annotations

from pathlib import Path

_PROJECT_MARKERS = ("pyproject.toml", "alembic.ini", "migrations")


def find_project_root(start: Path) -> Path:
    """Find find project root."""
    resolved = start.resolve()
    directory = resolved if resolved.is_dir() else resolved.parent
    for candidate in (directory, *directory.parents):
        if all((candidate / marker).exists() for marker in _PROJECT_MARKERS):
            return candidate
    markers = ", ".join(_PROJECT_MARKERS)
    raise RuntimeError(f"could not find project root containing: {markers}")
