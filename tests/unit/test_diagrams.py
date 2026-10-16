from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIAGRAMS = ROOT / "docs" / "assets" / "diagram"
NAMES = ("repository", "collection", "website", "automation", "foundations")
SVG = "{http://www.w3.org/2000/svg}"
GITHUB = "https://github.com/simonesiega/european-tech-opportunities-2027/"


@pytest.mark.parametrize("name", NAMES)
def test_diagram_links_and_accessibility_match_source(name: str) -> None:
    blocks = re.findall(
        r"```mermaid\n(.*?)\n```", (DIAGRAMS / "source.md").read_text(encoding="utf-8"), re.S
    )
    assert len(blocks) == len(NAMES)
    source = blocks[NAMES.index(name)]
    mappings = dict(re.findall(r'click (\w+) "([^"]+)"', source))
    labels = dict(re.findall(r'^\s*(\w+)[\[({]+"([^"\n]+)"', source, re.M))
    root = ET.parse(DIAGRAMS / "svg" / f"{name}.svg").getroot()
    assert root.tag == f"{SVG}svg"
    assert root.attrib["role"] == "img"
    for tag, marker, attribute in (
        ("title", "accTitle:", "aria-labelledby"),
        ("desc", "accDescr:", "aria-describedby"),
    ):
        element = root.find(f"{SVG}{tag}")
        assert element is not None
        expected = next(
            line.split(marker, 1)[1].strip() for line in source.splitlines() if marker in line
        )
        assert element.text == expected
        assert root.attrib[attribute] == element.attrib["id"]

    nodes: dict[str, str] = {}
    for anchor in root.iter(f"{SVG}a"):
        assert anchor.find(f".//{SVG}a") is None
        node = anchor.find(f"{SVG}g")
        assert node is not None
        match = re.fullmatch(r"flowchart-(\w+)-\d+", node.attrib["id"])
        assert match is not None
        identifier = match.group(1)
        assert identifier not in nodes
        url = anchor.attrib["href"]
        nodes[identifier] = url
        assert anchor.attrib["tabindex"] == "0"
        assert anchor.attrib["target"] == "_blank"
        assert set(anchor.attrib["rel"].split()) >= {"noopener", "noreferrer"}
        assert anchor.attrib["aria-label"] == (
            labels[identifier].replace("<br/>", " ") + " — open source on GitHub"
        )
        assert url.startswith(GITHUB)
        kind, revision, relative = url.removeprefix(GITHUB).split("/", 2)
        assert kind in {"blob", "tree"}
        assert revision == "main"
        target = (ROOT / unquote(relative)).resolve()
        assert target.is_relative_to(ROOT)
        assert target.exists()
    assert nodes == mappings

    for element in root.iter():
        assert element.tag not in {f"{SVG}{tag}" for tag in ("script", "foreignObject", "image")}
        for attribute, value in element.attrib.items():
            assert not attribute.lower().startswith("on")
            if attribute.endswith("href") and element.tag != f"{SVG}a":
                assert value.startswith("#")
            assert not re.search(r"url\(\s*['\"]?(?:https?:|//|data:)", value, re.I)
    styles = "".join(element.text or "" for element in root.iter(f"{SVG}style"))
    assert "@import" not in styles.casefold()
    assert not re.search(r"url\(\s*['\"]?(?:https?:|//|data:)", styles, re.I)
