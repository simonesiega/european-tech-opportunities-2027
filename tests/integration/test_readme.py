from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import StoredJob
from opportunities.public_exports import PUBLIC_EXPORT_FIELDS, directory_state_rows
from opportunities.readme import (
    ReadmeMetadata,
    directory_state_digest,
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
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
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
    assert "**Open opportunities:** 1 (Internships: 1 · New Grad: 0)" in block
    assert "**Last successful collection:** July 15, 2026 at 00:00 UTC" in block
    assert "### Latest New Grad opportunities" in block
    assert "### Latest internships" in block
    assert "Showing the 1 most recently discovered of 1 open internships" in block
    assert "Category" not in table
    assert "Example \\| Technology" in table

    readme = tmp_path / "README.md"
    readme.write_text(
        "# Test\n\n<!-- BEGIN OPPORTUNITY COUNTS -->\nold\n"
        "<!-- END OPPORTUNITY COUNTS -->\n\n<!-- BEGIN OPPORTUNITIES -->\nold\n"
        "<!-- END OPPORTUNITIES -->\n",
        encoding="utf-8",
    )
    render_readme(readme, [job], metadata)
    rendered = readme.read_text(encoding="utf-8")
    assert "old" not in rendered
    assert "Last successful collection: July 15, 2026 at 00:00 UTC" in rendered
    assert validate_readme(readme) == []
    assert validate_readme(readme, [job], metadata) == []


def test_readme_preview_is_bounded_to_five_opportunities_per_type() -> None:
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

    assert "Showing the 5 most recently discovered of 12 open internships" in block
    assert "Showing the 5 most recently discovered of 12 open New Grad opportunities" in block
    assert "| Company 11 |" in block
    assert "| Company 111 |" in block
    assert "| Company 6 |" not in block
    assert "| Company 106 |" not in block


def test_review_seal_detects_changes_beyond_preview_and_exact_timestamps(tmp_path: Path) -> None:
    now = datetime(2026, 7, 15, 12, 30, 0, 123456, tzinfo=UTC)
    jobs = [
        stored_job(index, EmploymentType.INTERNSHIP, now + timedelta(minutes=index))
        for index in range(7)
    ]
    metadata = ReadmeMetadata(open_positions=7, last_successful_collection=now)
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Test\n\n<!-- BEGIN OPPORTUNITY COUNTS -->\nold\n"
        "<!-- END OPPORTUNITY COUNTS -->\n\n<!-- BEGIN OPPORTUNITIES -->\nold\n"
        "<!-- END OPPORTUNITIES -->\n",
        encoding="utf-8",
    )

    render_readme(readme, jobs, metadata)
    original = readme.read_text(encoding="utf-8")
    assert re.search(r"</p>\n<!-- Public directory state v1 sha256: [0-9a-f]{64} -->\n", original)
    assert "| Company 0 |" not in original
    assert validate_readme(readme, jobs, metadata) == []
    assert tuple(directory_state_rows(jobs)[0]) == (*PUBLIC_EXPORT_FIELDS, "first_seen_at")

    changed_jobs = [jobs[0].model_copy(update={"company": "Corrected Company"}), *jobs[1:]]
    assert markdown_block(changed_jobs, metadata) == markdown_block(jobs, metadata)
    assert validate_readme(readme, changed_jobs, metadata) == [
        "README opportunity counts or directory state seal do not match SQLite"
    ]
    render_readme(readme, changed_jobs, metadata)
    assert readme.read_text(encoding="utf-8") != original
    assert validate_readme(readme, changed_jobs, metadata) == []

    changed_first_seen = [
        jobs[0].model_copy(update={"first_seen_at": jobs[0].first_seen_at + timedelta(seconds=1)}),
        *jobs[1:],
    ]
    assert directory_state_digest(changed_first_seen, now) != directory_state_digest(jobs, now)
    assert directory_state_digest(jobs, now + timedelta(microseconds=1)) != (
        directory_state_digest(jobs, now)
    )
    lifecycle_only = [
        jobs[0].model_copy(
            update={
                "last_seen_at": now + timedelta(days=1),
                "updated_at": now + timedelta(days=1),
                "posted_at": now - timedelta(days=1),
            }
        ),
        *jobs[1:],
    ]
    assert directory_state_digest(lifecycle_only, now) == directory_state_digest(jobs, now)

    malformed = readme.read_text(encoding="utf-8").replace(
        "<!-- Public directory state v1 sha256: ",
        "<!-- Public directory state v1 sha256: INVALID-",
    )
    readme.write_text(malformed, encoding="utf-8")
    assert validate_readme(readme) == ["README public directory state seal is missing or malformed"]


def test_readme_rejects_reversed_generated_markers(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Test\n\n<!-- BEGIN OPPORTUNITY COUNTS -->\nold\n"
        "<!-- END OPPORTUNITY COUNTS -->\n\n<!-- END OPPORTUNITIES -->\nold\n"
        "<!-- BEGIN OPPORTUNITIES -->\n",
        encoding="utf-8",
    )

    assert validate_readme(readme) == ["README opportunity markers are out of order"]
    with pytest.raises(ValueError, match="out of order"):
        render_readme(readme, [], ReadmeMetadata(0, None))


def test_empty_database_still_renders_both_table_headers() -> None:
    assert markdown_table([]) == "| Company | Title | Location | Listing |\n|---|---|---|---|\n"
    block = markdown_block([], ReadmeMetadata(0, None))
    assert block.startswith(
        "**Open opportunities:** 0 (Internships: 0 · New Grad: 0)<br>\n"
        "**Last successful collection:** Never\n\n"
    )
    assert block.count("| Company | Title | Location | Listing |") == 2
