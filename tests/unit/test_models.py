from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import DiscoveredJob, StoredJob
from opportunities.models.raw import RawJob


def discovered_payload() -> dict[str, object]:
    return {
        "linkedin_job_id": "1111111111",
        "company": "Example Technology",
        "title": "Software Engineering Intern 2027",
        "location": "London, UK",
        "link": "https://www.linkedin.com/jobs/view/1111111111",
        "category": OpportunityCategory.SOFTWARE_ENGINEERING,
        "employment_type": EmploymentType.INTERNSHIP,
    }


@pytest.mark.parametrize("field", ["company", "title", "location"])
@pytest.mark.parametrize("invalid", [None, 123, "   ", "&nbsp;"])
def test_discovered_job_rejects_invalid_required_text(field: str, invalid: object) -> None:
    payload = discovered_payload()
    payload[field] = invalid

    with pytest.raises(ValidationError):
        DiscoveredJob.model_validate(payload)


def test_discovered_job_normalizes_required_text_without_losing_unicode() -> None:
    job = DiscoveredJob.model_validate(
        {
            **discovered_payload(),
            "company": "  Example\t &amp; Technology  ",
            "title": "  Software\nIntern 2027 ",
            "location": "  Zürich,&nbsp; Switzerland  ",
        }
    )

    assert (job.company, job.title, job.location) == (
        "Example & Technology",
        "Software Intern 2027",
        "Zürich, Switzerland",
    )


def test_raw_job_rejects_non_string_locations() -> None:
    with pytest.raises(ValidationError, match="locations must contain strings"):
        RawJob.model_validate(
            {
                "source_job_id": "1111111111",
                "company": "Example Technology",
                "title": "Software Engineering Intern 2027",
                "locations": ["London, UK", None],
                "application_url": "https://www.linkedin.com/jobs/view/1111111111",
            }
        )


def test_job_models_canonicalize_listing_urls_consistently() -> None:
    url = " https://WWW.LINKEDIN.COM/jobs/view/1111111111/?trk=synthetic#details "
    discovered = DiscoveredJob.model_validate({**discovered_payload(), "link": url})
    raw = RawJob(
        source_job_id="1111111111",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        locations=["London, UK"],
        application_url=url,
    )

    assert raw.application_url == discovered.link == "https://www.linkedin.com/jobs/view/1111111111"


@pytest.mark.parametrize(
    ("source", "utc"),
    [
        ("2026-07-01T12:30:00", "2026-07-01T12:30:00+00:00"),
        ("2026-07-01T12:30:00Z", "2026-07-01T12:30:00+00:00"),
        ("2026-07-01T00:30:00.123456+05:30", "2026-06-30T19:00:00.123456+00:00"),
        ("2026-06-30T23:30:00.654321-02:00", "2026-07-01T01:30:00.654321+00:00"),
    ],
    ids=["naive-sqlite", "utc", "positive-offset", "negative-offset"],
)
def test_job_models_normalize_timestamps_to_utc(source: str, utc: str) -> None:
    timestamp = datetime.fromisoformat(source)
    discovered = DiscoveredJob.model_validate({**discovered_payload(), "posted_at": timestamp})
    raw = RawJob(
        source_job_id="1111111111",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        locations=["London, UK"],
        application_url="https://www.linkedin.com/jobs/view/1111111111",
        posted_at=timestamp,
    )
    stored = StoredJob.model_validate(
        {
            **discovered_payload(),
            "posted_at": timestamp,
            "first_seen_at": timestamp,
            "last_seen_at": timestamp,
            "updated_at": timestamp,
            "status": JobStatus.OPEN,
        }
    )

    expected = datetime.fromisoformat(utc)
    for actual in (
        discovered.posted_at,
        raw.posted_at,
        stored.posted_at,
        stored.first_seen_at,
        stored.last_seen_at,
        stored.updated_at,
    ):
        assert actual == expected
        # Datetime equality alone accepts an unnormalized equivalent offset.
        assert actual is not None
        assert actual.tzinfo is UTC
