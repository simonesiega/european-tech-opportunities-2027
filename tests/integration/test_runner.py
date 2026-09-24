from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from opportunities.config.rules import ClassificationRules
from opportunities.config.settings import Settings
from opportunities.database.models import JobSearchRow
from opportunities.database.repository import PersistSummary, Repository
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
    result = asyncio.run(pipeline.run([search, failing], fetcher=UnexpectedFetcher()))
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
    posted_at = earlier - timedelta(days=10)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Example Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        industries="Software Development",
        employment_type=EmploymentType.INTERNSHIP,
        start_date="Summer 2027",
        posted_at=posted_at,
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
        jobs=[job.model_copy(update={"industries": None, "start_date": None, "posted_at": later})],
        confirmed_unavailable_ids=(),
        found_count=1,
        excluded_count=0,
        warning_count=0,
        started_at=earlier,
        finished_at=earlier,
        duration_ms=1,
    )
    stored = repository.list_open_jobs()[0]
    assert stored.first_seen_at == posted_at
    assert stored.last_seen_at == later
    assert stored.industries == "Software Development"
    assert stored.employment_type == EmploymentType.INTERNSHIP
    assert stored.start_date == "Summer 2027"

    health = repository.search_health()
    assert set(health) == {search.slug, second.slug}
    assert health[search.slug].accepted_count == 1


def test_newer_rediscovery_updates_fields_and_preserves_missing_optional_metadata(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    now = datetime(2026, 7, 1, tzinfo=UTC)
    repository.sync_searches([search], now)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Original Technology",
        title="Software Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        industries="Software Development",
        employment_type=EmploymentType.INTERNSHIP,
        start_date="Summer 2027",
    )

    def persist(run: int, when: datetime, incoming: DiscoveredJob) -> PersistSummary:
        return repository.persist_success(
            run_id=f"00000000-0000-0000-0000-{run:012d}",
            search=search,
            jobs=[incoming],
            confirmed_unavailable_ids=(),
            found_count=1,
            excluded_count=0,
            warning_count=0,
            started_at=when,
            finished_at=when,
            duration_ms=1,
        )

    assert persist(1, now, job).new == 1
    later = now + timedelta(minutes=5)
    changed = job.model_copy(
        update={"company": "Updated Technology", "industries": None, "start_date": None}
    )
    assert persist(2, later, changed).updated == 1
    assert persist(3, later + timedelta(minutes=1), changed).updated == 0
    stored = repository.list_open_jobs()[0]
    assert stored.company == "Updated Technology"
    assert stored.industries == "Software Development"
    assert stored.start_date == "Summer 2027"
    assert stored.last_seen_at == later + timedelta(minutes=1)
    assert stored.updated_at == later


def test_overlapping_search_404_cannot_override_a_newer_valid_observation(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    first_seen = datetime(2026, 7, 1, tzinfo=UTC)
    second = search.model_copy(update={"slug": "second-search", "keywords": "software intern"})
    repository.sync_searches([search, second], first_seen)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Current Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )

    def persist(
        run: int,
        which: LinkedInSearchConfig,
        started: datetime,
        finished: datetime,
        *,
        found: bool,
    ) -> None:
        repository.persist_success(
            run_id=f"00000000-0000-0000-0000-{run:012d}",
            search=which,
            jobs=[job] if found else [],
            confirmed_unavailable_ids=() if found else (job.linkedin_job_id,),
            found_count=int(found),
            excluded_count=0,
            warning_count=0,
            started_at=started,
            finished_at=finished,
            duration_ms=1,
        )

    persist(1, search, first_seen, first_seen, found=True)
    earlier_check = first_seen + timedelta(minutes=1)
    valid_check = first_seen + timedelta(minutes=2)
    late_finish = first_seen + timedelta(minutes=3)
    # The first search checked an old/stale detail before the second search found
    # a valid job, but spent longer processing other jobs and finished last.
    persist(2, second, valid_check, valid_check, found=True)
    persist(3, search, earlier_check, late_finish, found=False)

    assert [item.linkedin_job_id for item in repository.list_open_jobs()] == [job.linkedin_job_id]
    with session_factory() as session:
        alias = session.get(JobSearchRow, (search.slug, job.linkedin_job_id))
        assert alias is not None
        assert alias.active
        assert alias.unavailable_confirmations == 0


