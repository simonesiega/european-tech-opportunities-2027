"""Single active scraper for LinkedIn's unauthenticated public jobs HTML."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import urlencode

from bs4 import BeautifulSoup, Tag

from opportunities.models.raw import KnownJob, RawJob
from opportunities.models.search import LinkedInSearchConfig
from opportunities.scrapers.http import FetchError
from opportunities.utils.text import clean_text, normalized_key
from opportunities.utils.time import ensure_utc, utc_now

LINKEDIN_SEARCH_ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
LINKEDIN_DETAIL_ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
LINKEDIN_PUBLIC_JOB_URL = "https://www.linkedin.com/jobs/view/{job_id}"
LINKEDIN_PAGE_SIZE = 25
MINIMUM_POSTED_AT = datetime(2026, 5, 1, tzinfo=UTC)
_JOB_ID_RE = re.compile(r"jobPosting:([0-9]+)$")
_RELATIVE_POSTED_RE = re.compile(
    r"^(?:reposted\s+)?(?P<count>\d+)\+?\s+"
    r"(?P<unit>minute|hour|day|week|month|year)s?\s+ago$",
    re.IGNORECASE,
)
_RELATIVE_POSTED_UNITS = {
    "minute": timedelta(minutes=1),
    "hour": timedelta(hours=1),
    "day": timedelta(days=1),
    "week": timedelta(weeks=1),
    "month": timedelta(days=31),
    "year": timedelta(days=365),
}
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
_START_DATE_VALUE = (
    r"(?:spring|summer|autumn|fall|winter|january|february|march|april|may|june|"
    r"july|august|september|october|november|december)\s+20\d{2}"
)
_START_DATE_RE = re.compile(rf"\b{_START_DATE_VALUE}\b", re.IGNORECASE)
_CONTEXTUAL_START_DATE_RE = re.compile(
    rf"(?:\b(?:start(?:ing|s)?|begin(?:ning|s)?|commenc(?:e|es|ing)|join(?:\s+our|\s+the)?)\b"
    rf"[^.\n]{{0,24}}(?P<after>{_START_DATE_VALUE})\b|"
    rf"\b(?P<before>{_START_DATE_VALUE})\s+(?:start|intake|internship|programme|program)\b)",
    re.IGNORECASE,
)
_DEFAULT_INTERNSHIP_TITLE_TERMS = (
    "intern",
    "internship",
    "internships",
    "industrial placement",
    "university placement",
    "co-op",
    "coop",
)
_DEFAULT_NEW_GRAD_TITLE_TERMS = (
    "new grad",
    "new graduate",
    "graduate",
    "university graduate",
    "recent graduate",
    "early career",
    "entry level",
    "entry-level",
)


class LinkedInPayloadError(ValueError):
    """LinkedIn returned an unexpected or blocked HTML document."""


class TextFetcher(Protocol):
    """Define the text-fetching interface used by the LinkedIn scraper."""

    async def get_text(self, url: str) -> str:
        """Fetch one URL and return validated text."""
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


def parse_job_detail(
    html: str,
    card: LinkedInSearchCard,
    *,
    observed_at: datetime | None = None,
) -> RawJob:
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
        industries=_extract_criterion(soup, "industries"),
        start_date=_extract_start_date(title, description),
        posted_at=_extract_posted_at(soup, observed_at or utc_now()),
    )


def _extract_posted_at(soup: BeautifulSoup, observed_at: datetime) -> datetime | None:
    """Infer the publication timestamp from LinkedIn's relative posting age."""
    value = _optional_text(soup, ".posted-time-ago__text")
    if not value:
        return None
    normalized = normalized_key(value)
    if normalized in {"just now", "today"}:
        return ensure_utc(observed_at)
    match = _RELATIVE_POSTED_RE.fullmatch(normalized)
    if match is None:
        return None
    duration = _RELATIVE_POSTED_UNITS[match.group("unit").casefold()]
    return ensure_utc(observed_at) - int(match.group("count")) * duration


