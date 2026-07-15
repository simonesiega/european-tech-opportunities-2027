"""Single active scraper for LinkedIn's unauthenticated public jobs HTML."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag

from internships.models.raw import KnownJob, RawJob
from internships.models.search import LinkedInSearchConfig
from internships.scrapers.http import FetchError, TextResponse
from internships.utils.text import clean_text, normalized_key

LINKEDIN_SEARCH_ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LINKEDIN_DETAIL_ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
LINKEDIN_PUBLIC_JOB_URL = "https://www.linkedin.com/jobs/view/{job_id}"
LINKEDIN_PAGE_SIZE = 25
_JOB_ID_RE = re.compile(r"jobPosting:([0-9]+)$")
_BLOCK_MARKERS = (
    "captcha-internal",
    "challenge-page",
    "security verification",
    "unusual activity",
)
_DATE_POSTED_PARAMETERS = {
    "day": "r86400",
    "week": "r604800",
    "month": "r2592000",
}
_WORKPLACE_PARAMETERS = {"on-site": "1", "remote": "2", "hybrid": "3"}
_DEFAULT_INTERNSHIP_TITLE_TERMS = (
    "intern",
    "internship",
    "internships",
    "industrial placement",
    "university placement",
    "co-op",
    "coop",
)


class LinkedInPayloadError(ValueError):
    """LinkedIn returned an unexpected or blocked HTML document."""


class TextFetcher(Protocol):
    """Define the text-fetching interface used by the LinkedIn scraper."""

    async def get_text(self, url: str) -> TextResponse:
        """Fetch one URL and return its text response."""
        ...


@dataclass(frozen=True, slots=True)
class LinkedInSearchCard:
    """Hold a parsed LinkedIn search-result card."""

    job_id: str
    title: str
    company: str
    location: str
    application_url: str


@dataclass(frozen=True, slots=True)
class SearchPageResult:
    """Hold parsed cards and page-level warnings."""

    cards: tuple[LinkedInSearchCard, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LinkedInScrapeResult:
    """Summarize one complete LinkedIn search."""

    positions: list[RawJob]
    warnings: tuple[str, ...]
    response_time_ms: int
    response_bytes: int
    pages_fetched: int
    search_result_count: int
    confirmed_unavailable_ids: tuple[str, ...] = ()


def build_search_url(search: LinkedInSearchConfig, *, start: int) -> str:
    """Build a bounded LinkedIn guest-search URL."""
    parameters: list[tuple[str, str]] = [
        ("keywords", search.keywords),
        ("location", search.location),
    ]
    if search.geo_id:
        parameters.append(("geoId", search.geo_id))
    parameters.append(("start", str(start)))
    if search.date_posted != "any":
        parameters.append(("f_TPR", _DATE_POSTED_PARAMETERS[search.date_posted]))
    if search.workplace != "any":
        parameters.append(("f_WT", _WORKPLACE_PARAMETERS[search.workplace]))
    return f"{LINKEDIN_SEARCH_ENDPOINT}?{urlencode(parameters)}"


def parse_search_page(html: str) -> SearchPageResult:
    """Parse cards from one LinkedIn search-results page."""
    _reject_blocked_document(html)
    soup = BeautifulSoup(html, "html.parser")
    cards: list[LinkedInSearchCard] = []
    warnings: list[str] = []
    nodes = soup.select("[data-entity-urn*='urn:li:jobPosting:']")
    for node in nodes:
        if not isinstance(node, Tag):
            continue
        try:
            entity_urn = str(node.get("data-entity-urn", ""))
            match = _JOB_ID_RE.search(entity_urn)
            if match is None:
                raise ValueError("missing job identifier")
            job_id = match.group(1)
            title = _required_text(node, ".base-search-card__title")
            company = _required_text(node, ".base-search-card__subtitle")
            location = _required_text(node, ".job-search-card__location")
            cards.append(
                LinkedInSearchCard(
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    application_url=LINKEDIN_PUBLIC_JOB_URL.format(job_id=job_id),
                )
            )
        except ValueError:
            warnings.append("LinkedIn search card skipped: malformed required fields")
    if nodes and len(warnings) / len(nodes) > 0.5:
        raise LinkedInPayloadError("LinkedIn search page rejected: most cards were malformed")
    return SearchPageResult(cards=tuple(cards), warnings=tuple(warnings))


def parse_job_detail(html: str, card: LinkedInSearchCard) -> RawJob:
    """Parse a LinkedIn detail page with card data as fallback."""
    _reject_blocked_document(html)
    soup = BeautifulSoup(html, "html.parser")
    title = _optional_text(soup, ".top-card-layout__title, .topcard__title") or card.title
    company = _optional_text(soup, ".topcard__org-name-link") or card.company
    location = (
        _optional_text(
            soup,
            ".top-card-layout__second-subline .topcard__flavor-row:first-of-type "
            ".topcard__flavor--bullet",
        )
        or card.location
    )
    if not title or not company:
        raise LinkedInPayloadError("LinkedIn detail page is missing title or company")
    description_node = soup.select_one(".show-more-less-html__markup")
    description = (
        clean_text(description_node.get_text(" ", strip=True))
        if isinstance(description_node, Tag)
        else None
    )
    return RawJob(
        source_job_id=card.job_id,
        company=company,
        title=title,
        locations=[location] if location else [],
        application_url=card.application_url,
        description=description,
    )


class LinkedInScraper:
    """Collect paginated cards and details through one provider-specific path."""

    def __init__(
        self, internship_title_terms: tuple[str, ...] = _DEFAULT_INTERNSHIP_TITLE_TERMS
    ) -> None:
        """Initialize the instance dependencies and state."""
        self._internship_title_patterns = tuple(
            re.compile(rf"(?:^|\s){re.escape(normalized_key(term))}(?:$|\s)")
            for term in internship_title_terms
        )
        # Searches overlap heavily, so share each in-flight detail request by job ID.
        self._detail_tasks: dict[str, asyncio.Task[TextResponse]] = {}
        self._detail_lock = asyncio.Lock()

    async def scrape(
        self,
        search: LinkedInSearchConfig,
        fetcher: TextFetcher,
        *,
        known_jobs: tuple[KnownJob, ...] = (),
    ) -> LinkedInScrapeResult:
        """Collect internships and optionally refresh generated documentation."""
        cards: dict[str, LinkedInSearchCard] = {}
        seen_search_ids: set[str] = set()
        allowed_companies = frozenset(normalized_key(name) for name in search.company_names)
        warnings: list[str] = []
        response_time_ms = 0
        response_bytes = 0
        pages_fetched = 0

        for page in range(search.max_pages):
            response = await fetcher.get_text(
                build_search_url(search, start=page * LINKEDIN_PAGE_SIZE)
            )
            response_time_ms += response.elapsed_ms
            response_bytes += response.content_bytes
            pages_fetched += 1
            parsed = parse_search_page(response.text)
            warnings.extend(parsed.warnings)
            new_search_ids = {
                card.job_id for card in parsed.cards if card.job_id not in seen_search_ids
            }
            # LinkedIn can repeat a full page at later offsets. Stop only on an empty
            # or fully repeated raw page; a page with no eligible titles may still be
            # followed by a useful page.
            if not parsed.cards or not new_search_ids:
                break
            seen_search_ids.update(card.job_id for card in parsed.cards)
            page_cards = [
                card
                for card in parsed.cards
                if _company_allowed(card.company, allowed_companies)
                and _title_allowed(card.title, self._internship_title_patterns)
            ]
            for card in page_cards:
                cards.setdefault(card.job_id, card)
            if len(cards) >= search.max_results:
                break

        selected_cards = list(cards.values())[: search.max_results]
        positions: list[RawJob] = []
        malformed_details = 0
        for card in selected_cards:
            try:
                response = await self._detail(card.job_id, fetcher)
                response_time_ms += response.elapsed_ms
                response_bytes += response.content_bytes
                positions.append(parse_job_detail(response.text, card))
            except FetchError as exc:
                if exc.status_code not in {404, 410}:
                    raise
                # Search-card disappearance does not close jobs; only explicit detail
                # responses count as unavailability evidence.
                warnings.append("LinkedIn job detail skipped: listing no longer available")
            except LinkedInPayloadError:
                malformed_details += 1
                warnings.append("LinkedIn job detail skipped: malformed HTML")
        if selected_cards and malformed_details / len(selected_cards) > 0.5:
            raise LinkedInPayloadError(
                "LinkedIn search rejected: most job detail pages were malformed"
            )

        confirmed_unavailable: list[str] = []
        # Bound rechecks deterministically by job ID so repeated runs inspect the same
        # subset until those jobs are observed again or explicitly become unavailable.
        absent_known = sorted(
            (job for job in known_jobs if job.source_job_id not in cards),
            key=lambda job: job.source_job_id,
        )[: search.max_rechecks]
        for known in absent_known:
            fallback = LinkedInSearchCard(
                job_id=known.source_job_id,
                title=known.title,
                company=known.company,
                location=known.locations[0] if known.locations else "",
                application_url=known.application_url,
            )
            try:
                response = await self._detail(known.source_job_id, fetcher)
                response_time_ms += response.elapsed_ms
                response_bytes += response.content_bytes
                positions.append(parse_job_detail(response.text, fallback))
            except FetchError as exc:
                if exc.status_code not in {404, 410}:
                    raise
                confirmed_unavailable.append(known.source_job_id)
            except LinkedInPayloadError:
                # Ambiguous HTML must not advance closure confirmations.
                warnings.append("Known LinkedIn job recheck skipped: malformed HTML")

        return LinkedInScrapeResult(
            positions=positions,
            warnings=tuple(warnings),
            response_time_ms=response_time_ms,
            response_bytes=response_bytes,
            pages_fetched=pages_fetched,
            search_result_count=len(cards),
            confirmed_unavailable_ids=tuple(confirmed_unavailable),
        )

    async def _detail(self, job_id: str, fetcher: TextFetcher) -> TextResponse:
        """Fetch and parse one LinkedIn job detail page."""
        # Protect task creation rather than the network wait: concurrent searches share
        # one request for the same job without serializing requests for different jobs.
        async with self._detail_lock:
            task = self._detail_tasks.get(job_id)
            if task is None:
                task = asyncio.create_task(
                    fetcher.get_text(LINKEDIN_DETAIL_ENDPOINT.format(job_id=job_id))
                )
                self._detail_tasks[job_id] = task
        return await task


def _required_text(node: Tag, selector: str) -> str:
    """Extract required text from a parsed element."""
    value = _optional_text(node, selector)
    if not value:
        raise ValueError(f"missing selector: {selector}")
    return value


def _optional_text(node: BeautifulSoup | Tag, selector: str) -> str:
    """Extract optional text from a parsed element."""
    selected = node.select_one(selector)
    return clean_text(selected.get_text(" ", strip=True)) if isinstance(selected, Tag) else ""


def _title_allowed(title: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    """Check whether a search card title has internship terminology."""
    key = normalized_key(title)
    return any(pattern.search(key) for pattern in patterns)


def _company_allowed(company: str, allowed_companies: frozenset[str]) -> bool:
    """Check whether a card company matches the normalized allowlist."""
    return not allowed_companies or normalized_key(company) in allowed_companies


def _reject_blocked_document(html: str) -> None:
    """Reject authentication, challenge, and block pages."""
    normalized = html.casefold()
    if any(marker in normalized for marker in _BLOCK_MARKERS):
        raise LinkedInPayloadError("LinkedIn returned an access or verification page")
