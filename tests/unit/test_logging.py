from __future__ import annotations

import json
import logging
import sys

from opportunities.utils.logging import JsonFormatter


def test_json_formatter_emits_only_approved_structured_fields() -> None:
    record = logging.LogRecord(
        name="opportunities.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=10,
        msg="retrying request",
        args=(),
        exc_info=None,
    )
    record.__dict__.update(
        error_code="timeout",
        attempt=2,
        response_body="must not be logged",
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "retrying request"
    assert payload["error_code"] == "timeout"
    assert payload["attempt"] == 2
    assert "response_body" not in payload


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

    assert payload["exception_type"] == "RuntimeError"
    assert "sensitive exception detail" not in json.dumps(payload)
