"""Typer CLI for collection, SQLite lifecycle state, and generated projections."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table
from sqlalchemy import Engine

from opportunities.config.rules import load_classification_rules
from opportunities.config.search_registry import (
    SearchRegistryError,
    load_search_registry,
    select_searches,
)
from opportunities.config.settings import Settings, apply_search_overrides, load_settings
from opportunities.database.migrations import migration_head, upgrade_database
from opportunities.database.repository import PersistSummary, Repository, SearchHealth
from opportunities.database.session import (
    create_database_engine,
    create_session_factory,
    database_exists,
    database_revision,
    missing_tables,
)
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.availability import audit_job_availability
from opportunities.pipeline.runner import CollectionPipeline, PipelineResult
from opportunities.public_exports import render_public_exports, validate_public_exports
from opportunities.readme import ReadmeMetadata, render_readme, validate_readme
from opportunities.search_registry_docs import (
    render_search_registry_docs,
    validate_search_registry_docs,
)
from opportunities.utils.logging import configure_logging
from opportunities.utils.paths import find_project_root
from opportunities.utils.time import ensure_utc, utc_now
from opportunities.utils.url import extract_linkedin_job_id

# App context and console for output. ROOT locates source-checkout or wheel-packaged migrations.
try:
    ROOT = find_project_root(Path(__file__))
except RuntimeError:
    packaged_root = Path(__file__).resolve().parents[1] / "resources"
    if not all((packaged_root / marker).exists() for marker in ("alembic.ini", "migrations")):
        raise
    ROOT = packaged_root
console = Console()
error_console = Console(stderr=True)
app = typer.Typer(
    no_args_is_help=True,
    help=(
        "Collect strict 2027 European tech internships and new-grad roles into SQLite with "
        "read-only public projections."
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
        bool, typer.Option("--no-render", help="Do not update generated projections.")
    ] = False,
) -> None:
    """Collect internships and new-grad roles, then optionally refresh projections."""
    settings = _settings(ctx)
    _require_linkedin_permission(settings)
    repository, engine = _repository(settings)
    try:
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
                _render_projections(settings, repository)
                console.print(
                    f"Generated projections updated: {settings.readme_path}; "
                    f"public exports: {settings.public_export_dir}"
                )
        except (SearchRegistryError, OSError, ValueError, ValidationError) as exc:
            error_console.print(f"[red]Scrape failed:[/red] {exc}")
            raise typer.Exit(2) from exc
    finally:
        _dispose_engine(engine)
    raise typer.Exit(result.exit_code)


@app.command("check-availability")
def check_availability(
    ctx: typer.Context,
    no_render: Annotated[
        bool, typer.Option("--no-render", help="Do not update generated projections.")
    ] = False,
) -> None:
    """Check every stored job page and delete explicitly unavailable rows."""
    settings = _settings(ctx)
    _require_linkedin_permission(settings)
    repository, engine = _repository(settings)
    try:
        _require_migrations(engine)
        result = asyncio.run(audit_job_availability(settings=settings, repository=repository))
        if not no_render:
            _render_projections(settings, repository)
        console.print(
            f"Checked {result.checked} position(s): {result.available} available, "
            f"{result.deleted} deleted, {result.reopened} reopened, "
            f"{len(result.inconclusive_ids)} inconclusive."
        )
    finally:
        _dispose_engine(engine)
    raise typer.Exit(result.exit_code)


@app.command("add-job")
def add_job(
    ctx: typer.Context,
    url: Annotated[str, typer.Option("--url", help="Public LinkedIn /jobs/view/<id> URL.")],
    company: Annotated[str, typer.Option("--company", help="Company name.")],
    title: Annotated[str, typer.Option("--title", help="Opportunity title.")],
    location: Annotated[str, typer.Option("--location", help="European job location.")],
    category: Annotated[
        OpportunityCategory, typer.Option("--category", help="Technology category.")
    ],
    employment_type: Annotated[
        EmploymentType, typer.Option("--employment-type", help="Internship or New Grad.")
    ],
    industries: Annotated[
        str | None, typer.Option("--industries", help="Optional industries metadata.")
    ] = None,
    start_date: Annotated[
        str | None, typer.Option("--start-date", help="Optional start date metadata.")
    ] = None,
    posted_at: Annotated[
        str | None, typer.Option("--posted-at", help="Optional ISO-8601 posting timestamp.")
    ] = None,
    no_render: Annotated[
        bool, typer.Option("--no-render", help="Do not update generated projections.")
    ] = False,
) -> None:
    """Add a known LinkedIn job directly to canonical state without provenance."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    try:
        _require_migrations(engine)
        try:
            observed_at = utc_now()
            job = DiscoveredJob(
                linkedin_job_id=extract_linkedin_job_id(url),
                company=company,
                title=title,
                location=location,
                link=url,
                category=category,
                industries=industries,
                employment_type=employment_type,
                start_date=start_date,
                posted_at=_parse_iso_timestamp(posted_at) if posted_at is not None else None,
            )
            summary = repository.upsert_manual_job(job, observed_at=observed_at)
            if not no_render:
                _render_projections(settings, repository)
        except (OSError, ValueError, ValidationError) as exc:
            error_console.print(f"[red]Add job failed:[/red] {exc}")
            raise typer.Exit(2) from exc
        action = _manual_job_action(summary)
        console.print(f"Job {job.linkedin_job_id} {action}.")
    finally:
        _dispose_engine(engine)


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
        _dispose_engine(engine)


