"""Offline scout contracts: complete public reads, evidence, reports, and approval boundaries."""

from __future__ import annotations

import hashlib
import html
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import httpx
import pytest
import yaml
from scripts.research import scout as command

from opportunities.config.rules import ClassificationRules
from opportunities.manual_jobs import load_manual_batch, parse_manual_batch
from opportunities.normalization.location import normalize_locations
from opportunities.normalization.title import normalize_title
from opportunities.pipeline.classification import Classifier
from opportunities.scout import (
    REPORT_COLUMNS,
    AvailabilityEvidence,
    Candidate,
    Research,
    assess,
    availability_from_public_html,
    prepare_batches,
    render_report,
)
from opportunities.scout_dataset import PublicDataset, load_public_dataset, validate_contract
from opportunities.scrapers.linkedin import (
    LinkedInPayloadError,
    has_closed_application_notice,
    parse_job_detail,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 20, 12, tzinfo=UTC)
STAMP = "2026-10-20T12:00:00.000000+00:00"


def row(index: int) -> dict[str, object]:
    job_id = str(1000000000 + index)
    return {
        "linkedinJobId": job_id,
        "company": "Example Labs",
        "title": "Firmware Intern 2027",
        "location": "Berlin, Germany",
        "link": f"https://www.linkedin.com/jobs/view/{job_id}",
        "category": "embedded-systems",
        "industries": None,
        "employmentType": "internship",
        "startDate": None,
        "firstSeenAt": STAMP,
    }


def export_bytes(indices: range | list[int]) -> bytes:
    names = {
        "linkedinJobId": "linkedin_job_id",
        "employmentType": "employment_type",
        "startDate": "start_date",
    }
    rows = [
        {names.get(key, key): value for key, value in row(index).items() if key != "firstSeenAt"}
        for index in indices
    ]
    return (json.dumps(rows) + "\n").encode()


def status(count: int | float, **updates: object) -> dict[str, object]:
    return {
        "last_successful_collection": None,
        "dataset_generated_at": STAMP,
        "opportunities": count,
        "dataset_sha256": "a" * 64,
        "release": "123-1",
        **updates,
    }


def dataset(*ids: str) -> PublicDataset:
    return PublicDataset(
        status=status(len(ids)), ids=frozenset(ids), retrieved_at=NOW, method="api"
    )


def candidate(index: int = 1, /, **updates: object) -> Candidate:
    public = row(index)
    raw = {
        "source_job_id": public["linkedinJobId"],
        "company": "Example Labs",
        "title": public["title"],
        "locations": [public["location"]],
        "application_url": public["link"],
    }
    raw.update(cast(dict[str, object], updates.pop("raw", {})))
    return Candidate.model_validate(
        {
            "url": public["link"],
            "listing": raw,
            "directly_verified": True,
            "availability": {
                "basis": "accepting_applications",
                "evidence": f"Explicit current LinkedIn status: accepting applications; {STAMP}",
            },
            "location_cycle_evidence": "Berlin, Germany; title cycle 2027",
            "supporting_evidence": f"LinkedIn details {public['link']}; observed {STAMP}",
            **updates,
        }
    )


def test_public_contract_is_available_in_the_installed_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "site-packages/opportunities"
    schema = package / "resources/schemas/opportunities-v1.schema.json"
    schema.parent.mkdir(parents=True)
    schema.write_bytes((ROOT / "schemas/opportunities-v1.schema.json").read_bytes())
    monkeypatch.setattr("opportunities.scout_dataset.__file__", str(package / "scout_dataset.py"))
    validate_contract(status(0), "statusSuccess")
    with pytest.raises(ValueError, match="contract"):
        validate_contract({"private": "not a public status"}, "statusSuccess")


