"""Offline evidence assessment, reports, and approved batch preparation for Codex."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from opportunities.manual_jobs import (
    MAX_MANUAL_BATCH_BYTES,
    MAX_MANUAL_BATCH_JOBS,
    parse_manual_batch,
    parse_posted_at,
)
from opportunities.models.job import DiscoveredJob
from opportunities.models.raw import RawJob
from opportunities.normalization.location import normalize_locations
from opportunities.normalization.title import normalize_title
from opportunities.pipeline.classification import ClassificationDecision, Classifier
from opportunities.scout_dataset import PublicDataset
from opportunities.scrapers.linkedin import has_closed_application_notice
from opportunities.utils.text import clean_text, normalized_key
from opportunities.utils.url import canonicalize_url, extract_linkedin_job_id

# A negative quotation can veto an open attestation, but cannot establish closure
# without the source context required by the existing scoped-alert detector.
_OPEN_CLAIM_CONTRADICTION_RE = re.compile(
    r"\b(?:no longer|not(?: currently)?) accepting applications\b|\bhttp\s*(?:404|410)\b"
)

REPORT_COLUMNS = (
    "Employer / indexed title",
    "LinkedIn URL",
    "Location and cycle evidence",
    "Conditional classification",
    "Supporting evidence and uncertainty",
)


class AvailabilityEvidence(BaseModel):
    """Attested source evidence, never an inference from a missing closure warning."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    basis: Literal["accepting_applications", "closure_alert", "http_404", "http_410", "unknown"] = (
        "unknown"
    )
    evidence: str = Field(default="", max_length=2_000)

    @property
    def contradicts_open_claim(self) -> bool:
        return self.basis == "accepting_applications" and bool(
            _OPEN_CLAIM_CONTRADICTION_RE.search(normalized_key(self.evidence))
        )

    @property
    def state(self) -> Literal["open", "closed", "unknown"]:
        if not clean_text(self.evidence) or self.basis == "unknown" or self.contradicts_open_claim:
            return "unknown"
        return "open" if self.basis == "accepting_applications" else "closed"


def availability_from_public_html(source_html: str) -> AvailabilityEvidence:
    """Inspect authorized HTML offline; absence is unknown and source challenges still raise."""
    if has_closed_application_notice(source_html):
        return AvailabilityEvidence(
            basis="closure_alert", evidence="Scoped LinkedIn closure alert detected"
        )
    return AvailabilityEvidence()


class Candidate(BaseModel):
    """Session-supplied facts; direct verification is an attestation, not an AI score."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    url: str
    listing: RawJob | None = None
    directly_verified: bool = Field(default=False, strict=True)
    availability: AvailabilityEvidence = Field(default_factory=AvailabilityEvidence)
    location_cycle_evidence: str = ""
    supporting_evidence: str = ""
    uncertainties: list[str] = Field(default_factory=list)

    @property
    def availability_state(self) -> Literal["open", "closed", "unknown"]:
        return self.availability.state if self.directly_verified else "unknown"

    @model_validator(mode="before")
    @classmethod
    def explicit_posting_time(cls, value: object) -> object:
        if isinstance(value, dict):
            listing = value.get("listing")
            if isinstance(listing, dict) and (posted := listing.get("posted_at")) is not None:
                if not isinstance(posted, str):
                    raise ValueError(
                        "research posting evidence must be an explicit timestamp string"
                    )
                parse_posted_at(posted)
        return value

    @model_validator(mode="after")
    def identity(self) -> Candidate:
        job_id = extract_linkedin_job_id(self.url)
        if self.listing is not None and self.listing.source_job_id != job_id:
            raise ValueError("research listing identity conflicts with URL")
        return self


class Research(BaseModel):
    """Local session ledger, including zero-result and access-limited runs."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    executed_at: datetime
    strategies: list[str]
    candidates: list[Candidate] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    registry_suggestions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def aware_clock(self) -> Research:
        if self.executed_at.tzinfo is None or self.executed_at.utcoffset() is None:
            raise ValueError("research execution time must include a timezone")
        return self


