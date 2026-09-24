from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest

from opportunities.config.settings import Settings
from opportunities.scrapers.http import LINKEDIN_SEARCH_ENDPOINT, FetchError, HttpFetcher


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
                await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)

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
                LINKEDIN_SEARCH_ENDPOINT.replace("https://", "http://"),
                "https://www.linkedin.com/feed",
            ):
                with pytest.raises(FetchError, match="approved LinkedIn HTTPS endpoint"):
                    await fetcher.get_text(url)

    asyncio.run(run())
    assert requests == 0


def test_http_fetcher_disables_redirects_on_an_injected_client() -> None:
    requested_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        return httpx.Response(302, headers={"location": "https://example.com/redirected"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True)
    settings = Settings(rate_limit_seconds=0, linkedin_crawl_authorized=True)

    async def run() -> None:
        async with client:
            with pytest.raises(FetchError, match="HTTP 302"):
                await HttpFetcher(settings, client=client).get_text(LINKEDIN_SEARCH_ENDPOINT)

    asyncio.run(run())
    assert requested_hosts == ["www.linkedin.com"]


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
            return await HttpFetcher(settings, client=client).get_text(LINKEDIN_SEARCH_ENDPOINT)

    assert asyncio.run(run()) == "<li>ok</li>"
    assert attempts == 2


def test_http_fetcher_caps_exponential_backoff() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503, text="temporary", request=request)

    async def sleep(delay: float) -> None:
        delays.append(delay)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        rate_limit_seconds=0,
        retry_backoff_seconds=30,
        max_retries=2,
        linkedin_crawl_authorized=True,
    )

    async def run() -> None:
        async with client:
            with pytest.raises(FetchError, match="HTTP 503"):
                await HttpFetcher(settings, client=client, sleep=sleep).get_text(
                    LINKEDIN_SEARCH_ENDPOINT
                )

    asyncio.run(run())
    assert attempts == 3
    assert delays == [30, 60]


def test_http_fetcher_stops_on_429_without_reading_response_body() -> None:
    attempts = 0
    delays: list[float] = []
    rate_limit_stream = ChunkedStream((b"rate limited", b"ignored"))

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            429,
            stream=rate_limit_stream,
            request=request,
            headers={"retry-after": "2"},
        )

    async def sleep(delay: float) -> None:
        delays.append(delay)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        rate_limit_seconds=0,
        retry_backoff_seconds=0,
        max_retries=1,
        linkedin_crawl_authorized=True,
    )

    async def run() -> None:
        async with client:
            with pytest.raises(FetchError, match="HTTP 429") as error:
                await HttpFetcher(settings, client=client, sleep=sleep).get_text(
                    LINKEDIN_SEARCH_ENDPOINT
                )
            assert error.value.status_code == 429

    asyncio.run(run())
    assert attempts == 1
    assert delays == []
    assert rate_limit_stream.read_count == 0
    assert rate_limit_stream.closed is True


@pytest.mark.parametrize("status_code", [302, 401, 403, 429])
def test_redirect_or_access_denial_stops_queued_and_later_requests(status_code: int) -> None:
    started = asyncio.Event()
    queued = asyncio.Event()
    release_queued = asyncio.Event()
    requests = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        started.set()
        await queued.wait()
        return httpx.Response(
            status_code,
            request=request,
            headers={"location": "https://www.linkedin.com/login"} if status_code == 302 else None,
        )

    async def sleep(_delay: float) -> None:
        queued.set()
        await release_queued.wait()

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        rate_limit_seconds=60,
        max_retries=2,
        linkedin_crawl_authorized=True,
    )

    async def run() -> None:
        async with client:
            fetcher = HttpFetcher(settings, client=client, sleep=sleep)
            first = asyncio.create_task(fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT))
            await started.wait()
            waiting = asyncio.create_task(fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT))
            await queued.wait()
            with pytest.raises(FetchError) as first_error:
                await first
            assert first_error.value.status_code == status_code
            release_queued.set()
            with pytest.raises(FetchError) as waiting_error:
                await waiting
            assert waiting_error.value.code == "source_blocked"
            with pytest.raises(FetchError) as later_error:
                await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            assert later_error.value.status_code == status_code

    asyncio.run(run())
    assert requests == 1


