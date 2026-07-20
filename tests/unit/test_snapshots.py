from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opportunities.database.migrations import migration_head, upgrade_database
from opportunities.database.snapshots import (
    RETENTION_POLICY,
    SnapshotError,
    create_snapshot,
    load_manifest,
    verify_snapshot,
)
from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))
CREATED_AT = datetime(2026, 7, 20, 3, 30, tzinfo=UTC)
COLLECTED_AT = "2026-07-20 03:15:00.000000"


def _database(path: Path) -> None:
    upgrade_database(f"sqlite:///{path.as_posix()}", repository_root=ROOT)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO searches "
            "(slug, name, keywords, location, enabled, config_hash, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "snapshot-test",
                "Snapshot test",
                "software intern",
                "Europe",
                1,
                "a" * 64,
                COLLECTED_AT,
            ),
        )
        connection.execute(
            "INSERT INTO search_runs "
            "(id, search_slug, status, started_at, finished_at, duration_ms, "
            "found_count, accepted_count, excluded_count, warning_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "00000000-0000-0000-0000-000000000001",
                "snapshot-test",
                "success",
                COLLECTED_AT,
                COLLECTED_AT,
                10,
                1,
                1,
                0,
                0,
            ),
        )


def _create_bundle(
    tmp_path: Path,
    *,
    name: str = "first",
    previous_manifest: Path | None = None,
) -> tuple[Path, Path]:
    database = tmp_path / "source.db"
    if not database.exists():
        _database(database)
    snapshot = tmp_path / f"{name}.db"
    manifest = tmp_path / f"{name}.json"
    create_snapshot(
        database,
        snapshot,
        manifest,
        key_prefix="opportunities/canonical-state",
        retention_days=365,
        repository="example/opportunities",
        run_id=name,
        run_attempt=1,
        previous_manifest_path=previous_manifest,
        created_at=CREATED_AT,
    )
    return snapshot, manifest


def test_snapshot_manifest_captures_recovery_metadata(tmp_path: Path) -> None:
    snapshot, manifest_path = _create_bundle(tmp_path)

    manifest = verify_snapshot(
        snapshot,
        manifest_path,
        expected_database_key=(
            "opportunities/canonical-state/snapshots/2026/07/20/"
            "20260720T033000.000000Z-run-first-attempt-1.db"
        ),
        expected_schema_revision=migration_head(repository_root=ROOT),
    )

    assert manifest.collection_timestamp == datetime(2026, 7, 20, 3, 15, tzinfo=UTC)
    assert manifest.previous_snapshot is None
    assert manifest.retention.policy == RETENTION_POLICY
    assert manifest.retention.days == 365
    assert manifest.retention.retain_until == datetime(2027, 7, 20, 3, 30, tzinfo=UTC)
    assert manifest.size_bytes == snapshot.stat().st_size
    assert len(manifest.sha256) == 64


def test_snapshot_links_to_previous_immutable_objects(tmp_path: Path) -> None:
    _first_snapshot, first_manifest_path = _create_bundle(tmp_path)
    second_snapshot, second_manifest_path = _create_bundle(
        tmp_path,
        name="second",
        previous_manifest=first_manifest_path,
    )

    first = load_manifest(first_manifest_path)
    second = verify_snapshot(second_snapshot, second_manifest_path)

    assert second.previous_snapshot is not None
    assert second.previous_snapshot.database_key == first.database_key
    assert second.previous_snapshot.manifest_key == first.manifest_key


def test_snapshot_creation_rejects_a_missing_previous_manifest(tmp_path: Path) -> None:
    database = tmp_path / "source.db"
    _database(database)

    with pytest.raises(SnapshotError, match="previous snapshot manifest does not exist"):
        create_snapshot(
            database,
            tmp_path / "snapshot.db",
            tmp_path / "manifest.json",
            key_prefix="opportunities/canonical-state",
            retention_days=365,
            repository="example/opportunities",
            run_id="missing-previous",
            run_attempt=1,
            previous_manifest_path=tmp_path / "missing.json",
            created_at=CREATED_AT,
        )


def test_snapshot_verification_rejects_tampered_database(tmp_path: Path) -> None:
    snapshot, manifest = _create_bundle(tmp_path)
    with snapshot.open("ab") as handle:
        handle.write(b"tampered")

    with pytest.raises(SnapshotError, match="size does not match"):
        verify_snapshot(snapshot, manifest)


def test_snapshot_manifest_requires_timezone_aware_timestamps(tmp_path: Path) -> None:
    _snapshot, manifest_path = _create_bundle(tmp_path)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["created_at"] = "2026-07-20T03:30:00"
    manifest_path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(SnapshotError, match="created_at must include a timezone"):
        load_manifest(manifest_path)


def test_snapshot_manifest_rejects_unknown_fields(tmp_path: Path) -> None:
    _snapshot, manifest_path = _create_bundle(tmp_path)
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["unsigned_note"] = "not allowed"
    manifest_path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(SnapshotError, match="unknown unsigned_note"):
        load_manifest(manifest_path)
