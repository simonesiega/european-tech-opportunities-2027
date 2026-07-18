from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from internships.config.rules import ClassificationRules, load_classification_rules
from internships.config.settings import Settings
from internships.database.migrations import upgrade_database
from internships.database.session import create_database_engine, create_session_factory
from internships.models.search import LinkedInSearchConfig
from internships.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))


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
        name="Test European internships",
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
