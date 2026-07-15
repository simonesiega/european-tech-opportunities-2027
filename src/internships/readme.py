"""Atomic rendering of the database-backed four-column README table."""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from internships.models.job import StoredJob

BEGIN_MARKER = "<!-- BEGIN INTERNSHIPS -->"
END_MARKER = "<!-- END INTERNSHIPS -->"
TABLE_HEADER = "| Company | Title | Location | Link |\n|---|---|---|---|\n"
_SEARCH_COUNT_PATTERN = re.compile(
    r"The current registry contains \d+ independently bounded searches\."
)


@dataclass(frozen=True, slots=True)
class ReadmeMetadata:
    """Hold generated README counters and timestamps."""

    open_internships: int
    last_successful_collection: datetime | None
    configured_searches: int | None = None


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
    rendered = _render_search_registry_count(rendered, metadata)
    _atomic_write(path, rendered)


def markdown_block(jobs: list[StoredJob], metadata: ReadmeMetadata) -> str:
    """Build the complete generated README block."""
    return f"{markdown_metadata(metadata)}\n{markdown_table(jobs)}"


def markdown_metadata(metadata: ReadmeMetadata) -> str:
    """Build README collection metadata."""
    last_collection = (
        _format_collection_time(metadata.last_successful_collection)
        if metadata.last_successful_collection is not None
        else "Never"
    )
    return (
        f"**Open internships:** {metadata.open_internships}<br>\n"
        f"**Last successful collection:** {last_collection}\n"
    )


def markdown_table(jobs: list[StoredJob]) -> str:
    """Build the four-column internship table."""
    lines = [TABLE_HEADER.rstrip("\n")]
    for job in jobs:
        lines.append(
            "| "
            + " | ".join(
                (
                    _escape(job.company),
                    _escape(job.title),
                    _escape(job.location),
                    f"[Link](<{_safe_url(job.link)}>)",
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
        errors.append("README internship table must have Company, Title, Location, Link columns")
    if (
        jobs is not None
        and metadata is not None
        and block != markdown_block(jobs, metadata).strip()
    ):
        errors.append("README internship block does not match open jobs and metadata in SQLite")
    if metadata is not None and metadata.configured_searches is not None:
        registry_sentences = _SEARCH_COUNT_PATTERN.findall(content)
        expected = _search_registry_sentence(metadata.configured_searches)
        if len(registry_sentences) > 1:
            errors.append("README contains more than one search registry count sentence")
        elif registry_sentences and registry_sentences[0] != expected:
            errors.append("README search registry count does not match configured searches")
    return errors


def _render_search_registry_count(content: str, metadata: ReadmeMetadata) -> str:
    """Replace the documented registry total with generated metadata."""
    if metadata.configured_searches is None:
        return content
    matches = _SEARCH_COUNT_PATTERN.findall(content)
    if len(matches) > 1:
        raise ValueError("README must contain no more than one search registry count sentence")
    if not matches:
        return content
    return _SEARCH_COUNT_PATTERN.sub(
        _search_registry_sentence(metadata.configured_searches), content, count=1
    )


def _search_registry_sentence(configured_searches: int) -> str:
    """Build the registry-count documentation sentence."""
    return f"The current registry contains {configured_searches} independently bounded searches."


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
