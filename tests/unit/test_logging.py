from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime

from opportunities.utils.logging import JsonFormatter


def test_json_formatter_emits_only_approved_structured_fields() -> None:
    record = logging.LogRecord(
        name="opportunities.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=10,
        msg="retrying request %s",
        args=("synthetic",),
        exc_info=None,
    )
    record.__dict__.update(
        error_code="timeout",
        attempt=2,
        delay_seconds=0.5,
        response_body="must not be logged",
        headers={"private": "must not be logged"},
        unexpected="must not be logged",
    )

    payload = json.loads(JsonFormatter().format(record))

    assert datetime.fromisoformat(payload.pop("timestamp")).tzinfo is UTC
    assert payload == {
        "level": "warning",
        "logger": "opportunities.test",
        "message": "retrying request synthetic",
        "error_code": "timeout",
        "attempt": 2,
        "delay_seconds": 0.5,
    }


def test_json_formatter_does_not_emit_exception_messages_or_tracebacks() -> None:
    try:
        raise RuntimeError("sensitive exception detail")
    except RuntimeError:
        record = logging.LogRecord(
            name="opportunities.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=30,
            msg="operation failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(JsonFormatter().format(record))

    assert datetime.fromisoformat(payload.pop("timestamp")).tzinfo is UTC
    assert payload == {
        "level": "error",
        "logger": "opportunities.test",
        "message": "operation failed",
        "exception_type": "RuntimeError",
    }
