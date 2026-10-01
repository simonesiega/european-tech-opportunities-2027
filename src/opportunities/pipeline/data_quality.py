"""Deterministic collection-level checks over bounded, aggregate-only baselines."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Literal

from opportunities.models.data_quality import (
    JOB_FIELDS,
    MAX_BASELINE_SNAPSHOTS,
    PARSER_FIELDS,
    DataQualitySnapshot,
    JobField,
    ParserField,
    SearchQualityCounts,
)
from opportunities.models.enums import OpportunityCategory
from opportunities.models.job import StoredJob
from opportunities.models.search import LinkedInSearchConfig, search_config_fingerprint
from opportunities.normalization.location import normalize_locations
from opportunities.pipeline.runner import PipelineResult
from opportunities.utils.time import ensure_utc

_MIN_BASELINES = 3
_MAX_BASELINE_AGE = timedelta(days=30)
_MIN_VOLUME = 10
_MIN_ACCEPTANCE_SAMPLE = 10
_MIN_FIELD_SAMPLE = 10
_MIN_PARSER_SAMPLE = 5
_MIN_COUNTRY_SAMPLE = 10
_MIN_CATEGORY_COUNT = 3
_WARNING_DELTA = 0.4
_BLOCKING_ACCEPTANCE_DELTA = 0.75
_HIGH_MISSING_RATE = 0.99


@dataclass(frozen=True, slots=True)
class DataQualityFinding:
    """An actionable result containing no listing or source diagnostic text."""

    code: str
    severity: Literal["warning", "blocking"]
    message: str
    context: Mapping[str, str | int | float]

    def to_payload(self) -> dict[str, object]:
        """Serialize only the approved report fields."""
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "context": dict(self.context),
        }


@dataclass(frozen=True, slots=True)
class DataQualityAnalysis:
    """A public report and an optional successful full-registry baseline."""

    report: dict[str, object]
    snapshot_json: str | None
    blocking: bool


def analyze_collection_quality(
    result: PipelineResult,
    *,
    open_jobs: list[StoredJob],
    previous_snapshots: tuple[str, ...],
    configured_searches: list[LinkedInSearchConfig],
    generated_at: datetime,
) -> DataQualityAnalysis:
    """Compare like-for-like collection observations; never mutate lifecycle state."""
    generated_at = ensure_utc(generated_at)
    snapshots, invalid_count = _parse_snapshots(previous_snapshots, generated_at)
    outcomes = sorted(result.outcomes, key=lambda outcome: outcome.search.slug)
    fingerprints = {
        search.slug: search_config_fingerprint(search)
        for search in configured_searches
        if search.enabled
    }
    complete_registry_run = (
        bool(outcomes) and {o.search.slug for o in outcomes} == fingerprints.keys()
    )
    successful = [outcome for outcome in outcomes if outcome.result is not None]
    full_success = complete_registry_run and len(successful) == len(outcomes)
    # Registry-wide comparisons need the same search population, not just matching slugs.
    matching = [snapshot for snapshot in snapshots if snapshot.search_fingerprints == fingerprints]
    findings: list[DataQualityFinding] = []
    if invalid_count:
        findings.append(
            DataQualityFinding(
                "baseline_snapshot_invalid",
                "warning",
                "Invalid stored quality baselines were ignored.",
                {"count": invalid_count},
            )
        )
    if not successful:
        findings.append(
            DataQualityFinding(
                "collection_failed",
                "blocking",
                "No selected search completed successfully.",
                {"search_count": len(outcomes)},
            )
        )

    search_metrics: dict[str, dict[str, object]] = {}
    search_counts: dict[str, SearchQualityCounts] = {}
    parser_missing: Counter[ParserField] = Counter()
    for outcome in outcomes:
        slug = outcome.search.slug
        if outcome.result is None:
            search_metrics[slug] = {"status": "failed"}
            findings.append(
                DataQualityFinding(
                    "search_failed",
                    "warning",
                    "A selected search failed; its metrics are unavailable.",
                    {"search": slug},
                )
            )
            continue
        scraped = outcome.result
        counts = SearchQualityCounts(
            found_count=scraped.search_result_count,
            accepted_count=outcome.accepted_count,
            classified_count=len(scraped.positions),
        )
        search_counts[slug] = counts
        missing: Counter[ParserField] = Counter(
            field
            for position in scraped.positions
            for field in PARSER_FIELDS
            if not getattr(position, field)
        )
        parser_missing.update(missing)
        fingerprint = search_config_fingerprint(outcome.search)
        baseline = [
            snapshot.searches[slug]
            for snapshot in snapshots
            if snapshot.search_fingerprints.get(slug) == fingerprint
        ]
        search_metrics[slug] = {
            "status": "success",
            **counts.model_dump(),
            "excluded_count": outcome.excluded_count,
            "warning_count": len(scraped.warnings),
            "acceptance_rate": _rate(counts.accepted_count, counts.classified_count),
            "parser_field_missing_rates": _rates(missing, counts.classified_count, PARSER_FIELDS),
            "baseline_snapshots": len(baseline),
        }
        _check_search(slug, counts, baseline, findings)
        # Scraper warnings also include unavailable details, not only malformed HTML.
        warning_count = len(scraped.warnings)
        sample = max(counts.found_count, counts.classified_count, warning_count, 1)
        if warning_count >= 3 and warning_count / sample >= 0.25:
            findings.append(
                DataQualityFinding(
                    "scraper_warning_rate_high",
                    "warning",
                    "Scraper warnings affect a substantial share of this search.",
                    {
                        "search": slug,
                        "warning_count": warning_count,
                        "warning_rate": round(warning_count / sample, 4),
                    },
                )
            )

    total_found = sum(count.found_count for count in search_counts.values())
    total_accepted = sum(count.accepted_count for count in search_counts.values())
    total_classified = sum(count.classified_count for count in search_counts.values())
    if full_success and len(matching) >= _MIN_BASELINES:
        baseline_found = median(
            sum(row.found_count for row in snapshot.searches.values()) for snapshot in matching
        )
        if baseline_found >= _MIN_VOLUME and total_found <= baseline_found * 0.2:
            findings.append(
                DataQualityFinding(
                    "collected_volume_drop",
                    "warning",
                    "Candidate volume fell by at least 80% from its matching registry baseline.",
                    {"current_candidates": total_found, "baseline_candidates": baseline_found},
                )
            )
            if total_found == 0:
                findings.append(
                    DataQualityFinding(
                        "all_searches_returned_zero_candidates",
                        "blocking",
                        "Every enabled search returned zero candidates despite productive history.",
                        {"baseline_found": baseline_found},
                    )
                )

    field_missing, categories, countries = _job_profile(open_jobs)
    _check_dataset_profile(categories, countries, matching, findings)
    _check_missing_fields(
        "optional",
        field_missing,
        len(open_jobs),
        [(snapshot.field_missing_counts, snapshot.open_job_count) for snapshot in matching],
        JOB_FIELDS,
        _MIN_FIELD_SAMPLE,
        findings,
    )
    # Partial/failed runs sample a different candidate population. Do not compare
    # their aggregate parser profile to a complete registry's profile.
    if full_success:
        _check_missing_fields(
            "parser",
            parser_missing,
            total_classified,
            [
                (snapshot.parser_missing_counts, snapshot.parser_candidate_count)
                for snapshot in matching
            ],
            PARSER_FIELDS,
            _MIN_PARSER_SAMPLE,
            findings,
        )

    findings.sort(
        key=lambda finding: (finding.code, json.dumps(dict(finding.context), sort_keys=True))
    )
    blocking_count = sum(finding.severity == "blocking" for finding in findings)
    warning_count = sum(finding.severity == "warning" for finding in findings)
    report: dict[str, object] = {
        "schema_version": 1,
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "scope": {
            "complete_registry_run": complete_registry_run,
            "enabled_search_count": len(fingerprints),
            "attempted_search_count": len(outcomes),
            "successful_search_count": len(successful),
        },
        "status": "failed" if blocking_count else "warning" if warning_count else "passed",
        "summary": {"blocking_failures": blocking_count, "warnings": warning_count},
        "baseline": {
            "required_snapshots": _MIN_BASELINES,
            "valid_snapshots": len(snapshots),
            "matching_registry_snapshots": len(matching),
            "status": "ready" if len(matching) >= _MIN_BASELINES else "warming_up",
            "parser_comparison_eligible": full_success,
        },
        "metrics": {
            "current": {
                "found_count": total_found,
                "accepted_count": total_accepted,
                "classified_count": total_classified,
                "acceptance_rate": _rate(total_accepted, total_classified),
                "open_job_count": len(open_jobs),
                "category_counts": dict(sorted(categories.items())),
                "country_counts": dict(sorted(countries.items())),
                "optional_field_missing_rates": _rates(field_missing, len(open_jobs), JOB_FIELDS),
                "parser_candidate_count": total_classified,
                "parser_field_missing_rates": _rates(
                    parser_missing, total_classified, PARSER_FIELDS
                ),
            },
            "searches": search_metrics,
        },
        "checks": [finding.to_payload() for finding in findings],
    }
    snapshot_json = None
    # A failed or blocked run must not become the baseline that normalizes its own drift.
    if full_success and not blocking_count:
        snapshot = DataQualitySnapshot(
            schema_version=1,
            captured_at=generated_at,
            search_fingerprints=fingerprints,
            searches=search_counts,
            open_job_count=len(open_jobs),
            category_counts=dict(categories),
            country_counts=dict(countries),
            field_missing_counts={field: field_missing[field] for field in JOB_FIELDS},
            parser_candidate_count=total_classified,
            parser_missing_counts={field: parser_missing[field] for field in PARSER_FIELDS},
        )
        snapshot_json = json.dumps(
            snapshot.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
    return DataQualityAnalysis(report, snapshot_json, bool(blocking_count))


def _check_search(
    slug: str,
    current: SearchQualityCounts,
    baseline: list[SearchQualityCounts],
    findings: list[DataQualityFinding],
) -> None:
    """Use only matching configurations and sufficiently sampled acceptance rates."""
    if len(baseline) < _MIN_BASELINES:
        return
    baseline_found = median(row.found_count for row in baseline)
    if current.found_count == 0 and baseline_found > 0:
        findings.append(
            DataQualityFinding(
                "search_returned_zero_candidates",
                "warning",
                "A previously productive search returned no candidates.",
                {"search": slug, "baseline_found": baseline_found},
            )
        )
    rates = [
        row.accepted_count / row.classified_count
        for row in baseline
        if row.classified_count >= _MIN_ACCEPTANCE_SAMPLE
    ]
    if current.classified_count < _MIN_ACCEPTANCE_SAMPLE or len(rates) < _MIN_BASELINES:
        return
    current_rate = current.accepted_count / current.classified_count
    baseline_rate = median(rates)
    # Round only the delta (not its operands), avoiding binary rounding at exact thresholds.
    change = round(abs(current_rate - baseline_rate), 10)
    if change >= _WARNING_DELTA:
        findings.append(
            DataQualityFinding(
                "acceptance_rate_drift",
                "blocking" if change >= _BLOCKING_ACCEPTANCE_DELTA else "warning",
                "A search acceptance rate changed sharply from its matching baseline.",
                {
                    "search": slug,
                    "current_rate": round(current_rate, 4),
                    "baseline_rate": round(baseline_rate, 4),
                    "absolute_change": round(change, 4),
                },
            )
        )


def _check_dataset_profile(
    categories: Counter[OpportunityCategory],
    countries: Counter[str],
    snapshots: list[DataQualitySnapshot],
    findings: list[DataQualityFinding],
) -> None:
    """Warn on established category loss and substantial open-listing country shifts."""
    if len(snapshots) < _MIN_BASELINES:
        return
    for category in OpportunityCategory:
        baseline_count = median(snapshot.category_counts.get(category, 0) for snapshot in snapshots)
        if baseline_count >= _MIN_CATEGORY_COUNT and not categories[category]:
            findings.append(
                DataQualityFinding(
                    "category_disappeared",
                    "warning",
                    "A previously established opportunity category has no open listings.",
                    {"category": category.value, "baseline_count": baseline_count},
                )
            )
    # Require substantial historical samples, not several pooled tiny profiles.
    profiles = [
        snapshot.country_counts
        for snapshot in snapshots
        if sum(snapshot.country_counts.values()) >= _MIN_COUNTRY_SAMPLE
    ]
    if len(profiles) < _MIN_BASELINES:
        return
    baseline_countries: Counter[str] = Counter()
    for profile in profiles:
        baseline_countries.update(profile)
    current_total, baseline_total = sum(countries.values()), sum(baseline_countries.values())
    if current_total < _MIN_COUNTRY_SAMPLE:
        findings.append(
            DataQualityFinding(
                "country_distribution_unavailable",
                "warning",
                "Too few recognized countries remain to compare the open-listing distribution.",
                {"country_observations": current_total},
            )
        )
        return
    distance = 0.5 * sum(
        abs(countries[country] / current_total - baseline_countries[country] / baseline_total)
        for country in sorted(countries.keys() | baseline_countries.keys())
    )
    if round(distance, 10) >= 0.5:
        findings.append(
            DataQualityFinding(
                "country_distribution_shift",
                "warning",
                "The open-listing country distribution moved substantially from baseline.",
                {"total_variation_distance": round(distance, 4)},
            )
        )


def _check_missing_fields[FieldName: str](
    kind: Literal["optional", "parser"],
    current: Mapping[FieldName, int],
    sample: int,
    previous: Sequence[tuple[Mapping[FieldName, int], int]],
    fields: tuple[FieldName, ...],
    minimum_sample: int,
    findings: list[DataQualityFinding],
) -> None:
    """Optional fields may legitimately be absent; alert only on well-sampled changes."""
    previous = [(counts, count) for counts, count in previous if count >= minimum_sample]
    if sample < minimum_sample or len(previous) < _MIN_BASELINES:
        return
    for field in fields:
        current_rate = current.get(field, 0) / sample
        baseline_rate = median(counts.get(field, 0) / count for counts, count in previous)
        if current_rate >= _HIGH_MISSING_RATE and baseline_rate < _HIGH_MISSING_RATE:
            code = f"{kind}_field_missing_rate_high"
        elif round(current_rate - baseline_rate, 10) >= _WARNING_DELTA:
            code = f"{kind}_field_missing_rate_drift"
        else:
            continue
        findings.append(
            DataQualityFinding(
                code,
                "warning",
                "A field's missing rate increased from its matching baseline.",
                {
                    "field": field,
                    "current_rate": round(current_rate, 4),
                    "baseline_rate": round(baseline_rate, 4),
                    "sample_size": sample,
                },
            )
        )


def _job_profile(
    jobs: list[StoredJob],
) -> tuple[Counter[JobField], Counter[OpportunityCategory], Counter[str]]:
    """Use canonical normalization without copying listing text into the report."""
    missing: Counter[JobField] = Counter()
    categories: Counter[OpportunityCategory] = Counter()
    countries: Counter[str] = Counter()
    for job in jobs:
        categories[job.category] += 1
        countries.update(normalize_locations([job.location]).country_codes)
        missing.update(field for field in JOB_FIELDS if not getattr(job, field))
    return missing, categories, countries


def _parse_snapshots(
    raw_snapshots: tuple[str, ...],
    generated_at: datetime,
) -> tuple[list[DataQualitySnapshot], int]:
    """Ignore damaged, future, and expired history without echoing stored values."""
    snapshots: list[DataQualitySnapshot] = []
    invalid = 0
    for raw in raw_snapshots[:MAX_BASELINE_SNAPSHOTS]:
        try:
            snapshot = DataQualitySnapshot.from_json(raw)
            if snapshot.captured_at > generated_at:
                raise ValueError("quality baseline is in the future")
        except ValueError:
            invalid += 1
            continue
        if generated_at - snapshot.captured_at <= _MAX_BASELINE_AGE:
            snapshots.append(snapshot)
    return snapshots, invalid


def _rates[FieldName: str](
    counts: Mapping[FieldName, int],
    denominator: int,
    fields: tuple[FieldName, ...],
) -> dict[str, float | None]:
    return {field: _rate(counts.get(field, 0), denominator) for field in fields}


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None
