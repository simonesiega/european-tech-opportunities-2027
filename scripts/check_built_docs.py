"""Verify local links, images, and anchors in the rendered MkDocs website."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1] / "build" / "docs-site"


def main() -> int:
    """Reject broken rendered references, including raw HTML image sources."""
    errors: list[str] = []
    pages = sorted(ROOT.rglob("*.html"))
    if not pages:
        sys.stderr.write("No built documentation pages found. Run scripts/build_docs.py first.\n")
        return 1

    for page in pages:
        soup = BeautifulSoup(page.read_text(encoding="utf-8"), "html.parser")
        for tag, attribute in (("a", "href"), ("img", "src"), ("script", "src"), ("link", "href")):
            for element in soup.find_all(tag):
                value = element.get(attribute)
                if not isinstance(value, str) or not value:
                    continue
                url = urlsplit(value)
                if url.scheme or url.netloc:
                    continue
                if url.path.startswith("/european-tech-opportunities-2027/"):
                    relative_path = url.path.removeprefix("/european-tech-opportunities-2027/")
                    target = ROOT / unquote(relative_path)
                elif url.path.startswith("/"):
                    target = ROOT / unquote(url.path.lstrip("/"))
                else:
                    target = (page.parent / unquote(url.path)).resolve() if url.path else page
                if url.path.endswith("/"):
                    target /= "index.html"
                if not target.is_relative_to(ROOT.resolve()) or not target.exists():
                    errors.append(f"{page.relative_to(ROOT)}: missing {value}")
                elif url.fragment and target.suffix == ".html":
                    target_soup = (
                        soup
                        if target == page
                        else BeautifulSoup(target.read_text(encoding="utf-8"), "html.parser")
                    )
                    if target_soup.find(id=unquote(url.fragment)) is None:
                        errors.append(f"{page.relative_to(ROOT)}: missing anchor {value}")

    if errors:
        sys.stderr.write("\n".join(errors) + "\n")
        return 1
    sys.stdout.write(f"Rendered links and anchors valid across {len(pages)} HTML pages.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
