from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping

import pytest

from internships.models.raw import KnownJob
from internships.models.search import LinkedInSearchConfig
from internships.scrapers.http import FetchError
from internships.scrapers.linkedin import (
    LINKEDIN_DETAIL_ENDPOINT,
    LinkedInPayloadError,
    LinkedInScraper,
    build_search_url,
    parse_job_detail,
    parse_search_page,
)


class FixtureFetcher:
    def __init__(self, responses: Mapping[str, str | FetchError]) -> None:
        self.responses = dict(responses)
        self.calls: list[str] = []

    async def get_text(self, url: str) -> str:
        self.calls.append(url)
        configured = self.responses[url]
        if isinstance(configured, FetchError):
            raise configured
        return configured


def configured_search(**changes: object) -> LinkedInSearchConfig:
    values: dict[str, object] = {
        "name": "Test LinkedIn search",
        "slug": "test-linkedin",
        "keywords": "software intern 2027",
        "location": "Europe",
        "geo_id": "91000000",
        "max_pages": 2,
        "max_results": 50,
    }
    values.update(changes)
    return LinkedInSearchConfig.model_validate(values)


def test_linkedin_search_page_parser_extracts_stable_cards(
    fixture_html: Callable[[str], str],
) -> None:
    result = parse_search_page(fixture_html("linkedin_search_page_1.html"))
    assert not result.warnings
    assert [card.job_id for card in result.cards] == ["1111111111", "2222222222"]
    assert result.cards[0].company == "Test Technology"
    assert result.cards[0].application_url == ("https://www.linkedin.com/jobs/view/1111111111")


def test_linkedin_job_detail_parser_extracts_description(
    fixture_html: Callable[[str], str],
) -> None:
    card = parse_search_page(fixture_html("linkedin_search_page_1.html")).cards[0]
    job = parse_job_detail(
        fixture_html("linkedin_job_detail_1111111111.html"),
        card,
    )
    assert job.source_job_id == "1111111111"
    assert job.company == "Test Technology"
    assert job.description is not None
    assert "Summer 2027" in job.description
    assert job.start_date == "Summer 2027"
    assert job.industries == "Software Development"


def test_linkedin_job_detail_extracts_criteria_without_linkedin_classes(
    fixture_html: Callable[[str], str],
) -> None:
    card = parse_search_page(fixture_html("linkedin_search_page_1.html")).cards[0]
    html = """<!doctype html>
    <h1 class="top-card-layout__title">Software Engineering Intern 2027</h1>
    <a class="topcard__org-name-link">Test Technology</a>
    <ul>
      <li><h3>Employment type</h3><span>Volunteer</span></li>
      <li><h3>Industries</h3><span>Software Development</span></li>
    </ul>
    """

    job = parse_job_detail(html, card)

    assert job.industries == "Software Development"


def test_linkedin_job_detail_does_not_infer_industries_from_description(
    fixture_html: Callable[[str], str],
) -> None:
    card = parse_search_page(fixture_html("linkedin_search_page_1.html")).cards[0]
    html = """<!doctype html>
    <h1 class="top-card-layout__title">Software Engineering Intern 2027</h1>
    <a class="topcard__org-name-link">Test Technology</a>
    <div class="show-more-less-html__markup">We follow a hybrid working model.</div>
    """

    job = parse_job_detail(html, card)

    assert job.industries is None


def test_linkedin_job_detail_does_not_treat_graduation_date_as_start_date(
    fixture_html: Callable[[str], str],
) -> None:
    card = parse_search_page(fixture_html("linkedin_search_page_1.html")).cards[0]
    html = """<!doctype html>
    <h1 class="top-card-layout__title">Software Engineering Intern 2027</h1>
    <a class="topcard__org-name-link">Test Technology</a>
    <div class="show-more-less-html__markup">Applicants must graduate in June 2027.</div>
    """

    job = parse_job_detail(html, card)

    assert job.start_date is None


def test_linkedin_scraper_paginates_and_deduplicates_job_ids(
    fixture_html: Callable[[str], str],
) -> None:
    search = configured_search()
    page_one = build_search_url(search, start=0)
    page_two = build_search_url(search, start=25)
    responses = {
        page_one: fixture_html("linkedin_search_page_1.html"),
        page_two: fixture_html("linkedin_search_page_2.html"),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id="1111111111"): fixture_html(
            "linkedin_job_detail_1111111111.html"
        ),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id="2222222222"): fixture_html(
            "linkedin_job_detail_2222222222.html"
        ),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id="3333333333"): fixture_html(
            "linkedin_job_detail_3333333333.html"
        ),
    }
    fetcher = FixtureFetcher(responses)
    result = asyncio.run(LinkedInScraper().scrape(search, fetcher))
    assert result.pages_fetched == 2
    assert result.search_result_count == 2
    assert [job.source_job_id for job in result.positions] == [
        "1111111111",
        "3333333333",
    ]
    duplicate_detail_url = LINKEDIN_DETAIL_ENDPOINT.format(job_id="1111111111")
    assert fetcher.calls.count(duplicate_detail_url) == 1
    assert all("2222222222" not in call for call in fetcher.calls)
    assert result.confirmed_unavailable_ids == ()
    job_without_industries = next(
        job for job in result.positions if job.source_job_id == "3333333333"
    )
    assert job_without_industries.industries is None


