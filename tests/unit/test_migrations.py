"""Seed historical schemas with raw SQL, independently of the current ORM models."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.settings import Settings
from opportunities.database.migrations import upgrade_database
from opportunities.database.repository import Repository
from opportunities.models.search import LinkedInSearchConfig
from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))


def test_repeated_upgrade_preserves_schema_and_existing_data(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    repository.sync_searches([search], datetime(2026, 7, 20, tzinfo=UTC))
    database = tmp_path / "opportunities.db"
    original = database.read_bytes()

    for _ in range(2):
        upgrade_database(settings.database_url, repository_root=ROOT)
        assert database.read_bytes() == original
        assert repository.stats().configured_searches == 1


def test_upgrade_database_creates_a_missing_sqlite_parent(tmp_path: Path) -> None:
    database = tmp_path / "nested" / "state" / "opportunities.db"

    upgrade_database(f"sqlite:///{database.as_posix()}", repository_root=ROOT)

    assert database.is_file()


def test_employment_type_migration_backfills_existing_jobs(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    command.upgrade(config, "e4a7c9d21b60")

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            """INSERT INTO jobs (
                linkedin_job_id, company, title, location, link, category, industries,
                employment_type, start_date, first_seen_at, last_seen_at, updated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "1111111111",
                "Example Technology",
                "Software Engineering Intern 2027",
                "London, UK",
                "https://www.linkedin.com/jobs/view/1111111111",
                "software-engineering",
                "Software Development",
                "full-time",
                None,
                "2026-07-01 00:00:00",
                "2026-07-01 00:00:00",
                "2026-07-01 00:00:00",
                "open",
            ),
        )

    command.upgrade(config, "head")

    with closing(sqlite3.connect(database)) as connection:
        value = connection.execute(
            "SELECT employment_type FROM jobs WHERE linkedin_job_id = '1111111111'"
        ).fetchone()
        columns = {row[1]: row[3] for row in connection.execute("PRAGMA table_info(jobs)")}
        jobs_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'jobs'"
        ).fetchone()
    assert value == ("internship",)
    assert columns["employment_type"] == 1
    assert jobs_sql is not None
    assert "ck_jobs_employment_type" in jobs_sql[0]


def test_canonical_state_migration_preserves_rows_and_rejects_invalid_state(
    tmp_path: Path,
) -> None:
    database = tmp_path / "constraints.db"
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database.as_posix()}")
    command.upgrade(config, "f2b8d4c61a90")

    observed_at = "2026-07-01 00:00:00"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(
            "INSERT INTO searches VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test", "Test", "software intern", "Europe", 1, "a" * 64, observed_at),
        )
        connection.execute(
            """INSERT INTO jobs (
                linkedin_job_id, company, title, location, link, category, industries,
                employment_type, start_date, first_seen_at, last_seen_at, updated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "1111111111",
                "Example Technology",
                "Software Engineering Intern 2027",
                "London, UK",
                "https://www.linkedin.com/jobs/view/1111111111",
                "software-engineering",
                "Software Development",
                "internship",
                None,
                observed_at,
                observed_at,
                observed_at,
                "open",
            ),
        )
        connection.execute(
            """INSERT INTO search_runs (
                id, search_slug, status, started_at, finished_at, duration_ms,
                found_count, accepted_count, excluded_count, warning_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("run-1", "test", "success", observed_at, observed_at, 1, 1, 1, 0, 0),
        )
        connection.execute(
            "INSERT INTO job_searches VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test", "1111111111", observed_at, observed_at, "run-1", 0, 1),
        )

    command.upgrade(config, "head")

    invalid_updates = (
        ("UPDATE jobs SET status = 'pending'", "ck_jobs_status"),
        (
            "UPDATE jobs SET last_seen_at = '2026-06-30 00:00:00'",
            "ck_jobs_seen_at_order",
        ),
        ("UPDATE search_runs SET status = 'running'", "ck_search_runs_status"),
        (
            "UPDATE search_runs SET duration_ms = -1",
            "ck_search_runs_duration_ms_nonnegative",
        ),
        (
            "UPDATE search_runs SET found_count = -1",
            "ck_search_runs_found_count_nonnegative",
        ),
        (
            "UPDATE search_runs SET accepted_count = -1",
            "ck_search_runs_accepted_count_nonnegative",
        ),
        (
            "UPDATE search_runs SET excluded_count = -1",
            "ck_search_runs_excluded_count_nonnegative",
        ),
        (
            "UPDATE search_runs SET warning_count = -1",
            "ck_search_runs_warning_count_nonnegative",
        ),
        (
            "UPDATE job_searches SET unavailable_confirmations = -1",
            "ck_job_searches_unavailable_confirmations_nonnegative",
        ),
        (
            "UPDATE job_searches SET last_seen_at = '2026-06-30 00:00:00'",
            "ck_job_searches_seen_at_order",
        ),
    )
    with closing(sqlite3.connect(database)) as connection, connection:
        assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM search_runs").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM job_searches").fetchone() == (1,)
        for statement, constraint_name in invalid_updates:
            with pytest.raises(sqlite3.IntegrityError, match=constraint_name):
                connection.execute(statement)
            connection.rollback()

    # The additive quality revision must also round-trip without touching lifecycle rows.
    command.downgrade(config, "a9c4e72b5d18")
    with closing(sqlite3.connect(database)) as connection:
        before = {
            table: connection.execute(f"SELECT * FROM {table}").fetchall()
            for table in ("jobs", "searches", "search_runs", "job_searches")
        }
        assert not connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'data_quality_snapshots'"
        ).fetchall()
    command.upgrade(config, "head")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM data_quality_snapshots").fetchone() == (0,)
        for table, rows in before.items():
            assert connection.execute(f"SELECT * FROM {table}").fetchall() == rows
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
