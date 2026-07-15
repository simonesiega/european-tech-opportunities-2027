from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from internships.config.rules import ClassificationRules
from internships.config.settings import Settings
from internships.database.repository import Repository
from internships.models.enums import InternshipCategory
from internships.models.job import DiscoveredJob
from internships.models.raw import KnownJob, RawJob
from internships.models.search import LinkedInSearchConfig
from internships.pipeline.runner import CollectionPipeline
from internships.scrapers.http import FetchError
from internships.scrapers.linkedin import LinkedInScrapeResult, TextFetcher


class FakeScraper:
    async def scrape(
        self,
        search: LinkedInSearchConfig,
        fetcher: TextFetcher,
        *,
        known_jobs: tuple[KnownJob, ...] = (),
    ) -> LinkedInScrapeResult:
        del fetcher, known_jobs
        if search.slug == "failing-search":
            raise FetchError("timeout", "timed out")
        jobs = [
            RawJob(
                source_job_id="1111111111",
                company="Example Technology",
                title="Software Engineering Intern 2027",
                locations=["London, UK"],
                application_url="https://www.linkedin.com/jobs/view/1111111111",
                description="Software internship for summer 2027.",
            ),
            RawJob(
                source_job_id="2222222222",
                company="Example Technology",
                title="Senior Software Engineer 2027",
                locations=["London, UK"],
                application_url="https://www.linkedin.com/jobs/view/2222222222",
                description="We also run internships.",
            ),
        ]
        return LinkedInScrapeResult(
            positions=jobs,
            warnings=(),
            response_time_ms=1,
            response_bytes=100,
            pages_fetched=1,
            search_result_count=2,
        )


def test_pipeline_filters_persists_and_isolates_failed_searches(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    failing = search.model_copy(
        update={"slug": "failing-search", "keywords": "different intern 2027"}
    )
    pipeline = CollectionPipeline(
        settings=settings,
        repository=Repository(session_factory, settings),
        rules=rules,
        scraper=FakeScraper(),
    )
    result = asyncio.run(pipeline.run([search, failing], fetcher=object()))  # type: ignore[arg-type]
    assert result.successful_searches == 1
    assert result.failed_searches == 1
    assert result.found == 2
    assert result.accepted == 1
    assert result.excluded == 1
    assert result.summary.new == 1
    jobs = Repository(session_factory, settings).list_open_jobs()
    assert [(job.company, job.title) for job in jobs] == [
        ("Example Technology", "Software Engineering Intern 2027")
    ]


def test_targeted_run_keeps_full_registry_enabled(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    second = search.model_copy(update={"slug": "second-search", "keywords": "security intern 2027"})
    repository = Repository(session_factory, settings)
    pipeline = CollectionPipeline(
        settings=settings,
        repository=repository,
        rules=rules,
        scraper=FakeScraper(),
    )

    asyncio.run(
        pipeline.run(
            [search],
            configured_searches=[search, second],
            fetcher=object(),  # type: ignore[arg-type]
        )
    )

    assert repository.stats().configured_searches == 2


def test_overlapping_search_timestamps_remain_monotonic(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    earlier = datetime(2026, 7, 1, tzinfo=UTC)
    later = earlier + timedelta(minutes=5)
    second = search.model_copy(update={"slug": "second-search", "keywords": "software intern"})
    repository.sync_searches([search, second], earlier)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=InternshipCategory.SOFTWARE_ENGINEERING,
    )
    repository.persist_success(
        run_id="00000000-0000-0000-0000-000000000001",
        search=search,
        jobs=[job],
        confirmed_unavailable_ids=(),
        found_count=1,
        excluded_count=0,
        warning_count=0,
        started_at=later,
        finished_at=later,
        duration_ms=1,
    )
    repository.persist_success(
        run_id="00000000-0000-0000-0000-000000000002",
        search=second,
        jobs=[job],
        confirmed_unavailable_ids=(),
        found_count=1,
        excluded_count=0,
        warning_count=0,
        started_at=earlier,
        finished_at=earlier,
        duration_ms=1,
    )
    stored = repository.list_open_jobs()[0]
    assert stored.first_seen_at == later
    assert stored.last_seen_at == later

    health = repository.search_health()
    assert set(health) == {search.slug, second.slug}
    assert health[search.slug].accepted_count == 1


def test_distinct_linkedin_ids_are_not_fuzzy_merged_and_explicit_404s_close(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 1, tzinfo=UTC)
    repository.sync_searches([search], now)
    jobs = [
        DiscoveredJob(
            linkedin_job_id=job_id,
            company="Same Company",
            title="Software Engineering Intern 2027",
            location=location,
            link=f"https://www.linkedin.com/jobs/view/{job_id}",
            category=InternshipCategory.SOFTWARE_ENGINEERING,
        )
        for job_id, location in (
            ("1111111111", "London, UK"),
            ("2222222222", "Berlin, Germany"),
        )
    ]
    repository.persist_success(
        run_id="00000000-0000-0000-0000-000000000011",
        search=search,
        jobs=jobs,
        confirmed_unavailable_ids=(),
        found_count=2,
        excluded_count=0,
        warning_count=0,
        started_at=now,
        finished_at=now,
        duration_ms=1,
    )
    assert len(repository.list_open_jobs()) == 2

    for index in (12, 13):
        observed = now + timedelta(days=index - 11)
        repository.persist_success(
            run_id=f"00000000-0000-0000-0000-{index:012d}",
            search=search,
            jobs=[],
            confirmed_unavailable_ids=("1111111111",),
            found_count=0,
            excluded_count=0,
            warning_count=0,
            started_at=observed,
            finished_at=observed,
            duration_ms=1,
        )
    open_ids = {job.linkedin_job_id for job in repository.list_open_jobs()}
    assert open_ids == {"2222222222"}
