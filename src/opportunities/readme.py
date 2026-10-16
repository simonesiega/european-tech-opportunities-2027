"""Render bounded README projections with preflight and atomic per-file writes."""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from opportunities.models.enums import EmploymentType
from opportunities.models.job import StoredJob
from opportunities.public_exports import directory_state_rows
from opportunities.readme_localization import LOCALES, ReadmeLocale, locale_for_path
from opportunities.utils.files import atomic_write_text
from opportunities.utils.time import ensure_utc

SUMMARY_BEGIN_MARKER = "<!-- BEGIN OPPORTUNITY COUNTS -->"
SUMMARY_END_MARKER = "<!-- END OPPORTUNITY COUNTS -->"
BEGIN_MARKER = "<!-- BEGIN OPPORTUNITIES -->"
END_MARKER = "<!-- END OPPORTUNITIES -->"
README_PREVIEW_LIMIT = 5
README_LANGUAGES = ("it", "fr", "de", "es", "zh-CN")
DIRECTORY_URL = "https://techopportunities.eu/"
STATE_SEAL_PREFIX = "<!-- Public directory state v1 sha256: "
STATE_SEAL_PATTERN = re.compile(r"<!-- Public directory state v1 sha256: [0-9a-f]{64} -->")


@dataclass(frozen=True, slots=True)
class ReadmeMetadata:
    """Hold generated README counters and timestamps."""

    open_positions: int
    last_successful_collection: datetime | None


def render_readme(path: Path, jobs: list[StoredJob], metadata: ReadmeMetadata) -> None:
    """Preflight all README projections, then replace only their generated regions."""
    outputs = [
        (target, _render_readme(target, jobs, metadata))
        for target in (path, *_translation_paths(path))
    ]
    for target, rendered in outputs:
        atomic_write_text(target, rendered)


def _render_readme(path: Path, jobs: list[StoredJob], metadata: ReadmeMetadata) -> str:
    if not path.is_file():
        raise ValueError(f"README does not exist: {path}")
    content = path.read_text(encoding="utf-8")
    locale = locale_for_path(path)
    summary_begin, summary_end = _marker_bounds(content, SUMMARY_BEGIN_MARKER, SUMMARY_END_MARKER)
    begin, end = _marker_bounds(content)
    if not (summary_end < begin or end < summary_begin):
        raise ValueError("README generated regions must not overlap")
    internship_count, new_grad_count = _type_counts(jobs)
    summary = opportunity_count_cards(
        metadata.open_positions,
        internship_count,
        new_grad_count,
        metadata.last_successful_collection,
        locale=locale,
    ) + _directory_state_seal(jobs, metadata.last_successful_collection)
    content = (
        content[:summary_begin]
        + SUMMARY_BEGIN_MARKER
        + "\n"
        + summary
        + SUMMARY_END_MARKER
        + content[summary_end + len(SUMMARY_END_MARKER) :]
    )
    begin, end = _marker_bounds(content)
    before = content[:begin]
    after = content[end + len(END_MARKER) :]
    block = markdown_block(jobs, metadata, locale=locale)
    return f"{before}{BEGIN_MARKER}\n{block}{END_MARKER}{after}"


def _translation_paths(path: Path) -> list[Path]:
    """Require the five supported projections when a translation directory exists."""
    directory = path.parent / "docs/translations"
    if path.name != "README.md" or not directory.is_dir():
        return []
    return [directory / f"README.{language}.md" for language in README_LANGUAGES]


def markdown_block(
    jobs: list[StoredJob], metadata: ReadmeMetadata, *, locale: ReadmeLocale = LOCALES["en"]
) -> str:
    """Build bounded previews for both supported opportunity types."""
    internships = _latest(jobs, EmploymentType.INTERNSHIP)
    new_grad = _latest(jobs, EmploymentType.NEW_GRAD)
    internship_count, new_grad_count = _type_counts(jobs)
    return (
        f"{markdown_metadata(metadata, internship_count, new_grad_count, locale=locale)}\n"
        f"{locale.directory.format(url=DIRECTORY_URL)}\n\n"
        f"### {locale.new_grad_heading}\n\n"
        f"{locale.new_grad_preview.format(shown=len(new_grad), total=new_grad_count)}\n\n"
        f"{markdown_table(new_grad, locale=locale)}\n"
        f"### {locale.internship_heading}\n\n"
        f"{locale.internship_preview.format(shown=len(internships), total=internship_count)}\n\n"
        f"{markdown_table(internships, locale=locale)}"
    )