@pytest.mark.parametrize("total", [0, 1, 100, 101, 215])
def test_public_reader_loads_every_page_and_valid_empty_dataset(total: int) -> None:
    requests: list[str] = []
    content = export_bytes(range(total))
    snapshot = status(float(total), dataset_sha256=hashlib.sha256(content).hexdigest())

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        assert request.url.host == "techopportunities.eu"
        assert "cookie" not in request.headers
        assert "authorization" not in request.headers
        if request.url.path.endswith("status"):
            return httpx.Response(200, json=snapshot)
        if request.url.path.endswith(".json"):
            return httpx.Response(
                200, content=content, headers={"content-type": "application/json"}
            )
        page = int(request.url.params["page"])
        assert dict(request.url.params) == {
            "page": str(page),
            "page-size": "100",
            "sort": "first-seen-desc",
        }
        return httpx.Response(
            200,
            json={
                "version": "v1",
                "pagination": {
                    "page": page,
                    "pageSize": 100,
                    "total": total,
                    "totalPages": (total + 99) // 100,
                },
                "data": [row(i) for i in range((page - 1) * 100, min(page * 100, total))],
            },
            headers={"set-cookie": "untrusted=value"},
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = load_public_dataset(client)
    assert result.ids == frozenset(str(1000000000 + i) for i in range(total))
    assert len(requests) == max((total + 99) // 100, 1) + 3
    assert result.method == "api"
    assert result.status == snapshot


@pytest.mark.parametrize(
    "defect",
    [
        "short",
        "duplicate",
        "total",
        "page",
        "pageSize",
        "totalPages",
        "identity",
        "schema",
        "drift",
        "export-mismatch",
        "http",
        "redirect",
        "invalid-json",
        "compressed",
        "content-type",
        "oversize",
        "legacy",
        "budget",
    ],
)
def test_public_reader_never_returns_partial_or_inconsistent_data(defect: str) -> None:
    calls = 0
    content = export_bytes([1, 3] if defect == "export-mismatch" else [1, 2])

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.url.path.endswith("status"):
            return httpx.Response(
                200,
                json=status(
                    2,
                    dataset_sha256=hashlib.sha256(content).hexdigest(),
                    **(
                        {"release": None}
                        if defect == "legacy"
                        else {"opportunities": 10001}
                        if defect == "budget"
                        else {"release": "124-1"}
                        if defect == "drift" and calls > 1
                        else {}
                    ),
                ),
            )
        if request.url.path.endswith(".json"):
            return httpx.Response(
                200, content=content, headers={"content-type": "application/json"}
            )
        if defect in {"http", "redirect"}:
            return httpx.Response(
                503 if defect == "http" else 302, headers={"location": "https://example.com"}
            )
        if defect in {"invalid-json", "compressed", "content-type", "oversize"}:
            headers = {
                "content-type": "text/html" if defect == "content-type" else "application/json"
            }
            if defect == "compressed":
                headers["content-encoding"] = "br"
            return httpx.Response(
                200,
                content=b"x" * (1024 * 1024 + 1) if defect == "oversize" else b"not-json",
                headers=headers,
            )
        rows = [row(1), row(2)]
        pagination = {"page": 1, "pageSize": 100, "total": 2, "totalPages": 1}
        if defect == "short":
            rows.pop()
        elif defect == "duplicate":
            rows[1] = row(1)
        elif defect in pagination:
            pagination[defect] += 1
        elif defect == "identity":
            rows[0]["link"] = row(2)["link"]
        elif defect == "schema":
            rows[0]["private"] = "not allowed"
        return httpx.Response(200, json={"version": "v1", "pagination": pagination, "data": rows})

    with (
        httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=True) as client,
        pytest.raises(ValueError, match=r"public|fixed-path|duplicate|identity"),
    ):
        load_public_dataset(client)
    assert calls <= 4


@pytest.mark.parametrize("defect", [None, "hash", "count", "duplicate", "schema", "drift"])
def test_public_export_fallback_checks_exact_bytes_and_status(defect: str | None) -> None:
    rows = [
        {
            "linkedin_job_id": "1000000001",
            "company": "Example Labs",
            "title": "Firmware Intern 2027",
            "location": "Berlin, Germany",
            "link": "https://www.linkedin.com/jobs/view/1000000001",
            "category": "embedded-systems",
            "industries": None,
            "employment_type": "internship",
            "start_date": None,
        }
    ]
    if defect == "duplicate":
        rows *= 2
    elif defect == "schema":
        rows[0].pop("title")
    content = (json.dumps(rows) + "\n").encode()
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if request.url.path.endswith("status"):
            return httpx.Response(
                200,
                json=status(
                    2 if defect == "count" else len(rows),
                    release=None,
                    dataset_sha256="a" * 64
                    if defect == "hash"
                    else hashlib.sha256(content).hexdigest(),
                    **(
                        {"dataset_generated_at": "2026-10-21T12:00:00.000000+00:00"}
                        if defect == "drift" and calls > 1
                        else {}
                    ),
                ),
            )
        assert request.url.path == "/open-opportunities.json"
        return httpx.Response(200, content=content, headers={"content-type": "application/json"})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        if defect:
            with pytest.raises(ValueError, match=r"public|duplicate"):
                load_public_dataset(client, use_export=True)
        else:
            result = load_public_dataset(client, use_export=True)
            assert result.ids == {"1000000001"}
            assert result.method == "export"


def test_public_reader_rejects_authentication_before_requests() -> None:
    with (
        httpx.Client(headers={"Authorization": "synthetic"}) as client,
        pytest.raises(ValueError, match="unauthenticated"),
    ):
        load_public_dataset(client)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({"title": "Software Intern", "description": "Applicants graduating in 2027"}, "rejected"),
        ({"title": "Software Intern", "posted_at": "2026-05-01T00:00:00Z"}, "confirmed"),
        ({"title": "Software Intern", "posted_at": "2026-04-30T23:59:59Z"}, "rejected"),
        ({"title": "Software Intern 2026", "posted_at": "2026-10-01T00:00:00Z"}, "rejected"),
        ({"title": "Senior Software Graduate 2027"}, "rejected"),
        ({"locations": ["EMEA"]}, "rejected"),
        ({"locations": ["London, South Africa"]}, "rejected"),
        ({"locations": ["x" * 480 + ", Germany", "y" * 480 + ", France"]}, "rejected"),
        ({"title": "Software New Grad 2027"}, "confirmed"),
        ({"posted_at": "2026-10-21T00:00:00Z"}, "conditional"),
    ],
)
def test_scout_calls_current_classifier_without_weakening_evidence(
    rules: ClassificationRules, raw: dict[str, object], expected: str
) -> None:
    research = Research(executed_at=NOW, strategies=[], candidates=[candidate(raw=raw)])
    finding = assess(research, dataset(), Classifier(rules, 2027))[0]
    assert finding.status == expected
    if expected != "confirmed":
        assert finding.manual_record is None


@pytest.mark.parametrize(
    "evidence",
    [
        {"directly_verified": False},
        {"uncertainties": ["Missing details"]},
        {"supporting_evidence": ""},
        {"supporting_evidence": "&nbsp;"},
        {"location_cycle_evidence": ""},
        {"location_cycle_evidence": "&#32;"},
        {"listing": None},
    ],
)
def test_missing_evidence_stays_conditional(
    rules: ClassificationRules, evidence: dict[str, object]
) -> None:
    research = Research(executed_at=NOW, strategies=[], candidates=[candidate(**evidence)])
    assert assess(research, dataset(), Classifier(rules, 2027))[0].status == "conditional"
    assert assess(research, None, Classifier(rules, 2027))[0].manual_record is None


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/jobs/view/1000000001",
        "http://www.linkedin.com/jobs/view/1000000001",
        "https://www.linkedin.com/jobs/view/title-1000000001",
        "https://www.linkedin.com/jobs/view/1000000002",
    ],
)
def test_candidate_identity_uses_repository_url_contract(url: str) -> None:
    with pytest.raises(ValueError, match=r"LinkedIn|HTTPS|identity"):
        candidate(url=url)


@pytest.mark.parametrize("value", ["true", "false", "yes", 1, 0, None])
def test_direct_verification_requires_an_explicit_boolean(value: object) -> None:
    with pytest.raises(ValueError, match="directly_verified"):
        candidate(directly_verified=value)


