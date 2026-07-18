"""Fixed publication-policy boundaries shared across pipeline stages."""

from datetime import UTC, datetime

MINIMUM_POSTED_AT = datetime(2026, 5, 1, tzinfo=UTC)
