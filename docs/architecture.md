# Architecture

[← README](../README.md)

This document describes the implemented `0.1.x` architecture for collecting strict 2027 European technology internships.

## Goals and boundaries

The supported production flow is:

```text
configs/searches/**/*.yml           configs/categories.yml
             │                               │
             └──────────────┬────────────────┘
                            ↓
                  LinkedIn guest search HTML
                            ↓
                 search-card title prefilter
                            ↓
                  LinkedIn guest detail HTML
                            ↓
             normalization and strict classification
                            ↓
                     transactional SQLite
                            ↓
                    open-job projection
                            ↓
                 atomic README table replacement
```

The architecture intentionally has:

- one external source: LinkedIn guest search and detail HTML;
- one canonical identity: the numeric LinkedIn job ID;
- one canonical state store: SQLite;
- one public output: the README's four-column table;
- one controlled collection writer;
- no credentials, cookies, account sessions, browser automation, private endpoints, or anti-bot bypasses.

## Component map

| Area | Main path | Responsibility |
|---|---|---|
| CLI | `src/internships/cli/app.py` | Loads validated settings, enforces command preconditions, invokes services, renders operator output, and maps outcomes to exit codes. |
| Settings | `src/internships/config/settings.py` | Combines defaults, `.env`, optional YAML, and process environment; validates limits and paths. |
| Search registry | `src/internships/config/search_registry.py` | Recursively loads search YAML, validates each query, rejects duplicate slugs and identities, and selects enabled searches. |
| Classification rules | `src/internships/config/rules.py` | Loads internship terminology, seniority exclusions, and technology-category keywords. |
| HTTP transport | `src/internships/scrapers/http.py` | Applies the authorization gate, pacing, timeouts, retries, response bounds, content checks, and sanitized transport errors. |
| LinkedIn collector | `src/internships/scrapers/linkedin.py` | Builds guest URLs, parses search cards and detail HTML, filters cards, deduplicates IDs, and confirms explicit unavailability. |
| Pipeline | `src/internships/pipeline/runner.py` | Runs independent searches concurrently, normalizes and classifies positions, isolates failures, and persists completed outcomes. |
| Classification | `src/internships/pipeline/classification.py` | Enforces title-explicit internship, target-cycle, technology-role, and European-location rules. |
| Normalization | `src/internships/normalization/` | Produces stable titles, normalized text, and explicit European geography signals. |
| ORM schema | `src/internships/database/models.py` | Declares current SQLAlchemy tables, columns, indexes, and relationships. |
| Repository | `src/internships/database/repository.py` | Owns transactional search synchronization, run history, job upserts, provenance, lifecycle, health, and statistics. |
| Migrations | `migrations/` | Defines reproducible schema creation and evolution through Alembic. |
| README renderer | `src/internships/readme.py` | Escapes fields, builds the exact table projection, and atomically replaces one marked block. |
| Tests | `tests/` | Exercises configuration, parsing, transport, classification, persistence, CLI behavior, rendering, and migrations offline. |

## Discovery and classification are separate

Search definitions are discovery hints, not acceptance policy.

A query such as `computer vision intern 2027` can return unrelated, stale, non-European, or incorrectly ranked listings. The collector therefore treats every search result as an untrusted candidate. It does not infer acceptance from the query that found it or from LinkedIn employment metadata.

The boundary is:

```text
Discovery
  produces RawJob candidates and explicit 404/410 confirmations

Classification
  converts only fully validated candidates into DiscoveredJob records

Persistence
  stores accepted jobs and safe lifecycle evidence
```

This separation permits broad enough discovery while preserving strict publication. It also makes parser fixtures and classifier tests independent.

## Collection sequence

For each enabled `LinkedInSearchConfig`, `LinkedInScraper.scrape()` performs these steps:

1. Build a LinkedIn guest search URL from keywords, location, optional Europe geo ID, workplace filter, date filter, and 25-result offset.
2. Fetch one page through the shared bounded `HttpFetcher`.
3. Reject challenge/access documents and parse cards containing a numeric `urn:li:jobPosting:<id>`.
4. Track every raw search ID so pagination can detect repeated pages.
5. Apply exact employer allowlists where configured.
6. Apply an internship-title prefilter before requesting details.
7. Continue through sparse pages until one of these conditions occurs:
   - no cards were returned;
   - the page contains no new raw search IDs;
   - the configured eligible-result limit was reached;
   - the configured page limit was reached.
8. Fetch detail HTML for selected cards and parse canonical title, company, location, and description.
9. Treat detail HTTP `404` or `410` as explicit unavailability; other transport failures fail the search.
10. Recheck a bounded number of previously known jobs that were absent from eligible current cards.
11. Return raw positions, warnings, request metrics, pages fetched, result count, and confirmed unavailable IDs.

Search-level card dictionaries deduplicate repeated IDs while preserving separate jobs with separate LinkedIn IDs. A shared detail-task cache prevents concurrent searches in one pipeline run from fetching the same detail ID repeatedly.

## HTTP transport

`HttpFetcher` is deliberately conservative:

