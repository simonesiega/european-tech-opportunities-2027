"""Create disposable website fixtures through real migrations, repository and exporters.

Never reads local settings, .env, or canonical data. The destination is fixed under
ignored test output so a test command cannot overwrite an operator-selected database.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from opportunities.config.settings import Settings
from opportunities.database.migrations import upgrade_database
from opportunities.database.repository import Repository
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.public_exports import render_public_exports, validate_public_exports
from opportunities.utils.time import utc_now

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIRECTORY = ROOT / "site" / "tests" / "e2e" / ".tmp"
COLLECTION_TIME = datetime(2026, 7, 17, 12, tzinfo=UTC)


def create_fixture(*, now: datetime, demo: bool = False) -> Path:
    directory = FIXTURE_DIRECTORY / "demo" if demo else FIXTURE_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    database = directory / "opportunities.db"
    # Fail rather than deleting sidecars from an unexpectedly active fixture writer.
    if any(Path(f"{database}{suffix}").exists() for suffix in ("-wal", "-shm", "-journal")):
        raise ValueError("Close the fixture database before regenerating it")
    database.unlink(missing_ok=True)
    settings = Settings(database_url=f"sqlite:///{database.as_posix()}")
    upgrade_database(settings.database_url, repository_root=ROOT)
    engine = create_database_engine(settings.database_url)
    repository = Repository(create_session_factory(engine), settings)
    rows = [
        (
            "Acme Labs",
            "Software Engineering Intern 2027",
            "Berlin, Germany",
            OpportunityCategory.SOFTWARE_ENGINEERING,
            "Software Development",
            EmploymentType.INTERNSHIP,
            "June 2027",
            40 * 24,
        ),
        (
            "Acme Labs",
            "Cybersecurity Intern 2027",
            "Dublin, Ireland",
            OpportunityCategory.CYBERSECURITY,
            "Computer and Network Security",
            EmploymentType.INTERNSHIP,
            None,
            20 * 24,
        ),
        (
            "Northstar Data",
            "Graduate Data Analyst 2027",
            "Paris, France",
            OpportunityCategory.DATA_SCIENCE,
            "Information Technology",
            EmploymentType.NEW_GRAD,
            "Summer 2027",
            8 * 24,
        ),
    ]
    demo_companies = [
        "Lumen Cloud",
        "Atlas Systems",
        "Orbit Software",
        "Helix Labs",
        "Juniper Digital",
        "Meridian Tech",
        "Aurora Computing",
        "Cobalt Systems",
        "Nova Engineering",
    ]
    for index, age in enumerate(
        [28 * 24, 14 * 24, 6 * 24, 5 * 24, 4 * 24, 3 * 24, 2 * 24, 12, 2], 1
    ):
        rows.append(
            (
                demo_companies[index - 1] if demo else f"Example {index:02d}",
                f"Platform Engineering Intern {index}",
                "Madrid, Spain; Lisbon, Portugal" if index == 1 else "Madrid, Spain",
                OpportunityCategory.SOFTWARE_ENGINEERING,
                "Software Development",
                EmploymentType.INTERNSHIP,
                None,
                age,
            )
        )
    jobs = [
        DiscoveredJob(
            linkedin_job_id=str(1000000001 + index),
            company=company,
            title=title,
            location=location,
            link=f"https://www.linkedin.com/jobs/view/{1000000001 + index}",
            category=category,
            industries=industries,
            employment_type=employment_type,
            start_date=start_date,
            posted_at=now - timedelta(hours=age),
        )
        for index, (
            company,
            title,
            location,
            category,
            industries,
            employment_type,
            start_date,
            age,
        ) in enumerate(rows)
    ]
    try:
        for offset in range(0, len(jobs), 10):
            repository.upsert_manual_jobs(jobs[offset : offset + 10], observed_at=now)
        search = LinkedInSearchConfig(
            name="Synthetic fixture", slug="synthetic-fixture", keywords="intern", location="Europe"
        )
        repository.sync_searches([search], COLLECTION_TIME)
        repository.persist_success(
            run_id="fixture-success",
            search=search,
            jobs=[],
            confirmed_unavailable_ids=(),
            found_count=0,
            excluded_count=0,
            warning_count=0,
            started_at=COLLECTION_TIME,
            finished_at=COLLECTION_TIME,
            duration_ms=0,
        )
        # A newer failed run must not advance the website's last-successful collection date.
        failed_at = COLLECTION_TIME + timedelta(days=2)
        repository.persist_failure(
            run_id="fixture-failure",
            search_slug=search.slug,
            started_at=failed_at,
            finished_at=failed_at,
            duration_ms=0,
            error_code="fixture",
            error_message="Synthetic failure",
        )
        open_jobs = repository.list_open_jobs()
        render_public_exports(directory, open_jobs)
        errors = validate_public_exports(directory, open_jobs)
        if errors:
            raise ValueError("; ".join(errors))
    finally:
        engine.dispose()
    return database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Fixed-clock promotional fixture")
    args = parser.parse_args()
    now = datetime(2026, 9, 28, 12, tzinfo=UTC) if args.demo else utc_now()
    create_fixture(now=now, demo=args.demo)


if __name__ == "__main__":
    main()