def _extract_criterion(soup: BeautifulSoup, expected_heading: str) -> str | None:
    """Extract one exact value from LinkedIn's structured job criteria."""
    for heading in soup.select(".description__job-criteria-subheader, dt, h3"):
        if not isinstance(heading, Tag):
            continue
        if normalized_key(heading.get_text(" ", strip=True)) != expected_heading:
            continue

        item = heading.parent
        if isinstance(item, Tag):
            value = _optional_text(
                item, ".description__job-criteria-text, dd, [class*='criteria-text']"
            )
            if value:
                return value

        sibling = heading.find_next_sibling()
        if isinstance(sibling, Tag):
            value = clean_text(sibling.get_text(" ", strip=True))
            if value:
                return value
    return None


def _extract_start_date(title: str, description: str | None) -> str | None:
    """Extract explicit start metadata without treating unrelated dates as starts."""
    title_match = _START_DATE_RE.search(title)
    description_match = _CONTEXTUAL_START_DATE_RE.search(description or "")
    value = title_match.group(0) if title_match else None
    if value is None and description_match is not None:
        value = description_match.group("after") or description_match.group("before")
    if value is None:
        return None
    words = value.split()
    return f"{words[0].title()} {words[1]}"


class LinkedInScraper:
    """Collect paginated cards and details through one provider-specific path."""

    def __init__(
        self,
        internship_title_terms: tuple[str, ...] = _DEFAULT_INTERNSHIP_TITLE_TERMS,
        new_grad_title_terms: tuple[str, ...] = _DEFAULT_NEW_GRAD_TITLE_TERMS,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        """Initialize the instance dependencies and state."""
        self._opportunity_title_patterns = tuple(
            re.compile(rf"(?:^|\s){re.escape(normalized_key(term))}(?:$|\s)")
            for term in (*internship_title_terms, *new_grad_title_terms)
        )
        self._clock = clock
        # Searches overlap heavily, so share each in-flight detail request by job ID.
        self._detail_tasks: dict[str, asyncio.Task[str]] = {}
        self._detail_lock = asyncio.Lock()

    async def scrape(
        self,
        search: LinkedInSearchConfig,
        fetcher: TextFetcher,
        *,
        known_jobs: tuple[KnownJob, ...] = (),
    ) -> LinkedInScrapeResult:
        """Collect internship and new-grad candidates from one bounded search."""
        cards: dict[str, LinkedInSearchCard] = {}
        seen_search_ids: set[str] = set()
        known_job_ids = frozenset(job.source_job_id for job in known_jobs)
        observed_at = ensure_utc(self._clock())
        allowed_companies = frozenset(normalized_key(name) for name in search.company_names)
        warnings: list[str] = []
        pages_fetched = 0

        for page in range(search.max_pages):
            html = await fetcher.get_text(build_search_url(search, start=page * LINKEDIN_PAGE_SIZE))
            pages_fetched += 1
            parsed = parse_search_page(html)
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
                and _title_allowed(card.title, self._opportunity_title_patterns)
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
                html = await self._detail(card.job_id, fetcher)
                job = parse_job_detail(html, card, observed_at=observed_at)
                if card.job_id in known_job_ids or _posting_is_eligible(job.posted_at):
                    positions.append(job)
                else:
                    warnings.append(
                        "LinkedIn job detail skipped: posting date is missing or before "
                        "2026-05-01"
                    )
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
                html = await self._detail(known.source_job_id, fetcher)
                positions.append(parse_job_detail(html, fallback, observed_at=observed_at))
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
            pages_fetched=pages_fetched,
            search_result_count=len(cards),
            confirmed_unavailable_ids=tuple(confirmed_unavailable),
        )

    async def _detail(self, job_id: str, fetcher: TextFetcher) -> str:
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


def _posting_is_eligible(posted_at: datetime | None) -> bool:
    """Allow only listings with posting evidence on or after the fixed cutoff."""
    return posted_at is not None and ensure_utc(posted_at) >= MINIMUM_POSTED_AT


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
    """Check whether a search-card title has a supported opportunity term."""
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
