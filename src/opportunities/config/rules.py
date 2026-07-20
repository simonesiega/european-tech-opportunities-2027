"""Validated deterministic classification rules."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from opportunities.models.enums import OpportunityCategory
from opportunities.utils.text import normalized_key


class ClassificationRules(BaseModel):
    """Human-reviewable keyword rules loaded from YAML."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[2]
    internship_keywords: tuple[str, ...] = Field(min_length=1)
    new_grad_keywords: tuple[str, ...] = Field(min_length=1)
    excluded_role_keywords: tuple[str, ...] = Field(min_length=1)
    categories: dict[OpportunityCategory, tuple[str, ...]] = Field(min_length=1)

    @field_validator(
        "internship_keywords", "new_grad_keywords", "excluded_role_keywords", mode="before"
    )
    @classmethod
    def normalize_keywords(cls, value: object) -> object:
        """Normalize and deduplicate configured keyword lists."""
        return _normalize_keyword_list(value)

    @field_validator("categories", mode="before")
    @classmethod
    def normalize_categories(cls, value: object) -> object:
        """Normalize category keyword mappings without dropping malformed entries."""
        if not isinstance(value, dict):
            raise ValueError("categories must be a mapping")
        return {
            str(category): _normalize_keyword_list(keywords) for category, keywords in value.items()
        }

    @model_validator(mode="after")
    def validate_categories(self) -> ClassificationRules:
        """Reject ambiguous or non-publishable category rules."""
        if OpportunityCategory.UNKNOWN in self.categories:
            raise ValueError("unknown cannot be configured as a publication category")
        owners: dict[str, OpportunityCategory] = {}
        for category, keywords in self.categories.items():
            for keyword in keywords:
                previous = owners.setdefault(keyword, category)
                if previous != category:
                    raise ValueError(
                        f"category keyword {keyword!r} is assigned to both "
                        f"{previous.value!r} and {category.value!r}"
                    )
        return self


def load_classification_rules(path: Path) -> ClassificationRules:
    """Load and validate classification rules from YAML."""
    if not path.is_file():
        raise ValueError(f"classification rules do not exist: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"could not read classification rules: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("classification rules must contain a YAML mapping")
    return ClassificationRules.model_validate(payload)


def _normalize_keyword_list(value: object) -> tuple[str, ...]:
    """Validate, normalize, and deduplicate one external keyword list."""
    if not isinstance(value, (list, tuple)):
        raise ValueError("keyword configuration must be a list")
    if len(value) > 500:
        raise ValueError("keyword configuration cannot contain more than 500 entries")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > 200:
            raise ValueError("keyword entries must be strings from 1 to 200 characters")
        keyword = normalized_key(item)
        if not keyword:
            raise ValueError("keyword entries must contain searchable text")
        normalized.append(keyword)
    return tuple(dict.fromkeys(normalized))