@dataclass(frozen=True)
class Finding:
    candidate: Candidate
    job_id: str
    status: Literal["confirmed", "conditional", "rejected", "duplicate"]
    classification: str
    reason: str
    manual_record: dict[str, str | None] | None = None
    observations: tuple[Candidate, ...] = ()


def _fact_key(value: object) -> str:
    if isinstance(value, str):
        text = clean_text(value)
        # Neither Unicode casefold nor the classifier's lossy ASCII projection is
        # sufficient alone; require both without turning blank text into a fact.
        return json.dumps((text.casefold(), normalized_key(text))) if text else ""
    if isinstance(value, list):
        return json.dumps(sorted({_fact_key(item) for item in value}))
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _joined(values: list[str]) -> str:
    return "; ".join(sorted({value.strip() for value in values if clean_text(value)}))


def _classify_listing(raw: RawJob, classifier: Classifier) -> ClassificationDecision:
    return classifier.classify(
        title=normalize_title(raw.title),
        description=raw.description,
        location=normalize_locations(raw.locations),
        posted_at=raw.posted_at,
    )


def _reconcile(observations: tuple[Candidate, ...], classifier: Classifier) -> Candidate:
    """Prefer verified facts, fill omissions, and quarantine incompatible verified values.

    No implicit newest-wins rule: verified contradictions need a documented fresh review.
    Free-text uncertainties on verified observations remain blocking until that review.
    """
    verified = [item for item in observations if item.directly_verified]
    trusted = verified or list(observations)
    listings = [item.listing for item in trusted if item.listing is not None]
    conflicts: list[str] = []
    raw: RawJob | None = None
    if listings:
        fields = listings[0].model_dump()
        for field in (
            "company",
            "title",
            "locations",
            "description",
            "industries",
            "start_date",
            "posted_at",
        ):
            values: list[object] = [
                value
                for item in listings
                if (value := getattr(item, field)) not in (None, "", []) and _fact_key(value)
            ]
            if len({_fact_key(value) for value in values}) > 1:
                conflicts.append(f"Conflicting {'verified' if verified else 'preliminary'} {field}")
            if values:
                fields[field] = values[0]
        # All replacements come from validated RawJob fields. Revalidating their
        # serialized form would decode entities again and change source semantics.
        raw = listings[0].model_copy(update=fields)
        if not conflicts and len(listings) > 1:
            decision = _classify_listing(raw, classifier)
            for listing in listings:
                # Fill omissions from agreeing facts, not from snippets. Compare
                # actual outcomes too: model/title cleanup can compose differently
                # from scalar keys, including case-sensitive entity decoding.
                completed = fields | {
                    key: value
                    for key, value in listing.model_dump().items()
                    if value not in (None, "", []) and _fact_key(value)
                }
                if completed == fields:
                    continue
                if _classify_listing(listing.model_copy(update=completed), classifier) != decision:
                    conflicts.append(
                        f"Conflicting {'verified' if verified else 'preliminary'} eligibility"
                    )
                    break
    availability = [item.availability for item in trusted if item.availability.state != "unknown"]
    contradictory = next(
        (item.availability for item in trusted if item.availability.contradicts_open_claim), None
    )
    if contradictory is not None:
        conflicts.append("Affirmative availability claim contradicts supplied evidence")
        resolved_availability = contradictory
    elif len({item.state for item in availability}) > 1:
        conflicts.append(f"Conflicting {'verified' if verified else 'preliminary'} availability")
        resolved_availability = AvailabilityEvidence()
    else:
        resolved_availability = availability[0] if availability else trusted[0].availability
    return Candidate(
        url=canonicalize_url(observations[0].url),
        listing=raw,
        directly_verified=bool(verified),
        availability=resolved_availability,
        location_cycle_evidence=_joined([item.location_cycle_evidence for item in trusted]),
        supporting_evidence=_joined([item.supporting_evidence for item in trusted]),
        uncertainties=sorted(
            {*conflicts, *(text for item in trusted for text in item.uncertainties)}
        ),
    )


