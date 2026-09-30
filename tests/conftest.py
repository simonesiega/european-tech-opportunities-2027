from __future__ import annotations

import os
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.rules import ClassificationRules, load_classification_rules
from opportunities.config.settings import Settings
from opportunities.database.migrations import upgrade_database
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.models.search import LinkedInSearchConfig
from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))


def live_tests_enabled(mark_expression: str, environment: Mapping[str, str]) -> bool:
    """Require the documented explicit selection and both authorization interlocks."""
    return (
        mark_expression.strip() == "live"
        and environment.get("OPPORTUNITIES_LIVE_TESTS") == "1"
        and environment.get("OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED") == "true"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not live_tests_enabled(config.option.markexpr, os.environ):
        skip = pytest.mark.skip(
            reason="live tests require -m live, OPPORTUNITIES_LIVE_TESTS=1, and source permission"
        )
        for item in items:
            if item.get_closest_marker("live") is not None:
                item.add_marker(skip)


@pytest.fixture(autouse=True)
def isolated_test_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """Keep normal tests away from operator settings, home files, and real HTTP."""
    if request.node.get_closest_marker("live") is not None:
        return  # Collection has already enforced the three explicit live-test gates.
    for name in tuple(os.environ):
        if name.startswith(("OPPORTUNITIES_", "CANONICAL_STATE_", "VPS_", "RELEASE_")) or name in {
            "GITHUB_RUN_ID",
            "GITHUB_RUN_ATTEMPT",
            "SSH_AUTH_SOCK",
            "SSH_AGENT_PID",
        }:
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    # pytest.fail cannot be swallowed by application code catching Exception and
    # treating a network mistake as an expected provider failure.
    def reject_http(_transport: httpx.HTTPTransport, _request: httpx.Request) -> httpx.Response:
        pytest.fail("real HTTP is disabled in offline tests; inject a mock transport")

    async def reject_async_http(
        _transport: httpx.AsyncHTTPTransport, _request: httpx.Request
    ) -> httpx.Response:
        pytest.fail("real HTTP is disabled in offline tests; inject a mock transport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", reject_http)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject_async_http)


@pytest.fixture
def fixture_html() -> Callable[[str], str]:
    def load(name: str) -> str:
        return (ROOT / "tests" / "fixtures" / name).read_text(encoding="utf-8")

    return load


@pytest.fixture
def rules() -> ClassificationRules:
    return load_classification_rules(ROOT / "configs" / "categories.yml")


@pytest.fixture
def search() -> LinkedInSearchConfig:
    return LinkedInSearchConfig(
        name="Test European opportunities",
        slug="test-search",
        keywords="software engineer intern 2027",
        location="Europe",
        geo_id="91000000",
        max_pages=1,
        max_results=25,
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'opportunities.db').as_posix()}",
        search_config_dir=ROOT / "configs" / "searches",
        category_config_path=ROOT / "configs" / "categories.yml",
        readme_path=tmp_path / "README.md",
        public_export_dir=tmp_path / "exports",
        rate_limit_seconds=0,
        retry_backoff_seconds=0,
        linkedin_crawl_authorized=True,
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    upgrade_database(settings.database_url, repository_root=ROOT)
    database_engine = create_database_engine(settings.database_url)
    yield database_engine
    database_engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return create_session_factory(engine)
