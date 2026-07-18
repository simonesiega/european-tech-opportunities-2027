# European Tech Internships 2027 Database and Lifecycle Guide

[← Documentation](../README.md) · [Architecture](../development/architecture.md) · [Automation](automation.md)

SQLite is the project’s canonical operational state. Search YAML defines discovery configuration, while the website and README remain read-only projections.

Default database path:

```text
data/internships.db
```

The database and SQLite sidecars are ignored by Git.

## Contents

- [Schema overview](#schema-overview)
- [Canonical job state](#canonical-job-state)
- [Search state and runs](#search-state-and-runs)
- [Provenance](#provenance)
- [Successful search transaction](#successful-search-transaction)
- [Closure lifecycle](#closure-lifecycle)
- [Timestamp invariants](#timestamp-invariants)
- [One-writer model](#one-writer-model)
- [Migrations](#migrations)
- [Backup](#backup)
- [Restore](#restore)
- [Projection consistency](#projection-consistency)
- [Data handling](#data-handling)

## Schema overview

```text
searches <── search_runs
    │
    └─── job_searches ──> jobs

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
| `first_seen_at` | First accepted observation; immutable |
| `last_seen_at` | Latest accepted observation; monotonic |
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
- warnings;
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

Search ranking, pagination, or query changes cannot close a job by themselves.

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

The confirmation threshold is configured through `INTERNSHIPS_CLOSURE_CONFIRMATION_RUNS`; see [Configuration](../getting-started/configuration.md#environment-reference).

## Timestamp invariants

Concurrent searches may finish out of order.

Persistence therefore uses monotonic timestamp updates:

```text
next timestamp = max(existing timestamp, observed timestamp)
```

This applies to job and association observations and prevents state from moving backwards.

Validation requires:

```text
last_seen_at >= first_seen_at
```

`first_seen_at` remains immutable after the first accepted observation.

## One-writer model

Only one collection or maintenance process may write canonical state at a time.

Supported concurrent access:

- one controlled application writer;
- multiple read-only website requests.

GitHub collection and database-maintenance workflows share a concurrency group to preserve this model.

Do not run an independent local or VPS collector against the same canonical file.

The website must open SQLite in read-only mode and must never run migrations or lifecycle mutations.

## Migrations

Upgrade the configured database:

```bash
uv run internships db-upgrade
```

Verify Alembic and SQLAlchemy agreement:

```bash
uv run python scripts/check_migrations.py
```

For a schema change:

1. update `src/internships/database/models.py`;
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
uv run python -c "import sqlite3; s=sqlite3.connect('data/internships.db'); d=sqlite3.connect('data/internships.backup.db'); s.backup(d); d.close(); s.close()"
```

Store backups outside normal repository cleanup paths.

For a cold filesystem copy:

1. stop every writer;
2. close active SQLite connections where practical;
3. checkpoint write-ahead logging;
4. copy the database and any required sidecars together.

GitHub Actions checkpoints WAL before cache or artifact publication. VPS deployment also preserves the previous canonical file as:

```text
internships.db.previous
```

Workflow cache, artifacts, and deployment sequencing are documented in [Automation](automation.md#state-continuity-and-artifacts).

## Restore

1. Stop every process that may write the database.
2. Stop or restart readers that could retain stale file handles.
3. Preserve the current or damaged state separately.
4. Restore a known-good backup.
5. Remove stale sidecars only while no SQLite connection is open.
6. Run:

```bash
uv run internships db-upgrade
uv run internships stats
```

When the restored database contains the representative state expected by the committed README preview, also run:

```bash
uv run internships render
uv run internships validate
```

A fresh rebuild loses lifecycle history. Do not delete canonical state as the first response to migration, locking, or integrity problems.

For symptom-based diagnosis before destructive recovery, use [Troubleshooting](troubleshooting.md#database-and-migration-failures).

## Projection consistency

SQLite remains canonical even though the project exposes two public projections.

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
- at most ten recently discovered open internships and ten recently discovered open New Grad positions.

The renderer owns only the marked internship block and replaces it atomically.

`validate` rebuilds the expected block in memory and requires exact equality with the committed projection.

Never reconstruct canonical state from the README. It omits:

- closed jobs;
- most open jobs;
- provenance;
- search runs;
- closure confirmations;
- operational diagnostics.

Manual edits inside the generated block are overwritten.

## Data handling

The database should contain public listing metadata and operational history, never:

- credentials;
- LinkedIn cookies or sessions;
- authenticated HTML;
- access tokens;
- private environment values.

Do not commit databases or sidecars, and do not attach production state to public issues.

Restrict access to:

- backups;
- GitHub Actions artifacts;
- workflow caches;
- VPS volume state;
- temporary deployment copies.

Review the disclosure and handling requirements in [`SECURITY.md`](../../../SECURITY.md).