@app.command()
def render(ctx: typer.Context) -> None:
    """Refresh generated README, registry documentation, and public exports."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    try:
        _require_migrations(engine)
        _configured_searches(settings)
        open_job_count = _render_projections(settings, repository)
        console.print(
            f"Generated projections updated for {open_job_count} open position(s); "
            f"public exports: {settings.public_export_dir}."
        )
    finally:
        _dispose_engine(engine)


@app.command("export-public")
def export_public(ctx: typer.Context) -> None:
    """Generate sanitized CSV and JSON projections of open opportunities."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    try:
        _require_migrations(engine)
        open_jobs = repository.list_open_jobs()
        render_public_exports(settings.public_export_dir, open_jobs)
        console.print(f"Public exports updated for {len(open_jobs)} open position(s).")
    finally:
        _dispose_engine(engine)


@app.command()
def searches(ctx: typer.Context) -> None:
    """Display configured searches and their latest health."""
    settings = _settings(ctx)
    try:
        configured = apply_search_overrides(
            load_search_registry(settings.search_config_dir), settings
        )
    except (SearchRegistryError, OSError, ValueError, ValidationError) as exc:
        error_console.print(f"[red]Search configuration error:[/red] {exc}")
        raise typer.Exit(2) from exc
    health: dict[str, SearchHealth] = {}
    if database_exists(settings.database_url):
        repository, engine = _repository(settings)
        try:
            if not missing_tables(engine) and database_revision(engine) == migration_head(
                repository_root=ROOT
            ):
                health = repository.search_health()
        finally:
            _dispose_engine(engine)

    table = Table(title="LinkedIn searches")
    table.add_column("Slug", no_wrap=True)
    for heading in ("Scope", "Enabled", "Limits P/R/C", "Last", "F/A"):
        table.add_column(heading)
    for item in configured:
        state = health.get(item.slug)
        status = state.status if state else "never-run"
        table.add_row(
            item.slug,
            item.location,
            "yes" if item.enabled else "no",
            f"{item.max_pages}/{item.max_results}/{item.max_rechecks}",
            status,
            f"{state.found_count}/{state.accepted_count}" if state else "-/-",
        )
    console.print(table)


@app.command()
def stats(ctx: typer.Context) -> None:
    """Display aggregate pipeline and database statistics."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    try:
        _require_migrations(engine)
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
        _dispose_engine(engine)


@app.command()
def validate(ctx: typer.Context) -> None:
    """Validate database invariants and generated projections."""
    settings = _settings(ctx)
    repository, engine = _repository(settings)
    try:
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
        errors.extend(validate_public_exports(settings.public_export_dir, open_jobs))
        jobs = repository.list_all_jobs()
        for job in jobs:
            if job.last_seen_at < job.first_seen_at:
                errors.append(f"job {job.linkedin_job_id}: last_seen_at precedes first_seen_at")
    finally:
        _dispose_engine(engine)
    if errors:
        for error in errors:
            error_console.print(f"[red]- {error}[/red]")
        raise typer.Exit(1)
    console.print(f"Valid: {len(jobs)} database position(s) and README checked.")


def _configured_searches(settings: Settings) -> list[LinkedInSearchConfig]:
    """Load configured searches with runtime overrides."""
    return apply_search_overrides(load_search_registry(settings.search_config_dir), settings)


def _parse_iso_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 CLI timestamp and normalize it to aware UTC."""
    candidate = value.strip()
    if "T" not in candidate and " " not in candidate:
        raise ValueError("posted_at must be a valid ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("posted_at must be a valid ISO-8601 timestamp") from exc
    return ensure_utc(parsed)


def _manual_job_action(summary: PersistSummary) -> str:
    """Describe the exact outcome of one manual job upsert."""
    if summary.new:
        return "added"
    if summary.updated and summary.reopened:
        return "updated and reopened"
    if summary.updated:
        return "updated"
    if summary.reopened:
        return "reopened"
    return "already current"


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
    try:
        return Repository(create_session_factory(engine), settings), engine
    except BaseException:
        _dispose_engine(engine)
        raise


def _dispose_engine(engine: Engine) -> None:
    """Dispose one CLI-owned engine without replacing an active command failure."""
    pending_exception = sys.exception()
    try:
        engine.dispose()
    except Exception:
        if pending_exception is None:
            raise


def _search_registry_docs_path(settings: Settings) -> Path:
    """Resolve registry documentation beside the configured README."""
    return settings.readme_path.parent / "docs" / "guides" / "user-guide" / "search-registry.md"


def _render_projections(settings: Settings, repository: Repository) -> int:
    """Refresh every read-only projection from one open-job snapshot."""
    open_jobs = repository.list_open_jobs()
    render_readme(
        settings.readme_path,
        open_jobs,
        _readme_metadata(repository),
    )
    render_search_registry_docs(_search_registry_docs_path(settings), settings.search_config_dir)
    render_public_exports(settings.public_export_dir, open_jobs)
    return len(open_jobs)


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
        "OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true only after express permission."
    )
    raise typer.Exit(2)


def _require_migrations(engine: Engine) -> None:
    """Reject database access when migrations are incomplete."""
    expected = migration_head(repository_root=ROOT)
    missing = missing_tables(engine)
    actual = database_revision(engine)
    if missing or actual != expected:
        error_console.print(
            "[red]Database is not migrated.[/red] Run `uv run opportunities db-upgrade`."
        )
        raise typer.Exit(3)


if __name__ == "__main__":
    app()
