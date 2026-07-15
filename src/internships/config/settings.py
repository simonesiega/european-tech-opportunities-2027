"""Validated settings loaded from `.env`, YAML, and process environment."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from internships.models.search import LinkedInSearchConfig


DEFAULT_USER_AGENT = (
    "european-tech-internships-2027/0.1 "
    "(+https://github.com/simonesiega/european-tech-internships-2027)"
)


class Settings(BaseModel):
    """Define validated application settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    database_url: str = "sqlite:///data/internships.db"
    search_config_dir: Path = Path("configs/searches")
    category_config_path: Path = Path("configs/categories.yml")
    readme_path: Path = Path("README.md")
    target_cycle: int = Field(default=2027, ge=2020, le=2100)
    search_max_pages: int | None = Field(default=None, ge=1, le=10)
    search_max_results: int | None = Field(default=None, ge=1, le=250)
    search_max_rechecks: int | None = Field(default=None, ge=0, le=250)
    request_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    connect_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_backoff_seconds: float = Field(default=0.5, ge=0, le=30)
    rate_limit_seconds: float = Field(default=2.0, ge=0, le=60)
    max_concurrency: int = Field(default=3, ge=1, le=16)
    max_response_bytes: int = Field(default=15_000_000, ge=10_000, le=100_000_000)
    closure_confirmation_runs: int = Field(default=2, ge=1, le=10)
    linkedin_crawl_authorized: bool = False
    user_agent: str = Field(default=DEFAULT_USER_AGENT, min_length=20, max_length=300)
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Validate the configured SQLAlchemy database URL."""
        if "://" not in value:
            raise ValueError("database_url must be a SQLAlchemy URL")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize the configured logging level."""
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be a standard Python logging level")
        return normalized

    @model_validator(mode="after")
    def validate_search_limits(self) -> Settings:
        """Validate global search-limit overrides."""
        if (
            self.search_max_pages is not None
            and self.search_max_results is not None
            and self.search_max_results > self.search_max_pages * 25
        ):
            raise ValueError("search_max_results cannot exceed search_max_pages * 25")
        return self


_ENV_FIELDS = {
    "DATABASE_URL": "database_url",
    "SEARCH_CONFIG_DIR": "search_config_dir",
    "CATEGORY_CONFIG_PATH": "category_config_path",
    "README_PATH": "readme_path",
    "TARGET_CYCLE": "target_cycle",
    "SEARCH_MAX_PAGES": "search_max_pages",
    "SEARCH_MAX_RESULTS": "search_max_results",
    "SEARCH_MAX_RECHECKS": "search_max_rechecks",
    "REQUEST_TIMEOUT_SECONDS": "request_timeout_seconds",
    "CONNECT_TIMEOUT_SECONDS": "connect_timeout_seconds",
    "MAX_RETRIES": "max_retries",
    "RETRY_BACKOFF_SECONDS": "retry_backoff_seconds",
    "RATE_LIMIT_SECONDS": "rate_limit_seconds",
    "MAX_CONCURRENCY": "max_concurrency",
    "MAX_RESPONSE_BYTES": "max_response_bytes",
    "CLOSURE_CONFIRMATION_RUNS": "closure_confirmation_runs",
    "LINKEDIN_CRAWL_AUTHORIZED": "linkedin_crawl_authorized",
    "USER_AGENT": "user_agent",
    "LOG_LEVEL": "log_level",
}


def load_settings(path: Path | None = None, *, dotenv_path: Path = Path(".env")) -> Settings:
    """Load defaults < `.env` < optional YAML < process environment."""
    dotenv = {
        key: value.strip() for key, value in dotenv_values(dotenv_path).items() if value is not None
    }
    configured_path = path
    settings_file_value = os.getenv("INTERNSHIPS_SETTINGS_FILE") or dotenv.get(
        "INTERNSHIPS_SETTINGS_FILE"
    )
    if configured_path is None and settings_file_value:
        configured_path = Path(settings_file_value.strip())
    if configured_path is None and Path("configs/settings.yml").is_file():
        configured_path = Path("configs/settings.yml")

    values = _environment_values(dotenv)
    if configured_path is not None:
        if not configured_path.is_file():
            raise ValueError(f"settings file does not exist: {configured_path}")
        loaded = yaml.safe_load(configured_path.read_text(encoding="utf-8"))
        if loaded is not None and not isinstance(loaded, dict):
            raise ValueError("settings YAML must contain a mapping")
        values.update(loaded or {})
    values.update(_environment_values(os.environ))
    return Settings.model_validate(values)


def apply_search_overrides(
    searches: list[LinkedInSearchConfig], settings: Settings
) -> list[LinkedInSearchConfig]:
    """Apply apply search overrides."""
    output: list[LinkedInSearchConfig] = []
    for search in searches:
        pages = settings.search_max_pages or search.max_pages
        results = settings.search_max_results or min(search.max_results, pages * 25)
        if results > pages * 25:
            raise ValueError(f"search {search.slug}: effective result limit exceeds page capacity")
        rechecks = (
            settings.search_max_rechecks
            if settings.search_max_rechecks is not None
            else search.max_rechecks
        )
        output.append(
            search.model_copy(
                update={
                    "max_pages": pages,
                    "max_results": results,
                    "max_rechecks": rechecks,
                }
            )
        )
    return output


def _environment_values(source: Mapping[str, str | None]) -> dict[str, str]:
    """Collect supported settings from environment variables."""
    values: dict[str, str] = {}
    for environment_name, field_name in _ENV_FIELDS.items():
        value = source.get(f"INTERNSHIPS_{environment_name}")
        if value is not None:
            values[field_name] = str(value).strip()
    return values
