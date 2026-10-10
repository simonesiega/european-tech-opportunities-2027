"""Keep authored translations separate from their shared generated projections."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from bs4 import BeautifulSoup
from scripts.docs import check_docs, lint_docs

from opportunities.readme import (
    BEGIN_MARKER,
    END_MARKER,
    STATE_SEAL_PREFIX,
    SUMMARY_BEGIN_MARKER,
    SUMMARY_END_MARKER,
    validate_readme,
)

ROOT = Path(__file__).resolve().parents[2]
READMES = {
    "English": ROOT / "README.md",
    "Italiano": ROOT / "docs/translations/README.it.md",
    "Français": ROOT / "docs/translations/README.fr.md",
    "Deutsch": ROOT / "docs/translations/README.de.md",
    "Español": ROOT / "docs/translations/README.es.md",
    "简体中文": ROOT / "docs/translations/README.zh-CN.md",
}
LOCALIZED_READMES = tuple(path for language, path in READMES.items() if language != "English")
HEADINGS = re.compile(r"^(#{2,6}) (.+)$", re.MULTILINE)


@pytest.mark.parametrize("readme", READMES.values(), ids=READMES.keys())
def test_readme_language_navigation_and_section_hierarchy(readme: Path) -> None:
    text = readme.read_text(encoding="utf-8")
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    assert [level for level, _heading in HEADINGS.findall(text)] == [
        level for level, _heading in HEADINGS.findall(english)
    ]
    source = BeautifulSoup(text, "html.parser")
    titles = source.find_all("h1")
    assert len(titles) == 1
    assert titles[0].get_text() == "European Tech Opportunities 2027"
    selector = titles[0].find_next_sibling()
    assert selector is not None
    assert selector.name == "div"
    assert selector.get("align") == "center"
    assert selector.get("markdown") == "1"
    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", selector.get_text())
    assert len(links) == len(READMES)
    for (_label, target), expected in zip(links, READMES.values(), strict=True):
        assert (readme.parent / target).resolve() == expected


@pytest.mark.parametrize("readme", LOCALIZED_READMES, ids=lambda path: path.name)
def test_localized_readmes_share_canonical_data(
    readme: Path,
) -> None:
    text = readme.read_text(encoding="utf-8")
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    assert validate_readme(readme) == []
    for begin, end in (
        (BEGIN_MARKER, END_MARKER),
        (SUMMARY_BEGIN_MARKER, SUMMARY_END_MARKER),
    ):
        pattern = re.escape(begin) + ".*?" + re.escape(end)
        translated = re.search(pattern, text, re.DOTALL)
        canonical = re.search(pattern, english, re.DOTALL)
        assert translated is not None
        assert canonical is not None
        if begin == BEGIN_MARKER:

            def rows(block: str) -> list[str]:
                return [
                    line.rsplit(" | ", 1)[0]
                    for line in block.splitlines()
                    if "https://www.linkedin.com/jobs/view/" in line
                ]

            assert rows(translated.group()) == rows(canonical.group())
            urls = r"https://www.linkedin.com/jobs/view/\d+"
            assert re.findall(urls, translated.group()) == re.findall(urls, canonical.group())
        else:
            counts = r"https://img.shields.io/badge/[^\n\"]+?-(\d+)-[0-9a-f]{6}"
            assert re.findall(counts, translated.group()) == re.findall(counts, canonical.group())
    seal = re.escape(STATE_SEAL_PREFIX) + r"[0-9a-f]{64} -->"
    assert re.findall(seal, text) == re.findall(seal, english)


def test_readme_translations_participate_in_documentation_checks_and_navigation() -> None:
    readmes = set(READMES.values())
    assert readmes <= set(check_docs.MARKDOWN_FILES)
    assert readmes <= {ROOT / path for path in lint_docs.maintained_markdown()}
    configuration = yaml.load(
        (ROOT / "mkdocs.yml").read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )
    project = next(
        section["Project and policies"]
        for section in configuration["nav"]
        if "Project and policies" in section
    )
    languages = next(
        section["README languages"] for section in project if "README languages" in section
    )
    targets = {target for entry in languages for target in entry.values()}
    assert targets == {path.relative_to(ROOT).as_posix() for path in READMES.values()}
