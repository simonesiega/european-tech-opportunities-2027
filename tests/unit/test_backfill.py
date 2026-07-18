from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from opportunities.models.enums import EmploymentType, InternshipCategory, JobStatus
from opportunities.models.job import StoredJob
from opportunities.pipeline.backfill import inspect_posting_dates
from opportunities.scrapers.http import FetchError
from opportunities.scrapers.linkedin import LINKEDIN_DETAIL_ENDPOINT


class FixtureFetcher:
    def __init__(self, responses: dict[str, str | FetchError]) -> None:
        self.responses = responses

    async def get_text(self, url: str) -> str:
        response = self.responses[url]
        if isinstance(response, FetchError):
            raise response
        return response


def stored_job(job_id: str) -> StoredJob:
    return StoredJob(
        linkedin_job_id=job_id,
        company="Test Technology",
        title="Software Engineering Intern 2027",
        location="Berlin, Germany",
        link=f"https://www.linkedin.com/jobs/view/{job_id}",
        category=InternshipCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
        first_seen_at=datetime(2026, 7, 10, tzinfo=UTC),
        last_seen_at=datetime(2026, 7, 15, tzinfo=UTC),
        updated_at=datetime(2026, 7, 15, tzinfo=UTC),
        status=JobStatus.OPEN,
    )


def detail(posting_age: str | None) -> str:
    metadata = (
        f'<span class="posted-time-ago__text topcard__flavor--metadata">{posting_age}</span>'
        if posting_age
        else ""
    )
    return f"""<!doctype html>
    <h1 class="top-card-layout__title">Software Engineering Intern 2027</h1>
    <a class="topcard__org-name-link">Test Technology</a>
    {metadata}"""


def test_posting_backfill_proposes_only_safe_backward_corrections() -> None:
    job_ids = [f"{index:010d}" for index in range(1, 6)]
    responses: dict[str, str | FetchError] = {
        LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_ids[0]): detail("20 days ago"),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_ids[1]): detail("5 days ago"),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_ids[2]): detail(None),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_ids[3]): FetchError(
            "http_status", "not found", status_code=404
        ),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_ids[4]): FetchError(
            "timeout", "timed out"
        ),
    }

    result = asyncio.run(
        inspect_posting_dates(
            [stored_job(job_id) for job_id in job_ids],
            FixtureFetcher(responses),
            observed_at=datetime(2026, 7, 18, tzinfo=UTC),
            max_concurrency=2,
        )
    )

    assert result.scanned == 5
    assert result.parsed == 2
    assert result.unchanged == 1
    assert result.missing == 1
    assert result.unavailable == 1
    assert result.failed == 1
    assert [(update.linkedin_job_id, update.first_seen_at) for update in result.updates] == [
        (job_ids[0], datetime(2026, 6, 28, tzinfo=UTC))
    ]
