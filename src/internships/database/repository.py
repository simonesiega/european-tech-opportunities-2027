"""Transactional persistence for the focused LinkedIn-to-README pipeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from internships.config.settings import Settings
from internships.database.models import JobRow, JobSearchRow, SearchRow, SearchRunRow
from internships.models.enums import JobStatus
from internships.models.job import DiscoveredJob, StoredJob
from internships.models.raw import KnownJob
from internships.models.search import LinkedInSearchConfig
from internships.utils.time import ensure_utc


@dataclass(frozen=True, slots=True)
class PersistSummary:
    """Summarize database changes from persistence."""

    new: int = 0
    updated: int = 0
    closed: int = 0
    reopened: int = 0

    def __add__(self, other: PersistSummary) -> PersistSummary:
        """Combine two persistence summaries."""
        return PersistSummary(
            new=self.new + other.new,
            updated=self.updated + other.updated,
            closed=self.closed + other.closed,
            reopened=self.reopened + other.reopened,
        )


@dataclass(frozen=True, slots=True)
class DatabaseStats:
    """Summarize aggregate database statistics."""

    total: int
    open: int
    closed: int
    configured_searches: int
    successful_runs: int
    failed_runs: int
    last_success_at: datetime | None


@dataclass(frozen=True, slots=True)
class SearchHealth:
    """Summarize the latest health of a configured search."""

    status: str
    finished_at: datetime
    found_count: int
    accepted_count: int
    excluded_count: int
    error_code: str | None


class Repository:
    """Use one short SQLite transaction per completed LinkedIn search."""

    def __init__(self, factory: sessionmaker[Session], settings: Settings) -> None:
        """Initialize the instance dependencies and state."""
        self.factory = factory
        self.settings = settings

    def sync_searches(self, searches: list[LinkedInSearchConfig], now: datetime) -> None:
        """Synchronize configured searches with database state."""
        active_slugs = {search.slug for search in searches}
        with self.factory.begin() as session:
            for search in searches:
                row = session.get(SearchRow, search.slug)
                digest = _config_hash(search)
                if row is None:
                    session.add(
                        SearchRow(
                            slug=search.slug,
                            name=search.name,
                            keywords=search.keywords,
                            location=search.location,
                            enabled=search.enabled,
                            config_hash=digest,
                            updated_at=now,
                        )
                    )
                else:
                    row.name = search.name
                    row.keywords = search.keywords
                    row.location = search.location
                    row.enabled = search.enabled
                    row.config_hash = digest
                    row.updated_at = now
            # Keep removed searches for run history and provenance; only disable collection.
            for row in session.scalars(select(SearchRow)).all():
                if row.slug not in active_slugs:
                    row.enabled = False
                    row.updated_at = now

    def known_jobs(self, search_slug: str) -> tuple[KnownJob, ...]:
        """Return active jobs associated with a search."""
        with self.factory() as session:
            rows = session.execute(
                select(JobRow, JobSearchRow)
                .join(JobSearchRow, JobSearchRow.linkedin_job_id == JobRow.linkedin_job_id)
                .where(
                    JobSearchRow.search_slug == search_slug,
                    JobSearchRow.active.is_(True),
                )
                .order_by(JobRow.linkedin_job_id)
            ).all()
            return tuple(
                KnownJob(
                    source_job_id=job.linkedin_job_id,
                    company=job.company,
                    title=job.title,
                    locations=(job.location,),
                    application_url=job.link,
                )
                for job, _alias in rows
            )

    def persist_success(
        self,
        *,
        run_id: str,
        search: LinkedInSearchConfig,
        jobs: list[DiscoveredJob],
        confirmed_unavailable_ids: tuple[str, ...],
        found_count: int,
        excluded_count: int,
        warning_count: int,
        started_at: datetime,
        finished_at: datetime,
        duration_ms: int,
    ) -> PersistSummary:
        """Persist one successful search transaction."""
        summary = PersistSummary()
        with self.factory.begin() as session:
            session.add(
                SearchRunRow(
                    id=run_id,
                    search_slug=search.slug,
                    status="success",
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    found_count=found_count,
                    accepted_count=len(jobs),
                    excluded_count=excluded_count,
                    warning_count=warning_count,
                )
            )
            session.flush()
            for job in jobs:
                summary += self._upsert_job(
                    session,
                    run_id=run_id,
                    search_slug=search.slug,
                    incoming=job,
                    observed_at=finished_at,
                )
            summary += self._confirm_unavailable(
                session,
                search_slug=search.slug,
                job_ids=confirmed_unavailable_ids,
                observed_at=finished_at,
            )
        return summary

    def persist_failure(
        self,
        *,
        run_id: str,
        search_slug: str,
        started_at: datetime,
        finished_at: datetime,
        duration_ms: int,
        error_code: str,
        error_message: str,
    ) -> None:
        """Persist diagnostics for one failed search."""
        with self.factory.begin() as session:
            session.add(
                SearchRunRow(
                    id=run_id,
                    search_slug=search_slug,
                    status="failed",
                    started_at=started_at,
                    finished_at=finished_at,
                    duration_ms=duration_ms,
                    found_count=0,
                    accepted_count=0,
                    excluded_count=0,
                    warning_count=0,
                    error_code=error_code[:100],
                    error_message=error_message[:500],
                )
            )

    def list_open_jobs(self) -> list[StoredJob]:
        """Return all open jobs in publication order."""
        with self.factory() as session:
            rows = session.scalars(
                select(JobRow)
                .where(JobRow.status == JobStatus.OPEN.value)
                .order_by(func.lower(JobRow.company), func.lower(JobRow.title), JobRow.location)
            ).all()
            return [_stored_job(row) for row in rows]

    def list_all_jobs(self) -> list[StoredJob]:
        """Return all jobs in stable identifier order."""
        with self.factory() as session:
            rows = session.scalars(select(JobRow).order_by(JobRow.linkedin_job_id)).all()
            return [_stored_job(row) for row in rows]

    def stats(self) -> DatabaseStats:
        """Display aggregate pipeline and database statistics."""
        with self.factory() as session:
            total = session.scalar(select(func.count()).select_from(JobRow)) or 0
            opened = (
                session.scalar(
                    select(func.count())
                    .select_from(JobRow)
                    .where(JobRow.status == JobStatus.OPEN.value)
                )
                or 0
            )
            successful = (
                session.scalar(
                    select(func.count())
                    .select_from(SearchRunRow)
                    .where(SearchRunRow.status == "success")
                )
                or 0
            )
            failed = (
                session.scalar(
                    select(func.count())
                    .select_from(SearchRunRow)
                    .where(SearchRunRow.status == "failed")
                )
                or 0
            )
            last_success = session.scalar(
                select(func.max(SearchRunRow.finished_at)).where(SearchRunRow.status == "success")
            )
            configured = (
                session.scalar(
                    select(func.count()).select_from(SearchRow).where(SearchRow.enabled.is_(True))
                )
                or 0
            )
            return DatabaseStats(
                total=total,
                open=opened,
                closed=total - opened,
                configured_searches=configured,
                successful_runs=successful,
                failed_runs=failed,
                last_success_at=ensure_utc(last_success) if last_success else None,
            )

    def search_health(self) -> dict[str, SearchHealth]:
        """Return latest run health keyed by search slug."""
        with self.factory() as session:
            # Correlate one latest-run lookup per enabled search inside SQL instead of
            # issuing one database round trip for every registry entry.
            latest_run_id = (
                select(SearchRunRow.id)
                .where(SearchRunRow.search_slug == SearchRow.slug)
                .order_by(SearchRunRow.finished_at.desc(), SearchRunRow.id.desc())
                .limit(1)
                .correlate(SearchRow)
                .scalar_subquery()
            )
            rows = session.execute(
                select(SearchRow.slug, SearchRunRow)
                .join(SearchRunRow, SearchRunRow.id == latest_run_id)
                .where(SearchRow.enabled.is_(True))
                .order_by(SearchRow.slug)
            ).all()
            return {
                slug: SearchHealth(
                    status=run.status,
                    finished_at=ensure_utc(run.finished_at),
                    found_count=run.found_count,
                    accepted_count=run.accepted_count,
                    excluded_count=run.excluded_count,
                    error_code=run.error_code,
                )
                for slug, run in rows
            }

    def _upsert_job(
        self,
        session: Session,
        *,
        run_id: str,
        search_slug: str,
        incoming: DiscoveredJob,
        observed_at: datetime,
    ) -> PersistSummary:
        """Insert or update a discovered job."""
        row = session.get(JobRow, incoming.linkedin_job_id)
        summary = PersistSummary()
        if row is None:
            row = JobRow(
                linkedin_job_id=incoming.linkedin_job_id,
                company=incoming.company,
                title=incoming.title,
                location=incoming.location,
                link=incoming.link,
                category=incoming.category.value,
                industries=incoming.industries,
                employment_type=incoming.employment_type.value,
                start_date=incoming.start_date,
                first_seen_at=observed_at,
                last_seen_at=observed_at,
                updated_at=observed_at,
                status=JobStatus.OPEN.value,
            )
            session.add(row)
            summary = PersistSummary(new=1)
        else:
            # A delayed run must never move lifecycle timestamps backwards.
            effective_time = max(ensure_utc(row.last_seen_at), ensure_utc(observed_at))
            # Missing optional metadata is not evidence that a previously observed
            # value became invalid; public detail markup can omit fields temporarily.
            next_industries = incoming.industries or row.industries
            next_employment_type = incoming.employment_type.value
            next_start_date = incoming.start_date or row.start_date
            changed = any(
                (
                    row.company != incoming.company,
                    row.title != incoming.title,
                    row.location != incoming.location,
                    row.link != incoming.link,
                    row.category != incoming.category.value,
                    row.industries != next_industries,
                    row.employment_type != next_employment_type,
                    row.start_date != next_start_date,
                )
            )
            reopened = row.status == JobStatus.CLOSED.value
            row.company = incoming.company
            row.title = incoming.title
            row.location = incoming.location
            row.link = incoming.link
            row.category = incoming.category.value
            row.industries = next_industries
            row.employment_type = next_employment_type
            row.start_date = next_start_date
            row.last_seen_at = effective_time
            row.status = JobStatus.OPEN.value
            if changed or reopened:
                row.updated_at = effective_time
            summary = PersistSummary(updated=int(changed), reopened=int(reopened))
        session.flush()

        # Provenance is tracked per search because one listing may be discovered by
        # several independent searches with different availability observations.
        alias = session.get(JobSearchRow, (search_slug, incoming.linkedin_job_id))
        if alias is None:
            session.add(
                JobSearchRow(
                    search_slug=search_slug,
                    linkedin_job_id=incoming.linkedin_job_id,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                    last_seen_run_id=run_id,
                    unavailable_confirmations=0,
                    active=True,
                )
            )
        else:
            alias.last_seen_at = max(ensure_utc(alias.last_seen_at), ensure_utc(observed_at))
            alias.last_seen_run_id = run_id
            # A fresh observation cancels consecutive unavailability evidence and can
            # reactivate provenance that previously reached the closure threshold.
            alias.unavailable_confirmations = 0
            alias.active = True
        return summary

    def _confirm_unavailable(
        self,
        session: Session,
        *,
        search_slug: str,
        job_ids: tuple[str, ...],
        observed_at: datetime,
    ) -> PersistSummary:
        """Advance explicit unavailability state for a known job."""
        if not job_ids:
            return PersistSummary()
        aliases = session.scalars(
            select(JobSearchRow).where(
                JobSearchRow.search_slug == search_slug,
                JobSearchRow.linkedin_job_id.in_(job_ids),
                JobSearchRow.active.is_(True),
            )
        ).all()
        affected: set[str] = set()
        for alias in aliases:
            alias.unavailable_confirmations += 1
            if alias.unavailable_confirmations >= self.settings.closure_confirmation_runs:
                alias.active = False
            affected.add(alias.linkedin_job_id)
        session.flush()

        # A job remains open while any search still provides active provenance.
        # Resolve all affected aliases in one query to avoid an N+1 closure check.
        active_job_ids = set(
            session.scalars(
                select(JobSearchRow.linkedin_job_id).where(
                    JobSearchRow.linkedin_job_id.in_(affected),
                    JobSearchRow.active.is_(True),
                )
            )
        )
        closable_ids = affected - active_job_ids
        if not closable_ids:
            return PersistSummary()

        jobs_to_close = session.scalars(
            select(JobRow).where(
                JobRow.linkedin_job_id.in_(closable_ids),
                JobRow.status != JobStatus.CLOSED.value,
            )
        ).all()
        for job in jobs_to_close:
            job.status = JobStatus.CLOSED.value
            job.updated_at = max(ensure_utc(job.updated_at), ensure_utc(observed_at))
        return PersistSummary(closed=len(jobs_to_close))


def _stored_job(row: JobRow) -> StoredJob:
    """Convert a database row into the stored-job model."""
    return StoredJob(
        linkedin_job_id=row.linkedin_job_id,
        company=row.company,
        title=row.title,
        location=row.location,
        link=row.link,
        category=row.category,
        industries=row.industries,
        employment_type=row.employment_type,
        start_date=row.start_date,
        first_seen_at=ensure_utc(row.first_seen_at),
        last_seen_at=ensure_utc(row.last_seen_at),
        updated_at=ensure_utc(row.updated_at),
        status=row.status,
    )


def _config_hash(search: LinkedInSearchConfig) -> str:
    """Return a stable hash of a search configuration."""
    payload = json.dumps(search.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()
