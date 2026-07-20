from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.settings import Settings
from opportunities.database.models import JobRow, JobSearchRow
from opportunities.database.repository import Repository
from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.availability import audit_job_availability
from opportunities.scrapers.http import FetchError
from opportunities.scrapers.linkedin import LINKEDIN_DETAIL_ENDPOINT


class FakeAvailabilityFetcher:
    def __init__(self) -> None:
        self.requested: list[str] = []

    async def get_text(self, url: str) -> str:
        self.requested.append(url)
        if url.endswith("2222222222"):
            raise FetchError("http_status", "not found", status_code=404)
        if url.endswith("3333333333"):
            raise FetchError("transient_http", "server error", status_code=503)
        if url.endswith("4444444444"):
            return "<html><body>Security verification challenge-page</body></html>"
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
        for job_id in ("1111111111", "2222222222", "3333333333", "4444444444")
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

    assert result.checked == 4
    assert result.available == 1
    assert result.deleted == 1
    assert result.reopened == 1
    assert result.inconclusive_ids == ("3333333333", "4444444444")
    assert result.exit_code == 2
    assert set(fetcher.requested) == {
        LINKEDIN_DETAIL_ENDPOINT.format(job_id=job.linkedin_job_id) for job in jobs
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
