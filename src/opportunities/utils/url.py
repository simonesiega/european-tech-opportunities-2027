"""Validation and canonicalization for untrusted public URLs."""

from __future__ import annotations

import ipaddress
import re
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
_DNS_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_LINKEDIN_JOB_HOST = "www.linkedin.com"


class UnsafeUrlError(ValueError):
    """Raised when source data contains a URL that is unsafe to publish."""


def _is_public_hostname(hostname: str) -> bool:
    """Check whether a hostname is a syntactically valid public DNS name or IP address."""
    normalized = hostname.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"} or normalized.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        try:
            ascii_hostname = normalized.encode("idna").decode("ascii")
        except UnicodeError:
            return False
        labels = ascii_hostname.split(".")
        return (
            len(ascii_hostname) <= 253
            and len(labels) >= 2
            and all(_DNS_LABEL_RE.fullmatch(label) for label in labels)
        )
    return address.is_global


def canonicalize_url(url: str, *, extra_tracking_parameters: Iterable[str] = ()) -> str:
    """Validate and canonicalize a public HTTPS URL."""
    candidate = url.strip()
    if not candidate:
        raise UnsafeUrlError("URL must not be empty")
    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise UnsafeUrlError("URL is malformed") from exc
    if parsed.scheme.lower() != "https":
        raise UnsafeUrlError("only HTTPS URLs are accepted")
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
    default_port = port == 443
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


def validate_linkedin_job_url(url: str, job_id: str) -> str:
    """Require a canonical LinkedIn public-job URL matching its numeric identity."""
    canonical = canonicalize_url(url)
    parsed = urlsplit(canonical)
    expected_path = f"/jobs/view/{job_id}"
    if (
        parsed.hostname != _LINKEDIN_JOB_HOST
        or parsed.port is not None
        or parsed.path != expected_path
        or parsed.query
    ):
        raise UnsafeUrlError("listing URL does not match its LinkedIn job identity")
    return canonical