def assess(
    research: Research, dataset: PublicDataset | None, classifier: Classifier
) -> list[Finding]:
    """Reconcile all observations before eligibility; never create canonical-state writers."""
    groups: dict[str, list[Candidate]] = {}
    for observation in research.candidates:
        groups.setdefault(extract_linkedin_job_id(observation.url), []).append(observation)
    ordered = {
        job_id: tuple(sorted(groups[job_id], key=lambda item: item.model_dump_json()))
        for job_id in sorted(groups, key=lambda value: (int(value), value))
    }
    findings: list[Finding] = []
    for job_id, observations in ordered.items():
        candidate = _reconcile(observations, classifier)
        if dataset is not None and job_id in dataset.ids:
            findings.append(
                Finding(
                    candidate,
                    job_id,
                    "duplicate",
                    "Not proposed",
                    "Already in published open dataset",
                )
            )
            continue
        if candidate.availability_state == "closed":
            findings.append(
                Finding(
                    candidate,
                    job_id,
                    "rejected",
                    "Not proposed",
                    "Explicit source closure evidence",
                )
            )
            continue
        raw = candidate.listing
        if raw is None:
            findings.append(
                Finding(candidate, job_id, "conditional", "Unverified", "Missing listing facts")
            )
            continue
        title = normalize_title(raw.title)
        locations = normalize_locations(raw.locations)
        decision = _classify_listing(raw, classifier)
        employment_type = decision.employment_type.value if decision.employment_type else "unknown"
        taxonomy = f"{employment_type} / {decision.category.value}"
        missing = list(candidate.uncertainties)
        if candidate.availability_state != "open":
            missing.append("Availability unknown; explicit current acceptance evidence required")
        if not candidate.directly_verified:
            missing.append("LinkedIn detail evidence not directly verified")
        if not clean_text(candidate.location_cycle_evidence) or not clean_text(
            candidate.supporting_evidence
        ):
            missing.append("Missing documented source evidence")
        if dataset is None:
            missing.append("Complete public dataset unavailable; novelty unknown")
        if raw.posted_at is not None and raw.posted_at > research.executed_at:
            missing.append("Posting evidence is in the future")
        # A failed deterministic check is conclusive only with sufficiently verified facts.
        if missing:
            findings.append(
                Finding(
                    candidate,
                    job_id,
                    "conditional",
                    taxonomy,
                    "; ".join([*missing, decision.exclusion_reason or "Available checks pass"]),
                )
            )
            continue
        if not decision.include:
            findings.append(
                Finding(
                    candidate, job_id, "rejected", taxonomy, decision.exclusion_reason or "Excluded"
                )
            )
            continue
        record = {
            "url": canonicalize_url(candidate.url),
            "company": raw.company,
            "title": title,
            "location": "; ".join(locations.locations),
            "category": decision.category.value,
            "employment_type": decision.employment_type.value if decision.employment_type else "",
            "industries": raw.industries,
            "start_date": raw.start_date,
            "posted_at": raw.posted_at.isoformat() if raw.posted_at else None,
        }
        try:
            DiscoveredJob.model_validate(
                {
                    **{key: value for key, value in record.items() if key != "url"},
                    "linkedin_job_id": job_id,
                    "link": record["url"],
                }
            )
        except ValidationError:
            findings.append(
                Finding(
                    candidate,
                    job_id,
                    "rejected",
                    taxonomy,
                    "Normalized fields fail the publication model",
                )
            )
            continue
        try:
            parse_manual_batch(
                json.dumps([record]).encode(),
                classifier=classifier,
                observed_at=research.executed_at,
            )
        except ValueError as exc:
            findings.append(
                Finding(
                    candidate,
                    job_id,
                    "confirmed",
                    taxonomy,
                    f"Research checks pass; not manually addable: {exc}",
                )
            )
        else:
            findings.append(
                Finding(
                    candidate,
                    job_id,
                    "confirmed",
                    taxonomy,
                    "Deterministic checks pass on supplied, directly verified facts",
                    record,
                )
            )
    result: list[Finding] = []
    for finding in findings:
        observations = ordered[finding.job_id]
        result.append(replace(finding, observations=observations))
        result.extend(
            Finding(
                item,
                finding.job_id,
                "duplicate",
                "Not proposed",
                "Repeated ID; evidence reconciled",
            )
            for item in observations[1:]
        )
    return result


