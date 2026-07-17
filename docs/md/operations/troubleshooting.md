# European Tech Internships 2027 Troubleshooting Guide

[← Documentation](../README.md) · [CLI reference](../user-guide/cli.md) · [Database lifecycle](database.md)

Start with the command’s exit code and first sanitized error. Preserve canonical state before making changes.

Do not delete SQLite, weaken classification rules, increase collection limits blindly, or bypass authorization as a shortcut.

## Contents

- [First diagnostics](#first-diagnostics)
- [Exit codes](#exit-codes)
- [Configuration failures](#configuration-failures)
- [Database and migration failures](#database-and-migration-failures)
- [README projection failures](#readme-projection-failures)
- [Collection failures](#collection-failures)
- [Classification and parsing problems](#classification-and-parsing-problems)
- [Lifecycle problems](#lifecycle-problems)
- [GitHub Actions and deployment](#github-actions-and-deployment)
- [Docker failures](#docker-failures)
- [Requesting help](#requesting-help)

## First diagnostics

From the repository root, record:

```bash
uv --version
uv run python --version
uv run internships --help
uv run internships searches
uv run internships stats
```

Also verify:

- the current Git branch and commit;
- the working directory;
- whether `.env` or a settings YAML is being loaded;
- `INTERNSHIPS_DATABASE_URL`;
- process-environment overrides;
- whether execution is local, Docker, or GitHub Actions;
- the exact command and exit code.

Never paste a complete environment file, production database, authenticated HTML, secret, or unredacted workflow context into an issue.

## Exit codes

| Code | Meaning | First action |
|---:|---|---|
| `0` | Success | No recovery action required |
| `1` | Complete collection failure or validation mismatch | Preserve state and inspect per-search or projection output |
| `2` | Partial collection or invalid command/configuration | Separate successful work from the command-specific failure |
| `3` | Database missing tables or not at migration head | Run `db-upgrade` against the same database URL |

Command-specific behavior is documented in the [CLI reference](../user-guide/cli.md#exit-codes).

## Configuration failures

### Invalid configuration or search registry

Common causes:

- unknown YAML field;
- YAML root is not a mapping;
- malformed lowercase kebab-case slug;
- duplicate slug or effective query identity;
- unsupported workplace or date filter;
- invalid boolean, timeout, log level, or database URL;
- `max_results` greater than `max_pages × 25`;
- unexpected process-environment override.

Run:

```bash
uv run internships searches
uv run pytest tests/unit/test_config.py
```

For a specific settings file:

```bash
uv run internships --settings configs/settings.local.yml stats
```

Correct the first validation error before investigating later messages.

Configuration precedence, variables, and limits are defined in [Configuration](../getting-started/configuration.md).

### LinkedIn collection is disabled

This is the safe default.

Local or Docker collection requires:

```text
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true
```

GitHub Actions collection requires:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

Neither value grants permission.

When the GitHub variable is missing or different, collection stops before LinkedIn network access. Leave the interlocks disabled unless express authorization exists.

### `setup-uv` cannot determine a version

Current workflows pin:

- the setup action revision;
- `uv` 0.11.6;
- Python 3.12.

Logs showing fallback to a latest-release API usually indicate an outdated workflow revision.

Update the branch from current `main` and rerun. Do not add insecure compatibility flags to hide the problem.

## Database and migration failures

### Database is not migrated

Run:

```bash
uv run internships db-upgrade
uv run internships stats
```

When the error remains, confirm both commands use the same `INTERNSHIPS_DATABASE_URL`, then run:

```bash
uv run python scripts/check_migrations.py
```

Back up canonical state before repair. Do not delete the database as the first response.

### Migration consistency or timestamp failure

Treat ORM/Alembic drift or `last_seen_at < first_seen_at` as a regression or state-corruption signal.

1. Stop every writer.
2. Preserve the database and sidecars.
3. Run the offline test suite.
4. Run migration consistency checks.
5. Restore a known-good backup when necessary.
6. Report the issue using synthetic or redacted evidence.

Do not rewrite old migrations or timestamps merely to make validation pass.

Schema, migration, backup, and restore procedures are canonical in [Database lifecycle](database.md).

### SQLite lock or concurrent-writer error

The supported model allows one canonical writer.

Typical causes:

- local collection while GitHub Actions is collecting;
- two pipeline containers using the same volume;
- a VPS collector while Actions owns canonical state;
- overlapping collection and maintenance workflows;
- another process holding a long write transaction.

Stop the additional writer and return to the one-writer model.

## README projection failures

### Marker or projection mismatch

The root README must contain exactly one opening and one closing internship marker.

Only when the database contains representative canonical state, run:

```bash
uv run internships render
uv run internships validate
```

The generated block contains:

- open-job metadata;
- latest successful collection time;
- the public website link;
- at most ten jobs.

Do not edit generated rows manually.

When mismatch remains, verify:

- `INTERNSHIPS_README_PATH`;
- `INTERNSHIPS_DATABASE_URL`;
- parent-directory write permission;
- absence of concurrent renderers or formatters;
- that the committed projection was not generated from empty state.

### README replacement fails

Atomic replacement requires a writable parent directory, not only a writable `README.md`.

In Docker, mount the repository directory rather than `README.md` as an individual file.

Container permissions are documented in [Docker](docker.md#volume-permissions).

## Collection failures

### No accepted jobs

Possible causes:

- no current listing passes strict rules;
- title-prefilter rejection;
- missing explicit 2027 evidence;
- unknown technology category;
- unknown or non-European location;
- employer allowlist mismatch;
- changed guest markup;
- source challenge or access block.

Compare found and accepted counts:

```bash
uv run internships searches
```

Identify the rejection stage before changing query limits or classification rules.

### Partial collection

Exit code `2` preserves successful search transactions.

1. Run validation.
2. Identify failed search slugs.
3. Inspect the first sanitized error for each failed search.
4. Rerun only the affected slug when appropriate.

A failed search does not apply absence or closure evidence.

### All searches failed

Exit code `1` usually indicates a shared problem involving:

- authorization;
- network access;
- upstream availability;
- access challenge;
- parser behavior;
- configuration.

Existing canonical state remains valid. Preserve it while diagnosing the shared cause.

### HTTP `429`, timeout, or `5xx`

Retries are finite.

- stop repeated manual runs;
- keep pacing conservative;
- retry one search later;
- determine whether the problem is isolated or shared.

A temporary timeout increase may be appropriate:

```dotenv
INTERNSHIPS_REQUEST_TIMEOUT_SECONDS=40
INTERNSHIPS_CONNECT_TIMEOUT_SECONDS=20
```

Do not increase concurrency to evade throttling.

### HTTP `403` or challenge page

Stop collection.

Do not add:

- login or session reuse;
- cookies;
- browser automation;
- CAPTCHA services;
- proxies;
- fingerprint evasion;
- private endpoints;
- anti-bot bypasses.

Confirm authorization remains valid. Investigate legitimate parser changes only through minimal sanitized fixtures.

## Classification and parsing problems

### A relevant job is excluded

Verify explicit evidence for every required rule:

- internship terminology in the title;
- no configured seniority exclusion;
- recognized technology category;
- explicit 2027 cycle;
- explicit European location.

Description or employment metadata alone cannot convert a non-internship title into an accepted listing.

When authorized, inspect one search without persistence:

```bash
uv run internships search-test <slug>
```

Prefer a focused regression test over weakening a global rule.

### Structured fields show `Not specified`

`Employment type` and `Industries` come from structured source criteria.

Confirm that:

- the deployed collector includes the current parser;
- collection ran after the field was cleared;
- the source contains structured evidence.

Expected structure resembles:

```text
Employment type  → Full-time
Industries       → Software Development
```

When parsing still fails:

1. reproduce only with express authorization;
2. reduce the markup to a minimal sanitized fixture;
3. add a failing parser regression test;
4. update the parser without broad description-keyword fallbacks.

The website should continue showing `Not specified` when structured evidence is absent.

### Guest markup changed

Do not commit full pages.

Create the smallest fixture preserving the changed structure, remove tracking and personal data, use synthetic IDs, and add a regression test.

Parser contribution requirements are defined in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#changing-linkedin-parsing).

## Lifecycle problems

### Job did not close

Search-card absence is intentionally ignored.

Closure requires repeated detail-page `404` or `410` confirmations for every active search association.

Because `max_rechecks` bounds work, a large queue may require several successful runs.

Check:

- `closure_confirmation_runs`;
- active search associations;
- recent successful search runs;
- the bounded recheck limit;
- whether a valid detail page reset confirmations.

The complete lifecycle algorithm is documented in [Database lifecycle](database.md#closure-lifecycle).

### Job closed or reopened unexpectedly

1. Stop writers.
2. Back up SQLite.
3. Inspect recent search runs and provenance.
4. Check the confirmation threshold.
5. Confirm whether another active association existed.
6. Restore known-good state only when evidence indicates corruption.

Do not manually rewrite timestamps or status values without preserving evidence.

## GitHub Actions and deployment

### Collection cache is missing

Cache is not durable backup.

Use, in order of availability:

1. the latest retained `internship-state-<run-id>` artifact;
2. the canonical VPS database;
3. a separately maintained backup.

The README cannot reconstruct canonical state.

### SSH or VPS deployment fails

Verify:

- `VPS_HOST`;
- `VPS_USER`;
- `VPS_SSH_PRIVATE_KEY`;
- `VPS_SSH_KNOWN_HOSTS`;
- `VPS_DOCKER_VOLUME`;
- optional `VPS_SSH_PORT`;
- non-interactive Docker access for the SSH user;
- existence of the Docker volume;
- whether another workflow holds the deployment lock.

Do not disable host-key verification.

### Deployed database is unchanged

Check:

- local and remote checksums;
- the target Docker volume;
- UID/GID and file mode;
- whether atomic rename completed;
- whether stale sidecars remain;
- whether the website reads `/app/data/internships.db`.

Deployment sequencing is documented in [Automation](automation.md#vps-deployment).

### State rebuild was requested unexpectedly

`allow_state_rebuild=true` can discard incompatible cached state and sidecars.

Before allowing it:

- confirm the run was intentional;
- preserve the current artifact or VPS database;
- verify that no compatible cache or backup should be restored instead;
- understand that first-seen history, provenance, closure evidence, and diagnostics will be lost.

Recovery policy is documented in [Automation](automation.md#recovery-and-state-rebuilds).

## Docker failures

Start with:

```bash
docker compose config
docker compose ps
docker compose run --rm internships stats
```

Expected pipeline database URL:

```text
sqlite:////app/data/internships.db
```

### Database appears empty

Confirm every command and service uses the same named volume.

Then run:

```bash
docker compose run --rm internships db-upgrade
docker compose run --rm internships stats
```

A newly created volume is expected to contain no listings.

### Website cannot read SQLite

Check:

- the named volume is mounted;
- the website mount is read-only;
- the database exists;
- UID `10001` has read permission;
- the configured path is `/app/data/internships.db`;
- database and sidecars were not copied inconsistently.

### README rendering fails in Docker

README rendering requires:

- the repository mounted at `/workspace`;
- writable parent-directory permission;
- write permission on `README.md`;
- no competing renderer.

### Compose configuration is wrong

Run:

```bash
docker compose config
```

Verify:

- environment expansion;
- bind-mount source paths;
- the read-only `/app/configs` mount;
- the named database volume;
- image targets and service names;
- `SITE_URL`;
- absence of an unintended fixed production port.

### Dokploy routing fails

Verify:

- the domain targets the `site` service;
- the internal port is `3000`;
- the site container is healthy;
- no conflicting host port is published;
- `SITE_URL` uses the public HTTPS origin.

Container setup and permissions are documented in [Docker and deployment](docker.md).

## Requesting help

A useful issue includes:

- exact command;
- exit code;
- expected behavior;
- actual behavior;
- operating system;
- relevant Python, `uv`, Bun, or Docker version;
- affected search slug;
- first sanitized error;
- minimal offline reproduction.

Do not include:

- `.env` contents;
- credentials or tokens;
- LinkedIn cookies;
- authenticated HTML;
- private paths;
- production databases;
- unredacted GitHub Actions contexts.

Report security-sensitive findings privately through [`SECURITY.md`](../../../SECURITY.md).