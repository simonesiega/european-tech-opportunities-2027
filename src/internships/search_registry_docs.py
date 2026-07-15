"""Rendering and validation helpers for search-registry documentation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SearchRegistryLayout:
    roles: int
    companies: int
    countries: int


def search_registry_layout(search_config_dir: Path) -> SearchRegistryLayout:
    return SearchRegistryLayout(
        roles=_count_yaml_files(search_config_dir / "roles"),
        companies=_count_yaml_files(search_config_dir / "companies"),
        countries=_count_yaml_files(search_config_dir / "countries"),
    )


def render_search_registry_docs(path: Path, search_config_dir: Path) -> None:
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    rendered = _render_layout_block(content, search_registry_layout(search_config_dir))
    path.write_text(rendered, encoding="utf-8", newline="\n")


def validate_search_registry_docs(path: Path, search_config_dir: Path) -> list[str]:
    if not path.is_file():
        return []
    content = path.read_text(encoding="utf-8")
    expected = _layout_block(search_registry_layout(search_config_dir))
    if expected not in content:
        return ["Search registry layout counts do not match configs/searches"]
    return []


def _count_yaml_files(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for item in path.iterdir() if item.is_file() and item.suffix in {".yml", ".yaml"})


def _render_layout_block(content: str, layout: SearchRegistryLayout) -> str:
    pattern = re.compile(
        r"```text\n"
        r"configs/searches/\n"
        r"├── roles/\s*# \d+ technology paths\n"
        r"├── companies/\s*# \d+ targeted employers\n"
        r"└── countries/\s*# \d+ country partitions\n"
        r"```"
    )
    rendered, replacements = pattern.subn(_layout_block(layout), content, count=1)
    if replacements > 1:
        raise ValueError("search registry docs must contain no more than one layout block")
    return rendered


def _layout_block(layout: SearchRegistryLayout) -> str:
    return (
        "```text\n"
        "configs/searches/\n"
        f"├── roles/       # {layout.roles} technology paths\n"
        f"├── companies/   # {layout.companies} targeted employers\n"
        f"└── countries/   # {layout.countries} country partitions\n"
        "```"
    )
