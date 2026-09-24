"""Offline restore wrapper failure tests using a fake SFTP store and SSH binary."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))
pytestmark = pytest.mark.skipif(os.name != "posix", reason="VPS restore runs on Linux Bash")


def run_restore(
    tmp_path: Path,
    *,
    local: bytes | None,
    snapshot: bool,
    ssh_status: int,
    bootstrap: bytes | None = None,
    dangling_symlink: bool = False,
    use_ssh_override: bool = True,
    home: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "canonical_state_store.sh").write_text(
        '#!/bin/bash\nset -e\nif [ "$FAKE_SNAPSHOT" = yes ]; then '
        'mkdir -p "$CANONICAL_STATE_WORK_DIR"; '
        'printf "manifest" > "$CANONICAL_STATE_WORK_DIR/latest.json"; '
        'printf "invalid snapshot" > "$CANONICAL_STATE_DATABASE"; fi\n',
        encoding="utf-8",
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "ssh").write_text('#!/bin/bash\nexit "$FAKE_SSH_STATUS"\n', encoding="utf-8")
    (fake_bin / "ssh").chmod(0o755)
    database = tmp_path / "state/opportunities.db"
    database.parent.mkdir()
    if local is not None:
        database.write_bytes(local)
    if dangling_symlink:
        database.symlink_to("missing-canonical-state.db")
    if bootstrap is not None:
        (tmp_path / "state/opportunities.db.bootstrap-123").write_bytes(bootstrap)
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "VPS_BACKUP_SSH_PRIVATE_KEY": "test-placeholder",
        "VPS_SSH_KNOWN_HOSTS": "test-placeholder",
        "VPS_BACKUP_HOST": "test.invalid",
        "VPS_HOST": "test.invalid",
        "VPS_USER": "test-user",
        "VPS_SSH_PRIVATE_KEY": "test-placeholder",
        "CANONICAL_STATE_DATABASE": str(database),
        "CANONICAL_STATE_WORK_DIR": str(tmp_path / "snapshot-work"),
        "FAKE_SNAPSHOT": "yes" if snapshot else "no",
        "FAKE_SSH_STATUS": str(ssh_status),
        "GITHUB_RUN_ID": "123",
        "PYTHONPATH": str(ROOT / "src"),
    }
    env.pop("CANONICAL_STATE_SSH_DIR", None)
    if use_ssh_override:
        env["CANONICAL_STATE_SSH_DIR"] = str(tmp_path / "ssh-credentials")
    if home is not None:
        env["HOME"] = str(home)
    return subprocess.run(
        ["bash", str(ROOT / "scripts/restore_canonical_state.sh")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_unreferenced_local_state_is_preserved_without_snapshot(tmp_path: Path) -> None:
    local = b"corrupt"
    result = run_restore(tmp_path, local=local, snapshot=False, ssh_status=0)
    assert result.returncode != 0
    assert "Local state without a durable snapshot" in result.stderr
    assert (tmp_path / "state/opportunities.db").read_bytes() == local


def test_unreferenced_dangling_symlink_is_preserved_without_snapshot(tmp_path: Path) -> None:
    result = run_restore(tmp_path, local=None, snapshot=False, ssh_status=0, dangling_symlink=True)
    database = tmp_path / "state/opportunities.db"
    assert result.returncode != 0
    assert "Local state without a durable snapshot" in result.stderr
    assert database.is_symlink()
    assert database.readlink() == Path("missing-canonical-state.db")


def test_default_ssh_directory_preserves_existing_home_credentials(tmp_path: Path) -> None:
    home = tmp_path / "home"
    ssh = home / ".ssh"
    ssh.mkdir(parents=True)
    credentials = {
        "id_backup_ed25519": b"existing backup key",
        "id_ed25519": b"existing deployment key",
        "known_hosts": b"existing hosts",
    }
    for name, content in credentials.items():
        (ssh / name).write_bytes(content)

    result = run_restore(
        tmp_path,
        local=b"unreferenced local state",
        snapshot=False,
        ssh_status=0,
        use_ssh_override=False,
        home=home,
    )
    assert result.returncode != 0
    for name, content in credentials.items():
        assert (ssh / name).read_bytes() == content


def test_preexisting_bootstrap_candidate_is_not_deleted(tmp_path: Path) -> None:
    result = run_restore(
        tmp_path, local=None, snapshot=False, ssh_status=0, bootstrap=b"previous candidate"
    )
    assert result.returncode != 0
    assert "Bootstrap staging already exists" in result.stderr
    assert (tmp_path / "state/opportunities.db.bootstrap-123").read_bytes() == b"previous candidate"


def test_invalid_restored_candidate_stops_without_bootstrap(tmp_path: Path) -> None:
    result = run_restore(tmp_path, local=None, snapshot=True, ssh_status=0)
    assert result.returncode != 0
    assert "invalid" in result.stderr.lower()
    assert (tmp_path / "state/opportunities.db").read_bytes() == b"invalid snapshot"


def test_no_snapshot_and_no_local_state_must_pass_legacy_guard(tmp_path: Path) -> None:
    # An existing release pointer or SSH failure prevents fallback to stale fixed paths.
    result = run_restore(tmp_path, local=None, snapshot=False, ssh_status=1)
    assert result.returncode != 0
    assert "Cannot bootstrap from legacy state" in result.stderr
    assert not (tmp_path / "state/opportunities.db").exists()


def test_snapshot_store_preserves_a_mismatched_local_database(tmp_path: Path) -> None:
    database = tmp_path / "opportunities.db"
    database.write_bytes(b"unsnapshotted canonical state")
    key = tmp_path / "key"
    hosts = tmp_path / "known_hosts"
    key.write_text("placeholder", encoding="utf-8")
    hosts.write_text("placeholder", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name, content in {
        "sftp": (
            "#!/bin/bash\nwhile IFS= read -r line; do\n"
            '  printf "%s\\n" "$line" >> "$FAKE_SFTP_LOG"\n'
            '  if [[ "$line" == *latest.json* ]]; then\n'
            '    printf "snapshot manifest\\n" > "$CANONICAL_STATE_WORK_DIR/latest.json"\n'
            "  fi\ndone\n"
        ),
        "uv": (
            '#!/bin/bash\nif [[ " $* " == *" key "* ]]; then\n'
            '  printf "canonical-state/snapshots/2026/test.db\\n"\n'
            "else\n  exit 1\nfi\n"
        ),
    }.items():
        executable = fake_bin / name
        executable.write_text(content, encoding="utf-8")
        executable.chmod(0o755)
    log = tmp_path / "sftp.log"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/canonical_state_store.sh"), "restore"],
        cwd=ROOT,
        env={
            **os.environ,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            "VPS_BACKUP_HOST": "test.invalid",
            "VPS_BACKUP_SSH_KEY": str(key),
            "VPS_BACKUP_KNOWN_HOSTS": str(hosts),
            "CANONICAL_STATE_DATABASE": str(database),
            "CANONICAL_STATE_WORK_DIR": str(tmp_path / "work"),
            "FAKE_SFTP_LOG": str(log),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "preserve" in result.stderr.lower()
    assert database.read_bytes() == b"unsnapshotted canonical state"
    assert "test.db" not in log.read_text(encoding="utf-8")


@pytest.mark.parametrize("operation", ["restore", "publish"])
def test_snapshot_store_rejects_sidecars_before_transfer(tmp_path: Path, operation: str) -> None:
    database = tmp_path / "opportunities.db"
    sidecar = tmp_path / "opportunities.db-wal"
    database.write_bytes(b"untouched")
    sidecar.write_bytes(b"committed WAL must not be lost")
    key = tmp_path / "key"
    hosts = tmp_path / "known_hosts"
    key.write_text("placeholder", encoding="utf-8")
    hosts.write_text("placeholder", encoding="utf-8")
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    sftp = fake_bin / "sftp"
    sftp.write_text('#!/bin/sh\nprintf called > "$FAKE_SFTP_LOG"\nexit 9\n', encoding="utf-8")
    sftp.chmod(0o755)
    sftp_log = tmp_path / "sftp-called"
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/canonical_state_store.sh"), operation],
        cwd=ROOT,
        env={
            **os.environ,
            "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_SFTP_LOG": str(sftp_log),
            "VPS_BACKUP_HOST": "test.invalid",
            "VPS_BACKUP_SSH_KEY": str(key),
            "VPS_BACKUP_KNOWN_HOSTS": str(hosts),
            "CANONICAL_STATE_DATABASE": str(database),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "sidecar exists" in result.stderr
    assert database.read_bytes() == b"untouched"
    assert sidecar.read_bytes() == b"committed WAL must not be lost"
    assert not sftp_log.exists()
