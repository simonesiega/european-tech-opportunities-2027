# European Tech Opportunities 2027 Architecture

[← Documentation hub](../../README.md) · [Development guide](development.md) · [Database lifecycle](../operations/database.md) · [Security policy](../../../SECURITY.md)

This is the canonical architecture guide for the project. It defines the system’s data flow, component boundaries, invariants, failure isolation, canonical state model, and extension policy.

## Contents

- [Architecture at a glance](#architecture-at-a-glance)
- [System flow](#system-flow)
- [Architectural principles](#architectural-principles)
- [Component map](#component-map)
- [Discovery is not acceptance](#discovery-is-not-acceptance)
- [Collection and classification](#collection-and-classification)
- [Failure isolation](#failure-isolation)
- [Persistence and lifecycle](#persistence-and-lifecycle)
- [Public projections](#public-projections)
- [Dependency direction](#dependency-direction)
- [Operational boundaries](#operational-boundaries)
- [Extension policy](#extension-policy)

## Architecture at a glance

The architecture is intentionally narrow:

- one LinkedIn guest-HTML source adapter;
- one deterministic classification pipeline;
- one SQLite lifecycle store;
- one controlled application writer;
- three read-only public projections.

The website is the complete public directory. The README contains only a bounded preview, while sanitized CSV and JSON files expose all open rows through a fixed public-field allowlist.

## System flow

<div align="center">
<pre>
search YAML + classification rules
↓
bounded LinkedIn guest search HTML
↓
internship/new-grad title prefilter
↓
LinkedIn guest detail HTML
↓
normalization + deterministic classification
↓
transactional SQLite lifecycle state
↓
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ searchable website   │ README preview       │ public CSV + JSON    │
│ all open listings    │ 5 latest rows/type   │ approved fields only │
└──────────────────────┴──────────────────────┴──────────────────────┘
</pre>
</div>

## Architectural principles

| Principle | Contract |
|---|---|
| Canonical identity | The numeric LinkedIn job ID uniquely identifies a listing |
| Canonical state | SQLite is the only source of lifecycle truth |
| Strict acceptance | Listings require explicit target-cycle evidence or an eligible posting date as the yearless fallback; ambiguous employment type, cycle, role, seniority, or geography results in exclusion |
| Safe closure | Search-page disappearance never closes a job |
| One writer | Only the repository layer mutates canonical application state |
| Isolated outcomes | One failed search cannot mutate another search’s lifecycle state |
| Bounded access | Requests, responses, retries, concurrency, pages, and result counts remain limited |
| Deterministic behavior | Classification, persistence, rendering, and validation are reproducible |
| Read-only projections | The website, README, and public exports never classify jobs or mutate lifecycle state |
| No privileged source access | The project does not use credentials, sessions, browsers, private endpoints, or anti-bot bypasses |

These are design contracts, not implementation suggestions. Changes that violate them require an explicit architecture and security decision.

## Component map

| Area | Path | Responsibility |
|---|---|---|
| CLI | `src/opportunities/cli/app.py` | Preconditions, orchestration, output, and exit codes |
| Settings | `src/opportunities/config/settings.py` | Layered and validated runtime configuration |
| Search registry | `src/opportunities/config/search_registry.py` | Recursive YAML loading, duplicate rejection, and search selection |
| Classification rules | `src/opportunities/config/rules.py` and `configs/categories.yml` | Employment type, seniority, category, cycle, and geography signals |
| HTTP transport | `src/opportunities/scrapers/http.py` | Authorization gate, pacing, timeouts, retries, bounds, and sanitized errors |
| LinkedIn adapter | `src/opportunities/scrapers/linkedin.py` | Guest URLs, cards, details, structured criteria, and explicit unavailability |
| Pipeline runner | `src/opportunities/pipeline/runner.py` | Bounded fetching, isolated outcomes, classification, and serialized persistence |
| Classifier | `src/opportunities/pipeline/classification.py` | Deterministic acceptance and exclusion decisions |
| Normalization | `src/opportunities/normalization/` | Stable title, text, and location signals |
| Repository | `src/opportunities/database/repository.py` | Transactions, provenance, lifecycle transitions, and statistics |
| ORM and migrations | `src/opportunities/database/` and `migrations/` | Current schema intent and upgrade history |
| README renderer | `src/opportunities/readme.py` | Deterministic bounded projection and atomic replacement |
| Public export renderer | `src/opportunities/public_exports.py` | Whitelisted CSV/JSON serialization, spreadsheet safety, validation, and atomic replacement |
| Website | `site/src/` | Read-only server queries, export delivery, and client-side directory interaction |
| Tests | `tests/` | Offline unit, integration, migration, rendering, lifecycle coverage, and performance benchmarks |

## Discovery is not acceptance

Search results are discovery candidates, not trusted records. They may be stale, unrelated, incorrectly ranked, duplicated across queries, or outside the project scope.

```text
Discovery       → RawJob candidates
Classification  → accepted DiscoveredJob values
Persistence     → canonical jobs and lifecycle evidence
Projection      → website, README, and public CSV/JSON exports
```

The search that found a listing establishes provenance. It does not prove that the listing is a valid 2027 European technology internship or New Grad opportunity.

Search configuration controls where the pipeline looks; classification controls what may be published.

## Collection and classification

For each enabled search, the pipeline:

1. builds a bounded guest-search request;
2. fetches through the shared authorization-gated transport;
3. rejects access challenges and structurally invalid result pages;
4. applies low-cost company and title prefilters;
5. fetches selected detail pages with cross-search deduplication;
6. normalizes source fields and structured criteria;
7. applies deterministic acceptance rules;
8. records explicit detail-page unavailability separately from search absence;
9. returns one isolated outcome for persistence.

Overlapping searches may discover the same job. The numeric LinkedIn ID deduplicates the listing, while provenance remains associated with every search that found it.

Classification checks require evidence for:

- exactly one normalized employment type: `internship` or `new-grad` (internship wins if both title signals appear);
- absence of configured seniority exclusions;
- a supported technology category;
- cycle evidence: the explicit target cycle, or no conflicting cycle year with resolved posting-date evidence on or after May 1, 2026 as the yearless fallback;
- an explicit European location; `EMEA` alone also covers non-European regions and is insufficient.

Graduation-year eligibility language is not internship-cycle evidence. For title-explicit New Grad roles, a title or contextual opportunity year identifies the hiring cycle, so explicit 2025 or 2026 roles are rejected. A listing with target-cycle evidence does not require posting-age metadata; a listing with no explicit opportunity-cycle evidence does. Known jobs may be rechecked without treating missing current posting-age metadata as closure evidence. Malformed or ambiguous candidates are excluded without failing unrelated candidates.

Search schema and pagination rules are documented in the [search registry guide](../user-guide/search-registry.md).

## Failure isolation

Searches fetch concurrently under bounded limits, but persistence is serialized.

Each selected search produces an independent outcome containing:

- run identity;
- UTC timing;
- result counts and warnings; or
- a bounded sanitized error.

| Overall status | Condition | Exit code |
|---|---|---:|
| Success | At least one search succeeds and none fail | `0` |
| Partial | At least one search succeeds and at least one fails | `2` |
| Failed | No selected search succeeds | `1` |

A successful search may commit even when another search fails.

A failed search:

- records diagnostics;
- does not upsert jobs;
- does not apply absence evidence;
- does not increment unavailability confirmations;
- does not close jobs.

This prevents temporary network, parser, or configuration failures from corrupting lifecycle state.

## Persistence and lifecycle

`Repository` is the sole application writer.

A successful search transaction atomically:

1. records the search run;
2. upserts accepted jobs;
3. refreshes search provenance;
4. applies explicit detail-page unavailability evidence;
5. updates monotonic observation timestamps;
6. closes a job only when no active supporting association remains.

Search-page absence is never closure evidence.

A later valid rediscovery can reactivate provenance and reopen a job. Separately, a daily full-state auditor checks every stored job through its public listing and, after a successful page without a closure alert, the guest detail endpoint. Successful validation preserves or reopens the record; an explicit `404` or `410` from either request or a scoped “No longer accepting applications” alert deletes it; ambiguous failures leave its state unchanged.

Concurrent searches may finish out of order. The pipeline persists their outcomes in finish-time order, and the repository ignores stale observations rather than letting them overwrite newer metadata, closure, or provenance. Both accepted details and explicit unavailability evidence use the search start as a conservative observation lower bound; a late finish alone cannot overrule later evidence from an overlapping search. Lifecycle timestamps remain monotonic.

Schema, transactions, provenance, closure, migrations, backup, and restore are owned by the [database lifecycle guide](../operations/database.md).

## Public projections

SQLite state feeds exactly three read-only public projections.

### Website

The Next.js website:

- opens short-lived read-only SQLite connections;
- returns every currently open listing;
- reads the latest successful collection time;
- performs search, filtering, sorting, and pagination as presentation behavior;
- never runs collection, classification, migrations, or lifecycle writes.

The website contract is documented in the [website guide](../user-guide/website.md).

### README preview

The renderer creates a deterministic bounded projection containing:

- total open-job count;
- latest successful collection time;
- the public website link;
- at most five recently discovered internships and five recently discovered New Grad opportunities.

A generated review seal covers every website-visible open row and the exact last successful collection time, including jobs outside the preview. This lets the [automation review gate](../operations/automation.md#first-public-state-review-seal) detect public-directory changes before deployment without expanding the README tables.

The renderer owns the marked opportunity-count and opportunity-preview regions and replaces the resulting README atomically. Validation reconstructs both expected regions from SQLite and requires exact equality.

The README cannot reconstruct lifecycle state because it omits most jobs, closed state, provenance, run history, and closure evidence.

### Public CSV and JSON exports

The pipeline atomically generates `open-opportunities.csv` and `open-opportunities.json` from all currently open SQLite rows. The export schema is an explicit allowlist:

- LinkedIn job ID;
- company, title, and location;
- canonical public listing URL;
- technology category and industries;
- employment type and start date.

The exports deliberately omit status, posting and observation timestamps, provenance, search runs, closure evidence, diagnostics, and every other lifecycle or operational field. CSV text that could be interpreted as a spreadsheet formula is neutralized. The website serves the generated files as attachments through fixed read-only routes; it does not generate or mutate export data.

Exports are disposable projections. They can be regenerated from SQLite and must never be used to restore lifecycle history.

## Dependency direction

```text
CLI
 ├── configuration
 ├── pipeline
 │    ├── transport + LinkedIn adapter
 │    ├── normalization + classification
 │    └── repository
 ├── README renderer
 └── public export renderer

repository → ORM → database session
migrations → ORM metadata
website → read-only SQLite + generated public exports
```

Dependency boundaries are intentional:

- source parsing does not write SQL;
- the repository does not parse HTML;
- classification does not render documentation;
- the website does not classify or mutate lifecycle state;
- the README and public export renderers do not discover jobs;
- public exports contain only explicitly approved fields;
- migrations describe schema evolution rather than application orchestration.

Business rules should remain independent from CLI presentation, network transport, and public projections.

The maintainer-only `add-job` and `add-jobs` commands are a second input path into the same validated persistence boundary. They construct `DiscoveredJob` values, reuse the deterministic classifier (without fetching source content), reject closed-row manual reopen, and use the repository's shared job-row upsert. `add-jobs` validates a bounded batch and writes it in one transaction before the normal projection renderer runs. Operator-supplied source facts must be independently reviewed by a maintainer; offline classification cannot authenticate them. These commands perform no source access and deliberately create no search configuration, run record, or provenance association. Ordinary collection can later attach genuine provenance to the same canonical LinkedIn ID, and the full-state availability auditor treats manual rows like every other stored job.

## Operational boundaries

The supported architecture requires:

- express authorization before LinkedIn network access;
- fixed HTTPS guest endpoints;
- disabled redirects;
- bounded timeouts, concurrency, retries, response sizes, pages, and results;
- same-host request pacing;
- sanitized diagnostics without response-body logging;
- one canonical SQLite writer;
- read-only website database access;
- versioned, checksum-verified SQLite snapshots with automated restore tests;
- main-only GitHub environments for canonical-state and deployment credentials;
- exact-scope validation of automation-generated README commits;
- atomic README and public-export replacement;
- offline deterministic tests by default.

An upstream block or challenge is a stop condition, not a problem to bypass.

Exact authorization variables and network settings are documented in [Configuration](../getting-started/configuration.md). Disclosure and trust boundaries are defined in [`SECURITY.md`](../../../SECURITY.md).

## Extension policy

Extensions that preserve the existing boundaries can normally be implemented without changing the architecture. Examples include:

- focused search configuration;
- stricter, tested classification signals;
- sanitized parser fixtures for guest-HTML variations;
- additional read-only views;
- improved lifecycle observability;
- safer migrations and recovery checks;
- website accessibility, performance, and usability improvements.

The following change trust, ownership, or state boundaries and therefore require an explicit architecture and security decision before implementation:

- additional job providers;
- login, session, or browser-based collection;
- private endpoints;
- multiple concurrent writers;
- APIs or forms that mutate canonical state;
- user-provided content;
- new authentication or authorization surfaces;
- new canonical output formats.

Discuss boundary-changing proposals before implementation. Follow [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) for review expectations and [`SECURITY.md`](../../../SECURITY.md) for security-sensitive changes.
