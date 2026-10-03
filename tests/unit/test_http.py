from __future__ import annotations

import asyncio
import gzip
import zlib
from collections.abc import AsyncIterator
from types import SimpleNamespace

import httpx
import pytest

import opportunities.scrapers.http as http_module
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


@pytest.mark.parametrize(
    "destination",
    [
        "https://it.linkedin.com/jobs/ingegnere-offerte-di-lavoro?trk=expired_jd_redirect",
        "https://www.linkedin.com/jobs/software-engineer-jobs?trk=expired_jd_redirect",
        "https://de.linkedin.com:443/jobs/software-jobs/?trk=expired_jd_redirect",
    ],
)
@pytest.mark.parametrize("cleanup", ["normal", "timeout", "transport", "unexpected", "classified"])
def test_expired_listing_redirect_is_inconclusive_without_following_reading_or_retrying(
    destination: str, cleanup: str
) -> None:
    failures = {
        "timeout": httpx.ReadTimeout("synthetic-private-cleanup"),
        "transport": httpx.ReadError("synthetic-private-cleanup"),
        "unexpected": RuntimeError("synthetic-private-cleanup"),
        "classified": FetchError("http_status", "synthetic-private-cleanup", status_code=404),
    }

    class RedirectStream(ChunkedStream):
        async def aclose(self) -> None:
            await super().aclose()
            if cleanup in failures:
                raise failures[cleanup]

    stream = RedirectStream((b"synthetic-private-redirect-body",))
    requested: list[str] = []
    delays: list[float] = []
    public_url = "https://www.linkedin.com/jobs/view/1111111111"

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if str(request.url) == public_url:
            return httpx.Response(301, headers={"Location": destination}, stream=stream)
        assert str(request.url) == LINKEDIN_SEARCH_ENDPOINT
        return httpx.Response(200, text="<li>synthetic</li>")

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def run() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), follow_redirects=True
        ) as client:
            fetcher = HttpFetcher(
                Settings(linkedin_crawl_authorized=True, rate_limit_seconds=0, max_retries=2),
                client=client,
                sleep=sleep,
            )
            with pytest.raises(FetchError) as error:
                await fetcher.get_text(public_url)
            assert error.value.code == "listing_redirect"
            assert error.value.status_code == 301
            assert not error.value.retryable
            assert "synthetic-private" not in str(error.value)
            assert destination not in str(error.value)
            assert await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT) == "<li>synthetic</li>"
            # Recognizing a destination must not authorize requests to it.
            with pytest.raises(FetchError) as unsafe:
                await fetcher.get_text(destination)
            assert unsafe.value.code == "invalid_url"

    asyncio.run(run())
    assert requested == [public_url, LINKEDIN_SEARCH_ENDPOINT]
    assert delays == []
    assert stream.read_count == 0
    assert stream.closed


