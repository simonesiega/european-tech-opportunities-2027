"""YAML registry for bounded LinkedIn job searches."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import yaml
from pydantic import ValidationError

from internships.models.search import LinkedInSearchConfig


class SearchRegistryError(ValueError):
    """A LinkedIn search file is missing, malformed, or duplicated."""


def load_search_file(path: Path) -> LinkedInSearchConfig:
    """Load and validate one search YAML file."""
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SearchRegistryError(f"could not read search {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SearchRegistryError(f"search {path} must contain a YAML mapping")
    try:
        return LinkedInSearchConfig.model_validate(payload)
    except ValidationError as exc:
        raise SearchRegistryError(f"invalid search {path}: {exc}") from exc


def load_search_registry(
    directory: Path, *, enabled_only: bool = False
) -> list[LinkedInSearchConfig]:
    """Load search files in stable order and reject duplicate query identities."""
    if not directory.is_dir():
        raise SearchRegistryError(f"search configuration directory does not exist: {directory}")
    paths = sorted((*directory.rglob("*.yml"), *directory.rglob("*.yaml")))
    searches = [load_search_file(path) for path in paths]
    duplicate_slugs = _duplicates(search.slug for search in searches)
    if duplicate_slugs:
        raise SearchRegistryError(f"duplicate search slugs: {', '.join(sorted(duplicate_slugs))}")
    identities = (
        "|".join(
            (
                search.keywords.casefold(),
                search.location.casefold(),
                search.geo_id or "",
                search.workplace,
                search.date_posted,
                ",".join(company.casefold() for company in search.company_names),
            )
        )
        for search in searches
    )
    duplicate_queries = _duplicates(identities)
    if duplicate_queries:
        raise SearchRegistryError("duplicate LinkedIn search queries are not allowed")
    selected = [search for search in searches if search.enabled] if enabled_only else searches
    return sorted(selected, key=lambda search: search.slug)


def select_searches(
    searches: Iterable[LinkedInSearchConfig], *, search_slug: str | None = None
) -> list[LinkedInSearchConfig]:
    """Select enabled LinkedIn searches by optional slug."""
    selected = [search for search in searches if search.enabled]
    if search_slug:
        selected = [search for search in selected if search.slug == search_slug.lower()]
    return sorted(selected, key=lambda search: search.slug)


def _duplicates(values: Iterable[str]) -> set[str]:
    """Return values that occur more than once."""
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates
