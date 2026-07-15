# Database lifecycle

[← README](../README.md)

SQLite is the canonical operational state for the project. The README is a generated projection and search YAML is configuration; neither replaces job history, provenance, or lifecycle state stored in the database.

Default path:

```text
data/internships.db
```

The database and SQLite sidecar files are ignored by Git. Preserve and back up this file when operating a long-lived collector.

## Schema overview

The focused schema has four application tables plus Alembic's version table:

```text
searches
  ├── has many search_runs
  └── has many job_searches

jobs
  └── has many job_searches

job_searches
  ├── links one search to one job
  └── records the last search_run that observed that relationship

alembic_version
  └── records the current database schema migration
```

| Table | Primary key | Purpose |
|---|---|---|
| `jobs` | `linkedin_job_id` | Canonical accepted job fields, technology category, timestamps, and open/closed status. |
| `searches` | `slug` | Last synchronized search name, keywords, location, enabled state, config hash, and update time. |
| `search_runs` | UUID `id` | Per-search status, timing, counts, warnings, and sanitized errors. |
| `job_searches` | `(search_slug, linkedin_job_id)` | Provenance, observation times, last run, unavailability confirmations, and active state. |
| `alembic_version` | revision ID | Alembic's applied schema revision. |

## `jobs`

A job is identified only by its numeric LinkedIn job ID. Different LinkedIn IDs remain separate even when company, title, and location look identical.

Important fields:

| Field | Meaning |
|---|---|
| `linkedin_job_id` | Canonical source identity. |
| `company` | Parsed and cleaned display company. |
| `title` | Normalized display title. |
| `location` | Semicolon-joined normalized explicit locations. |
| `link` | Canonical public `https://www.linkedin.com/jobs/view/<id>` URL; unique. |
| `category` | Internal `InternshipCategory` string used for filtering/statistics, not README output. |
| `first_seen_at` | First accepted observation time. Never moves. |
| `last_seen_at` | Latest accepted observation time across searches. Never moves backwards. |
| `updated_at` | Latest material field/status change. |
| `status` | `open` or `closed`. |

Open jobs are ordered case-insensitively by company and title, then location, before README rendering.

## `searches`

Before a collection run, enabled YAML definitions are synchronized into `searches`.

- New slugs are inserted.
- Existing slugs update name, keywords, location, enabled state, config hash, and timestamp.
- Database slugs absent from the selected synchronized registry are marked disabled.
- Historical runs, jobs, and provenance are retained.

The SHA-256 `config_hash` is computed from a stable JSON representation of the complete validated search model. It records configuration changes without making YAML the lifecycle store.

Renaming a slug creates a new identity. Prefer stable slugs.

## `search_runs`

Every selected search produces an independent run row.

Successful rows record:

- start, finish, and duration;
- eligible candidate count;
- accepted and excluded counts;
- parser warning count.

Failed rows record zero counts plus a bounded `error_code` and sanitized `error_message`. Raw response bodies and exception internals are not persisted.

A partial pipeline can therefore contain committed successful run rows and committed failed run rows. Failure in one search does not roll back another search.

The `searches` CLI command reads the latest run per enabled slug to display status and found/accepted counts. `stats` aggregates successful and failed run totals.

## `job_searches` provenance

A job can be discovered by several role, employer, and country queries. `job_searches` preserves each association separately.

| Field | Meaning |
|---|---|
| `search_slug` | Search that observed the job. |
| `linkedin_job_id` | Canonical job. |
| `first_seen_at` | First observation by this search. |
| `last_seen_at` | Latest observation by this search. |
| `last_seen_run_id` | Successful run that last observed it. |
| `unavailable_confirmations` | Consecutive explicit detail-page `404`/`410` confirmations. |
| `active` | Whether this association still supports the job being open. |

This table is why the project can distinguish “not ranked in this search today” from “the detail page is repeatedly unavailable.”

## Successful persistence transaction

Each successful search is stored in one short transaction:

```text
insert successful search_run
          ↓
upsert every accepted job
          ↓
insert or refresh job_search provenance
          ↓
apply explicit unavailable confirmations
          ↓
deactivate associations reaching threshold
          ↓
close jobs with no active associations
          ↓
commit
```

If any step raises, the transaction rolls back. The search cannot leave half-written jobs or lifecycle changes.

### New job

A new ID creates:

- one open `jobs` row;
- one active `job_searches` row;
- equal first/last observation timestamps.

### Existing job

Rediscovery updates company, title, location, link, and category from the accepted detail. It advances `last_seen_at` using the maximum of existing and incoming times, resets that search association's unavailable confirmations, and marks the association active.

A material field change advances `updated_at`. Merely seeing an unchanged open job advances `last_seen_at` but does not create an artificial content update.

### Reopened job

If a closed job is accepted again, it becomes open and the persistence summary counts one reopen. Its rediscovered association becomes active with zero unavailable confirmations.

## Closure algorithm

Search-page absence is never closure evidence.

For each successful search:

