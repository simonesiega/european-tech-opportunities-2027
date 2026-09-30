from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from opportunities.config.settings import Settings
from opportunities.database import snapshots
from opportunities.database.migrations import migration_head, upgrade_database
from opportunities.database.repository import Repository
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.database.snapshots import (
    RETENTION_POLICY,
    SnapshotError,
    create_snapshot,
    load_manifest,
    verify_snapshot,
)
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))
CREATED_AT = datetime(2026, 7, 20, 3, 30, tzinfo=UTC)
COLLECTED_AT = "2026-07-20 03:15:00.000000"


def _database(path: Path) -> None:
    settings = Settings(database_url=f"sqlite:///{path.as_posix()}")
    upgrade_database(settings.database_url, repository_root=ROOT)
    engine = create_database_engine(settings.database_url)
    try:
        repository = Repository(create_session_factory(engine), settings)
        observed = datetime(2026, 7, 20, 3, 15, tzinfo=UTC)
        search = LinkedInSearchConfig(
            slug="snapshot-test",
            name="Snapshot test",
            keywords="software intern",
            location="Europe",
        )
        repository.sync_searches([search], observed)
        repository.persist_success(
            run_id="00000000-0000-0000-0000-000000000001",
            search=search,
            jobs=[
                DiscoveredJob(
                    linkedin_job_id="1111111111",
                    company="Synthetic Technology",
                    title="Software Intern 2027",
                    location="Berlin, Germany",
                    link="https://www.linkedin.com/jobs/view/1111111111",
                    category=OpportunityCategory.SOFTWARE_ENGINEERING,
                    employment_type=EmploymentType.INTERNSHIP,
                )
            ],
            confirmed_unavailable_ids=(),
            found_count=1,
            excluded_count=0,
            warning_count=0,
            started_at=observed,
            finished_at=observed,
            duration_ms=10,
        )
    finally:
        engine.dispose()


def _create_bundle(
    tmp_path: Path,
    *,
    name: str = "first",
    previous_manifest: Path | None = None,
    database: Path | None = None,
) -> tuple[Path, Path]:
    database = database or tmp_path / "source.db"
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


