"""Strict deterministic scope checks for 2027 European technology internships."""

from __future__ import annotations

import re
from dataclasses import dataclass

from internships.config.rules import ClassificationRules
from internships.models.enums import InternshipCategory
from internships.normalization.location import EUROPEAN_COUNTRY_CODES, LocationResult
from internships.utils.text import html_to_text, normalized_key

_YEAR_RE = re.compile(r"\b20[2-4]\d\b")
_CONTEXTUAL_YEAR_RE = re.compile(
    r"(?:internship|intern|summer|placement|programme|program|cycle)\W{0,24}(20[2-4]\d)|"
    r"(20[2-4]\d)\W{0,24}(?:internship|intern|summer|placement|programme|program|cycle)"
)
_TITLE_SCOPE_NOISE = frozenset(
    {"co", "coop", "intern", "internship", "placement", "student", "summer", "university"}
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
    category: InternshipCategory
    exclusion_reason: str | None = None


class Classifier:
    """Accept only title-explicit internships in the target cycle and geography."""

    def __init__(self, rules: ClassificationRules, target_cycle: int) -> None:
        """Initialize the instance dependencies and state."""
        self.rules = rules
        self.target_cycle = target_cycle
        # Normalize configured phrases once; classification runs for every detail page.
        self._internship_keywords = tuple(
            normalized_key(item) for item in rules.internship_keywords
        )
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
    ) -> ClassificationDecision:
        """Apply strict internship, role, cycle, and geography checks."""
        title_key = normalized_key(title)
        description_key = normalized_key(html_to_text(description))

        if not self._contains_any(title_key, self._internship_keywords):
            return self._exclude("title does not explicitly identify an internship")
        if self._contains_any(title_key, self._excluded_role_keywords):
            return self._exclude("title contains excluded seniority terminology")

        category = self.classify_category(title_key)
        # Description fallback is deliberately narrow: generic technology titles may
        # use it, but an unrelated explicit title cannot be reclassified by body text.
        if category == InternshipCategory.UNKNOWN and self._description_can_define_category(
            title_key
        ):
            category = self.classify_category("", description_key)
        if category == InternshipCategory.UNKNOWN:
            return self._exclude("title has no technology-role signal")

        cycle = self.classify_cycle(title_key, description_key)
        if cycle != str(self.target_cycle):
            reason = (
                f"listing is for the {cycle} cycle"
                if cycle != "unknown"
                else f"internship cycle is not explicitly {self.target_cycle}"
            )
            return ClassificationDecision(False, category, reason)

        explicit_europe = bool(set(location.country_codes) & EUROPEAN_COUNTRY_CODES)
        # An explicit European country overrides broad text such as a global or mixed
        # location description; otherwise a clear non-European signal is rejected.
        if location.non_europe_signal and not explicit_europe:
            return ClassificationDecision(False, category, "location is outside Europe")
        if not (explicit_europe or location.europe_signal):
            return ClassificationDecision(False, category, "location is not explicitly European")

        return ClassificationDecision(True, category)

    def classify_category(self, title_key: str, description_key: str = "") -> InternshipCategory:
        """Return the first configured category found in title-first order."""
        for text in (title_key, description_key):
            for category, keywords in self._categories.items():
                if self._contains_any(text, keywords):
                    return category
        if self._contains_any(f"{title_key} {description_key}", _OTHER_TECH_KEYWORDS):
            return InternshipCategory.OTHER_TECH
        return InternshipCategory.UNKNOWN

    def classify_cycle(self, title_key: str, description_key: str) -> str:
        """Resolve the internship cycle while ignoring graduation-year eligibility."""
        title_years = [
            match.group()
            for match in _YEAR_RE.finditer(title_key)
            if not _is_eligibility_year(title_key, match.start())
        ]
        target = str(self.target_cycle)
        # Title evidence has priority over description context; accepting a body year
        # first could misclassify an explicitly advertised internship cycle.
        if target in title_years:
            return target
        if title_years:
            return title_years[0]
        contextual_years: list[str] = []
        for match in _CONTEXTUAL_YEAR_RE.finditer(description_key):
            group = 1 if match.group(1) else 2
            if not _is_eligibility_year(description_key, match.start(group)):
                contextual_years.append(str(match.group(group)))
        if target in contextual_years:
            return target
        return contextual_years[0] if contextual_years else "unknown"

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
        return ClassificationDecision(False, InternshipCategory.UNKNOWN, reason)


def _contains_phrase(text: str, phrase: str) -> bool:
    """Check whether normalized text contains a complete phrase."""
    return bool(phrase and re.search(rf"(?:^|\s){re.escape(phrase)}(?:$|\s)", text))


def _is_eligibility_year(text: str, year_start: int) -> bool:
    """Check whether a year reference only describes candidate eligibility."""
    prefix = text[max(0, year_start - 40) : year_start]
    return bool(re.search(r"(?:class\s+of|graduat\w*)(?:\s+\w+){0,4}\s*$", prefix))