def test_naive_posting_evidence_and_conflicting_identity_are_not_repaired() -> None:
    with pytest.raises(ValueError, match="timezone"):
        candidate(raw={"posted_at": "2026-10-01T00:00:00"})
    with pytest.raises(ValueError, match="identity"):
        candidate(raw={"application_url": "https://www.linkedin.com/jobs/view/999"})


@pytest.mark.parametrize(
    ("basis", "evidence", "verified", "expected"),
    [
        ("accepting_applications", "Explicit current acceptance status", True, "confirmed"),
        ("closure_alert", "No longer accepting applications", True, "rejected"),
        ("http_404", "Approved numeric listing returned HTTP 404", True, "rejected"),
        ("http_410", "Approved numeric listing returned HTTP 410", True, "rejected"),
        ("unknown", "No closure warning; Apply button visible", True, "conditional"),
        ("accepting_applications", "  ", True, "conditional"),
        ("accepting_applications", "&nbsp;", True, "conditional"),
        ("accepting_applications", "Search snippet says open", False, "conditional"),
        ("closure_alert", "Unverified snippet says closed", False, "conditional"),
    ],
)
def test_availability_requires_verified_positive_evidence(
    rules: ClassificationRules, basis: str, evidence: str, verified: bool, expected: str
) -> None:
    research = Research(
        executed_at=NOW,
        strategies=[],
        candidates=[
            candidate(
                directly_verified=verified, availability={"basis": basis, "evidence": evidence}
            )
        ],
    )
    classifier = Classifier(rules, 2027)
    finding = assess(research, dataset(), classifier)[0]
    assert finding.status == expected
    batches, skipped = prepare_batches(
        research, dataset(), [finding.job_id], classifier=classifier, observed_at=NOW
    )
    assert bool(batches) == (expected == "confirmed")
    assert bool(skipped) == (expected != "confirmed")
    report = render_report(research, dataset(), [finding])
    assert f"Availability: {finding.candidate.availability_state}" in report
    assert basis in html.unescape(report)
    if evidence.strip():
        assert evidence in html.unescape(report)


def test_scoped_closure_alert_cannot_reach_a_manual_batch(rules: ClassificationRules) -> None:
    source = (
        '<h1 class="top-card-layout__title">Software Intern 2027</h1>'
        '<a class="topcard__org-name-link">Example Labs</a>'
        '<div class="show-more-less-html__markup">Software internship for 2027.</div>'
        '<div role="alert">No longer accepting applications</div>'
    )
    assert has_closed_application_notice(source)
    raw = parse_job_detail(
        source, job_id="1000000001", fallback_location="Berlin, Germany", observed_at=NOW
    )
    classifier = Classifier(rules, 2027)
    for availability, expected in (
        (AvailabilityEvidence(), "conditional"),
        (availability_from_public_html(source), "rejected"),
    ):
        research = Research(
            executed_at=NOW,
            strategies=[],
            candidates=[
                candidate(
                    listing=raw,
                    availability=availability,
                    supporting_evidence="Public listing: No longer accepting applications",
                )
            ],
        )
        finding = assess(research, dataset(), classifier)[0]
        assert finding.status == expected
        assert finding.manual_record is None
        assert not prepare_batches(
            research, dataset(), [finding.job_id], classifier=classifier, observed_at=NOW
        )[0]
    # Explicit absence is still usable when no title/company could be parsed.
    closed = candidate(listing=None, availability={"basis": "http_404", "evidence": "HTTP 404"})
    assert (
        assess(Research(executed_at=NOW, strategies=[], candidates=[closed]), None, classifier)[
            0
        ].status
        == "rejected"
    )


@pytest.mark.parametrize(
    "source",
    [
        "<h1>Software Intern 2027</h1>",
        "<button>Apply</button>",
        "<p>We are accepting applications</p>",
        "<p>No longer accepting applications</p>",
    ],
)
def test_html_inspection_never_invents_open_status(source: str) -> None:
    assert availability_from_public_html(source).state == "unknown"


def test_html_inspection_propagates_existing_source_challenges() -> None:
    with pytest.raises(LinkedInPayloadError, match="verification"):
        availability_from_public_html("<html>Security verification challenge-page</html>")


@pytest.mark.parametrize(
    "case",
    [
        "identical",
        "complementary",
        "snippet",
        "normalization",
        "whitespace",
        "ligature",
        "contradictory-snippet",
    ],
)
def test_reconciliation_uses_verified_complementary_facts_in_either_order(
    rules: ClassificationRules, case: str
) -> None:
    detail = candidate(
        raw={"industries": "Semiconductors", "description": "Firmware placement for 2027"}
    )
    other = {
        "identical": detail,
        "complementary": candidate(
            raw={"locations": [], "industries": None, "description": "  "},
            availability={},
            location_cycle_evidence="",
        ),
        "snippet": candidate(
            directly_verified=False,
            raw={
                "title": "Senior Software Engineer 2026",
                "company": "Snippet employer",
                "locations": ["Austin, United States"],
            },
            availability={"basis": "closure_alert", "evidence": "Unverified closure snippet"},
            uncertainties=["Snippet only"],
            supporting_evidence="Search index reference",
        ),
        "whitespace": candidate(
            raw={
                "company": "  Example\tLabs  ",
                "title": "Firmware  Intern\t2027",
                "locations": ["  Berlin,   Germany "],
                "description": "Firmware  placement\nfor 2027",
            }
        ),
        "ligature": candidate(raw={"title": "ﬁrmware Intern 2027"}),
        "contradictory-snippet": candidate(
            directly_verified=False,
            availability={
                "basis": "accepting_applications",
                "evidence": "No longer accepting applications",
            },
            supporting_evidence="Unverified index excerpt only",
        ),
        "normalization": candidate(
            raw={
                "title": "FIRMWARE INTERN 2027",
                "company": "EXAMPLE LABS",
                "industries": "Semiconductors",
            }
        ),
    }[case]
    classifier = Classifier(rules, 2027)
    reports: list[str] = []
    records: list[bytes] = []
    for observations in ([other, detail], [detail, other]):
        research = Research(executed_at=NOW, strategies=[], candidates=observations)
        findings = assess(research, dataset(), classifier)
        assert [item.status for item in findings] == ["confirmed", "duplicate"]
        assert len(findings[0].observations) == 2
        batches, skipped = prepare_batches(
            research, dataset(), ["1000000001"], classifier=classifier, observed_at=NOW
        )
        assert not skipped
        assert len(batches) == 1
        jobs = parse_manual_batch(batches[0], classifier=classifier, observed_at=NOW)
        assert len(jobs) == 1
        assert jobs[0].industries == "Semiconductors"
        assert jobs[0].location == "Berlin, Germany"
        records.append(batches[0])
        reports.append(render_report(research, dataset(), findings))
    assert records[0] == records[1]
    assert reports[0] == reports[1]
    if case == "snippet":
        assert "Preliminary observation" in reports[0]
        assert "Senior Software Engineer 2026" in reports[0]
        assert "Search index reference" in reports[0]


