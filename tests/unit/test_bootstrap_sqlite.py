"""Offline regression for the first-production-activation SQLite handoff."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

from opportunities.database.migrations import upgrade_database
from opportunities.database.snapshots import inspect_database
from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))


def test_bootstrap_fails_when_source_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "missing.db"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/bootstrap_sqlite.py"), str(source)],
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stdout == b""
    assert not source.exists()


def test_bootstrap_stream_includes_committed_wal_rows(tmp_path: Path) -> None:
    """Copying only the live .db file would silently omit these committed rows."""
    source = tmp_path / "source.db"
    destination = tmp_path / "download.db"
    upgrade_database(f"sqlite:///{source.as_posix()}", repository_root=ROOT)
    with closing(sqlite3.connect(source)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute(
            "INSERT INTO searches "
            "(slug, name, keywords, location, enabled, config_hash, updated_at) "
            "VALUES ('bootstrap', 'Bootstrap', 'intern', 'Europe', 1, ?, '2026-07-20')",
            ("a" * 64,),
        )
        writer.commit()
        assert (tmp_path / "source.db-wal").stat().st_size > 0

        with destination.open("wb") as output:
            subprocess.run(
                [sys.executable, str(ROOT / "scripts/bootstrap_sqlite.py"), str(source)],
                stdout=output,
                check=True,
            )

    inspect_database(destination)
    with closing(sqlite3.connect(destination)) as copy:
        assert copy.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        assert copy.execute("SELECT slug FROM searches").fetchall() == [("bootstrap",)]
    assert not (tmp_path / "download.db-wal").exists()
