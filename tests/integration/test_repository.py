from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.settings import Settings
from opportunities.database.models import JobRow, JobSearchRow, SearchRunRow
from opportunities.database.repository import Repository
from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig


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
    summary = repository.upsert_manual_job(changed, observed_at=updated_at)

    assert summary.updated == 1
    assert summary.reopened == 1
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
