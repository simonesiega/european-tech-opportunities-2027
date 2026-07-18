"""Orchestration for LinkedIn HTML → strict filtering → SQLite."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import ValidationError

from opportunities.config.rules import ClassificationRules
from opportunities.config.settings import Settings
from opportunities.database.repository import PersistSummary, Repository
from opportunities.models.enums import RunStatus
from opportunities.models.job import DiscoveredJob
from opportunities.models.raw import KnownJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.normalization.location import normalize_locations
from opportunities.normalization.title import normalize_title
from opportunities.pipeline.classification import Classifier
from opportunities.scrapers.http import FetchError, HttpFetcher
from opportunities.scrapers.linkedin import LinkedInScraper, LinkedInScrapeResult, TextFetcher
from opportunities.utils.time import utc_now

Clock = Callable[[], datetime]


class Scraper(Protocol):
    """Define the scraper interface used by the pipeline."""

    async def scrape(
        self,
        search: LinkedInSearchConfig,
        fetcher: TextFetcher,
        *,
        known_jobs: tuple[KnownJob, ...] = (),
    ) -> LinkedInScrapeResult:
        """Collect jobs for one configured search."""
        ...


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    """Describe the outcome of one configured search."""

    search: LinkedInSearchConfig
    run_id: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    result: LinkedInScrapeResult | None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Summarize all outcomes from a pipeline run."""

    status: RunStatus
    successful_searches: int
    failed_searches: int
    found: int
    accepted: int
    excluded: int
    warnings: int
    summary: PersistSummary
    outcomes: tuple[SearchOutcome, ...]

    @property
    def exit_code(self) -> int:
        """Return a process exit code derived from search outcomes."""
        if self.status == RunStatus.SUCCESS:
            return 0
        if self.status == RunStatus.PARTIAL:
            return 2
        return 1


