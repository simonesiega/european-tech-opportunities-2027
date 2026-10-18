"""Bounded rotating public-page and detail-page availability auditing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from opportunities.config.settings import Settings
from opportunities.database.repository import Repository
from opportunities.models.job import StoredJob
from opportunities.scrapers.http import (
    LINKEDIN_DETAIL_ENDPOINT,
    LINKEDIN_PUBLIC_JOB_URL,
    FetchError,
    HttpFetcher,
)
from opportunities.scrapers.linkedin import (
    TextFetcher,
    has_closed_application_notice,
    validate_job_detail_page,
)
from opportunities.utils.concurrency import map_concurrently
from opportunities.utils.time import utc_now

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AvailabilityAuditResult:
    """Availability outcomes, source stops, and deferred backlog for one batch."""

    checked: int
    available: int
    deleted: int
    reopened: int
    inconclusive_ids: tuple[str, ...]
    source_blocked: bool = False
    deferred: int = 0
    blocked: int = 0
    blocked_reason: str | None = None
    rate_limited: int = 0
    listing_redirect_ids: tuple[str, ...] = ()

    @property
    def rate_limited_partial(self) -> bool:
        """Retain confirmed checks after HTTP 429, tolerating only public-listing 301s."""
        return (
            self.source_blocked
            and self.blocked > 0
            and self.rate_limited == self.blocked
            and set(self.inconclusive_ids).issubset(self.listing_redirect_ids)
            and self.checked > self.blocked + len(self.inconclusive_ids)
        )

    @property
    def exit_code(self) -> int:
        """Distinguish publishable partial work from a blocking source denial."""
        if self.source_blocked:
            return 4 if self.rate_limited_partial else 1
        return 2 if self.inconclusive_ids else 0


async def audit_job_availability(
    *,
    settings: Settings,
    repository: Repository,
    fetcher: TextFetcher | None = None,
    observed_at: datetime | None = None,
) -> AvailabilityAuditResult:
    """Check a bounded batch of due jobs and delete explicitly unavailable rows.

    HTTP 404/410 responses and LinkedIn's explicit closed-application alert prove that
    a listing is unavailable. Otherwise, the guest detail endpoint must still contain
    recognizable listing identity fields. Authentication failures, rate limits, server
    errors, malformed responses, and transport failures are inconclusive and never
    delete data.
    """
    checked_at = observed_at or utc_now()
    jobs, deferred = repository.availability_batch(checked_at)
    logger.info("availability batch: %d selected, %d due deferred", len(jobs), deferred)

    if fetcher is None:
        async with HttpFetcher(settings) as managed:
            return await _audit_jobs(
                jobs=jobs,
                repository=repository,
                fetcher=managed,
                max_concurrency=settings.max_concurrency,
                observed_at=checked_at,
                deferred=deferred,
            )
    return await _audit_jobs(
        jobs=jobs,
        repository=repository,
        fetcher=fetcher,
        max_concurrency=settings.max_concurrency,
        observed_at=checked_at,
        deferred=deferred,
    )


async def _audit_jobs(
    *,
    jobs: list[StoredJob],
    repository: Repository,
    fetcher: TextFetcher,
    max_concurrency: int,
    observed_at: datetime,
    deferred: int,
) -> AvailabilityAuditResult:
    """Fetch all public and guest-detail pages before one atomic database mutation."""

    blocked_reason: str | None = None

    async def check(job: StoredJob) -> tuple[str, str]:
        nonlocal blocked_reason
        if blocked_reason is not None:
            return job.linkedin_job_id, "deferred"
        try:
            public_html = await fetcher.get_text(
                LINKEDIN_PUBLIC_JOB_URL.format(job_id=job.linkedin_job_id)
            )
            if has_closed_application_notice(public_html):
                return job.linkedin_job_id, "unavailable"

            # A source stop also forbids starting details for an in-flight public page.
            if blocked_reason is not None:
                return job.linkedin_job_id, "deferred"
            # A public page can be a generic shell, so retain the existing identity
            # check before using the absence of a closure alert as availability proof.
            detail_html = await fetcher.get_text(
                LINKEDIN_DETAIL_ENDPOINT.format(job_id=job.linkedin_job_id)
            )
            validate_job_detail_page(detail_html)
        except FetchError as exc:
            if exc.code == "source_blocked":
                if blocked_reason is None or blocked_reason == "HTTP 429":
                    blocked_reason = (
                        f"HTTP {exc.status_code}"
                        if exc.status_code is not None
                        else "source_blocked"
                    )
                return job.linkedin_job_id, "rate_limited" if exc.status_code == 429 else "blocked"
            if exc.code == "listing_redirect":
                return job.linkedin_job_id, "listing_redirect"
            if exc.status_code in {404, 410}:
                return job.linkedin_job_id, "unavailable"
            return job.linkedin_job_id, "inconclusive"
        except Exception:
            # Keep unexpected provider/client failures from deleting valid rows.
            return job.linkedin_job_id, "inconclusive"
        return job.linkedin_job_id, "available"

    outcomes = await map_concurrently(jobs, check, limit=max_concurrency)
    available_ids = tuple(job_id for job_id, state in outcomes if state == "available")
    unavailable_ids = tuple(job_id for job_id, state in outcomes if state == "unavailable")
    listing_redirect_ids = tuple(
        job_id for job_id, state in outcomes if state == "listing_redirect"
    )
    inconclusive_ids = tuple(
        job_id for job_id, state in outcomes if state in {"inconclusive", "listing_redirect"}
    )
    changes = repository.apply_availability_audit(
        available_ids=available_ids,
        unavailable_ids=unavailable_ids,
        observed_at=observed_at,
        inconclusive_ids=inconclusive_ids,
    )
    return AvailabilityAuditResult(
        checked=sum(state != "deferred" for _, state in outcomes),
        available=len(available_ids),
        deleted=changes.deleted,
        reopened=changes.reopened,
        inconclusive_ids=inconclusive_ids,
        source_blocked=blocked_reason is not None,
        deferred=deferred + sum(state == "deferred" for _, state in outcomes),
        blocked=sum(state in {"blocked", "rate_limited"} for _, state in outcomes),
        blocked_reason=blocked_reason,
        rate_limited=sum(state == "rate_limited" for _, state in outcomes),
        listing_redirect_ids=listing_redirect_ids,
    )
