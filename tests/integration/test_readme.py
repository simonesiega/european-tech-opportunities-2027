from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from opportunities.models.enums import EmploymentType, JobStatus, OpportunityCategory
from opportunities.models.job import StoredJob
from opportunities.public_exports import PUBLIC_EXPORT_FIELDS, directory_state_rows
from opportunities.readme import (
    BEGIN_MARKER,
    END_MARKER,
    SUMMARY_BEGIN_MARKER,
    SUMMARY_END_MARKER,
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


@pytest.mark.parametrize("filename", ["README.md", "it.md", "README.ja.md"])
def test_readme_contains_type_sections_and_escapes_values(tmp_path: Path, filename: str) -> None:
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

    readme = tmp_path / filename
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


@pytest.fixture
def readme_projections(tmp_path: Path) -> tuple[Path, list[Path]]:
    root = tmp_path / "README.md"
    directory = tmp_path / "docs/translations"
    directory.mkdir(parents=True)
    translations = [
        directory / f"README.{language}.md" for language in ("it", "fr", "de", "es", "zh-CN")
    ]
    for path in (root, *translations):
        path.write_text(
            f"# Authored {path.name}\n\nPréface · 项目简介\n"
            f"{SUMMARY_BEGIN_MARKER}\nold counts\n{SUMMARY_END_MARKER}\n"
            f"## Preview\n{BEGIN_MARKER}\nold preview\n{END_MARKER}\n"
            "## Authored footer\nKeep this text.\n",
            encoding="utf-8",
        )
    return root, translations


def test_readme_render_preserves_authored_text_and_updates_translations(
    readme_projections: tuple[Path, list[Path]],
) -> None:
    readme, translations = readme_projections
    originals = {path: path.read_text(encoding="utf-8") for path in (readme, *translations)}
    now = datetime(2026, 7, 15, tzinfo=UTC)
    jobs = [
        stored_job(1, EmploymentType.INTERNSHIP, now),
        stored_job(2, EmploymentType.NEW_GRAD, now),
    ]
    metadata = ReadmeMetadata(2, now)

    render_readme(readme, jobs, metadata)

    assert validate_readme(readme, jobs, metadata) == []
    for path, original in originals.items():
        updated = path.read_text(encoding="utf-8")
        for begin, end in (
            (SUMMARY_BEGIN_MARKER, SUMMARY_END_MARKER),
            (BEGIN_MARKER, END_MARKER),
        ):
            pattern = re.escape(begin) + ".*?" + re.escape(end)
            original = re.sub(pattern, "", original, flags=re.DOTALL)
            updated = re.sub(pattern, "", updated, flags=re.DOTALL)
        assert updated == original
    rendered = {path: path.read_bytes() for path in originals}
    render_readme(readme, jobs, metadata)
    assert {path: path.read_bytes() for path in originals} == rendered


@pytest.mark.parametrize("region", ["counts", "preview"])
def test_readme_validation_reports_stale_translation(
    readme_projections: tuple[Path, list[Path]], region: str
) -> None:
    readme, translations = readme_projections
    now = datetime(2026, 7, 15, tzinfo=UTC)
    jobs = [stored_job(1, EmploymentType.INTERNSHIP, now)]
    metadata = ReadmeMetadata(1, now)
    render_readme(readme, jobs, metadata)
    stale = translations[-1]
    old, new = ("-1-2563eb", "-9-2563eb") if region == "counts" else ("Company 1", "Stale")
    stale.write_text(stale.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    before = {path: path.read_bytes() for path in (readme, *translations)}

    errors = validate_readme(readme, jobs, metadata)

    assert len(errors) == 1
    assert errors[0].startswith(f"{stale.name}:")
    assert ("counts" if region == "counts" else "opportunity block") in errors[0]
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("failure", ["missing", "duplicate", "reversed", "overlap"])
def test_translation_preflight_failure_preserves_all_projections(
    readme_projections: tuple[Path, list[Path]], failure: str
) -> None:
    readme, translations = readme_projections
    invalid = translations[-1]
    text = invalid.read_text(encoding="utf-8")
    if failure == "missing":
        invalid.unlink()
    else:
        if failure == "duplicate":
            text += BEGIN_MARKER
        elif failure == "reversed":
            text = (
                text.replace(BEGIN_MARKER, "temporary")
                .replace(END_MARKER, BEGIN_MARKER)
                .replace("temporary", END_MARKER)
            )
        else:
            text = f"{SUMMARY_BEGIN_MARKER}\n{BEGIN_MARKER}\n{SUMMARY_END_MARKER}\n{END_MARKER}\n"
        invalid.write_text(text, encoding="utf-8")
    before = {path: path.read_bytes() for path in (readme, *translations) if path.exists()}

    with pytest.raises(ValueError, match=r"does not exist|marker|overlap"):
        render_readme(readme, [], ReadmeMetadata(0, None))

    assert {path: path.read_bytes() for path in before} == before
    assert any(
        error.startswith(f"{invalid.name}:")
        for error in validate_readme(readme, [], ReadmeMetadata(0, None))
    )
    if failure == "missing":
        assert not invalid.exists()


@pytest.mark.parametrize(
    ("language", "timestamp", "header", "view", "never"),
    [
        (
            "en",
            "December 31, 2026 at 23:05 UTC",
            "| Company | Title | Location | Listing |",
            "View",
            "Never",
        ),
        (
            "it",
            "31 dicembre 2026 alle 23:05 UTC",
            "| Azienda | Posizione | Località | Annuncio |",
            "Apri",
            "Mai",
        ),
        (
            "fr",
            "31 décembre 2026 à 23 h 05 UTC",
            "| Entreprise | Intitulé du poste | Localisation | Annonce |",
            "Voir l\u2019offre",
            "Jamais",
        ),
        (
            "de",
            "31. Dezember 2026 um 23:05 UTC",
            "| Unternehmen | Position | Standort | Anzeige |",
            "Ansehen",
            "Nie",
        ),
        (
            "es",
            "31 de diciembre de 2026 a las 23:05 UTC",
            "| Empresa | Puesto | Ubicación | Anuncio |",
            "Ver oferta",
            "Nunca",
        ),
        (
            "zh-CN",
            "2026 年 12 月 31 日 23:05\uff08UTC\uff09",
            "| 公司 | 职位名称 | 地点 | 原始公告 |",
            "查看",
            "从未",
        ),
    ],
)
@pytest.mark.parametrize("empty", [False, True])
def test_localized_rendering_preserves_canonical_data_and_formats_utc(
    tmp_path: Path, language: str, timestamp: str, header: str, view: str, never: str, empty: bool
) -> None:
    now = datetime(2027, 1, 1, 1, 5, tzinfo=timezone(timedelta(hours=2)))
    jobs = (
        []
        if empty
        else [
            stored_job(index + offset, employment_type, now)
            for employment_type, offset in (
                (EmploymentType.INTERNSHIP, 0),
                (EmploymentType.NEW_GRAD, 100),
            )
            for index in range(6)
        ]
    )
    if jobs:
        jobs[-1] = jobs[-1].model_copy(
            update={"company": "Example | <Company>", "title": "Software [Engineer] 2027"}
        )
    metadata = ReadmeMetadata(len(jobs), None if empty else now)
    path = tmp_path / ("README.md" if language == "en" else f"README.{language}.md")
    path.write_text(
        f"# Authored\n{SUMMARY_BEGIN_MARKER}\nold\n{SUMMARY_END_MARKER}\n"
        f"{BEGIN_MARKER}\nold\n{END_MARKER}\nFooter\n",
        encoding="utf-8",
    )

    render_readme(path, jobs, metadata)
    content = path.read_text(encoding="utf-8")

    assert validate_readme(path, jobs, metadata) == []
    assert content.count(never if empty else timestamp) == 2
    assert content.count(header) == 2
    assert re.findall(r"https://img\.shields\.io/badge/[^\n\"]+?-(\d+)-[0-9a-f]{6}", content) == (
        ["0", "0", "0"] if empty else ["12", "6", "6"]
    )
    ids = re.findall(r"https://www\.linkedin\.com/jobs/view/(\d+)", content)
    assert ids == (
        []
        if empty
        else [str(1_000_000_000 + index) for index in (105, 104, 103, 102, 101, 5, 4, 3, 2, 1)]
    )
    assert directory_state_digest(jobs, metadata.last_successful_collection) in content
    if jobs:
        assert f"[{view}](<https://www.linkedin.com/jobs/view/1000000105>)" in content
        assert r"Example \| &lt;Company&gt;" in content
        assert r"Software \[Engineer\] 2027" in content


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

    # Only the seal can detect this edit: the row is outside the five-row preview.
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
    # Internal lifecycle updates must not churn a seal of public state.
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
