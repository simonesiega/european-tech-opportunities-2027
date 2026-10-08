from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.rules import ClassificationRules
from opportunities.config.settings import Settings
from opportunities.database.models import JobSearchRow, SearchRunRow
from opportunities.database.repository import Repository
from opportunities.models.enums import EmploymentType, OpportunityCategory
from opportunities.models.job import DiscoveredJob
from opportunities.models.raw import KnownJob, RawJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.pipeline.runner import CollectionPipeline, SearchOutcome
from opportunities.scrapers.http import LINKEDIN_DETAIL_ENDPOINT, FetchError
from opportunities.scrapers.linkedin import (
    LinkedInScraper,
    LinkedInScrapeResult,
    TextFetcher,
    build_search_url,
)


class UnexpectedFetcher:
    async def get_text(self, url: str) -> str:
        raise AssertionError(f"unexpected network request: {url}")


class FakeScraper:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure or FetchError("timeout", "timed out")

    async def scrape(
        self,
        search: LinkedInSearchConfig,
        fetcher: TextFetcher,
        *,
        known_jobs: tuple[KnownJob, ...] = (),
    ) -> LinkedInScrapeResult:
        del fetcher, known_jobs
        if search.slug == "failing-search":
            raise self.failure
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
            pages_fetched=1,
            search_result_count=2,
        )


@pytest.mark.parametrize(
    ("failure", "code"),
    [
        (FetchError("timeout", "timed out"), "timeout"),
        (FetchError("source_blocked", "LinkedIn access denied", status_code=429), "source_blocked"),
        (ValueError("synthetic-private-payload"), "invalid_html"),
        (RuntimeError("synthetic-private-payload"), "unexpected"),
    ],
)
def test_pipeline_filters_persists_and_isolates_failed_searches(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
    failure: Exception,
    code: str,
) -> None:
    failing = search.model_copy(update={"slug": "failing-search", "keywords": "different intern"})
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 20, tzinfo=UTC)
    repository.sync_searches([search, failing], now)
    previous = DiscoveredJob(
        linkedin_job_id="9999999999",
        company="Previously Seen Technology",
        title="Software Intern 2027",
        location="Berlin, Germany",
        link="https://www.linkedin.com/jobs/view/9999999999",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )
    # Leave the failing search one 404 short of closure to expose leaked failure evidence.
    for index in (0, 1):
        repository.persist_success(
            run_id=f"seed-{index}",
            search=failing,
            jobs=[previous] if index == 0 else [],
            confirmed_unavailable_ids=(previous.linkedin_job_id,) if index == 1 else (),
            found_count=1 if index == 0 else 0,
            excluded_count=0,
            warning_count=0,
            started_at=now + timedelta(minutes=index),
            finished_at=now + timedelta(minutes=index),
            duration_ms=1,
        )
    original = repository.list_all_jobs()[0]
    pipeline = CollectionPipeline(
        settings=settings,
        repository=repository,
        rules=rules,
        scraper=FakeScraper(failure),
        clock=lambda: now + timedelta(minutes=2),
    )
    result = asyncio.run(pipeline.run([search, failing], fetcher=UnexpectedFetcher()))
    assert result.successful_searches == 1
    assert result.failed_searches == 1
    assert result.exit_code == (1 if code == "source_blocked" else 2)
    assert result.source_blocked == (code == "source_blocked")
    assert result.found == 2
    assert result.accepted == 1
    assert result.excluded == 1
    assert [(o.accepted_count, o.excluded_count) for o in result.outcomes] == [(1, 1), (0, 0)]
    assert result.summary.new == 1
    jobs = {job.linkedin_job_id: job for job in repository.list_open_jobs()}
    assert set(jobs) == {"1111111111", previous.linkedin_job_id}
    assert (jobs["1111111111"].company, jobs["1111111111"].title) == (
        "Example Technology",
        "Software Engineering Intern 2027",
    )
    assert jobs[previous.linkedin_job_id] == original
    with session_factory() as session:
        alias = session.get(JobSearchRow, (failing.slug, previous.linkedin_job_id))
        assert alias is not None
        assert alias.active
        assert alias.unavailable_confirmations == 1
        assert alias.last_seen_run_id == "seed-0"
        diagnostic = session.scalar(select(SearchRunRow).where(SearchRunRow.status == "failed"))
        assert diagnostic is not None
        assert diagnostic.error_code == code
        assert "synthetic-private-payload" not in (diagnostic.error_message or "")


