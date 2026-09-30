# Architecture and invariants

[← Maintainer handbook](../README.md) · [Classification](classification.md) · [Database lifecycle](../operations/database.md) · [Security policy](../../../SECURITY.md)

One permission-gated LinkedIn guest-HTML adapter feeds a deterministic classifier and one canonical SQLite lifecycle store. The website, API, downloads, and bounded README are read-only projections.

[Open the annotated repository maps](../../assets/diagram/README.md) for five subsystem views and links to implementation. The overview below connects configuration, lifecycle state, public projections, and supporting tools.

![Repository overview connecting configuration, the Python pipeline, canonical SQLite, read-only publication, and supporting operations](../../assets/diagram/svg/repository.svg)

## Architectural principles

| Contract | Required behavior |
|---|---|
| Identity | Numeric LinkedIn job IDs uniquely identify listings; distinct IDs remain distinct |
| Canonical state | SQLite alone owns lifecycle truth; public files cannot reconstruct it |
| Strict acceptance | Ambiguous type, role, seniority, cycle/posting date, or geography is excluded |
| Safe closure | Search-page disappearance never closes a job |
| Failure isolation | Failed searches record diagnostics, not lifecycle mutations |
| One writer | Canonical application writes occur through `Repository`; Alembic owns schema evolution |
| Bounded access | Requests, retries, pages, results, concurrency, response sizes, and pacing remain limited |
| Unauthenticated source | No source credentials, cookies, browser collection, private endpoints, or evasion |
| Read-only projections | Presentation does not collect, classify, migrate, or mutate canonical state |
| Determinism | The same evidence and settings produce the same classification and publication |

These are contracts, not suggestions. Review [SECURITY.md](../../../SECURITY.md) before proposing a changed boundary.

## Component map

| Owner | Path | Responsibility |
|---|---|---|
| CLI | `src/opportunities/cli/` | Preconditions, command input, orchestration, output and exit codes |
| Configuration | `src/opportunities/config/`, `configs/` | Settings, rules, recursive search registry and limits |
| Transport | `src/opportunities/scrapers/http.py` | Authorization interlock, approved endpoints, no redirects/cookies, bounded retries and pacing |
| Source adapter | `src/opportunities/scrapers/linkedin.py` | Guest URL construction, cards, detail identity, structured metadata and closure alerts |
| Normalization | `src/opportunities/normalization/` | Stable title and conservative location signals |
| Classification | `src/opportunities/pipeline/classification.py` | Pure acceptance/rejection decisions |
| Collection orchestration | `src/opportunities/pipeline/runner.py` | Bounded concurrent discovery, isolated outcomes, serialized persistence |
| Availability | `src/opportunities/pipeline/availability.py` | Full-state explicit evidence audit |
| Persistence | `src/opportunities/database/`, `migrations/` | Transactions, provenance, lifecycle, snapshots and schema evolution |
| Projections | `src/opportunities/readme.py`, `public_exports.py`, `search_registry_docs.py` | Generated regions, public serialization and validation |
| Website | `site/src/lib/`, `site/src/components/` | Server-only read-only queries; client-only interaction |
| Operations | `scripts/`, `.github/workflows/` | Verified recovery, validation, review handoff and release-pointer deployment |

## Discovery is not acceptance

Search YAML controls **where to look**, not what may be published. Search cards undergo company/title prefilters before bounded detail fetching. Detail responses must independently contain title and company identity; a current card cannot make a generic HTTP-success page valid. Detail location may fall back to card location.

Overlapping searches share in-flight detail requests by numeric ID. Completed response bodies are evicted; one cancelled search must not cancel a request another search uses. Accepted `DiscoveredJob` values cross the repository boundary only after normalization and [classification](classification.md).

[Search registry](search-registry.md) owns discovery schema and pagination; [Configuration](../getting-started/configuration.md#http-policy) owns transport tuning. Never add acceptance rules to the website, YAML workflow, or README renderer.

## Failure isolation

Searches fetch concurrently, then outcomes persist in finish-time order. Each successful search commits independently. A failed search records bounded, sanitized diagnostics but does not upsert jobs, apply absence, confirm unavailability, or close rows. A partial batch preserves successful work. [CLI exit codes](../operations/cli.md#exit-codes) are canonical.

The search start is a conservative observation lower bound: a detail page fetched early in a slow search must not overrule a newer observation merely because its search finished later. Repository stale-evidence guards and monotonic timestamps enforce this. Exact transitions, the separate full-state audit, and migrations belong to [Database and lifecycle](../operations/database.md).

## Public projections

| Projection | Owner and contract |
|---|---|
| Website | Short-lived read-only SQLite connections; all open rows and latest successful collection time; [website engineering](website.md) |
| API | Same query and release selection, bounded inputs and explicit field allowlist; [v1 contract](../../users/data/api.md) |
| CSV / JSON / metadata | Python renderer selects approved fields, neutralizes CSV formulas, validates schema/bytes/counts/hashes, and atomically replaces files; [download contract](../../users/data/data.md) |
| README | Renderer owns exactly one count region and one preview region; maximum five newest rows per employment type |
| Registry documentation | Renderer owns the search-directory count block, not the surrounding guide |

The README includes a hidden SHA-256 seal covering **every** website-visible open row and the exact last-successful-collection timestamp, including rows outside its preview. Validation reconstructs both regions from SQLite and requires equality. [Automation's reviewed-state barrier](../operations/automation.md#first-public-state-review-seal) prevents deploying unreviewed public state. A hash alone does not explain a change: review the sanitized artifact and protected evidence when necessary.

Coverage metrics are a separate generated region in [Testing](testing.md#coverage-baseline), owned by `scripts/docs/coverage_docs.py`. No production database is needed to refresh them.

## Dependency direction

CLI → configuration / pipeline / repository / projection renderers. Pipeline → transport + parser / normalization + classifier / repository. Repository → models + database session. Website → read-only SQLite; downloads → fixed generated files. The parser does not write SQL, the repository does not parse HTML, and renderers do not discover jobs.

Maintainer `add-job` / `add-jobs` is an offline input path through the same classifier and repository upsert. It validates supplied facts but cannot authenticate them, rejects manual reopening of closed rows, and invents no search provenance. [CLI](../operations/cli.md#add-jobs) owns the input contract; [Database](../operations/database.md#manual-job-insertion) owns transaction semantics.

## Browser-local state is not lifecycle state

Saved, applied, hidden, and visit timestamps exist only in browser localStorage. They contain IDs, not job metadata or application details, and never reach SQLite or the API. [Website engineering](website.md#local-state-contract) owns storage semantics; [Privacy](../../../PRIVACY.md) owns the disclosure.

## Extension policy

Focused searches, stricter classification with nearby rejection tests, sanitized fixtures, read-only views, accessibility improvements, and safer recovery checks can preserve these boundaries. Additional providers, source authentication/browser collection, multiple writers, server-stored application state, mutation APIs, user content, or new authentication surfaces require explicit architecture and security review. Do not introduce them as incidental refactoring.
