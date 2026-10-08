"""Offline source-stop publication eligibility and durable search scheduling."""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.rules import ClassificationRules
from opportunities.config.settings import Settings
from opportunities.database.models import SearchRow
from opportunities.database.repository import Repository
from opportunities.database.session import create_database_engine, create_session_factory
from opportunities.database.snapshots import create_snapshot, verify_snapshot
from opportunities.models.raw import KnownJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.data_quality import analyze_collection_quality
from opportunities.pipeline.runner import CollectionPipeline, PipelineResult
from opportunities.scrapers.http import LINKEDIN_SEARCH_ENDPOINT, FetchError, HttpFetcher
from opportunities.scrapers.linkedin import LinkedInScrapeResult, TextFetcher

NOW = datetime(2026, 10, 8, tzinfo=UTC)


def fixed_clock(when: datetime) -> Callable[[], datetime]:
    return lambda: when


def registry(search: LinkedInSearchConfig, count: int = 3) -> list[LinkedInSearchConfig]:
    return [
        search.model_copy(
            update={
                "slug": f"search-{index}",
                "keywords": f"software intern {index}",
                "max_pages": 1,
                "max_rechecks": 0,
            }
        )
        for index in range(count)
    ]


@pytest.mark.parametrize("denial_at", [1, 2, 3, 4, 5, 6])
@pytest.mark.parametrize("denial", [429, 403, 401, 302, "challenge"])
def test_early_mid_late_source_stop_retains_only_completed_searches(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
    denial_at: int,
    denial: int | str,
) -> None:
    selected = registry(search)
    requests: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if len(requests) == denial_at:
            return (
                httpx.Response(200, text="security verification")
                if denial == "challenge"
                else httpx.Response(int(denial))
            )
        if "/search" in request.url.path:
            job_id = str(100 + int(request.url.params["keywords"].rsplit(" ", 1)[1]))
            return httpx.Response(
                200,
                text=(
                    f'<div data-entity-urn="urn:li:jobPosting:{job_id}">'
                    '<h3 class="base-search-card__title">Software Intern 2027</h3>'
                    '<h4 class="base-search-card__subtitle">Synthetic Technology</h4>'
                    '<span class="job-search-card__location">Berlin, Germany</span></div>'
                ),
            )
        return httpx.Response(
            200,
            text=(
                '<h1 class="top-card-layout__title">Software Intern 2027</h1>'
                '<a class="topcard__org-name-link">Synthetic Technology</a>'
            ),
        )

    configured = settings.model_copy(
        update={"max_concurrency": 1, "rate_limit_seconds": 0, "linkedin_crawl_authorized": True}
    )
    repository = Repository(session_factory, configured)

    async def collect() -> PipelineResult:
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client,
            HttpFetcher(configured, client=client) as fetcher,
        ):
            return await CollectionPipeline(
                settings=configured, repository=repository, rules=rules, clock=lambda: NOW
            ).run(selected, fetcher=fetcher)

    # No live transport: even authorized settings use only the synthetic response function.
    result = asyncio.run(collect())
    completed = (denial_at - 1) // 2
    assert len(requests) == denial_at  # No retry or subsequent request, at either endpoint.
    assert result.successful_searches == completed
    assert result.accepted == completed
    assert repository.stats().successful_runs == completed
    assert len(repository.list_open_jobs()) == completed
    assert result.source_blocked
    assert result.exit_code == (4 if denial == 429 and completed else 1)
    assert sum(o.error_code == "source_skipped" for o in result.outcomes) == 2 - completed
    quality = analyze_collection_quality(
        result,
        open_jobs=repository.list_open_jobs(),
        previous_snapshots=(),
        configured_searches=selected,
        generated_at=NOW,
    )
    assert quality.snapshot_json is None
    assert quality.blocking == (denial != 429 or not completed)
    assert quality.report["publication_eligible"] == (denial == 429 and completed > 0)