def test_collection_uses_explicit_cycle_when_posting_age_is_missing(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    observed = datetime(2026, 7, 20, tzinfo=UTC)
    first_id, second_id = "1111111111", "2222222222"
    cards = "".join(
        f'<div data-entity-urn="urn:li:jobPosting:{job_id}">'
        f'<h3 class="base-search-card__title">{title}</h3>'
        '<h4 class="base-search-card__subtitle">Test Technology</h4>'
        '<span class="job-search-card__location">Berlin, Germany</span></div>'
        for job_id, title in (
            (first_id, "Software Engineering Intern 2027"),
            (second_id, "Software Engineering Intern"),
        )
    )
    responses = {
        build_search_url(search, start=0, observed_at=observed): cards,
        **{
            LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_id): (
                f'<h1 class="top-card-layout__title">{title}</h1>'
                '<a class="topcard__org-name-link">Test Technology</a>'
            )
            for job_id, title in (
                (first_id, "Software Engineering Intern 2027"),
                (second_id, "Software Engineering Intern"),
            )
        },
    }

    class OfflineFetcher:
        async def get_text(self, url: str) -> str:
            return responses[url]

    repository = Repository(session_factory, settings)
    result = asyncio.run(
        CollectionPipeline(
            settings=settings,
            repository=repository,
            rules=rules,
            scraper=LinkedInScraper(clock=lambda: observed),
            clock=lambda: observed,
        ).run([search], fetcher=OfflineFetcher())
    )

    assert result.accepted == 1
    assert result.excluded == 1
    assert [job.linkedin_job_id for job in repository.list_open_jobs()] == [first_id]


