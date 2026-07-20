"""Safe filesystem write helpers."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a text file while preserving its permission bits."""
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
