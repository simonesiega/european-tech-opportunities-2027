"""Deterministic public CSV and JSON projections of open opportunities."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from opportunities.models.enums import JobStatus
from opportunities.models.job import StoredJob
from opportunities.utils.files import atomic_write_text
from opportunities.utils.time import ensure_utc

CSV_FILENAME = "open-opportunities.csv"
JSON_FILENAME = "open-opportunities.json"
PUBLIC_EXPORT_FIELDS = (
    "linkedin_job_id",
    "company",
    "title",
    "location",
    "link",
    "category",
    "industries",
    "employment_type",
    "start_date",
)


def render_public_exports(directory: Path, jobs: list[StoredJob]) -> None:
    """Atomically replace sanitized public exports derived from open SQLite rows."""
    directory.mkdir(parents=True, exist_ok=True)
    rows = _public_rows(jobs)
    atomic_write_text(directory / CSV_FILENAME, _csv_content(rows))
    atomic_write_text(directory / JSON_FILENAME, _json_content(rows))


def validate_public_exports(directory: Path, jobs: list[StoredJob]) -> list[str]:
    """Return projection errors without mutating export files."""
    rows = _public_rows(jobs)
    expected = {
        CSV_FILENAME: _csv_content(rows),
        JSON_FILENAME: _json_content(rows),
    }
    errors: list[str] = []
    for filename, expected_content in expected.items():
        path = directory / filename
        if not path.is_file():
            errors.append(f"public export is missing: {filename}")
            continue
        try:
            actual_content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append(f"public export could not be read: {filename}")
            continue
        if actual_content != expected_content:
            errors.append(f"public export does not match open jobs in SQLite: {filename}")
    return errors


def _public_rows(jobs: list[StoredJob]) -> list[dict[str, str | None]]:
    """Project directory rows to the smaller public-download allowlist."""
    return [
        {field: row[field] for field in PUBLIC_EXPORT_FIELDS} for row in directory_state_rows(jobs)
    ]


def directory_state_rows(jobs: list[StoredJob]) -> list[dict[str, str | None]]:
    """Select website-visible open fields in deterministic publication order."""
    ordered = sorted(
        (job for job in jobs if job.status == JobStatus.OPEN),
        key=lambda job: (job.first_seen_at, job.linkedin_job_id),
        reverse=True,
    )
    return [
        {
            "linkedin_job_id": job.linkedin_job_id,
            "company": job.company,
            "title": job.title,
            "location": job.location,
            "link": job.link,
            "category": job.category.value,
            "industries": job.industries,
            "employment_type": job.employment_type.value,
            "start_date": job.start_date,
            "first_seen_at": ensure_utc(job.first_seen_at).isoformat(timespec="microseconds"),
        }
        for job in ordered
    ]


def _csv_content(rows: Sequence[Mapping[str, str | None]]) -> str:
    """Serialize rows as UTF-8 CSV while neutralizing spreadsheet formulas."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=PUBLIC_EXPORT_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: _safe_csv_cell(row[field]) for field in PUBLIC_EXPORT_FIELDS})
    return output.getvalue()


def _json_content(rows: Sequence[Mapping[str, str | None]]) -> str:
    """Serialize public rows as stable UTF-8 JSON."""
    return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"


def _safe_csv_cell(value: str | None) -> str:
    """Prevent public text from becoming a spreadsheet formula when opened."""
    if value is None:
        return ""
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{value}"
    return value