@pytest.mark.parametrize(
    ("first_raw", "second_raw", "field"),
    [
        (
            {"title": "Busineß Development Software Intern 2027"},
            {"title": "Business Development Software Intern 2027"},
            "title",
        ),
        (
            {"title": "BUSINEẞ DEVELOPMENT SOFTWARE INTERN 2027"},
            {"title": "BUSINESS DEVELOPMENT SOFTWARE INTERN 2027"},
            "title",
        ),
        (
            {"title": "Research Intern 2027", "description": "Quality assurance"},
            {"title": "Research Intern 2027", "description": "Quality aßurance"},
            "description",
        ),
        ({"locations": ["Brussels"]}, {"locations": ["Brußels"]}, "locations"),
    ],
)
def test_verified_unicode_aliases_cannot_hide_policy_disagreements(
    rules: ClassificationRules,
    first_raw: dict[str, object],
    second_raw: dict[str, object],
    field: str,
) -> None:
    # Harmless employer capitalization used to select the accepted variant while
    # the old casefold-only key silently merged the differing policy interpretations.
    first = candidate(raw={"company": "EXAMPLE LABS", **first_raw})
    second = candidate(raw={"company": "Example Labs", **second_raw})
    assert first.listing is not None
    assert second.listing is not None
    classifier = Classifier(rules, 2027)
    decisions = [
        classifier.classify(
            title=normalize_title(raw.title),
            description=raw.description,
            location=normalize_locations(raw.locations),
            posted_at=raw.posted_at,
        )
        for raw in (first.listing, second.listing)
    ]
    assert decisions[0].include
    assert not decisions[1].include
    reports: list[str] = []
    for observations in ([first, second], [second, first]):
        research = Research(executed_at=NOW, strategies=[], candidates=observations)
        findings = assess(research, dataset(), classifier)
        assert findings[0].status == "conditional"
        assert f"Conflicting verified {field}" in findings[0].reason
        assert all(item.manual_record is None for item in findings)
        batches, skipped = prepare_batches(
            research, dataset(), ["1000000001"], classifier=classifier, observed_at=NOW
        )
        assert not batches
        assert f"Conflicting verified {field}" in skipped["1000000001"]
        report = render_report(research, dataset(), findings)
        for raw in (first_raw, second_raw):
            observed = raw[field]
            values = observed if isinstance(observed, list) else [observed]
            for value in values:
                assert str(value) in html.unescape(report)
        assert "Manually addable: 0; required batches: 0" in report
        assert all(
            len(line.split("|")) == 7 for line in report.splitlines() if line.startswith("|")
        )
        reports.append(report)
    assert reports[0] == reports[1]


@pytest.mark.parametrize("repeated", [False, True])
def test_reconciliation_does_not_decode_validated_source_fields_again(
    rules: ClassificationRules, repeated: bool
) -> None:
    observation = candidate(raw={"title": "Research&amp;amp;amp;VerticalBar; Engineer Intern 2027"})
    raw = observation.listing
    assert raw is not None
    original = raw.model_dump()
    classifier = Classifier(rules, 2027)
    decision = classifier.classify(
        title=normalize_title(raw.title),
        description=raw.description,
        location=normalize_locations(raw.locations),
        posted_at=raw.posted_at,
    )
    assert not decision.include
    research = Research(
        executed_at=NOW,
        strategies=[],
        candidates=[observation] * (2 if repeated else 1),
    )
    finding = assess(research, dataset(), classifier)[0]
    assert finding.status == "rejected"
    assert finding.reason == decision.exclusion_reason
    assert finding.candidate.listing is not None
    assert finding.candidate.listing.model_dump() == original
    assert observation.listing is raw
    assert raw.model_dump() == original
    assert finding.manual_record is None
    assert not prepare_batches(
        research, dataset(), [finding.job_id], classifier=classifier, observed_at=NOW
    )[0]


@pytest.mark.parametrize(
    ("first", "second", "conflict"),
    [
        (
            {"title": "Research&amp;amp;VerticalBar; Engineer Intern 2027"},
            {"title": "Research&amp;amp;verticalbar; Engineer Intern 2027"},
            "title",
        ),
        ({"locations": ["London, DE"]}, {"locations": ["London, de"]}, "eligibility"),
    ],
)
def test_reconciliation_checks_actual_normalization_pipeline_outcomes(
    rules: ClassificationRules,
    first: dict[str, object],
    second: dict[str, object],
    conflict: str,
) -> None:
    classifier = Classifier(rules, 2027)
    observations = [
        candidate(raw={"company": "EXAMPLE LABS", **first}),
        candidate(raw={"company": "Example Labs", **second}),
    ]
    # Entity decoding and case-sensitive country codes can disagree. Scalar keys
    # alone miss the latter; compare the actual classifier outcomes as well.
    singles = [
        assess(Research(executed_at=NOW, strategies=[], candidates=[item]), dataset(), classifier)[
            0
        ]
        for item in observations
    ]
    assert [item.status for item in singles] == ["confirmed", "rejected"]
    assert singles[0].manual_record is not None
    assert singles[1].manual_record is None
    for ordered in (observations, list(reversed(observations))):
        research = Research(executed_at=NOW, strategies=[], candidates=ordered)
        findings = assess(research, dataset(), classifier)
        assert findings[0].status == "conditional"
        assert f"Conflicting verified {conflict}" in findings[0].reason
        assert all(item.manual_record is None for item in findings)
        batches, skipped = prepare_batches(
            research, dataset(), ["1000000001"], classifier=classifier, observed_at=NOW
        )
        assert not batches
        assert conflict in skipped["1000000001"]
        assert f"Conflicting verified {conflict}" in render_report(research, dataset(), findings)


