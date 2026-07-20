"""Minimal in-memory LinkedIn job records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opportunities.utils.text import clean_text
from opportunities.utils.url import canonicalize_url, validate_linkedin_job_url

MAX_DESCRIPTION_CHARS = 200_000


@dataclass(frozen=True, slots=True)
class KnownJob:
    """Describe an active job eligible for availability rechecks."""

    source_job_id: str
    company: str
    title: str
    locations: tuple[str, ...]
    application_url: str


class RawJob(BaseModel):
    """Parsed public job content retained only for the current collection run."""

    model_config = ConfigDict(extra="forbid")

    source_job_id: str = Field(pattern=r"^[0-9]+$", max_length=30)
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    locations: list[str] = Field(default_factory=list, max_length=20)
    application_url: str = Field(max_length=2_048)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_CHARS)
    industries: str | None = Field(default=None, max_length=500)
    start_date: str | None = Field(default=None, max_length=100)
    posted_at: datetime | None = None

    @field_validator("source_job_id", "company", "title", mode="before")
    @classmethod
    def normalize_scalar_text(cls, value: object) -> object:
        """Normalize optional scalar text from scraped payloads."""
        if isinstance(value, str):
            cleaned = clean_text(value)
            return cleaned or None
        return value

    @field_validator("locations", mode="before")
    @classmethod
    def normalize_location_list(cls, value: object) -> object:
        """Normalize and deduplicate scraped job locations."""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            raise ValueError("locations must be a list")
        if len(value) > 20:
            raise ValueError("locations cannot contain more than 20 values")
        cleaned = [clean_text(str(item)) for item in value]
        if any(len(item) > 500 for item in cleaned):
            raise ValueError("location values cannot exceed 500 characters")
        return list(dict.fromkeys(item for item in cleaned if item))

    @field_validator("industries", "start_date", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        """Normalize optional display metadata."""
        if isinstance(value, str):
            return clean_text(value) or None
        return value

    @field_validator("application_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Validate and canonicalize scraped URLs."""
        return canonicalize_url(value)

    @model_validator(mode="after")
    def validate_link_identity(self) -> RawJob:
        """Ensure source identity and the public LinkedIn URL agree."""
        validate_linkedin_job_url(self.application_url, self.source_job_id)
        return self
