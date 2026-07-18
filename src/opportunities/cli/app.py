"""Typer CLI for LinkedIn collection, SQLite storage, and README rendering."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from sqlalchemy import Engine

# Importing opportunity modules registers every table on Base.metadata for
# comparison and Alembic autogeneration.
from opportunities.config.rules import load_classification_rules
from opportunities.config.search_registry import (
    SearchRegistryError,
    load_search_registry,
    select_searches,
)
from opportunities.config.settings import Settings, apply_search_overrides, load_settings
from opportunities.database.migrations import migration_head, upgrade_database
from opportunities.database.repository import Repository, SearchHealth
from opportunities.database.session import (
    create_database_engine,
    create_session_factory,
    database_revision,
    missing_tables,
)
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.runner import CollectionPipeline, PipelineResult
from opportunities.readme import ReadmeMetadata, render_readme, validate_readme
from opportunities.search_registry_docs import (
    render_search_registry_docs,
    validate_search_registry_docs,
)
from opportunities.utils.logging import configure_logging
from opportunities.utils.paths import find_project_root

# App context and console for output. The ROOT path is used to locate the migrations directory.
ROOT = find_project_root(Path(__file__))
console = Console()
error_console = Console(stderr=True)
app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Collect strict 2027 European tech internships and new-grad roles into SQLite and README."
    ),
)


@app.callback()
def main(
    ctx: typer.Context,
    settings_file: Annotated[
        Path | None,
        typer.Option("--settings", help="Optional YAML settings file; .env loads automatically."),
    ] = None,
) -> None:
    """Load settings and initialize the CLI context."""
    try:
        settings = load_settings(settings_file)
    except (OSError, ValueError, ValidationError) as exc:
        error_console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(2) from exc
    configure_logging(settings.log_level)
    ctx.obj = settings


@app.command("db-upgrade")
def db_upgrade(ctx: typer.Context) -> None:
    """Upgrade the configured database to the latest migration."""
    settings = _settings(ctx)
    upgrade_database(settings.database_url, repository_root=ROOT)
    console.print("Database is at the latest migration.")


@app.command()
def scrape(
    ctx: typer.Context,
    search: Annotated[str | None, typer.Option("--search", help="Run one search slug.")] = None,
    no_render: Annotated[
        bool, typer.Option("--no-render", help="Do not update README after persistence.")
    ] = False,
) -> None:
    """Collect internships and new-grad roles, then optionally refresh documentation."""
    settings = _settings(ctx)
    _require_linkedin_permission(settings)
    repository, engine = _repository(settings)
    _require_migrations(engine)
    try:
        configured = _configured_searches(settings)
        selected = _selected_searches(configured, search)
        rules = load_classification_rules(settings.category_config_path)
        result = asyncio.run(
            CollectionPipeline(
                settings=settings,
                repository=repository,
                rules=rules,
            ).run(selected, configured_searches=configured)
        )
        _print_result(result)
        if not no_render and result.successful_searches:
            render_readme(
                settings.readme_path,
                repository.list_open_jobs(),
                _readme_metadata(repository),
            )
            render_search_registry_docs(
                _search_registry_docs_path(settings), settings.search_config_dir
            )
            console.print(f"README updated: {settings.readme_path}")
    except (SearchRegistryError, OSError, ValueError, ValidationError) as exc:
        error_console.print(f"[red]Scrape failed:[/red] {exc}")
        raise typer.Exit(2) from exc
    finally:
        engine.dispose()
    raise typer.Exit(result.exit_code)


@app.command("search-test")
def search_test(ctx: typer.Context, search_slug: str) -> None:
    """Preview one configured search without persisting results."""
    settings = _settings(ctx)
    _require_linkedin_permission(settings)
    repository, engine = _repository(settings)
    try:
        selected = _selected_searches(_configured_searches(settings), search_slug)
        if not selected:
            raise ValueError(f"unknown or disabled search: {search_slug}")
        rules = load_classification_rules(settings.category_config_path)
        result, jobs, excluded = asyncio.run(
            CollectionPipeline(
                settings=settings,
                repository=repository,
                rules=rules,
            ).test_search(selected[0])
        )
        _print_jobs(jobs)
        console.print(
            f"Found {result.search_result_count}, accepted {len(jobs)}, excluded {excluded}, "
            f"warnings {len(result.warnings)}."
        )
    except (SearchRegistryError, OSError, ValueError, ValidationError) as exc:
        error_console.print(f"[red]Search test failed:[/red] {exc}")
        raise typer.Exit(2) from exc
    finally:
        engine.dispose()


@app.command()
def render(ctx: typer.Context) -> None:
    """Refresh generated README and registry documentation."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    _require_migrations(engine)
    try:
        _configured_searches(settings)
        open_jobs = repository.list_open_jobs()
        render_readme(
            settings.readme_path,
            open_jobs,
            _readme_metadata(repository),
        )
        render_search_registry_docs(
            _search_registry_docs_path(settings), settings.search_config_dir
        )
        console.print(f"README updated with {len(open_jobs)} open position(s).")
    finally:
        engine.dispose()


@app.command()
def searches(ctx: typer.Context) -> None:
    """Display configured searches and their latest health."""
    settings = _settings(ctx)
    configured = apply_search_overrides(load_search_registry(settings.search_config_dir), settings)
    health: dict[str, SearchHealth] = {}
    repository, engine = _repository(settings)
    if not missing_tables(engine) and database_revision(engine) == migration_head(
        repository_root=ROOT
    ):
        health = repository.search_health()
    table = Table(title="LinkedIn searches")
    table.add_column("Slug", no_wrap=True)
    for heading in ("Scope", "Limits P/R/C", "Last", "F/A"):
        table.add_column(heading)
    for item in configured:
        state = health.get(item.slug)
        status = state.status if state else "never-run"
        table.add_row(
            item.slug,
            item.location,
            f"{item.max_pages}/{item.max_results}/{item.max_rechecks}",
            status,
            f"{state.found_count}/{state.accepted_count}" if state else "-/-",
        )
    console.print(table)
    engine.dispose()


