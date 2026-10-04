"""Offline checks for the safe MkDocs projection and its rendered-link guard."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from scripts.docs import build_docs, check_built_docs


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


@pytest.mark.parametrize(
    ("asset", "approved"),
    [
        ("docs/assets/promo/soundtrack.mp3", True),
        ("docs/assets/soundtrack.mp3", False),
        ("docs/assets/promo/other.mp3", False),
        ("docs/assets/promo/soundtrack.MP3", False),
        ("docs/assets/promo/.work/soundtrack.mp3", False),
    ],
)
def test_rendered_soundtrack_links_and_exact_publication_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    asset: str,
    approved: bool,
) -> None:
    monkeypatch.setattr(check_built_docs, "ROOT", tmp_path)
    (tmp_path / "CNAME").write_text("docs.techopportunities.eu\n", encoding="utf-8")
    icon = tmp_path / check_built_docs.STAGED_ICON
    icon.parent.mkdir(parents=True)
    icon.write_bytes(check_built_docs.SITE_ICON.read_bytes())
    soundtrack = tmp_path / asset
    soundtrack.parent.mkdir(parents=True, exist_ok=True)
    soundtrack.write_bytes(b"synthetic audio")
    (tmp_path / "index.html").write_text(
        f'<a href="{asset}">Original soundtrack</a>', encoding="utf-8"
    )

    assert check_built_docs.main() == (0 if approved else 1)
    if not approved:
        assert f"Unexpected published file: {asset}" in capsys.readouterr().err
        return

    soundtrack.unlink()
    assert check_built_docs.main() == 1
    assert f"missing {asset}" in capsys.readouterr().err


def test_legacy_redirects_require_a_real_canonical_destination(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="redirect target is missing"):
        build_docs._write_legacy_redirects(tmp_path)
    for destination in build_docs.LEGACY_PAGES.values():
        path = tmp_path / "docs" / f"{destination}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<h1>Canonical guide</h1>", encoding="utf-8")
    build_docs._write_legacy_redirects(tmp_path)
    for legacy, destination in build_docs.LEGACY_PAGES.items():
        source = tmp_path / "docs" / f"{legacy}.html"
        redirect = source.read_text(encoding="utf-8")
        link = re.search(r'<a href="([^"]+)">', redirect)
        assert link is not None
        relative = link.group(1)
        assert (source.parent / relative).resolve() == (
            tmp_path / "docs" / f"{destination}.html"
        ).resolve()
        assert f'http-equiv="refresh" content="0; url={relative}"' in redirect
        assert f'rel="canonical" href="{relative}"' in redirect


def test_legacy_redirects_point_directly_to_current_topic_guides() -> None:
    docs = build_docs.ROOT / "docs"
    guides = {
        path.relative_to(docs).with_suffix("").as_posix()
        for audience in ("maintainers", "users")
        for path in (docs / audience).rglob("*.md")
        if path.name != "README.md"
    }
    destinations = set(build_docs.LEGACY_PAGES.values())
    assert destinations <= guides
    assert set(build_docs.LEGACY_PAGES).isdisjoint(guides)
    for guide in destinations:
        audience, _topic, name = guide.split("/")
        assert build_docs.LEGACY_PAGES[f"{audience}/{name}"] == guide
    assert build_docs.LEGACY_PAGES["guides/development/architecture"] == (
        "maintainers/engineering/architecture"
    )
    assert build_docs.LEGACY_PAGES["guides/user-guide/public-dataset"] == "users/data/data"


@pytest.mark.parametrize(
    "asset", ["diagram.svg", "tour.mp4", "poster.webp", "promo/soundtrack.mp3"]
)
def test_public_staging_publishes_media_but_not_private_root_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, asset: str
) -> None:
    import subprocess

    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    monkeypatch.setattr(build_docs, "LEGACY_PAGES", {})
    icon = tmp_path / "site-icon.svg"
    icon.write_bytes(b"<svg/>")
    monkeypatch.setattr(build_docs, "SITE_ICON", icon)
    source = tmp_path / "docs/assets" / asset
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic media")
    (tmp_path / ".env").write_text("private sentinel", encoding="utf-8")
    for filename in build_docs.PUBLIC_ROOT_FILES:
        (tmp_path / filename).write_text("# Public\n", encoding="utf-8")
    built = tmp_path / "build/docs-site"
    built.mkdir(parents=True)

    def build(command: list[str], *, cwd: Path, env: dict[str, str]) -> int:
        assert "--strict" in command
        assert cwd == tmp_path
        staged = Path(env["DOCS_BUILD_DIR"])
        assert (staged / "docs/assets" / asset).read_bytes() == b"synthetic media"
        assert (staged / "AGENTS.md").is_file()
        assert not (staged / ".env").exists()
        assert (staged / build_docs.STAGED_ICON).read_bytes() == icon.read_bytes()
        return 0

    monkeypatch.setattr(subprocess, "call", build)
    assert build_docs.main() == 0
    assert (built / "CNAME").read_text(encoding="utf-8") == "docs.techopportunities.eu\n"


@pytest.mark.parametrize(
    "private_file",
    [
        "assets/private.db",
        "assets/.env",
        "maintainers/private.mp4",
        "assets/soundtrack.mp3",
        "assets/promo/other.mp3",
        "assets/promo/soundtrack.MP3",
        "assets/promo/.work/soundtrack.mp3",
        "assets/promo/scripts/render.mjs",
        "assets/promo/index.html",
        "assets/promo/bun.lock",
    ],
)
def test_public_staging_rejects_unapproved_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, private_file: str
) -> None:
    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    source = tmp_path / "docs" / private_file
    source.parent.mkdir(parents=True)
    source.write_bytes(b"must not publish")
    with pytest.raises(ValueError, match="Unexpected documentation file"):
        build_docs.main()


@pytest.mark.parametrize("asset", ["image.webp", "promo/soundtrack.mp3"])
def test_public_staging_rejects_symlinked_media(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, asset: str
) -> None:
    monkeypatch.setattr(build_docs, "ROOT", tmp_path)
    private = tmp_path / "private"
    private.write_text("private", encoding="utf-8")
    alias = tmp_path / "docs/assets" / asset
    alias.parent.mkdir(parents=True)
    try:
        alias.symlink_to(private)
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")
    with pytest.raises(ValueError, match="symlinks are not allowed"):
        build_docs.main()
