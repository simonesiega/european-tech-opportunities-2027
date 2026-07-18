"""Validated job records crossing the scraper/database boundary."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from opportunities.models.enums import EmploymentType, InternshipCategory, JobStatus
from opportunities.utils.text import clean_text
from opportunities.utils.url import canonicalize_url


class DiscoveredJob(BaseModel):
    """A strict 2027 European technology opportunity ready for persistence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    linkedin_job_id: str = Field(pattern=r"^[0-9]+$", max_length=30)
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=500)
    link: str
    category: InternshipCategory
    industries: str | None = Field(default=None, max_length=500)
    employment_type: EmploymentType
    start_date: str | None = Field(default=None, max_length=100)
    posted_at: datetime | None = None

    @field_validator("company", "title", "location", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> str:
        """Normalize required job text fields."""
        cleaned = clean_text(str(value))
        if not cleaned:
            raise ValueError("job text fields cannot be empty")
        return cleaned

    @field_validator("industries", "start_date", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        """Normalize optional display metadata."""
        if isinstance(value, str):
            return clean_text(value) or None
        return value

    @field_validator("link")
    @classmethod
    def normalize_link(cls, value: str) -> str:
        """Canonicalize the job application URL."""
        return canonicalize_url(value)


class StoredJob(DiscoveredJob):
    """Database-backed job used by README rendering and statistics."""

    first_seen_at: datetime
    last_seen_at: datetime
    updated_at: datetime
    status: JobStatus