def test_slow_search_early_valid_detail_cannot_reopen_after_later_404(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    initial = datetime(2026, 7, 1, tzinfo=UTC)
    slow = search.model_copy(update={"slug": "slow-search", "keywords": "software intern"})
    repository.sync_searches([search, slow], initial)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Current Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )

    def persist(
        run: int,
        which: LinkedInSearchConfig,
        started: datetime,
        finished: datetime,
        *,
        found: bool,
    ) -> None:
        repository.persist_success(
            run_id=f"00000000-0000-0000-0000-{run:012d}",
            search=which,
            jobs=[job] if found else [],
            confirmed_unavailable_ids=() if found else (job.linkedin_job_id,),
            found_count=int(found),
            excluded_count=0,
            warning_count=0,
            started_at=started,
            finished_at=finished,
            duration_ms=1,
        )

    persist(1, search, initial, initial, found=True)
    persist(2, search, initial + timedelta(minutes=1), initial + timedelta(minutes=1), found=False)

    # The slow search obtained a valid detail just after minute 2, but finished
    # after another search's later 404 reached the closure threshold.
    slow_started = initial + timedelta(minutes=2)
    persist(3, search, initial + timedelta(minutes=3), initial + timedelta(minutes=4), found=False)
    persist(4, slow, slow_started, initial + timedelta(minutes=5), found=True)

    assert repository.list_open_jobs() == []
    with session_factory() as session:
        assert session.get(JobSearchRow, (slow.slug, job.linkedin_job_id)) is None


def test_stale_observations_cannot_overwrite_metadata_or_newer_closure(
    session_factory: sessionmaker[Session],
    settings: Settings,
    search: LinkedInSearchConfig,
) -> None:
    repository = Repository(session_factory, settings)
    earlier = datetime(2026, 7, 1, tzinfo=UTC)
    later = earlier + timedelta(minutes=5)
    repository.sync_searches([search], earlier)
    job = DiscoveredJob(
        linkedin_job_id="1111111111",
        company="Current Technology",
        title="Software Engineering Intern 2027",
        location="London, UK",
        link="https://www.linkedin.com/jobs/view/1111111111",
        category=OpportunityCategory.SOFTWARE_ENGINEERING,
        employment_type=EmploymentType.INTERNSHIP,
    )

    def persist(
        run: str, when: datetime, jobs: list[DiscoveredJob], unavailable: bool = False
    ) -> None:
        repository.persist_success(
            run_id=f"00000000-0000-0000-0000-{run:0>12}",
            search=search,
            jobs=jobs,
            confirmed_unavailable_ids=(job.linkedin_job_id,) if unavailable else (),
            found_count=len(jobs),
            excluded_count=0,
            warning_count=0,
            started_at=when,
            finished_at=when,
            duration_ms=1,
        )

    persist("1", later, [job])
    persist("2", earlier, [job.model_copy(update={"company": "Stale Technology"})])
    persist("3", earlier, [], unavailable=True)
    assert repository.list_open_jobs()[0].company == "Current Technology"
    with session_factory() as session:
        alias = session.get(JobSearchRow, (search.slug, job.linkedin_job_id))
        assert alias is not None
        assert alias.unavailable_confirmations == 0

    persist("4", later + timedelta(minutes=1), [], unavailable=True)
    persist("5", later + timedelta(minutes=2), [], unavailable=True)
    assert repository.list_open_jobs() == []
    persist("6", earlier, [job])
    assert repository.list_open_jobs() == []


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
            category=OpportunityCategory.SOFTWARE_ENGINEERING,
            employment_type=EmploymentType.INTERNSHIP,
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
