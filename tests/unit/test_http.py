from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest

from opportunities.config.settings import Settings
from opportunities.scrapers.http import FetchError, HttpFetcher


class ChunkedStream(httpx.AsyncByteStream):
    """Expose read progress so response-bound behavior can be asserted."""

    def __init__(self, chunks: tuple[bytes, ...]) -> None:
        self.chunks = chunks
        self.read_count = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            self.read_count += 1
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


def test_linkedin_http_is_blocked_without_explicit_authorization() -> None:
    settings = Settings(rate_limit_seconds=0)

    async def run() -> None:
        async with HttpFetcher(settings) as fetcher:
            with pytest.raises(FetchError, match="express permission"):
                await fetcher.get_text("https://www.linkedin.com/jobs-guest/jobs/api/search")

    asyncio.run(run())


def test_http_fetcher_rejects_non_linkedin_or_non_https_urls_without_network() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, text="<html></html>", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(rate_limit_seconds=0, linkedin_crawl_authorized=True)

    async def run() -> None:
        async with client:
            fetcher = HttpFetcher(settings, client=client)
            for url in (
                "https://example.com/jobs",
                "http://www.linkedin.com/jobs-guest/jobs/api/search",
            ):
                with pytest.raises(FetchError, match="approved LinkedIn HTTPS endpoint"):
                    await fetcher.get_text(url)

    asyncio.run(run())
    assert requests == 0


def test_http_fetcher_retries_transient_linkedin_response() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="temporary", request=request)
        return httpx.Response(
            200,
            text="<li>ok</li>",
            request=request,
            headers={"content-type": "text/html; charset=utf-8"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        rate_limit_seconds=0,
        retry_backoff_seconds=0,
        max_retries=2,
        linkedin_crawl_authorized=True,
    )

    async def run() -> str:
        async with client:
            return await HttpFetcher(settings, client=client).get_text(
                "https://www.linkedin.com/jobs-guest/jobs/api/search"
            )

    assert asyncio.run(run()) == "<li>ok</li>"
    assert attempts == 2


def test_http_fetcher_honors_429_retry_after() -> None:
    attempts = 0
    delays: list[float] = []
    retry_stream = ChunkedStream((b"rate limited", b"ignored"))

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                stream=retry_stream,
                request=request,
                headers={"retry-after": "2"},
            )
        return httpx.Response(
            200,
            text="<html></html>",
            request=request,
            headers={"content-type": "text/html"},
        )

    async def sleep(delay: float) -> None:
        delays.append(delay)
        if delay == 2.0:
            assert retry_stream.closed is True

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        rate_limit_seconds=0,
        retry_backoff_seconds=0,
        max_retries=1,
        linkedin_crawl_authorized=True,
    )

    async def run() -> None:
        async with client:
            await HttpFetcher(settings, client=client, sleep=sleep).get_text(
                "https://www.linkedin.com/jobs-guest/jobs/api/search"
            )

    asyncio.run(run())
    assert attempts == 2
    assert 2.0 in delays
    assert retry_stream.read_count == 0
    assert retry_stream.closed is True


def test_http_fetcher_rejects_non_html_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"jobs": []},
            request=request,
            headers={"content-type": "application/json"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(rate_limit_seconds=0, max_retries=0, linkedin_crawl_authorized=True)

    async def run() -> None:
        async with client:
            with pytest.raises(FetchError, match="did not return HTML"):
                await HttpFetcher(settings, client=client).get_text(
                    "https://www.linkedin.com/jobs-guest/jobs/api/search"
                )

    asyncio.run(run())


def test_http_fetcher_enforces_response_size_limit() -> None:
    body = ("<html>" + ("x" * 20_000) + "</html>").encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=body,
            request=request,
            headers={"content-type": "text/html", "content-length": str(len(body))},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        rate_limit_seconds=0,
        max_retries=0,
        max_response_bytes=10_000,
        linkedin_crawl_authorized=True,
    )

    async def run() -> None:
        async with client:
            with pytest.raises(FetchError, match="size limit"):
                await HttpFetcher(settings, client=client).get_text(
                    "https://www.linkedin.com/jobs-guest/jobs/api/search"
                )

    asyncio.run(run())


def test_http_fetcher_stops_streaming_at_response_size_limit() -> None:
    stream = ChunkedStream((b"x" * 6_000, b"y" * 6_000, b"z" * 6_000))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            stream=stream,
            request=request,
            headers={"content-type": "text/html"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        rate_limit_seconds=0,
        max_retries=0,
        max_response_bytes=10_000,
        linkedin_crawl_authorized=True,
    )

    async def run() -> None:
        async with client:
            with pytest.raises(FetchError, match="size limit"):
                await HttpFetcher(settings, client=client).get_text(
                    "https://www.linkedin.com/jobs-guest/jobs/api/search"
                )

    asyncio.run(run())
    assert stream.read_count == 2
    assert stream.closed is True
