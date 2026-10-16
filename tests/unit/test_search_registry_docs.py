from __future__ import annotations

from pathlib import Path

import yaml

from opportunities.config.search_registry import load_search_registry
from opportunities.models.search import LinkedInSearchConfig
from opportunities.search_registry_docs import (
    SearchRegistryLayout,
    render_search_registry_docs,
    search_registry_layout,
    validate_search_registry_docs,
)


def test_registry_layout_matches_recursive_loader(
    tmp_path: Path, search: LinkedInSearchConfig
) -> None:
    registry = tmp_path / "searches"
    for index, relative in enumerate(
        ("roles/software.yml", "roles/specialized/security.yaml", "companies/example.yml")
    ):
        path = registry / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        configured = search.model_copy(
            update={"slug": f"search-{index}", "keywords": f"software intern {index}"}
        )
        path.write_text(yaml.safe_dump(configured.model_dump(mode="json")), encoding="utf-8")
    for filename in ("notes.txt", "backup.yml.disabled"):
        (registry / "roles" / filename).write_text("not a search", encoding="utf-8")

    assert len(load_search_registry(registry)) == 3
    assert search_registry_layout(registry) == SearchRegistryLayout(
        roles=2, companies=1, countries=0
    )

    document = tmp_path / "search-registry.md"
    document.write_text(
        "# Registry\n\nAuthored introduction.\n\n```text\nconfigs/searches/\n"
        "├── roles/       # 0 technology paths\n"
        "├── companies/   # 0 targeted employers\n"
        "└── countries/   # 0 country partitions\n```\n\nAuthored conclusion.\n",
        encoding="utf-8",
    )
    assert validate_search_registry_docs(document, registry)
    render_search_registry_docs(document, registry)
    assert validate_search_registry_docs(document, registry) == []
    rendered = document.read_text(encoding="utf-8")
    assert rendered.startswith("# Registry\n\nAuthored introduction.\n")
    assert rendered.endswith("\nAuthored conclusion.\n")
    render_search_registry_docs(document, registry)
    assert document.read_text(encoding="utf-8") == rendered
