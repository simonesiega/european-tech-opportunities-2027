from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from internships.models.enums import EmploymentType, InternshipCategory, JobStatus
from internships.models.job import StoredJob
from internships.readme import (
    ReadmeMetadata,
    markdown_block,
    markdown_table,
    render_readme,
    validate_readme,
)


def stored_job(index: int, employment_type: EmploymentType, first_seen_at: datetime) -> StoredJob:
    return StoredJob(
        linkedin_job_id=str(1_000_000_000 + index),
        company=f"Company {index}",
        title=f"Software Engineer 2027 #{index}",
        location="London, UK",
        link=f"https://www.linkedin.com/jobs/view/{1_000_000_000 + index}",
        category=InternshipCategory.SOFTWARE_ENGINEERING,
        employment_type=employment_type,
        first_seen_at=first_seen_at,
        last_seen_at=first_seen_at,
        updated_at=first_seen_at,
        status=JobStatus.OPEN,
    )


def test_readme_contains_type_sections_and_escapes_values(tmp_path: Path) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    job = stored_job(1, EmploymentType.INTERNSHIP, now).model_copy(
        update={
            "company": "Example | Technology",
            "title": "Software [Engineering] Intern 2027",
        }
    )
    metadata = ReadmeMetadata(open_positions=1, last_successful_collection=now)
    table = markdown_table([job])
    block = markdown_block([job], metadata)

    assert table.startswith("| Company | Title | Location | Listing |\n|---|---|---|---|\n")
    assert "**Open positions:** 1 (Internships: 1 · New Grad: 0)" in block
    assert "**Last successful collection:** July 15, 2026 at 00:00 UTC" in block
    assert "### Latest New Grad positions" in block
    assert "### Latest internships" in block
    assert "Showing the 1 most recently discovered of 1 open internships" in block
    assert "Category" not in table
    assert "Example \\| Technology" in table

    readme = tmp_path / "README.md"
    readme.write_text(
        "# Test\n\n<!-- BEGIN INTERNSHIPS -->\nold\n<!-- END INTERNSHIPS -->\n",
        encoding="utf-8",
    )
    render_readme(readme, [job], metadata)
    assert "old" not in readme.read_text(encoding="utf-8")
    assert validate_readme(readme) == []
    assert validate_readme(readme, [job], metadata) == []


def test_readme_preview_is_bounded_to_ten_positions_per_type() -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    internships = [
        stored_job(index, EmploymentType.INTERNSHIP, now + timedelta(minutes=index))
        for index in range(12)
    ]
    new_grad = [
        stored_job(index + 100, EmploymentType.NEW_GRAD, now + timedelta(minutes=index))
        for index in range(12)
    ]

    block = markdown_block(internships + new_grad, ReadmeMetadata(24, now))

    assert "Showing the 10 most recently discovered of 12 open internships" in block
    assert "Showing the 10 most recently discovered of 12 open New Grad positions" in block
    assert "| Company 11 |" in block
    assert "| Company 111 |" in block
    assert "| Company 1 |" not in block
    assert "| Company 101 |" not in block


def test_empty_database_still_renders_both_table_headers() -> None:
    assert markdown_table([]) == "| Company | Title | Location | Listing |\n|---|---|---|---|\n"
    block = markdown_block([], ReadmeMetadata(0, None))
    assert block.startswith(
        "**Open positions:** 0 (Internships: 0 · New Grad: 0)<br>\n"
        "**Last successful collection:** Never\n\n"
    )
    assert block.count("| Company | Title | Location | Listing |") == 2