@pytest.mark.parametrize(
    "evidence",
    [
        "No longer accepting applications",
        'LinkedIn status: "NO LONGER ACCEPTING APPLICATIONS"; observed at source URL',
        "We are not accepting applications for this listing.",
        "We are not currently accepting applications.",
        "Approved numeric listing returned HTTP 404.",
        "HTTP 410 observed at the source URL.",
    ],
)
@pytest.mark.parametrize("with_positive_observation", [False, True])
def test_contradictory_open_attestations_stay_review_required(
    rules: ClassificationRules, evidence: str, with_positive_observation: bool
) -> None:
    contradictory = candidate(
        availability={"basis": "accepting_applications", "evidence": evidence}
    )
    observations = [contradictory, candidate()] if with_positive_observation else [contradictory]
    classifier = Classifier(rules, 2027)
    for ordered in (observations, list(reversed(observations))):
        research = Research(executed_at=NOW, strategies=[], candidates=ordered)
        findings = assess(research, dataset(), classifier)
        assert findings[0].status == "conditional"
        assert findings[0].candidate.availability_state == "unknown"
        assert "contradicts" in findings[0].reason
        assert all(item.manual_record is None for item in findings)
        batches, skipped = prepare_batches(
            research, dataset(), ["1000000001"], classifier=classifier, observed_at=NOW
        )
        assert not batches
        assert "contradicts" in skipped["1000000001"]
        assert evidence in html.unescape(render_report(research, dataset(), findings))
    # Unscoped negative words are not mechanically promoted to actual closure.
    assert contradictory.availability.state == "unknown"


@pytest.mark.parametrize(
    "changed",
    [
        {"title": "Senior Software Engineer 2026", "locations": ["Austin, United States"]},
        {"title": "Software New Grad 2027"},
        {"company": "Different employer"},
        {"locations": ["Austin, United States"]},
        {"description": "Internship for the 2026 cycle"},
        {"industries": "Finance"},
        {"start_date": "September 2027"},
        {"posted_at": "2026-10-19T12:00:00Z"},
    ],
)
def test_contradictory_verified_facts_require_review_in_either_order(
    rules: ClassificationRules, changed: dict[str, object]
) -> None:
    first = candidate(
        raw={
            "title": "Software Intern 2027",
            "description": "Internship 2027",
            "industries": "Software",
            "start_date": "June 2027",
            "posted_at": "2026-10-18T12:00:00Z",
        }
    )
    assert first.listing is not None
    later = candidate(raw={**first.listing.model_dump(mode="json"), **changed})
    classifier = Classifier(rules, 2027)
    reports: list[str] = []
    for observations in ([first, later], [later, first]):
        research = Research(executed_at=NOW, strategies=[], candidates=observations)
        findings = assess(research, dataset(), classifier)
        assert [item.status for item in findings] == ["conditional", "duplicate"]
        assert findings[0].manual_record is None
        assert "Conflicting verified" in findings[0].reason
        batches, skipped = prepare_batches(
            research, dataset(), ["1000000001"], classifier=classifier, observed_at=NOW
        )
        assert not batches
        assert "Conflicting verified" in skipped["1000000001"]
        reports.append(render_report(research, dataset(), findings))
    assert reports[0] == reports[1]
    if "Senior" in str(changed):
        assert "Software Intern 2027" in reports[0]
        assert "Senior Software Engineer 2026" in reports[0]
        assert "Austin, United States" in reports[0]


@pytest.mark.parametrize("same_title", [True, False])
def test_reconciliation_preserves_punctuation_and_ignores_location_order(
    rules: ClassificationRules, same_title: bool
) -> None:
    first = candidate(
        raw={"title": "Software C++ Intern 2027", "locations": ["Berlin, Germany", "Paris, France"]}
    )
    other = candidate(
        raw={
            "title": "Software C++ Intern 2027" if same_title else "Software C# Intern 2027",
            "locations": ["Paris, France", "Berlin, Germany"],
        }
    )
    classifier = Classifier(rules, 2027)
    results: list[tuple[list[bytes], dict[str, str]]] = []
    for observations in ([first, other], [other, first]):
        research = Research(executed_at=NOW, strategies=[], candidates=observations)
        finding = assess(research, dataset(), classifier)[0]
        assert finding.status == ("confirmed" if same_title else "conditional")
        result = prepare_batches(
            research, dataset(), [finding.job_id], classifier=classifier, observed_at=NOW
        )
        assert bool(result[0]) == same_title
        results.append(result)
    assert results[0] == results[1]


@pytest.mark.parametrize("known_basis", ["accepting_applications", "closure_alert", "unknown"])
def test_verified_unknown_availability_is_not_contradictory_evidence(
    rules: ClassificationRules, known_basis: str
) -> None:
    classifier = Classifier(rules, 2027)
    known = candidate(availability={"basis": known_basis, "evidence": "Source observation"})
    absent = candidate(availability={}, raw={"description": "  "})
    for observations in ([known, absent], [absent, known]):
        research = Research(executed_at=NOW, strategies=[], candidates=observations)
        finding = assess(research, dataset(), classifier)[0]
        assert (
            finding.status
            == {
                "accepting_applications": "confirmed",
                "closure_alert": "rejected",
                "unknown": "conditional",
            }[known_basis]
        )
        assert not finding.candidate.uncertainties
        result = prepare_batches(
            research, dataset(), [finding.job_id], classifier=classifier, observed_at=NOW
        )
        assert bool(result[0]) == (known_basis == "accepting_applications")


