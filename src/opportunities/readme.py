"""Atomic rendering of the bounded database-backed README preview."""

from __future__ import annotations

import html
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from opportunities.models.enums import EmploymentType
from opportunities.models.job import StoredJob

BEGIN_MARKER = "<!-- BEGIN INTERNSHIPS -->"
END_MARKER = "<!-- END INTERNSHIPS -->"
TABLE_HEADER = "| Company | Title | Location | Listing |\n|---|---|---|---|\n"
README_PREVIEW_LIMIT = 10
DIRECTORY_URL = "https://internship2027.simonesiega.com/"


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
    if content.count(BEGIN_MARKER) != 1 or content.count(END_MARKER) != 1:
        raise ValueError("README must contain exactly one internship marker pair")
    # Replace only the generated marker range; all hand-written documentation remains intact.
    before, remainder = content.split(BEGIN_MARKER, 1)
    _old, after = remainder.split(END_MARKER, 1)
    block = markdown_block(jobs, metadata)
    rendered = f"{before}{BEGIN_MARKER}\n{block}{END_MARKER}{after}"
    _atomic_write(path, rendered)


def markdown_block(jobs: list[StoredJob], metadata: ReadmeMetadata) -> str:
    """Build bounded previews for both supported opportunity types."""
    internships = _latest(jobs, EmploymentType.INTERNSHIP)
    new_grad = _latest(jobs, EmploymentType.NEW_GRAD)
    internship_count = sum(job.employment_type == EmploymentType.INTERNSHIP for job in jobs)
    new_grad_count = sum(job.employment_type == EmploymentType.NEW_GRAD for job in jobs)
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
    """Build a four-column internship table from the supplied preview rows."""
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
    if content.count(BEGIN_MARKER) != 1 or content.count(END_MARKER) != 1:
        errors.append("README must contain exactly one internship marker pair")
        return errors
    block = content.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0].strip()
    if TABLE_HEADER.strip() not in block:
        errors.append("README position tables must have Company, Title, Location, Link columns")
    if (
        jobs is not None
        and metadata is not None
        and block != markdown_block(jobs, metadata).strip()
    ):
        errors.append("README internship block does not match open jobs and metadata in SQLite")
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
    month = value.strftime("%B")
    return f"{month} {value.day}, {value.year} at {value.hour:02d}:{value.minute:02d} UTC"


def _atomic_write(path: Path, content: str) -> None:
    """Replace a file atomically with UTF-8 content."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
