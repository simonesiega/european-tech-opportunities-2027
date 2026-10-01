"""Offline client-side deployment preflight and interrupted-upload tests."""

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
    sys.platform != "linux", reason="the VPS deployment client runs on Linux"
)


def run_deploy(
    tmp_path: Path,
    *,
    fake_transport: bool = False,
    fail_validation: bool = False,
    validation_sidecar: bool = False,
    use_ssh_override: bool = True,
    home: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {
        **offline_shell_environment(tmp_path),
        "VPS_SSH_PRIVATE_KEY": "placeholder",
        "VPS_SSH_KNOWN_HOSTS": "placeholder",
        "VPS_HOST": "test.invalid",
        "VPS_USER": "testuser",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    env.pop("CANONICAL_STATE_SSH_DIR", None)
    if use_ssh_override:
        env["CANONICAL_STATE_SSH_DIR"] = str(tmp_path / "ssh")
    if home is not None:
        env["HOME"] = str(home)
    if fake_transport or fail_validation or validation_sidecar:
        binaries = tmp_path / "bin"
        binaries.mkdir()
        sidecar = "echo uncheckpointed > data/opportunities.db-wal\n" if validation_sidecar else ""
        (binaries / "uv").write_text(
            f"#!/bin/sh\n{sidecar}exit {1 if fail_validation else 0}\n", encoding="utf-8"
        )
        (binaries / "uv").chmod(0o755)
        env["PATH"] = f"{binaries}{os.pathsep}{env['PATH']}"
    if fake_transport:
        (binaries / "ssh").write_text(
            '#!/bin/sh\nprintf "%s\\n" ssh >> "$DEPLOY_CALLS"\nexit 0\n', encoding="utf-8"
        )
        (binaries / "scp").write_text(
            '#!/bin/sh\nprintf "%s\\n" scp >> "$DEPLOY_CALLS"\nexit 9\n', encoding="utf-8"
        )
        for command in ("ssh", "scp"):
            (binaries / command).chmod(0o755)
        env["DEPLOY_CALLS"] = str(tmp_path / "calls")
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/deployment/deploy_canonical_state.sh")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert not (tmp_path / "blocked-network.log").exists(), result.stderr
    return result


def prepare(tmp_path: Path) -> None:
    exports = tmp_path / "data/exports"
    exports.mkdir(parents=True)
    (tmp_path / "data/opportunities.db").write_bytes(b"synthetic local db")
    (exports / "open-opportunities.csv").write_text("id\n", encoding="utf-8")
    (exports / "open-opportunities.json").write_text("[]\n", encoding="utf-8")
    (exports / "dataset-metadata.json").write_text('{"total": 0}\n', encoding="utf-8")


@pytest.mark.parametrize(
    "missing_file",
    [
        "data/opportunities.db",
        "data/exports/open-opportunities.csv",
        "data/exports/open-opportunities.json",
        "data/exports/dataset-metadata.json",
    ],
)
def test_missing_local_file_fails_before_network(tmp_path: Path, missing_file: str) -> None:
    prepare(tmp_path)
    (tmp_path / missing_file).unlink()
    result = run_deploy(tmp_path)
    assert result.returncode != 0
    assert "missing or empty" in result.stderr
    assert not (tmp_path / "ssh").exists()


def test_stale_bundle_fails_validation_before_network(tmp_path: Path) -> None:
    prepare(tmp_path)
    result = run_deploy(tmp_path, fail_validation=True)
    assert result.returncode != 0
    assert not (tmp_path / "ssh").exists()


def test_validation_creating_wal_fails_before_network(tmp_path: Path) -> None:
    prepare(tmp_path)
    result = run_deploy(tmp_path, validation_sidecar=True)
    assert result.returncode != 0
    assert "Checkpoint" in result.stderr
    assert (tmp_path / "data/opportunities.db-wal").is_file()
    assert not (tmp_path / "ssh").exists()


def test_local_wal_fails_without_removing_sidecar(tmp_path: Path) -> None:
    prepare(tmp_path)
    wal = tmp_path / "data/opportunities.db-wal"
    wal.write_bytes(b"do not discard")
    result = run_deploy(tmp_path)
    assert result.returncode != 0
    assert "Checkpoint" in result.stderr
    assert wal.read_bytes() == b"do not discard"
    assert not (tmp_path / "ssh").exists()


def test_partial_upload_aborts_and_requests_staging_cleanup(tmp_path: Path) -> None:
    prepare(tmp_path)
    result = run_deploy(tmp_path, fake_transport=True)
    assert result.returncode != 0
    assert (tmp_path / "calls").read_text(encoding="utf-8").splitlines() == ["ssh", "scp", "ssh"]
    assert not (tmp_path / "ssh/id_ed25519").exists()
    assert not (tmp_path / "ssh/known_hosts").exists()
    assert (tmp_path / "data/opportunities.db").read_bytes() == b"synthetic local db"


def test_default_ssh_directory_preserves_existing_home_credentials(tmp_path: Path) -> None:
    prepare(tmp_path)
    home = tmp_path / "home"
    ssh = home / ".ssh"
    ssh.mkdir(parents=True)
    credentials = {
        "id_ed25519": b"existing deployment key",
        "known_hosts": b"existing hosts",
    }
    for name, content in credentials.items():
        (ssh / name).write_bytes(content)

    result = run_deploy(tmp_path, fake_transport=True, use_ssh_override=False, home=home)
    assert result.returncode != 0
    for name, content in credentials.items():
        assert (ssh / name).read_bytes() == content
