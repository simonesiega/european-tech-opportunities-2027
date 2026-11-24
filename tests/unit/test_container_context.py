"""Protect directory-level exclusions for private container build inputs."""

from pathlib import Path


def test_container_context_excludes_operator_directories() -> None:
    patterns = {
        line.strip()
        for line in (Path(__file__).parents[2] / ".dockerignore")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    # Filename suffixes alone do not exclude manifests or prepared research batches.
    assert {"data", "state", "reports", "quality-reports", ".agents", ".context"} <= patterns
