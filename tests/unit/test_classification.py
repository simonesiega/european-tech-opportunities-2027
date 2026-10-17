from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

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


def test_title_with_both_types_is_categorized_as_internship(rules: ClassificationRules) -> None:
    result = classify(rules, title="Graduate Software Engineering Internship 2027")

    assert result.include
    assert result.employment_type == EmploymentType.INTERNSHIP


@pytest.mark.parametrize(
    "title", ["Senior Software Engineering Intern 2027", "Senior New Grad Software Engineer 2027"]
)
def test_senior_opportunity_title_is_excluded(rules: ClassificationRules, title: str) -> None:
    result = classify(rules, title=title)
    assert not result.include
    assert result.exclusion_reason == "title contains excluded seniority terminology"


def test_non_technology_title_cannot_be_rescued_by_technical_description(
    rules: ClassificationRules,
) -> None:
    result = classify(
        rules,
        title="Finance Intern 2027",
        description="Work alongside software engineering and machine learning teams.",
    )
    assert not result.include
    assert result.exclusion_reason == "title has no technology-role signal"


@pytest.mark.parametrize(
    "title",
    [
        "Market Research Intern 2027",
        "Clinical Research Intern 2027",
        "Software Sales Intern 2027",
        "Software Marketing Intern 2027",
        "Software Recruitment Intern 2027",
        "Business Developer Intern 2027",
        "Graduate Software Sales 2027",
    ],
)
def test_non_technical_roles_cannot_be_rescued_by_technology_keywords(
    rules: ClassificationRules, title: str
) -> None:
    result = classify(
        rules,
        title=title,
        description="Software engineering and machine learning research in a technology team.",
    )
    assert not result.include
    assert result.exclusion_reason == "title identifies a non-technology role"


@pytest.mark.parametrize(
    "title",
    ["Research Intern 2027", "Research Scientist Intern 2027", "Biology Research Internship 2027"],
)
def test_generic_research_titles_require_technology_evidence(
    rules: ClassificationRules, title: str
) -> None:
    result = classify(rules, title=title)
    assert not result.include
    assert result.exclusion_reason == "title has no technology-role signal"


@pytest.mark.parametrize(
    ("title", "description", "category"),
    [
        ("Research Engineer Intern 2027", "", OpportunityCategory.RESEARCH_ENGINEERING),
        ("AI Research Intern 2027", "", OpportunityCategory.RESEARCH_ENGINEERING),
        (
            "Research Scientist Intern 2027",
            "Machine learning research on computer vision.",
            OpportunityCategory.MACHINE_LEARNING,
        ),
        (
            "Research Intern 2027",
            "Computer science research on compilers.",
            OpportunityCategory.RESEARCH_ENGINEERING,
        ),
        (
            "Salesforce Software Engineering Intern 2027",
            "",
            OpportunityCategory.SOFTWARE_ENGINEERING,
        ),
        ("Software Engineering Intern 2027", "", OpportunityCategory.SOFTWARE_ENGINEERING),
    ],
)
def test_technical_roles_remain_eligible_next_to_non_technical_exclusions(
    rules: ClassificationRules,
    title: str,
    description: str,
    category: OpportunityCategory,
) -> None:
    result = classify(rules, title=title, description=description)
    assert result.include
    assert result.category == category
    assert result.employment_type == EmploymentType.INTERNSHIP


@pytest.mark.parametrize(
    "title", ["International Software Engineer 2027", "Internal Software Engineer 2027"]
)
def test_employment_type_requires_whole_word_evidence(
    rules: ClassificationRules, title: str
) -> None:
    result = classify(rules, title=title)
    assert not result.include
    assert result.exclusion_reason == (
        "title does not explicitly identify an internship or new-grad role"
    )


