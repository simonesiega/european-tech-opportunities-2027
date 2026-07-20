from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
import typer
from sqlalchemy import Engine
from typer.testing import CliRunner

import opportunities.cli.app as cli_app_module
from opportunities.cli.app import app
from opportunities.database.repository import Repository
from opportunities.utils.paths import find_project_root

runner = CliRunner()
ROOT = find_project_root(Path(__file__))


def cli_env(tmp_path: Path) -> dict[str, str]:
    return {
        "OPPORTUNITIES_DATABASE_URL": f"sqlite:///{(tmp_path / 'opportunities.db').as_posix()}",
        "OPPORTUNITIES_SEARCH_CONFIG_DIR": str(ROOT / "configs" / "searches"),
        "OPPORTUNITIES_CATEGORY_CONFIG_PATH": str(ROOT / "configs" / "categories.yml"),
        "OPPORTUNITIES_README_PATH": str(tmp_path / "README.md"),
        "OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED": "true",
        "OPPORTUNITIES_RATE_LIMIT_SECONDS": "0",
    }


def test_database_render_stats_and_validate_commands(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    (tmp_path / "README.md").write_text(
        "# Test\n\n<!-- BEGIN OPPORTUNITIES -->\nold\n<!-- END OPPORTUNITIES -->\n",
        encoding="utf-8",
    )
    docs_path = tmp_path / "docs" / "md" / "user-guide" / "search-registry.md"
    docs_path.parent.mkdir(parents=True)
    docs_path.write_text(
        "# Search registry\n\n```text\nconfigs/searches/\n"
        "├── roles/       # 0 technology paths\n"
        "├── companies/   # 0 targeted employers\n"
        "└── countries/   # 0 country partitions\n```\n",
        encoding="utf-8",
    )
    before = runner.invoke(app, ["stats"], env=environment)
    assert before.exit_code == 3

    assert runner.invoke(app, ["db-upgrade"], env=environment).exit_code == 0
    rendered = runner.invoke(app, ["render"], env=environment)
    assert rendered.exit_code == 0, rendered.output
    availability = runner.invoke(app, ["check-availability"], env=environment)
    assert availability.exit_code == 0, availability.output
    assert "Checked 0 position(s)" in availability.output
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "| Company | Title | Location | Listing |" in readme
    assert "# 23 technology paths" in docs_path.read_text(encoding="utf-8")

    statistics = runner.invoke(app, ["stats"], env=environment)
    assert statistics.exit_code == 0
    assert "Total positions" in statistics.output
    validated = runner.invoke(app, ["validate"], env=environment)
    assert validated.exit_code == 0, validated.output


def test_searches_works_without_database(tmp_path: Path) -> None:
    result = runner.invoke(app, ["searches"], env=cli_env(tmp_path))
    assert result.exit_code == 0, result.output
    assert "LinkedIn searches" in result.output
    assert "Enabled" in result.output
    assert "robotics" in result.output
    assert not (tmp_path / "opportunities.db").exists()


@pytest.mark.parametrize(
    "command",
    [("scrape",), ("check-availability",), ("render",), ("stats",), ("validate",)],
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