class ApprovalError(ValueError):
    """Invalid candidate selection, separate from evidence or classification failures."""


def prepare_batches(
    research: Research,
    dataset: PublicDataset | None,
    approved_ids: list[str],
    *,
    classifier: Classifier,
    observed_at: datetime,
) -> tuple[list[bytes], dict[str, str]]:
    """Reassess the ledger independently of report text/status; validate bytes, never dispatch."""
    findings = assess(research, dataset, classifier)
    if len(approved_ids) != len(set(approved_ids)):
        raise ApprovalError("duplicate approval identity")
    by_id = {finding.job_id: finding for finding in findings if finding.status != "duplicate"}
    if set(approved_ids) - by_id.keys():
        raise ApprovalError("approval references an unknown or duplicate candidate")
    records: list[dict[str, str | None]] = []
    skipped: dict[str, str] = {}
    for job_id in approved_ids:
        finding = by_id[job_id]
        if finding.status != "confirmed" or finding.manual_record is None:
            skipped[job_id] = finding.reason
            continue
        record = finding.manual_record
        try:
            parse_manual_batch(
                json.dumps([record]).encode(), classifier=classifier, observed_at=observed_at
            )
        except ValueError as exc:
            skipped[job_id] = str(exc)
        else:
            records.append(record)
    batches = _encode_batches(records)
    for content in batches:
        parse_manual_batch(content, classifier=classifier, observed_at=observed_at)
    return batches, skipped


