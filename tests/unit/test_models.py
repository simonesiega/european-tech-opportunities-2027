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


def test_discovered_job_rejects_non_string_text_fields() -> None:
    payload = discovered_payload()
    payload["company"] = None

    with pytest.raises(ValidationError, match="job text fields must be strings"):
        DiscoveredJob.model_validate(payload)


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


def test_job_models_normalize_naive_timestamps_to_utc() -> None:
    timestamp = datetime.fromisoformat("2026-07-01T12:30:00")
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
            "first_seen_at": timestamp,
            "last_seen_at": timestamp,
            "updated_at": timestamp,
            "status": JobStatus.OPEN,
        }
    )

    expected = timestamp.replace(tzinfo=UTC)
    assert discovered.posted_at == expected
    assert raw.posted_at == expected
    assert stored.first_seen_at == expected
    assert stored.last_seen_at == expected
    assert stored.updated_at == expected
