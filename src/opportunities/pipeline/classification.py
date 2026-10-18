"""Strict deterministic checks for 2027 European tech internships and new-grad roles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from opportunities.config.policy import MINIMUM_POSTED_AT
from opportunities.config.rules import ClassificationRules
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.normalization.location import EUROPEAN_COUNTRY_CODES, LocationResult
from opportunities.utils.text import contains_normalized_phrase, normalized_key
from opportunities.utils.time import ensure_utc

# Recognize past and future conflicts before falling back to posting dates.
_YEAR_RE = re.compile(r"\b(?:19|20|21)\d{2}\b")
_OPPORTUNITY_CONTEXT_RE = re.compile(
    r"\b(?:internship|intern|summer|placement|programme|program|cycle|graduate|"
    r"new\s+grad|early\s+career|entry\s+level)\b"
)
_GENERIC_TECH_TITLE_WORDS = frozenset(
    {
        "ai",
        "career",
        "co",
        "computer",
        "coop",
        "data",
        "developer",
        "early",
        "engineering",
        "entry",
        "grad",
        "graduate",
        "intern",
        "internship",
        "level",
        "ml",
        "new",
        "placement",
        "research",
        "science",
        "scientist",
        "software",
        "student",
        "summer",
        "technical",
        "technology",
        "university",
    }
)
_OTHER_TECH_KEYWORDS = (
    "computer science",
    "developer",
    "information technology",
    "technical engineering",
    "technology intern",
)


@dataclass(frozen=True, slots=True)
class ClassificationDecision:
    """Acceptance result and exclusion reason for one listing."""

    include: bool
    category: OpportunityCategory
    employment_type: EmploymentType | None = None
    exclusion_reason: str | None = None


class Classifier:
    """Strict classifier for title-explicit internships and new-grad roles."""

    def __init__(self, rules: ClassificationRules, target_cycle: int) -> None:
        self.target_cycle = target_cycle
        self._internship_keywords = rules.internship_keywords
        self._new_grad_keywords = rules.new_grad_keywords
        self._excluded_role_keywords = rules.excluded_role_keywords
        self._non_technical_role_keywords = rules.non_technical_role_keywords
        self._categories = dict(rules.categories)

    def classify(
        self,
        *,
        title: str,
        description: str | None,
        location: LocationResult,
        posted_at: datetime | None = None,
    ) -> ClassificationDecision:
        """Apply strict opportunity type, role, cycle, and geography checks."""
        title_key = normalized_key(title)
        description_key = normalized_key(description or "")

        employment_type = self.classify_employment_type(title_key)
        if employment_type is None:
            return self._exclude(
                "title does not explicitly identify an internship or new-grad role"
            )
        if self._contains_any(title_key, self._excluded_role_keywords):
            return self._exclude("title contains excluded seniority terminology")
        if self._contains_any(title_key, self._non_technical_role_keywords):
            return self._exclude("title identifies a non-technology role")

        category = self.classify_category(title_key)
        # Unrelated titles cannot be rescued by technical description keywords.
        if category == OpportunityCategory.UNKNOWN and all(
            word.isdigit() or word in _GENERIC_TECH_TITLE_WORDS for word in title_key.split()
        ):
            category = self.classify_category("", description_key)
        if category == OpportunityCategory.UNKNOWN:
            return self._exclude("title has no technology-role signal")

        cycle = self.classify_cycle(title_key, description_key, employment_type)
        target_cycle = str(self.target_cycle)
        if cycle != target_cycle:
            if cycle != "unknown":
                return ClassificationDecision(
                    False,
                    category,
                    employment_type,
                    f"listing is for the {cycle} cycle",
                )
            if posted_at is None or ensure_utc(posted_at) < MINIMUM_POSTED_AT:
                return ClassificationDecision(
                    False,
                    category,
                    employment_type,
                    f"opportunity cycle is not explicitly {self.target_cycle} and posting "
                    "date is not eligible",
                )

        explicit_europe = not EUROPEAN_COUNTRY_CODES.isdisjoint(location.country_codes)
        # An explicit European country overrides broad text such as a global or mixed
        # location description; otherwise a clear non-European signal is rejected.
        if location.non_europe_signal and not explicit_europe:
            return ClassificationDecision(
                False, category, employment_type, "location is outside Europe"
            )
        if not (explicit_europe or location.europe_signal):
            return ClassificationDecision(
                False, category, employment_type, "location is not explicitly European"
            )

        return ClassificationDecision(True, category, employment_type)

    def classify_employment_type(self, title_key: str) -> EmploymentType | None:
        """Categorize a title into exactly one published opportunity type."""
        # Internship takes precedence for titles such as "graduate software intern".
        if self._contains_any(title_key, self._internship_keywords):
            return EmploymentType.INTERNSHIP
        if self._contains_any(title_key, self._new_grad_keywords):
            return EmploymentType.NEW_GRAD
        return None

    def classify_category(self, title_key: str, description_key: str = "") -> OpportunityCategory:
        """Return the first configured category found in title-first order."""
        for text in (title_key, description_key):
            for category, keywords in self._categories.items():
                if self._contains_any(text, keywords):
                    return category
        if self._contains_any(f"{title_key} {description_key}", _OTHER_TECH_KEYWORDS):
            return OpportunityCategory.OTHER_TECH
        return OpportunityCategory.UNKNOWN

    def classify_cycle(
        self, title_key: str, description_key: str, employment_type: EmploymentType
    ) -> str:
        """Resolve the opportunity cycle without confusing internship eligibility text."""
        title_years = [
            match.group()
            for match in _YEAR_RE.finditer(title_key)
            if employment_type == EmploymentType.NEW_GRAD
            or not _is_eligibility_year(title_key, match.start())
        ]
        target = str(self.target_cycle)
        # Title years take precedence over description context.
        if title_years:
            return next((year for year in title_years if year != target), target)
        contextual_years = _contextual_years(
            description_key,
            ignore_eligibility=employment_type == EmploymentType.INTERNSHIP,
        )
        return next(
            (year for year in contextual_years if year != target),
            target if contextual_years else "unknown",
        )

    @staticmethod
    def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
        return any(contains_normalized_phrase(text, keyword) for keyword in keywords)

    @staticmethod
    def _exclude(reason: str) -> ClassificationDecision:
        return ClassificationDecision(
            include=False,
            category=OpportunityCategory.UNKNOWN,
            exclusion_reason=reason,
        )


def _contextual_years(text: str, *, ignore_eligibility: bool) -> list[str]:
    """Return every year within the narrow opportunity-context window."""
    years: list[str] = []
    for year in _YEAR_RE.finditer(text):
        # Search only around this year. This stays linear for unusually repetitive
        # descriptions instead of comparing every year with every context term.
        window_start = max(0, year.start() - 48)
        window_end = min(len(text), year.end() + 48)
        has_context = any(
            0 <= year.start() - context.end() <= 24 or 0 <= context.start() - year.end() <= 24
            for context in _OPPORTUNITY_CONTEXT_RE.finditer(text, window_start, window_end)
        )
        if has_context and (not ignore_eligibility or not _is_eligibility_year(text, year.start())):
            years.append(year.group())
    return years


def _is_eligibility_year(text: str, year_start: int) -> bool:
    """Check whether a year reference narrowly describes candidate eligibility."""
    prefix = text[max(0, year_start - 64) : year_start]
    return bool(
        re.search(
            r"(?:class\s+of|"
            r"(?:must|should|will|to|expected\s+to|planning\s+to|eligible\s+to)\s+"
            r"graduate(?:\s+(?:in|by))?|"
            r"graduating(?:\s+(?:in|by))?|"
            r"graduation(?:\s+date)?(?:\s+(?:in|by))?)\s*$",
            prefix,
        )
    )
