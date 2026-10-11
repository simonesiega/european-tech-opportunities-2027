"""Build the public documentation from an explicit allowlist of repository files.

Keep the repository-relative Markdown paths intact so GitHub and MkDocs resolve the
same links. Never point MkDocs at the repository root (which contains private state).
"""

from __future__ import annotations

import html
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE_ICON = ROOT / "site" / "src" / "app" / "icon.svg"
STAGED_ICON = Path("docs/assets/site-icon.svg")
# GitHub alert syntax is not understood by Python-Markdown. Convert only staged
# copies so the same source remains readable as an alert on GitHub.
_ALERT_RE = re.compile(r"^> \[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\](?:\n>.*)*", re.MULTILINE)

PUBLIC_ROOT_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "SECURITY.md",
    "PRIVACY.md",
    "CODE_OF_CONDUCT.md",
    "lychee.toml",
    "LICENSE",
)


def _render_alerts(text: str) -> str:
    """Translate GitHub alerts to Material admonitions without changing source files."""

    def replace(match: re.Match[str]) -> str:
        lines = match.group().splitlines()
        body = "\n".join("    " + line.removeprefix("> ") for line in lines[1:])
        return f"!!! {match.group(1).lower()}\n{body}"

    return _ALERT_RE.sub(replace, text)


# Paths are relative to docs/, without extensions. Preserve both former guide layouts
# with direct redirects to current topics, not duplicate Markdown or redirect chains.
LEGACY_PAGES = {
    "guides/getting-started/installation": "maintainers/getting-started/setup",
    "guides/getting-started/configuration": "maintainers/getting-started/configuration",
    "guides/development/architecture": "maintainers/engineering/architecture",
    "guides/development/development": "maintainers/engineering/testing",
    "guides/operations/automation": "maintainers/operations/automation",
    "guides/operations/database": "maintainers/operations/database",
    "guides/operations/docker": "maintainers/operations/deployment",
    "guides/operations/troubleshooting": "maintainers/operations/troubleshooting",
    "guides/user-guide/cli": "maintainers/operations/cli",
    "guides/user-guide/search-registry": "maintainers/engineering/search-registry",
    "guides/user-guide/website": "users/browsing/directory",
    "guides/user-guide/public-dataset": "users/data/data",
    "maintainers/setup": "maintainers/getting-started/setup",
    "maintainers/configuration": "maintainers/getting-started/configuration",
    "maintainers/architecture": "maintainers/engineering/architecture",
    "maintainers/classification": "maintainers/engineering/classification",
    "maintainers/search-registry": "maintainers/engineering/search-registry",
    "maintainers/website": "maintainers/engineering/website",
    "maintainers/testing": "maintainers/engineering/testing",
    "maintainers/documentation": "maintainers/engineering/documentation",
    "maintainers/cli": "maintainers/operations/cli",
    "maintainers/automation": "maintainers/operations/automation",
    "maintainers/database": "maintainers/operations/database",
    "maintainers/deployment": "maintainers/operations/deployment",
    "maintainers/troubleshooting": "maintainers/operations/troubleshooting",
    "users/directory": "users/browsing/directory",
    "users/lists": "users/browsing/lists",
    "users/help": "users/browsing/help",
    "users/data": "users/data/data",
    "users/api": "users/data/api",
}


def _write_legacy_redirects(output: Path) -> None:
    for old, new in LEGACY_PAGES.items():
        source = output / "docs" / f"{old}.html"
        target = output / "docs" / f"{new}.html"
        if not target.is_file():
            raise ValueError(f"Documentation redirect target is missing: {new}")
        relative = html.escape(posixpath.relpath(target.as_posix(), source.parent.as_posix()))
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta http-equiv="refresh" content="0; url={relative}">'
            f'<link rel="canonical" href="{relative}"><title>Guide moved</title></head>'
            f'<body><p>This guide moved. <a href="{relative}">Continue to the guide</a>.</p>'
            "</body></html>\n",
            encoding="utf-8",
        )


def main() -> int:
    """Stage only public content and run MkDocs in strict mode."""
    with tempfile.TemporaryDirectory(prefix="opportunities-docs-") as directory:
        staging = Path(directory)
        for source in (ROOT / "docs").rglob("*"):
            if source.is_symlink():
                raise ValueError(f"Documentation symlinks are not allowed: {source}")
            if source.is_file():
                if source.suffix.lower() != ".md" and not (
                    source.is_relative_to(ROOT / "docs" / "assets")
                    and source.suffix.lower() in {".webp", ".svg", ".mp4"}
                ):
                    raise ValueError(f"Unexpected documentation file: {source}")
                destination = staging / source.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.suffix.lower() == ".md":
                    destination.write_text(
                        _render_alerts(source.read_text(encoding="utf-8")), encoding="utf-8"
                    )
                else:
                    shutil.copyfile(source, destination)
        if SITE_ICON.is_symlink() or not SITE_ICON.is_file():
            raise ValueError(f"Website icon is missing or a symlink: {SITE_ICON}")
        shutil.copyfile(SITE_ICON, staging / STAGED_ICON)
        for filename in PUBLIC_ROOT_FILES:
            source = ROOT / filename
            if source.is_symlink():
                raise ValueError(f"Public document symlinks are not allowed: {source}")
            destination = staging / filename
            if source.suffix == ".md":
                destination.write_text(
                    _render_alerts(source.read_text(encoding="utf-8")), encoding="utf-8"
                )
            else:
                shutil.copyfile(source, destination)
        env = {**os.environ, "DOCS_BUILD_DIR": str(staging), "PYTHONIOENCODING": "utf-8"}
        result = subprocess.call(
            [
                sys.executable,
                "-m",
                "mkdocs",
                "build",
                "--strict",
                "--config-file",
                str(ROOT / "mkdocs.yml"),
            ],
            cwd=ROOT,
            env=env,
        )
        if result == 0:
            _write_legacy_redirects(ROOT / "build" / "docs-site")
            (ROOT / "build" / "docs-site" / "CNAME").write_text(
                "docs.techopportunities.eu\n", encoding="utf-8"
            )
        return result


if __name__ == "__main__":
    raise SystemExit(main())