@pytest.mark.parametrize("basis", ["closure_alert", "http_404", "http_410"])
def test_conflicting_verified_availability_blocks_confirmation_and_batching(
    rules: ClassificationRules, basis: str
) -> None:
    classifier = Classifier(rules, 2027)
    opened = candidate()
    closed = candidate(availability={"basis": basis, "evidence": "Explicit closure observation"})
    for observations in ([opened, closed], [closed, opened]):
        research = Research(executed_at=NOW, strategies=[], candidates=observations)
        findings = assess(research, dataset(), classifier)
        assert findings[0].status == "conditional"
        assert findings[0].candidate.availability_state == "unknown"
        assert "Conflicting verified availability" in findings[0].reason
        assert not prepare_batches(
            research, dataset(), ["1000000001"], classifier=classifier, observed_at=NOW
        )[0]
        report = render_report(research, dataset(), findings)
        assert "availability: open" in report
        assert "availability: closed" in report
        assert "Explicit closure observation" in report


def test_missing_verified_facts_and_unresolved_uncertainty_cannot_borrow_snippets(
    rules: ClassificationRules,
) -> None:
    classifier = Classifier(rules, 2027)
    for verified in (
        candidate(listing=None),
        candidate(supporting_evidence=""),
        candidate(uncertainties=["Unresolved source contradiction"]),
    ):
        research = Research(
            executed_at=NOW,
            strategies=[],
            candidates=[candidate(directly_verified=False), verified],
        )
        assert assess(research, dataset(), classifier)[0].status == "conditional"
        assert not prepare_batches(
            research, dataset(), ["1000000001"], classifier=classifier, observed_at=NOW
        )[0]