def test_malformed_detail_does_not_publish_a_current_search_card(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    class OfflineFetcher:
        async def get_text(self, url: str) -> str:
            if "/search?" in url:
                return (
                    '<div data-entity-urn="urn:li:jobPosting:1111111111">'
                    '<h3 class="base-search-card__title">Software Intern 2027</h3>'
                    '<h4 class="base-search-card__subtitle">Test Technology</h4>'
                    '<span class="job-search-card__location">Berlin, Germany</span></div>'
                )
            return "<html><body>Temporarily unavailable</body></html>"

    repository = Repository(session_factory, settings)
    result = asyncio.run(
        CollectionPipeline(settings=settings, repository=repository, rules=rules).run(
            [search], fetcher=OfflineFetcher()
        )
    )

    assert result.failed_searches == 1
    assert result.accepted == 0
    assert result.exit_code == 1
    assert repository.list_all_jobs() == []
    assert repository.stats().successful_runs == 0


def test_concurrent_search_outcomes_apply_in_observation_order(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    earlier = datetime(2026, 7, 1, tzinfo=UTC)
    later = earlier + timedelta(minutes=1)
    second = search.model_copy(update={"slug": "second-search", "keywords": "engineering intern"})

    def outcome(which: LinkedInSearchConfig, when: datetime, company: str) -> SearchOutcome:
        return SearchOutcome(
            search=which,
            run_id=f"00000000-0000-0000-0000-00000000000{1 if which == search else 2}",
            started_at=when,
            finished_at=when,
            duration_ms=1,
            result=LinkedInScrapeResult(
                positions=[
                    RawJob(
                        source_job_id="1111111111",
                        company=company,
                        title="Software Engineering Intern 2027",
                        locations=["London, UK"],
                        application_url="https://www.linkedin.com/jobs/view/1111111111",
                    )
                ],
                warnings=(),
                pages_fetched=1,
                search_result_count=1,
            ),
        )

    # Force out-of-order outcomes without depending on scheduler timing or sleeps.
    class ReversedPipeline(CollectionPipeline):
        async def _fetch_all(
            self, searches: list[LinkedInSearchConfig], fetcher: TextFetcher
        ) -> list[SearchOutcome]:
            del searches, fetcher
            return [
                outcome(second, later, "Newest Technology"),
                outcome(search, earlier, "Old Technology"),
            ]

    repository = Repository(session_factory, settings)
    result = asyncio.run(
        ReversedPipeline(settings=settings, repository=repository, rules=rules).run(
            [search, second], fetcher=UnexpectedFetcher()
        )
    )

    assert result.successful_searches == 2
    assert repository.list_open_jobs()[0].company == "Newest Technology"
    with session_factory() as session:
        assert session.get(JobSearchRow, (search.slug, "1111111111")) is not None
        assert session.get(JobSearchRow, (second.slug, "1111111111")) is not None


def test_equal_finish_times_keep_configured_search_order(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    observed = datetime(2026, 7, 1, tzinfo=UTC)
    second = search.model_copy(update={"slug": "second-search", "keywords": "engineering intern"})

    def outcome(which: LinkedInSearchConfig, run_id: str, company: str) -> SearchOutcome:
        return SearchOutcome(
            search=which,
            run_id=run_id,
            started_at=observed,
            finished_at=observed,
            duration_ms=1,
            result=LinkedInScrapeResult(
                positions=[
                    RawJob(
                        source_job_id="1111111111",
                        company=company,
                        title="Software Engineering Intern 2027",
                        locations=["London, UK"],
                        application_url="https://www.linkedin.com/jobs/view/1111111111",
                    )
                ],
                warnings=(),
                pages_fetched=1,
                search_result_count=1,
            ),
        )

    class TiedPipeline(CollectionPipeline):
        async def _fetch_all(
            self, searches: list[LinkedInSearchConfig], fetcher: TextFetcher
        ) -> list[SearchOutcome]:
            del fetcher
            assert searches == [search, second]
            # Run IDs have the opposite lexical order from the configured searches.
            return [
                outcome(search, "00000000-0000-0000-0000-000000000002", "First Technology"),
                outcome(second, "00000000-0000-0000-0000-000000000001", "Second Technology"),
            ]

    repository = Repository(session_factory, settings)
    result = asyncio.run(
        TiedPipeline(
            settings=settings, repository=repository, rules=rules, clock=lambda: observed
        ).run([search, second], fetcher=UnexpectedFetcher())
    )

    assert result.successful_searches == 2
    assert repository.list_open_jobs()[0].company == "Second Technology"


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
            fetcher=UnexpectedFetcher(),
        )
    )

    assert repository.stats().configured_searches == 2


@pytest.mark.parametrize("injected_fetcher", [False, True])
def test_search_preview_classifies_without_persisting(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
    injected_fetcher: bool,
) -> None:
    repository = Repository(session_factory, settings)
    before = repository.stats()
    pipeline = CollectionPipeline(
        settings=settings,
        repository=repository,
        rules=rules,
        scraper=FakeScraper(),
    )
    result, jobs, excluded = asyncio.run(
        pipeline.test_search(
            search,
            fetcher=UnexpectedFetcher() if injected_fetcher else None,
        )
    )
    assert result.search_result_count == 2
    assert [job.linkedin_job_id for job in jobs] == ["1111111111"]
    assert excluded == 1
    assert repository.stats() == before
    assert repository.list_all_jobs() == []
    with session_factory() as session:
        assert session.scalars(select(JobSearchRow)).all() == []


def test_empty_search_selection_fails_before_persistence(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
) -> None:
    repository = Repository(session_factory, settings)
    before = repository.stats()
    with pytest.raises(ValueError, match="no enabled LinkedIn searches"):
        asyncio.run(
            CollectionPipeline(settings=settings, repository=repository, rules=rules).run(
                [],
                fetcher=UnexpectedFetcher(),
            )
        )
    assert repository.stats() == before


def test_normalized_oversize_location_is_excluded_without_losing_valid_jobs(
    session_factory: sessionmaker[Session],
    settings: Settings,
    rules: ClassificationRules,
    search: LinkedInSearchConfig,
) -> None:
    class OversizedLocationScraper(FakeScraper):
        async def scrape(
            self,
            search: LinkedInSearchConfig,
            fetcher: TextFetcher,
            *,
            known_jobs: tuple[KnownJob, ...] = (),
        ) -> LinkedInScrapeResult:
            result = await super().scrape(search, fetcher, known_jobs=known_jobs)
            # Each location fits alone; joining them exceeds the canonical field limit.
            invalid = RawJob(
                source_job_id="3333333333",
                company="Synthetic Technology",
                title="Software Intern 2027",
                locations=[f"District {index}, " + "x" * 250 + ", Germany" for index in range(3)],
                application_url="https://www.linkedin.com/jobs/view/3333333333",
            )
            return LinkedInScrapeResult(
                positions=[*result.positions, invalid],
                warnings=(),
                pages_fetched=1,
                search_result_count=3,
            )

    repository = Repository(session_factory, settings)
    result = asyncio.run(
        CollectionPipeline(
            settings=settings,
            repository=repository,
            rules=rules,
            scraper=OversizedLocationScraper(),
            clock=lambda: datetime(2026, 7, 20, tzinfo=UTC),
        ).run([search], fetcher=UnexpectedFetcher())
    )
    assert result.exit_code == 0
    assert result.accepted == 1
    assert result.excluded == 2
    assert [job.linkedin_job_id for job in repository.list_open_jobs()] == ["1111111111"]
