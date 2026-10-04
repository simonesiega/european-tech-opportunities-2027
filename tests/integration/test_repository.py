from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.settings import Settings
from opportunities.database.models import (
    DataQualitySnapshotRow,
    JobRow,
    JobSearchRow,
    SearchRow,
    SearchRunRow,
)
from opportunities.database.repository import PersistSummary, Repository
from opportunities.models.data_quality import (
    JOB_FIELDS,
    PARSER_FIELDS,
    DataQualitySnapshot,
    SearchQualityCounts,
)
from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.utils.time import ensure_utc


@pytest.fixture
def collected_job() -> DiscoveredJob:
    return DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Synthetic Technology",
        title="Software Intern 2027",
        location="Berlin, Germany",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )


def persist_search(
    repository: Repository,
    search: LinkedInSearchConfig,
    run: int,
    observed: datetime,
    jobs: list[DiscoveredJob],
    unavailable: tuple[str, ...] = (),
    *,
    finished: datetime | None = None,
) -> PersistSummary:
    """Use search start as observation time, allowing completion to occur later."""
    return repository.persist_success(
        run_id=f"run-{run}",
        search=search,
        jobs=jobs,
        confirmed_unavailable_ids=unavailable,
        found_count=len(jobs),
        excluded_count=0,
        warning_count=0,
        started_at=observed,
        finished_at=finished or observed,
        duration_ms=1,
    )


