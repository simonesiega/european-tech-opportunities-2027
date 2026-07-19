"""Create and verify self-describing, durable SQLite snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final

FORMAT_VERSION: Final = 1
RETENTION_POLICY: Final = "restricted-vps-sftp"
EXPECTED_TABLES: Final = frozenset(
    {"alembic_version", "searches", "search_runs", "jobs", "job_searches"}
)
_SHA256_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA_REVISION_RE: Final = re.compile(r"^[A-Za-z0-9]+$")
_RUN_ID_RE: Final = re.compile(r"^[A-Za-z0-9._-]+$")
_KEY_RE: Final = re.compile(r"^[A-Za-z0-9!_.*'()/-]+$")


class SnapshotError(ValueError):
    """Raised when a snapshot or its recovery metadata is invalid."""


@dataclass(frozen=True)
class PreviousSnapshot:
    """Reference the immutable database and manifest preceding a snapshot."""

    database_key: str
    manifest_key: str


@dataclass(frozen=True)
class Retention:
    """Describe the restricted storage policy that retains a snapshot."""

    policy: str
    days: int
    retain_until: datetime


@dataclass(frozen=True)
class SnapshotSource:
    """Identify the workflow execution that produced a snapshot."""

    repository: str
    run_id: str
    run_attempt: int


@dataclass(frozen=True)
class SnapshotManifest:
    """Metadata required to authenticate and recover one SQLite snapshot."""

    format_version: int
    manifest_key: str
    database_key: str
    sha256: str
    size_bytes: int
    schema_revision: str
    created_at: datetime
    collection_timestamp: datetime | None
    previous_snapshot: PreviousSnapshot | None
    retention: Retention
    source: SnapshotSource

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-compatible manifest representation."""
        previous = (
            {
                "database_key": self.previous_snapshot.database_key,
                "manifest_key": self.previous_snapshot.manifest_key,
            }
            if self.previous_snapshot is not None
            else None
        )
        return {
            "collection_timestamp": _format_timestamp(self.collection_timestamp),
            "created_at": _format_timestamp(self.created_at),
            "database": {
                "key": self.database_key,
                "sha256": self.sha256,
                "size_bytes": self.size_bytes,
            },
            "format_version": self.format_version,
            "manifest_key": self.manifest_key,
            "previous_snapshot": previous,
            "retention": {
                "days": self.retention.days,
                "policy": self.retention.policy,
                "retain_until": _format_timestamp(self.retention.retain_until),
            },
            "schema_revision": self.schema_revision,
            "source": {
                "repository": self.source.repository,
                "run_attempt": self.source.run_attempt,
                "run_id": self.source.run_id,
            },
        }

    @classmethod
    def from_dict(cls, value: object) -> SnapshotManifest:
        """Validate and construct a manifest from decoded JSON."""
        root = _mapping(
            value,
            "manifest",
            {
                "collection_timestamp",
                "created_at",
                "database",
                "format_version",
                "manifest_key",
                "previous_snapshot",
                "retention",
                "schema_revision",
                "source",
            },
        )
        format_version = _integer(root["format_version"], "format_version", minimum=1)
        if format_version != FORMAT_VERSION:
            raise SnapshotError(f"unsupported snapshot format version: {format_version}")

        database = _mapping(root["database"], "database", {"key", "sha256", "size_bytes"})
        retention_data = _mapping(
            root["retention"], "retention", {"days", "policy", "retain_until"}
        )
        source_data = _mapping(root["source"], "source", {"repository", "run_attempt", "run_id"})

        created_at = _timestamp(root["created_at"], "created_at")
        collection_timestamp = _optional_timestamp(
            root["collection_timestamp"], "collection_timestamp"
        )
        if collection_timestamp is not None and collection_timestamp > created_at:
            raise SnapshotError("collection_timestamp cannot follow created_at")

        retention_days = _integer(retention_data["days"], "retention.days", minimum=1)
        if retention_days > 3650:
            raise SnapshotError("retention.days must not exceed 3650")
        retention_policy = _string(retention_data["policy"], "retention.policy")
        if retention_policy != RETENTION_POLICY:
            raise SnapshotError(f"unsupported retention policy: {retention_policy}")
        retain_until = _timestamp(retention_data["retain_until"], "retention.retain_until")
        expected_retain_until = created_at + timedelta(days=retention_days)
        if retain_until != expected_retain_until:
            raise SnapshotError("retention.retain_until does not match created_at plus days")

        sha256 = _string(database["sha256"], "database.sha256")
        if not _SHA256_RE.fullmatch(sha256):
            raise SnapshotError("database.sha256 must be a lowercase SHA-256 digest")
        schema_revision = _string(root["schema_revision"], "schema_revision")
        if not _SCHEMA_REVISION_RE.fullmatch(schema_revision):
            raise SnapshotError("schema_revision contains unsupported characters")

        previous_data = root["previous_snapshot"]
        previous: PreviousSnapshot | None = None
        if previous_data is not None:
            previous_mapping = _mapping(
                previous_data,
                "previous_snapshot",
                {"database_key", "manifest_key"},
            )
            previous = PreviousSnapshot(
                database_key=_object_key(
                    previous_mapping["database_key"], "previous_snapshot.database_key"
                ),
                manifest_key=_object_key(
                    previous_mapping["manifest_key"], "previous_snapshot.manifest_key"
                ),
            )

        manifest = cls(
            format_version=format_version,
            manifest_key=_object_key(root["manifest_key"], "manifest_key"),
            database_key=_object_key(database["key"], "database.key"),
            sha256=sha256,
            size_bytes=_integer(database["size_bytes"], "database.size_bytes", minimum=1),
            schema_revision=schema_revision,
            created_at=created_at,
            collection_timestamp=collection_timestamp,
            previous_snapshot=previous,
            retention=Retention(
                policy=retention_policy,
                days=retention_days,
                retain_until=retain_until,
            ),
            source=SnapshotSource(
                repository=_string(source_data["repository"], "source.repository"),
                run_id=_run_identifier(source_data["run_id"], "source.run_id"),
                run_attempt=_integer(source_data["run_attempt"], "source.run_attempt", minimum=1),
            ),
        )
        if manifest.database_key == manifest.manifest_key:
            raise SnapshotError("database and manifest object keys must differ")
        if previous is not None and (
            previous.database_key == manifest.database_key
            or previous.manifest_key == manifest.manifest_key
        ):
            raise SnapshotError("previous_snapshot must reference an earlier snapshot")
        return manifest