def test_snapshot_from_live_wal_is_cold_and_sidecar_free(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    _database(source)
    with closing(sqlite3.connect(source)) as writer:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone() == ("wal",)
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute(
            "INSERT INTO searches "
            "(slug, name, keywords, location, enabled, config_hash, updated_at) "
            "VALUES ('in-wal', 'WAL row', 'intern', 'Europe', 1, ?, ?)",
            ("a" * 64, COLLECTED_AT),
        )
        writer.commit()
        assert (tmp_path / "source.db-wal").stat().st_size > 0
        snapshot, manifest = _create_bundle(tmp_path)

    verify_snapshot(snapshot, manifest)
    with closing(sqlite3.connect(snapshot.resolve().as_uri() + "?mode=ro", uri=True)) as reader:
        assert reader.execute("PRAGMA journal_mode").fetchone() == ("delete",)
        assert reader.execute("SELECT name FROM searches WHERE slug='in-wal'").fetchone() == (
            "WAL row",
        )
    assert not (tmp_path / "first.db-wal").exists()
    assert not (tmp_path / "first.db-shm").exists()


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


@pytest.mark.parametrize("same_size", [False, True])
def test_snapshot_verification_rejects_tampered_database(tmp_path: Path, same_size: bool) -> None:
    snapshot, manifest = _create_bundle(tmp_path)
    content = bytearray(snapshot.read_bytes())
    if same_size:
        content[-1] ^= 1
    else:
        content.extend(b"tampered")
    snapshot.write_bytes(content)

    with pytest.raises(SnapshotError, match="SHA-256" if same_size else "size does not match"):
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


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    directory = tmp_path / "snapshots"
    directory.mkdir()
    return directory


@pytest.mark.parametrize("source_name", [".first.db.tmp", ".first.json.tmp"])
def test_snapshot_never_deletes_source_matching_old_staging_names(
    workspace: Path, source_name: str
) -> None:
    source = workspace / source_name
    _database(source)
    original = source.read_bytes()
    snapshot, manifest = _create_bundle(workspace, database=source)
    assert source.read_bytes() == original
    verify_snapshot(snapshot, manifest)


def test_snapshot_preserves_other_operations_staging_files(workspace: Path) -> None:
    preserved = [workspace / ".first.db.tmp", workspace / ".first.json.tmp"]
    for path in preserved:
        path.write_bytes(b"another operation owns this file")
    snapshot, manifest = _create_bundle(workspace)
    verify_snapshot(snapshot, manifest)
    for path in preserved:
        assert path.read_bytes() == b"another operation owns this file"


@pytest.mark.parametrize("output_name", ["first.db", "first.json"])
def test_failed_snapshot_preserves_outputs_it_did_not_publish(
    workspace: Path, monkeypatch: pytest.MonkeyPatch, output_name: str
) -> None:
    source = workspace / "source.db"
    _database(source)
    original = source.read_bytes()
    foreign = workspace / output_name

    def fail_inspection(_path: Path) -> snapshots.DatabaseMetadata:
        foreign.write_bytes(b"foreign output")
        raise SnapshotError("synthetic inspection failure")

    monkeypatch.setattr(snapshots, "inspect_database", fail_inspection)
    with pytest.raises(SnapshotError, match="synthetic inspection failure"):
        _create_bundle(workspace)
    assert foreign.read_bytes() == b"foreign output"
    assert source.read_bytes() == original
    assert set(workspace.iterdir()) == {source, foreign}


def test_partial_snapshot_promotion_cleans_only_owned_files(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = workspace / "source.db"
    _database(source)
    original = source.read_bytes()
    replace = os.replace

    def fail_manifest_promotion(source_path: Path, destination_path: Path) -> None:
        if destination_path == workspace / "first.json":
            raise OSError("synthetic promotion failure")
        replace(source_path, destination_path)

    monkeypatch.setattr(os, "replace", fail_manifest_promotion)
    with pytest.raises(OSError, match="synthetic promotion failure"):
        _create_bundle(workspace)
    assert source.read_bytes() == original
    assert set(workspace.iterdir()) == {source}


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
@pytest.mark.parametrize("destination", ["snapshot", "manifest"])
def test_snapshot_rejects_source_sidecar_outputs(
    workspace: Path, suffix: str, destination: str
) -> None:
    source = workspace / "source.db"
    _database(source)
    original = source.read_bytes()
    sidecar = Path(f"{source}{suffix}")
    with pytest.raises(SnapshotError, match="sidecars"):
        create_snapshot(
            source,
            sidecar if destination == "snapshot" else workspace / "first.db",
            sidecar if destination == "manifest" else workspace / "first.json",
            key_prefix="synthetic/state",
            retention_days=30,
            repository="example/synthetic",
            run_id="test",
            run_attempt=1,
            created_at=CREATED_AT,
        )
    assert source.read_bytes() == original
    assert set(workspace.iterdir()) == {source}


@pytest.mark.parametrize(
    ("bad_field", "bad_value"),
    [
        pytest.param("run_attempt", True, id="boolean-attempt"),
        pytest.param("retention_days", True, id="boolean-retention"),
        pytest.param("retention_days", 1.5, id="fractional-retention"),
        pytest.param("key_prefix", "x" * 1000, id="oversized-completed-key"),
        pytest.param("created_at", datetime(9999, 12, 31, tzinfo=UTC), id="retention-overflow"),
    ],
)
def test_snapshot_validates_manifest_limits_before_writing(
    workspace: Path, bad_field: str, bad_value: object
) -> None:
    source = workspace / "source.db"
    _database(source)
    original = source.read_bytes()
    with pytest.raises(SnapshotError):
        create_snapshot(
            source,
            workspace / "first.db",
            workspace / "first.json",
            repository="example/synthetic",
            run_id="test",
            key_prefix=cast(str, bad_value) if bad_field == "key_prefix" else "synthetic/state",
            retention_days=cast(int, bad_value) if bad_field == "retention_days" else 30,
            run_attempt=cast(int, bad_value) if bad_field == "run_attempt" else 1,
            created_at=cast(datetime, bad_value) if bad_field == "created_at" else CREATED_AT,
        )
    assert source.read_bytes() == original
    assert set(workspace.iterdir()) == {source}


def test_manifest_read_rejects_oversized_bytes(workspace: Path) -> None:
    manifest = workspace / "oversized.json"
    manifest.write_bytes(b" " * (65_536 + 1))
    with pytest.raises(SnapshotError, match="size limit"):
        load_manifest(manifest)


@pytest.mark.parametrize("duplicate", ["format_version", "run_id"])
def test_manifest_rejects_duplicate_root_and_nested_fields(workspace: Path, duplicate: str) -> None:
    _snapshot, manifest = _create_bundle(workspace)
    content = manifest.read_text(encoding="utf-8")
    insertion = (
        '"format_version": 999, ' if duplicate == "format_version" else '"run_id": "other", '
    )
    target = f'"{duplicate}":'
    manifest.write_text(content.replace(target, insertion + target, 1), encoding="utf-8")
    with pytest.raises(SnapshotError, match="duplicate"):
        load_manifest(manifest)


@pytest.mark.parametrize("timestamp", ["9999-12-31T23:59:59Z", "0001-01-01T00:00:00+01:00"])
def test_manifest_timestamp_overflow_is_a_validation_error(workspace: Path, timestamp: str) -> None:
    _snapshot, manifest = _create_bundle(workspace)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["created_at"] = timestamp
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SnapshotError):
        load_manifest(manifest)


def test_snapshot_rejects_dangling_output_symlinks(workspace: Path) -> None:
    output = workspace / "first.db"
    try:
        output.symlink_to("missing-target.db")
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")
    with pytest.raises(SnapshotError, match="must not already exist"):
        _create_bundle(workspace)
    assert output.is_symlink()
    assert output.readlink() == Path("missing-target.db")
    assert not (workspace / "missing-target.db").exists()