def opportunity_count_cards(
    total: int,
    internships: int,
    new_grad: int,
    last_successful_collection: datetime | None,
    *,
    locale: ReadmeLocale = LOCALES["en"],
) -> str:
    """Build localized update and count cards from the same canonical counters."""
    updated_text = locale.collection_time(last_successful_collection)
    badges = "".join(
        f'  <img src="https://img.shields.io/badge/{quote(label, safe="")}-'
        f'{count}-{color}?style=for-the-badge" alt="{alt}{count}" />\n'
        for label, alt, count, color in zip(
            locale.badge_labels,
            locale.badge_alt_labels,
            (total, internships, new_grad),
            ("2563eb", "16a34a", "9333ea"),
            strict=True,
        )
    )
    return (
        '<p align="center">\n'
        f"  <strong>{locale.collection_label}{updated_text}</strong><br>\n"
        f"{badges}</p>\n"
    )


def directory_state_digest(
    jobs: list[StoredJob], last_successful_collection: datetime | None
) -> str:
    """Hash the complete public directory state and exact collection timestamp."""
    timestamp = (
        ensure_utc(last_successful_collection).isoformat(timespec="microseconds")
        if last_successful_collection is not None
        else None
    )
    # Seal all public rows, not just the preview, so off-preview changes require review.
    payload = {
        "version": 1,
        "last_successful_collection": timestamp,
        "opportunities": directory_state_rows(jobs),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _directory_state_seal(
    jobs: list[StoredJob], last_successful_collection: datetime | None
) -> str:
    return f"{STATE_SEAL_PREFIX}{directory_state_digest(jobs, last_successful_collection)} -->\n"


def _type_counts(jobs: list[StoredJob]) -> tuple[int, int]:
    return (
        sum(job.employment_type == EmploymentType.INTERNSHIP for job in jobs),
        sum(job.employment_type == EmploymentType.NEW_GRAD for job in jobs),
    )


def markdown_metadata(
    metadata: ReadmeMetadata,
    internship_count: int = 0,
    new_grad_count: int = 0,
    *,
    locale: ReadmeLocale = LOCALES["en"],
) -> str:
    """Build README collection metadata and per-type counters."""
    return locale.metadata.format(
        total=metadata.open_positions,
        internships=internship_count,
        new_grad=new_grad_count,
        updated=locale.collection_time(metadata.last_successful_collection),
    )


def _latest(jobs: list[StoredJob], employment_type: EmploymentType) -> list[StoredJob]:
    """Return the bounded newest-first preview for one opportunity type."""
    return sorted(
        (job for job in jobs if job.employment_type == employment_type),
        key=lambda job: (job.first_seen_at, job.linkedin_job_id),
        reverse=True,
    )[:README_PREVIEW_LIMIT]


def markdown_table(jobs: list[StoredJob], *, locale: ReadmeLocale = LOCALES["en"]) -> str:
    """Localize table labels without translating or altering supplied listing values."""
    lines = [locale.table_header.rstrip("\n")]
    for job in jobs:
        lines.append(
            "| "
            + " | ".join(
                (
                    _escape(job.company),
                    _escape(job.title),
                    _escape(job.location),
                    f"[{locale.view}](<{_safe_url(job.link)}>)",
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
    locale = locale_for_path(path)
    errors: list[str] = []
    try:
        begin, end = _marker_bounds(content)
        summary_begin, summary_end = _marker_bounds(
            content, SUMMARY_BEGIN_MARKER, SUMMARY_END_MARKER
        )
        if not (summary_end < begin or end < summary_begin):
            raise ValueError("README generated regions must not overlap")
    except ValueError as exc:
        errors.append(str(exc))
        return errors
    block = content[begin + len(BEGIN_MARKER) : end].strip()
    summary = content[summary_begin + len(SUMMARY_BEGIN_MARKER) : summary_end].strip()
    seal_lines = [line for line in summary.splitlines() if line.startswith(STATE_SEAL_PREFIX)]
    if (
        content.count(STATE_SEAL_PREFIX) != 1
        or len(seal_lines) != 1
        or STATE_SEAL_PATTERN.fullmatch(seal_lines[0]) is None
    ):
        errors.append("README public directory state seal is missing or malformed")
    if jobs is not None and metadata is not None:
        internship_count, new_grad_count = _type_counts(jobs)
        expected_summary = (
            opportunity_count_cards(
                metadata.open_positions,
                internship_count,
                new_grad_count,
                metadata.last_successful_collection,
                locale=locale,
            )
            + _directory_state_seal(jobs, metadata.last_successful_collection)
        ).strip()
        if summary != expected_summary:
            errors.append("README opportunity counts or directory state seal do not match SQLite")
    if locale.table_header.strip() not in block:
        errors.append("README position tables must have " + ", ".join(locale.columns) + " columns")
    if (
        jobs is not None
        and metadata is not None
        and block != markdown_block(jobs, metadata, locale=locale).strip()
    ):
        errors.append("README opportunity block does not match open jobs and metadata in SQLite")
    for translation in _translation_paths(path):
        errors.extend(
            f"{translation.name}: {error}" for error in validate_readme(translation, jobs, metadata)
        )
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
