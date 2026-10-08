from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from pydantic import ValidationError

from opportunities.database.repository import PersistSummary
from opportunities.models.data_quality import DataQualitySnapshot
from opportunities.models.enums import EmploymentType, OpportunityCategory, RunStatus
from opportunities.models.job import StoredJob
from opportunities.models.raw import RawJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.data_quality import DataQualityAnalysis, analyze_collection_quality
from opportunities.pipeline.runner import PipelineResult, SearchOutcome
from opportunities.scrapers.linkedin import LinkedInScrapeResult


def _search() -> LinkedInSearchConfig:
    return LinkedInSearchConfig(
        name="Synthetic European search",
        slug="software-internships",
        keywords="software intern 2027",
        location="Europe",
        max_pages=1,
        max_results=25,
    )


def _open_jobs(country: str = "London, United Kingdom", count: int = 10) -> list[StoredJob]:
    return [
        StoredJob(
            linkedin_job_id=str(1111111111 + index),
            company=f"Synthetic Company {index}",
            title="Software Engineering Intern 2027",
            location=country,
            link=f"https://www.linkedin.com/jobs/view/{1111111111 + index}",
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.INTERNSHIP,
            industries="Software Development",
            start_date="Summer 2027",
            first_seen_at=datetime(2026, 7, 1, tzinfo=UTC),
            last_seen_at=datetime(2026, 7, 2, tzinfo=UTC),
            updated_at=datetime(2026, 7, 2, tzinfo=UTC),
            status="open",
        )
        for index in range(count)
    ]


def _raw_job(index: int, *, complete: bool = True) -> RawJob:
    job_id = str(2222222222 + index)
    return RawJob(
        source_job_id=job_id,
        company="Synthetic Company",
        title="Software Engineering Intern 2027",
        locations=["London, United Kingdom"] if complete else [],
        application_url=f"https://www.linkedin.com/jobs/view/{job_id}",
        description="Summer software internship." if complete else None,
        industries="Software Development" if complete else None,
        start_date="Summer 2027" if complete else None,
        posted_at=datetime(2026, 7, 1, tzinfo=UTC) if complete else None,
    )


def _collection(
    *,
    found: int = 20,
    accepted: int = 10,
    parsed: int = 20,
    complete_parser_fields: bool = True,
    missing_parser_fields: int = 0,
    search: LinkedInSearchConfig | None = None,
    warnings: tuple[str, ...] = (),
    failed: bool = False,
) -> PipelineResult:
    """Separate discovery and detail counts: rechecks need not produce new search cards."""
    search = search or _search()
    if failed:
        found = accepted = parsed = 0
        warnings = ()
    assert 0 <= accepted <= parsed
    positions = [
        _raw_job(
            index,
            complete=complete_parser_fields and index >= missing_parser_fields,
        )
        for index in range(parsed)
    ]
    scrape_result = LinkedInScrapeResult(
        positions=positions,
        warnings=warnings,
        pages_fetched=1,
        search_result_count=found,
    )
    outcome = SearchOutcome(
        search=search,
        run_id="synthetic-run",
        started_at=datetime(2026, 7, 1, tzinfo=UTC),
        finished_at=datetime(2026, 7, 1, tzinfo=UTC),
        duration_ms=1,
        result=None if failed else scrape_result,
        accepted_count=accepted,
        excluded_count=parsed - accepted,
    )
    return PipelineResult(
        status=RunStatus.FAILED if failed else RunStatus.SUCCESS,
        successful_searches=0 if failed else 1,
        failed_searches=1 if failed else 0,
        found=found,
        accepted=accepted,
        excluded=parsed - accepted,
        warnings=len(warnings),
        summary=PersistSummary(),
        outcomes=(outcome,),
    )


