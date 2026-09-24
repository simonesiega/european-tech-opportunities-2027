"""Bounded, rate-limited HTTP transport for public LinkedIn HTML pages."""

from __future__ import annotations

import asyncio
import codecs
import logging
import math
import re
import time
from collections.abc import Awaitable, Callable
from email.utils import parsedate_to_datetime
from http.cookiejar import CookieJar, DefaultCookiePolicy
from urllib.parse import urlsplit

import httpx

from opportunities.config.settings import Settings
from opportunities.utils.time import utc_now

logger = logging.getLogger(__name__)
Sleep = Callable[[float], Awaitable[None]]
LINKEDIN_SEARCH_ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LINKEDIN_DETAIL_ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
LINKEDIN_PUBLIC_JOB_URL = "https://www.linkedin.com/jobs/view/{job_id}"
_LINKEDIN_HOST = "www.linkedin.com"
_LINKEDIN_DETAIL_PATH_RE = re.compile(r"^/jobs-guest/jobs/api/jobPosting/[0-9]{1,30}$")
_LINKEDIN_PUBLIC_PATH_RE = re.compile(r"^/jobs/view/[0-9]{1,30}$")
_MAX_RETRY_DELAY_SECONDS = 60.0
_BLOCK_MARKERS = (
    "captcha-internal",
    "challenge-page",
    "security verification",
    "unusual activity",
)


def is_linkedin_access_challenge(html: str) -> bool:
    """Recognize a known LinkedIn access or verification document."""
    normalized = html.casefold()
    return any(marker in normalized for marker in _BLOCK_MARKERS)


