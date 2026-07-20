"""Strict deterministic checks for 2027 European tech internships and new-grad roles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from opportunities.config.policy import MINIMUM_POSTED_AT
from opportunities.config.rules import ClassificationRules
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.normalization.location import EUROPEAN_COUNTRY_CODES, LocationResult
from opportunities.utils.text import html_to_text, normalized_key
from opportunities.utils.time import ensure_utc

_YEAR_RE = re.compile(r"\b20[2-4]\d\b")
_OPPORTUNITY_CONTEXT_RE = re.compile(
    r"\b(?:internship|intern|summer|placement|programme|program|cycle|graduate|"
    r"new\s+grad|early\s+career|entry\s+level)\b"
)
_TITLE_SCOPE_NOISE = frozenset(
    {
        "career",
        "co",
        "coop",
        "early",
        "entry",
        "grad",
        "graduate",
        "intern",
        "internship",
        "level",
        "new",
        "placement",
        "student",
        "summer",
        "university",
    }
)
_DESCRIPTION_CATEGORY_TITLE_WORDS = frozenset(
    {
        "ai",
        "computer",
        "data",
        "developer",
        "engineering",
        "ml",
        "research",
        "science",
        "software",
        "technical",
        "technology",
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
    """Describe the acceptance decision for one job."""

    include: bool
    category: OpportunityCategory
    employment_type: EmploymentType | None = None
    exclusion_reason: str | None = None


class Classifier:
    """Accept only title-explicit internships or new-grad roles in scope."""

    def __init__(self, rules: ClassificationRules, target_cycle: int) -> None:
        """Initialize the instance dependencies and state."""
        self.rules = rules
        self.target_cycle = target_cycle
        # Normalize configured phrases once; classification runs for every detail page.
        self._internship_keywords = tuple(
            normalized_key(item) for item in rules.internship_keywords
        )
        self._new_grad_keywords = tuple(normalized_key(item) for item in rules.new_grad_keywords)
        self._excluded_role_keywords = tuple(
            normalized_key(item) for item in rules.excluded_role_keywords
        )
        self._categories = {
            category: tuple(normalized_key(item) for item in keywords)
            for category, keywords in rules.categories.items()
        }

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
        description_key = normalized_key(html_to_text(description))

        employment_type = self.classify_employment_type(title_key)
        if employment_type is None:
            return self._exclude(
                "title does not explicitly identify an internship or new-grad role"
            )
        if self._contains_any(title_key, self._excluded_role_keywords):
            return self._exclude("title contains excluded seniority terminology")

        category = self.classify_category(title_key)
        # Description fallback is deliberately narrow: generic technology titles may
        # use it, but an unrelated explicit title cannot be reclassified by body text.
        if category == OpportunityCategory.UNKNOWN and self._description_can_define_category(
            title_key
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

        explicit_europe = bool(set(location.country_codes) & EUROPEAN_COUNTRY_CODES)
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
        # Title evidence has priority over description context; accepting a body year
        # first could misclassify an explicitly advertised internship cycle.
        conflicting_title_year = next((year for year in title_years if year != target), None)
        if conflicting_title_year is not None:
            return conflicting_title_year
        if target in title_years:
            return target
        contextual_years = _contextual_years(
            description_key,
            ignore_eligibility=employment_type == EmploymentType.INTERNSHIP,
        )
        conflicting_contextual_year = next(
            (year for year in contextual_years if year != target), None
        )
        if conflicting_contextual_year is not None:
            return conflicting_contextual_year
        return target if target in contextual_years else "unknown"

    @staticmethod
    def _description_can_define_category(title_key: str) -> bool:
        """Check whether description fallback is allowed for the title."""
        words = {word for word in set(title_key.split()) - _TITLE_SCOPE_NOISE if not word.isdigit()}
        return not words or words <= _DESCRIPTION_CATEGORY_TITLE_WORDS

    def _contains_any(self, text: str, keywords: tuple[str, ...]) -> bool:
        """Check whether text contains any normalized configured phrase."""
        return any(_contains_phrase(text, keyword) for keyword in keywords)

    @staticmethod
    def _exclude(reason: str) -> ClassificationDecision:
        """Build an excluded classification decision."""
        return ClassificationDecision(
            include=False,
            category=OpportunityCategory.UNKNOWN,
            exclusion_reason=reason,
        )


def _contains_phrase(text: str, phrase: str) -> bool:
    """Check whether normalized text contains a complete phrase."""
    return bool(phrase and re.search(rf"(?:^|\s){re.escape(phrase)}(?:$|\s)", text))


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
