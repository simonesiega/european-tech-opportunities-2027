# European Tech Opportunities 2027 Architecture

[← Documentation](../README.md) · [Database lifecycle](../operations/database.md) · [Development guide](development.md)

This guide explains the system’s data flow, component boundaries, invariants, failure isolation, canonical state model, and extension policy.

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

The project has:

- one LinkedIn guest-HTML source adapter;
- one deterministic classification pipeline;
- one canonical SQLite state store;
- one controlled application writer;
- two read-only public projections.

The website is the complete public directory. The README contains only a bounded preview.

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
┌─────────┴─────────┐
│                   │
searchable website     README preview
all open roles         10 recent roles/type
</pre>
</div>

## Architectural principles

| Principle | Contract |
|---|---|
| Canonical identity | The numeric LinkedIn job ID uniquely identifies a listing |
| Canonical state | SQLite is the only source of lifecycle truth |
| Strict acceptance | Ambiguous cycle, role, seniority, or geography results in exclusion |
| Safe closure | Search-page disappearance never closes a job |
| One writer | Only the repository layer mutates canonical application state |
| Isolated outcomes | One failed search cannot mutate another search’s lifecycle state |
| Bounded access | Requests, responses, retries, concurrency, pages, and result counts remain limited |
| Deterministic behavior | Classification, persistence, rendering, and validation are reproducible |
| Read-only projections | The website and README never classify jobs or mutate lifecycle state |
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
| Website | `site/src/` | Read-only server queries and client-side directory interaction |
| Tests | `tests/` | Offline unit, integration, migration, rendering, and lifecycle coverage |

## Discovery is not acceptance

Search results are candidates, not trusted records. They may be stale, unrelated, incorrectly ranked, duplicated across queries, or outside the project scope.

```text
Discovery       → RawJob candidates
Classification  → accepted DiscoveredJob values
Persistence     → canonical jobs and lifecycle evidence
Projection      → website and README
```

The search that found a listing establishes provenance. It does not prove that the listing is a valid 2027 European technology internship or New Grad position.

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

Overlapping searches may discover the same job. The numeric LinkedIn ID keeps the listing canonical, while provenance remains associated with every search that found it.

Classification checks require explicit evidence for:

- exactly one normalized employment type: `internship` or `new-grad` (internship wins if both title signals appear);
- absence of configured seniority exclusions;
- a supported technology category;
- the target opportunity cycle;
- a European location.

Graduation-year eligibility language is not internship-cycle evidence. For title-explicit New Grad roles, a title year identifies the hiring cycle. Malformed or ambiguous candidates are excluded without failing unrelated candidates.

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

A later valid rediscovery can reactivate provenance and reopen a job.

Concurrent searches may finish out of order, so persisted observation timestamps use monotonic maximums rather than completion order.

Schema, transactions, provenance, closure, migrations, backup, and restore are owned by the [database lifecycle guide](../operations/database.md).

## Public projections

Canonical SQLite state feeds two read-only projections.

### Website

The Next.js website:

- opens short-lived read-only SQLite connections;
- returns every currently open listing;
- reads the latest completed collection time;
- performs search, filtering, sorting, and pagination as presentation behavior;
- never runs collection, classification, migrations, or lifecycle writes.

The website contract is documented in the [website guide](../user-guide/website.md).

### README preview

The renderer creates a deterministic bounded projection containing:

- total open-job count;
- latest successful collection time;
- the public website link;
- at most ten recently posted internships and ten recently posted New Grad positions.

The renderer owns one marked block and replaces it atomically. Validation reconstructs the expected projection from SQLite and requires exact equality.

The README cannot reconstruct canonical state because it omits most jobs, closed state, provenance, run history, and closure evidence.

## Dependency direction

```text
CLI
 ├── configuration
 ├── pipeline
 │    ├── transport + LinkedIn adapter
 │    ├── normalization + classification
 │    └── repository
 └── README renderer

repository → ORM → database session
migrations → ORM metadata
website → read-only SQLite
```

Dependency boundaries are intentional:

- source parsing does not write SQL;
- the repository does not parse HTML;
- classification does not render documentation;
- the website does not classify or mutate lifecycle state;
- the README renderer does not discover jobs;
- migrations describe schema evolution rather than application orchestration.

Business rules should remain independent from CLI presentation, network transport, and public projections.

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
- atomic README replacement;
- offline deterministic tests by default.

An upstream block or challenge is a stop condition, not a problem to bypass.

Exact authorization variables and network settings are documented in [Configuration](../getting-started/configuration.md). Disclosure and trust boundaries are defined in [`SECURITY.md`](../../../SECURITY.md).

## Extension policy

Good extensions preserve the existing boundaries. Examples include:

- focused search configuration;
- stricter, tested classification signals;
- sanitized parser fixtures for guest-HTML variations;
- additional read-only views;
- improved lifecycle observability;
- safer migrations and recovery checks;
- website accessibility, performance, and usability improvements.

The following require an explicit architecture and security decision before implementation:

- additional job providers;
- login, session, or browser-based collection;
- private endpoints;
- multiple concurrent writers;
- APIs or forms that mutate canonical state;
- user-provided content;
- new authentication or authorization surfaces;
- new canonical output formats.

Discuss boundary-changing proposals before implementation. Follow [`CONTRIBUTING.md`](../../../CONTRIBUTING.md) for review expectations and [`SECURITY.md`](../../../SECURITY.md) for security-sensitive changes.