# Automation

[← README](../README.md)

The repository separates offline quality assurance from network collection:

```text
CI workflow
  validates code, tests, schema, package runtime, and container

Collection workflow
  runs manually, only after an explicit repository authorization gate
```

## Continuous integration

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

Triggers:

- push to `main`;
- every pull request;
- manual `workflow_dispatch`.

Permissions are read-only for repository contents.

### Quality job

The `quality` job runs on Ubuntu and performs:

1. checkout;
2. `uv` setup with dependency caching;
3. frozen development dependency installation;
4. Ruff format verification;
5. Ruff lint;
6. strict mypy over source and tests;
7. offline pytest execution (`-m "not live"`);
8. Alembic/ORM migration consistency;
9. clean SQLite migration, README render, and validation smoke test.

The migration smoke test uses `data/ci.db`, not a developer database. Rendering against that fresh database proves the committed README markers work with an empty canonical store.

### Docker job

The separate `docker` job:

1. builds the production Dockerfile;
2. runs `internships --help` inside the image.

This catches missing packaged files, broken entry points, and production-only dependency problems independently of the local virtual environment.

CI never enables LinkedIn collection and never requires network fixtures from LinkedIn.

## Controlled collection workflow

Workflow: [`.github/workflows/scrape.yml`](../.github/workflows/scrape.yml)

Trigger: manual `workflow_dispatch` only.

The job-level condition requires this repository variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

If the variable is missing or differs in case/value, the collection job is skipped. Setting it is an operator attestation and must happen only after express LinkedIn permission; GitHub cannot verify that permission.

### Inputs

| Input | Default | Purpose |
|---|---:|---|
| `open_pull_request` | `false` | Create a branch and pull request when the generated README changed. |
| `allow_state_rebuild` | `false` | Permit deleting incompatible cached SQLite state if migration fails. Use only after backup review. |

### Concurrency and timeout

```yaml
concurrency:
  group: internship-collection
  cancel-in-progress: false
```

Only one collection workflow can operate at a time, and a newer dispatch does not cancel a running writer. The job timeout is 90 minutes.

This protects the one-writer SQLite lifecycle model. It does not replace LinkedIn request pacing, which is enforced inside the application.

### Workflow sequence

```text
checkout full Git history
        ↓
install frozen dependencies
        ↓
restore latest SQLite cache
        ↓
upgrade database
        ↓
scrape → classify → persist → render
        ↓
validate SQLite and README
        ↓
checkpoint SQLite WAL
        ↓
save cache + upload backup artifact
        ↓
optionally open README pull request
```

#### State restore

The workflow restores `data/internships.db` using:

```text
key: internship-db-<current-run-id>
restore prefix: internship-db-
```

Because the exact current key cannot already exist, the restore prefix selects a prior cache entry. GitHub cache is a convenience, not guaranteed archival storage: caches can expire or be evicted.

The uploaded artifact is the explicit short-term backup and should be downloaded when durable retention is required.

#### Migration and state rebuild

The workflow first runs:

```bash
uv run internships db-upgrade
```

On failure:

- with `allow_state_rebuild=false`, the workflow stops and preserves evidence;
- with `allow_state_rebuild=true`, it removes the SQLite file/sidecars and creates a fresh database.

A rebuild loses first-seen history, provenance, closure confirmations, and run diagnostics. Back up and investigate incompatible state before enabling it.

#### Collection exit handling

`internships scrape` uses:

| Exit | Workflow behavior |
|---:|---|
| `0` | Continue normally. |
| `1` | Stop: every selected search failed. |
| `2` | Continue as partial success; successful search transactions remain valid. |
| `3` | Stop: migration/state precondition failed. |

After success or partial success, `validate` must pass. A partial run can therefore publish results from successful searches without applying lifecycle mutations from failed searches.

#### Checkpoint, cache, and artifact

Before backup, Python's SQLite driver runs:

```sql
PRAGMA wal_checkpoint(TRUNCATE);
```

The workflow then:

- saves `data/internships.db` under the current run-specific cache key;
- uploads `data/internships.db` and `README.md` as `internship-state-<run-id>`;
- retains the artifact for 30 days.

Repository administrators should verify that artifact access matches the repository's data-handling expectations. See [Database lifecycle](database.md#backups).

#### Optional README pull request

When `open_pull_request=true` and `README.md` changed, the workflow:

1. creates `automated/readme-update-<run-id>`;
2. configures the standard GitHub Actions bot identity;
3. commits only `README.md`;
4. pushes the branch;
5. opens a pull request against `main` with `gh pr create`.

SQLite is never committed. If the README is unchanged, no branch or pull request is created.

The workflow currently grants `contents: write` and `pull-requests: write` for this optional path. Changes to workflow permissions should follow least privilege while preserving the selected behavior.

## Running collection manually

After documented permission, set the repository variable through:

```text
Repository Settings → Secrets and variables → Actions → Variables
```

Then dispatch:

```text
Actions → Collect internships → Run workflow
```

Choose `open_pull_request` deliberately. Leave `allow_state_rebuild` false during normal operation.

After completion:

1. inspect the collection summary and any partial failures;
2. confirm validation passed;
3. retain/download the database artifact when needed;
4. review the README diff or generated pull request;
5. inspect `stats` and per-search found/accepted values before tuning queries.

## Adding a schedule

A schedule is intentionally absent. Do not add one merely for convenience.

Before adding `schedule:`:

1. obtain and retain express LinkedIn authorization for unattended access;
2. confirm permitted frequency, endpoints, user agent, and request limits;
3. keep the repository authorization variable gate;
4. estimate worst-case duration and request volume from all search tiers/rechecks;
5. define cache-loss and database-backup recovery;
6. prevent overlapping writers;
7. document operator ownership and a rapid disable procedure;
8. update README, Security, and this guide;
9. test the workflow manually first.

A schedule must remain disableable without a code deployment, for example by setting the repository authorization variable to false.

## Future website publication

A website is also deferred. If added, it should consume a read-only projection from canonical SQLite state or a deterministic generated artifact. It must not become a second lifecycle writer or independently infer closure.

## Workflow security

- Do not place LinkedIn credentials in Actions; the project does not support them.
- Do not print `.env`, GitHub contexts, or database contents in logs.
- Keep third-party actions pinned to reviewed major/version references or stronger immutable references according to project policy.
- Treat pull requests from forks as untrusted and never expose collection/notification secrets to them.
- Review artifact retention and repository visibility.
- Stop collection when authorization is withdrawn by disabling the repository variable.

See [Security](../SECURITY.md) for private vulnerability reporting and complete operational boundaries.
