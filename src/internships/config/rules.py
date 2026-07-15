"""Validated deterministic classification rules."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from internships.models.enums import InternshipCategory


class ClassificationRules(BaseModel):
    """Human-reviewable keyword rules loaded from YAML."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    internship_keywords: tuple[str, ...]
    excluded_role_keywords: tuple[str, ...]
    categories: dict[InternshipCategory, tuple[str, ...]]

    @field_validator("internship_keywords", "excluded_role_keywords", mode="before")
    @classmethod
    def normalize_keywords(cls, value: object) -> object:
        """Normalize and deduplicate configured keyword lists."""
        if not isinstance(value, (list, tuple)):
            raise ValueError("keyword configuration must be a list")
        return tuple(
            dict.fromkeys(str(item).strip().lower() for item in value if str(item).strip())
        )

    @field_validator("categories", mode="before")
    @classmethod
    def normalize_categories(cls, value: object) -> object:
        """Normalize category keyword mappings."""
        if not isinstance(value, dict):
            raise ValueError("categories must be a mapping")
        return {
            str(category): tuple(
                dict.fromkeys(str(item).strip().lower() for item in keywords if str(item).strip())
            )
            for category, keywords in value.items()
            if isinstance(keywords, (list, tuple))
        }


def load_classification_rules(path: Path) -> ClassificationRules:
    """Load and validate classification rules from YAML."""
    if not path.is_file():
        raise ValueError(f"classification rules do not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("classification rules must contain a YAML mapping")
    return ClassificationRules.model_validate(payload)
