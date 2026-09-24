from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

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
)


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
        found_count=3,
        excluded_count=0,
        warning_count=0,
        started_at=observed_at,
        finished_at=observed_at,
        duration_ms=1,
    )
    with session_factory.begin() as session:
        closed_job = session.get(JobRow, "1111111111")
        closed_alias = session.get(JobSearchRow, (search.slug, "1111111111"))
        assert closed_job is not None
        assert closed_alias is not None
        closed_job.status = JobStatus.CLOSED.value
        closed_alias.active = False
        closed_alias.unavailable_confirmations = 2

    fetcher = FakeAvailabilityFetcher()
    result = asyncio.run(
        audit_job_availability(
            settings=settings,
            repository=repository,
            fetcher=fetcher,
            observed_at=observed_at,
        )
    )

    assert result.checked == 5
    assert result.available == 1
    assert result.deleted == 2
    assert result.reopened == 1
    assert result.inconclusive_ids == ("3333333333", "4444444444")
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
