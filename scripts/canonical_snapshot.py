"""Create and verify canonical SQLite snapshot bundles for workflow storage."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn

from opportunities.database.snapshots import (
    SnapshotError,
    create_snapshot,
    load_manifest,
    verify_snapshot,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a consistent database and manifest bundle")
    create.add_argument("--database", type=Path, required=True)
    create.add_argument("--snapshot", type=Path, required=True)
    create.add_argument("--manifest", type=Path, required=True)
    create.add_argument("--key-prefix", required=True)
    create.add_argument("--retention-days", type=int, required=True)
    create.add_argument("--repository", required=True)
    create.add_argument("--run-id", required=True)
    create.add_argument("--run-attempt", type=int, required=True)
    create.add_argument("--previous-manifest", type=Path)
    create.add_argument(
        "--created-at",
        type=datetime.fromisoformat,
        help="Optional timezone-aware ISO timestamp for deterministic testing",
    )

    verify = commands.add_parser("verify", help="Verify a database against its manifest")
    verify.add_argument("--database", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--expected-database-key")
    verify.add_argument("--expected-schema-revision")

    key = commands.add_parser("key", help="Print an immutable key from a manifest")
    key.add_argument("--manifest", type=Path, required=True)
    key.add_argument("--kind", choices=("database", "manifest"), required=True)

    field = commands.add_parser("field", help="Print one publication field from a manifest")
    field.add_argument("--manifest", type=Path, required=True)
    field.add_argument(
        "--name",
        choices=("sha256", "schema-revision", "collection-timestamp", "retain-until"),
        required=True,
    )
    return parser


def _fail(message: str) -> NoReturn:
    sys.stderr.write(f"Canonical snapshot error: {message}\n")
    raise SystemExit(1)


def main() -> int:
    """Execute one snapshot operation."""
    arguments = _parser().parse_args()
    try:
        if arguments.command == "create":
            manifest = create_snapshot(
                arguments.database,
                arguments.snapshot,
                arguments.manifest,
                key_prefix=arguments.key_prefix,
                retention_days=arguments.retention_days,
                repository=arguments.repository,
                run_id=arguments.run_id,
                run_attempt=arguments.run_attempt,
                previous_manifest_path=arguments.previous_manifest,
                created_at=arguments.created_at,
            )
            sys.stdout.write(f"Created snapshot {manifest.database_key} ({manifest.sha256}).\n")
            return 0
        if arguments.command == "verify":
            manifest = verify_snapshot(
                arguments.database,
                arguments.manifest,
                expected_database_key=arguments.expected_database_key,
                expected_schema_revision=arguments.expected_schema_revision,
            )
            sys.stdout.write(
                f"Verified snapshot {manifest.database_key} ({manifest.schema_revision}).\n"
            )
            return 0
        if arguments.command == "key":
            manifest = load_manifest(arguments.manifest)
            value = manifest.database_key if arguments.kind == "database" else manifest.manifest_key
            sys.stdout.write(value + "\n")
            return 0
        if arguments.command == "field":
            manifest = load_manifest(arguments.manifest)
            values = {
                "sha256": manifest.sha256,
                "schema-revision": manifest.schema_revision,
                "collection-timestamp": (
                    manifest.collection_timestamp.isoformat().replace("+00:00", "Z")
                    if manifest.collection_timestamp is not None
                    else "none"
                ),
                "retain-until": manifest.retention.retain_until.isoformat().replace("+00:00", "Z"),
            }
            sys.stdout.write(values[arguments.name] + "\n")
            return 0
    except (OSError, SnapshotError) as exc:
        _fail(str(exc))
    _fail(f"unsupported command: {arguments.command}")


if __name__ == "__main__":
    raise SystemExit(main())