class CollectionPipeline:
    """Coordinate collection, classification, and persistence."""

    def __init__(
        self,
        *,
        settings: Settings,
        repository: Repository,
        rules: ClassificationRules,
        scraper: Scraper | None = None,
        clock: Clock = utc_now,
    ) -> None:
        """Initialize the instance dependencies and state."""
        self.settings = settings
        self.repository = repository
        self.classifier = Classifier(rules, settings.target_cycle)
        self.scraper = scraper or LinkedInScraper(
            rules.internship_keywords,
            rules.new_grad_keywords,
            clock=clock,
        )
        self.clock = clock

    async def run(
        self,
        searches: list[LinkedInSearchConfig],
        *,
        configured_searches: list[LinkedInSearchConfig] | None = None,
        fetcher: TextFetcher | None = None,
    ) -> PipelineResult:
        """Run selected searches and persist isolated outcomes."""
        if not searches:
            raise ValueError("no enabled LinkedIn searches matched the selection")
        self.repository.sync_searches(configured_searches or searches, self.clock())
        if fetcher is None:
            async with HttpFetcher(self.settings) as managed:
                outcomes = await self._fetch_all(searches, managed)
        else:
            outcomes = await self._fetch_all(searches, fetcher)

        successful = failed = found = accepted = excluded = warnings = 0
        summary = PersistSummary()
        for outcome in outcomes:
            if outcome.result is None:
                # Persist each failure independently; one broken search must not roll
                # back successful searches from the same collection run.
                failed += 1
                self.repository.persist_failure(
                    run_id=outcome.run_id,
                    search_slug=outcome.search.slug,
                    started_at=outcome.started_at,
                    finished_at=outcome.finished_at,
                    duration_ms=outcome.duration_ms,
                    error_code=outcome.error_code or "unknown",
                    error_message=outcome.error_message or "LinkedIn search failed",
                )
                continue
            jobs, search_excluded = self._classify(outcome.result)
            result = outcome.result
            summary += self.repository.persist_success(
                run_id=outcome.run_id,
                search=outcome.search,
                jobs=jobs,
                confirmed_unavailable_ids=result.confirmed_unavailable_ids,
                found_count=result.search_result_count,
                excluded_count=search_excluded,
                warning_count=len(result.warnings),
                started_at=outcome.started_at,
                finished_at=outcome.finished_at,
                duration_ms=outcome.duration_ms,
            )
            successful += 1
            found += result.search_result_count
            accepted += len(jobs)
            excluded += search_excluded
            warnings += len(result.warnings)

        if not successful:
            status = RunStatus.FAILED
        elif failed:
            status = RunStatus.PARTIAL
        else:
            status = RunStatus.SUCCESS
        return PipelineResult(
            status=status,
            successful_searches=successful,
            failed_searches=failed,
            found=found,
            accepted=accepted,
            excluded=excluded,
            warnings=warnings,
            summary=summary,
            outcomes=tuple(outcomes),
        )

    async def test_search(
        self, search: LinkedInSearchConfig, *, fetcher: TextFetcher | None = None
    ) -> tuple[LinkedInScrapeResult, list[DiscoveredJob], int]:
        """Run one search without persistence."""
        if fetcher is None:
            async with HttpFetcher(self.settings) as managed:
                result = await self.scraper.scrape(search, managed)
        else:
            result = await self.scraper.scrape(search, fetcher)
        jobs, excluded = self._classify(result)
        return result, jobs, excluded

    def _classify(self, result: LinkedInScrapeResult) -> tuple[list[DiscoveredJob], int]:
        """Classify scraped jobs and collect accepted records."""
        # Multiple searches or duplicate cards may expose the same LinkedIn ID;
        # publication and persistence use one canonical record per source ID.
        jobs: dict[str, DiscoveredJob] = {}
        excluded = 0
        for raw in result.positions:
            try:
                title = normalize_title(raw.title)
                location = normalize_locations(raw.locations)
                decision = self.classifier.classify(
                    title=title,
                    description=raw.description,
                    location=location,
                )
                if not decision.include:
                    excluded += 1
                    continue
                display_location = "; ".join(location.locations)
                if not display_location or decision.employment_type is None:
                    excluded += 1
                    continue
                jobs[raw.source_job_id] = DiscoveredJob(
                    linkedin_job_id=raw.source_job_id,
                    company=raw.company,
                    title=title,
                    location=display_location,
                    link=raw.application_url,
                    category=decision.category,
                    industries=raw.industries,
                    employment_type=decision.employment_type,
                    start_date=raw.start_date,
                    posted_at=raw.posted_at,
                )
            except (ValidationError, ValueError):
                excluded += 1
        return list(jobs.values()), excluded

    async def _fetch_all(
        self, searches: list[LinkedInSearchConfig], fetcher: TextFetcher
    ) -> list[SearchOutcome]:
        """Run selected searches concurrently within configured limits."""
        # Limit complete search workflows, not only individual HTTP calls, so parsing
        # and database lookups cannot create an unbounded number of active tasks.
        semaphore = asyncio.Semaphore(self.settings.max_concurrency)

        async def fetch(search: LinkedInSearchConfig) -> SearchOutcome:
            """Collect one search while isolating its errors."""
            async with semaphore:
                run_id = str(uuid.uuid4())
                started_at = self.clock()
                started = time.monotonic()
                try:
                    result = await self.scraper.scrape(
                        search,
                        fetcher,
                        known_jobs=self.repository.known_jobs(search.slug),
                    )
                    return SearchOutcome(
                        search=search,
                        run_id=run_id,
                        started_at=started_at,
                        finished_at=self.clock(),
                        duration_ms=round((time.monotonic() - started) * 1000),
                        result=result,
                    )
                except FetchError as exc:
                    code, message = exc.code, str(exc)
                except (ValidationError, ValueError) as exc:
                    code, message = "invalid_html", f"LinkedIn HTML rejected: {type(exc).__name__}"
                # Preserve batch progress for unexpected provider/parser failures while
                # keeping potentially sensitive exception details out of persisted logs.
                except Exception as exc:
                    code, message = "unexpected", f"unexpected failure: {type(exc).__name__}"
                return SearchOutcome(
                    search=search,
                    run_id=run_id,
                    started_at=started_at,
                    finished_at=self.clock(),
                    duration_ms=round((time.monotonic() - started) * 1000),
                    result=None,
                    error_code=code,
                    error_message=message,
                )

        return list(await asyncio.gather(*(fetch(search) for search in searches)))
