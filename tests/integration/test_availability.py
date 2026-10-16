from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.settings import Settings
from opportunities.database.models import JobRow, JobSearchRow
from opportunities.database.repository import Repository
from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.availability import audit_job_availability
from opportunities.scrapers.http import (
    LINKEDIN_DETAIL_ENDPOINT,
    LINKEDIN_PUBLIC_JOB_URL,
    FetchError,
    HttpFetcher,
)
from opportunities.utils.time import ensure_utc


class FakeAvailabilityFetcher:
    def __init__(self) -> None:
        self.requested: list[str] = []

    async def get_text(self, url: str) -> str:
        self.requested.append(url)
        if LINKEDIN_PUBLIC_JOB_URL.split("{")[0] in url:
            if url.endswith("2222222222"):
                raise FetchError("http_status", "not found", status_code=404)
            if url.endswith("3333333333"):
                raise FetchError("transient_http", "server error", status_code=503)
            if url.endswith("4444444444"):
                return "<html><body>Security verification challenge-page</body></html>"
            if url.endswith("5555555555"):
                return """<div class="unstable-hashed-class" aria-atomic="true"
                  aria-live="assertive"><svg aria-label="Error"></svg>
                  <p>No longer accepting applications</p></div>"""
            return "<html><body>Public job page</body></html>"
        return (
            '<h1 class="top-card-layout__title">Software Engineering Intern 2027</h1>'
            '<a class="topcard__org-name-link">Example Technology</a>'
        )


def test_availability_audit_checks_every_row_deletes_only_explicit_unavailability(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    observed_at = datetime(2026, 7, 19, 3, 17, tzinfo=UTC)
    repository.sync_searches([search], observed_at)
    jobs = [
        DiscoveredJob(
            linkedin_job_id=job_id,
            company="Example Technology",
            title=f"Software Engineering Intern 2027 ({job_id})",
            location="London, UK",
            link=f"https://www.linkedin.com/jobs/view/{job_id}",
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.INTERNSHIP,
        )
        for job_id in (
            "1111111111",
            "2222222222",
            "3333333333",
            "4444444444",
            "5555555555",
        )
    ]
    repository.persist_success(
        run_id="00000000-0000-0000-0000-000000000001",
        search=search,
        jobs=jobs,
        confirmed_unavailable_ids=(),
        found_count=len(jobs),
        excluded_count=0,
        warning_count=0,
        started_at=observed_at,
        finished_at=observed_at,
        duration_ms=1,
    )
    for run in (2, 3):
        when = observed_at + timedelta(minutes=run)
        repository.persist_success(
            run_id=f"00000000-0000-0000-0000-{run:012d}",
            search=search,
            jobs=[],
            confirmed_unavailable_ids=("1111111111",),
            found_count=0,
            excluded_count=0,
            warning_count=0,
            started_at=when,
            finished_at=when,
            duration_ms=1,
        )
    original = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    assert original["1111111111"].status == JobStatus.CLOSED
    fetcher = FakeAvailabilityFetcher()
    result = asyncio.run(
        audit_job_availability(
            settings=settings,
            repository=repository,
            fetcher=fetcher,
            observed_at=observed_at + timedelta(minutes=4),
        )
    )

    assert result.checked == 5
    assert result.available == 1
    assert result.deleted == 2
    assert result.reopened == 1
    assert result.inconclusive_ids == ("3333333333", "4444444444")
    current = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    for job_id in result.inconclusive_ids:
        assert current[job_id] == original[job_id]
    assert result.exit_code == 2
    assert set(fetcher.requested) == {
        *(LINKEDIN_PUBLIC_JOB_URL.format(job_id=job.linkedin_job_id) for job in jobs),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id="1111111111"),
    }
    assert {job.linkedin_job_id for job in repository.list_all_jobs()} == {
        "1111111111",
        "3333333333",
        "4444444444",
    }
    assert {job.linkedin_job_id for job in repository.list_open_jobs()} == {
        "1111111111",
        "3333333333",
        "4444444444",
    }
    with session_factory() as session:
        reopened_alias = session.get(JobSearchRow, (search.slug, "1111111111"))
        deleted_alias = session.get(JobSearchRow, (search.slug, "2222222222"))
        assert reopened_alias is not None
        assert reopened_alias.active is True
        assert reopened_alias.unavailable_confirmations == 0
        assert deleted_alias is None