@pytest.mark.parametrize("defect", ["closed", "unknown", "facts", "availability"])
def test_batch_cli_reassesses_ledger_not_a_forged_report(
    tmp_path: Path, rules: ClassificationRules, defect: str, capsys: pytest.CaptureFixture[str]
) -> None:
    observations = [candidate()]
    if defect == "unknown":
        observations = [candidate(availability={})]
    elif defect == "closed":
        observations = [candidate(availability={"basis": "closure_alert", "evidence": "Closed"})]
    elif defect == "facts":
        observations.append(
            candidate(
                raw={
                    "title": "Senior Software Engineer 2026",
                    "locations": ["Austin, United States"],
                }
            )
        )
    else:
        observations.append(candidate(availability={"basis": "http_410", "evidence": "HTTP 410"}))
    research = Research(executed_at=NOW, strategies=[], candidates=observations)
    (tmp_path / "research.json").write_text(research.model_dump_json(), encoding="utf-8")
    (tmp_path / "dataset.json").write_text(dataset().model_dump_json(), encoding="utf-8")
    (tmp_path / "report.md").write_text(
        "Confirmed; availability open; no conflicts", encoding="utf-8"
    )
    assert (
        command.main(["batches", "--directory", str(tmp_path), "--approved-ids", "1000000001"]) == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["batches"] == 0
    assert "1000000001" in result["skipped"]
    assert not list(tmp_path.glob("batch-*.json"))
    # A separately attested ledger can contain corrected facts without rewriting
    # the old one. This does not authenticate a source recheck or prove freshness.
    fresh = Research(
        executed_at=NOW,
        strategies=[],
        candidates=[candidate()],
        limitations=[
            "Synthetic separate attestation; original ledger retained; freshness not proven"
        ],
    )
    batches, skipped = prepare_batches(
        fresh, dataset(), ["1000000001"], classifier=Classifier(rules, 2027), observed_at=NOW
    )
    assert not skipped
    assert len(json.loads(batches[0])) == 1
    assert (tmp_path / "research.json").read_text(encoding="utf-8") == research.model_dump_json()


@pytest.mark.parametrize("count", [0, 1, 10, 11, 21, 23, 25])
def test_approved_batches_match_real_manual_schema_at_boundaries(
    rules: ClassificationRules, count: int
) -> None:
    classifier = Classifier(rules, 2027)
    research = Research(
        executed_at=NOW, strategies=[], candidates=[candidate(i) for i in range(count)]
    )
    findings = assess(research, dataset(), classifier)
    approvals = [item.job_id for item in findings]
    batches, skipped = prepare_batches(
        research, dataset(), approvals, classifier=classifier, observed_at=NOW
    )
    assert not skipped
    assert [len(json.loads(batch)) for batch in batches] == [
        min(10, count - start) for start in range(0, count, 10)
    ]
    parsed = [
        job
        for batch in batches
        for job in parse_manual_batch(batch, classifier=classifier, observed_at=NOW)
    ]
    assert [job.linkedin_job_id for job in parsed] == approvals
    assert all(job.category.value == "embedded-systems" for job in parsed)
    assert prepare_batches(research, dataset(), [], classifier=classifier, observed_at=NOW) == (
        [],
        {},
    )
    if count >= 5:
        selected, skipped = prepare_batches(
            research, dataset(), approvals[:5], classifier=classifier, observed_at=NOW
        )
        assert not skipped
        assert [job["url"].rsplit("/", 1)[1] for job in json.loads(selected[0])] == approvals[:5]


def test_batches_respect_utf8_byte_budget_without_losing_approved_jobs(
    rules: ClassificationRules,
) -> None:
    classifier = Classifier(rules, 2027)
    research = Research(
        executed_at=NOW,
        strategies=[],
        candidates=[
            candidate(
                i,
                raw={
                    "company": "🧪" * 200,
                    "title": "Firmware Intern 2027 " + "🧪" * 479,
                    "locations": ["Berlin, Germany; " + "🧪" * 480],
                    "industries": "🧪" * 500,
                    "start_date": "🧪" * 100,
                },
            )
            for i in range(10)
        ],
    )
    findings = assess(research, dataset(), classifier)
    assert all(item.manual_record is not None for item in findings)
    batches, skipped = prepare_batches(
        research,
        dataset(),
        [item.job_id for item in findings],
        classifier=classifier,
        observed_at=NOW,
    )
    assert not skipped
    assert len(batches) == 2
    assert all(len(content) <= 65_536 for content in batches)
    assert (
        sum(
            len(parse_manual_batch(content, classifier=classifier, observed_at=NOW))
            for content in batches
        )
        == 10
    )
    assert "required batches: 2" in render_report(research, dataset(), findings)


def test_description_only_acceptance_is_not_manually_batched(rules: ClassificationRules) -> None:
    classifier = Classifier(rules, 2027)
    research = Research(
        executed_at=NOW,
        strategies=[],
        candidates=[
            candidate(
                raw={
                    "title": "Research Intern 2027",
                    "description": "Software engineering internship.",
                }
            ),
            candidate(2, directly_verified=False),
        ],
    )
    findings = assess(research, dataset(), classifier)
    assert findings[0].status == "confirmed"
    assert findings[0].manual_record is None
    batches, skipped = prepare_batches(
        research,
        dataset(),
        [item.job_id for item in findings],
        classifier=classifier,
        observed_at=NOW,
    )
    assert not batches
    assert len(skipped) == 2
    for approvals in (["999"], ["1000000001", "1000000001"]):
        with pytest.raises(ValueError, match="approval"):
            prepare_batches(research, dataset(), approvals, classifier=classifier, observed_at=NOW)


def test_report_deduplicates_and_escapes_exact_five_columns(rules: ClassificationRules) -> None:
    research = Research(
        executed_at=NOW,
        strategies=["Specialist placements"],
        candidates=[
            candidate(1),
            candidate(2, raw={"company": "A|B\n<script>*[link](url)"}),
            candidate(2, raw={"company": "A|B\n<script>*[link](url)"}),
            candidate(3, directly_verified=False),
            candidate(4, raw={"title": "Senior Software Intern 2027"}),
        ],
    )
    findings = assess(research, dataset("1000000001"), Classifier(rules, 2027))
    assert [item.status for item in findings] == [
        "duplicate",
        "confirmed",
        "duplicate",
        "conditional",
        "rejected",
    ]
    report = render_report(research, dataset("1000000001"), findings)
    assert report.count("| " + " | ".join(REPORT_COLUMNS) + " |") == 3
    assert all(len(line.split("|")) == 7 for line in report.splitlines() if line.startswith("|"))
    assert "<script>" not in report
    assert "&#124;" in report
    assert "&lt;script&gt;" in report
    assert "[LinkedIn 1000000002](https://www.linkedin.com/jobs/view/1000000002)" in report
    assert "duplicates removed: 2" in report
    assert "1 existing open positions examined" in report
    assert "Do you want to submit" in report
    assert "BEFORE the README review PR" in report
    empty = Research(
        executed_at=NOW, strategies=["Access denied"], limitations=["No compliant detail tools"]
    )
    empty_report = render_report(empty, None, assess(empty, None, Classifier(rules, 2027)))
    assert "existing open count unknown" in empty_report
    assert "Candidate observations: 0" in empty_report
    assert "No compliant detail tools" in empty_report


def test_offline_workflow_writes_report_then_requires_approval_without_canonical_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, rules: ClassificationRules
) -> None:
    import sqlite3

    def forbid(*args: object, **kwargs: object) -> None:
        pytest.fail("research must not access canonical state or run processes")

    monkeypatch.setattr(sqlite3, "connect", forbid)
    monkeypatch.setattr(subprocess, "run", forbid)
    monkeypatch.setattr(command, "utc_now", lambda: NOW)
    research = Research(
        executed_at=NOW,
        strategies=["Offline fixture"],
        candidates=[candidate(i) for i in range(11)],
    )
    (tmp_path / "research.json").write_text(research.model_dump_json(), encoding="utf-8")
    requests: list[str] = []
    real_client = httpx.Client
    fail_api = False
    content = export_bytes(range(900, 1001))

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if request.url.path.endswith("status"):
            return httpx.Response(
                200, json=status(101, dataset_sha256=hashlib.sha256(content).hexdigest())
            )
        if request.url.path.endswith(".json"):
            return httpx.Response(
                200, content=content, headers={"content-type": "application/json"}
            )
        if fail_api:
            return httpx.Response(503)
        page = int(request.url.params["page"])
        return httpx.Response(
            200,
            json={
                "version": "v1",
                "pagination": {"page": page, "pageSize": 100, "total": 101, "totalPages": 2},
                "data": [
                    row(i) for i in range(900 + (page - 1) * 100, min(900 + page * 100, 1001))
                ],
            },
        )

    def client_factory(**kwargs: object) -> httpx.Client:
        return real_client(transport=httpx.MockTransport(handle))

    monkeypatch.setattr("scripts.research.scout.httpx.Client", client_factory)
    (tmp_path / ".env").write_text(
        "OPPORTUNITIES_DATABASE_URL=invalid-not-to-be-loaded\n", encoding="utf-8"
    )
    common = ["--directory", str(tmp_path)]
    assert command.main(["dataset", *common]) == 0
    assert len(requests) == 5
    assert (
        len(PublicDataset.model_validate_json((tmp_path / "dataset.json").read_bytes()).ids) == 101
    )
    assert command.main(["report", *common]) == 0
    assert (tmp_path / "report.md").exists()
    assert not list(tmp_path.glob("batch-*.json"))
    assert command.main(["batches", *common]) == 1
    approvals = ",".join(str(1000000000 + i) for i in range(11))
    assert command.main(["batches", *common, "--approved-ids", approvals]) == 0
    assert (
        len(
            load_manual_batch(
                tmp_path / "batch-01.json", classifier=Classifier(rules, 2027), observed_at=NOW
            )
        )
        == 10
    )
    assert (
        len(
            load_manual_batch(
                tmp_path / "batch-02.json", classifier=Classifier(rules, 2027), observed_at=NOW
            )
        )
        == 1
    )
    before = (tmp_path / "report.md").read_bytes()
    assert command.main(["report", *common]) == 1
    assert (tmp_path / "report.md").read_bytes() == before
    fail_api = True
    assert command.main(["dataset", "--directory", str(tmp_path / "failed")]) == 1
    assert not (tmp_path / "failed/dataset.json").exists()
    assert not list(tmp_path.rglob("*.db"))


