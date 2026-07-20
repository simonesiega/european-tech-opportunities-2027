from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from opportunities.config.rules import load_classification_rules
from opportunities.config.search_registry import SearchRegistryError, load_search_registry
from opportunities.config.settings import Settings, apply_search_overrides, load_settings
from opportunities.models.enums import OpportunityCategory
from opportunities.models.search import LinkedInSearchConfig
from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))


def test_production_search_registry_is_bounded_and_scope_specific() -> None:
    search_root = ROOT / "configs" / "searches"
    searches = load_search_registry(search_root)
    assert len(searches) == 89
    assert {path.parent.name for path in search_root.rglob("*.yml")} == {
        "roles",
        "companies",
        "countries",
    }
    role_names = {path.stem for path in (search_root / "roles").glob("*.yml")}
    category_names = {category.value for category in OpportunityCategory}
    assert role_names <= category_names
    assert all(search.enabled for search in searches)
    for search in searches:
        # Discovery covers the complete cycle window. Explicit years are resolved
        # from detail pages, where conflicting 2025/2026 roles are rejected.
        assert "2027" not in search.keywords
        assert search.date_posted == "cycle"
        assert "intern" in search.keywords.casefold()
        assert "new grad" in search.keywords.casefold()
        assert "graduate" in search.keywords.casefold()
        assert 1 <= search.max_pages <= 4
        assert search.max_results == search.max_pages * 25
        assert 5 <= search.max_rechecks <= 25
        if search.location == "Europe":
            assert search.geo_id == "91000000"
        if search.slug.startswith("company-"):
            assert search.company_names
        if search.slug.startswith("country-"):
            assert search.location != "Europe"
            assert search.geo_id is None


def test_dotenv_loads_automatically_and_process_environment_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".env").write_text(
        "OPPORTUNITIES_RATE_LIMIT_SECONDS=4\nOPPORTUNITIES_SEARCH_MAX_PAGES=2\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPPORTUNITIES_RATE_LIMIT_SECONDS", "1")
    settings = load_settings()
    assert settings.rate_limit_seconds == 1
    assert settings.search_max_pages == 2


def test_trailing_environment_whitespace_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED", "true ")
    assert load_settings(dotenv_path=Path("missing.env")).linkedin_crawl_authorized is True


def test_global_search_limits_override_yaml_values(tmp_path: Path) -> None:
    (tmp_path / "search.yml").write_text(
        "name: Search\nslug: search\nkeywords: software intern 2027\n"
        "location: Europe\nmax_pages: 10\nmax_results: 250\n",
        encoding="utf-8",
    )
    searches = load_search_registry(tmp_path)
    settings = load_settings(dotenv_path=Path("missing.env")).model_copy(
        update={
            "search_max_pages": 2,
            "search_max_results": 50,
            "search_max_rechecks": 7,
        }
    )
    effective = apply_search_overrides(searches, settings)
    assert effective[0].max_pages == 2
    assert effective[0].max_results == 50
    assert effective[0].max_rechecks == 7


def test_invalid_search_and_duplicate_query_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        LinkedInSearchConfig(
            name="Bad",
            slug="Not Valid",
            keywords="software intern",
            location="Europe",
        )
    body = "name: Search {n}\nslug: search-{n}\nkeywords: same intern 2027\nlocation: Europe\n"
    for number in (1, 2):
        (tmp_path / f"{number}.yml").write_text(body.format(n=number), encoding="utf-8")
    with pytest.raises(SearchRegistryError, match="duplicate LinkedIn search"):
        load_search_registry(tmp_path)


def test_duplicate_query_identity_ignores_company_allowlist_order(tmp_path: Path) -> None:
    body = (
        "name: Search {number}\nslug: search-{number}\nkeywords: software intern\n"
        "location: Europe\ncompany_names:\n{companies}"
    )
    (tmp_path / "one.yml").write_text(
        body.format(number=1, companies="  - Example One\n  - Example Two\n"),
        encoding="utf-8",
    )
    (tmp_path / "two.yml").write_text(
        body.format(number=2, companies="  - Example Two\n  - Example One\n"),
        encoding="utf-8",
    )

    with pytest.raises(SearchRegistryError, match="duplicate LinkedIn search"):
        load_search_registry(tmp_path)


def test_settings_and_classification_yaml_fail_closed(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.yml"
    malformed.write_text("value: [unterminated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="could not read settings file"):
        load_settings(malformed, dotenv_path=tmp_path / "missing.env")
    with pytest.raises(ValueError, match="could not read classification rules"):
        load_classification_rules(malformed)

    invalid_rules = tmp_path / "rules.yml"
    invalid_rules.write_text(
        "schema_version: 2\ninternship_keywords: [intern]\n"
        "new_grad_keywords: [graduate]\nexcluded_role_keywords: [senior]\n"
        "categories:\n  software-engineering: not-a-list\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match="keyword configuration must be a list"):
        load_classification_rules(invalid_rules)


def test_settings_require_sqlite_and_safe_header_values() -> None:
    with pytest.raises(ValidationError, match="must use SQLite"):
        Settings(database_url="postgresql://user:password@example.com/opportunities")
    with pytest.raises(ValidationError, match="control characters"):
        Settings(user_agent="valid-user-agent-value\r\nInjected: true")
