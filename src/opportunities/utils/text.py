"""Small, deterministic text-cleaning helpers."""

from __future__ import annotations

import html
import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def clean_text(value: str | None) -> str:
    """Collapse whitespace and decode text safely."""
    if not value:
        return ""
    return _WHITESPACE_RE.sub(" ", html.unescape(value)).strip()


def normalized_key(value: str) -> str:
    """Return a case-folded key for deterministic comparisons."""
    decomposed = unicodedata.normalize("NFKD", clean_text(value)).encode("ascii", "ignore").decode()
    return _NON_WORD_RE.sub(" ", decomposed.lower()).strip()


def contains_normalized_phrase(text: str, phrase: str) -> bool:
    """Return whether one normalized key contains another on word boundaries."""
    return bool(phrase and f" {phrase} " in f" {text} ")
