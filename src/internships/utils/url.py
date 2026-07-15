"""Validation and canonicalization for untrusted public URLs."""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETERS = frozenset(
    {
        "fbclid",
        "gclid",
        "originalsubdomain",
        "pagenum",
        "position",
        "ref",
        "referrer",
        "refid",
        "source",
        "trackingid",
        "trk",
    }
)
TRACKING_PREFIXES = ("utm_",)


class UnsafeUrlError(ValueError):
    """Raised when source data contains a URL that is unsafe to publish."""


def _is_public_hostname(hostname: str) -> bool:
    """Check whether a hostname resolves only to public addresses."""
    normalized = hostname.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"} or normalized.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        return "." in normalized
    return address.is_global


def canonicalize_url(url: str, *, extra_tracking_parameters: Iterable[str] = ()) -> str:
    """Validate and canonicalize an HTTP or HTTPS URL."""
    candidate = url.strip()
    if not candidate:
        raise UnsafeUrlError("URL must not be empty")
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeUrlError("only http and https URLs are accepted")
    if not parsed.hostname or not _is_public_hostname(parsed.hostname):
        raise UnsafeUrlError("URL must contain a public hostname")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("URLs containing credentials are not accepted")
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrlError("URL contains an invalid port") from exc

    hostname = parsed.hostname.lower().rstrip(".")
    try:
        hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise UnsafeUrlError("URL contains an invalid hostname") from exc
    if ":" in hostname:
        hostname = f"[{hostname}]"
    default_port = (parsed.scheme.lower() == "https" and port == 443) or (
        parsed.scheme.lower() == "http" and port == 80
    )
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    ignored = TRACKING_PARAMETERS | {item.lower() for item in extra_tracking_parameters}
    query_items = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in ignored
        and not any(key.lower().startswith(prefix) for prefix in TRACKING_PREFIXES)
    ]
    query_items.sort(key=lambda item: (item[0].lower(), item[1]))
    path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, urlencode(query_items), ""))


def urls_equal(left: str, right: str) -> bool:
    """Compare two URLs after canonicalization."""
    try:
        return canonicalize_url(left) == canonicalize_url(right)
    except UnsafeUrlError:
        return False
