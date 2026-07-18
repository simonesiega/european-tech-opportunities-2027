from __future__ import annotations

from datetime import UTC, datetime

from opportunities.config.rules import ClassificationRules
from opportunities.models.enums import EmploymentType, InternshipCategory
from opportunities.normalization.location import normalize_locations
from opportunities.pipeline.classification import ClassificationDecision, Classifier


def classify(
    rules: ClassificationRules,
    *,
    title: str,
    description: str = "",
    locations: list[str] | None = None,
    posted_at: datetime | None = None,
) -> ClassificationDecision:
    return Classifier(rules, target_cycle=2027).classify(
        title=title,
        description=description,
        location=normalize_locations(locations or ["London, UK"]),
        posted_at=posted_at,
    )


def test_explicit_2027_software_internship_is_accepted(rules: ClassificationRules) -> None:
    result = classify(rules, title="Backend Software Engineering Intern 2027")
    assert result.include
    assert result.category == InternshipCategory.SOFTWARE_ENGINEERING
    assert result.employment_type == EmploymentType.INTERNSHIP


def test_cycle_must_be_explicit_and_not_only_graduation_year(
    rules: ClassificationRules,
) -> None:
    unknown = classify(
        rules,
        title="Software Engineering Intern",
        description="Applicants must graduate in 2027.",
    )
    class_of = classify(rules, title="Class of 2027 Software Engineering Intern")
    assert not unknown.include
    assert not class_of.include


def test_missing_cycle_is_accepted_for_recent_posting(rules: ClassificationRules) -> None:
    result = classify(
        rules,
        title="Graduate Software Engineer",
        posted_at=datetime(2026, 5, 1, tzinfo=UTC),
    )

    assert result.include
    assert result.employment_type == EmploymentType.NEW_GRAD
    assert result.category == InternshipCategory.SOFTWARE_ENGINEERING


def test_wrong_cycle_is_excluded(rules: ClassificationRules) -> None:
    result = classify(
        rules,
        title="Software Engineering Internship 2026",
        posted_at=datetime(2026, 7, 18, tzinfo=UTC),
    )
    assert not result.include
    assert result.exclusion_reason == "listing is for the 2026 cycle"


def test_conflicting_cycle_evidence_is_rejected(rules: ClassificationRules) -> None:
    conflicting_title = classify(
        rules,
        title="Graduate Software Engineer 2026/2027",
    )
    conflicting_description = classify(
        rules,
        title="Graduate Software Engineer",
        description=(
            "Our 2026 graduate programme remains open. The 2027 graduate programme is now open."
        ),
    )

    assert not conflicting_title.include
    assert conflicting_title.exclusion_reason == "listing is for the 2026 cycle"
    assert not conflicting_description.include
    assert conflicting_description.exclusion_reason == "listing is for the 2026 cycle"


def test_canonical_2025_2026_graduate_listing_is_rejected(
    rules: ClassificationRules,
) -> None:
    result = classify(
        rules,
        title="Graduate Software Engineer, Open Source and Linux, Canonical Ubuntu",
        description=(
            "We are hiring 2025 and 2026 Graduate Software Engineers into engineering "
            "teams around the world."
        ),
        locations=["EMEA"],
    )

    assert not result.include
    assert result.exclusion_reason == "listing is for the 2026 cycle"


def test_full_time_title_is_rejected_even_if_description_mentions_internships(
    rules: ClassificationRules,
) -> None:
    result = classify(
        rules,
        title="Senior Software Engineer 2027",
        description="Our company operates a large internship programme.",
    )
    assert not result.include
    assert (
        result.exclusion_reason
        == "title does not explicitly identify an internship or new-grad role"
    )


def test_explicit_2027_new_grad_role_is_accepted(rules: ClassificationRules) -> None:
    result = classify(rules, title="Software Engineer, University Graduate 2027")

    assert result.include
    assert result.category == InternshipCategory.SOFTWARE_ENGINEERING
    assert result.employment_type == EmploymentType.NEW_GRAD


def test_new_grad_cycle_and_seniority_remain_strict(rules: ClassificationRules) -> None:
    wrong_cycle = classify(rules, title="Graduate Data Engineer 2026")
    senior = classify(rules, title="Senior New Grad Software Engineer 2027")

    assert not wrong_cycle.include
    assert wrong_cycle.exclusion_reason == "listing is for the 2026 cycle"
    assert not senior.include
    assert senior.exclusion_reason == "title contains excluded seniority terminology"


def test_title_with_both_types_is_categorized_as_internship(rules: ClassificationRules) -> None:
    result = classify(rules, title="Graduate Software Engineering Internship 2027")

    assert result.include
    assert result.employment_type == EmploymentType.INTERNSHIP


def test_senior_intern_title_is_excluded(rules: ClassificationRules) -> None:
    result = classify(rules, title="Senior Software Engineering Intern 2027")
    assert not result.include
    assert result.exclusion_reason == "title contains excluded seniority terminology"


def test_non_technology_and_non_european_jobs_are_excluded(
    rules: ClassificationRules,
) -> None:
    finance = classify(rules, title="Finance Intern 2027")
    usa = classify(
        rules,
        title="Software Engineering Intern 2027",
        locations=["New York, United States"],
    )
    assert not finance.include
    assert not usa.include


def test_description_can_classify_generic_technical_internship(
    rules: ClassificationRules,
) -> None:
    result = classify(
        rules,
        title="Technical Internship 2027",
        description="A machine learning engineering internship for summer 2027.",
    )
    assert result.include
    assert result.category == InternshipCategory.MACHINE_LEARNING
