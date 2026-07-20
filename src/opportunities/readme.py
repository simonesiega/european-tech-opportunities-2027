"""Atomic rendering of the bounded database-backed README preview."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from opportunities.models.enums import EmploymentType
from opportunities.models.job import StoredJob
from opportunities.utils.files import atomic_write_text
from opportunities.utils.time import ensure_utc

SUMMARY_BEGIN_MARKER = "<!-- BEGIN OPPORTUNITY COUNTS -->"
SUMMARY_END_MARKER = "<!-- END OPPORTUNITY COUNTS -->"
BEGIN_MARKER = "<!-- BEGIN OPPORTUNITIES -->"
END_MARKER = "<!-- END OPPORTUNITIES -->"
TABLE_HEADER = "| Company | Title | Location | Listing |\n|---|---|---|---|\n"
README_PREVIEW_LIMIT = 10
DIRECTORY_URL = "https://opportunities2027.simonesiega.com/"


@dataclass(frozen=True, slots=True)
class ReadmeMetadata:
    """Hold generated README counters and timestamps."""

    open_positions: int
    last_successful_collection: datetime | None


def render_readme(path: Path, jobs: list[StoredJob], metadata: ReadmeMetadata) -> None:
    """Replace exactly one generated block without touching surrounding documentation."""
    if not path.is_file():
        raise ValueError(f"README does not exist: {path}")
    content = path.read_text(encoding="utf-8")
    begin, end = _marker_bounds(content)
    summary_begin, summary_end = _marker_bounds(
        content, SUMMARY_BEGIN_MARKER, SUMMARY_END_MARKER
    )
    internship_count, new_grad_count = _type_counts(jobs)
    summary = opportunity_count_cards(metadata.open_positions, internship_count, new_grad_count)
    content = (
        content[:summary_begin]
        + SUMMARY_BEGIN_MARKER
        + "\n"
        + summary
        + SUMMARY_END_MARKER
        + content[summary_end + len(SUMMARY_END_MARKER) :]
    )
    # Summary replacement does not change the offsets of the later opportunity block.
    begin, end = _marker_bounds(content)
    before = content[:begin]
    after = content[end + len(END_MARKER) :]
    block = markdown_block(jobs, metadata)
    rendered = f"{before}{BEGIN_MARKER}\n{block}{END_MARKER}{after}"
    atomic_write_text(path, rendered)


def markdown_block(jobs: list[StoredJob], metadata: ReadmeMetadata) -> str:
    """Build bounded previews for both supported opportunity types."""
    internships = _latest(jobs, EmploymentType.INTERNSHIP)
    new_grad = _latest(jobs, EmploymentType.NEW_GRAD)
    internship_count, new_grad_count = _type_counts(jobs)
    return (
        f"{markdown_metadata(metadata, internship_count, new_grad_count)}\n"
        f"Browse and filter the complete directory at **[{DIRECTORY_URL}]({DIRECTORY_URL})**.\n\n"
        f"### Latest New Grad positions\n\n"
        f"Showing the {len(new_grad)} most recently posted of {new_grad_count} open "
        f"New Grad positions:\n\n"
        f"{markdown_table(new_grad)}\n"
        f"### Latest internships\n\n"
        f"Showing the {len(internships)} most recently posted of {internship_count} open "
        f"internships:\n\n"
        f"{markdown_table(internships)}"
    )


def opportunity_count_cards(total: int, internships: int, new_grad: int) -> str:
    """Build three colored, generated count cards for the README header."""
    return (
        '<p align="center">\n'
        f'  <img src="https://img.shields.io/badge/Total%20opportunities-{total}-2563eb?style=for-the-badge" alt="Total opportunities: {total}" />\n'
        f'  <img src="https://img.shields.io/badge/Internships-{internships}-16a34a?style=for-the-badge" alt="Internships: {internships}" />\n'
        f'  <img src="https://img.shields.io/badge/New%20Grad-{new_grad}-9333ea?style=for-the-badge" alt="New Grad opportunities: {new_grad}" />\n'
        '</p>\n'
    )


def _type_counts(jobs: list[StoredJob]) -> tuple[int, int]:
    return (
        sum(job.employment_type == EmploymentType.INTERNSHIP for job in jobs),
        sum(job.employment_type == EmploymentType.NEW_GRAD for job in jobs),
    )


def markdown_metadata(
    metadata: ReadmeMetadata, internship_count: int = 0, new_grad_count: int = 0
) -> str:
    """Build README collection metadata and per-type counters."""
    last_collection = (
        _format_collection_time(metadata.last_successful_collection)
        if metadata.last_successful_collection is not None
        else "Never"
    )
    return (
        f"**Open positions:** {metadata.open_positions} "
        f"(Internships: {internship_count} · New Grad: {new_grad_count})<br>\n"
        f"**Last successful collection:** {last_collection}\n"
    )


def _latest(jobs: list[StoredJob], employment_type: EmploymentType) -> list[StoredJob]:
    """Return the bounded newest-first preview for one opportunity type."""
    return sorted(
        (job for job in jobs if job.employment_type == employment_type),
        key=lambda job: (job.first_seen_at, job.linkedin_job_id),
        reverse=True,
    )[:README_PREVIEW_LIMIT]


def markdown_table(jobs: list[StoredJob]) -> str:
    """Build a four-column opportunity table from the supplied preview rows."""
    lines = [TABLE_HEADER.rstrip("\n")]
    for job in jobs:
        lines.append(
            "| "
            + " | ".join(
                (
                    _escape(job.company),
                    _escape(job.title),
                    _escape(job.location),
                    f"[View](<{_safe_url(job.link)}>)",
                )
            )
            + " |"
        )
    return f"{'\n'.join(lines)}\n"


def validate_readme(
    path: Path,
    jobs: list[StoredJob] | None = None,
    metadata: ReadmeMetadata | None = None,
) -> list[str]:
    """Validate generated README content against canonical state."""
    if not path.is_file():
        return [f"README does not exist: {path}"]
    content = path.read_text(encoding="utf-8")
    errors: list[str] = []
    try:
        begin, end = _marker_bounds(content)
        summary_begin, summary_end = _marker_bounds(
            content, SUMMARY_BEGIN_MARKER, SUMMARY_END_MARKER
        )
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    block = content[begin + len(BEGIN_MARKER) : end].strip()
    if jobs is not None and metadata is not None:
        internship_count, new_grad_count = _type_counts(jobs)
        summary = content[
            summary_begin + len(SUMMARY_BEGIN_MARKER) : summary_end
        ].strip()
        expected_summary = opportunity_count_cards(
            metadata.open_positions, internship_count, new_grad_count
        ).strip()
        if summary != expected_summary:
            errors.append("README opportunity count cards do not match open jobs in SQLite")
    if TABLE_HEADER.strip() not in block:
        errors.append("README position tables must have Company, Title, Location, Listing columns")
    if (
        jobs is not None
        and metadata is not None
        and block != markdown_block(jobs, metadata).strip()
    ):
        errors.append("README opportunity block does not match open jobs and metadata in SQLite")
    return errors


def _escape(value: str) -> str:
    """Escape text for a Markdown table cell."""
    escaped = html.escape(value.replace("\n", " "), quote=False)
    for character in ("\\", "|", "[", "]", "(", ")", "`", "*", "_"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _safe_url(value: str) -> str:
    """Escape angle brackets in a Markdown link target."""
    return value.replace("<", "%3C").replace(">", "%3E")


def _format_collection_time(value: datetime) -> str:
    """Format a collection timestamp for README display."""
    normalized = ensure_utc(value)
    month = normalized.strftime("%B")
    return (
        f"{month} {normalized.day}, {normalized.year} at "
        f"{normalized.hour:02d}:{normalized.minute:02d} UTC"
    )


def _marker_bounds(
    content: str, begin_marker: str = BEGIN_MARKER, end_marker: str = END_MARKER
) -> tuple[int, int]:
    """Return one correctly ordered generated marker pair."""
    marker_name = "opportunity" if begin_marker == BEGIN_MARKER else "opportunity count"
    if content.count(begin_marker) != 1 or content.count(end_marker) != 1:
        raise ValueError(f"README must contain exactly one {marker_name} marker pair")
    begin = content.index(begin_marker)
    end = content.index(end_marker)
    if begin >= end:
        raise ValueError(f"README {marker_name} markers are out of order")
    return begin, end
