from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from opportunities.cli.app import app
from opportunities.utils.paths import find_project_root

runner = CliRunner()
ROOT = find_project_root(Path(__file__))


def cli_env(tmp_path: Path) -> dict[str, str]:
    return {
        "INTERNSHIPS_DATABASE_URL": f"sqlite:///{(tmp_path / 'opportunities.db').as_posix()}",
        "INTERNSHIPS_SEARCH_CONFIG_DIR": str(ROOT / "configs" / "searches"),
        "INTERNSHIPS_CATEGORY_CONFIG_PATH": str(ROOT / "configs" / "categories.yml"),
        "INTERNSHIPS_README_PATH": str(tmp_path / "README.md"),
        "INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED": "true",
        "INTERNSHIPS_RATE_LIMIT_SECONDS": "0",
    }


def test_database_render_stats_and_validate_commands(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    (tmp_path / "README.md").write_text(
        "# Test\n\n<!-- BEGIN INTERNSHIPS -->\nold\n<!-- END INTERNSHIPS -->\n",
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
    assert "robotics" in result.output


def test_scrape_requires_permission_even_when_dotenv_enables_it(tmp_path: Path) -> None:
    environment = cli_env(tmp_path)
    environment["INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED"] = "false"
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