def _analyze(
    result: PipelineResult,
    *,
    jobs: list[StoredJob] | None = None,
    baselines: tuple[str, ...] = (),
    search: LinkedInSearchConfig | None = None,
    days: int = 0,
) -> DataQualityAnalysis:
    return analyze_collection_quality(
        result,
        open_jobs=_open_jobs() if jobs is None else jobs,
        previous_snapshots=baselines,
        configured_searches=[search or _search()],
        generated_at=datetime(2026, 7, 20, tzinfo=UTC) + timedelta(days=days),
    )


def _stable_baselines(
    *,
    accepted: int = 10,
    complete_parser_fields: bool = True,
    jobs: list[StoredJob] | None = None,
) -> tuple[str, ...]:
    snapshots: list[str] = []
    for index in range(3):
        analysis = _analyze(
            _collection(accepted=accepted, complete_parser_fields=complete_parser_fields),
            jobs=jobs,
            days=index - 3,
        )
        assert analysis.snapshot_json is not None
        snapshots.append(analysis.snapshot_json)
    # Match the repository's newest-first baseline order.
    return tuple(reversed(snapshots))


def _codes(analysis: DataQualityAnalysis) -> set[str]:
    checks = cast(list[dict[str, object]], analysis.report["checks"])
    return {str(check["code"]) for check in checks}


def test_first_observation_builds_a_sanitized_baseline_without_false_alerts() -> None:
    analysis = _analyze(_collection())

    assert analysis.report["status"] == "passed"
    assert analysis.report["checks"] == []
    assert analysis.snapshot_json is not None
    assert cast(dict[str, object], analysis.report["baseline"])["status"] == "warming_up"
    assert "Synthetic Company" not in analysis.snapshot_json
    assert "1111111111" not in analysis.snapshot_json
    assert json.loads(analysis.snapshot_json)["schema_version"] == 1


