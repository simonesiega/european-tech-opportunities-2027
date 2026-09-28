"""Deterministic public CSV and JSON projections of open opportunities."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from opportunities.models.enums import EmploymentType, JobStatus
from opportunities.models.job import StoredJob
from opportunities.utils.files import atomic_write_text
from opportunities.utils.time import ensure_utc, utc_now

CSV_FILENAME = "open-opportunities.csv"
JSON_FILENAME = "open-opportunities.json"
METADATA_FILENAME = "dataset-metadata.json"
SCHEMA_VERSION = "v1"
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
    csv_content = _csv_content(rows)
    json_content = _json_content(rows)
    atomic_write_text(directory / CSV_FILENAME, csv_content)
    atomic_write_text(directory / JSON_FILENAME, json_content)
    atomic_write_text(
        directory / METADATA_FILENAME,
        _metadata_content(rows, csv_content.encode("utf-8"), json_content.encode("utf-8")),
    )


def validate_public_exports(directory: Path, jobs: list[StoredJob]) -> list[str]:
    """Return projection errors without mutating export files."""
    rows = _public_rows(jobs)
    expected = {
        CSV_FILENAME: _csv_content(rows),
        JSON_FILENAME: _json_content(rows),
    }
    errors: list[str] = []
    actual: dict[str, bytes] = {}
    for filename, expected_content in expected.items():
        path = directory / filename
        if not path.is_file():
            errors.append(f"public export is missing: {filename}")
            continue
        try:
            content = path.read_bytes()
            actual_content = content.decode("utf-8")
        except (OSError, UnicodeError):
            errors.append(f"public export could not be read: {filename}")
            continue
        actual[filename] = content
        if actual_content != expected_content:
            errors.append(f"public export does not match open jobs in SQLite: {filename}")

    validator: Draft202012Validator | None = None
    try:
        schema = json.loads(_schema_path().read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
    except (ValueError, OSError, UnicodeError, SchemaError):
        errors.append("public dataset schema is unavailable or invalid")
    else:
        if JSON_FILENAME in actual:
            try:
                document = json.loads(actual[JSON_FILENAME])
                if not validator.is_valid(document):
                    errors.append(f"public export does not conform to {SCHEMA_VERSION} schema")
            except (ValueError, UnicodeError):
                errors.append(f"public export is not valid JSON: {JSON_FILENAME}")
        if CSV_FILENAME in actual:
            try:
                with io.StringIO(actual[CSV_FILENAME].decode("utf-8"), newline="") as stream:
                    parsed = list(csv.reader(stream, strict=True))
                csv_document = {"header": parsed[0], "rows": parsed[1:]}
                csv_contract = {"$ref": "#/$defs/csvDataset", "$defs": schema["$defs"]}
                if not validator.evolve(schema=csv_contract).is_valid(csv_document):
                    errors.append(
                        f"public export does not conform to {SCHEMA_VERSION} CSV contract"
                    )
            except (UnicodeError, csv.Error, IndexError):
                errors.append(f"public export is not valid CSV: {CSV_FILENAME}")

    metadata_path = directory / METADATA_FILENAME
    if not metadata_path.is_file():
        errors.append(f"public export is missing: {METADATA_FILENAME}")
    else:
        try:
            metadata = json.loads(metadata_path.read_bytes())
            generated = datetime.fromisoformat(metadata["generated_at"])
            if generated.tzinfo is None or generated.utcoffset() != timedelta(0):
                raise ValueError("generated_at must be UTC")
            expected_metadata = _metadata(
                rows,
                actual.get(CSV_FILENAME, b""),
                actual.get(JSON_FILENAME, b""),
                generated_at=metadata["generated_at"],
            )
            if validator is not None:
                metadata_contract = {"$ref": "#/$defs/metadata", "$defs": schema["$defs"]}
                if not validator.evolve(schema=metadata_contract).is_valid(metadata):
                    raise ValueError("metadata does not conform to schema")
            if set(metadata) != set(expected_metadata) or any(
                type(metadata[key]) is not type(value) or metadata[key] != value
                for key, value in expected_metadata.items()
            ):
                errors.append("public dataset metadata counts or hashes do not match exports")
        except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
            errors.append(f"public dataset metadata is invalid: {METADATA_FILENAME}")
    return errors


def _schema_path() -> Path:
    packaged = (
        Path(__file__).resolve().parent / "resources" / "schemas" / "opportunities-v1.schema.json"
    )
    if packaged.is_file():
        return packaged
    return Path(__file__).resolve().parents[2] / "schemas" / "opportunities-v1.schema.json"


def _metadata(
    rows: Sequence[Mapping[str, str | None]],
    csv_bytes: bytes,
    json_bytes: bytes,
    *,
    generated_at: str,
) -> dict[str, str | int]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "total": len(rows),
        "internship_count": sum(
            row["employment_type"] == EmploymentType.INTERNSHIP for row in rows
        ),
        "new_grad_count": sum(row["employment_type"] == EmploymentType.NEW_GRAD for row in rows),
        "json_sha256": hashlib.sha256(json_bytes).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
    }


def _metadata_content(
    rows: Sequence[Mapping[str, str | None]], csv_bytes: bytes, json_bytes: bytes
) -> str:
    return (
        json.dumps(
            _metadata(
                rows, csv_bytes, json_bytes, generated_at=utc_now().isoformat(timespec="seconds")
            ),
            indent=2,
        )
        + "\n"
    )


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