def create_snapshot(
    database_path: Path,
    snapshot_path: Path,
    manifest_path: Path,
    *,
    key_prefix: str,
    retention_days: int,
    repository: str,
    run_id: str,
    run_attempt: int,
    previous_manifest_path: Path | None = None,
    created_at: datetime | None = None,
) -> SnapshotManifest:
    """Create a consistent SQLite backup and its timestamped storage manifest."""
    if not database_path.is_file():
        raise SnapshotError(f"database does not exist: {database_path}")
    if not 1 <= retention_days <= 3650:
        raise SnapshotError("retention_days must be between 1 and 3650")
    if run_attempt < 1:
        raise SnapshotError("run_attempt must be positive")
    _run_identifier(run_id, "run_id")
    if not repository or any(character in repository for character in "\r\n\0"):
        raise SnapshotError("repository is invalid")
    if database_path.resolve() == snapshot_path.resolve():
        raise SnapshotError("snapshot output must differ from the source database")

    normalized_prefix = _key_prefix(key_prefix)
    created = _utc(created_at or datetime.now(UTC), "created_at")
    timestamp_slug = created.strftime("%Y%m%dT%H%M%S.%fZ")
    object_stem = (
        f"{normalized_prefix}/snapshots/{created:%Y/%m/%d}/"
        f"{timestamp_slug}-run-{run_id}-attempt-{run_attempt}"
    )
    database_key = f"{object_stem}.db"
    manifest_key = f"{object_stem}.manifest.json"

    previous: PreviousSnapshot | None = None
    if previous_manifest_path is not None and previous_manifest_path.is_file():
        prior = load_manifest(previous_manifest_path)
        if prior.created_at > created:
            raise SnapshotError("previous snapshot cannot be newer than the new snapshot")
        previous = PreviousSnapshot(
            database_key=prior.database_key,
            manifest_key=prior.manifest_key,
        )

    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_snapshot = snapshot_path.with_name(f".{snapshot_path.name}.tmp")
    temporary_manifest = manifest_path.with_name(f".{manifest_path.name}.tmp")
    for temporary in (temporary_snapshot, temporary_manifest):
        temporary.unlink(missing_ok=True)

    source_uri = database_path.resolve().as_uri() + "?mode=ro"
    try:
        with (
            closing(sqlite3.connect(source_uri, uri=True)) as source,
            closing(sqlite3.connect(temporary_snapshot)) as destination,
        ):
            source.backup(destination)
        os.replace(temporary_snapshot, snapshot_path)

        database_metadata = inspect_database(snapshot_path)
        if (
            database_metadata.collection_timestamp is not None
            and database_metadata.collection_timestamp > created
        ):
            raise SnapshotError("database collection timestamp cannot follow snapshot creation")
        digest = sha256_file(snapshot_path)
        manifest = SnapshotManifest(
            format_version=FORMAT_VERSION,
            manifest_key=manifest_key,
            database_key=database_key,
            sha256=digest,
            size_bytes=snapshot_path.stat().st_size,
            schema_revision=database_metadata.schema_revision,
            created_at=created,
            collection_timestamp=database_metadata.collection_timestamp,
            previous_snapshot=previous,
            retention=Retention(
                policy=RETENTION_POLICY,
                days=retention_days,
                retain_until=created + timedelta(days=retention_days),
            ),
            source=SnapshotSource(
                repository=repository,
                run_id=run_id,
                run_attempt=run_attempt,
            ),
        )
        serialized = (
            json.dumps(manifest.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        )
        temporary_manifest.write_text(serialized, encoding="utf-8", newline="\n")
        os.replace(temporary_manifest, manifest_path)
        return manifest
    except BaseException:
        temporary_snapshot.unlink(missing_ok=True)
        temporary_manifest.unlink(missing_ok=True)
        raise


@dataclass(frozen=True)
class DatabaseMetadata:
    """Values read from a verified SQLite snapshot."""

    schema_revision: str
    collection_timestamp: datetime | None


def inspect_database(database_path: Path) -> DatabaseMetadata:
    """Run recovery checks and return metadata stored inside a SQLite database."""
    if not database_path.is_file() or database_path.stat().st_size == 0:
        raise SnapshotError(f"snapshot database is missing or empty: {database_path}")
    database_uri = database_path.resolve().as_uri() + "?mode=ro"
    try:
        with closing(sqlite3.connect(database_uri, uri=True)) as connection:
            connection.execute("PRAGMA query_only=ON")
            integrity = [str(row[0]) for row in connection.execute("PRAGMA integrity_check")]
            if integrity != ["ok"]:
                detail = integrity[0] if integrity else "no result"
                raise SnapshotError(f"SQLite integrity check failed: {detail}")
            foreign_key_error = connection.execute("PRAGMA foreign_key_check").fetchone()
            if foreign_key_error is not None:
                raise SnapshotError("SQLite foreign-key check failed")

            table_rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            tables = {str(row[0]) for row in table_rows}
            missing = EXPECTED_TABLES - tables
            if missing:
                raise SnapshotError(
                    f"snapshot is missing required tables: {', '.join(sorted(missing))}"
                )

            revision_rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
            if len(revision_rows) != 1:
                raise SnapshotError("snapshot must contain exactly one schema revision")
            schema_revision = str(revision_rows[0][0])
            if not _SCHEMA_REVISION_RE.fullmatch(schema_revision):
                raise SnapshotError("snapshot contains an invalid schema revision")

            collection_row = connection.execute(
                "SELECT MAX(finished_at) FROM search_runs WHERE status = 'success'"
            ).fetchone()
    except sqlite3.Error as exc:
        raise SnapshotError(f"cannot verify SQLite snapshot: {exc}") from exc

    raw_collection = collection_row[0] if collection_row is not None else None
    collection_timestamp = (
        _timestamp(str(raw_collection), "database collection timestamp")
        if raw_collection is not None
        else None
    )
    return DatabaseMetadata(
        schema_revision=schema_revision,
        collection_timestamp=collection_timestamp,
    )


def verify_snapshot(
    database_path: Path,
    manifest_path: Path,
    *,
    expected_database_key: str | None = None,
    expected_schema_revision: str | None = None,
) -> SnapshotManifest:
    """Verify manifest structure, checksum, schema, timestamps, and SQLite recovery."""
    manifest = load_manifest(manifest_path)
    if not database_path.is_file() or database_path.stat().st_size == 0:
        raise SnapshotError(f"snapshot database is missing or empty: {database_path}")
    if expected_database_key is not None and manifest.database_key != expected_database_key:
        raise SnapshotError("manifest database key does not match the requested object")
    if database_path.stat().st_size != manifest.size_bytes:
        raise SnapshotError("snapshot size does not match its manifest")
    digest = sha256_file(database_path)
    if digest != manifest.sha256:
        raise SnapshotError("snapshot SHA-256 does not match its manifest")

    metadata = inspect_database(database_path)
    if metadata.schema_revision != manifest.schema_revision:
        raise SnapshotError("snapshot schema revision does not match its manifest")
    if (
        expected_schema_revision is not None
        and metadata.schema_revision != expected_schema_revision
    ):
        raise SnapshotError(
            f"snapshot schema revision {metadata.schema_revision!r} does not match "
            f"expected revision {expected_schema_revision!r}"
        )
    if metadata.collection_timestamp != manifest.collection_timestamp:
        raise SnapshotError("snapshot collection timestamp does not match its manifest")
    return manifest


def load_manifest(path: Path) -> SnapshotManifest:
    """Read and validate one snapshot manifest."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot read snapshot manifest: {exc}") from exc
    return SnapshotManifest.from_dict(value)


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest for a file."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise SnapshotError(f"cannot hash snapshot: {exc}") from exc
    return digest.hexdigest()


def _mapping(value: object, label: str, expected_keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SnapshotError(f"{label} must be an object")
    mapping = {str(key): item for key, item in value.items()}
    actual_keys = set(mapping)
    if actual_keys != expected_keys:
        missing = expected_keys - actual_keys
        unknown = actual_keys - expected_keys
        details: list[str] = []
        if missing:
            details.append(f"missing {', '.join(sorted(missing))}")
        if unknown:
            details.append(f"unknown {', '.join(sorted(unknown))}")
        raise SnapshotError(f"{label} has invalid fields: {'; '.join(details)}")
    return mapping


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SnapshotError(f"{label} must be a non-empty string")
    if any(character in value for character in "\r\n\0"):
        raise SnapshotError(f"{label} contains control characters")
    return value


def _integer(value: object, label: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SnapshotError(f"{label} must be an integer of at least {minimum}")
    return value


def _timestamp(value: object, label: str) -> datetime:
    text = _string(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError(f"{label} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _optional_timestamp(value: object, label: str) -> datetime | None:
    return None if value is None else _timestamp(value, label)


def _format_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value, "timestamp").isoformat(timespec="microseconds").replace("+00:00", "Z")


def _utc(value: datetime, label: str) -> datetime:
    if value.tzinfo is None:
        raise SnapshotError(f"{label} must include a timezone")
    return value.astimezone(UTC)


def _object_key(value: object, label: str) -> str:
    key = _string(value, label)
    if key.startswith("/") or "//" in key or not _KEY_RE.fullmatch(key):
        raise SnapshotError(f"{label} is not a safe object key")
    if ".." in key.split("/"):
        raise SnapshotError(f"{label} contains a parent segment")
    return key


def _key_prefix(value: str) -> str:
    prefix = value.strip("/")
    _object_key(prefix, "key_prefix")
    return prefix


def _run_identifier(value: object, label: str) -> str:
    identifier = _string(value, label)
    if not _RUN_ID_RE.fullmatch(identifier):
        raise SnapshotError(f"{label} contains unsupported characters")
    return identifier
