from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from opportunities.config.search_registry import SearchRegistryError, load_search_registry
from opportunities.config.settings import apply_search_overrides, load_settings
from opportunities.models.enums import InternshipCategory
from opportunities.models.search import LinkedInSearchConfig
from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))


def test_production_search_registry_is_bounded_and_scope_specific() -> None:
    search_root = ROOT / "configs" / "searches"
    searches = load_search_registry(search_root)
    assert len(searches) == 69
    assert {path.parent.name for path in search_root.rglob("*.yml")} == {
        "roles",
        "companies",
        "countries",
    }
    role_names = {path.stem for path in (search_root / "roles").glob("*.yml")}
    category_names = {category.value for category in InternshipCategory}
    assert role_names <= category_names
    assert all(search.enabled for search in searches)
    for search in searches:
        assert "2027" in search.keywords
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
        "INTERNSHIPS_RATE_LIMIT_SECONDS=4\nINTERNSHIPS_SEARCH_MAX_PAGES=2\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INTERNSHIPS_RATE_LIMIT_SECONDS", "1")
    settings = load_settings()
    assert settings.rate_limit_seconds == 1
    assert settings.search_max_pages == 2


def test_trailing_environment_whitespace_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED", "true ")
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
