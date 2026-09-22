# European Tech Opportunities 2027 Database and Lifecycle Guide

[← Documentation hub](../../README.md) · [Architecture](../development/architecture.md) · [Automation](automation.md) · [Troubleshooting](troubleshooting.md) · [Security policy](../../../SECURITY.md)

This is the canonical database and lifecycle guide for the project. SQLite is the source of truth for operational lifecycle state. Search YAML defines discovery configuration, while the website, README, and public downloads remain read-only projections.

## Contents

- [Database location](#database-location)
- [Schema overview](#schema-overview)
- [Canonical job state](#canonical-job-state)
- [Search state and runs](#search-state-and-runs)
- [Provenance](#provenance)
- [Successful search transaction](#successful-search-transaction)
- [Manual job insertion](#manual-job-insertion)
- [Closure lifecycle](#closure-lifecycle)
- [Daily full-state availability audit](#daily-full-state-availability-audit)
- [Timestamp invariants](#timestamp-invariants)
- [One-writer model](#one-writer-model)
- [Migrations](#migrations)
- [Backup](#backup)
- [Restore](#restore)
- [Projection consistency](#projection-consistency)
- [Data handling](#data-handling)

## Database location

Default database path:

```text
data/opportunities.db
```

The database and SQLite sidecars are ignored by Git.

### Legacy database rename

Deployments created before the Opportunities rename must stop all writers and rename `internships.db` to `opportunities.db` before starting the updated pipeline or website. Move any active `-wal` and `-shm` sidecars together, or checkpoint WAL before renaming.

## Schema overview

```text
searches 1 ──────── * search_runs
   │
   └──── 1 ─────── * job_searches * ─────── 1 jobs

alembic_version records the current schema revision
```

| Table | Primary key | Responsibility |
|---|---|---|
| `jobs` | `linkedin_job_id` | Accepted listing fields, category, timestamps, and open or closed state |
| `searches` | `slug` | Synchronized search identity, configuration, and enabled state |
| `search_runs` | UUID `id` | Per-search outcome, counts, timing, warnings, and sanitized diagnostics |
| `job_searches` | `(search_slug, linkedin_job_id)` | Search provenance and explicit unavailability evidence |
| `alembic_version` | revision | Current Alembic schema revision |

## Canonical job state

Important `jobs` fields:

| Field | Meaning |
|---|---|
| `linkedin_job_id` | Canonical numeric identity |
| `company`, `title`, `location`, `link` | Normalized public listing data |
| `category` | Deterministic internal technology category |
| `industries` | Structured source industries criterion, when available |
| `employment_type` | Required deterministic type: `internship` or `new-grad` |
| `start_date` | Explicit month or season plus year, when available |
| `first_seen_at` | Inferred LinkedIn publication time for new rows; immutable |
| `last_seen_at` | Latest successful listing observation or availability validation; monotonic |
| `updated_at` | Latest material field change, reopen, or close |
| `status` | `open` or `closed` |

Distinct LinkedIn IDs remain distinct jobs even when their display fields match.

Every accepted row has one employment type. The migration introducing New Grad support backfills all pre-existing rows as `internship`, because the former classifier accepted internships only. Missing optional metadata does not erase a previously observed value.

## Search state and runs

Before collection, YAML definitions synchronize into `searches`:

- new slugs are inserted;
- changed definitions update their configuration hash;
- removed slugs are disabled rather than deleted;
- YAML remains configuration, not lifecycle state.

Each selected search creates one `search_runs` row.

Successful runs record:

- found, accepted, and excluded counts;
- warning count;
- start and finish timestamps;
- duration.

Failed runs store bounded sanitized diagnostics.

Because every search has its own run record and transaction, partial pipeline execution can preserve successful results without applying lifecycle changes from failed searches.

## Provenance

A job may be discovered through several role, employer, or country searches.

`job_searches` tracks every association independently:

- first observation;
- latest accepted observation;
- latest successful run;
- consecutive explicit-unavailability confirmations;
- whether the association is active.

This distinction is fundamental:

```text
absent from one search page
        ≠
explicitly unavailable
```

Search ranking, pagination, card disappearance, or query changes cannot close a job by themselves.

## Successful search transaction

Each successful search commits atomically:

<div align="center">
<pre>
insert successful search run
↓
upsert accepted jobs
↓
insert or refresh provenance
↓
apply explicit 404/410 confirmations
↓
deactivate threshold-reaching associations
↓
close jobs with no active association
</pre>
</div>

A failure rolls back the complete search transaction.

Rediscovery:

- refreshes available public metadata;
- reactivates provenance;
- resets explicit-unavailability confirmations;
- can reopen a previously closed job.

## Manual job insertion

Maintainers may add a known, validated LinkedIn listing through `opportunities add-job`. The repository writes the `jobs` row directly without creating a synthetic search, search run, or `job_searches` association.

For a new row, the command records it as open and initializes `first_seen_at` from the supplied posting timestamp when present, bounded by the actual observation time. Otherwise, the observation time is used. For an existing row, normal public fields are refreshed, omitted optional metadata remains preserved, `first_seen_at` remains immutable, lifecycle timestamps remain monotonic, and a closed row is reopened.

Manual rows participate in all normal read paths and the full-state availability audit. If collection later discovers the same numeric LinkedIn ID, the successful search transaction updates the existing row and attaches genuine search provenance. Manual insertion never changes collection statistics or the latest successful collection timestamp.

## Closure lifecycle

Search-card absence is never closure evidence.

For each successful search:

1. select active jobs associated with that search;
2. choose a deterministic bounded subset missing from current eligible cards;
3. fetch their detail pages;
4. increment confirmation only for HTTP `404` or `410`;
5. reset confirmations when a valid accepted detail page is observed;
6. ignore malformed or newly excluded details as closure evidence;
7. apply no lifecycle mutation after unrelated network failures;
8. deactivate the association when `closure_confirmation_runs` is reached;
9. close the job only when no active search association remains;
10. reopen the job after a later valid rediscovery.

With a threshold of two:

```text
first 404  → confirmation 1; association remains active
second 404 → association becomes inactive

another active association → job remains open
no active association      → job closes
```

Deleting or disabling search YAML does not close jobs.

The confirmation threshold is configured through `OPPORTUNITIES_CLOSURE_CONFIRMATION_RUNS`; see [Configuration](../getting-started/configuration.md#environment-reference).

## Daily full-state availability audit

The scheduled workflow runs `opportunities check-availability` once per day before collection. Unlike bounded per-search rechecks, this pass checks the public listing for every row, including closed rows. A successful public page without a closure alert is then followed by guest detail validation.

Results are deliberately narrow:

```text
public page without a closure alert + valid guest detail → keep or reopen the job
HTTP 404 or 410 from either request                    → delete the job and job_searches rows
scoped “No longer accepting applications” alert       → delete the job and job_searches rows
anything else                                          → preserve the job as inconclusive
```

The auditor collects every outcome before applying confirmed changes in one transaction. Rate limits, authentication failures, redirects, server errors, invalid content, and transport failures never become deletion evidence. Search and run history remain available after a job deletion.

The README is regenerated after the transaction. The nightly workflow includes the audit result in its combined, README-only pull request, dispatches and awaits validation on that generated commit, and requests auto-merge only after the exact-scope check and successful runs. A manual availability-only run uses a separate validated, manual-review pull request. SQLite remains the runtime source of truth and is not committed to Git.

## Timestamp invariants

Concurrent searches may finish out of order.

Persistence therefore uses monotonic timestamp updates:

```text
next timestamp = max(existing timestamp, observed timestamp)
```

This applies to job and association observations and prevents state from moving backwards. On a job’s first insert, `first_seen_at` is initialized from LinkedIn’s relative posting age or an explicitly supplied manual posting timestamp; later observations never rewrite it. Provenance timestamps continue to represent actual search observations.

Validation requires:

```text
last_seen_at >= first_seen_at
```

`first_seen_at` remains immutable after insertion. For a new row, it is initialized from the inferred LinkedIn posting timestamp when available, bounded so it can never be later than the actual observation time; otherwise it uses the first accepted observation time. Missing posting metadata excludes a yearless listing, but a listing with explicit target-cycle evidence may still be admitted. Known jobs may also be rechecked safely without treating missing current posting-age metadata as closure evidence.

## One-writer model

Only one collection or maintenance process may write the database at a time.

Supported concurrent access:

- one controlled application writer;
- multiple read-only website requests.

GitHub collection workflows share a concurrency group to preserve this model.

Do not run an independent local or VPS collector against the same file.

The website must open SQLite in read-only mode and must never run migrations or lifecycle mutations.

## Migrations

Upgrade the configured database:

```bash
uv run opportunities db-upgrade
```

Verify Alembic and SQLAlchemy agreement:

```bash
uv run python scripts/check_migrations.py
```

For a schema change:

1. update `src/opportunities/database/models.py`;
2. create a new revision under `migrations/versions/`;
3. point `down_revision` to the current head;
4. preserve existing data in `upgrade()`;
5. provide a practical `downgrade()`;
6. add migration and repository tests;
7. test a fresh database;
8. test a representative backup when existing state changes;
9. run migration consistency checks.

Never rewrite an applied migration to hide schema drift.

A rebuild is not a normal migration strategy because it loses first-seen history, provenance, closure evidence, and run diagnostics.

Contributor expectations are summarized in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#database-and-migrations).

## Backup

When SQLite may still be open, use the backup API:

```bash
uv run python -c "import sqlite3; s=sqlite3.connect('data/opportunities.db'); d=sqlite3.connect('data/opportunities.backup.db'); s.backup(d); d.close(); s.close()"
```

Store backups outside normal repository cleanup paths and treat verified durable snapshots as the preferred recovery source for production state.

For a cold filesystem copy:

1. stop every writer;
2. close active SQLite connections where practical;
3. checkpoint write-ahead logging;
4. copy the database and any required sidecars together.

GitHub Actions checkpoints WAL, then uses the SQLite backup API to create a timestamped snapshot through a restricted VPS SFTP account. Each snapshot has a strict manifest containing its SHA-256 checksum, schema revision, collection and creation timestamps, previous-snapshot reference, and configured retention metadata. The workflow round-trips and opens uploaded files before atomically advancing the latest pointer. Canonical SQLite is never placed in GitHub Actions cache or artifacts; 30-day artifacts contain only sanitized public projections.

VPS deployment also preserves the previous canonical file as:

```text
opportunities.db.previous
```

Restricted VPS snapshot storage, sanitized artifacts, retention, and deployment sequencing are documented in [Automation](automation.md#state-continuity-and-artifacts).

## Restore

1. Stop every process that may write the database.
2. Stop or restart readers that could retain stale file handles.
3. Preserve the current or damaged state separately.
4. Select a timestamped durable snapshot; inspect its collection time, schema revision, checksum, and previous-snapshot link.
5. Download both the immutable database object and its manifest.
6. Verify the manifest and database before replacement:

```bash
uv run python scripts/canonical_snapshot.py verify \
  --database /safe/recovery/opportunities.db \
  --manifest /safe/recovery/manifest.json
```

7. Restore the verified database atomically; do not replace state with unverified bytes.
8. Remove stale sidecars only while no SQLite connection is open.
9. Run:

```bash
uv run opportunities db-upgrade
uv run opportunities stats
```

When the restored database contains the representative state expected by the committed README preview, also run:

```bash
uv run opportunities render
uv run opportunities validate
```

A fresh rebuild loses lifecycle history. Do not delete the database as the first response to migration, locking, or integrity problems.

For symptom-based diagnosis before destructive recovery, use [Troubleshooting](troubleshooting.md#database-and-migration-failures).

## Projection consistency

SQLite remains the source of truth even though the project exposes three read-only public projections.

### Website

The website reads every currently open row through short-lived read-only SQLite connections.

It does not:

- classify listings;
- update jobs;
- apply migrations;
- close or reopen state.

The website contract belongs to the [website guide](../user-guide/website.md#read-only-database-contract).

### README preview

`render` produces:

- total open-job count;
- latest successful collection time;
- the public website link;
- at most five recently discovered open internships and five recently discovered open New Grad opportunities.

The renderer owns the marked opportunity-count and opportunity-preview regions and replaces the resulting README atomically.

`validate` rebuilds both expected regions in memory and requires exact equality with the committed projection.

Never reconstruct lifecycle state from the README. It omits:

- closed jobs;
- most open jobs;
- provenance;
- search runs;
- closure confirmations;
- operational diagnostics.

Manual edits inside the generated regions are overwritten.

### Public exports

The pipeline generates `open-opportunities.csv` and `open-opportunities.json` from the same currently open rows. Only the approved public export fields are serialized: LinkedIn job ID, company, title, location, listing URL, category, industries, employment type, and start date.

The files exclude job status, all timestamps, provenance, search runs, closure confirmations, diagnostics, and other lifecycle or operational state. They are validated against SQLite, atomically replaced, and deployed beside the database for read-only website delivery. They are disposable projections and cannot restore lifecycle history.

## Data handling

The database should contain public listing metadata and operational history, never:

- credentials;
- LinkedIn cookies or sessions;
- authenticated HTML;
- access tokens;
- private environment values.

Do not commit databases or sidecars, and do not attach production state to public issues.

Restrict access to:

- restricted VPS snapshots and manifests;
- backups and independent replicas;
- VPS volume state;
- temporary deployment copies.

Do not place canonical SQLite or its manifest in GitHub Actions cache or artifacts. Workflow artifacts may contain only explicitly sanitized public projections and ordinary quality reports.

Review the disclosure and handling requirements in [`SECURITY.md`](../../../SECURITY.md).
