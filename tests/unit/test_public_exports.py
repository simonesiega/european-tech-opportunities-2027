from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator

from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import StoredJob
from opportunities.public_exports import (
    CSV_FILENAME,
    JSON_FILENAME,
    METADATA_FILENAME,
    PUBLIC_EXPORT_FIELDS,
    SCHEMA_VERSION,
    _schema_path,
    render_public_exports,
    validate_public_exports,
)


def stored_job(index: int, first_seen_at: datetime) -> StoredJob:
    return StoredJob(
        linkedin_job_id=str(1_000_000_000 + index),
        company=f"Company {index}",
        title=f"Software Engineer 2027 #{index}",
        location="Zürich, Switzerland",
        link=f"https://www.linkedin.com/jobs/view/{1_000_000_000 + index}",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        industries="Software Development",
        employment_type=EmploymentType.INTERNSHIP,
        start_date="Summer 2027",
        first_seen_at=first_seen_at,
        last_seen_at=first_seen_at,
        updated_at=first_seen_at,
        status=JobStatus.OPEN,
    )


def test_public_exports_include_only_approved_fields_in_stable_order(tmp_path: Path) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    jobs = [
        stored_job(1, now),
        stored_job(2, now + timedelta(minutes=1)),
        stored_job(3, now + timedelta(minutes=2)).model_copy(update={"status": JobStatus.CLOSED}),
    ]

    assert validate_public_exports(tmp_path, jobs) == [
        f"public export is missing: {CSV_FILENAME}",
        f"public export is missing: {JSON_FILENAME}",
        f"public export is missing: {METADATA_FILENAME}",
    ]

    render_public_exports(tmp_path, jobs)

    json_rows = json.loads((tmp_path / JSON_FILENAME).read_text(encoding="utf-8"))
    assert [row["linkedin_job_id"] for row in json_rows] == ["1000000002", "1000000001"]
    assert tuple(json_rows[0]) == PUBLIC_EXPORT_FIELDS
    assert "first_seen_at" not in json_rows[0]
    assert "status" not in json_rows[0]
    assert "Zürich" in json_rows[0]["location"]

    with (tmp_path / CSV_FILENAME).open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert tuple(csv_rows[0]) == PUBLIC_EXPORT_FIELDS
    assert [row["linkedin_job_id"] for row in csv_rows] == ["1000000002", "1000000001"]
    metadata = json.loads((tmp_path / METADATA_FILENAME).read_text(encoding="utf-8"))
    assert metadata["schema_version"] == SCHEMA_VERSION
    assert (metadata["total"], metadata["internship_count"], metadata["new_grad_count"]) == (
        2,
        2,
        0,
    )
    datetime.fromisoformat(metadata["generated_at"])
    for filename, key in ((CSV_FILENAME, "csv_sha256"), (JSON_FILENAME, "json_sha256")):
        assert metadata[key] == hashlib.sha256((tmp_path / filename).read_bytes()).hexdigest()
    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json_rows)
    assert tuple(schema["$defs"]["jsonRow"]["properties"]) == PUBLIC_EXPORT_FIELDS
    assert schema["$defs"]["csvDataset"]["properties"]["header"]["const"] == list(
        PUBLIC_EXPORT_FIELDS
    )
    assert validate_public_exports(tmp_path, jobs) == []


