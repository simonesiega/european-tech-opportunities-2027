"""Exercise publication reconciliation through a filesystem-backed SFTP fake."""

import subprocess
import sys
from pathlib import Path

import pytest

from opportunities.utils.paths import find_project_root

ROOT = find_project_root(Path(__file__))


@pytest.mark.parametrize(
    "failure",
    [
        "none",
        "before-put",
        "partial-put",
        "after-put",
        "after-rename",
        "get",
        "always",
        "permission",
        "conflict",
        "staging-conflict",
        "changed-pointer",
    ],
)
@pytest.mark.parametrize("mutable", [False, True])
def test_publication_reconciles_transport(tmp_path: Path, failure: str, mutable: bool) -> None:
    source = tmp_path / "source"
    source.write_text("synthetic snapshot bytes")
    previous = tmp_path / "previous"
    previous.write_text("unexpected")
    remote = tmp_path / "remote"
    remote.mkdir()
    if failure == "conflict":
        (remote / "final").write_text("unexpected")
    if failure == "changed-pointer":
        (remote / "final").write_text("newer pointer")
    if failure == "staging-conflict":
        (remote / "final.upload-1-1").write_text("unexpected")
    fake = tmp_path / "fake.py"
    fake.write_text("""import os, pathlib, shlex, sys
root = pathlib.Path(sys.argv[1]); mode = sys.argv[2]
command = shlex.split(sys.stdin.read()); op = command[0]
log = root / 'log'
with log.open('a') as f: f.write(op + '\\n')
marker = root / 'failed'
def fail():
    marker.touch(); print('Connection closed', file=sys.stderr); sys.exit(255)
if mode == 'always': fail()
if mode == 'permission':
    print('Permission denied', file=sys.stderr); sys.exit(255)
if op == 'ls':
    for p in root.iterdir(): print('/state/' + p.name)
elif op == 'get':
    if mode == 'get' and not marker.exists(): fail()
    pathlib.Path(command[2]).write_bytes((root / pathlib.Path(command[1]).name).read_bytes())
elif op == 'put':
    data = pathlib.Path(command[1]).read_bytes()
    dest = root / pathlib.Path(command[2]).name
    if mode == 'before-put' and not marker.exists(): fail()
    if mode == 'partial-put' and not marker.exists():
        dest.write_bytes(data[:5]); fail()
    dest.write_bytes(data)
    if mode == 'after-put' and not marker.exists(): fail()
elif op == 'rename':
    (root / pathlib.Path(command[1]).name).replace(root / pathlib.Path(command[2]).name)
    if mode == 'after-rename' and not marker.exists(): fail()
else: sys.exit(1)
""")
    script = f'''set -euo pipefail
work_dir="{tmp_path.as_posix()}"
VPS_BACKUP_REMOTE_ROOT=/state
raw_sftp() {{
  "{Path(sys.executable).as_posix()}" "{fake.as_posix()}" "{remote.as_posix()}" "{failure}"
}}
sleep() {{ :; }}
source "{(ROOT / "scripts/database/sftp_publication.sh").as_posix()}"
local_source="{source.as_posix()}"
previous="{previous.as_posix()}"
mutable={str(mutable).lower()}
publication_file "$local_source" /state/final /state/final.upload-1-1 "$mutable" "$previous"
publication_file "$local_source" /state/final /state/final.upload-1-1 "$mutable" "$previous"
'''
    bash = (
        Path("C:/Program Files/Git/bin/bash.exe") if sys.platform == "win32" else Path("/bin/bash")
    )
    if not bash.exists():
        pytest.skip("Bash is unavailable")
    result = subprocess.run([str(bash), "-c", script], capture_output=True, text=True, timeout=30)
    success = failure not in {"always", "permission", "staging-conflict", "changed-pointer"} and (
        failure != "conflict" or mutable
    )
    assert (result.returncode == 0) == success, result.stderr
    operations = (remote / "log").read_text().splitlines()
    if success:
        assert (remote / "final").read_bytes() == source.read_bytes()
        assert operations.count("rename") == 1
    if failure == "always":
        assert len(operations) == 3
    if failure == "permission":
        assert len(operations) == 1
    if failure in {"staging-conflict", "changed-pointer"} or (
        failure == "conflict" and not mutable
    ):
        assert "put" not in operations
        assert "rename" not in operations


@pytest.mark.parametrize("gate", ["success", "checksum", "stats"])
def test_latest_requires_round_trip_validation(tmp_path: Path, gate: str) -> None:
    store = (ROOT / "scripts/database/canonical_state_store.sh").read_text()
    publish = store[
        store.index("publish_state() {") : store.rindex('if [[ "$operation" == "restore" ]]; then')
    ]
    work = tmp_path / "work"
    bundle = work / "publish"
    bundle.mkdir(parents=True)
    database = tmp_path / "canonical.db"
    database.write_text("synthetic")
    (bundle / "opportunities.snapshot.db").write_bytes(database.read_bytes())
    (bundle / "manifest.json").write_text("synthetic manifest")
    script = f'''set -euo pipefail
work_dir="{work.as_posix()}"
CANONICAL_STATE_DATABASE="{database.as_posix()}"
GITHUB_REPOSITORY=test/repo
GITHUB_RUN_ID=1
GITHUB_RUN_ATTEMPT=1
CANONICAL_STATE_PREFIX=canonical-state
VPS_BACKUP_REMOTE_ROOT=/state
remote_latest=/state/canonical-state/latest.json
latest_manifest="$work_dir/latest.json"
reject_sidecars() {{ :; }}
set_output() {{ :; }}
publication_directories() {{ :; }}
publication_file() {{ echo "promote $2"; }}
publication_download() {{
  case "$1" in
    *.db) cp "$work_dir/publish/opportunities.snapshot.db" "$2" ;;
    *) cp "$work_dir/publish/manifest.json" "$2" ;;
  esac
}}
snapshot_tool() {{
  if [[ "$1" == key ]]; then
    if [[ "$5" == database ]]; then
      echo canonical-state/snapshots/test-run-1-attempt-1.db
    else
      echo canonical-state/snapshots/test-run-1-attempt-1.manifest.json
    fi
  elif [[ "{gate}" == checksum && "$*" == *restore-verification* ]]; then
    echo checksum-failed >&2
    return 1
  fi
}}
uv() {{ [[ "{gate}" != stats ]]; }}
{publish}
publish_state
'''
    bash = (
        Path("C:/Program Files/Git/bin/bash.exe") if sys.platform == "win32" else Path("/bin/bash")
    )
    if not bash.exists():
        pytest.skip("Bash is unavailable")
    result = subprocess.run([str(bash), "-c", script], capture_output=True, text=True, timeout=30)
    assert (result.returncode == 0) == (gate == "success"), result.stderr
    assert ("promote /state/canonical-state/latest.json" in result.stdout) == (gate == "success")
    assert "retry" not in result.stderr