def _encode_batches(records: list[dict[str, str | None]]) -> list[bytes]:
    """Partition by both workflow limits, counting exact UTF-8 bytes rather than characters."""

    def encode(rows: list[dict[str, str | None]]) -> bytes:
        return (json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    batches: list[bytes] = []
    current: list[dict[str, str | None]] = []
    for record in records:
        proposed = [*current, record]
        if len(proposed) > MAX_MANUAL_BATCH_JOBS or len(encode(proposed)) > MAX_MANUAL_BATCH_BYTES:
            if not current or len(encode([record])) > MAX_MANUAL_BATCH_BYTES:
                raise ValueError("one manual record exceeds the workflow byte budget")
            batches.append(encode(current))
            current = [record]
        else:
            current = proposed
    if current:
        batches.append(encode(current))
    return batches


def _cell(value: str) -> str:
    # Escape source text, not Markdown links generated from validated identity URLs.
    escaped = html.escape(value, quote=False).replace("\\", "&#92;")
    for char in "|[]*`_":
        escaped = escaped.replace(char, f"&#{ord(char)};")
    return " ".join(escaped.split())


def _finding_evidence(finding: Finding) -> str:
    candidate = finding.candidate
    parts = [
        f"Availability: {candidate.availability_state} ({candidate.availability.basis}): "
        f"{candidate.availability.evidence or 'Not established'}",
        candidate.supporting_evidence,
        finding.reason,
        *candidate.uncertainties,
    ]
    if len(finding.observations) > 1:
        # Preserve both stronger and superseded evidence; never hide contradictory facts
        # in a generic duplicate counter. The original ledger retains full descriptions.
        for observation in finding.observations:
            raw = observation.listing
            facts = (
                f"{raw.company} / {raw.title}; locations: {', '.join(raw.locations)}; "
                f"description: {(raw.description or '')[:240]}; industries: {raw.industries}; "
                f"start: {raw.start_date}; posted: {raw.posted_at}"
                if raw
                else "Missing listing facts"
            )
            parts.append(
                f"{'Verified' if observation.directly_verified else 'Preliminary'} observation: "
                f"{facts}; availability: {observation.availability_state} "
                f"({observation.availability.basis}): {observation.availability.evidence}; "
                f"{observation.location_cycle_evidence}; {observation.supporting_evidence}; "
                f"uncertainties: {'; '.join(observation.uncertainties)}"
            )
    return "; ".join(part for part in parts if part)


def render_report(
    research: Research, dataset: PublicDataset | None, findings: list[Finding]
) -> str:
    """Render exactly five primary columns and a truthful, approval-gated handoff."""
    counts = {
        status: sum(item.status == status for item in findings)
        for status in ("confirmed", "conditional", "rejected", "duplicate")
    }
    manual_count = sum(item.manual_record is not None for item in findings)
    batch_count = len(
        _encode_batches([item.manual_record for item in findings if item.manual_record is not None])
    )
    lines = [
        "# LinkedIn opportunity research",
        "",
        f"Executed: {research.executed_at.isoformat()}",
        "",
    ]
    if dataset is None:
        lines.append(
            "Dataset: unavailable or incomplete; existing open count unknown. No novelty claims."
        )
    else:
        lines.append(f"Dataset: {_cell(json.dumps(dataset.status, sort_keys=True))}")
        lines.append(
            f"Retrieved: {dataset.retrieved_at.isoformat()} via {dataset.method}; "
            f"{len(dataset.ids)} existing open positions examined."
        )
    lines += [
        "",
        "Absence means not currently published open, not never present in canonical history.",
        "Direct verification is a session attestation; "
        "deterministic checks do not authenticate source facts.",
        "",
        f"Candidate observations: {len(research.candidates)}; "
        f"duplicates removed: {counts['duplicate']}; confirmed eligible: {counts['confirmed']}; "
        f"conditional: {counts['conditional']}; rejected: {counts['rejected']}.",
        f"Manually addable: {manual_count}; required batches: {batch_count}.",
        "",
        "## Search strategies",
        "",
        *[f"- {_cell(item)}" for item in research.strategies],
    ]
    for status, heading in (
        ("confirmed", "Confirmed candidates"),
        ("conditional", "Further review"),
        ("rejected", "Rejected candidates"),
    ):
        lines += [
            "",
            f"## {heading}",
            "",
            "| " + " | ".join(REPORT_COLUMNS) + " |",
            "|---|---|---|---|---|",
        ]
        for finding in findings:
            if finding.status != status:
                continue
            candidate = finding.candidate
            raw = candidate.listing
            identity = f"{raw.company} / {normalize_title(raw.title)}" if raw else "Not verified"
            evidence = _finding_evidence(finding)
            cells = [
                _cell(identity),
                f"[LinkedIn {finding.job_id}]({canonicalize_url(candidate.url)})",
                _cell(candidate.location_cycle_evidence or "Not established"),
                _cell(f"{status}: {finding.classification}"),
                _cell(evidence),
            ]
            lines.append("| " + " | ".join(cells) + " |")
        if not any(item.status == status for item in findings):
            lines += ["", "None found."]
    lines += [
        "",
        "## Duplicates",
        "",
        *[
            f"- LinkedIn {item.job_id}: {_cell(_finding_evidence(item))}"
            for item in findings
            if item.status == "duplicate"
        ],
        "",
        "## Access and verification limitations",
        "",
        *[f"- {_cell(item)}" for item in research.limitations],
        "",
        "## Search registry suggestions",
        "",
        *[f"- {_cell(item)}" for item in research.registry_suggestions],
        "",
        "## Approval required",
        "",
        "No canonical writes, workflow dispatch, PR creation, merge, or deployment performed.",
        "Do you want to submit specific reviewed candidates? Identify the approved LinkedIn IDs.",
        "Dispatch writes canonical state and publishes a protected snapshot "
        "BEFORE the README review PR.",
        "Each later batch waits for the previous reviewed state to merge "
        "and requires dispatch approval.",
        "",
    ]
    return "\n".join(lines)
