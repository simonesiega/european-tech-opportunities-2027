from __future__ import annotations

from datetime import UTC, datetime

import pytest

from opportunities.config.rules import ClassificationRules
from opportunities.models.enums import EmploymentType, OpportunityCategory
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
        location=normalize_locations(["London, UK"] if locations is None else locations),
        posted_at=posted_at,
    )


def test_explicit_2027_software_internship_is_accepted(rules: ClassificationRules) -> None:
    result = classify(rules, title="Backend Software Engineering Intern 2027")
    assert result.include
    assert result.category == OpportunityCategory.SOFTWARE_ENGINEERING
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


def test_new_grad_graduation_year_is_cycle_evidence(rules: ClassificationRules) -> None:
    result = classify(
        rules,
        title="Graduate Software Engineer",
        description="Applicants must graduate in 2026.",
        posted_at=datetime(2026, 7, 18, tzinfo=UTC),
    )

    assert not result.include
    assert result.exclusion_reason == "listing is for the 2026 cycle"


def test_missing_cycle_is_accepted_for_recent_posting(rules: ClassificationRules) -> None:
    result = classify(
        rules,
        title="Graduate Software Engineer",
        posted_at=datetime(2026, 5, 1, tzinfo=UTC),
    )

    assert result.include
    assert result.employment_type == EmploymentType.NEW_GRAD
    assert result.category == OpportunityCategory.SOFTWARE_ENGINEERING


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


def test_program_year_is_not_mistaken_for_graduation_eligibility(
    rules: ClassificationRules,
) -> None:
    result = classify(
        rules,
        title="Graduate Software Engineer",
        description="Our graduate programme starts in 2026.",
        posted_at=datetime(2026, 7, 18, tzinfo=UTC),
    )

    assert not result.include
    assert result.exclusion_reason == "listing is for the 2026 cycle"


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
        posted_at=datetime(2026, 7, 13, tzinfo=UTC),
    )

    assert not result.include
    assert result.exclusion_reason == "listing is for the 2025 cycle"


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
    assert result.category == OpportunityCategory.SOFTWARE_ENGINEERING
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
    european_city_namesake = classify(
        rules,
        title="Software Engineering Intern 2027",
        locations=["London, Ontario, Canada"],
    )
    abbreviated_namesake = classify(
        rules,
        title="Software Engineering Intern 2027",
        locations=["Paris, TX"],
    )
    explicitly_outside_europe = classify(
        rules,
        title="Software Engineering Intern 2027",
        locations=["Remote, non-European"],
    )
    ambiguous_remote = classify(
        rules,
        title="Software Engineering Intern 2027",
        locations=["Remote"],
    )
    ambiguous_emea = classify(
        rules,
        title="Software Engineering Intern 2027",
        locations=["EMEA"],
    )
    emea_with_european_country = classify(
        rules,
        title="Software Engineering Intern 2027",
        locations=["EMEA; Berlin, Germany"],
    )
    assert not finance.include
    assert not usa.include
    assert not european_city_namesake.include
    assert not abbreviated_namesake.include
    assert not explicitly_outside_europe.include
    assert not ambiguous_remote.include
    assert not ambiguous_emea.include
    assert ambiguous_emea.exclusion_reason == "location is not explicitly European"
    assert emea_with_european_country.include
    assert ambiguous_remote.exclusion_reason == "location is not explicitly European"


@pytest.mark.parametrize(
    "location",
    [
        "Paris, US",
        "London, CA",
        "Perth, AU",
        "London, IN",
        "Paris, NZ",
        "London, SG",
        "Wilmington, DE, United States",
        "Portland, ME, USA",
        "Birmingham, AL, US",
        "Whitefish, MT, US",
        "Richmond, VA, United States",
        "Baltimore, MD, US",
        "Regina, SK, Canada",
        "St. Johns, NL, CA",
        "Porto Alegre, RS, Brazil",
    ],
)
def test_non_european_country_codes_prevent_city_fallback(
    rules: ClassificationRules, location: str
) -> None:
    result = classify(rules, title="Software Intern 2027", locations=[location])
    assert not result.include
    assert result.exclusion_reason == "location is outside Europe"


