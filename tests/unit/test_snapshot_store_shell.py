"""Prove SFTP absence checks cannot turn failed access into bootstrap permission."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from opportunities.utils.paths import find_project_root
from tests.shell_helpers import offline_shell_environment

ROOT = find_project_root(Path(__file__))
pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="VPS snapshot storage runs on Linux Bash"
)


@pytest.mark.parametrize(
    ("mode", "success"),
    [
        ("missing-store", True),
        ("empty-store", True),
        ("root-listing-failure", False),
        ("store-listing-failure", False),
        ("store-not-directory", False),
        ("download-failure", False),
        ("empty-manifest", False),
        ("missing-pointer", False),
    ],
)
def test_snapshot_absence_requires_successful_listing(
    tmp_path: Path, mode: str, success: bool
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    sftp = fake_bin / "sftp"
    sftp.write_text(
        """#!/bin/bash
set -eu
while IFS= read -r line; do
  printf '%s\n' "$line" >> "$FAKE_SFTP_LOG"
  case "$line" in
    'cd "/state"') ;;
    'cd "/state/canonical-state"')
      [[ "$FAKE_MODE" != store-not-directory ]] || exit 1
      ;;
    'ls -1 "/state"')
      [[ "$FAKE_MODE" != root-listing-failure ]] || exit 1
      if [[ "$FAKE_MODE" != missing-store ]]; then
        printf '/state/canonical-state\n'
      fi
      ;;
    'ls -1 "/state/canonical-state"')
      [[ "$FAKE_MODE" != store-listing-failure ]] || exit 1
      if [[ "$FAKE_MODE" == missing-pointer ]]; then
        printf '/state/canonical-state/snapshots\n'
      elif [[ "$FAKE_MODE" != empty-store ]]; then
        printf '/state/canonical-state/latest.json\n'
      fi
      ;;
    'get '*latest.json*)
      [[ "$FAKE_MODE" != download-failure ]] || exit 1
      : > "$CANONICAL_STATE_WORK_DIR/latest.json"
      ;;
    *) exit 9 ;;
  esac
done
""",
        encoding="utf-8",
    )
    sftp.chmod(0o755)
    # No snapshot verification is expected for any of these failure/absence cases.
    uv = fake_bin / "uv"
    uv.write_text("#!/bin/bash\nexit 9\n", encoding="utf-8")
    uv.chmod(0o755)
    key = tmp_path / "key"
    hosts = tmp_path / "known_hosts"
    key.write_text("placeholder", encoding="utf-8")
    hosts.write_text("placeholder", encoding="utf-8")
    database = tmp_path / "opportunities.db"
    log = tmp_path / "sftp.log"
    base_environment = offline_shell_environment(tmp_path)
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/database/canonical_state_store.sh"), "restore"],
        cwd=tmp_path,
        env={
            **base_environment,
            "PATH": f"{fake_bin}{os.pathsep}{base_environment['PATH']}",
            "VPS_BACKUP_HOST": "test.invalid",
            "VPS_BACKUP_SSH_KEY": str(key),
            "VPS_BACKUP_KNOWN_HOSTS": str(hosts),
            "VPS_BACKUP_REMOTE_ROOT": "/state",
            "CANONICAL_STATE_PREFIX": "canonical-state",
            "CANONICAL_STATE_DATABASE": str(database),
            "CANONICAL_STATE_WORK_DIR": str(tmp_path / "work"),
            "FAKE_MODE": mode,
            "FAKE_SFTP_LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert not (tmp_path / "blocked-network.log").exists(), result.stderr
    assert (result.returncode == 0) is success
    assert ("No VPS canonical snapshot exists yet" in result.stdout) is success
    assert not database.exists()
    assert "-get" not in log.read_text(encoding="utf-8")