@pytest.mark.parametrize(
    ("endpoint", "status", "destination"),
    [
        ("public", 301, None),
        ("public", 301, "http://it.linkedin.com/jobs/software-jobs?trk=expired_jd_redirect"),
        ("public", 301, "//it.linkedin.com/jobs/software-jobs?trk=expired_jd_redirect"),
        (
            "public",
            301,
            "https://it.linkedin.com.evil.test/jobs/software-jobs?trk=expired_jd_redirect",
        ),
        ("public", 301, "https://unknown.linkedin.com/jobs/software-jobs?trk=expired_jd_redirect"),
        ("public", 301, "https://user@it.linkedin.com/jobs/software-jobs?trk=expired_jd_redirect"),
        ("public", 301, "https://it.linkedin.com:444/jobs/software-jobs?trk=expired_jd_redirect"),
        ("public", 301, "https://it.linkedin.com/login?trk=expired_jd_redirect"),
        ("public", 301, "https://it.linkedin.com/authwall?trk=expired_jd_redirect"),
        ("public", 301, "https://it.linkedin.com/checkpoint/challenge?trk=expired_jd_redirect"),
        ("public", 301, "https://it.linkedin.com/jobs/view/2222222222?trk=expired_jd_redirect"),
        ("public", 301, "https://it.linkedin.com/jobs/software-jobs"),
        ("public", 301, "https://it.linkedin.com/jobs/software-jobs?trk=unknown"),
        (
            "public",
            301,
            "https://it.linkedin.com/jobs/software-jobs?trk=expired_jd_redirect&next=login",
        ),
        ("public", 301, "https://it.linkedin.com/jobs/software-jobs?trk=expired_jd_redirect#login"),
        (
            "public",
            301,
            "https://it.linkedin.com/jobs/software-jobs%2f..%2flogin?trk=expired_jd_redirect",
        ),
        *[
            (endpoint, status, "https://it.linkedin.com/jobs/software-jobs?trk=expired_jd_redirect")
            for endpoint, status in (
                ("detail", 301),
                ("search", 301),
                ("public", 302),
                ("public", 307),
                ("public", 308),
                ("public", 401),
                ("public", 403),
                ("public", 429),
            )
        ],
    ],
)
def test_expired_redirect_exception_does_not_relax_other_source_stops(
    endpoint: str, status: int, destination: str | None
) -> None:
    urls = {
        "public": "https://www.linkedin.com/jobs/view/1111111111",
        "detail": "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/1111111111",
        "search": LINKEDIN_SEARCH_ENDPOINT,
    }
    stream = ChunkedStream((b"synthetic-private-response",))
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(
            status, headers={"Location": destination} if destination else {}, stream=stream
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            fetcher = HttpFetcher(
                Settings(linkedin_crawl_authorized=True, rate_limit_seconds=0), client=client
            )
            for url in (urls[endpoint], LINKEDIN_SEARCH_ENDPOINT):
                with pytest.raises(FetchError) as error:
                    await fetcher.get_text(url)
                assert error.value.code == "source_blocked"
                assert error.value.status_code == status
                assert not error.value.retryable

    asyncio.run(run())
    assert requested == [urls[endpoint]]
    assert stream.read_count == 0
    assert stream.closed


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
@pytest.mark.parametrize("max_retries", [0, 2])
@pytest.mark.parametrize("failure", [httpx.ReadTimeout, httpx.ReadError, RuntimeError])
def test_response_cleanup_cannot_hide_a_detected_source_denial(
    status_code: int, max_retries: int, failure: type[Exception]
) -> None:
    class FailingCloseStream(ChunkedStream):
        async def aclose(self) -> None:
            await super().aclose()
            raise failure("synthetic-private-cleanup-detail")

    stream = FailingCloseStream((b"ignored denial body",))
    attempts = 0
    delays: list[float] = []

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts <= max_retries:
            return httpx.Response(503, request=request)
        return httpx.Response(status_code, stream=stream, request=request)

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            fetcher = HttpFetcher(
                Settings(
                    linkedin_crawl_authorized=True,
                    rate_limit_seconds=0,
                    retry_backoff_seconds=0,
                    max_retries=max_retries,
                ),
                client=client,
                sleep=sleep,
            )
            for _ in range(2):
                with pytest.raises(FetchError) as error:
                    await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
                assert error.value.code == "source_blocked"
                assert error.value.status_code == status_code
                assert not error.value.retryable
                assert "synthetic-private-cleanup-detail" not in str(error.value)

    asyncio.run(run())
    assert attempts == max_retries + 1
    assert delays == [0] * max_retries
    assert stream.read_count == 0
    assert stream.closed


def test_unexpected_client_failure_without_a_denial_is_preserved() -> None:
    failure = RuntimeError("synthetic unexpected client failure")

    def handle(_request: httpx.Request) -> httpx.Response:
        raise failure

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            fetcher = HttpFetcher(
                Settings(linkedin_crawl_authorized=True, rate_limit_seconds=0), client=client
            )
            with pytest.raises(RuntimeError) as error:
                await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            assert error.value is failure

    asyncio.run(run())


@pytest.mark.parametrize("status_code", [302, 401, 403, 429])
def test_redirect_or_access_denial_stops_queued_and_later_requests(
    status_code: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Start beyond the pacing interval so the first request sends without sleeping.
    monkeypatch.setattr(http_module, "time", SimpleNamespace(monotonic=lambda: 1000.0))
    started = asyncio.Event()
    queued = asyncio.Event()
    release_queued = asyncio.Event()
    requests = 0

    # Hold the denial until another request is pacing, then resume that waiter after blocking.
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

    asyncio.run(asyncio.wait_for(run(), timeout=5))
    assert requests == 1


def test_challenge_page_stops_queued_and_later_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http_module, "time", SimpleNamespace(monotonic=lambda: 1000.0))
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

    asyncio.run(asyncio.wait_for(run(), timeout=5))
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


@pytest.mark.parametrize("authentication", ["authorization", "proxy-authorization", "client-auth"])
def test_injected_http_clients_must_remain_unauthenticated(authentication: str) -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, text="synthetic")

    async def run() -> None:
        headers = (
            {authentication: "synthetic-placeholder"} if authentication != "client-auth" else {}
        )
        auth = (
            httpx.BasicAuth("synthetic", "placeholder") if authentication == "client-auth" else None
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle), headers=headers, auth=auth
        ) as client:
            with pytest.raises(ValueError, match="authentication"):
                HttpFetcher(Settings(), client=client)

    asyncio.run(run())
    assert requests == []


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "x-unsupported", "identity"])
def test_response_bounds_apply_before_decompression(encoding: str) -> None:
    # Small fixtures suffice: compression must be rejected before any chunk is decoded.
    body = b"<html>synthetic fixture</html>"
    payloads = {"gzip": gzip.compress(body, mtime=0), "deflate": zlib.compress(body)}
    stream = ChunkedStream((payloads.get(encoding, body),))
    requested_encodings: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requested_encodings.append(request.headers["accept-encoding"])
        return httpx.Response(
            200,
            stream=stream,
            headers={"content-encoding": encoding, "content-type": "text/html"},
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            fetcher = HttpFetcher(
                Settings(linkedin_crawl_authorized=True, rate_limit_seconds=0), client=client
            )
            if encoding == "identity":
                assert await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT) == body.decode()
                assert stream.read_count == 1
            else:
                with pytest.raises(FetchError) as error:
                    await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
                assert error.value.code == "content_encoding"
                assert stream.read_count == 0
        assert stream.closed
        assert requested_encodings == ["identity"]

    asyncio.run(run())


@pytest.mark.parametrize("failure", [httpx.ReadTimeout, httpx.ConnectError])
def test_transport_failures_have_bounded_retries_and_sanitized_errors(
    failure: type[httpx.TransportError],
) -> None:
    attempts = 0
    delays: list[float] = []

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise failure("synthetic-private-response-detail", request=request)

    async def sleep(delay: float) -> None:
        delays.append(delay)

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            fetcher = HttpFetcher(
                Settings(linkedin_crawl_authorized=True, rate_limit_seconds=0, max_retries=2),
                client=client,
                sleep=sleep,
            )
            with pytest.raises(FetchError) as error:
                await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            assert error.value.code == ("timeout" if failure is httpx.ReadTimeout else "transport")
            assert "synthetic-private-response-detail" not in str(error.value)

    asyncio.run(run())
    assert attempts == 3
    assert delays == [0.5, 1.0]
