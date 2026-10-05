"""Offline coverage for bounded backlog draining and persistent audit scheduling."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.settings import Settings
from opportunities.database.models import JobRow
from opportunities.database.repository import Repository
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.availability import audit_job_availability
from opportunities.scrapers.http import FetchError
from opportunities.utils.time import ensure_utc

NOW = datetime(2026, 10, 5, tzinfo=UTC)
IDENTITY = (
    '<h1 class="top-card-layout__title">Software Intern 2027</h1>'
    '<a class="topcard__org-name-link">Synthetic Technology</a>'
)


class RecordingFetcher:
    def __init__(self, error: str | None = None) -> None:
        self.requested: list[str] = []
        self.error = error

    async def get_text(self, url: str) -> str:
        self.requested.append(url)
        if self.error:
            raise FetchError(self.error, "synthetic failure")
        return IDENTITY


def seed(repository: Repository, search: LinkedInSearchConfig, count: int) -> None:
    repository.sync_searches([search], NOW)
    repository.persist_success(
        run_id="seed",
        search=search,
        jobs=[
            DiscoveredJob(
                linkedin_job_id=str(index + 1),
                company="Synthetic Technology",
                title="Software Intern 2027",
                location="Berlin, Germany",
                link=f"https://www.linkedin.com/jobs/view/{index + 1}",
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.INTERNSHIP,
            )
            for index in range(count)
        ],
        confirmed_unavailable_ids=(),
        found_count=count,
        excluded_count=0,
        warning_count=0,
        started_at=NOW,
        finished_at=NOW,
        duration_ms=0,
    )


def test_initial_backlog_is_capped_and_rotates_across_five_runs(
    session_factory: sessionmaker[Session], settings: Settings, search: LinkedInSearchConfig
) -> None:
    repository = Repository(session_factory, settings)
    seed(repository, search, 1062)
    checked: set[str] = set()
    for day, expected in enumerate((250, 250, 250, 250, 62)):
        fetcher = RecordingFetcher()
        result = asyncio.run(
            audit_job_availability(
                settings=settings,
                repository=repository,
                fetcher=fetcher,
                observed_at=NOW + timedelta(days=day),
            )
        )
        ids = {url.rsplit("/", 1)[1] for url in fetcher.requested}
        assert not ids & checked
        checked.update(ids)
        assert result.checked == result.available == expected
        assert result.deferred == max(1062 - (day + 1) * 250, 0)
        assert result.exit_code == 0  # A planned cap is not a source failure.
        assert len(fetcher.requested) == expected * 2
    assert len(checked) == 1062

    # Rebuilding Repository proves the schedule is durable, not process-local.
    repository = Repository(session_factory, settings)
    jobs, deferred = repository.availability_batch(NOW + timedelta(days=5))
    assert len(jobs) == 250
    assert deferred == 0
    assert all(job.last_seen_at == NOW for job in jobs)


def test_due_boundary_and_ordering_do_not_use_discovery_timestamps(
    session_factory: sessionmaker[Session], settings: Settings, search: LinkedInSearchConfig
) -> None:
    configured = settings.model_copy(update={"availability_max_jobs": 1})
    repository = Repository(session_factory, configured)
    seed(repository, search, 3)
    with session_factory.begin() as session:
        third = session.get(JobRow, "3")
        assert third is not None
        third.first_seen_at = NOW - timedelta(days=30)
        third.status = "closed"  # Never-audited closed/manual rows remain eligible.
    jobs, deferred = repository.availability_batch(NOW)
    assert [job.linkedin_job_id for job in jobs] == ["3"]  # Older posting beats lower ID.
    assert deferred == 2
    with session_factory.begin() as session:
        first = session.get(JobRow, "1")
        second = session.get(JobRow, "2")
        assert first is not None
        assert second is not None
        first.last_availability_checked_at = NOW
        second.last_availability_checked_at = NOW - timedelta(days=1)

    jobs, deferred = repository.availability_batch(NOW + timedelta(days=5))
    assert [job.linkedin_job_id for job in jobs] == ["3"]
    assert deferred == 2
    repository.apply_availability_audit(
        available_ids=("3",), unavailable_ids=(), observed_at=NOW + timedelta(hours=1)
    )
    jobs, deferred = repository.availability_batch(NOW + timedelta(days=5) - timedelta(seconds=1))
    assert [job.linkedin_job_id for job in jobs] == ["2"]
    assert deferred == 0
    repository.apply_availability_audit(
        available_ids=("2",), unavailable_ids=(), observed_at=NOW + timedelta(hours=1)
    )
    jobs, deferred = repository.availability_batch(NOW + timedelta(days=5))
    assert [job.linkedin_job_id for job in jobs] == ["1"]
    assert deferred == 0

    # Fresh search observations do not postpone the public-page audit.
    existing = repository.list_all_jobs()[0]
    repository.upsert_manual_job(
        DiscoveredJob(**existing.model_dump(include=set(DiscoveredJob.model_fields))),
        observed_at=NOW + timedelta(days=4),
    )
    jobs, _ = repository.availability_batch(NOW + timedelta(days=5))
    assert jobs[0].linkedin_job_id == "1"


@pytest.mark.parametrize("error", [None, "transient_http", "listing_redirect", "source_blocked"])
def test_attempts_rotate_without_changing_inconclusive_lifecycle_or_stamping_denials(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    error: str | None,
) -> None:
    configured = settings.model_copy(update={"availability_max_jobs": 1})
    repository = Repository(session_factory, configured)
    seed(repository, search, 2)
    before = repository.list_all_jobs()
    fetcher = RecordingFetcher(error)
    result = asyncio.run(
        audit_job_availability(
            settings=configured,
            repository=repository,
            fetcher=fetcher,
            observed_at=NOW + timedelta(hours=1),
        )
    )
    assert result.checked == 1
    assert result.deferred == 1
    assert result.source_blocked == (error == "source_blocked")
    if error:
        assert repository.list_all_jobs() == before
    with session_factory() as session:
        first = session.get(JobRow, "1")
        second = session.get(JobRow, "2")
        assert first is not None
        assert second is not None
        assert second.last_availability_checked_at is None
        if error == "source_blocked":
            assert first.last_availability_checked_at is None
        else:
            assert first.last_availability_checked_at is not None
            assert ensure_utc(first.last_availability_checked_at) == NOW + timedelta(hours=1)
    jobs, _ = repository.availability_batch(NOW + timedelta(days=1))
    assert jobs[0].linkedin_job_id == ("1" if error == "source_blocked" else "2")


@pytest.mark.parametrize("confirmed", ["available", "unavailable"])
def test_inconclusive_and_confirmed_outcomes_cannot_overlap(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    confirmed: str,
) -> None:
    repository = Repository(session_factory, settings)
    seed(repository, search, 1)
    before = repository.list_all_jobs()
    with pytest.raises(ValueError, match="must not overlap"):
        repository.apply_availability_audit(
            available_ids=("1",) if confirmed == "available" else (),
            unavailable_ids=("1",) if confirmed == "unavailable" else (),
            inconclusive_ids=("1",),
            observed_at=NOW,
        )
    assert repository.list_all_jobs() == before
    assert len(repository.availability_batch(NOW)[0]) == 1


def test_no_due_jobs_produces_no_requests_and_audit_timestamps_are_monotonic(
    session_factory: sessionmaker[Session], settings: Settings, search: LinkedInSearchConfig
) -> None:
    repository = Repository(session_factory, settings)
    seed(repository, search, 1)
    repository.apply_availability_audit(available_ids=("1",), unavailable_ids=(), observed_at=NOW)
    repository.apply_availability_audit(
        available_ids=(),
        unavailable_ids=(),
        inconclusive_ids=("1",),
        observed_at=NOW - timedelta(days=1),
    )
    fetcher = RecordingFetcher()
    result = asyncio.run(
        audit_job_availability(
            settings=settings, repository=repository, fetcher=fetcher, observed_at=NOW
        )
    )
    assert result.checked == result.deferred == 0
    assert result.exit_code == 0
    assert fetcher.requested == []
    assert repository.availability_batch(NOW + timedelta(days=5) - timedelta(seconds=1)) == ([], 0)
    assert len(repository.availability_batch(NOW + timedelta(days=5))[0]) == 1
