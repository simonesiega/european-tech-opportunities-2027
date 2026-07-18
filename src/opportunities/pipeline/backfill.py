"""One-time first-seen backfill from LinkedIn relative posting metadata."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from opportunities.models.job import StoredJob
from opportunities.scrapers.http import FetchError
from opportunities.scrapers.linkedin import (
    LINKEDIN_DETAIL_ENDPOINT,
    LinkedInPayloadError,
    LinkedInSearchCard,
    TextFetcher,
    parse_job_detail,
)
from opportunities.utils.time import ensure_utc


@dataclass(frozen=True, slots=True)
class FirstSeenUpdate:
    """Describe one safe proposed correction to an existing job."""

    linkedin_job_id: str
    first_seen_at: datetime


@dataclass(frozen=True, slots=True)
class PostingBackfillResult:
    """Summarize bounded posting-date inspection."""

    scanned: int
    parsed: int
    unchanged: int
    missing: int
    unavailable: int
    failed: int
    updates: tuple[FirstSeenUpdate, ...]


async def inspect_posting_dates(
    jobs: list[StoredJob],
    fetcher: TextFetcher,
    *,
    observed_at: datetime,
    max_concurrency: int,
) -> PostingBackfillResult:
    """Inspect open jobs and propose only safe, backward first-seen corrections."""
    semaphore = asyncio.Semaphore(max_concurrency)

    async def inspect(job: StoredJob) -> tuple[str, FirstSeenUpdate | None]:
        async with semaphore:
            try:
                html = await fetcher.get_text(
                    LINKEDIN_DETAIL_ENDPOINT.format(job_id=job.linkedin_job_id)
                )
                card = LinkedInSearchCard(
                    job_id=job.linkedin_job_id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    application_url=job.link,
                )
                parsed = parse_job_detail(html, card, observed_at=observed_at)
            except FetchError as exc:
                if exc.status_code in {404, 410}:
                    return "unavailable", None
                return "failed", None
            except (LinkedInPayloadError, ValueError):
                return "failed", None

            if parsed.posted_at is None:
                return "missing", None
            posted_at = ensure_utc(parsed.posted_at)
            # Never move first_seen_at forward and never infer publication after an
            # already-recorded observation. Both cases indicate ambiguous metadata,
            # commonly a repost, and must remain unchanged.
            if posted_at >= ensure_utc(job.first_seen_at) or posted_at > ensure_utc(
                job.last_seen_at
            ):
                return "unchanged", None
            return "update", FirstSeenUpdate(job.linkedin_job_id, posted_at)

    outcomes = await asyncio.gather(*(inspect(job) for job in jobs))
    updates = tuple(update for status, update in outcomes if status == "update" and update)
    return PostingBackfillResult(
        scanned=len(jobs),
        parsed=sum(status in {"update", "unchanged"} for status, _update in outcomes),
        unchanged=sum(status == "unchanged" for status, _update in outcomes),
        missing=sum(status == "missing" for status, _update in outcomes),
        unavailable=sum(status == "unavailable" for status, _update in outcomes),
        failed=sum(status == "failed" for status, _update in outcomes),
        updates=updates,
    )
