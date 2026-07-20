"""Validated configuration for public LinkedIn job searches."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opportunities.utils.text import clean_text, normalized_key

DatePosted = Literal["any", "day", "week", "month", "cycle"]
WorkplaceFilter = Literal["any", "on-site", "remote", "hybrid"]


class LinkedInSearchConfig(BaseModel):
    """One bounded query against LinkedIn's unauthenticated public jobs pages."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    keywords: str = Field(min_length=2, max_length=300)
    location: str = Field(min_length=1, max_length=200)
    geo_id: str | None = Field(default=None, pattern=r"^[0-9]+$", max_length=30)
    company_names: tuple[str, ...] = ()
    workplace: WorkplaceFilter = "any"
    date_posted: DatePosted = "any"
    max_pages: int = Field(default=1, ge=1, le=10)
    max_results: int = Field(default=25, ge=1, le=250)
    max_rechecks: int = Field(default=25, ge=0, le=250)
    enabled: bool = True
    verified_at: date | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("name", "keywords", "location", "notes", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        """Trim required search text fields."""
        if isinstance(value, str):
            return clean_text(value)
        return value

    @field_validator("company_names", mode="before")
    @classmethod
    def normalize_companies(cls, value: object) -> object:
        """Normalize and deduplicate company allowlists."""
        if value is None:
            return ()
        if not isinstance(value, (list, tuple)):
            raise ValueError("company_names must be a list")
        if len(value) > 50:
            raise ValueError("company_names cannot contain more than 50 values")
        if any(not isinstance(item, str) for item in value):
            raise ValueError("company_names must contain strings")
        companies = tuple(clean_text(item) for item in value)
        if any(not company or len(company) > 200 for company in companies):
            raise ValueError("company_names must contain non-empty values up to 200 characters")
        unique: dict[str, str] = {}
        for company in companies:
            unique.setdefault(normalized_key(company), company)
        return tuple(unique.values())

    @model_validator(mode="after")
    def validate_scope(self) -> LinkedInSearchConfig:
        """Reject placeholder or unbounded search definitions."""
        if normalized_key(self.name) in {"example", "example search"}:
            raise ValueError("placeholder searches are not allowed")
        if self.max_results > self.max_pages * 25:
            raise ValueError("max_results cannot exceed max_pages * 25")
        return self
