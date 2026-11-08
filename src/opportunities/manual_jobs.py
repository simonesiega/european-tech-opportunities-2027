"""Pure manual-addition validation shared by the CLI and local research tools."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.normalization.location import normalize_locations
from opportunities.pipeline.classification import Classifier
from opportunities.utils.time import ensure_utc
from opportunities.utils.url import extract_linkedin_job_id

MAX_MANUAL_BATCH_BYTES = 65_536
MAX_MANUAL_BATCH_JOBS = 10
_REQUIRED_FIELDS = frozenset({"url", "company", "title", "location", "category", "employment_type"})
_OPTIONAL_FIELDS = frozenset({"industries", "start_date", "posted_at"})


def parse_posted_at(value: str) -> datetime:
    """Require explicit timezone evidence and normalize an ISO timestamp to UTC."""
    candidate = value.strip()
    if "T" not in candidate and " " not in candidate:
        raise ValueError("posted_at must be a valid ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("posted_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("posted_at must include an explicit timezone")
    return ensure_utc(parsed)


def prepare_manual_job(
    *,
    classifier: Classifier,
    observed_at: datetime,
    url: str,
    company: str,
    title: str,
    location: str,
    category: OpportunityCategory,
    employment_type: EmploymentType,
    industries: str | None,
    start_date: str | None,
    posted_at: str | None,
) -> DiscoveredJob:
    """Apply the same strict model and classifier checks to both manual commands."""
    job = DiscoveredJob(
        linkedin_job_id=extract_linkedin_job_id(url),
        company=company,
        title=title,
        location=location,
        link=url,
        category=category,
        industries=industries,
        employment_type=employment_type,
        start_date=start_date,
        posted_at=parse_posted_at(posted_at) if posted_at is not None else None,
    )
    if job.posted_at is not None and job.posted_at > observed_at:
        raise ValueError("posting timestamp cannot be in the future")
    decision = classifier.classify(
        title=job.title,
        description=None,
        location=normalize_locations([job.location]),
        posted_at=job.posted_at,
    )
    if not decision.include:
        raise ValueError(f"listing is outside publication policy: {decision.exclusion_reason}")
    if decision.category != job.category or decision.employment_type != job.employment_type:
        raise ValueError("category/type conflicts with classifier")
    return job


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys before any listing can be written."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def load_manual_batch(
    input_file: Path, *, classifier: Classifier, observed_at: datetime
) -> list[DiscoveredJob]:
    """Read a bounded JSON array and validate every record without persistence."""
    with input_file.open("rb") as source:
        content = source.read(MAX_MANUAL_BATCH_BYTES + 1)
    return parse_manual_batch(content, classifier=classifier, observed_at=observed_at)


def parse_manual_batch(
    content: bytes, *, classifier: Classifier, observed_at: datetime
) -> list[DiscoveredJob]:
    """Validate exact workflow bytes without opening a database or loading settings."""
    if len(content) > MAX_MANUAL_BATCH_BYTES:
        raise ValueError("input file exceeds 64 KiB")
    try:
        parsed: object = json.loads(content.decode("utf-8"), object_pairs_hook=unique_json_object)
    except (ValueError, RecursionError) as exc:
        raise ValueError(
            "input file must contain valid UTF-8 JSON without duplicate fields"
        ) from exc
    if not isinstance(parsed, list) or not 1 <= len(parsed) <= MAX_MANUAL_BATCH_JOBS:
        raise ValueError("input must be a JSON array of 1 to 10 jobs")
    jobs: list[DiscoveredJob] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(parsed, start=1):
        try:
            job = _manual_job_from_record(
                cast(object, item), classifier=classifier, observed_at=observed_at
            )
        except ValidationError as exc:
            raise ValueError(f"job {index}: invalid listing fields") from exc
        except ValueError as exc:
            raise ValueError(f"job {index}: {exc}") from exc
        if job.linkedin_job_id in seen_ids:
            raise ValueError(f"job {index}: duplicate LinkedIn job identity")
        seen_ids.add(job.linkedin_job_id)
        jobs.append(job)
    return jobs


def _manual_job_from_record(
    item: object, *, classifier: Classifier, observed_at: datetime
) -> DiscoveredJob:
    """Convert one flat JSON object to the existing manual-job validation path."""
    if not isinstance(item, dict):
        raise ValueError("each job must be an object")
    record = cast(dict[str, object], item)
    if not _REQUIRED_FIELDS.issubset(record):
        raise ValueError("missing required listing fields")
    if record.keys() - (_REQUIRED_FIELDS | _OPTIONAL_FIELDS):
        raise ValueError("unknown listing fields")
    if not all(isinstance(record[key], str) for key in _REQUIRED_FIELDS) or any(
        record.get(key) is not None and not isinstance(record[key], str) for key in _OPTIONAL_FIELDS
    ):
        raise ValueError("listing fields have invalid types")
    try:
        category = OpportunityCategory(cast(str, record["category"]))
        employment_type = EmploymentType(cast(str, record["employment_type"]))
    except ValueError as exc:
        raise ValueError("unsupported category or employment type") from exc
    return prepare_manual_job(
        classifier=classifier,
        observed_at=observed_at,
        url=cast(str, record["url"]),
        company=cast(str, record["company"]),
        title=cast(str, record["title"]),
        location=cast(str, record["location"]),
        category=category,
        employment_type=employment_type,
        industries=cast(str | None, record.get("industries")),
        start_date=cast(str | None, record.get("start_date")),
        posted_at=cast(str | None, record.get("posted_at")),
    )
