"""Minimal structured logging without an additional runtime dependency."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

_SAFE_EXTRA_FIELDS = frozenset({"attempt", "delay_seconds", "error_code"})


class JsonFormatter(logging.Formatter):
    """Format one-line JSON with only explicitly approved structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format one log record as compact JSON."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _SAFE_EXTRA_FIELDS:
            if key in record.__dict__:
                payload[key] = record.__dict__[key]
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str, ensure_ascii=False, sort_keys=True)


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    """Configure application logging."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter() if json_output else logging.Formatter("%(levelname)s %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