def test_challenge_page_stops_queued_and_later_requests() -> None:
    started = asyncio.Event()
    queued = asyncio.Event()
    release_queued = asyncio.Event()
    requests = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        started.set()
        await queued.wait()
        return httpx.Response(
            200,
            text="<html>Security verification challenge-page</html>",
            request=request,
        )

    async def sleep(_delay: float) -> None:
        queued.set()
        await release_queued.wait()

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(rate_limit_seconds=60, linkedin_crawl_authorized=True)

    async def run() -> None:
        async with client:
            fetcher = HttpFetcher(settings, client=client, sleep=sleep)
            first = asyncio.create_task(fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT))
            await started.wait()
            waiting = asyncio.create_task(fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT))
            await queued.wait()
            with pytest.raises(FetchError, match="verification page") as first_error:
                await first
            assert first_error.value.code == "source_blocked"
            release_queued.set()
            with pytest.raises(FetchError) as waiting_error:
                await waiting
            assert waiting_error.value.code == "source_blocked"
            with pytest.raises(FetchError) as later_error:
                await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            assert later_error.value.code == "source_blocked"

    asyncio.run(run())
    assert requests == 1


def test_http_fetcher_never_retains_or_sends_source_cookies() -> None:
    sent_cookies: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_cookies.append(request.headers.get("cookie"))
        return httpx.Response(
            200,
            text="<html></html>",
            request=request,
            headers={"set-cookie": "li_at=synthetic; Domain=.linkedin.com; Path=/"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(rate_limit_seconds=0, linkedin_crawl_authorized=True)

    async def run() -> None:
        async with client:
            fetcher = HttpFetcher(settings, client=client)
            await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)

    asyncio.run(run())
    assert sent_cookies == [None, None]
    assert list(client.cookies.jar) == []


def test_http_fetcher_rejects_preconfigured_cookie_header() -> None:
    client = httpx.AsyncClient(headers={"Cookie": "li_at=synthetic"})

    async def run() -> None:
        async with client:
            with pytest.raises(ValueError, match="must not have a Cookie header"):
                HttpFetcher(Settings(), client=client)

    asyncio.run(run())


def test_owned_http_client_ignores_ambient_https_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "")
    real_client = httpx.AsyncClient

    sent_cookies: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_cookies.append(request.headers.get("cookie"))
        return httpx.Response(
            200,
            text="<html></html>",
            request=request,
            headers={"set-cookie": "guest=synthetic; Path=/"},
        )

    transport = httpx.MockTransport(handler)

    def client_with_offline_transport(*, trust_env: bool, **_kwargs: object) -> httpx.AsyncClient:
        assert trust_env is False
        return real_client(transport=transport, trust_env=trust_env)

    monkeypatch.setattr(httpx, "AsyncClient", client_with_offline_transport)
    settings = Settings(rate_limit_seconds=0, linkedin_crawl_authorized=True)

    async def run() -> tuple[str, str]:
        async with HttpFetcher(settings) as fetcher:
            first = await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            second = await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            return first, second

    assert asyncio.run(run()) == ("<html></html>", "<html></html>")
    assert sent_cookies == [None, None]


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
                await HttpFetcher(settings, client=client).get_text(LINKEDIN_SEARCH_ENDPOINT)

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
                await HttpFetcher(settings, client=client).get_text(LINKEDIN_SEARCH_ENDPOINT)

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
                await HttpFetcher(settings, client=client).get_text(LINKEDIN_SEARCH_ENDPOINT)

    asyncio.run(run())
    assert stream.read_count == 2
    assert stream.closed is True