@pytest.mark.parametrize(
    "location", ["Paris, FR", "Berlin, DE", "London, GB", "London", "Berlin, Germany; US"]
)
def test_explicit_european_locations_remain_eligible(
    rules: ClassificationRules, location: str
) -> None:
    assert classify(rules, title="Software Intern 2027", locations=[location]).include


def test_description_can_classify_generic_technical_internship(
    rules: ClassificationRules,
) -> None:
    result = classify(
        rules,
        title="Technical Internship 2027",
        description="A machine learning engineering internship for summer 2027.",
    )
    assert result.include
    assert result.category == OpportunityCategory.MACHINE_LEARNING


@pytest.mark.parametrize("year", [1999, 2000, 2019, 2050, 2099, 2100])
@pytest.mark.parametrize("evidence", ["title", "description"])
@pytest.mark.parametrize("title", ["Software Intern", "Software Engineer New Grad"])
def test_conflicting_years_cannot_fall_back_to_recent_posting_dates(
    rules: ClassificationRules, year: int, evidence: str, title: str
) -> None:
    result = classify(
        rules,
        title=f"{title} {year}" if evidence == "title" else title,
        description=f"Our programme starts in {year}." if evidence == "description" else "",
        posted_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    assert not result.include
    assert result.exclusion_reason == f"listing is for the {year} cycle"


@pytest.mark.parametrize(
    ("title", "description", "posted_at"),
    [
        ("Software Intern 2027", "An old internship programme ran in 2019.", None),
        ("Class of 2050 Software Intern 2027", "", None),
        ("Software Intern", "Applicants must graduate in 2050.", datetime(2026, 7, 20, tzinfo=UTC)),
    ],
)
def test_title_precedence_and_internship_eligibility_remain_distinct(
    rules: ClassificationRules, title: str, description: str, posted_at: datetime | None
) -> None:
    result = classify(rules, title=title, description=description, posted_at=posted_at)
    assert result.include
    assert result.employment_type == EmploymentType.INTERNSHIP


@pytest.mark.parametrize("target", [2020, 2049, 2050, 2099, 2100])
def test_supported_target_cycles_need_no_posting_date(
    rules: ClassificationRules, target: int
) -> None:
    result = Classifier(rules, target).classify(
        title=f"Software Intern {target}",
        description=None,
        location=normalize_locations(["Germany"]),
    )
    assert result.include


@pytest.mark.parametrize("title", ["Software Intern", "Graduate Software Engineer"])
@pytest.mark.parametrize(
    ("timestamp", "include"),
    [
        ("2026-04-30T23:59:59.999999+00:00", False),
        ("2026-05-01T00:00:00+00:00", True),
        ("2026-05-01T01:59:59.999999+02:00", False),
        ("2026-05-01T02:00:00+02:00", True),
        ("2026-04-30T19:00:00-05:00", True),
    ],
)
def test_posting_floor_uses_the_utc_instant(
    rules: ClassificationRules, title: str, timestamp: str, include: bool
) -> None:
    result = classify(rules, title=title, posted_at=datetime.fromisoformat(timestamp))
    assert result.include is include
    if not include:
        assert result.exclusion_reason == (
            "opportunity cycle is not explicitly 2027 and posting date is not eligible"
        )


def test_explicit_separate_european_location_survives_a_mixed_country_list(
    rules: ClassificationRules,
) -> None:
    assert classify(rules, title="Software Intern 2027", locations=["DE", "US"]).include


@pytest.mark.parametrize("locations", [[], ["Remote"], ["EMEA"]])
def test_missing_or_ambiguous_geography_is_not_assumed_european(
    rules: ClassificationRules, locations: list[str]
) -> None:
    result = classify(rules, title="Software Intern 2027", locations=locations)
    assert not result.include
    assert result.exclusion_reason == "location is not explicitly European"
