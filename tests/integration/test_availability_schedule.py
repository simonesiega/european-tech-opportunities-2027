"""Offline coverage for bounded backlog draining and persistent audit scheduling."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.settings import Settings
from opportunities.database.models import JobRow
from opportunities.database.repository import Repository
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.database.snapshots import create_snapshot, verify_snapshot
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


def test_700_jobs_rotate_across_20_daily_runs(
    session_factory: sessionmaker[Session], settings: Settings, search: LinkedInSearchConfig
) -> None:
    repository = Repository(session_factory, settings)
    seed(repository, search, 700)
    ordered = sorted(str(index + 1) for index in range(700))
    last_checked: dict[str, int] = {}
    for day in range(20):
        # A fresh repository per run must resume from SQLite, not an in-memory cursor.
        repository = Repository(session_factory, settings)
        fetcher = RecordingFetcher()
        result = asyncio.run(
            audit_job_availability(
                settings=settings,
                repository=repository,
                fetcher=fetcher,
                observed_at=NOW + timedelta(days=day),
            )
        )
        ids = [url.rsplit("/", 1)[1] for url in fetcher.requested[::2]]
        offset = (day % 14) * 50
        assert ids == ordered[offset : offset + 50]
        assert result.checked == result.available == 50
        assert result.deleted == result.reopened == result.blocked == 0
        assert result.exit_code == 0
        assert len(fetcher.requested) == 100
        for job_id in ids:
            if job_id in last_checked:
                assert day - last_checked[job_id] >= 5
            last_checked[job_id] = day
        with session_factory() as session:
            for job_id in ids:
                row = session.get(JobRow, job_id)
                assert row is not None
                assert row.last_availability_checked_at is not None
                assert ensure_utc(row.last_availability_checked_at) == NOW + timedelta(days=day)
        if day == 13:
            assert len(last_checked) == 700
        assert len(repository.list_open_jobs()) == 700
    assert len(last_checked) == 700


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


def test_new_jobs_and_deferred_denials_recover_without_starvation(
    session_factory: sessionmaker[Session], settings: Settings, search: LinkedInSearchConfig
) -> None:
    repository = Repository(session_factory, settings)
    seed(repository, search, 700)
    before = repository.list_all_jobs()
    denied = RecordingFetcher("source_blocked")
    result = asyncio.run(
        audit_job_availability(
            settings=settings, repository=repository, fetcher=denied, observed_at=NOW
        )
    )
    assert result.checked == result.blocked == 1
    assert result.deferred == 699
    assert result.inconclusive_ids == ()
    assert len(denied.requested) == 1
    assert repository.list_all_jobs() == before
    original = [job.linkedin_job_id for job in repository.availability_batch(NOW)[0]]
    checked: set[str] = set()
    for day in range(15):
        if day == 1:
            existing = repository.list_all_jobs()[0]
            repository.upsert_manual_job(
                DiscoveredJob(
                    **{
                        **existing.model_dump(include=set(DiscoveredJob.model_fields)),
                        "linkedin_job_id": "9999",
                        "link": "https://www.linkedin.com/jobs/view/9999",
                        "posted_at": None,
                    }
                ),
                observed_at=NOW + timedelta(days=day),
            )
        # Inconclusive evidence must drain the queue without lifecycle mutations.
        fetcher = RecordingFetcher("transient_http")
        result = asyncio.run(
            audit_job_availability(
                settings=settings,
                repository=repository,
                fetcher=fetcher,
                observed_at=NOW + timedelta(days=day),
            )
        )
        ids = [url.rsplit("/", 1)[1] for url in fetcher.requested]
        if day == 0:
            assert ids == original
        if day < 14:
            assert not checked.intersection(ids)
        if day == 14:
            assert ids[0] == "9999"  # Never checked beats the oldest previous attempt.
        checked.update(ids)
        assert result.checked == 50
        assert result.deleted == result.reopened == result.blocked == 0
        assert result.exit_code == 2
    assert checked == {job.linkedin_job_id for job in before} | {"9999"}
    assert repository.list_all_jobs()[:700] == before


def test_interrupted_audit_does_not_stamp_completed_or_unprocessed_jobs(
    session_factory: sessionmaker[Session], settings: Settings, search: LinkedInSearchConfig
) -> None:
    repository = Repository(session_factory, settings)
    seed(repository, search, 3)
    before = repository.list_all_jobs()

    async def interrupt() -> None:
        interrupted = asyncio.Event()

        class InterruptedFetcher(RecordingFetcher):
            async def get_text(self, url: str) -> str:
                if url.endswith("/2"):
                    interrupted.set()
                    await asyncio.Event().wait()
                return await super().get_text(url)

        configured = settings.model_copy(update={"max_concurrency": 1})
        task = asyncio.create_task(
            audit_job_availability(
                settings=configured,
                repository=repository,
                fetcher=InterruptedFetcher(),
                observed_at=NOW,
            )
        )
        await interrupted.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(asyncio.wait_for(interrupt(), timeout=5))
    assert repository.list_all_jobs() == before
    assert len(repository.availability_batch(NOW)[0]) == 3
    with session_factory() as session:
        assert all(row.last_availability_checked_at is None for row in session.query(JobRow))


def test_verified_snapshot_restores_audit_rotation(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    seed(repository, search, 700)
    asyncio.run(
        audit_job_availability(
            settings=settings, repository=repository, fetcher=RecordingFetcher(), observed_at=NOW
        )
    )
    expected, expected_deferred = repository.availability_batch(NOW + timedelta(days=1))
    snapshot = tmp_path / "verified.db"
    create_snapshot(
        tmp_path / "opportunities.db",
        snapshot,
        tmp_path / "verified.manifest.json",
        key_prefix="snapshots",
        retention_days=365,
        repository="synthetic/repository",
        run_id="1",
        run_attempt=1,
        created_at=NOW + timedelta(days=1),
    )
    verify_snapshot(snapshot, tmp_path / "verified.manifest.json")
    restored_engine = create_database_engine(f"sqlite:///{snapshot.as_posix()}")
    try:
        restored = Repository(create_session_factory(restored_engine), settings)
        jobs, deferred = restored.availability_batch(NOW + timedelta(days=1))
        assert jobs == expected
        assert deferred == expected_deferred == 600
        with create_session_factory(restored_engine)() as session:
            stamped = [row for row in session.query(JobRow) if row.last_availability_checked_at]
            assert len(stamped) == 50
            for row in stamped:
                assert row.last_availability_checked_at is not None
                assert ensure_utc(row.last_availability_checked_at) == NOW
    finally:
        restored_engine.dispose()
