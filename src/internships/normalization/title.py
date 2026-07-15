"""Conservative LinkedIn title normalization."""

from __future__ import annotations

import re

from internships.utils.text import clean_text


def normalize_title(value: str) -> str:
    """Normalize job titles for matching."""
    title = clean_text(value).strip("-\u2013\u2014| ")
    return re.sub(r"\s+[-\u2013\u2014|]\s+Apply(?: Now)?$", "", title, flags=re.IGNORECASE)
