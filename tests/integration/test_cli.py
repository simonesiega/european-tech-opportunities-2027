from __future__ import annotations

import json
import socket
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest
import typer
from sqlalchemy import Engine
from typer.testing import CliRunner

import opportunities.cli.app as cli_app_module
from opportunities.cli.app import app
from opportunities.config.settings import Settings
from opportunities.database.repository import PersistSummary, Repository
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.utils.paths import find_project_root

runner = CliRunner()
ROOT = find_project_root(Path(__file__))


def cli_env(tmp_path: Path) -> dict[str, str]:
    return {
        "OPPORTUNITIES_DATABASE_URL": f"sqlite:///{(tmp_path / 'opportunities.db').as_posix()}",
        "OPPORTUNITIES_SEARCH_CONFIG_DIR": str(ROOT / "configs" / "searches"),
        "OPPORTUNITIES_CATEGORY_CONFIG_PATH": str(ROOT / "configs" / "categories.yml"),
        "OPPORTUNITIES_README_PATH": str(tmp_path / "README.md"),
        "OPPORTUNITIES_PUBLIC_EXPORT_DIR": str(tmp_path / "exports"),
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
    docs_path = tmp_path / "docs" / "guides" / "user-guide" / "search-registry.md"
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


def test_database_render_stats_and_validate_commands(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    initialize_projection_files(tmp_path)
    docs_path = tmp_path / "docs" / "guides" / "user-guide" / "search-registry.md"
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

    statistics = runner.invoke(app, ["stats"], env=environment)
    assert statistics.exit_code == 0
    assert "Total positions" in statistics.output
    validated = runner.invoke(app, ["validate"], env=environment)
    assert validated.exit_code == 0, validated.output


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


def test_scrape_requires_permission_even_when_dotenv_enables_it(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED"] = "false"
    result = runner.invoke(app, ["scrape"], env=environment)
    assert result.exit_code == 2
    assert "LinkedIn collection is disabled" in result.output


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


def test_add_job_no_render_only_updates_sqlite(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    environment["OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED"] = "false"
    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0

    result = runner.invoke(
        app,
        [
            "add-job",
            "--url",
            "https://www.linkedin.com/jobs/view/2222222222",
            "--company",
            "Example Technology",
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
    assert not (tmp_path / "README.md").exists()
    assert not (tmp_path / "exports").exists()
    repository, engine = repository_for(environment)
    try:
        assert [job.linkedin_job_id for job in repository.list_open_jobs()] == ["2222222222"]
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("summary", "message"),
    [
        (PersistSummary(new=1), "added"),
        (PersistSummary(updated=1), "updated"),
        (PersistSummary(), "already current"),
    ],
)
def test_add_job_reports_exact_persistence_outcome(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    summary: PersistSummary,
    message: str,
) -> None:
    repository = Mock(spec=Repository)
    repository.upsert_manual_job.return_value = summary
    engine = Mock(spec=Engine)
    monkeypatch.setattr(cli_app_module, "_repository", lambda _settings: (repository, engine))
    monkeypatch.setattr(cli_app_module, "_require_migrations", lambda _engine: None)

    result = runner.invoke(
        app,
        [
            "add-job",
            "--url",
            "https://www.linkedin.com/jobs/view/2222222222",
            "--company",
            "Example Technology",
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
        env=cli_env(tmp_path),
    )

    assert result.exit_code == 0, result.output
    assert f"Job 2222222222 {message}." in result.output
    engine.dispose.assert_called_once_with()


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
