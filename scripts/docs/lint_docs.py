"""Run the pinned, offline documentation linters on maintained Markdown only."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROOT_FILES = (
    ".github/WORKFLOWS.md",
    ".github/pull_request_template.md",
    "scripts/SCRIPT.md",
    "tests/TEST.md",
    "AGENTS.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "PRIVACY.md",
    "README.md",
    "SECURITY.md",
    "docs/README.md",
    "docs/assets/README.md",
    "docs/assets/promo/maintainers/VIDEO.md",
)
MARKDOWNLINT = (
    "davidanson/markdownlint-cli2:v0.23.3@"
    "sha256:d5f3f3f04b2e285dcbcdcd13b4454d119e273e3c393a9dabd163dba4abad526d"
)
VALE = "jdkato/vale:v3.13.0@sha256:04bb8794dff4505bcf588522e860ba9547b73f02dd8b2de0faecb155472da672"


def maintained_markdown() -> list[str]:
    """Scan authored docs, not generated output or third-party assets."""
    files = set(ROOT_FILES)
    for path in (ROOT / "docs").rglob("*.md"):
        relative = path.relative_to(ROOT)
        if relative.parts[1] in {"generated", "vendor"}:
            continue
        if relative.parts[1] == "assets" and not (
            relative.as_posix() == "docs/assets/README.md"
            or path.is_relative_to(ROOT / "docs" / "assets" / "diagram")
        ):
            continue
        files.add(relative.as_posix())
    files.update(
        path.relative_to(ROOT).as_posix() for path in (ROOT / ".github/ISSUE_TEMPLATE").glob("*.md")
    )
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tool", nargs="?", choices=("markdownlint", "vale"))
    args = parser.parse_args()
    if shutil.which("docker") is None:
        parser.error("Docker is required to run the pinned documentation linters")

    files = maintained_markdown()
    for file in files:
        if not (ROOT / file).is_file():
            parser.error(f"Maintained documentation file is missing: {file}")

    common = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--mount",
        f"type=bind,source={ROOT},target=/workdir,readonly",
        "--workdir",
        "/workdir",
    ]
    commands = {
        "markdownlint": [*common, MARKDOWNLINT, *files],
        "vale": [*common, VALE, "--no-global", "--output=line", *files],
    }
    for name in (args.tool,) if args.tool else commands:
        sys.stdout.write(f"Running {name} on {len(files)} maintained Markdown files\n")
        sys.stdout.flush()
        result = subprocess.run(commands[name], cwd=ROOT, check=False)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
