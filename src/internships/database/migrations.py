"""Programmatic Alembic migration entry point used by the CLI and tests."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


def _config(repository_root: Path) -> Config:
    """Build an Alembic configuration for the repository."""
    config = Config(str(repository_root / "alembic.ini"))
    config.set_main_option(
        "script_location", str(repository_root / "migrations").replace("%", "%%")
    )
    return config


def migration_head(*, repository_root: Path = Path(".")) -> str | None:
    """Return the latest available migration revision."""
    return ScriptDirectory.from_config(_config(repository_root)).get_current_head()


def upgrade_database(database_url: str, *, repository_root: Path = Path(".")) -> None:
    """Upgrade upgrade database."""
    config = _config(repository_root)
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    # A second upgrade must be a no-op and proves the version row was committed.
    command.upgrade(config, "head")
