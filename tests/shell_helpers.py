"""Isolated environments for offline Linux deployment/recovery subprocess tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def offline_shell_environment(tmp_path: Path) -> dict[str, str]:
    """Allow runtime essentials while blocking real SSH/SFTP/SCP behind test fakes."""
    blockers = tmp_path / "blocked-network-bin"
    blockers.mkdir(exist_ok=True)
    for command in ("ssh", "scp", "sftp"):
        executable = blockers / command
        executable.write_text(
            '#!/bin/sh\nprintf "%s\\n" "unexpected transport" >> "$BLOCKED_NETWORK_LOG"\n'
            'echo "Real network transport is disabled in shell tests" >&2\nexit 97\n',
            encoding="utf-8",
        )
        executable.chmod(0o755)
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return {
        **{
            name: os.environ[name]
            for name in ("SYSTEMROOT", "WINDIR", "PATHEXT")
            if name in os.environ
        },
        # Callers prepend fakes; blockers must still precede every host transport binary.
        "PATH": f"{blockers}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(home),
        "TMPDIR": str(tmp_path),
        "RUNNER_TEMP": str(tmp_path),
        "LC_ALL": "C",
        "VIRTUAL_ENV": sys.prefix,
        "UV_PYTHON": sys.executable,
        "UV_NO_SYNC": "1",
        "UV_OFFLINE": "1",
        "BLOCKED_NETWORK_LOG": str(tmp_path / "blocked-network.log"),
    }