def test_availability_audit_includes_manual_jobs_without_provenance(
    session_factory: sessionmaker[Session], settings: Settings
) -> None:
    repository = Repository(session_factory, settings)
    observed_at = datetime(2026, 7, 19, 3, 17, tzinfo=UTC)
    repository.upsert_manual_job(
        DiscoveredJob(
            linkedin_job_id="2222222222",
            company="Example Technology",
            title="Software Engineering Intern 2027",
            location="London, UK",
            link="https://www.linkedin.com/jobs/view/2222222222",
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.INTERNSHIP,
        ),
        observed_at=observed_at,
    )
    fetcher = FakeAvailabilityFetcher()

    result = asyncio.run(
        audit_job_availability(
            settings=settings,
            repository=repository,
            fetcher=fetcher,
            observed_at=observed_at,
        )
    )

    assert result.checked == 1
    assert result.deleted == 1
    assert fetcher.requested == [LINKEDIN_PUBLIC_JOB_URL.format(job_id="2222222222")]
    assert repository.list_all_jobs() == []


def test_delayed_audit_cannot_delete_newer_rediscovery(
    session_factory: sessionmaker[Session], settings: Settings, search: LinkedInSearchConfig
) -> None:
    repository = Repository(session_factory, settings)
    checked_at = datetime(2026, 7, 19, 3, 17, tzinfo=UTC)
    newer = checked_at + timedelta(minutes=2)
    job = DiscoveredJob(
        linkedin_job_id="2222222222",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/2222222222",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )
    repository.sync_searches([search], checked_at)

    def persist(run: int, when: datetime) -> None:
        repository.persist_success(
            run_id=f"00000000-0000-0000-0000-{run:012d}",
            search=search,
            jobs=[job],
            confirmed_unavailable_ids=(),
            found_count=1,
            excluded_count=0,
            warning_count=0,
            started_at=when,
            finished_at=when,
            duration_ms=1,
        )

    persist(1, checked_at)

    class DelayedNotFound:
        async def get_text(self, _url: str) -> str:
            # Insert the newer discovery during the old audit's fetch, without a timing race.
            persist(2, newer)
            raise FetchError("http_status", "not found", status_code=404)

    result = asyncio.run(
        audit_job_availability(
            settings=settings,
            repository=repository,
            fetcher=DelayedNotFound(),
            observed_at=checked_at,
        )
    )
    assert result.deleted == 0
    assert repository.list_open_jobs()[0].last_seen_at == newer
    with session_factory() as session:
        assert session.get(JobSearchRow, (search.slug, job.linkedin_job_id)) is not None
        row = session.get(JobRow, job.linkedin_job_id)
        assert row is not None
        assert row.last_availability_checked_at is not None
        assert ensure_utc(row.last_availability_checked_at) == checked_at
    assert repository.availability_batch(newer) == ([], 0)

    # A delayed successful audit must not reopen a later closure either.
    repository.persist_success(
        run_id="00000000-0000-0000-0000-000000000003",
        search=search,
        jobs=[],
        confirmed_unavailable_ids=(job.linkedin_job_id,),
        found_count=0,
        excluded_count=0,
        warning_count=0,
        started_at=newer + timedelta(minutes=1),
        finished_at=newer + timedelta(minutes=1),
        duration_ms=1,
    )
    repository.persist_success(
        run_id="00000000-0000-0000-0000-000000000004",
        search=search,
        jobs=[],
        confirmed_unavailable_ids=(job.linkedin_job_id,),
        found_count=0,
        excluded_count=0,
        warning_count=0,
        started_at=newer + timedelta(minutes=2),
        finished_at=newer + timedelta(minutes=2),
        duration_ms=1,
    )
    assert repository.list_open_jobs() == []
    changes = repository.apply_availability_audit(
        available_ids=(job.linkedin_job_id,), unavailable_ids=(), observed_at=checked_at
    )
    assert changes.reopened == 0
    assert repository.list_open_jobs() == []


@pytest.mark.parametrize("endpoint", ["public", "detail"])
@pytest.mark.parametrize("denial", [301, 302, 307, 308, 401, 403, 429, "challenge"])
def test_availability_distinguishes_public_listing_301s_from_source_stops(
    session_factory: sessionmaker[Session], settings: Settings, endpoint: str, denial: int | str
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    for job_id in ("1", "2", "3"):
        repository.upsert_manual_job(
            DiscoveredJob(
                linkedin_job_id=job_id,
                company="Synthetic Technology",
                title="Software Intern 2027",
                location="Berlin, Germany",
                link=f"https://www.linkedin.com/jobs/view/{job_id}",
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.INTERNSHIP,
            ),
            observed_at=now,
        )
    before = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    requested: list[str] = []
    blocked_url = (
        LINKEDIN_PUBLIC_JOB_URL if endpoint == "public" else LINKEDIN_DETAIL_ENDPOINT
    ).format(job_id="2")

    def respond(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        if str(request.url) == blocked_url:
            if denial == "challenge":
                return httpx.Response(200, text="<html>Security verification challenge-page</html>")
            assert isinstance(denial, int)
            return httpx.Response(
                denial,
                headers={"Location": "https://example.invalid/unfamiliar?token=synthetic-private"},
            )
        return httpx.Response(
            200,
            text='<h1 class="top-card-layout__title">Software Intern 2027</h1>'
            '<a class="topcard__org-name-link">Synthetic Technology</a>',
        )

    inconclusive_redirect = endpoint == "public" and denial == 301

    async def audit() -> None:
        serial_settings = settings.model_copy(update={"max_concurrency": 1})
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client,
            HttpFetcher(serial_settings, client=client) as fetcher,
        ):
            result = await audit_job_availability(
                settings=serial_settings,
                repository=repository,
                fetcher=fetcher,
                observed_at=now + timedelta(minutes=1),
            )
        assert result.checked == (3 if inconclusive_redirect else 2)
        assert result.blocked == (0 if inconclusive_redirect else 1)
        assert result.deferred == (0 if inconclusive_redirect else 1)
        assert result.available == (2 if inconclusive_redirect else 1)
        assert result.deleted == result.reopened == 0
        assert result.inconclusive_ids == (("2",) if inconclusive_redirect else ())
        assert result.listing_redirect_ids == (("2",) if inconclusive_redirect else ())
        assert result.exit_code == (2 if inconclusive_redirect else 4 if denial == 429 else 1)
        assert result.rate_limited == int(denial == 429)
        assert result.source_blocked is not inconclusive_redirect

    asyncio.run(audit())
    if inconclusive_redirect:
        assert requested == [
            LINKEDIN_PUBLIC_JOB_URL.format(job_id="1"),
            LINKEDIN_DETAIL_ENDPOINT.format(job_id="1"),
            blocked_url,
            LINKEDIN_PUBLIC_JOB_URL.format(job_id="3"),
            LINKEDIN_DETAIL_ENDPOINT.format(job_id="3"),
        ]
    else:
        assert requested[-1] == blocked_url
        assert len(requested) == (3 if endpoint == "public" else 4)
    after = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    assert after["1"].last_seen_at == now + timedelta(minutes=1)
    assert after["2"] == before["2"]
    with session_factory() as session:
        for job_id in ("2", "3"):
            row = session.get(JobRow, job_id)
            assert row is not None
            assert (row.last_availability_checked_at is not None) == inconclusive_redirect
    if inconclusive_redirect:
        assert after["3"].last_seen_at == now + timedelta(minutes=1)
    else:
        assert after["3"] == before["3"]


@pytest.mark.parametrize("denial_status", [403, 429])
@pytest.mark.parametrize("inflight_status", [200, 404])
def test_concurrent_audit_keeps_inflight_evidence_but_stops_new_requests_after_denial(
    session_factory: sessionmaker[Session],
    settings: Settings,
    inflight_status: int,
    denial_status: int,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    repository.upsert_manual_jobs(
        [
            DiscoveredJob(
                linkedin_job_id=job_id,
                company="Synthetic Technology",
                title="Software Intern 2027",
                location="Berlin, Germany",
                link=f"https://www.linkedin.com/jobs/view/{job_id}",
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.INTERNSHIP,
            )
            for job_id in ("1", "2", "3")
        ],
        observed_at=now,
    )
    before = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    requested: list[str] = []
    detail_started = asyncio.Event()
    denial_returned = asyncio.Event()
    identity = (
        '<h1 class="top-card-layout__title">Software Intern 2027</h1>'
        '<a class="topcard__org-name-link">Synthetic Technology</a>'
    )

    async def respond(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path == "/jobs/view/1":
            return httpx.Response(200, text=identity)
        if request.url.path == "/jobs-guest/jobs/api/jobPosting/1":
            detail_started.set()
            await denial_returned.wait()
            return httpx.Response(inflight_status, text=identity)
        if request.url.path == "/jobs/view/2":
            await detail_started.wait()
            denial_returned.set()
            return httpx.Response(denial_status)
        pytest.fail("unexpected request after source denial")

    async def audit() -> None:
        concurrent_settings = settings.model_copy(update={"max_concurrency": 2})
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client,
            HttpFetcher(concurrent_settings, client=client) as fetcher,
        ):
            result = await audit_job_availability(
                settings=concurrent_settings,
                repository=repository,
                fetcher=fetcher,
                observed_at=now + timedelta(minutes=1),
            )
        assert result.source_blocked
        assert result.exit_code == (4 if denial_status == 429 else 1)
        assert result.rate_limited == int(denial_status == 429)
        assert result.checked == 2
        assert result.blocked == result.deferred == 1
        assert result.available == int(inflight_status == 200)
        assert result.deleted == int(inflight_status == 404)
        assert result.reopened == 0
        assert result.inconclusive_ids == ()

    asyncio.run(asyncio.wait_for(audit(), timeout=5))
    assert requested == [
        "/jobs/view/1",
        "/jobs-guest/jobs/api/jobPosting/1",
        "/jobs/view/2",
    ]
    after = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    assert after["2"] == before["2"]
    assert after["3"] == before["3"]
    if inflight_status == 200:
        assert after["1"].last_seen_at == now + timedelta(minutes=1)
    else:
        assert "1" not in after


@pytest.fixture
def partial_audit_state(
    session_factory: sessionmaker[Session], settings: Settings
) -> tuple[Repository, datetime]:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    repository.upsert_manual_jobs(
        [
            DiscoveredJob(
                linkedin_job_id=job_id,
                company="Synthetic Technology",
                title="Software Intern 2027",
                location="Berlin, Germany",
                link=f"https://www.linkedin.com/jobs/view/{job_id}",
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.INTERNSHIP,
            )
            for job_id in ("1", "2", "3", "4")
        ],
        observed_at=now,
    )
    return repository, now


@pytest.mark.parametrize("public_redirect", [False, True])
@pytest.mark.parametrize(
    "scenario",
    [
        "429-only",
        "redirects-only",
        "redirect-then-unavailable",
        "rate-limit-first",
        "timeout",
        "transport",
        "invalid-html",
        "unexpected",
        "http-status",
        "public-301",
        "public-302",
        "detail-301",
        "403-first",
        "challenge-first",
    ],
)
def test_partial_audit_requires_completed_checks_and_only_rate_limit_failures(
    partial_audit_state: tuple[Repository, datetime],
    session_factory: sessionmaker[Session],
    settings: Settings,
    scenario: str,
    public_redirect: bool,
) -> None:
    repository, now = partial_audit_state
    if public_redirect:
        repository.upsert_manual_job(
            DiscoveredJob(
                linkedin_job_id="0",
                company="Synthetic Technology",
                title="Software Intern 2027",
                location="Berlin, Germany",
                link="https://www.linkedin.com/jobs/view/0",
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.INTERNSHIP,
            ),
            observed_at=now,
        )
    before = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    requested: list[str] = []
    identity = (
        '<h1 class="top-card-layout__title">Software Intern 2027</h1>'
        '<a class="topcard__org-name-link">Synthetic Technology</a>'
    )

    def respond(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        job_id = request.url.path.rsplit("/", 1)[1]
        if job_id == "0" or (
            job_id == "1" and scenario in {"redirects-only", "redirect-then-unavailable"}
        ):
            return httpx.Response(301)
        if scenario == "rate-limit-first" or job_id == "3":
            return httpx.Response(429)
        if job_id == "2":
            if scenario == "detail-301":
                return httpx.Response(
                    301 if "/jobs-guest/" in request.url.path else 200, text=identity
                )
            if scenario == "timeout":
                raise httpx.ReadTimeout("synthetic-private-timeout")
            if scenario == "transport":
                raise httpx.ReadError("synthetic-private-transport")
            if scenario == "unexpected":
                raise RuntimeError("synthetic-private-unexpected")
            if scenario == "invalid-html":
                return httpx.Response(200, text="<html>Generic shell</html>")
            if scenario == "challenge-first":
                return httpx.Response(200, text="<html>Security verification challenge-page</html>")
            status = {
                "429-only": 410,
                "redirects-only": 301,
                "redirect-then-unavailable": 410,
                "http-status": 503,
                "public-301": 301,
                "public-302": 302,
                "403-first": 403,
            }
            return httpx.Response(status[scenario])
        return httpx.Response(200, text=identity)

    async def audit() -> None:
        configured = settings.model_copy(update={"max_concurrency": 1, "max_retries": 0})
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client,
            HttpFetcher(configured, client=client) as fetcher,
        ):
            result = await audit_job_availability(
                settings=configured,
                repository=repository,
                fetcher=fetcher,
                observed_at=now + timedelta(minutes=1),
            )
        eligible = scenario in {"429-only", "public-301", "redirect-then-unavailable"}
        assert result.source_blocked
        assert result.rate_limited_partial == eligible
        assert result.exit_code == (4 if eligible else 1)
        assert result.available == int(
            scenario not in {"rate-limit-first", "redirects-only", "redirect-then-unavailable"}
        )
        assert result.deleted == int(scenario in {"429-only", "redirect-then-unavailable"})
        assert result.rate_limited == int(
            scenario not in {"403-first", "challenge-first", "public-302", "detail-301"}
        )
        redirects: tuple[str, ...] = ("0",) if public_redirect else ()
        if scenario in {"redirects-only", "redirect-then-unavailable"}:
            redirects += ("1",)
        if scenario in {"public-301", "redirects-only"}:
            redirects += ("2",)
        assert result.listing_redirect_ids == redirects
        assert set(redirects).issubset(result.inconclusive_ids)

    asyncio.run(audit())
    assert requested[-1] == (
        "/jobs/view/1"
        if scenario == "rate-limit-first"
        else "/jobs/view/2"
        if scenario in {"403-first", "challenge-first", "public-302"}
        else "/jobs-guest/jobs/api/jobPosting/2"
        if scenario == "detail-301"
        else "/jobs/view/3"
    )
    after = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    assert after["4"] == before["4"]
    if public_redirect:
        assert after["0"] == before["0"]
        assert requested.count("/jobs/view/0") == 1
        assert "/jobs-guest/jobs/api/jobPosting/0" not in requested
    with session_factory() as session:
        if public_redirect:
            redirected = session.get(JobRow, "0")
            assert redirected is not None
            assert redirected.last_availability_checked_at is not None
            assert ensure_utc(redirected.last_availability_checked_at) == now + timedelta(minutes=1)
        for job_id in ("3", "4"):
            row = session.get(JobRow, job_id)
            assert row is not None
            assert row.last_availability_checked_at is None


@pytest.mark.parametrize(
    "failure",
    [
        "timeout",
        "transport",
        "unexpected",
        "http-status",
        "invalid-html",
        "403",
        "403-before-429",
        "challenge",
        "public-shell",
        "public-301",
        "retry-backoff",
        "retry-pacing",
    ],
)
def test_rate_limit_cannot_mask_an_independent_concurrent_audit_failure(
    partial_audit_state: tuple[Repository, datetime],
    session_factory: sessionmaker[Session],
    settings: Settings,
    failure: str,
) -> None:
    repository, now = partial_audit_state
    before = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    requested: list[str] = []
    failure_started = asyncio.Event()
    denial_returned = asyncio.Event()
    rate_limit_started = asyncio.Event()
    retry_pending = asyncio.Event()
    identity = (
        '<h1 class="top-card-layout__title">Software Intern 2027</h1>'
        '<a class="topcard__org-name-link">Synthetic Technology</a>'
    )

    async def respond(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path == "/jobs/view/1":
            return httpx.Response(200, text=identity)
        if request.url.path == "/jobs-guest/jobs/api/jobPosting/1":
            await denial_returned.wait()
            return httpx.Response(200, text=identity)
        if request.url.path == "/jobs/view/3":
            rate_limit_started.set()
            await failure_started.wait()
            denial_returned.set()
            return httpx.Response(429)
        if request.url.path == "/jobs/view/2" and failure not in {"public-shell", "public-301"}:
            return httpx.Response(200, text=identity)
        if failure == "403-before-429":
            await rate_limit_started.wait()
            failure_started.set()
            return httpx.Response(403)
        if failure in {"retry-backoff", "retry-pacing"}:
            await rate_limit_started.wait()
            retry_pending.set()
            return httpx.Response(503)
        failure_started.set()
        await denial_returned.wait()
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic-private-timeout")
        if failure == "transport":
            raise httpx.ReadError("synthetic-private-transport")
        if failure == "unexpected":
            raise RuntimeError("synthetic-private-unexpected")
        if failure == "403":
            return httpx.Response(403)
        if failure == "challenge":
            return httpx.Response(200, text="<html>Security verification challenge-page</html>")
        if failure == "public-shell":
            return httpx.Response(200, text=identity)
        if failure == "public-301":
            return httpx.Response(301)
        return httpx.Response(
            503 if failure == "http-status" else 200, text="<html>Generic shell</html>"
        )

    async def wait_for_source_stop(delay: float) -> None:
        if retry_pending.is_set() and (failure == "retry-backoff" or delay > 0):
            failure_started.set()
            await denial_returned.wait()

    async def audit() -> None:
        configured = settings.model_copy(
            update={
                "max_concurrency": 3,
                "max_retries": 2,
                "rate_limit_seconds": int(failure == "retry-pacing"),
            }
        )
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client,
            HttpFetcher(configured, client=client, sleep=wait_for_source_stop) as fetcher,
        ):
            result = await audit_job_availability(
                settings=configured,
                repository=repository,
                fetcher=fetcher,
                observed_at=now + timedelta(minutes=1),
            )
        assert result.source_blocked
        assert result.available == 1
        assert result.exit_code == (4 if failure in {"public-shell", "public-301"} else 1)
        assert result.rate_limited_partial == (failure in {"public-shell", "public-301"})
        assert result.listing_redirect_ids == (("2",) if failure == "public-301" else ())
        assert result.deleted == 0
        assert "synthetic-private" not in str(result)
        if failure in {"403", "403-before-429"}:
            assert result.blocked_reason == "HTTP 403"

    asyncio.run(asyncio.wait_for(audit(), timeout=5))
    after = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
    assert after["1"].last_seen_at == now + timedelta(minutes=1)
    for job_id in ("2", "3", "4"):
        assert after[job_id] == before[job_id]
    with session_factory() as session:
        for job_id in ("3", "4"):
            row = session.get(JobRow, job_id)
            assert row is not None
            assert row.last_availability_checked_at is None
        row = session.get(JobRow, "2")
        assert row is not None
        assert (row.last_availability_checked_at is None) == (
            failure in {"403", "403-before-429", "challenge", "public-shell"}
        )
    assert "/jobs/view/4" not in requested
    if failure in {"public-shell", "public-301"}:
        assert "/jobs-guest/jobs/api/jobPosting/2" not in requested
    assert requested.count("/jobs-guest/jobs/api/jobPosting/2") <= 1


@pytest.mark.parametrize("endpoint", ["public", "detail"])
@pytest.mark.parametrize("status", [401, 403, 404, 410, 429, 500, 503, None])
def test_availability_errors_are_not_closure_evidence_except_not_found_or_gone(
    session_factory: sessionmaker[Session],
    settings: Settings,
    endpoint: str,
    status: int | None,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Synthetic Technology",
        title="Software Intern 2027",
        location="Berlin, Germany",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )
    repository.upsert_manual_job(job, observed_at=now)
    before = repository.list_all_jobs()
    requested: list[str] = []

    class FailingFetcher:
        async def get_text(self, url: str) -> str:
            requested.append(url)
            if endpoint == "public" or url == LINKEDIN_DETAIL_ENDPOINT.format(
                job_id=job.linkedin_job_id
            ):
                if status is None:
                    raise RuntimeError("synthetic unexpected client failure")
                raise FetchError("http_status", "synthetic", status_code=status)
            return "<html>Public listing shell</html>"

    result = asyncio.run(
        audit_job_availability(
            settings=settings,
            repository=repository,
            fetcher=FailingFetcher(),
            observed_at=now + timedelta(minutes=1),
        )
    )
    assert result.checked == 1
    assert result.available == result.reopened == 0
    assert len(requested) == (1 if endpoint == "public" else 2)
    if status in {404, 410}:
        assert result.deleted == 1
        assert result.exit_code == 0
        assert repository.list_all_jobs() == []
    else:
        assert result.deleted == 0
        assert result.inconclusive_ids == (job.linkedin_job_id,)
        assert result.exit_code == 2
        assert repository.list_all_jobs() == before
