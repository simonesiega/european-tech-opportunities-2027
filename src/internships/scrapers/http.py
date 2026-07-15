"""Bounded, rate-limited HTTP transport for public LinkedIn HTML pages."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx

from internships.config.settings import Settings
from internships.utils.time import utc_now

logger = logging.getLogger(__name__)
Sleep = Callable[[float], Awaitable[None]]


class FetchError(RuntimeError):
    """A sanitized network or response-validation failure."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        """Initialize the instance dependencies and state."""
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class TextResponse:
    """Validated HTML response with non-sensitive request metrics."""

    text: str
    status_code: int
    elapsed_ms: int
    content_bytes: int


class HttpFetcher:
    """Fetch public HTML with retries, host pacing, and response-size limits."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.AsyncClient | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        """Initialize the instance dependencies and state."""
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
        self._client = client or httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=False,
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-GB,en;q=0.8",
            },
        )
        self._host_locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}

    async def __aenter__(self) -> HttpFetcher:
        """Open the asynchronous HTTP client context."""
        return self

    async def __aexit__(self, *_args: object) -> None:
        """Close the asynchronous HTTP client context."""
        if self._owns_client:
            await self._client.aclose()

    async def get_text(self, url: str) -> TextResponse:
        """Fetch HTML/text, retrying timeout, transport, 429, and 5xx failures."""
        hostname = (urlsplit(url).hostname or "").casefold()
        # Enforce authorization before creating any network traffic, including retries.
        if (
            hostname == "linkedin.com" or hostname.endswith(".linkedin.com")
        ) and not self.settings.linkedin_crawl_authorized:
            raise FetchError(
                "crawl_not_authorized",
                "LinkedIn crawling is disabled until express permission is configured",
            )
        last_error: FetchError | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                return await self._request_once(url)
            except FetchError as exc:
                last_error = exc
                if not exc.retryable or attempt >= self.settings.max_retries:
                    raise
                delay = self.settings.retry_backoff_seconds * (2**attempt)
                logger.warning(
                    "retrying LinkedIn request",
                    extra={
                        "error_code": exc.code,
                        "attempt": attempt + 1,
                        "delay_seconds": delay,
                    },
                )
                await self._sleep(delay)
        if last_error is None:  # pragma: no cover - loop always executes
            raise FetchError("internal", "request did not execute")
        raise last_error

    async def _request_once(self, url: str) -> TextResponse:
        """Perform one HTTP request and classify its response."""
        host = urlsplit(url).hostname
        if not host:
            raise FetchError("invalid_url", "request URL has no hostname")
        await self._wait_for_host(host.casefold())
        started = time.monotonic()
        try:
            response = await self._client.get(url)
        except httpx.TimeoutException as exc:
            raise FetchError("timeout", "LinkedIn request timed out", retryable=True) from exc
        except httpx.TransportError as exc:
            raise FetchError("transport", "LinkedIn request failed", retryable=True) from exc
        elapsed_ms = round((time.monotonic() - started) * 1000)

        if response.status_code == 429 or response.status_code >= 500:
            retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
            if retry_after is not None:
                await self._sleep(min(retry_after, 60.0))
            raise FetchError(
                "transient_http",
                f"LinkedIn returned HTTP {response.status_code}",
                status_code=response.status_code,
                retryable=True,
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise FetchError(
                "http_status",
                f"LinkedIn returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        # Reject an advertised oversized body early, then verify the actual bytes because
        # Content-Length can be absent or inaccurate.
        content_length = response.headers.get("Content-Length")
        if (
            content_length
            and content_length.isdigit()
            and int(content_length) > self.settings.max_response_bytes
        ):
            raise FetchError("response_too_large", "response exceeds configured size limit")
        body = await response.aread()
        if len(body) > self.settings.max_response_bytes:
            raise FetchError("response_too_large", "response exceeds configured size limit")
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not any(item in content_type for item in ("html", "text/plain")):
            raise FetchError("content_type", "LinkedIn did not return HTML")
        encoding = response.encoding or "utf-8"
        try:
            text = body.decode(encoding)
        except (LookupError, UnicodeDecodeError) as exc:
            raise FetchError("invalid_text", "LinkedIn returned undecodable HTML") from exc
        return TextResponse(
            text=text,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            content_bytes=len(body),
        )

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


def _retry_after_seconds(value: str | None) -> float | None:
    """Parse a Retry-After header into a bounded delay."""
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            return max((retry_at - utc_now()).total_seconds(), 0.0)
        except (TypeError, ValueError, OverflowError):
            return None