@app.command()
def stats(ctx: typer.Context) -> None:
    """Display aggregate pipeline and database statistics."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    _require_migrations(engine)
    try:
        snapshot = repository.stats()
        table = Table(title="Pipeline statistics")
        table.add_column("Metric")
        table.add_column("Value", justify="right")
        table.add_row("Total positions", str(snapshot.total))
        table.add_row("Open", str(snapshot.open))
        table.add_row("Closed", str(snapshot.closed))
        table.add_row("Configured searches", str(snapshot.configured_searches))
        table.add_row("Successful search runs", str(snapshot.successful_runs))
        table.add_row("Failed search runs", str(snapshot.failed_runs))
        table.add_row(
            "Last success",
            snapshot.last_success_at.isoformat() if snapshot.last_success_at else "never",
        )
        console.print(table)
    finally:
        engine.dispose()


@app.command()
def validate(ctx: typer.Context) -> None:
    """Validate database invariants and generated documentation."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    _require_migrations(engine)
    _configured_searches(settings)
    open_jobs = repository.list_open_jobs()
    errors = validate_readme(
        settings.readme_path,
        open_jobs,
        _readme_metadata(repository),
    )
    errors.extend(
        validate_search_registry_docs(
            _search_registry_docs_path(settings), settings.search_config_dir
        )
    )
    try:
        jobs = repository.list_all_jobs()
        for job in jobs:
            if job.last_seen_at < job.first_seen_at:
                errors.append(f"job {job.linkedin_job_id}: last_seen_at precedes first_seen_at")
    finally:
        engine.dispose()
    if errors:
        for error in errors:
            error_console.print(f"[red]- {error}[/red]")
        raise typer.Exit(1)
    console.print(f"Valid: {len(jobs)} database position(s) and README checked.")


def _configured_searches(settings: Settings) -> list[LinkedInSearchConfig]:
    """Load configured searches with runtime overrides."""
    return apply_search_overrides(load_search_registry(settings.search_config_dir), settings)


def _selected_searches(
    searches: list[LinkedInSearchConfig], slug: str | None
) -> list[LinkedInSearchConfig]:
    """Select enabled searches by optional slug."""
    selected = select_searches(searches, search_slug=slug)
    if not selected:
        raise ValueError(f"unknown or disabled search: {slug}")
    return selected


def _repository(settings: Settings) -> tuple[Repository, Engine]:
    """Create a repository and its database engine."""
    engine = create_database_engine(settings.database_url)
    return Repository(create_session_factory(engine), settings), engine


def _search_registry_docs_path(settings: Settings) -> Path:
    """Resolve registry documentation beside the configured README."""
    return settings.readme_path.parent / "docs" / "md" / "user-guide" / "search-registry.md"


def _readme_metadata(repository: Repository) -> ReadmeMetadata:
    """Build README metadata from database statistics."""
    snapshot = repository.stats()
    return ReadmeMetadata(
        open_positions=snapshot.open,
        last_successful_collection=snapshot.last_success_at,
    )


def _print_result(result: PipelineResult) -> None:
    """Display collection outcomes in a terminal table."""
    table = Table(title="LinkedIn scrape")
    for heading in ("Search", "Status", "Found", "Duration", "Error"):
        table.add_column(heading)
    for outcome in result.outcomes:
        table.add_row(
            outcome.search.slug,
            "success" if outcome.result is not None else "failed",
            str(outcome.result.search_result_count if outcome.result else 0),
            f"{outcome.duration_ms} ms",
            outcome.error_code or "",
        )
    console.print(table)
    console.print(
        f"Status {result.status.value}: found {result.found}, accepted {result.accepted}, "
        f"new {result.summary.new}, updated {result.summary.updated}, "
        f"closed {result.summary.closed}, reopened {result.summary.reopened}, "
        f"excluded {result.excluded}."
    )


def _print_jobs(jobs: list[DiscoveredJob]) -> None:
    """Display discovered jobs in a terminal table."""
    table = Table(title="Accepted positions")
    for heading in ("Type", "Company", "Title", "Location", "Link"):
        table.add_column(heading)
    for job in jobs:
        table.add_row(job.employment_type.value, job.company, job.title, job.location, job.link)
    console.print(table)


def _settings(ctx: typer.Context) -> Settings:
    """Return validated settings from the CLI context."""
    if not isinstance(ctx.obj, Settings):
        raise RuntimeError("settings were not initialized")
    return ctx.obj


def _require_linkedin_permission(settings: Settings) -> None:
    """Reject collection unless explicit authorization is configured."""
    if settings.linkedin_crawl_authorized:
        return
    error_console.print(
        "[red]LinkedIn collection is disabled.[/red] Set "
        "INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true only after express permission."
    )
    raise typer.Exit(2)


def _require_migrations(engine: Engine) -> None:
    """Reject database access when migrations are incomplete."""
    expected = migration_head(repository_root=ROOT)
    missing = missing_tables(engine)
    actual = database_revision(engine)
    if missing or actual != expected:
        error_console.print(
            "[red]Database is not migrated.[/red] Run `uv run internships db-upgrade`."
        )
        raise typer.Exit(3)


if __name__ == "__main__":
    app()