def test_report_identifies_partial_registry_scope() -> None:
    second_search = _search().model_copy(update={"slug": "another-search"})
    analysis = analyze_collection_quality(
        _collection(),
        open_jobs=_open_jobs(),
        previous_snapshots=(),
        configured_searches=[_search(), second_search],
        generated_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    scope = cast(dict[str, object], analysis.report["scope"])

    assert scope == {
        "complete_registry_run": False,
        "enabled_search_count": 2,
        "attempted_search_count": 1,
        "skipped_search_count": 0,
        "successful_search_count": 1,
    }
    assert analysis.snapshot_json is None


def test_acceptance_rate_uses_classified_records_not_search_card_count() -> None:
    analysis = _analyze(_collection(found=0, accepted=10, parsed=20))
    metrics = cast(dict[str, object], analysis.report["metrics"])
    current = cast(dict[str, object], metrics["current"])

    assert current["found_count"] == 0
    assert current["accepted_count"] == 10
    assert current["acceptance_rate"] == 0.5


def test_eighty_percent_candidate_volume_drop_warns_but_does_not_block() -> None:
    analysis = _analyze(
        _collection(found=4, accepted=10, parsed=20),
        baselines=_stable_baselines(),
    )

    assert analysis.report["status"] == "warning"
    assert not analysis.blocking
    assert "collected_volume_drop" in _codes(analysis)
    assert "acceptance_rate_drift" not in _codes(analysis)


def test_all_searches_returning_zero_after_a_productive_baseline_blocks() -> None:
    analysis = _analyze(
        _collection(found=0, accepted=0, parsed=0),
        baselines=_stable_baselines(),
    )

    assert analysis.blocking
    assert analysis.report["status"] == "failed"
    assert "search_returned_zero_candidates" in _codes(analysis)
    assert "all_searches_returned_zero_candidates" in _codes(analysis)


def test_search_configuration_change_resets_its_drift_baseline() -> None:
    changed_search = _search().model_copy(update={"keywords": "different software interns 2027"})
    analysis = _analyze(
        _collection(found=0, accepted=0, parsed=0, search=changed_search),
        baselines=_stable_baselines(),
        search=changed_search,
    )

    assert not analysis.blocking
    assert analysis.report["checks"] == []


def test_extreme_acceptance_and_parser_field_missingness_are_reported() -> None:
    analysis = _analyze(
        _collection(accepted=0, complete_parser_fields=False),
        baselines=_stable_baselines(accepted=20),
    )

    assert analysis.blocking
    assert "acceptance_rate_drift" in _codes(analysis)
    assert "parser_field_missing_rate_high" in _codes(analysis)


def test_category_country_and_optional_field_distribution_shifts_are_reported() -> None:
    jobs = [
        job.model_copy(
            update={
                "location": "Berlin, Germany",
                "category": OpportunityCategory.COMPUTER_SCIENCE,
                "industries": None,
                "start_date": None,
            }
        )
        for job in _open_jobs()
    ]
    analysis = _analyze(_collection(), jobs=jobs, baselines=_stable_baselines())

    assert "category_disappeared" in _codes(analysis)
    assert "country_distribution_shift" in _codes(analysis)
    assert "optional_field_missing_rate_high" in _codes(analysis)


def test_country_distribution_warns_when_country_codes_disappear() -> None:
    analysis = _analyze(
        _collection(),
        jobs=_open_jobs(country="Europe"),
        baselines=_stable_baselines(),
    )

    assert "country_distribution_unavailable" in _codes(analysis)


def test_moderate_optional_field_missing_jump_is_reported_against_baseline() -> None:
    jobs = [
        job.model_copy(update={"industries": None}) if index < 5 else job
        for index, job in enumerate(_open_jobs())
    ]
    analysis = _analyze(_collection(), jobs=jobs, baselines=_stable_baselines())

    assert "optional_field_missing_rate_drift" in _codes(analysis)
    assert "optional_field_missing_rate_high" not in _codes(analysis)


def test_moderate_parser_field_missing_jump_is_reported_against_baseline() -> None:
    analysis = _analyze(
        _collection(missing_parser_fields=10),
        baselines=_stable_baselines(),
    )

    assert "parser_field_missing_rate_drift" in _codes(analysis)
    assert "parser_field_missing_rate_high" not in _codes(analysis)


def test_stable_absolute_field_missingness_does_not_repeat_alerts() -> None:
    jobs = [job.model_copy(update={"industries": None, "start_date": None}) for job in _open_jobs()]
    baselines = _stable_baselines(complete_parser_fields=False, jobs=jobs)
    analysis = _analyze(
        _collection(complete_parser_fields=False),
        jobs=jobs,
        baselines=baselines,
    )

    codes = _codes(analysis)
    assert "optional_field_missing_rate_high" not in codes
    assert "parser_field_missing_rate_high" not in codes
    assert "optional_field_missing_rate_drift" not in codes
    assert "parser_field_missing_rate_drift" not in codes


def test_missing_field_comparisons_require_sampled_history() -> None:
    baselines = []
    for index in range(3):
        snapshot = _analyze(
            _collection(found=0, accepted=0, parsed=0),
            jobs=[],
            days=index - 3,
        ).snapshot_json
        assert snapshot is not None
        baselines.append(snapshot)
    jobs = [job.model_copy(update={"industries": None, "start_date": None}) for job in _open_jobs()]
    analysis = _analyze(
        _collection(complete_parser_fields=False),
        jobs=jobs,
        baselines=tuple(baselines),
    )

    assert analysis.report["checks"] == []


def test_malformed_snapshots_are_ignored_and_reported() -> None:
    analysis = _analyze(_collection(), baselines=("not json",))

    assert not analysis.blocking
    assert "baseline_snapshot_invalid" in _codes(analysis)


# With 20 classified records, differences of 8 and 15 reach the warning and blocking
# thresholds (40 and 75 percentage points); adjacent values test the boundaries.
@pytest.mark.parametrize(
    ("accepted", "baseline_accepted", "severity"),
    [
        (11, 4, None),
        (12, 4, "warning"),
        (4, 12, "warning"),
        (15, 0, "blocking"),
        (0, 15, "blocking"),
        (14, 0, "warning"),
    ],
)
def test_acceptance_thresholds_in_both_directions(
    accepted: int,
    baseline_accepted: int,
    severity: str | None,
) -> None:
    analysis = _analyze(
        _collection(accepted=accepted), baselines=_stable_baselines(accepted=baseline_accepted)
    )
    checks = cast(list[dict[str, object]], analysis.report["checks"])
    acceptance = [check for check in checks if check["code"] == "acceptance_rate_drift"]
    assert [check["severity"] for check in acceptance] == ([] if severity is None else [severity])
    assert (analysis.snapshot_json is None) == (severity == "blocking")
    assert "collected_volume_drop" not in _codes(analysis)


@pytest.mark.parametrize("baseline_count", [0, 1, 2])
def test_empty_search_warms_up_without_premature_blocking(baseline_count: int) -> None:
    analysis = _analyze(
        _collection(found=0, accepted=0, parsed=0),
        baselines=_stable_baselines()[:baseline_count],
    )
    assert analysis.report["checks"] == []
    assert analysis.snapshot_json is not None


@pytest.mark.parametrize("found", [5, 20, 30])
def test_candidate_volume_above_drop_threshold_does_not_warn(found: int) -> None:
    assert "collected_volume_drop" not in _codes(
        _analyze(_collection(found=found), baselines=_stable_baselines())
    )


def test_small_acceptance_samples_do_not_trigger_a_block() -> None:
    analysis = _analyze(_collection(parsed=9, accepted=0), baselines=_stable_baselines(accepted=20))
    assert "acceptance_rate_drift" not in _codes(analysis)
    small = _analyze(_collection(parsed=9, accepted=9), days=-1).snapshot_json
    assert small is not None
    assert "acceptance_rate_drift" not in _codes(
        _analyze(_collection(accepted=0), baselines=(small,) * 3)
    )


@pytest.mark.parametrize("warnings", [2, 4, 5, 25])
def test_scraper_warning_frequency_is_bounded_and_sanitized(warnings: int) -> None:
    analysis = _analyze(_collection(warnings=("private-diagnostic-must-not-leak",) * warnings))
    assert ("scraper_warning_rate_high" in _codes(analysis)) == (warnings >= 5)
    assert "must-not-leak" not in json.dumps(analysis.report)
    if warnings >= 5:
        checks = cast(list[dict[str, object]], analysis.report["checks"])
        context = cast(dict[str, float], checks[0]["context"])
        assert 0 <= context["warning_rate"] <= 1


def test_editorial_search_changes_preserve_drift_detection() -> None:
    search = _search().model_copy(update={"name": "Renamed", "notes": "Updated notes"})
    analysis = _analyze(
        _collection(found=0, parsed=0, accepted=0, search=search),
        search=search,
        baselines=_stable_baselines(),
    )
    assert analysis.blocking


def test_partial_and_failed_searches_do_not_create_baselines_or_fake_zero_metrics() -> None:
    baseline = _stable_baselines()
    failed = _collection(failed=True)
    analysis = _analyze(failed, baselines=baseline)
    assert analysis.blocking
    assert analysis.snapshot_json is None
    assert _codes(analysis) == {"collection_failed", "search_failed"}
    metrics = cast(dict[str, object], analysis.report["metrics"])
    searches = cast(dict[str, object], metrics["searches"])
    assert searches[_search().slug] == {
        "status": "failed",
        "error_code": failed.outcomes[0].error_code,
        "http_status": None,
    }

    other = _search().model_copy(update={"slug": "other-search"})
    healthy = replace(
        _collection(),
        successful_searches=2,
        found=40,
        accepted=20,
        excluded=20,
        outcomes=(*_collection().outcomes, *_collection(search=other).outcomes),
    )
    full_snapshot = analyze_collection_quality(
        healthy,
        open_jobs=_open_jobs(),
        previous_snapshots=(),
        configured_searches=[_search(), other],
        generated_at=datetime(2026, 7, 19, tzinfo=UTC),
    ).snapshot_json
    assert full_snapshot is not None
    # A selected search or a failed sibling must not compare its parser sample
    # or volume with a complete registry population, even with matching history.
    for sibling in ((), _collection(search=other, failed=True).outcomes):
        partial = replace(
            _collection(found=0, complete_parser_fields=False),
            status=RunStatus.PARTIAL if sibling else RunStatus.SUCCESS,
            failed_searches=int(bool(sibling)),
            outcomes=(*_collection(found=0, complete_parser_fields=False).outcomes, *sibling),
        )
        analysis = analyze_collection_quality(
            partial,
            open_jobs=_open_jobs(),
            previous_snapshots=(full_snapshot,) * 3,
            configured_searches=[_search(), other],
            generated_at=datetime(2026, 7, 20, tzinfo=UTC),
        )
        assert not analysis.blocking
        assert analysis.snapshot_json is None
        assert not {"parser_field_missing_rate_high", "collected_volume_drop"} & _codes(analysis)


def test_changed_registry_does_not_compare_incompatible_profiles() -> None:
    search = _search().model_copy(update={"location": "Germany"})
    analysis = _analyze(
        _collection(search=search, complete_parser_fields=False),
        search=search,
        jobs=_open_jobs(country="Berlin, Germany"),
        baselines=_stable_baselines(),
    )
    assert analysis.report["checks"] == []


@pytest.mark.parametrize("days", [-31, -30, 1])
def test_only_recent_nonfuture_baselines_can_block(days: int) -> None:
    snapshot = _analyze(_collection(), days=days).snapshot_json
    assert snapshot is not None
    analysis = _analyze(_collection(found=0, parsed=0, accepted=0), baselines=(snapshot,) * 3)
    assert analysis.blocking == (days == -30)
    assert ("baseline_snapshot_invalid" in _codes(analysis)) == (days > 0)


@pytest.mark.parametrize(
    "update",
    [
        {"schema_version": True},
        {"schema_version": 1.0},
        {"schema_version": 2},
        {"captured_at": "2026-07-19T00:00:00"},
        {"open_job_count": -1},
        {"category_counts": {"private-must-not-leak": 10}},
        {"country_counts": {"private-must-not-leak": 10}},
        {"country_counts": {"GB": 11}},
        {"category_counts": {}},
        {"field_missing_counts": {"industries": 11, "start_date": 0}},
        {"parser_missing_counts": {"description": 21}},
        {"parser_candidate_count": 21},
        {"search_fingerprints": {}},
        {"searches": {}},
        {
            "searches": {
                "software-internships": {
                    "found_count": 20,
                    "accepted_count": 21,
                    "classified_count": 20,
                }
            }
        },
        {"private-must-not-leak": "raw content"},
    ],
)
def test_invalid_baselines_cannot_influence_or_leak_into_reports(update: dict[str, object]) -> None:
    payload = json.loads(_stable_baselines()[0])
    payload.update(update)
    raw = json.dumps(payload)
    with pytest.raises(ValidationError):
        DataQualitySnapshot.from_json(raw)
    analysis = _analyze(_collection(), baselines=(raw,))
    assert _codes(analysis) == {"baseline_snapshot_invalid"}
    assert "must-not-leak" not in json.dumps(analysis.report)


@pytest.mark.parametrize(
    "payload",
    ["[" * 300, " " * 131_073, "null", "[]"],
    ids=["deeply-nested", "oversized", "null", "array"],
)
def test_baseline_parsing_is_bounded(payload: str) -> None:
    assert _codes(_analyze(_collection(), baselines=(payload,))) == {"baseline_snapshot_invalid"}


def test_report_and_snapshot_are_deterministic_and_history_is_bounded() -> None:
    baselines = _stable_baselines()
    first = _analyze(_collection(), baselines=baselines)
    second = _analyze(_collection(), jobs=list(reversed(_open_jobs())), baselines=baselines)
    assert first == second
    # Only the latest five payloads may be inspected, even if a caller supplies more.
    assert (
        _analyze(_collection(), baselines=(*baselines, *baselines, "invalid")).report["checks"]
        == []
    )