def test_title_prefilter_selects_new_grad_cards() -> None:
    search = configured_search(max_pages=1, max_results=25)
    job_id = "4444444444"
    page = f"""<!doctype html><div class="base-search-card"
      data-entity-urn="urn:li:jobPosting:{job_id}">
      <h3 class="base-search-card__title">Graduate Software Engineer 2027</h3>
      <h4 class="base-search-card__subtitle">New Technology</h4>
      <span class="job-search-card__location">Berlin, Germany</span></div>"""
    detail = """<!doctype html>
      <h1 class="top-card-layout__title">Graduate Software Engineer 2027</h1>
      <a class="topcard__org-name-link">New Technology</a>
      <div class="show-more-less-html__markup">A graduate software role.</div>"""
    fetcher = FixtureFetcher(
        {
            build_search_url(search, start=0): page,
            LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_id): detail,
        }
    )

    result = asyncio.run(LinkedInScraper().scrape(search, fetcher))

    assert [job.source_job_id for job in result.positions] == [job_id]


def test_title_prefilter_continues_to_later_search_pages(
    fixture_html: Callable[[str], str],
) -> None:
    search = configured_search()
    page_one = """<!doctype html><div class="base-search-card"
      data-entity-urn="urn:li:jobPosting:2222222222">
      <h3 class="base-search-card__title">Senior Product Manager</h3>
      <h4 class="base-search-card__subtitle">Other Technology</h4>
      <span class="job-search-card__location">Paris, France</span></div>"""
    fetcher = FixtureFetcher(
        {
            build_search_url(search, start=0): page_one,
            build_search_url(search, start=25): fixture_html("linkedin_search_page_2.html"),
            LINKEDIN_DETAIL_ENDPOINT.format(job_id="1111111111"): fixture_html(
                "linkedin_job_detail_1111111111.html"
            ),
            LINKEDIN_DETAIL_ENDPOINT.format(job_id="3333333333"): fixture_html(
                "linkedin_job_detail_3333333333.html"
            ),
        }
    )
    result = asyncio.run(LinkedInScraper().scrape(search, fetcher))
    assert result.pages_fetched == 2
    assert {job.source_job_id for job in result.positions} == {
        "1111111111",
        "3333333333",
    }
    assert all("2222222222" not in call for call in fetcher.calls)


def test_linkedin_company_filter_is_applied_before_detail_fetch(
    fixture_html: Callable[[str], str],
) -> None:
    search = configured_search(
        max_pages=1,
        max_results=25,
        company_names=["Test Technology"],
    )
    responses = {
        build_search_url(search, start=0): fixture_html("linkedin_search_page_1.html"),
        LINKEDIN_DETAIL_ENDPOINT.format(job_id="1111111111"): fixture_html(
            "linkedin_job_detail_1111111111.html"
        ),
    }
    fetcher = FixtureFetcher(responses)
    result = asyncio.run(LinkedInScraper().scrape(search, fetcher))
    assert [job.company for job in result.positions] == ["Test Technology"]
    assert all("2222222222" not in call for call in fetcher.calls)


def test_known_job_404_is_reported_as_confirmed_unavailable() -> None:
    search = configured_search(max_pages=1, max_results=25, max_rechecks=1)
    job_id = "9999999999"
    fetcher = FixtureFetcher(
        {
            build_search_url(search, start=0): "<!doctype html>",
            LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_id): FetchError(
                "http_status", "not found", status_code=404
            ),
        }
    )
    known = KnownJob(
        source_job_id=job_id,
        company="Known Technology",
        title="Software Intern 2027",
        locations=("Berlin, Germany",),
        application_url=f"https://www.linkedin.com/jobs/view/{job_id}",
    )
    result = asyncio.run(LinkedInScraper().scrape(search, fetcher, known_jobs=(known,)))
    assert result.confirmed_unavailable_ids == (job_id,)


def test_linkedin_access_challenge_is_rejected() -> None:
    with pytest.raises(LinkedInPayloadError, match="verification"):
        parse_search_page("<html><body>Security verification challenge-page</body></html>")