def test_public_csv_neutralizes_formulas_and_validation_detects_stale_files(
    tmp_path: Path,
) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    job = stored_job(1, now).model_copy(update={"company": "=DANGEROUS()"})

    render_public_exports(tmp_path, [job])

    with (tmp_path / CSV_FILENAME).open(encoding="utf-8", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["company"] == "'=DANGEROUS()"
    assert json.loads((tmp_path / JSON_FILENAME).read_text(encoding="utf-8"))[0]["company"] == (
        "=DANGEROUS()"
    )

    (tmp_path / JSON_FILENAME).write_text("[]\n", encoding="utf-8")
    errors = validate_public_exports(tmp_path, [job])
    assert f"public export does not match open jobs in SQLite: {JSON_FILENAME}" in errors
    assert "public dataset metadata counts or hashes do not match exports" in errors


def test_export_schema_and_metadata_validation_rejects_tampering(tmp_path: Path) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    jobs = [stored_job(1, now).model_copy(update={"employment_type": EmploymentType.NEW_GRAD})]
    render_public_exports(tmp_path, jobs)
    metadata_path = tmp_path / METADATA_FILENAME
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["new_grad_count"] == 1
    metadata["total"] = 2
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert (
        "public dataset metadata counts or hashes do not match exports"
        in validate_public_exports(tmp_path, jobs)
    )

    metadata["total"] = 1
    metadata["internship_count"] = 1
    metadata["generated_at"] = "2026-07-15T10:00:00+02:00"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert f"public dataset metadata is invalid: {METADATA_FILENAME}" in validate_public_exports(
        tmp_path, jobs
    )

    render_public_exports(tmp_path, jobs)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["internship_count"] = 1  # Each count fits the schema, but their sum is stale.
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert (
        "public dataset metadata counts or hashes do not match exports"
        in validate_public_exports(tmp_path, jobs)
    )

    render_public_exports(tmp_path, jobs)
    json_path = tmp_path / JSON_FILENAME
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    rows[0]["private_field"] = "leak"
    json_path.write_text(json.dumps(rows), encoding="utf-8")
    assert f"public export does not conform to {SCHEMA_VERSION} schema" in validate_public_exports(
        tmp_path, jobs
    )

    render_public_exports(tmp_path, jobs)
    csv_path = tmp_path / CSV_FILENAME
    csv_path.write_text("wrong,header\n1,2\n", encoding="utf-8")
    assert (
        f"public export does not conform to {SCHEMA_VERSION} CSV contract"
        in validate_public_exports(tmp_path, jobs)
    )

    render_public_exports(tmp_path, [])
    assert validate_public_exports(tmp_path, []) == []
    assert json.loads(metadata_path.read_text(encoding="utf-8"))["total"] == 0


def test_documented_examples_match_all_three_v1_contracts() -> None:
    root = _schema_path().parents[1]
    schema = json.loads(_schema_path().read_text(encoding="utf-8"))
    assert schema["$id"] == "https://techopportunities.eu/schemas/opportunities-v1.schema.json"
    examples = root / "schemas" / "examples"
    guide = (root / "docs/guides/user-guide/public-dataset.md").read_text(encoding="utf-8")

    def shown_example(heading: str, language: str) -> str:
        match = re.search(
            rf"^## {heading}\n.*?^```{language}\n(.*?)^```",
            guide,
            flags=re.MULTILINE | re.DOTALL,
        )
        assert match is not None
        return match.group(1)

    json_rows = json.loads((examples / "open-opportunities-v1.json").read_text(encoding="utf-8"))
    assert Draft202012Validator(schema).is_valid(json_rows)
    assert json.loads(shown_example("JSON download", "json")) == json_rows

    csv_content = (examples / "open-opportunities-v1.csv").read_text(encoding="utf-8")
    parsed = list(csv.reader(csv_content.splitlines(keepends=True), strict=True))
    csv_contract = {"$defs": schema["$defs"], "$ref": "#/$defs/csvDataset"}
    assert Draft202012Validator(csv_contract).is_valid({"header": parsed[0], "rows": parsed[1:]})
    assert shown_example("CSV download", "csv") == csv_content
    assert [dict(zip(parsed[0], cells, strict=True)) for cells in parsed[1:]] == [
        {field: "" if row[field] is None else row[field] for field in PUBLIC_EXPORT_FIELDS}
        for row in json_rows
    ]

    api = json.loads((examples / "api-opportunities-v1.json").read_text(encoding="utf-8"))
    api_contract = {"$defs": schema["$defs"], "$ref": "#/$defs/apiResponse"}
    assert Draft202012Validator(api_contract).is_valid(api)
    assert json.loads(shown_example("API response", "json")) == api
    assert api["pagination"]["total"] == len(json_rows) == len(api["data"])
    assert [
        {
            "linkedin_job_id": row["linkedinJobId"],
            "company": row["company"],
            "title": row["title"],
            "location": row["location"],
            "link": row["link"],
            "category": row["category"],
            "industries": row["industries"],
            "employment_type": row["employmentType"],
            "start_date": row["startDate"],
        }
        for row in api["data"]
    ] == json_rows

    metadata = json.loads((examples / "dataset-metadata-v1.json").read_text(encoding="utf-8"))
    metadata_contract = {"$defs": schema["$defs"], "$ref": "#/$defs/metadata"}
    assert Draft202012Validator(metadata_contract).is_valid(metadata)
    assert metadata["schema_version"] == SCHEMA_VERSION
    assert metadata["total"] == len(json_rows)
    assert metadata["internship_count"] == sum(
        row["employment_type"] == EmploymentType.INTERNSHIP for row in json_rows
    )
    assert metadata["new_grad_count"] == sum(
        row["employment_type"] == EmploymentType.NEW_GRAD for row in json_rows
    )
    assert (
        metadata["json_sha256"]
        == hashlib.sha256((examples / "open-opportunities-v1.json").read_bytes()).hexdigest()
    )
    assert (
        metadata["csv_sha256"]
        == hashlib.sha256((examples / "open-opportunities-v1.csv").read_bytes()).hexdigest()
    )