@pytest.mark.parametrize(
    ("denial", "cleanup"),
    [
        ("challenge", "normal"),
        *[
            (status, cleanup)
            for status in (401, 403, 302)
            for cleanup in ("normal", "unexpected", "classified")
        ],
    ],
)
def test_mixed_inflight_denials_never_qualify_for_partial_publication(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
    denial: str | int,
    cleanup: str,
) -> None:
    selected = registry(search)
    requested: list[str] = []
    hard_started = asyncio.Event()
    rate_limit_finished = asyncio.Event()

    class DenialStream(httpx.AsyncByteStream):
        def __init__(self, *, rate_limit: bool = False) -> None:
            self.rate_limit = rate_limit

        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b"security verification"

        async def aclose(self) -> None:
            if self.rate_limit:
                rate_limit_finished.set()
            elif cleanup != "normal":
                await rate_limit_finished.wait()
                if cleanup == "classified":
                    raise FetchError("http_status", "synthetic-private-cleanup", status_code=404)
                raise RuntimeError("synthetic-private-cleanup")

    async def respond(request: httpx.Request) -> httpx.Response:
        keywords = request.url.params["keywords"]
        requested.append(keywords)
        if keywords == selected[0].keywords:
            return httpx.Response(200, text="")
        if keywords == selected[1].keywords:
            await hard_started.wait()
            return httpx.Response(429, stream=DenialStream(rate_limit=True))
        hard_started.set()
        if denial == "challenge":
            await rate_limit_finished.wait()
            return httpx.Response(200, stream=DenialStream())
        return httpx.Response(int(denial), stream=DenialStream())

    configured = settings.model_copy(
        update={"max_concurrency": 3, "rate_limit_seconds": 0, "linkedin_crawl_authorized": True}
    )
    repository = Repository(session_factory, configured)

    async def collect() -> PipelineResult:
        async with (
            httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client,
            HttpFetcher(configured, client=client) as fetcher,
        ):
            result = await CollectionPipeline(
                settings=configured, repository=repository, rules=rules, clock=lambda: NOW
            ).run(selected, fetcher=fetcher)
            with pytest.raises(FetchError) as error:
                await fetcher.get_text(LINKEDIN_SEARCH_ENDPOINT)
            assert error.value.status_code == (None if denial == "challenge" else denial)
            assert not error.value.retryable
            assert "synthetic-private" not in str(error.value)
            return result

    result = asyncio.run(asyncio.wait_for(collect(), timeout=5))
    assert len(requested) == 3
    assert result.successful_searches == 1
    assert result.publication_outcome == "blocked"
    assert result.exit_code == 1
    quality = analyze_collection_quality(
        result,
        open_jobs=repository.list_open_jobs(),
        previous_snapshots=(),
        configured_searches=selected,
        generated_at=NOW,
    )
    assert quality.blocking
    assert not quality.report["publication_eligible"]
    assert quality.snapshot_json is None


class LimitedScraper:
    def __init__(self, successes: int = 2, *, interrupt: bool = False) -> None:
        self.successes = successes
        self.interrupt = interrupt
        self.interrupted = asyncio.Event()
        self.calls: list[str] = []

    async def scrape(
        self,
        search: LinkedInSearchConfig,
        fetcher: TextFetcher,
        *,
        known_jobs: tuple[KnownJob, ...] = (),
    ) -> LinkedInScrapeResult:
        self.calls.append(search.slug)
        if len(self.calls) > self.successes:
            if self.interrupt:
                self.interrupted.set()
                await asyncio.Event().wait()
            raise FetchError("source_blocked", "LinkedIn returned HTTP 429", status_code=429)
        return LinkedInScrapeResult([], (), 1, 0)


class NoNetwork:
    async def get_text(self, url: str) -> str:
        raise AssertionError("Synthetic scheduling must not fetch")


