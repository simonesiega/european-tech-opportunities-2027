"""Strict aggregate-only storage contract for collection-quality baselines."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from opportunities.models.enums import OpportunityCategory

MAX_BASELINE_SNAPSHOTS = 5
MAX_SNAPSHOT_BYTES = 131_072
ParserField = Literal["description", "industries", "locations", "posted_at", "start_date"]
JobField = Literal["industries", "start_date"]
PARSER_FIELDS: tuple[ParserField, ...] = (
    "description",
    "industries",
    "locations",
    "posted_at",
    "start_date",
)
JOB_FIELDS: tuple[JobField, ...] = ("industries", "start_date")
Count = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
SearchSlug = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)]
Fingerprint = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]


class SearchQualityCounts(BaseModel):
    """Keep discovery counts separate from classified details, which include rechecks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    found_count: Count
    accepted_count: Count
    classified_count: Count

    @model_validator(mode="after")
    def validate_counts(self) -> SearchQualityCounts:
        """Reject impossible acceptance rates without bounding rechecks by discovery."""
        if self.accepted_count > self.classified_count:
            raise ValueError("accepted count exceeds classified count")
        return self


class DataQualitySnapshot(BaseModel):
    """Allow only validated aggregate observations, never listing or diagnostic text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Annotated[int, Field(strict=True, ge=1, le=1)]
    captured_at: AwareDatetime
    search_fingerprints: dict[SearchSlug, Fingerprint]
    searches: dict[SearchSlug, SearchQualityCounts]
    open_job_count: Count
    category_counts: dict[OpportunityCategory, Count]
    country_counts: dict[CountryCode, Count]
    field_missing_counts: dict[JobField, Count]
    parser_candidate_count: Count
    parser_missing_counts: dict[ParserField, Count]

    @model_validator(mode="after")
    def validate_counts(self) -> DataQualitySnapshot:
        """Ensure every aggregate has a coherent population and complete run scope."""
        if not self.searches or self.searches.keys() != self.search_fingerprints.keys():
            raise ValueError("snapshot must cover every enabled search")
        if sum(self.category_counts.values()) != self.open_job_count:
            raise ValueError("category counts do not match open job count")
        if (
            sum(row.classified_count for row in self.searches.values())
            != self.parser_candidate_count
        ):
            raise ValueError("parser count does not match classified count")
        if self.field_missing_counts.keys() != set(JOB_FIELDS) or any(
            count > self.open_job_count for count in self.field_missing_counts.values()
        ):
            raise ValueError("invalid optional-field counts")
        if self.parser_missing_counts.keys() != set(PARSER_FIELDS) or any(
            count > self.parser_candidate_count for count in self.parser_missing_counts.values()
        ):
            raise ValueError("invalid parser-field counts")
        # A multi-country listing contributes once to each recognized country.
        if any(count > self.open_job_count for count in self.country_counts.values()):
            raise ValueError("country count exceeds open job count")
        return self

    @classmethod
    def from_json(cls, payload: str) -> DataQualitySnapshot:
        """Bound validation work for persisted, potentially damaged observations."""
        if len(payload.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
            raise ValueError("data-quality snapshot exceeds 128 KiB")
        return cls.model_validate_json(payload)
