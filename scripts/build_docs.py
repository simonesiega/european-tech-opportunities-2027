"""Build the public documentation from an explicit allowlist of repository files.

Keep the repository-relative Markdown paths intact so GitHub and MkDocs resolve the
same links. Never point MkDocs at the repository root (which contains private state).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "PRIVACY.md",
    "CODE_OF_CONDUCT.md",
    "lychee.toml",
    "LICENSE",
)


def main() -> int:
    """Stage only public content and run MkDocs in strict mode."""
    with tempfile.TemporaryDirectory(prefix="opportunities-docs-") as directory:
        staging = Path(directory)
        for source in (ROOT / "docs").rglob("*"):
            if source.is_symlink():
                raise ValueError(f"Documentation symlinks are not allowed: {source}")
            if source.is_file():
                if source.suffix.lower() not in {".md", ".webp"}:
                    raise ValueError(f"Unexpected documentation file: {source}")
                destination = staging / source.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
        for filename in PUBLIC_ROOT_FILES:
            source = ROOT / filename
            if source.is_symlink():
                raise ValueError(f"Public document symlinks are not allowed: {source}")
            shutil.copyfile(source, staging / filename)
        # MkDocs does not rewrite links inside raw HTML; keep GitHub source untouched.
        readme = staging / "README.md"
        text = readme.read_text(encoding="utf-8")
        for html_source, html_destination in (
            ('href="docs/README.md"', 'href="docs/index.html"'),
            ('href="CONTRIBUTING.md"', 'href="CONTRIBUTING.html"'),
            ('href="PRIVACY.md"', 'href="PRIVACY.html"'),
        ):
            text = text.replace(html_source, html_destination)
        readme.write_text(text, encoding="utf-8")
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
            (ROOT / "build" / "docs-site" / "CNAME").write_text(
                "docs.techopportunities.eu\n", encoding="utf-8"
            )
        return result


if __name__ == "__main__":
    raise SystemExit(main())