- LinkedIn hosts are blocked unless `linkedin_crawl_authorized` is true;
- redirects are disabled;
- overall and connection timeouts are explicit;
- connections and concurrency are bounded;
- request starts to each host are spaced through a pacing lock;
- timeouts, transport errors, HTTP `429`, and HTTP `5xx` are retried finitely;
- retries use exponential backoff and bounded `Retry-After` handling;
- declared and actual response sizes are checked;
- only HTML or text responses are accepted;
- decoding and transport failures become stable, sanitized `FetchError` values;
- response bodies are not logged or stored as diagnostics.

The collector itself constructs fixed HTTPS LinkedIn guest endpoints. An access challenge is a reason to stop, not a condition to bypass.

See [Configuration](configuration.md) for every transport control and [Security](../SECURITY.md) for the trust model.

## Normalization and classification pipeline

Each raw position passes through these stages:

```text
raw title ───────────────> title normalization
raw location(s) ─────────> location normalization + Europe signals
raw description ─────────> HTML-to-text normalization
                                  ↓
                         deterministic classifier
                                  ↓
                     accepted DiscoveredJob or exclusion
```

The classifier applies checks in this order:

1. The normalized title must contain configured internship terminology.
2. The title must not contain configured seniority exclusions.
3. A technology category must be identifiable from the title or narrowly allowed description fallback.
4. The target cycle must be explicit in the title or contextual internship language in the description.
5. Graduation-year eligibility language is ignored as cycle evidence.
6. Location must explicitly resolve to Europe or a supported European country.
7. A clear non-European signal is rejected unless an explicit European country is also present.

An invalid candidate is counted as excluded and never reaches job persistence. A malformed candidate cannot fail or roll back a different completed search.

## Pipeline orchestration and failure isolation

`CollectionPipeline` synchronizes configured searches first, then runs selected searches with an `asyncio.Semaphore` bounded by `max_concurrency`.

Every search receives:

- a UUID run ID;
- independent start/finish timestamps;
- duration metrics;
- an isolated result or sanitized error;
- access to that search's active known jobs for lifecycle rechecks.

Search fetches run concurrently, but persistence is deliberately serialized after all outcomes return. Each successful or failed search is committed independently.

Overall status is:

| Status | Condition | CLI exit code |
|---|---|---:|
| Success | At least one search succeeded and none failed. | `0` |
| Partial | At least one search succeeded and at least one failed. | `2` |
| Failed | No search succeeded. | `1` |

A partial run preserves successful transactions. Failed searches record diagnostics but do not mutate their job associations.

## Repository and transaction strategy

`Repository` is the only supported application write boundary.

The repository uses one short `Session.begin()` transaction for each operation:

- synchronize all search definitions;
- persist one successful search and its lifecycle effects;
- persist one failed search diagnostic.

A successful-search transaction contains:

1. the `search_runs` success row;
2. accepted job inserts or updates;
3. `job_searches` provenance inserts or refreshes;
4. unavailable-confirmation increments;
5. association deactivation when the threshold is reached;
6. job closure only when no active association remains.

If any step fails, that search transaction rolls back. Another search's committed state remains intact.

Job and association timestamps use the maximum of existing and incoming observation times. This prevents an earlier-finishing concurrent search from moving `last_seen_at` backwards.

SQLite is operated with foreign keys enabled. The supported workflow assumes one collection writer; concurrent readers are safe, but multiple collection writers are outside the design contract.

See [Database lifecycle](database.md) for schema and transition details.

## README projection

The README is a projection, never a second database.

`Repository.list_open_jobs()` sorts open rows by case-insensitive company, title, and location. `Repository.stats()` supplies generated metadata for the same projection: open internship count and latest successful collection timestamp.

The generated block contains metadata followed by a table whose columns are exactly:

```text
Company | Title | Location | Link
```

The renderer:

1. requires exactly one opening and closing marker in `README.md`;
2. writes open-count and last-successful-collection metadata from SQLite;
3. escapes HTML and Markdown-sensitive display characters in table rows;
4. replaces only the content between markers;
5. writes a temporary file in the same directory;
6. atomically replaces the original file.

`validate` regenerates the expected metadata and table in memory and requires exact equality with the marked block. It also verifies that every stored job has `last_seen_at >= first_seen_at`.

## Dependency direction

The intended dependency direction is:

```text
CLI
 ├── configuration
 ├── pipeline
 │    ├── collector + transport
 │    ├── normalization + classification
 │    └── repository
 └── README renderer

repository ──> ORM models ──> database base/session
migrations ──> ORM metadata
```

Collector code does not write SQLite. Repository code does not parse HTML. Rendering does not classify or mutate jobs. These boundaries should remain explicit when adding features.

## Extension boundaries

Suitable extensions preserve the focused architecture, for example:

- additional validated search YAML;
- stricter or better-tested classification signals;
- parser support for changed guest HTML;
- additional read-only operational statistics;
- a notification consumer that reads committed jobs and writes dedicated idempotency state.

Changes that require a new source, login, browser automation, private endpoint, alternative public export, or multiple writers require an explicit architecture decision rather than an incidental pull request.
