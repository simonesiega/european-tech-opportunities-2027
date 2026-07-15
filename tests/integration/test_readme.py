from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from internships.models.enums import InternshipCategory, JobStatus
from internships.models.job import StoredJob
from internships.readme import (
    ReadmeMetadata,
    markdown_block,
    markdown_table,
    render_readme,
    validate_readme,
)


def test_readme_contains_exactly_four_columns_and_escapes_values(tmp_path: Path) -> None:
    now = datetime(2026, 7, 15, tzinfo=UTC)
    job = StoredJob(
        linkedin_job_id="1111111111",
        company="Example | Technology",
        title="Software [Engineering] Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=InternshipCategory.SOFTWARE_ENGINEERING,
        first_seen_at=now,
        last_seen_at=now,
        updated_at=now,
        status=JobStatus.OPEN,
    )
    metadata = ReadmeMetadata(open_internships=1, last_successful_collection=now)
    table = markdown_table([job])
    block = markdown_block([job], metadata)
    assert table.startswith("| Company | Title | Location | Link |\n|---|---|---|---|\n")
    assert "**Open internships:** 1" in block
    assert "**Last successful collection:** July 15, 2026 at 00:00 UTC" in block
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


def test_empty_database_still_renders_table_header() -> None:
    assert markdown_table([]) == "| Company | Title | Location | Link |\n|---|---|---|---|\n"
    assert markdown_block([], ReadmeMetadata(0, None)).startswith(
        "**Open internships:** 0<br>\n**Last successful collection:** Never\n\n"
    )
