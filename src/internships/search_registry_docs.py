"""Rendering and validation helpers for search-registry documentation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_LAYOUT_PATTERN = re.compile(
    r"```text\n"
    r"configs/searches/\n"
    r"├── roles/\s*# \d+ technology paths\n"
    r"├── companies/\s*# \d+ targeted employers\n"
    r"└── countries/\s*# \d+ country partitions\n"
    r"```"
)


@dataclass(frozen=True, slots=True)
class SearchRegistryLayout:
    """Hold generated counts for each registry group."""

    roles: int
    companies: int
    countries: int


def search_registry_layout(search_config_dir: Path) -> SearchRegistryLayout:
    """Count searches in each registry group."""
    return SearchRegistryLayout(
        roles=_count_yaml_files(search_config_dir / "roles"),
        companies=_count_yaml_files(search_config_dir / "companies"),
        countries=_count_yaml_files(search_config_dir / "countries"),
    )


def render_search_registry_docs(path: Path, search_config_dir: Path) -> None:
    """Refresh documented registry counts from the YAML layout."""
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    rendered = _render_layout_block(content, search_registry_layout(search_config_dir))
    path.write_text(rendered, encoding="utf-8", newline="\n")


def validate_search_registry_docs(path: Path, search_config_dir: Path) -> list[str]:
    """Validate documented registry counts against YAML files."""
    if not path.is_file():
        return []
    content = path.read_text(encoding="utf-8")
    matches = _LAYOUT_PATTERN.findall(content)
    if len(matches) != 1:
        return ["Search registry docs must contain exactly one generated layout block"]
    expected = _layout_block(search_registry_layout(search_config_dir))
    if matches[0] != expected:
        return ["Search registry layout counts do not match configs/searches"]
    return []


def _count_yaml_files(path: Path) -> int:
    """Count YAML files directly inside a registry group."""
    if not path.is_dir():
        return 0
    return sum(
        1
        for item in path.iterdir()
        if item.is_file() and item.suffix.casefold() in {".yml", ".yaml"}
    )


def _render_layout_block(content: str, layout: SearchRegistryLayout) -> str:
    """Replace the registry layout block with generated counts."""
    matches = _LAYOUT_PATTERN.findall(content)
    if len(matches) != 1:
        raise ValueError("search registry docs must contain exactly one generated layout block")
    return _LAYOUT_PATTERN.sub(_layout_block(layout), content, count=1)


def _layout_block(layout: SearchRegistryLayout) -> str:
    """Build the registry layout documentation block."""
    return (
        "```text\n"
        "configs/searches/\n"
        f"├── roles/       # {layout.roles} technology paths\n"
        f"├── companies/   # {layout.companies} targeted employers\n"
        f"└── countries/   # {layout.countries} country partitions\n"
        "```"
    )
