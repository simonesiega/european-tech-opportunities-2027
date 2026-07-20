"""Full-state job detail-page availability auditing."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from opportunities.config.settings import Settings
from opportunities.database.repository import Repository
from opportunities.models.job import StoredJob
from opportunities.scrapers.http import FetchError, HttpFetcher
from opportunities.scrapers.linkedin import LINKEDIN_DETAIL_ENDPOINT, validate_job_detail_page
from opportunities.utils.time import utc_now


class AvailabilityFetcher(Protocol):
    """Define the transport needed by the availability auditor."""

    async def get_text(self, url: str) -> str:
        """Fetch one public listing page."""
        ...


@dataclass(frozen=True, slots=True)
class AvailabilityAuditResult:
    """Summarize one complete pass over canonical job rows."""

    checked: int
    available: int
    deleted: int
    reopened: int
    inconclusive_ids: tuple[str, ...]

    @property
    def exit_code(self) -> int:
        """Return partial success when any page could not be classified safely."""
        return 2 if self.inconclusive_ids else 0


async def audit_job_availability(
    *,
    settings: Settings,
    repository: Repository,
    fetcher: AvailabilityFetcher | None = None,
    observed_at: datetime | None = None,
) -> AvailabilityAuditResult:
    """Check every job detail page and delete rows with explicit 404/410 responses.

    A successful HTML response proves availability. HTTP 404 and 410 prove that a
    listing is unavailable. Authentication failures, rate limits, server errors,
    malformed responses, and transport failures are inconclusive and never delete data.
    """
    jobs = repository.list_all_jobs()
    checked_at = observed_at or utc_now()

    if fetcher is None:
        async with HttpFetcher(settings) as managed:
            return await _audit_jobs(
                jobs=jobs,
                repository=repository,
                fetcher=managed,
                max_concurrency=settings.max_concurrency,
                observed_at=checked_at,
            )
    return await _audit_jobs(
        jobs=jobs,
        repository=repository,
        fetcher=fetcher,
        max_concurrency=settings.max_concurrency,
        observed_at=checked_at,
    )


async def _audit_jobs(
    *,
    jobs: list[StoredJob],
    repository: Repository,
    fetcher: AvailabilityFetcher,
    max_concurrency: int,
    observed_at: datetime,
) -> AvailabilityAuditResult:
    """Fetch all job detail pages before applying one atomic database mutation."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def check(job: StoredJob) -> tuple[str, str]:
        async with semaphore:
            try:
                html = await fetcher.get_text(
                    LINKEDIN_DETAIL_ENDPOINT.format(job_id=job.linkedin_job_id)
                )
                validate_job_detail_page(html)
            except FetchError as exc:
                if exc.status_code in {404, 410}:
                    return job.linkedin_job_id, "unavailable"
                return job.linkedin_job_id, "inconclusive"
            except Exception:
                # Keep unexpected provider/client failures from deleting valid rows.
                return job.linkedin_job_id, "inconclusive"
            return job.linkedin_job_id, "available"

    outcomes = await asyncio.gather(*(check(job) for job in jobs))
    available_ids = tuple(job_id for job_id, state in outcomes if state == "available")
    unavailable_ids = tuple(job_id for job_id, state in outcomes if state == "unavailable")
    inconclusive_ids = tuple(job_id for job_id, state in outcomes if state == "inconclusive")
    changes = repository.apply_availability_audit(
        available_ids=available_ids,
        unavailable_ids=unavailable_ids,
        observed_at=observed_at,
    )
    return AvailabilityAuditResult(
        checked=len(jobs),
        available=len(available_ids),
        deleted=changes.deleted,
        reopened=changes.reopened,
        inconclusive_ids=inconclusive_ids,
    )