def test_overlapping_search_timestamps_remain_monotonic(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    earlier = datetime(2026, 7, 1, tzinfo=UTC)
    later = earlier + timedelta(minutes=5)
    second = search.model_copy(update={"slug": "second-search", "keywords": "software intern"})
    repository.sync_searches([search, second], earlier)
    posted_at = earlier - timedelta(days=10)
    job = collected_job.model_copy(
        update={
            "industries": "Software Development",
            "start_date": "Summer 2027",
            "posted_at": posted_at,
        }
    )
    persist_search(repository, search, 1, later, [job])
    persist_search(
        repository,
        second,
        2,
        earlier,
        [job.model_copy(update={"industries": None, "start_date": None, "posted_at": later})],
    )
    stored = repository.list_open_jobs()[0]
    assert stored.first_seen_at == posted_at
    assert stored.last_seen_at == later
    assert stored.updated_at == later
    assert stored.industries == "Software Development"
    assert stored.employment_type == EmploymentType.INTERNSHIP
    assert stored.start_date == "Summer 2027"
    health = repository.search_health()
    assert set(health) == {search.slug, second.slug}
    assert health[search.slug].accepted_count == 1


def test_newer_rediscovery_updates_fields_and_preserves_missing_optional_metadata(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 1, tzinfo=UTC)
    repository.sync_searches([search], now)
    job = collected_job.model_copy(
        update={"industries": "Software Development", "start_date": "Summer 2027"}
    )
    assert persist_search(repository, search, 1, now, [job]).new == 1
    later = now + timedelta(minutes=5)
    changed = job.model_copy(
        update={"company": "Updated Technology", "industries": None, "start_date": None}
    )
    assert persist_search(repository, search, 2, later, [changed]).updated == 1
    assert (
        persist_search(repository, search, 3, later + timedelta(minutes=1), [changed]).updated == 0
    )
    stored = repository.list_open_jobs()[0]
    assert stored.company == "Updated Technology"
    assert stored.industries == "Software Development"
    assert stored.start_date == "Summer 2027"
    assert stored.last_seen_at == later + timedelta(minutes=1)
    assert stored.updated_at == later


def test_overlapping_search_404_cannot_override_a_newer_valid_observation(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 1, tzinfo=UTC)
    second = search.model_copy(update={"slug": "second-search", "keywords": "software intern"})
    repository.sync_searches([search, second], now)
    persist_search(repository, search, 1, now, [collected_job])
    # Persist in finish order: the later-finishing search carries the older 404.
    persist_search(repository, second, 2, now + timedelta(minutes=2), [collected_job])
    persist_search(
        repository,
        search,
        3,
        now + timedelta(minutes=1),
        [],
        (collected_job.linkedin_job_id,),
        finished=now + timedelta(minutes=3),
    )
    assert [job.linkedin_job_id for job in repository.list_open_jobs()] == [
        collected_job.linkedin_job_id
    ]
    with session_factory() as session:
        alias = session.get(JobSearchRow, (search.slug, collected_job.linkedin_job_id))
        assert alias is not None
        assert alias.active
        assert alias.unavailable_confirmations == 0


def test_slow_search_early_valid_detail_cannot_reopen_after_later_404(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 1, tzinfo=UTC)
    slow = search.model_copy(update={"slug": "slow-search", "keywords": "software intern"})
    repository.sync_searches([search, slow], now)
    unavailable = (collected_job.linkedin_job_id,)
    persist_search(repository, search, 1, now, [collected_job])
    persist_search(repository, search, 2, now + timedelta(minutes=1), [], unavailable)
    # Start time, not the slow search's later finish, governs evidence freshness.
    persist_search(
        repository,
        search,
        3,
        now + timedelta(minutes=3),
        [],
        unavailable,
        finished=now + timedelta(minutes=4),
    )
    persist_search(
        repository,
        slow,
        4,
        now + timedelta(minutes=2),
        [collected_job],
        finished=now + timedelta(minutes=5),
    )
    assert repository.list_open_jobs() == []
    with session_factory() as session:
        assert session.get(JobSearchRow, (slow.slug, collected_job.linkedin_job_id)) is None


def test_stale_observations_cannot_overwrite_metadata_or_newer_closure(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    earlier = datetime(2026, 7, 1, tzinfo=UTC)
    later = earlier + timedelta(minutes=5)
    unavailable = (collected_job.linkedin_job_id,)
    repository.sync_searches([search], earlier)
    persist_search(repository, search, 1, later, [collected_job])
    persist_search(
        repository,
        search,
        2,
        earlier,
        [collected_job.model_copy(update={"company": "Stale Technology"})],
    )
    persist_search(repository, search, 3, earlier, [], unavailable)
    assert repository.list_open_jobs()[0].company == collected_job.company
    with session_factory() as session:
        alias = session.get(JobSearchRow, (search.slug, collected_job.linkedin_job_id))
        assert alias is not None
        assert alias.unavailable_confirmations == 0
    persist_search(repository, search, 4, later + timedelta(minutes=1), [], unavailable)
    persist_search(repository, search, 5, later + timedelta(minutes=2), [], unavailable)
    assert repository.list_open_jobs() == []
    persist_search(repository, search, 6, earlier, [collected_job])
    assert repository.list_open_jobs() == []


def test_distinct_linkedin_ids_are_not_fuzzy_merged_and_explicit_404s_close(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 1, tzinfo=UTC)
    repository.sync_searches([search], now)
    # Only IDs and matching URLs differ; display metadata cannot supply identity.
    jobs = [
        collected_job.model_copy(
            update={
                "linkedin_job_id": job_id,
                "link": f"https://www.linkedin.com/jobs/view/{job_id}",
            }
        )
        for job_id in ("1111111111", "2222222222")
    ]
    persist_search(repository, search, 1, now, jobs)
    assert len(repository.list_open_jobs()) == 2
    for run in (2, 3):
        persist_search(repository, search, run, now + timedelta(days=run), [], ("1111111111",))
    assert {job.linkedin_job_id for job in repository.list_open_jobs()} == {"2222222222"}


@pytest.mark.parametrize(
    "job_ids",
    [
        ("3333333333", "1111111111", "2222222222"),
        ("2222222222", "3333333333", "1111111111"),
    ],
)
def test_open_jobs_with_identical_display_fields_use_identifier_order(
    session_factory: sessionmaker[Session],
    settings: Settings,
    collected_job: DiscoveredJob,
    job_ids: tuple[str, ...],
) -> None:
    repository = Repository(session_factory, settings)
    observed_at = datetime(2026, 7, 20, tzinfo=UTC)
    for job_id in job_ids:
        job = collected_job.model_copy(
            update={
                "linkedin_job_id": job_id,
                "link": f"https://www.linkedin.com/jobs/view/{job_id}",
            }
        )
        repository.upsert_manual_job(job, observed_at=observed_at)

    assert [job.linkedin_job_id for job in repository.list_open_jobs()] == sorted(job_ids)


def test_manual_upsert_preserves_lifecycle_metadata_and_adds_no_provenance(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    observed_at = datetime(2026, 7, 10, 12, tzinfo=UTC)
    posted_at = observed_at - timedelta(days=10)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        industries="Software Development",
        employment_type=EmploymentType.INTERNSHIP,
        start_date="Summer 2027",
        posted_at=posted_at,
    )

    assert repository.upsert_manual_job(job, observed_at=observed_at).new == 1
    stored = repository.list_open_jobs()[0]
    assert stored.first_seen_at == posted_at
    assert stored.last_seen_at == observed_at
    assert stored.updated_at == observed_at
    assert stored.status == JobStatus.OPEN
    assert repository.stats().successful_runs == 0
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(JobSearchRow)) == 0
        assert session.scalar(select(func.count()).select_from(SearchRunRow)) == 0

    # Seed closure directly in the disposable database to isolate the manual-write guard.
    with session_factory.begin() as session:
        row = session.get(JobRow, job.linkedin_job_id)
        assert row is not None
        row.status = JobStatus.CLOSED.value
        row.updated_at = observed_at + timedelta(hours=1)

    updated_at = observed_at + timedelta(days=1)
    changed = job.model_copy(
        update={
            "company": "Example Technology Ltd",
            "title": "Graduate Software Engineer 2027",
            "employment_type": EmploymentType.NEW_GRAD,
            "industries": None,
            "start_date": None,
            "posted_at": updated_at,
        }
    )
    with pytest.raises(ValueError, match="availability audit"):
        repository.upsert_manual_job(changed, observed_at=updated_at)
    assert repository.list_open_jobs() == []
    repository.apply_availability_audit(
        available_ids=(job.linkedin_job_id,), unavailable_ids=(), observed_at=updated_at
    )
    summary = repository.upsert_manual_job(changed, observed_at=updated_at)

    assert summary.updated == 1
    assert summary.reopened == 0
    stored = repository.list_open_jobs()[0]
    assert stored.company == "Example Technology Ltd"
    assert stored.title == "Graduate Software Engineer 2027"
    assert stored.employment_type == EmploymentType.NEW_GRAD
    assert stored.industries == "Software Development"
    assert stored.start_date == "Summer 2027"
    assert stored.first_seen_at == posted_at
    assert stored.last_seen_at == updated_at
    assert stored.updated_at == updated_at

    delayed = changed.model_copy(update={"title": "Graduate Software Engineer"})
    repository.upsert_manual_job(delayed, observed_at=observed_at)
    stored = repository.list_open_jobs()[0]
    assert stored.last_seen_at == updated_at
    assert stored.updated_at == updated_at

    discovered_at = updated_at + timedelta(days=1)
    repository.sync_searches([search], discovered_at)
    repository.persist_success(
        run_id="00000000-0000-0000-0000-000000000001",
        search=search,
        jobs=[delayed],
        confirmed_unavailable_ids=(),
        found_count=1,
        excluded_count=0,
        warning_count=0,
        started_at=discovered_at,
        finished_at=discovered_at,
        duration_ms=1,
    )
    with session_factory() as session:
        provenance = session.get(JobSearchRow, (search.slug, job.linkedin_job_id))
        assert provenance is not None
        assert provenance.last_seen_run_id == "00000000-0000-0000-0000-000000000001"


def test_manual_insert_bounds_future_posting_time_by_observation(
    session_factory: sessionmaker[Session], settings: Settings
) -> None:
    repository = Repository(session_factory, settings)
    observed_at = datetime(2026, 7, 10, 12, tzinfo=UTC)
    job = DiscoveredJob(
        linkedin_job_id="2222222222",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        location="Berlin, Germany",
        link="https://www.linkedin.com/jobs/view/2222222222",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
        posted_at=observed_at + timedelta(days=1),
    )

    repository.upsert_manual_job(job, observed_at=observed_at)

    stored = repository.list_open_jobs()[0]
    assert stored.first_seen_at == observed_at
    assert stored.last_seen_at == observed_at


def test_manual_batch_rolls_back_when_later_job_is_closed(
    session_factory: sessionmaker[Session], settings: Settings
) -> None:
    repository = Repository(session_factory, settings)
    observed_at = datetime(2026, 7, 10, 12, tzinfo=UTC)
    first = DiscoveredJob(
        linkedin_job_id="3333333333",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/3333333333",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )
    second = first.model_copy(
        update={
            "linkedin_job_id": "4444444444",
            "link": "https://www.linkedin.com/jobs/view/4444444444",
        }
    )
    repository.upsert_manual_job(second, observed_at=observed_at)
    with session_factory.begin() as session:
        row = session.get(JobRow, second.linkedin_job_id)
        assert row is not None
        row.status = JobStatus.CLOSED.value

    # Rejecting the second row must also undo the valid first row's insertion.
    with pytest.raises(ValueError, match="availability audit"):
        repository.upsert_manual_jobs([first, second], observed_at=observed_at + timedelta(hours=1))

    assert repository.list_open_jobs() == []
    assert [job.linkedin_job_id for job in repository.list_all_jobs()] == ["4444444444"]


def test_manual_batch_rejects_duplicate_identity_without_writing(
    session_factory: sessionmaker[Session], settings: Settings
) -> None:
    repository = Repository(session_factory, settings)
    observed_at = datetime(2026, 7, 10, 12, tzinfo=UTC)
    job = DiscoveredJob(
        linkedin_job_id="5555555555",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/5555555555",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )

    with pytest.raises(ValueError, match="duplicate LinkedIn job identity"):
        repository.upsert_manual_jobs([job, job], observed_at=observed_at)

    assert repository.list_all_jobs() == []


@pytest.mark.parametrize("offset", [-5, 2])
def test_repository_persists_run_and_provenance_timestamps_in_utc(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
    offset: int,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, 12, tzinfo=UTC)
    observed = now.astimezone(timezone(timedelta(hours=offset)))
    repository.sync_searches([search], observed)
    persist_search(
        repository, search, 1, observed, [collected_job], finished=observed + timedelta(minutes=1)
    )
    repository.persist_failure(
        run_id="failure",
        search_slug=search.slug,
        started_at=observed + timedelta(minutes=2),
        finished_at=observed + timedelta(minutes=3),
        duration_ms=1,
        error_code="synthetic",
        error_message="synthetic failure",
    )
    assert repository.stats().last_success_at == now + timedelta(minutes=1)
    with session_factory() as session:
        definition = session.get(SearchRow, search.slug)
        success = session.get(SearchRunRow, "run-1")
        failure = session.get(SearchRunRow, "failure")
        alias = session.get(JobSearchRow, (search.slug, collected_job.linkedin_job_id))
        assert definition is not None
        assert success is not None
        assert failure is not None
        assert alias is not None
        assert ensure_utc(definition.updated_at) == now
        assert ensure_utc(success.started_at) == now
        assert ensure_utc(success.finished_at) == now + timedelta(minutes=1)
        assert ensure_utc(failure.started_at) == now + timedelta(minutes=2)
        assert ensure_utc(failure.finished_at) == now + timedelta(minutes=3)
        assert ensure_utc(alias.first_seen_at) == ensure_utc(alias.last_seen_at) == now
    for run in (2, 3):
        persist_search(
            repository,
            search,
            run,
            now + timedelta(minutes=10 + run),
            [],
            (collected_job.linkedin_job_id,),
        )
    assert repository.list_all_jobs()[0].status == JobStatus.CLOSED


def test_absence_and_one_closed_search_cannot_close_another_search_active_job(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    other = search.model_copy(update={"slug": "other-search", "keywords": "software graduate"})
    repository.sync_searches([search, other], now)
    persist_search(repository, search, 1, now, [collected_job])
    persist_search(repository, other, 2, now, [collected_job])
    unavailable = (collected_job.linkedin_job_id,)
    for run in (3, 4):
        result = persist_search(
            repository, search, run, now + timedelta(minutes=run), [], unavailable
        )
        assert result.closed == 0
    # Disappearance from the other search is not a second source of closure evidence.
    persist_search(repository, other, 5, now + timedelta(minutes=5), [])
    with session_factory() as session:
        first = session.get(JobSearchRow, (search.slug, collected_job.linkedin_job_id))
        second = session.get(JobSearchRow, (other.slug, collected_job.linkedin_job_id))
        assert first is not None
        assert second is not None
        assert not first.active
        assert second.active
        assert second.unavailable_confirmations == 0
    assert repository.list_all_jobs()[0].status == JobStatus.OPEN
    persist_search(repository, other, 6, now + timedelta(minutes=6), [], unavailable)
    # A fresh rediscovery resets consecutive confirmation evidence for its association.
    persist_search(repository, other, 7, now + timedelta(minutes=7), [collected_job])
    assert (
        persist_search(repository, other, 8, now + timedelta(minutes=8), [], unavailable).closed
        == 0
    )
    assert (
        persist_search(repository, other, 9, now + timedelta(minutes=9), [], unavailable).closed
        == 1
    )
    assert repository.list_open_jobs() == []
    reopened = persist_search(repository, search, 10, now + timedelta(minutes=10), [collected_job])
    assert reopened.reopened == 1
    assert repository.list_open_jobs()[0].first_seen_at == now
    with session_factory() as session:
        alias = session.get(JobSearchRow, (search.slug, collected_job.linkedin_job_id))
        assert alias is not None
        assert alias.active
        assert alias.unavailable_confirmations == 0


def test_search_sync_preserves_retired_history_without_closing_jobs(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    repository.sync_searches([search], now)
    persist_search(repository, search, 1, now, [collected_job])
    updated = search.model_copy(update={"name": "Updated search", "keywords": "new query"})
    repository.sync_searches([updated], now + timedelta(minutes=1))
    with session_factory() as session:
        row = session.get(SearchRow, search.slug)
        assert row is not None
        assert (row.name, row.keywords) == ("Updated search", "new query")
    repository.sync_searches([], now + timedelta(minutes=2))
    assert repository.stats().configured_searches == 0
    assert repository.stats().successful_runs == 1
    assert repository.search_health() == {}
    assert repository.list_open_jobs()[0].linkedin_job_id == collected_job.linkedin_job_id
    with session_factory() as session:
        assert session.get(JobSearchRow, (search.slug, collected_job.linkedin_job_id)) is not None


def test_failed_search_transaction_rolls_back_earlier_job_and_provenance_writes(
    engine: Engine,
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    repository.sync_searches([search], now)
    persist_search(repository, search, 1, now, [collected_job])
    before = repository.list_all_jobs()
    changed = collected_job.model_copy(update={"company": "Must roll back"})
    second = collected_job.model_copy(
        update={
            "linkedin_job_id": "2222222222",
            "link": "https://www.linkedin.com/jobs/view/2222222222",
        }
    )
    # Inject a real SQLite write failure only in this disposable migrated database.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TRIGGER reject_second BEFORE INSERT ON jobs "
            "WHEN NEW.linkedin_job_id = '2222222222' "
            "BEGIN SELECT RAISE(ABORT, 'synthetic write failure'); END"
        )
    with pytest.raises(IntegrityError, match="synthetic write failure"):
        persist_search(repository, search, 2, now + timedelta(minutes=1), [changed, second])
    assert repository.list_all_jobs() == before
    assert repository.stats().successful_runs == 1
    with session_factory() as session:
        assert session.get(SearchRunRow, "run-2") is None
        alias = session.get(JobSearchRow, (search.slug, collected_job.linkedin_job_id))
        assert alias is not None
        assert alias.last_seen_run_id == "run-1"
        assert ensure_utc(alias.last_seen_at) == now
    # The rolled-back transaction must not poison subsequent writes.
    assert persist_search(repository, search, 2, now + timedelta(minutes=2), [changed]).updated == 1


def test_contradictory_availability_evidence_fails_without_writes(
    session_factory: sessionmaker[Session],
    settings: Settings,
    collected_job: DiscoveredJob,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    repository.upsert_manual_job(collected_job, observed_at=now)
    before = repository.list_all_jobs()
    with pytest.raises(ValueError, match="both available and unavailable"):
        repository.apply_availability_audit(
            available_ids=(collected_job.linkedin_job_id,),
            unavailable_ids=(collected_job.linkedin_job_id,),
            observed_at=now,
        )
    assert repository.list_all_jobs() == before


@pytest.mark.parametrize("size", [0, 11])
def test_manual_batch_bounds_fail_before_any_write(
    session_factory: sessionmaker[Session],
    settings: Settings,
    collected_job: DiscoveredJob,
    size: int,
) -> None:
    repository = Repository(session_factory, settings)
    jobs = [
        collected_job.model_copy(
            update={
                "linkedin_job_id": str(1000000000 + index),
                "link": f"https://www.linkedin.com/jobs/view/{1000000000 + index}",
            }
        )
        for index in range(size)
    ]
    with pytest.raises(ValueError, match="1 to 10 jobs"):
        repository.upsert_manual_jobs(jobs, observed_at=datetime(2026, 7, 20, tzinfo=UTC))
    assert repository.list_all_jobs() == []


@pytest.mark.parametrize("payload", ['{"schema_version":true}', '{"schema_version":1.0}'])
def test_data_quality_baseline_rejects_non_integer_schema_versions(
    payload: str, session_factory: sessionmaker[Session], settings: Settings
) -> None:
    repository = Repository(session_factory, settings)

    with pytest.raises(ValueError, match="schema_version"):
        repository.record_data_quality_snapshot(payload)


def test_data_quality_baselines_are_aggregate_bounded_and_newest_first(
    session_factory: sessionmaker[Session], settings: Settings
) -> None:
    repository = Repository(session_factory, settings)
    captured_at = datetime(2026, 7, 1, tzinfo=UTC)

    for index in range(95):
        # Equal timestamps use insertion order; dates, not insertion order, govern retention.
        observation = captured_at + timedelta(seconds=index // 2)
        snapshot = DataQualitySnapshot(
            schema_version=1,
            captured_at=observation,
            search_fingerprints={"test": "0" * 64},
            searches={
                "test": SearchQualityCounts(found_count=index, accepted_count=0, classified_count=0)
            },
            open_job_count=0,
            category_counts={},
            country_counts={},
            field_missing_counts=dict.fromkeys(JOB_FIELDS, 0),
            parser_candidate_count=0,
            parser_missing_counts=dict.fromkeys(PARSER_FIELDS, 0),
        )
        repository.record_data_quality_snapshot(snapshot.model_dump_json())

    # A late write of an old observation must not displace the newest baselines.
    repository.record_data_quality_snapshot(
        snapshot.model_copy(
            update={"captured_at": captured_at - timedelta(days=1)}
        ).model_dump_json()
    )

    baselines = repository.data_quality_baselines()
    assert [json.loads(value)["searches"]["test"]["found_count"] for value in baselines] == [
        94,
        93,
        92,
        91,
        90,
    ]
    with pytest.raises(ValueError, match="128 KiB"):
        repository.record_data_quality_snapshot(" " * 131_073)
    assert repository.data_quality_baselines() == baselines
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(DataQualitySnapshotRow)) == 90
