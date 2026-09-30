"""Synthetic browser state must exercise the real schema and public projections."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest
from scripts.testing import create_site_fixture

from opportunities.config.settings import Settings
from opportunities.database.repository import Repository
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.public_exports import validate_public_exports


def test_fixture_matches_migrated_repository_and_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(create_site_fixture, "FIXTURE_DIRECTORY", tmp_path)
    # Settings() must not load local environment configuration or a canonical path.
    monkeypatch.setenv("OPPORTUNITIES_DATABASE_URL", "not-a-database-url")
    now = datetime(2026, 9, 28, 12, tzinfo=UTC)
    database = create_site_fixture.create_fixture(now=now)
    settings = Settings(database_url=f"sqlite:///{database.as_posix()}")
    engine = create_database_engine(settings.database_url)
    try:
        repository = Repository(create_session_factory(engine), settings)
        jobs = repository.list_open_jobs()
        assert len(jobs) == 12
        by_id = {job.linkedin_job_id: job for job in jobs}
        assert set(by_id) == {str(1000000001 + index) for index in range(12)}
        assert by_id["1000000012"].first_seen_at.isoformat() == "2026-09-28T10:00:00+00:00"
        assert by_id["1000000001"].first_seen_at.isoformat() == "2026-08-19T12:00:00+00:00"
        assert validate_public_exports(tmp_path, jobs) == []
        assert repository.stats().last_success_at == create_site_fixture.COLLECTION_TIME
    finally:
        engine.dispose()
    with closing(sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM job_searches").fetchone() == (0,)
    original = (tmp_path / "open-opportunities.json").read_bytes()
    create_site_fixture.create_fixture(now=now)
    assert (tmp_path / "open-opportunities.json").read_bytes() == original
    demo = create_site_fixture.create_fixture(now=now, demo=True)
    assert demo.parent == tmp_path / "demo"
    rows = json.loads((demo.parent / "open-opportunities.json").read_bytes())
    assert len(rows) == 12
    assert rows[0]["company"] == "Nova Engineering"


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_fixture_refuses_to_replace_state_with_sidecars(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    monkeypatch.setattr(create_site_fixture, "FIXTURE_DIRECTORY", tmp_path)
    database = tmp_path / "opportunities.db"
    database.write_bytes(b"preserve database")
    sidecar = tmp_path / f"opportunities.db{suffix}"
    sidecar.write_bytes(b"preserve sidecar")
    with pytest.raises(ValueError, match="Close the fixture database"):
        create_site_fixture.create_fixture(now=datetime(2026, 9, 28, tzinfo=UTC))
    assert database.read_bytes() == b"preserve database"
    assert sidecar.read_bytes() == b"preserve sidecar"