1. Collect active known jobs associated with that search.
2. Identify those absent from the current eligible card set.
3. Recheck at most that search's `max_rechecks` detail pages.
4. If a detail returns HTTP `404` or `410`, increment the association's confirmation count.
5. If detail succeeds and the job remains accepted, refresh the association and reset confirmations to zero.
6. If the fetched job is excluded or detail is malformed, do not count new closure evidence; no accepted-job refresh occurs.
7. If another HTTP/network failure occurs, fail the search and apply no lifecycle mutation for it.
8. Deactivate an association only after `closure_confirmation_runs` explicit confirmations.
9. Close the job only when it has no active associations from any search.

Example with the default threshold of two:

```text
Run 1: absent from cards, detail 404 → confirmations 1, still active/open
Run 2: absent from cards, detail 404 → confirmations 2, association inactive
Other active association exists      → job remains open
No active association exists         → job closes
Later valid rediscovery              → job and association reopen
```

Deleting, disabling, or changing a search does not directly close jobs.

## Timestamp invariants

Searches run concurrently and can finish out of start order. Persistence therefore uses monotonic updates:

```text
new last_seen_at = max(existing last_seen_at, observed_at)
```

The same rule applies to job-search association timestamps and closure/update timestamps where relevant.

`internships validate` checks that no stored job has `last_seen_at < first_seen_at`. All datetimes are normalized to UTC when mapped out of SQLite.

## One-writer model

The supported runtime uses one collection pipeline writing SQLite. Successful searches are persisted sequentially in short transactions after concurrent fetching finishes.

Do not run two `scrape` processes against the same file. SQLite can support concurrent readers, but competing lifecycle writers can create lock contention and violate operational assumptions even when individual transactions remain valid.

The manual GitHub workflow uses a concurrency group with `cancel-in-progress: false` to prevent overlapping collection runs.

## Migrations

SQLAlchemy models declare the desired current schema. Alembic migration files declare how a real database reaches that schema.

Relevant paths:

```text
alembic.ini
migrations/env.py
migrations/script.py.mako
migrations/versions/
src/internships/database/migrations.py
scripts/check_migrations.py
```

Upgrade to the latest committed revision:

```bash
uv run internships db-upgrade
```

`upgrade_database()` calls Alembic upgrade-to-head twice. The second call must be a no-op; if the first revision row were not committed correctly, reapplying the schema would expose the problem.

Check that a fresh database at migration head exactly matches ORM metadata:

```bash
uv run python scripts/check_migrations.py
```

The check:

1. creates a temporary SQLite file;
2. upgrades it to head;
3. confirms `alembic_version` equals the single committed head;
4. compares the resulting schema with `Base.metadata`;
5. fails on any unrepresented ORM difference.

### Changing schema

When changing a table, column, index, constraint, or persisted representation:

1. update SQLAlchemy models;
2. generate or write a new revision under `migrations/versions/`;
3. set `down_revision` to the current head;
4. implement a data-preserving `upgrade()`;
5. implement a safe `downgrade()` where practical;
6. add migration/repository tests;
7. test both a fresh database and a representative backup;
8. run all migration checks.

Do not edit or delete an applied migration merely to make autogeneration pass.

## Backups

Use SQLite's backup API while the database may be open:

```bash
uv run python -c "import sqlite3; source=sqlite3.connect('data/internships.db'); target=sqlite3.connect('data/internships.backup.db'); source.backup(target); target.close(); source.close()"
```

Then store `data/internships.backup.db` somewhere protected from repository cleanup.

For a cold file copy:

1. stop every writer;
2. checkpoint WAL if enabled;
3. close database connections;
4. copy the database and any relevant sidecars together.

The GitHub collection workflow checkpoints SQLite before caching/uploading its backup artifact.

## Restore and recovery

Safe restore procedure:

1. stop collection and any process using the database;
2. preserve the damaged/current file separately for investigation;
3. restore the known-good backup to the configured path;
4. remove stale `-wal` and `-shm` sidecars only while no connection is open and only when they do not belong to the restored backup;
5. run `uv run internships db-upgrade`;
6. run `uv run internships render`;
7. run `uv run internships validate`;
8. inspect `uv run internships stats` before collecting again.

Do not use deletion/rebuild as the first response to a migration or validation failure. Rebuilding loses closure evidence, first-seen history, provenance, and run diagnostics.

## README consistency

Render from canonical state:

```bash
uv run internships render
```

Verify exact agreement:

```bash
uv run internships validate
```

Manual edits inside the generated block, including the open-count and last-collection metadata lines, are overwritten and cause validation failure. Documentation outside the marker block is preserved.

## Data handling

The database is designed to contain public listing metadata and operational history, not credentials. Nevertheless:

- do not commit it;
- do not attach it to public issues without reviewing content;
- control access to workflow artifacts;
- back it up before risky changes;
- never store cookies, tokens, or authenticated HTML in its diagnostic fields.

See [Security](../SECURITY.md) for the full data-safety model.
