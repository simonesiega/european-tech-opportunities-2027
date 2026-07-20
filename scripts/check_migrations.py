"""Check that ORM metadata is represented by the latest Alembic migration."""

from __future__ import annotations

import tempfile
from pathlib import Path

# Importing alembic modules registers the Alembic environment for autogeneration.
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

# Importing opportunities.database.models registers every table on Base.metadata for comparison.
from opportunities.database import models as database_models  # noqa: F401
from opportunities.database.base import Base
from opportunities.database.migrations import migration_head, upgrade_database
from opportunities.utils.paths import find_project_root


def main() -> None:
    """Check ORM metadata against a database upgraded to migration head."""
    repository_root = find_project_root(Path(__file__))
    expected_version = migration_head(repository_root=repository_root)

    # Upgrade a temporary SQLite database, then compare its schema with ORM metadata.
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "migration-check.db"
        url = f"sqlite:///{database.as_posix()}"
        upgrade_database(url, repository_root=repository_root)
        engine = create_engine(url)
        with engine.connect() as connection:
            version = connection.scalar(text("SELECT version_num FROM alembic_version"))
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
        engine.dispose()

    # Require the expected revision and no schema differences.
    if version != expected_version:
        raise SystemExit(f"unexpected Alembic version: {version!r}; expected {expected_version!r}")
    if differences:
        formatted = "\n".join(str(difference) for difference in differences)
        raise SystemExit(f"ORM metadata is not represented by Alembic head:\n{formatted}")


if __name__ == "__main__":
    main()
