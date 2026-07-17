"""Validate local Markdown links, image paths, and heading anchors."""

from __future__ import annotations

import re
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = (
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    *sorted((ROOT / "docs").rglob("*.md")),
)
_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^) >]+)")
_IMAGE_RE = re.compile(r'<img[^>]+src="([^"]+)"')
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def _heading_anchor(heading: str) -> str:
    """Approximate GitHub's stable anchor for project documentation headings."""
    without_html = re.sub(r"<[^>]+>", "", heading).strip().casefold()
    words = re.sub(r"[^\w\- ]", "", without_html).replace(" ", "-")
    return re.sub(r"-+", "-", words)


def _local_target(source: Path, target: str) -> tuple[Path, str | None] | None:
    """Resolve a local Markdown target and optional heading anchor."""
    cleaned = target.strip("<>")
    if cleaned.startswith(_EXTERNAL_PREFIXES):
        return None
    path_text, separator, anchor = cleaned.partition("#")
    path = source if not path_text else (source.parent / urllib.parse.unquote(path_text)).resolve()
    return path, anchor if separator else None


def main() -> int:
    """Return nonzero when local documentation references are broken."""
    anchors = {
        path.resolve(): {
            _heading_anchor(heading)
            for heading in _HEADING_RE.findall(path.read_text(encoding="utf-8"))
        }
        for path in MARKDOWN_FILES
    }
    errors: list[str] = []

    for source in MARKDOWN_FILES:
        text = source.read_text(encoding="utf-8")
        for target in (*_LINK_RE.findall(text), *_IMAGE_RE.findall(text)):
            resolved = _local_target(source, target)
            if resolved is None:
                continue
            path, anchor = resolved
            if not path.exists():
                errors.append(f"{source.relative_to(ROOT)}: missing {target}")
                continue
            if anchor and path in anchors and anchor not in anchors[path]:
                errors.append(f"{source.relative_to(ROOT)}: missing heading #{anchor} in {target}")

    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    sys.stdout.write(f"Documentation links valid across {len(MARKDOWN_FILES)} Markdown files.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