def test_multi_day_rotation_survives_snapshots_and_discarded_interruptions(
    tmp_path: Path,
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    selected = registry(search, 7)
    configured = settings.model_copy(update={"max_concurrency": 1})
    repository = Repository(session_factory, configured)
    source = tmp_path / "opportunities.db"
    completions: dict[str, list[int]] = {s.slug: [] for s in selected}
    engines = []
    try:
        for day in range(14):
            when = NOW + timedelta(days=day)
            scraper = LimitedScraper()
            result = asyncio.run(
                CollectionPipeline(
                    settings=configured,
                    repository=repository,
                    rules=rules,
                    scraper=scraper,
                    clock=fixed_clock(when),
                ).run(selected, fetcher=NoNetwork())
            )
            assert result.exit_code == 4
            assert len(scraper.calls) == 3
            for slug in scraper.calls[:2]:
                completions[slug].append(day)
            expected = repository.order_searches(selected)
            assert expected[0].slug not in scraper.calls[:2]
            snapshot, manifest = tmp_path / f"day-{day}.db", tmp_path / f"day-{day}.json"
            create_snapshot(
                source,
                snapshot,
                manifest,
                key_prefix="snapshots",
                retention_days=365,
                repository="synthetic/repository",
                run_id=str(day + 1),
                run_attempt=1,
                created_at=when + timedelta(hours=1),
            )
            verify_snapshot(snapshot, manifest)
            working = tmp_path / f"restored-{day}.db"
            shutil.copyfile(snapshot, working)
            engine = create_database_engine(f"sqlite:///{working.as_posix()}")
            engines.append(engine)
            restored = Repository(create_session_factory(engine), configured)
            assert restored.order_searches(selected) == expected
            # An interrupted disposable execution cannot advance restored durable order.
            interrupted = LimitedScraper(interrupt=True)

            async def cancel(pipeline: CollectionPipeline, scraper: LimitedScraper) -> None:
                task = asyncio.create_task(pipeline.run(selected, fetcher=NoNetwork()))
                await scraper.interrupted.wait()
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task

            asyncio.run(
                asyncio.wait_for(
                    cancel(
                        CollectionPipeline(
                            settings=configured,
                            repository=restored,
                            rules=rules,
                            scraper=interrupted,
                            clock=fixed_clock(when),
                        ),
                        interrupted,
                    ),
                    timeout=5,
                )
            )
            assert restored.order_searches(selected) == expected
            verify_snapshot(snapshot, manifest)
            repository, source = restored, working
        assert all(3 <= len(days) <= 5 for days in completions.values())
        assert all(days[0] <= 3 and 14 - days[-1] <= 4 for days in completions.values())
        assert all(max(b - a for a, b in pairwise(days)) <= 4 for days in completions.values())
    finally:
        for engine in engines:
            engine.dispose()


def test_rotation_handles_registry_changes_and_full_recovery(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    selected = registry(search)
    repository = Repository(session_factory, settings)
    configured = settings.model_copy(update={"max_concurrency": 1})
    asyncio.run(
        CollectionPipeline(
            settings=configured,
            repository=repository,
            rules=rules,
            scraper=LimitedScraper(),
            clock=lambda: NOW,
        ).run(selected, fetcher=NoNetwork())
    )
    assert repository.order_searches(selected)[0] == selected[2]
    # Editorial updates preserve progress; effective query edits reset it.
    edited = selected[0].model_copy(update={"notes": "Editorial update"})
    disabled = selected[1].model_copy(update={"enabled": False})
    added = selected[0].model_copy(update={"slug": "new-search", "keywords": "new query"})
    repository.sync_searches([edited, disabled, selected[2], added], NOW)
    assert repository.order_searches([edited, selected[2], added]) == [selected[2], added, edited]
    with session_factory() as session:
        row = session.get(SearchRow, disabled.slug)
        assert row is not None
        assert row.last_completed_at is not None
    reenabled = disabled.model_copy(update={"enabled": True})
    repository.sync_searches([edited, reenabled, selected[2], added], NOW)
    assert repository.order_searches([reenabled, selected[2]]) == [selected[2], reenabled]
    repository.sync_searches([edited, selected[2], added], NOW)
    repository.sync_searches([edited, reenabled, selected[2], added], NOW)
    assert repository.order_searches([reenabled, selected[2]]) == [selected[2], reenabled]
    changed = edited.model_copy(update={"keywords": "modified query"})
    repository.sync_searches([changed, added], NOW)
    assert repository.order_searches([changed, added]) == [changed, added]
    assert repository.stats().configured_searches == 2
    result = asyncio.run(
        CollectionPipeline(
            settings=configured,
            repository=repository,
            rules=rules,
            scraper=LimitedScraper(10),
            clock=lambda: NOW + timedelta(days=1),
        ).run([changed, added], fetcher=NoNetwork())
    )
    assert result.exit_code == 0
    assert result.publication_outcome == "full"
