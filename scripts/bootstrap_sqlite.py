"""Stream a consistent SQLite backup of the live VPS database to stdout.
Executed over SSH with this file on stdin; only snapshot bytes go to stdout.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


def main(source_path: Path) -> None:
    """Include committed WAL changes without copying live SQLite sidecars."""
    with tempfile.TemporaryDirectory(prefix="opportunities-bootstrap-") as temporary:
        backup_path = Path(temporary) / "opportunities.db"
        with (
            # Read-only URI mode fails when the legacy database is missing; a
            # plain SQLite connection would silently create an empty source.
            closing(
                sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True)
            ) as source,
            closing(sqlite3.connect(backup_path)) as destination,
        ):
            source.backup(destination)
            # The streamed artifact must be usable as a cold, sidecar-free file.
            if destination.execute("PRAGMA journal_mode=DELETE").fetchone() != ("delete",):
                raise RuntimeError("bootstrap backup could not leave WAL mode")
        with backup_path.open("rb") as backup:
            shutil.copyfileobj(backup, sys.stdout.buffer)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