@pytest.mark.parametrize(
    "failure",
    ["dataset_changed", "export_required", "http_429", "public_timeout", "invalid_input_or_data"],
)
def test_cli_errors_expose_only_bounded_actionable_categories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    content = export_bytes([])
    snapshot = status(0, dataset_sha256=hashlib.sha256(content).hexdigest())
    real_client = httpx.Client
    status_calls = 0
    private = "DO_NOT_PRINT_PRIVATE_RESPONSE_OR_EXCEPTION"

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal status_calls
        if failure == "public_timeout":
            raise httpx.ReadTimeout(private)
        if failure == "http_429":
            return httpx.Response(429, text=private)
        if failure == "invalid_input_or_data":
            return httpx.Response(200, json={"private": private})
        if request.url.path.endswith("status"):
            status_calls += 1
            return httpx.Response(
                200,
                json={
                    **snapshot,
                    "release": None
                    if failure == "export_required"
                    else "124-1"
                    if status_calls > 1
                    else "123-1",
                },
            )
        if request.url.path.endswith(".json"):
            return httpx.Response(
                200, content=content, headers={"content-type": "application/json"}
            )
        return httpx.Response(
            200,
            json={
                "version": "v1",
                "data": [],
                "pagination": {"page": 1, "pageSize": 100, "total": 0, "totalPages": 0},
            },
        )

    def client_factory(**kwargs: object) -> httpx.Client:
        assert kwargs == {"timeout": 20, "trust_env": False, "follow_redirects": False}
        return real_client(transport=httpx.MockTransport(handle))

    monkeypatch.setattr("scripts.research.scout.httpx.Client", client_factory)
    assert command.main(["dataset", "--directory", str(tmp_path)]) == 1
    output = capsys.readouterr()
    assert f"[{failure}]" in output.err
    assert private not in output.err
    assert not output.out
    assert not (tmp_path / "dataset.json").exists()


@pytest.mark.parametrize(
    ("arguments", "category"),
    [
        (["dataset", "--without-dataset"], "invalid_options"),
        (["report", "--export"], "invalid_options"),
        (["report", "--approved-ids", "1000000001"], "invalid_options"),
        (["batches", "--without-dataset"], "invalid_options"),
        (["batches"], "approval_required"),
        (["dataset"], "output_exists"),
    ],
)
def test_cli_preflight_rejects_invalid_options_and_existing_outputs_without_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    category: str,
) -> None:
    def forbid(*args: object, **kwargs: object) -> None:
        pytest.fail("preflight must precede input reads and HTTP client creation")

    (tmp_path / "dataset.json").write_text("preserve previous output", encoding="utf-8")
    monkeypatch.setattr(command, "read_json", forbid)
    monkeypatch.setattr("scripts.research.scout.httpx.Client", forbid)
    assert command.main([*arguments, "--directory", str(tmp_path)]) == 1
    assert f"[{category}]" in capsys.readouterr().err
    assert (tmp_path / "dataset.json").read_text(encoding="utf-8") == "preserve previous output"


@pytest.mark.parametrize("output", ["dataset.json", "batch-02.json"])
@pytest.mark.parametrize("dangling_link", [False, True])
def test_existing_outputs_block_reads_or_partial_batch_writes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    output: str,
    dangling_link: bool,
) -> None:
    existing = tmp_path / output
    if dangling_link:
        try:
            existing.symlink_to(tmp_path / "absent-output")
        except OSError:
            pytest.skip("creating symlinks requires OS support and permission")
    else:
        existing.write_bytes(b"preserve original")
    if output == "dataset.json":
        arguments = ["dataset"]  # The offline guard forbids any unnecessary HTTP.
    else:
        research = Research(
            executed_at=NOW, strategies=[], candidates=[candidate(i) for i in range(11)]
        )
        (tmp_path / "research.json").write_text(research.model_dump_json(), encoding="utf-8")
        (tmp_path / "dataset.json").write_text(dataset().model_dump_json(), encoding="utf-8")
        approvals = ",".join(str(1000000000 + i) for i in range(11))
        arguments = ["batches", "--approved-ids", approvals]
    assert command.main([*arguments, "--directory", str(tmp_path)]) == 1
    assert "[output_exists]" in capsys.readouterr().err
    assert not (tmp_path / "batch-01.json").exists()
    assert not (tmp_path / "absent-output").exists()
    if dangling_link:
        assert existing.is_symlink()
    else:
        assert existing.read_bytes() == b"preserve original"


@pytest.mark.parametrize("approvals", ["999", "1000000001,1000000001"])
def test_cli_rejects_invalid_approvals_with_actionable_sanitized_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], approvals: str
) -> None:
    research = Research(executed_at=NOW, strategies=[], candidates=[candidate()])
    (tmp_path / "research.json").write_text(research.model_dump_json(), encoding="utf-8")
    (tmp_path / "dataset.json").write_text(dataset().model_dump_json(), encoding="utf-8")
    assert command.main(["batches", "--directory", str(tmp_path), "--approved-ids", approvals]) == 1
    output = capsys.readouterr()
    assert "[invalid_approval]" in output.err
    assert approvals not in output.err
    assert not output.out
    assert not list(tmp_path.glob("batch-*.json"))


def test_shared_skill_is_discoverable_while_personal_files_and_reports_remain_ignored() -> None:
    entry = ROOT / ".agents/skills/linkedin-opportunity-scout/SKILL.md"
    text = entry.read_text(encoding="utf-8")
    metadata = yaml.safe_load(text.split("---", 2)[1])
    assert metadata["name"] == "linkedin-opportunity-scout"
    assert all(
        word in metadata["description"] for word in ("LinkedIn", "dataset", "report", "manual")
    )
    assert "## E. Report and STOP" in text
    assert "## F. Only after specific approval" in text
    assert "reusable-process-state.yml" in text
    assert "manual_jobs.py" in text
    paths = [
        ".agents/skills/linkedin-opportunity-scout/SKILL.md",
        ".agents/skills/linkedin-opportunity-scout/private.md",
        ".agents/skills/private/SKILL.md",
        ".agents/skills/ROUTER.md",
        ".context/private.md",
        "reports/linkedin-opportunity-scout/run/report.md",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin", "-z"],
        input=("\0".join(paths) + "\0").encode(),
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0
    assert set(result.stdout.decode().strip("\0").split("\0")) == set(paths[1:])
