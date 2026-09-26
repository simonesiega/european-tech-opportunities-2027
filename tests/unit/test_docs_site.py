"""Offline checks for the safe MkDocs projection and its rendered-link guard."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts import build_docs, check_built_docs


def test_github_alerts_render_as_material_admonitions_without_changing_other_text() -> None:
    source = (
        "# Guide\n\n> [!IMPORTANT]\n> Authorization is required.\n\n"
        "Other > text and [!NOTE] in a paragraph remain unchanged.\n"
    )
    assert build_docs._render_alerts(source) == (
        "# Guide\n\n!!! important\n    Authorization is required.\n\n"
        "Other > text and [!NOTE] in a paragraph remain unchanged.\n"
    )


def test_rendered_link_check_detects_missing_images_and_anchors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Importing the script does not read production state; override its output root.
    monkeypatch.setattr(check_built_docs, "ROOT", tmp_path)
    (tmp_path / "CNAME").write_text("docs.techopportunities.eu\n", encoding="utf-8")
    icon = tmp_path / check_built_docs.STAGED_ICON
    icon.parent.mkdir(parents=True)
    icon.write_bytes(check_built_docs.SITE_ICON.read_bytes())
    (tmp_path / "index.html").write_text(
        '<a href="other.html#missing">guide</a><img src="docs/missing.webp">',
        encoding="utf-8",
    )
    (tmp_path / "other.html").write_text('<h1 id="existing">Guide</h1>', encoding="utf-8")
    assert check_built_docs.main() == 1

    (tmp_path / "index.html").write_text(
        '<a href="other.html#existing">guide</a><img src="docs/image.webp">',
        encoding="utf-8",
    )
    (tmp_path / "docs" / "image.webp").write_bytes(b"image")
    assert check_built_docs.main() == 0

    icon.write_text("not the website icon", encoding="utf-8")
    assert check_built_docs.main() == 1
    icon.write_bytes(check_built_docs.SITE_ICON.read_bytes())

    (tmp_path / ".env").write_text("private", encoding="utf-8")
    assert check_built_docs.main() == 1
