"""Offline Linux tests for the VPS-side locked release cutover; no SSH or live state."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import pytest

from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))
SCRIPT = ROOT / "scripts/activate_canonical_release.sh"
pytestmark = pytest.mark.skipif(
    os.name != "posix" or shutil.which("flock") is None,
    reason="the VPS release activation requires Linux flock",
)


def stage(root: Path, release_id: str, company: str) -> dict[str, str]:
    directory = root / ".incoming" / release_id
    (directory / "exports").mkdir(parents=True)
    with closing(sqlite3.connect(directory / "opportunities.db")) as database, database:
        database.execute("CREATE TABLE listing (company TEXT)")
        database.execute("INSERT INTO listing VALUES (?)", (company,))
    (directory / "exports/open-opportunities.csv").write_text(company + "\n", encoding="utf-8")
    (directory / "exports/open-opportunities.json").write_text(
        '["' + company + '"]\n', encoding="utf-8"
    )
    files = [
        directory / "opportunities.db",
        directory / "exports/open-opportunities.csv",
        directory / "exports/open-opportunities.json",
    ]
    hashes = [hashlib.sha256(file.read_bytes()).hexdigest() for file in files]
    return {
        "RELEASE_DATA_DIR": str(root),
        "RELEASE_ID": release_id,
        "RELEASE_GROUP": subprocess.check_output(["id", "-gn"], text=True).strip(),
        "DATABASE_SHA": hashes[0],
        "CSV_SHA": hashes[1],
        "JSON_SHA": hashes[2],
    }


def activate(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={**os.environ, **env},
        text=True,
        capture_output=True,
        check=False,
    )


def test_single_cutover_retains_active_reader_and_legacy_paths(tmp_path: Path) -> None:
    legacy = tmp_path / "opportunities.db"
    legacy.write_bytes(b"unchanged legacy state")
    first = stage(tmp_path, "1-1", "old")
    assert activate(first).returncode == 0
    with closing(sqlite3.connect(tmp_path / "current/opportunities.db")) as reader:
        assert reader.execute("SELECT company FROM listing").fetchone() == ("old",)
        second = stage(tmp_path, "2-1", "new")
        assert activate(second).returncode == 0
        assert reader.execute("SELECT company FROM listing").fetchone() == ("old",)
    with closing(sqlite3.connect(tmp_path / "current/opportunities.db")) as reader:
        assert reader.execute("SELECT company FROM listing").fetchone() == ("new",)
    assert (tmp_path / "current").readlink() == Path("releases/2-1")
    assert (tmp_path / "releases/1-1/exports/open-opportunities.csv").read_text() == "old\n"
    subprocess.run(
        ["sha256sum", "-c", "checksums.sha256"],
        cwd=tmp_path / "releases/1-1",
        capture_output=True,
        check=True,
    )
    assert legacy.read_bytes() == b"unchanged legacy state"
    assert (tmp_path / "releases/2-1/opportunities.db").stat().st_mode & 0o777 == 0o440


@pytest.mark.parametrize("defect", ["missing", "checksum", "sidecar", "pointer", "duplicate"])
def test_failure_preserves_active_release(tmp_path: Path, defect: str) -> None:
    assert activate(stage(tmp_path, "1-1", "old")).returncode == 0
    second = stage(tmp_path, "2-1", "new")
    staged = tmp_path / ".incoming/2-1"
    if defect == "missing":
        (staged / "exports/open-opportunities.json").unlink()
    elif defect == "checksum":
        (staged / "exports/open-opportunities.csv").write_text("corrupt\n")
    elif defect == "sidecar":
        (staged / "opportunities.db-wal").write_bytes(b"uncheckpointed")
    elif defect == "pointer":
        (tmp_path / "current").unlink()
        (tmp_path / "current").symlink_to("../elsewhere")
    else:
        second["RELEASE_ID"] = "1-1"
    result = activate(second)
    assert result.returncode != 0
    assert not (tmp_path / "releases/2-1").exists()
    if defect != "pointer":
        assert (tmp_path / "current").readlink() == Path("releases/1-1")


def test_lock_contention_and_interrupted_pointer_promotion(tmp_path: Path) -> None:
    assert activate(stage(tmp_path, "1-1", "old")).returncode == 0
    second = stage(tmp_path, "2-1", "new")
    with subprocess.Popen(
        ["flock", "-x", str(tmp_path / ".release-deploy.lock"), "sleep", "3"]
    ) as holder:
        import time

        time.sleep(0.2)
        assert holder.poll() is None
        assert activate(second).returncode != 0
    assert (tmp_path / "current").readlink() == Path("releases/1-1")

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_mv = fake_bin / "mv"
    fake_mv.write_text(
        '#!/bin/sh\nif [ "$1" = \'-Tf\' ]; then exit 9; fi\nexec /usr/bin/mv "$@"\n',
        encoding="utf-8",
    )
    fake_mv.chmod(0o755)
    result = activate({**second, "PATH": f"{fake_bin}:{os.environ['PATH']}"})
    assert result.returncode != 0
    assert (tmp_path / "current").readlink() == Path("releases/1-1")
    assert (tmp_path / "releases/2-1/opportunities.db").exists()
    assert not (tmp_path / ".current-2-1").exists()
