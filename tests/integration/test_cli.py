from __future__ import annotations

import asyncio
import json
import logging
import socket
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
import typer
from sqlalchemy import Engine
from typer.testing import CliRunner

import opportunities.cli.app as cli_app_module
import opportunities.pipeline.availability as availability_module
from opportunities.cli.app import app
from opportunities.config.settings import Settings
from opportunities.database.models import JobSearchRow
from opportunities.database.repository import Repository
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.raw import KnownJob, RawJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.availability import AvailabilityAuditResult
from opportunities.scrapers.http import FetchError
from opportunities.scrapers.linkedin import LinkedInScraper, LinkedInScrapeResult, TextFetcher
from opportunities.utils.paths import find_project_root

runner = CliRunner()
ROOT = find_project_root(Path(__file__))


@pytest.fixture(autouse=True)
def fixed_cli_clock_and_logging(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep date validation and CLI logging independent of the host and test order."""
    monkeypatch.setattr(cli_app_module, "utc_now", lambda: datetime(2026, 7, 20, tzinfo=UTC))
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    try:
        yield
    finally:
        for handler in root.handlers:
            if handler not in handlers:
                handler.close()
        root.handlers[:] = handlers
        root.setLevel(level)


def cli_env(tmp_path: Path) -> dict[str, str]:
    return {
        "OPPORTUNITIES_DATABASE_URL": f"sqlite:///{(tmp_path / 'opportunities.db').as_posix()}",
        "OPPORTUNITIES_SEARCH_CONFIG_DIR": str(ROOT / "configs" / "searches"),
        "OPPORTUNITIES_CATEGORY_CONFIG_PATH": str(ROOT / "configs" / "categories.yml"),
        "OPPORTUNITIES_README_PATH": str(tmp_path / "README.md"),
        "OPPORTUNITIES_PUBLIC_EXPORT_DIR": str(tmp_path / "exports"),
        # Exercise injected collection paths; conftest still blocks real HTTPX transports.
        "OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED": "true",
        "OPPORTUNITIES_RATE_LIMIT_SECONDS": "0",
    }


def initialize_projection_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "# Test\n\n<!-- BEGIN OPPORTUNITY COUNTS -->\nold\n"
        "<!-- END OPPORTUNITY COUNTS -->\n\n<!-- BEGIN OPPORTUNITIES -->\nold\n"
        "<!-- END OPPORTUNITIES -->\n",
        encoding="utf-8",
    )
    docs_path = tmp_path / "docs/maintainers/engineering/search-registry.md"
    docs_path.parent.mkdir(parents=True)
    docs_path.write_text(
        "# Search registry\n\n```text\nconfigs/searches/\n"
        "├── roles/       # 0 technology paths\n"
        "├── companies/   # 0 targeted employers\n"
        "└── countries/   # 0 country partitions\n```\n",
        encoding="utf-8",
    )


def repository_for(environment: dict[str, str]) -> tuple[Repository, Engine]:
    settings = Settings(database_url=environment["OPPORTUNITIES_DATABASE_URL"])
    engine = create_database_engine(settings.database_url)
    return Repository(create_session_factory(engine), settings), engine


def install_quality_scraper(
    monkeypatch: pytest.MonkeyPatch,
    *,
    found: int = 20,
    accepted: int = 20,
    failed_slugs: tuple[str, ...] = (),
    failure_code: str = "timeout",
) -> None:
    """Exercise the real pipeline, repository, and quality gate without source access."""

    async def scrape(
        self: LinkedInScraper,
        search: LinkedInSearchConfig,
        fetcher: TextFetcher,
        *,
        known_jobs: tuple[KnownJob, ...] = (),
    ) -> LinkedInScrapeResult:
        del self, fetcher, known_jobs
        if search.slug in failed_slugs:
            raise FetchError(failure_code, "private-diagnostic-must-not-leak")
        return LinkedInScrapeResult(
            positions=[
                RawJob(
                    source_job_id=str(1111111111 + index),
                    company="private-company-must-not-leak",
                    title="Software Intern 2027" if index < accepted else "Senior Engineer 2027",
                    locations=["Berlin, Germany"],
                    application_url=f"https://www.linkedin.com/jobs/view/{1111111111 + index}",
                    description="private-description-must-not-leak",
                    industries="Software Development",
                    start_date="Summer 2027",
                    posted_at=datetime(2026, 7, 1, tzinfo=UTC),
                )
                for index in range(found)
            ],
            warnings=(),
            pages_fetched=1,
            search_result_count=found,
        )

    monkeypatch.setattr(LinkedInScraper, "scrape", scrape)


@pytest.mark.parametrize(
    ("mode", "exit_code", "status", "baseline_count"),
    [
        ("success", 0, "passed", 4),
        ("warning", 0, "warning", 4),
        ("blocking", 1, "failed", 3),
        ("partial", 2, "warning", 3),
        ("blocked", 1, "warning", 3),
        ("failed", 1, "failed", 3),
        ("selected", 0, "passed", 3),
    ],
)
def test_scrape_quality_gate_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    search: LinkedInSearchConfig,
    mode: str,
    exit_code: int,
    status: str,
    baseline_count: int,
) -> None:
    environment = cli_env(tmp_path)
    initialize_projection_files(tmp_path)
    other = search.model_copy(update={"slug": "other-search"})
    monkeypatch.setattr(cli_app_module, "_configured_searches", lambda _settings: [search, other])
    install_quality_scraper(monkeypatch)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    report_path = tmp_path / "quality-reports/data-quality-report.json"
    args = ["scrape", "--quality-report", str(report_path)]
    # Establish complete observations so the next run tests drift rather than warm-up.
    for _ in range(3):
        command = runner.invoke(app, [*args, "--no-render"], env=environment)
        assert command.exit_code == 0, command.output
    before_readme = (tmp_path / "README.md").read_bytes()
    failures = (
        (other.slug,)
        if mode in {"partial", "blocked"}
        else (search.slug, other.slug)
        if mode == "failed"
        else ()
    )
    install_quality_scraper(
        monkeypatch,
        found=0 if mode == "blocking" else 20,
        accepted=10 if mode == "warning" else 20,
        failed_slugs=failures,
        failure_code="source_blocked" if mode == "blocked" else "timeout",
    )
    if mode == "selected":
        args += ["--search", search.slug]
    command = runner.invoke(app, args, env=environment)

    assert command.exit_code == exit_code, command.output
    report_text = report_path.read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert report["status"] == status
    assert "must-not-leak" not in report_text
    assert "1111111111" not in report_text
    if exit_code == 1:
        assert (tmp_path / "README.md").read_bytes() == before_readme
        assert not (tmp_path / "exports").exists()
    else:
        assert runner.invoke(app, ["validate"], env=environment).exit_code == 0
    repository, engine = repository_for(environment)
    try:
        assert len(repository.data_quality_baselines()) == baseline_count
        # Drift never closes existing rows.
        assert len(repository.list_open_jobs()) == 20
        expected_successes = (
            0 if mode == "failed" else 1 if mode in {"partial", "selected", "blocked"} else 2
        )
        assert repository.stats().successful_runs == 6 + expected_successes
    finally:
        engine.dispose()


@pytest.mark.parametrize("failure", ["read", "analysis", "write", "persist"])
def test_requested_quality_gate_fails_closed_on_local_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    search: LinkedInSearchConfig,
    failure: str,
) -> None:
    environment = cli_env(tmp_path)
    monkeypatch.setattr(cli_app_module, "_configured_searches", lambda _settings: [search])
    install_quality_scraper(monkeypatch)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    target, attribute = {
        "read": (Repository, "data_quality_baselines"),
        "analysis": (cli_app_module, "analyze_collection_quality"),
        "write": (cli_app_module, "atomic_write_text"),
        "persist": (Repository, "record_data_quality_snapshot"),
    }[failure]
    monkeypatch.setattr(target, attribute, Mock(side_effect=OSError("private-must-not-leak")))
    report_path = tmp_path / "quality-reports/data-quality-report.json"
    command = runner.invoke(app, ["scrape", "--quality-report", str(report_path)], env=environment)

    assert command.exit_code == 1
    assert "cannot continue" in command.output
    assert "must-not-leak" not in command.output
    assert not (tmp_path / "README.md").exists()
    assert not (tmp_path / "exports").exists()
    # Writing the report precedes baseline persistence, so persistence failure keeps evidence.
    assert report_path.exists() == (failure == "persist")


@pytest.mark.parametrize("no_render", [False, True])
@pytest.mark.parametrize("blocked", [False, True])
def test_availability_source_block_fails_closed_without_rendering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, blocked: bool, no_render: bool
) -> None:
    environment = cli_env(tmp_path)
    initialize_projection_files(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    before = {
        path: path.read_bytes()
        for path in (
            tmp_path / "README.md",
            tmp_path / "docs/maintainers/engineering/search-registry.md",
        )
    }

    async def audit(*, settings: Settings, repository: Repository) -> AvailabilityAuditResult:
        return AvailabilityAuditResult(1, 0, 0, 0, ("1111111111",), source_blocked=blocked)

    monkeypatch.setattr(cli_app_module, "audit_job_availability", audit)
    args = ["check-availability", *(["--no-render"] if no_render else [])]
    result = runner.invoke(app, args, env=environment)

    assert result.exit_code == (1 if blocked else 2), result.output
    if blocked:
        assert "source processing stopped" in result.output
        assert "Projections were not refreshed" in result.output
    else:
        assert "source processing stopped" not in result.output
    if blocked or no_render:
        assert {path: path.read_bytes() for path in before} == before
        assert not (tmp_path / "exports").exists()
    else:
        assert runner.invoke(app, ["validate"], env=environment).exit_code == 0


def test_availability_public_listing_301_returns_partial_success_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_MAX_CONCURRENCY"] = "1"
    initialize_projection_files(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    now = datetime(2026, 7, 20, tzinfo=UTC)
    checked_at = now + timedelta(minutes=1)
    monkeypatch.setattr(availability_module, "utc_now", lambda: checked_at)
    requested: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path == "/jobs/view/2":
            return httpx.Response(
                301,
                headers={"Location": "https://example.invalid/unfamiliar?token=synthetic-private"},
                text="synthetic-private-redirect-body",
            )
        return httpx.Response(
            200,
            text='<h1 class="top-card-layout__title">Software Intern 2027</h1>'
            '<a class="topcard__org-name-link">Synthetic Technology</a>',
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: client)
    repository, engine = repository_for(environment)
    try:
        repository.upsert_manual_jobs(
            [
                DiscoveredJob(
                    linkedin_job_id=job_id,
                    company="Synthetic Technology",
                    title="Software Intern 2027",
                    location="Berlin, Germany",
                    link=f"https://www.linkedin.com/jobs/view/{job_id}",
                    category=OpportunityCategory.SOFTWARE_ENGINEERING,
                    employment_type=EmploymentType.INTERNSHIP,
                )
                for job_id in ("1", "2", "3")
            ],
            observed_at=now,
        )
        before = {job.linkedin_job_id: job for job in repository.list_all_jobs()}

        result = runner.invoke(app, ["check-availability"], env=environment)

        assert result.exit_code == 2, result.output
        assert "Checked 3 position(s): 2 available, 0 deleted, 0 reopened" in result.output
        assert "1 inconclusive" in result.output
        assert "source processing stopped" not in result.output
        assert "synthetic-private" not in result.output
        assert client.is_closed
        assert requested == [
            "/jobs/view/1",
            "/jobs-guest/jobs/api/jobPosting/1",
            "/jobs/view/2",
            "/jobs/view/3",
            "/jobs-guest/jobs/api/jobPosting/3",
        ]
        after = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
        assert after["2"] == before["2"]
        for job_id in ("1", "3"):
            assert after[job_id].last_seen_at == checked_at
        assert runner.invoke(app, ["validate"], env=environment).exit_code == 0
    finally:
        asyncio.run(client.aclose())
        engine.dispose()


@pytest.mark.parametrize("cleanup_failure", [False, True])
def test_availability_denial_preserves_confirmed_state_but_never_refreshes_existing_projections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    search: LinkedInSearchConfig,
    cleanup_failure: bool,
) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_MAX_CONCURRENCY"] = "1"
    environment["OPPORTUNITIES_MAX_RETRIES"] = "0"
    initialize_projection_files(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    now = datetime(2026, 7, 20, tzinfo=UTC)
    checked_at = now + timedelta(minutes=3)
    monkeypatch.setattr(availability_module, "utc_now", lambda: checked_at)
    requested: list[str] = []

    class DeniedStream(httpx.ByteStream):
        async def aclose(self) -> None:
            if cleanup_failure:
                raise httpx.ReadError("synthetic-private-cleanup-detail")

    def respond(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path.endswith("/2"):
            return httpx.Response(404)
        if request.url.path.endswith("/3"):
            return httpx.Response(403, stream=DeniedStream(b"synthetic-private-denial-body"))
        return httpx.Response(
            200,
            text='<h1 class="top-card-layout__title">Software Intern 2027</h1>'
            '<a class="topcard__org-name-link">Synthetic Technology</a>',
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: client)
    repository, engine = repository_for(environment)
    try:
        repository.sync_searches([search], now)
        jobs = [
            DiscoveredJob(
                linkedin_job_id=job_id,
                company="Synthetic Technology",
                title="Software Intern 2027",
                location="Berlin, Germany",
                link=f"https://www.linkedin.com/jobs/view/{job_id}",
                category=OpportunityCategory.SOFTWARE_ENGINEERING,
                employment_type=EmploymentType.INTERNSHIP,
            )
            for job_id in ("1", "2", "3")
        ]
        for run, unavailable in enumerate(((), ("1", "3"), ("1",))):
            when = now + timedelta(minutes=run)
            repository.persist_success(
                run_id=f"audit-seed-{run}",
                search=search,
                jobs=jobs if run == 0 else [],
                confirmed_unavailable_ids=unavailable,
                found_count=3 if run == 0 else 0,
                excluded_count=0,
                warning_count=0,
                started_at=when,
                finished_at=when,
                duration_ms=1,
            )
        before_jobs = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
        before_stats = repository.stats()
        assert runner.invoke(app, ["render"], env=environment).exit_code == 0
        before_files = {
            path: path.read_bytes()
            for path in (
                tmp_path / "README.md",
                tmp_path / "docs/maintainers/engineering/search-registry.md",
                *sorted((tmp_path / "exports").iterdir()),
            )
        }

        result = runner.invoke(app, ["check-availability"], env=environment)

        assert result.exit_code == 1, result.output
        assert "source processing stopped" in result.output
        assert "1 available, 1 deleted, 1 reopened" in result.output
        assert "0 inconclusive, 1 blocked" in " ".join(result.output.split())
        assert "Collection skipped: availability audit stopped (HTTP 403)" in " ".join(
            result.output.split()
        )
        assert "synthetic-private" not in result.output
        assert client.is_closed
        assert requested == [
            "/jobs/view/1",
            "/jobs-guest/jobs/api/jobPosting/1",
            "/jobs/view/2",
            "/jobs/view/3",
        ]
        assert {path: path.read_bytes() for path in before_files} == before_files
        current = {job.linkedin_job_id: job for job in repository.list_all_jobs()}
        assert set(current) == {"1", "3"}
        assert current["1"].last_seen_at == checked_at
        assert current["1"].first_seen_at == before_jobs["1"].first_seen_at
        assert current["3"] == before_jobs["3"]
        assert repository.stats().successful_runs == before_stats.successful_runs
        assert repository.stats().last_success_at == before_stats.last_success_at
        with repository.factory() as session:
            reopened = session.get(JobSearchRow, (search.slug, "1"))
            preserved = session.get(JobSearchRow, (search.slug, "3"))
            assert reopened is not None
            assert reopened.active is True
            assert reopened.unavailable_confirmations == 0
            assert session.get(JobSearchRow, (search.slug, "2")) is None
            assert preserved is not None
            assert preserved.active is True
            assert preserved.unavailable_confirmations == 1
    finally:
        asyncio.run(client.aclose())
        engine.dispose()


def test_database_render_stats_and_validate_commands(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    initialize_projection_files(tmp_path)
    docs_path = tmp_path / "docs/maintainers/engineering/search-registry.md"
    before = runner.invoke(app, ["stats"], env=environment)
    assert before.exit_code == 3

    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    exported = runner.invoke(app, ["export-public"], env=environment)
    assert exported.exit_code == 0, exported.output
    rendered = runner.invoke(app, ["render"], env=environment)
    assert rendered.exit_code == 0, rendered.output
    availability = runner.invoke(app, ["check-availability"], env=environment)
    assert availability.exit_code == 0, availability.output
    assert "Checked 0 position(s)" in availability.output
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "| Company | Title | Location | Listing |" in readme
    assert "# 23 technology paths" in docs_path.read_text(encoding="utf-8")
    assert (tmp_path / "exports" / "open-opportunities.csv").is_file()
    assert (tmp_path / "exports" / "open-opportunities.json").is_file()
    assert (tmp_path / "exports" / "dataset-metadata.json").is_file()

    statistics = runner.invoke(app, ["stats"], env=environment)
    assert statistics.exit_code == 0
    assert "Total positions" in statistics.output
    validated = runner.invoke(app, ["validate"], env=environment)
    assert validated.exit_code == 0, validated.output

    registry_content = docs_path.read_text(encoding="utf-8")
    docs_path.write_text(
        registry_content.replace("# 23 technology paths", "# 0 technology paths"),
        encoding="utf-8",
    )
    invalid_registry = runner.invoke(app, ["validate"], env=environment)
    assert invalid_registry.exit_code == 1
    assert "Search registry layout counts do not match" in invalid_registry.output
    assert "# 0 technology paths" in docs_path.read_text(encoding="utf-8")
    assert runner.invoke(app, ["render"], env=environment).exit_code == 0
    assert docs_path.read_text(encoding="utf-8") == registry_content
    assert not (tmp_path / "docs/maintainers/search-registry.md").exists()

    metadata_path = tmp_path / "exports" / "dataset-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["total"] = 1
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    invalid = runner.invoke(app, ["validate"], env=environment)
    assert invalid.exit_code == 1
    assert "metadata counts or hashes" in invalid.output


def test_controlled_insertion_and_removal_require_projection_regeneration(tmp_path: Path) -> None:
    """Simulate a maintenance write through Repository, never direct website/SQL writes."""
    environment = cli_env(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Test\n\n<!-- BEGIN OPPORTUNITY COUNTS -->\nold\n"
        "<!-- END OPPORTUNITY COUNTS -->\n\n<!-- BEGIN OPPORTUNITIES -->\nold\n"
        "<!-- END OPPORTUNITIES -->\n",
        encoding="utf-8",
    )
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    engine = create_database_engine(environment["OPPORTUNITIES_DATABASE_URL"])
    repository = Repository(create_session_factory(engine), Settings())
    now = datetime(2026, 7, 20, tzinfo=UTC)
    search = LinkedInSearchConfig(
        name="Synthetic search",
        slug="synthetic-search",
        keywords="software intern 2027",
        location="Europe",
        max_pages=1,
        max_results=25,
    )
    job_id = "1111111111"
    try:
        repository.sync_searches([search], now)
        repository.persist_success(
            run_id="00000000-0000-0000-0000-000000000001",
            search=search,
            jobs=[
                DiscoveredJob(
                    linkedin_job_id=job_id,
                    company="Synthetic Technology",
                    title="Software Engineering Intern 2027",
                    location="London, UK",
                    link=f"https://www.linkedin.com/jobs/view/{job_id}",
                    category=OpportunityCategory.SOFTWARE_ENGINEERING,
                    employment_type=EmploymentType.INTERNSHIP,
                )
            ],
            confirmed_unavailable_ids=(),
            found_count=1,
            excluded_count=0,
            warning_count=0,
            started_at=now,
            finished_at=now,
            duration_ms=1,
        )
        assert runner.invoke(app, ["render"], env=environment).exit_code == 0
        assert runner.invoke(app, ["validate"], env=environment).exit_code == 0
        assert "Synthetic Technology" in readme.read_text(encoding="utf-8")
        assert "Synthetic Technology" in (tmp_path / "exports/open-opportunities.csv").read_text(
            encoding="utf-8"
        )
        repository.apply_availability_audit(
            available_ids=(), unavailable_ids=(job_id,), observed_at=now
        )
        assert runner.invoke(app, ["validate"], env=environment).exit_code == 1
        assert runner.invoke(app, ["render"], env=environment).exit_code == 0
        assert runner.invoke(app, ["validate"], env=environment).exit_code == 0
        assert "Synthetic Technology" not in readme.read_text(encoding="utf-8")
        assert (tmp_path / "exports/open-opportunities.json").read_text(encoding="utf-8") == "[]\n"
    finally:
        engine.dispose()


def test_searches_works_without_database(tmp_path: Path) -> None:
    result = runner.invoke(app, ["searches"], env=cli_env(tmp_path))
    assert result.exit_code == 0, result.output
    assert "LinkedIn searches" in result.output
    assert "Enabled" in result.output
    assert "robotics" in result.output
    assert not (tmp_path / "opportunities.db").exists()


@pytest.mark.parametrize(
    "command",
    [
        ("scrape",),
        ("check-availability",),
        ("render",),
        ("export-public",),
        ("stats",),
        ("validate",),
    ],
)
def test_database_engine_is_disposed_when_migration_check_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: tuple[str, ...],
) -> None:
    engine = Mock(spec=Engine)
    engine.dispose.side_effect = RuntimeError("cleanup failed")
    monkeypatch.setattr(cli_app_module, "create_database_engine", lambda _url: engine)

    def reject_unmigrated_database(_engine: Engine) -> None:
        raise typer.Exit(3)

    monkeypatch.setattr(cli_app_module, "_require_migrations", reject_unmigrated_database)

    result = runner.invoke(app, list(command), env=cli_env(tmp_path))

    assert result.exit_code == 3
    engine.dispose.assert_called_once_with()


def test_scrape_preserves_unexpected_migration_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = Mock(spec=Engine)
    migration_error = ValueError("migration check failed")
    monkeypatch.setattr(cli_app_module, "create_database_engine", lambda _url: engine)

    def fail_migration(_engine: Engine) -> None:
        raise migration_error

    monkeypatch.setattr(cli_app_module, "_require_migrations", fail_migration)

    result = runner.invoke(app, ["scrape"], env=cli_env(tmp_path))

    assert result.exception is migration_error
    engine.dispose.assert_called_once_with()


def test_searches_disposes_engine_when_database_inspection_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "opportunities.db").touch()
    engine = Mock(spec=Engine)
    engine.dispose.side_effect = RuntimeError("cleanup failed")
    monkeypatch.setattr(cli_app_module, "create_database_engine", lambda _url: engine)

    def fail_database_inspection(_engine: Engine) -> set[str]:
        raise typer.Exit(3)

    monkeypatch.setattr(cli_app_module, "missing_tables", fail_database_inspection)

    result = runner.invoke(app, ["searches"], env=cli_env(tmp_path))

    assert result.exit_code == 3
    engine.dispose.assert_called_once_with()


def test_repository_construction_failure_disposes_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = Mock(spec=Engine)
    construction_error = RuntimeError("repository construction failed")
    engine.dispose.side_effect = RuntimeError("cleanup failed")
    monkeypatch.setattr(cli_app_module, "create_database_engine", lambda _url: engine)

    def fail_session_factory(_engine: Engine) -> None:
        raise construction_error

    monkeypatch.setattr(cli_app_module, "create_session_factory", fail_session_factory)

    result = runner.invoke(app, ["stats"], env=cli_env(tmp_path))

    assert result.exception is construction_error
    engine.dispose.assert_called_once_with()


def test_disposal_failure_does_not_replace_command_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = Mock(spec=Engine)
    command_error = RuntimeError("command failed")
    engine.dispose.side_effect = RuntimeError("cleanup failed")
    monkeypatch.setattr(cli_app_module, "create_database_engine", lambda _url: engine)
    monkeypatch.setattr(cli_app_module, "_require_migrations", lambda _engine: None)

    def fail_command(_repository: object) -> None:
        raise command_error

    monkeypatch.setattr(Repository, "stats", fail_command)

    result = runner.invoke(app, ["stats"], env=cli_env(tmp_path))

    assert result.exception is command_error
    engine.dispose.assert_called_once_with()


@pytest.mark.parametrize(
    "command",
    [
        ("scrape",),
        ("scrape", "--quality-report", "quality.json"),
        ("check-availability",),
        ("search-test", "test-search"),
    ],
)
def test_collection_commands_require_permission_even_when_dotenv_enables_it(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    # The dotenv fixture is explicit; this must never rely on an operator's real .env.
    (tmp_path / ".env").write_text(
        "OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true\n", encoding="utf-8"
    )
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED"] = "false"
    result = runner.invoke(app, list(command), env=environment)
    assert result.exit_code == 2
    assert "LinkedIn collection is disabled" in result.output
    assert not (tmp_path / "opportunities.db").exists()


@pytest.mark.parametrize("scheme", ["sqlite", "postgresql"])
def test_configuration_errors_are_sanitized_before_database_access(
    tmp_path: Path, scheme: str
) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_DATABASE_URL"] = f"{scheme}://user:SYNTH@example.invalid/database"
    result = runner.invoke(app, ["stats"], env=environment)
    assert result.exit_code == 2
    assert "Configuration error" in result.output
    assert "SYNTH" not in result.output
    assert "Traceback" not in result.output
    assert not (tmp_path / "opportunities.db").exists()


def test_unknown_search_is_rejected_without_network(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["search-test", "does-not-exist"],
        env=cli_env(tmp_path),
    )
    assert result.exit_code == 2
    assert "unknown or disabled search" in result.output


def test_add_job_persists_and_renders_without_authorization_or_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED"] = "false"
    initialize_projection_files(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0

    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unexpected network request")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    result = runner.invoke(
        app,
        [
            "add-job",
            "--url",
            "https://www.linkedin.com/jobs/view/1111111111?trk=public_jobs",
            "--company",
            "Example Technology",
            "--title",
            "Software Engineering Intern 2027",
            "--location",
            "London, UK",
            "--category",
            "software-engineering",
            "--employment-type",
            "internship",
            "--industries",
            "Software Development",
            "--start-date",
            "Summer 2027",
            "--posted-at",
            "2026-07-01T10:30:00+02:00",
        ],
        env=environment,
    )

    assert result.exit_code == 0, result.output
    assert "Job 1111111111 added" in result.output
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Example Technology" in readme
    assert "Last successful collection: Never" in readme
    assert (tmp_path / "exports" / "open-opportunities.csv").is_file()
    assert (tmp_path / "exports" / "open-opportunities.json").is_file()
    repository, engine = repository_for(environment)
    try:
        stored = repository.list_open_jobs()[0]
        assert stored.linkedin_job_id == "1111111111"
        assert stored.link == "https://www.linkedin.com/jobs/view/1111111111"
        assert stored.first_seen_at.isoformat() == "2026-07-01T08:30:00+00:00"
        assert repository.stats().successful_runs == 0
    finally:
        engine.dispose()


def test_add_job_reports_persisted_changes_without_rendering(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED"] = "false"
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    repository, engine = repository_for(environment)
    try:
        # Reuse one database so each reported outcome must follow real persisted changes.
        for company, message in (
            ("Example Technology", "added"),
            ("Renamed Technology", "updated"),
            ("Renamed Technology", "already current"),
        ):
            result = runner.invoke(
                app,
                [
                    "add-job",
                    "--url",
                    "https://www.linkedin.com/jobs/view/2222222222",
                    "--company",
                    company,
                    "--title",
                    "Graduate Software Engineer 2027",
                    "--location",
                    "Berlin, Germany",
                    "--category",
                    "software-engineering",
                    "--employment-type",
                    "new-grad",
                    "--no-render",
                ],
                env=environment,
            )
            assert result.exit_code == 0, result.output
            assert f"Job 2222222222 {message}." in result.output
            jobs = repository.list_open_jobs()
            assert [(job.linkedin_job_id, job.company) for job in jobs] == [("2222222222", company)]
            assert repository.stats().successful_runs == 0
            assert not (tmp_path / "README.md").exists()
            assert not (tmp_path / "exports").exists()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("extra_args", "message"),
    [
        (["--url", "https://example.com/jobs/view/1111111111"], "canonical LinkedIn job"),
        (["--posted-at", "not-a-timestamp"], "valid ISO-8601 timestamp"),
        (["--posted-at", "2026-07-01"], "valid ISO-8601 timestamp"),
        (["--category", "not-a-category"], "Invalid value"),
        (["--title", "Senior Software Engineer Intern 2027"], "outside publication policy"),
        (["--title", "Software Engineering Intern 2026"], "outside publication policy"),
        (["--title", "Software Engineering Intern"], "outside publication policy"),
        (["--location", "London, Ontario, Canada"], "outside publication policy"),
        (["--category", "cybersecurity"], "conflicts with classifier"),
        (["--employment-type", "new-grad"], "conflicts with classifier"),
        (["--posted-at", "2026-06-01T12:00:00"], "explicit timezone"),
        (["--posted-at", "2100-01-01T00:00:00Z"], "cannot be in the future"),
        (["--company", "SensitiveExample" * 20], "Invalid listing fields"),
    ],
)
def test_add_job_rejects_invalid_input(tmp_path: Path, extra_args: list[str], message: str) -> None:
    environment = cli_env(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    arguments = [
        "add-job",
        "--url",
        "https://www.linkedin.com/jobs/view/1111111111",
        "--company",
        "Example Technology",
        "--title",
        "Software Engineering Intern 2027",
        "--location",
        "London, UK",
        "--category",
        "software-engineering",
        "--employment-type",
        "internship",
        "--no-render",
        *extra_args,
    ]

    result = runner.invoke(app, arguments, env=environment)

    assert result.exit_code == 2
    assert message in result.output
    assert "SensitiveExample" not in result.output
    repository, engine = repository_for(environment)
    try:
        assert repository.list_all_jobs() == []
    finally:
        engine.dispose()


def _manual_batch_record(job_id: str) -> dict[str, str]:
    return {
        "url": f"https://www.linkedin.com/jobs/view/{job_id}",
        "company": "Example Technology",
        "title": "Software Engineering Intern 2027",
        "location": "London, UK",
        "category": "software-engineering",
        "employment_type": "internship",
    }


def test_add_jobs_persists_three_and_renders_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED"] = "false"
    initialize_projection_files(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    input_file = tmp_path / "reviewed-jobs.json"
    input_file.write_text(
        json.dumps([_manual_batch_record(str(1_000_000_000 + index)) for index in range(3)]),
        encoding="utf-8",
    )

    def reject_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("unexpected network request")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    result = runner.invoke(app, ["add-jobs", "--input", str(input_file)], env=environment)

    assert result.exit_code == 0, result.output
    assert "Processed 3 job(s): 3 added, 0 updated, 0 already current." in result.output
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "1000000000" in readme
    assert "1000000002" in readme
    assert (tmp_path / "exports" / "open-opportunities.json").is_file()
    repository, engine = repository_for(environment)
    try:
        assert len(repository.list_open_jobs()) == 3
        assert repository.stats().successful_runs == 0
    finally:
        engine.dispose()


def test_add_jobs_no_render_only_updates_sqlite(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    input_file = tmp_path / "reviewed-jobs.json"
    input_file.write_text(json.dumps([_manual_batch_record("3333333333")]), encoding="utf-8")

    result = runner.invoke(
        app, ["add-jobs", "--input", str(input_file), "--no-render"], env=environment
    )

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "README.md").exists()
    assert not (tmp_path / "exports").exists()
    repository, engine = repository_for(environment)
    try:
        assert [job.linkedin_job_id for job in repository.list_open_jobs()] == ["3333333333"]
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[]", "array of 1 to 10 jobs"),
        (
            json.dumps([_manual_batch_record(str(1_000_000_000 + index)) for index in range(11)]),
            "array of 1 to 10 jobs",
        ),
        (json.dumps(_manual_batch_record("1111111111")), "array of 1 to 10 jobs"),
        (
            json.dumps(
                [
                    _manual_batch_record("1111111111"),
                    {**_manual_batch_record("2222222222"), "title": "Senior Engineer 2027"},
                ]
            ),
            "job 2: listing is outside publication policy",
        ),
        (
            json.dumps(
                [
                    {
                        key: value
                        for key, value in _manual_batch_record("1111111111").items()
                        if key != "title"
                    }
                ]
            ),
            "missing required listing fields",
        ),
        (
            json.dumps([{**_manual_batch_record("1111111111"), "secret_marker": "must-not-echo"}]),
            "unknown listing fields",
        ),
        (
            json.dumps(
                [
                    _manual_batch_record("1111111111"),
                    {
                        **_manual_batch_record("1111111111"),
                        "url": "https://www.linkedin.com/jobs/view/1111111111?trk=foo",
                    },
                ]
            ),
            "duplicate LinkedIn job identity",
        ),
        (
            json.dumps([{**_manual_batch_record("1111111111"), "company": 10}]),
            "listing fields have invalid types",
        ),
        (
            json.dumps(
                [{**_manual_batch_record("1111111111"), "posted_at": "2026-07-01T12:00:00"}]
            ),
            "explicit timezone",
        ),
        (
            '[{"url":"https://www.linkedin.com/jobs/view/1111111111","url":"must-not-echo"}]',
            "valid UTF-8 JSON",
        ),
        ("[" * 10_000 + "0" + "]" * 10_000, None),
        ("[" + " " * 65_536 + "]", "exceeds 64 KiB"),
    ],
    ids=[
        "empty",
        "too-many",
        "not-array",
        "invalid-later-job",
        "missing-field",
        "unknown-field",
        "duplicate-id",
        "invalid-type",
        "naive-time",
        "duplicate-key",
        "deeply-nested",
        "oversize",
    ],
)
def test_add_jobs_rejects_bad_batch_before_writing(
    tmp_path: Path, content: str, message: str | None
) -> None:
    environment = cli_env(tmp_path)
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    input_file = tmp_path / "reviewed-jobs.json"
    input_file.write_text(content, encoding="utf-8")

    result = runner.invoke(
        app, ["add-jobs", "--input", str(input_file), "--no-render"], env=environment
    )

    assert result.exit_code == 2
    if message is not None:
        assert message in result.output
    assert "Traceback" not in result.output
    assert "must-not-echo" not in result.output
    repository, engine = repository_for(environment)
    try:
        assert repository.list_all_jobs() == []
    finally:
        engine.dispose()