@pytest.mark.parametrize(
    "location",
    [
        "New York, United States",
        "London, Ontario, Canada",
        "Paris, TX",
        "Remote, non-European",
        "Paris, US",
        "London, CA",
        "Perth, AU",
        "London, IN",
        "Paris, NZ",
        "London, SG",
        # State and province abbreviations can collide with European country codes.
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
def test_explicit_non_european_locations_prevent_city_fallback(
    rules: ClassificationRules, location: str
) -> None:
    result = classify(rules, title="Software Intern 2027", locations=[location])
    assert not result.include
    assert result.exclusion_reason == "location is outside Europe"


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


@pytest.mark.parametrize(
    ("title", "description", "year"),
    [
        # Each lexical boundary reaches both evidence paths. Alternate employment
        # types instead of multiplying every equivalent year by every type.
        ("Software Intern 1999", "", 1999),
        ("Software Engineer New Grad", "Our programme starts in 1999.", 1999),
        ("Software Engineer New Grad 2000", "", 2000),
        ("Software Intern", "Our programme starts in 2000.", 2000),
        ("Software Intern 2019", "", 2019),
        ("Software Engineer New Grad", "Our programme starts in 2019.", 2019),
        ("Software Engineer New Grad 2050", "", 2050),
        ("Software Intern", "Our programme starts in 2050.", 2050),
        ("Software Intern 2099", "", 2099),
        ("Software Engineer New Grad", "Our programme starts in 2099.", 2099),
        ("Software Engineer New Grad 2100", "", 2100),
        ("Software Intern", "Our programme starts in 2100.", 2100),
        # These have different semantics from a single generic programme year.
        ("Software Engineering Internship 2026", "", 2026),
        ("Graduate Data Engineer 2026", "", 2026),
        ("Graduate Software Engineer", "Applicants must graduate in 2026.", 2026),
        ("Graduate Software Engineer", "Our graduate programme starts in 2026.", 2026),
        ("Graduate Software Engineer 2026/2027", "", 2026),
        (
            "Graduate Software Engineer",
            "Our 2026 graduate programme remains open. The 2027 graduate programme is now open.",
            2026,
        ),
    ],
)
def test_conflicting_years_cannot_fall_back_to_recent_posting_dates(
    rules: ClassificationRules, title: str, description: str, year: int
) -> None:
    result = classify(
        rules,
        title=title,
        description=description,
        posted_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    assert not result.include
    assert result.exclusion_reason == f"listing is for the {year} cycle"
    assert result.employment_type == (
        EmploymentType.INTERNSHIP if "Intern" in title else EmploymentType.NEW_GRAD
    )
    assert result.category == (
        OpportunityCategory.DATA_ENGINEERING
        if title == "Graduate Data Engineer 2026"
        else OpportunityCategory.SOFTWARE_ENGINEERING
    )


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


@pytest.mark.parametrize("target", [2020, 2050, 2100])
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
    assert result.category == OpportunityCategory.SOFTWARE_ENGINEERING
    assert result.employment_type == (
        EmploymentType.INTERNSHIP if title == "Software Intern" else EmploymentType.NEW_GRAD
    )
    if not include:
        assert result.exclusion_reason == (
            "opportunity cycle is not explicitly 2027 and posting date is not eligible"
        )


@pytest.mark.parametrize(
    ("location", "codes", "include"),
    [
        (case["location"], case["codes"], case["include"])
        for case in json.loads(
            (
                Path(__file__).parents[2]
                / "site"
                / "tests"
                / "fixtures"
                / "european_locations.json"
            ).read_text(encoding="utf-8")
        )
    ],
)
def test_shared_location_cases_do_not_invent_european_evidence(
    rules: ClassificationRules, location: str, codes: list[str], include: bool
) -> None:
    normalized = normalize_locations([location])
    assert normalized.country_codes == codes
    result = classify(rules, title="Software Intern 2027", locations=[location])
    assert result.include is include


def test_explicit_separate_european_location_survives_a_mixed_country_list(
    rules: ClassificationRules,
) -> None:
    # Separate entries are independent locations; US must not reinterpret DE as Delaware.
    assert classify(rules, title="Software Intern 2027", locations=["DE", "US"]).include


@pytest.mark.parametrize("locations", [[], ["Remote"], ["EMEA"]])
def test_missing_or_ambiguous_geography_is_not_assumed_european(
    rules: ClassificationRules, locations: list[str]
) -> None:
    result = classify(rules, title="Software Intern 2027", locations=locations)
    assert not result.include
    assert result.exclusion_reason == "location is not explicitly European"