class FetchError(RuntimeError):
    """A sanitized network or response-validation failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        """Carry a sanitized failure code and optional HTTP status."""
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after_seconds = retry_after_seconds


class HttpFetcher:
    """Fetch public HTML with retries, host pacing, and response-size limits."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        """Create a bounded source client or reuse an injected offline client."""
        self.settings = settings
        self._sleep = sleep
        self._owns_client = client is None
        timeout = httpx.Timeout(
            settings.request_timeout_seconds, connect=settings.connect_timeout_seconds
        )
        limits = httpx.Limits(
            max_connections=settings.max_concurrency,
            max_keepalive_connections=settings.max_concurrency,
        )
        # Ambient proxy variables must not change the approved source route.
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            trust_env=False,
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-GB,en;q=0.8",
            },
        )
        if "cookie" in self._client.headers:
            raise ValueError("LinkedIn client must not have a Cookie header")
        # HTTPX otherwise retains Set-Cookie values and sends them on later guest
        # requests. Reject cookies at the jar so concurrent responses cannot race a
        # post-response clear; apply this to injected offline clients as well.
        self._client.cookies = CookieJar(policy=DefaultCookiePolicy(allowed_domains=[]))
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}
        self._blocked_status: int | None = None
        self._blocked_challenge = False

    async def __aenter__(self) -> HttpFetcher:
        """Open the asynchronous HTTP client context."""
        return self

    async def __aexit__(self, *_args: object) -> None:
        """Close the asynchronous HTTP client context."""
        if self._owns_client:
            await self._client.aclose()

    async def get_text(self, url: str) -> str:
        """Fetch approved LinkedIn HTML with bounded transient retries."""
        try:
            parsed = urlsplit(url)
            port = parsed.port
        except ValueError as exc:
            raise FetchError("invalid_url", "LinkedIn request URL is malformed") from exc
        hostname = (parsed.hostname or "").casefold().rstrip(".")
        if (
            parsed.scheme.casefold() != "https"
            or hostname != _LINKEDIN_HOST
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 443}
            or parsed.fragment
            or not _is_approved_path(parsed.path, parsed.query)
        ):
            raise FetchError(
                "invalid_url",
                "request URL is not an approved LinkedIn HTTPS endpoint",
            )
        # Enforce authorization before creating any network traffic, including retries.
        if not self.settings.linkedin_crawl_authorized:
            raise FetchError(
                "crawl_not_authorized",
                "LinkedIn crawling is disabled until express permission is configured",
            )
        attempt = 0
        while True:
            self._raise_if_blocked()
            try:
                return await self._request_once(url)
            except FetchError as exc:
                if not exc.retryable or attempt >= self.settings.max_retries:
                    raise
                self._raise_if_blocked()
                backoff = self.settings.retry_backoff_seconds * (2**attempt)
                delay = min(
                    max(backoff, exc.retry_after_seconds or 0.0),
                    _MAX_RETRY_DELAY_SECONDS,
                )
                logger.warning(
                    "retrying LinkedIn request",
                    extra={
                        "error_code": exc.code,
                        "attempt": attempt + 1,
                        "delay_seconds": delay,
                    },
                )
                await self._sleep(delay)
                attempt += 1

    async def _request_once(self, url: str) -> str:
        """Perform one HTTP request and classify its response."""
        host = urlsplit(url).hostname
        if not host:
            raise FetchError("invalid_url", "request URL has no hostname")
        await self._wait_for_host(host.casefold())
        # Another request may have hit a denial while this one waited for pacing.
        self._raise_if_blocked()
        retry_after: float | None = None
        transient_status: int
        try:
            async with self._client.stream("GET", url, follow_redirects=False) as response:
                if 300 <= response.status_code < 400 or response.status_code in {
                    401,
                    403,
                    429,
                }:
                    self._blocked_status = response.status_code
                    raise FetchError(
                        "source_blocked",
                        f"LinkedIn returned HTTP {response.status_code}",
                        status_code=response.status_code,
                    )
                # Redirects, access denials, and rate limits are upstream stop
                # signals; only server failures are eligible for bounded retries.
                if response.status_code >= 500:
                    transient_status = response.status_code
                    retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                else:
                    return await self._read_text(response)
        except httpx.TimeoutException as exc:
            raise FetchError("timeout", "LinkedIn request timed out", retryable=True) from exc
        except httpx.TransportError as exc:
            raise FetchError("transport", "LinkedIn request failed", retryable=True) from exc

        raise FetchError(
            "transient_http",
            f"LinkedIn returned HTTP {transient_status}",
            status_code=transient_status,
            retryable=True,
            retry_after_seconds=retry_after,
        )

    def _raise_if_blocked(self) -> None:
        """Stop queued requests after an access denial or rate limit."""
        if self._blocked_status is not None:
            raise FetchError(
                "source_blocked",
                f"LinkedIn returned HTTP {self._blocked_status}; collection stopped",
                status_code=self._blocked_status,
            )
        if self._blocked_challenge:
            raise FetchError(
                "source_blocked",
                "LinkedIn returned an access or verification page; collection stopped",
            )

    async def _read_text(self, response: httpx.Response) -> str:
        """Read and validate one successful response without exceeding its byte limit."""
        if response.status_code < 200 or response.status_code >= 300:
            raise FetchError(
                "http_status",
                f"LinkedIn returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        # Reject an advertised oversized body early, then bound the streamed bytes because
        # Content-Length can be absent, inaccurate, or smaller than decoded content.
        content_length = response.headers.get("Content-Length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > self.settings.max_response_bytes
        ):
            raise FetchError("response_too_large", "response exceeds configured size limit")
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > self.settings.max_response_bytes:
                raise FetchError("response_too_large", "response exceeds configured size limit")
            chunks.append(chunk)
        body = b"".join(chunks)

        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not any(item in content_type for item in ("html", "text/plain")):
            raise FetchError("content_type", "LinkedIn did not return HTML")
        encoding = _response_encoding(response, body)
        try:
            html = body.decode(encoding)
        except (LookupError, UnicodeDecodeError) as exc:
            raise FetchError("invalid_text", "LinkedIn returned undecodable HTML") from exc
        if is_linkedin_access_challenge(html):
            self._blocked_challenge = True
            self._raise_if_blocked()
        return html

    async def _wait_for_host(self, host: str) -> None:
        """Apply per-host pacing before an HTTP request."""
        lock = self._host_locks.setdefault(host, asyncio.Lock())
        # Reserve request start times under the lock, but release it during I/O so slow
        # responses do not unnecessarily block later rate-limited requests.
        async with lock:
            now = time.monotonic()
            elapsed = now - self._last_request_at.get(host, 0.0)
            wait_for = self.settings.rate_limit_seconds - elapsed
            if wait_for > 0:
                await self._sleep(wait_for)
            self._last_request_at[host] = time.monotonic()


def _is_approved_path(path: str, query: str) -> bool:
    """Allow only the three fixed public LinkedIn endpoint families."""
    search_path = urlsplit(LINKEDIN_SEARCH_ENDPOINT).path
    if path == search_path:
        return True
    if query:
        return False
    return bool(
        _LINKEDIN_DETAIL_PATH_RE.fullmatch(path) or _LINKEDIN_PUBLIC_PATH_RE.fullmatch(path)
    )


def _response_encoding(response: httpx.Response, body: bytes) -> str:
    """Match HTTPX's post-read encoding selection for a bounded streamed body."""
    if hasattr(response, "_encoding"):
        return response.encoding or "utf-8"
    encoding = response.charset_encoding
    if encoding is not None:
        try:
            codecs.lookup(encoding)
        except LookupError:
            encoding = None
    if encoding is None:
        default_encoding = response.default_encoding
        encoding = default_encoding if isinstance(default_encoding, str) else default_encoding(body)
    return encoding or "utf-8"


def _retry_after_seconds(value: str | None) -> float | None:
    """Parse a Retry-After header into a bounded delay."""
    if not value:
        return None
    try:
        seconds = float(value)
        return max(seconds, 0.0) if math.isfinite(seconds) else None
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            return max((retry_at - utc_now()).total_seconds(), 0.0)
        except (TypeError, ValueError, OverflowError):
            return None
