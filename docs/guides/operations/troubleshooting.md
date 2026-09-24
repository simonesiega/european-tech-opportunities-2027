# European Tech Opportunities 2027 Troubleshooting Guide

[← Documentation hub](../../README.md) · [CLI reference](../user-guide/cli.md) · [Database lifecycle](database.md) · [Automation](automation.md) · [Docker and deployment](docker.md) · [Security policy](../../../SECURITY.md)

This is the canonical troubleshooting guide for the project. Start with the command’s exit code and first sanitized error, and preserve state before making changes.

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
uv run opportunities --help
uv run opportunities searches
uv run opportunities stats
```

Also verify:

- the current Git branch and commit;
- the working directory;
- whether `.env` or a settings YAML is being loaded;
- `OPPORTUNITIES_DATABASE_URL`;
- `OPPORTUNITIES_PUBLIC_EXPORT_DIR` when downloads are affected;
- process-environment overrides;
- whether execution is local, Docker, or GitHub Actions;
- the exact command and exit code.

Never paste a complete environment file, production database, authenticated HTML, secret, or unredacted workflow context into an issue.

## Exit codes

| Code | Meaning | First action |
|---:|---|---|
| `0` | Success | No recovery action required |
| `1` | Complete collection failure or validation mismatch | Preserve state and inspect per-search or projection output |
| `2` | Partial collection or availability audit, or rejected configuration/command input | Preserve successful work and inspect the command-specific error |
| `3` | Database missing tables or not at migration head | Run `db-upgrade` against the same database URL |

Exit code `2` is intentionally overloaded by command context: collection uses it for partial success, the availability audit uses it when one or more checks are inconclusive, and configuration or selection errors also use it for rejected input.

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
uv run opportunities searches
uv run pytest tests/unit/test_config.py
```

For a specific settings file:

```bash
uv run opportunities --settings configs/settings.local.yml stats
```

Correct the first validation error before investigating later messages.

Configuration precedence, variables, and limits are defined in [Configuration](../getting-started/configuration.md).

### LinkedIn collection is disabled

This is the safe default.

Local or Docker collection requires:

```text
OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true
```

GitHub Actions collection and availability auditing require:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

Neither value grants permission.

When the GitHub variable is missing or different, collection and availability workflows stop before LinkedIn network access. Leave the interlocks disabled unless express authorization exists.

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
uv run opportunities db-upgrade
uv run opportunities stats
```

When the error remains, confirm both commands use the same `OPPORTUNITIES_DATABASE_URL`, then run:

```bash
uv run python scripts/check_migrations.py
```

Back up the database before repair. Do not delete it as the first response.

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

The supported model allows one writer.

Typical causes:

- local collection while GitHub Actions is collecting;
- two pipeline containers using the same volume;
- a VPS collector while Actions owns canonical state;
- overlapping collection and maintenance workflows;
- another process holding a long write transaction.

Stop the additional writer, preserve the current database and sidecars, and return to the one-writer model before retrying.

## README projection failures

### Marker or projection mismatch

The root README must contain exactly one opening and one closing marker for each generated region: opportunity counts and opportunity previews.

Only when the database contains representative state, run:

```bash
uv run opportunities render
uv run opportunities validate
```

The generated regions contain:

- open-job metadata;
- latest successful collection time;
- the public website link;
- at most five internships and five New Grad opportunities.

Do not edit generated counts, timestamps, or rows manually; fix the database state or renderer instead.

When mismatch remains, verify:

- `OPPORTUNITIES_README_PATH`;
- `OPPORTUNITIES_DATABASE_URL`;
- parent-directory write permission;
- absence of concurrent renderers or formatters;
- that the committed projection was not generated from empty state.

### Public export is missing or stale

Regenerate only the sanitized downloads from migrated state:

```bash
uv run opportunities export-public
uv run opportunities validate
```

Verify `OPPORTUNITIES_PUBLIC_EXPORT_DIR`, directory write permission for the pipeline, read permission for the website, and that deployment uploaded both files with matching checksums. Do not generate exports in the website or expose arbitrary filesystem paths as a fallback.

The expected files are `open-opportunities.csv` and `open-opportunities.json`. They contain no lifecycle or operational state and can be safely regenerated from SQLite.

### README replacement fails

Atomic replacement requires a writable parent directory, not only a writable `README.md`.

In Docker, mount the repository directory rather than `README.md` as an individual file.

Container permissions are documented in [Docker](docker.md#volume-permissions).

### Coverage metrics are stale

Python CI generates `quality-reports/coverage.json` from the current test run and then verifies that the committed README coverage table matches it.

Regenerate the report and coverage table from the repository root:

```bash
make coverage
```

When Make is unavailable, run the complete coverage command documented in [Development](../development/development.md#python-and-documentation), including the JSON report, then run:

```bash
uv run python scripts/coverage_docs.py
```

Use `uv run python scripts/coverage_docs.py --check` only after generating a current coverage report. Check mode verifies committed content without rewriting it. Never edit the coverage markers or table manually.

## Collection failures

### No accepted jobs

Possible causes:

- no current listing passes strict rules;
- title-prefilter rejection;
- a conflicting cycle year, or a missing cycle combined with ineligible posting-date evidence;
- unknown technology category;
- unknown or non-European location;
- employer allowlist mismatch;
- changed guest markup;
- source challenge or access block.

Compare found and accepted counts:

```bash
uv run opportunities searches
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

Existing state remains valid. Preserve it while diagnosing the shared cause.

### Timeout or HTTP `5xx`

Retries are finite.

- stop repeated manual runs;
- keep pacing conservative;
- retry one search later when the upstream failure is temporary;
- determine whether the problem is isolated or shared.

A temporary timeout increase may be appropriate:

```dotenv
OPPORTUNITIES_REQUEST_TIMEOUT_SECONDS=40
OPPORTUNITIES_CONNECT_TIMEOUT_SECONDS=20
```

Do not increase concurrency to evade throttling.

### Redirect, HTTP `401`, `403`, `429`, or challenge page

Stop collection. A redirect, HTTP `401`, `403`, or `429` blocks further requests through the same fetcher; requests already in flight may finish. Review access before starting another run.

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

- internship or New Grad terminology in the title;
- no configured seniority exclusion;
- recognized technology category;
- explicit 2027 cycle, or no conflicting cycle year with posting-date evidence on or after May 1, 2026 serving as the yearless fallback;
- explicit European location.

Description or source employment metadata alone cannot convert a title without Internship or New Grad evidence into an accepted listing.

When authorized, inspect one search without persistence:

```bash
uv run opportunities search-test <slug>
```

Prefer a focused regression test over weakening a global rule.

### Industries shows `Not specified`

`Industries` comes from structured source criteria. Employment type is instead required and classified from the title as Internship or New Grad.

Confirm that:

- the deployed collector includes the current parser;
- collection ran after the field was cleared;
- the source contains structured industries evidence.

Expected structure resembles:

```text
Industries → Software Development
```

When industries parsing still fails:

1. reproduce only with express authorization;
2. reduce the markup to a minimal sanitized fixture;
3. add a failing parser regression test;
4. update the parser without broad description-keyword fallbacks.

The website should continue showing `Not specified` for industries when structured evidence is absent. A missing or unsupported employment type excludes the listing instead of publishing an unspecified value.

### Guest markup changed

Do not commit full pages.

Create the smallest fixture preserving the changed structure, remove tracking and personal data, use synthetic IDs, and add a regression test.

Parser contribution requirements are defined in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#changing-linkedin-parsing).

## Lifecycle problems

### Job did not close

Search-card absence is intentionally ignored.

During collection, closure requires repeated detail-page `404` or `410` confirmations for every active search association. Separately, the daily full-state audit permanently deletes a row after an explicit `404` or `410` from its public listing or guest detail request, or after a scoped “No longer accepting applications” alert.

Because `max_rechecks` bounds collection work, a large per-search queue may require several successful runs.

Check:

- `closure_confirmation_runs`;
- active search associations;
- recent successful search runs;
- the bounded recheck limit;
- whether a valid detail page reset confirmations;
- whether the latest full-state audit was complete or reported the row as inconclusive.

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

### Canonical-state job cannot access its environment

Confirm that:

- the workflow was dispatched from `main`;
- the environment is named exactly `canonical-state`;
- its deployment-branch rule allows `main` and no other branch or tag;
- unattended scheduled runs are not waiting for a required reviewer;
- all five environment secrets are present: `VPS_HOST`, `VPS_USER`, `VPS_SSH_PRIVATE_KEY`, `VPS_BACKUP_SSH_PRIVATE_KEY`, and `VPS_SSH_KNOWN_HOSTS`.

Do not copy these secrets back to repository scope to bypass an environment-policy failure. Correct the environment and branch policy. The final deployment separately uses the `production` environment and should remain approval-gated when practical.

### Docker image pull or Trivy scan fails

First distinguish infrastructure failure from a vulnerability finding:

- Docker exit code `125`, registry authentication errors, connection resets, and image or vulnerability-database download errors indicate that the scan could not run.
- A completed Trivy report followed by exit code `1` indicates at least one fixable high or critical vulnerability and must be investigated.

The workflow retries the immutable digest-pinned Trivy image pull three times with bounded delays. After an exhausted transient pull or database-download failure, wait for the registry to recover and rerun the failed workflow. If failures persist, inspect Docker Hub and Trivy database registry availability without printing credentials.

Do not remove digest pins, disable Trivy, broaden vulnerability exclusions, or change the scan exit code to turn an infrastructure or security failure into success.

### Canonical snapshot is missing

Canonical SQLite is never stored in GitHub Actions cache or artifacts. When restricted VPS snapshot storage is healthy, the workflow downloads `latest.json`, verifies its timestamped SQLite file, and uses that exact state.

During initial rollout, if `latest.json` is absent and the snapshot directory is empty, the workflow may stream a consistent SQLite backup from the reviewed live VPS database after independent integrity, foreign-key, required-table, and Alembic-revision checks. It never treats an unreferenced local database as a bootstrap source. If timestamped snapshots exist but the pointer is missing, automation stops so the pointer can be recovered instead of starting an unrelated history.

The README and sanitized projection artifacts cannot reconstruct lifecycle state.

### VPS snapshot restore or publication fails

Do not bypass host-key, manifest, checksum, or restore checks to finish a collection run.

Check, without printing credentials:

- the main-only `canonical-state` environment and its secrets;
- `VPS_HOST`, `VPS_BACKUP_USER`, and `VPS_SSH_PORT`;
- the `VPS_BACKUP_SSH_PRIVATE_KEY` secret and verified `VPS_SSH_KNOWN_HOSTS` entry;
- SFTP-only account access to `/state`;
- absence of shell, sudo, forwarding, `opportunities-site` membership, and live-database access;
- database size, SHA-256, schema revision, and collection timestamp against the manifest;
- SQLite `integrity_check`, `foreign_key_check`, and required tables.

If restoration reports that local state differs from the latest manifest or that restore/bootstrap staging already exists, preserve those files and any sidecars for investigation; do not remove them just to make a retry pass. A fresh protected job normally starts with no local database.

A publication failure before latest-pointer promotion leaves the prior snapshot authoritative. Preserve failed-run logs and inspect newly uploaded timestamped files; do not repoint `latest.json` manually until the pair passes:

```bash
uv run python scripts/canonical_snapshot.py verify \
  --database /safe/recovery/opportunities.db \
  --manifest /safe/recovery/manifest.json
```

For recovery, walk the manifest `previous_snapshot` references newest to oldest. A manifest or checksum failure is a stop condition, not permission to use unverified bytes. Restricted account setup and required settings are documented in [Automation](automation.md#restricted-vps-snapshot-configuration).

### SSH or VPS deployment fails

Verify:

- that the `production` environment approved the deployment and allows only `main`;
- `VPS_HOST`;
- `VPS_USER`;
- `VPS_SSH_PRIVATE_KEY`;
- `VPS_BACKUP_SSH_PRIVATE_KEY` for the restore/publication phase;
- `VPS_SSH_KNOWN_HOSTS`;
- optional `VPS_SSH_PORT`;
- access to `/srv/european-tech-opportunities-2027/data` for the restricted SSH user;
- whether another workflow holds the deployment lock;
- whether the local working database has `-wal`, `-shm`, or `-journal` sidecars; checkpoint and close it before retrying, without discarding uncheckpointed data;
- whether `data/current` is invalid, the run ID has already been published, or a partial upload failed checksum verification. Inspect the pointer and immutable releases under the deployment lock before retrying; never remove an active release.

Do not disable host-key verification.

### Deployed database is unchanged

First distinguish the pipeline's working file from the versioned release served by the website. Check:

- that deployment-only automation completed and its local and remote payload checksums agree;
- that `data/current` is a valid relative symlink to the intended `data/releases/<run-id>-<attempt>` and `(cd data/current && sha256sum -c checksums.sha256)` passes;
- that the site has `OPPORTUNITIES_RELEASE_ROOT=/app/data` **on every instance** after the coordinated rollout; without it, the site continues to read the stale legacy fixed paths;
- that the site group can traverse `data/releases/` and read the selected database and both exports;
- that old site instances and cached responses are not being mistaken for the new release. A page and a later download can span a cutover.

A missing or invalid `current` is a stop condition, not a reason to repoint the site to legacy state. Deployment sequencing and rollback are documented in [Automation](automation.md#vps-deployment).

### Migration or canonical-state validation fails

Collection workflows deliberately provide no state-rebuild input. They stop rather than deleting an incompatible restored database or its sidecars.

1. Preserve the failed state and stop additional writers.
2. Review verified durable manifests and snapshots first, then retained versioned releases under `data/releases/`; a legacy `opportunities.db.previous` is not current state after rollout. Sanitized projection artifacts cannot restore state.
3. Verify the selected snapshot’s checksum, schema revision, integrity, and foreign keys.
4. Restore it with the procedure in [Database lifecycle](database.md#restore).

Do not initialize an empty database merely to make automation pass. An intentional manual rebuild loses first-seen history, provenance, closure evidence, and diagnostics. Recovery policy is documented in [Automation](automation.md#recovery-and-migration-failures).

### Nightly pull request does not auto-merge

Confirm that:

- repository auto-merge is enabled and GitHub Actions may create pull requests;
- the README mutation job has `actions: write`, `contents: write`, and `pull-requests: write`;
- branch protection requires `ruff`, `python`, `site`, `docker`, `Analyze (Python)`, `Analyze (TypeScript)`, and `Gitleaks secret scan`;
- the pull request targets `main`;
- its head branch is `automated/nightly-full-update`;
- its title is `data: nightly availability and scrape update`;
- `README.md` is the only changed file;
- `workflow_dispatch` runs exist for all five validation workflows on the automation branch head SHA;
- the README mutation job identified those run IDs and waited for each successful conclusion before requesting auto-merge.

A branch push made by `GITHUB_TOKEN` does not reliably trigger ordinary push or pull-request recursion. The README mutation workflow compensates by explicitly dispatching all five validation workflows after its exact-scope check, then keeping the branch alive until they finish. If those runs are missing, inspect that job for workflow-dispatch permission or policy failures; do not bypass required checks.

A validation run that fails instantly with zero jobs and no logs usually means the automation branch was merged and deleted before GitHub finished creating jobs. The explicit dispatch wait prevents that race without weakening validation. The workflow also refuses validation dispatch and auto-merge when any scope check differs. Do not weaken either safeguard; restore the fixed automation branch to the expected README-only diff instead.

## Docker failures

Start with:

```bash
docker compose config
docker compose ps
docker compose run --rm opportunities stats
```

Expected pipeline database URL:

```text
sqlite:////app/data/opportunities.db
```

### Database appears empty

Confirm both services mount `/srv/european-tech-opportunities-2027/data`. In versioned production mode the pipeline's working file and the site's `current` release are intentionally different; compare the site's selected release with the latest reviewed deployment, not with the working file.

For an intentionally new **local development** directory only, initialize and inspect it explicitly:

```bash
docker compose run --rm opportunities db-upgrade
docker compose run --rm opportunities stats
```

A fresh local directory intentionally contains no listings. In production, restore and verify canonical state before migration; website startup never creates or migrates it automatically.

### Website cannot read SQLite

Check:

- the host state directory is mounted;
- the website bind mount is read-only;
- the database and both public export files exist;
- UID/GID `10001:10001` has read access through the configured host ownership or group mapping;
- in versioned mode, `OPPORTUNITIES_RELEASE_ROOT=/app/data` and a valid `current` symlink target under `/app/data/releases/` are present; in legacy/local mode only, the configured database path is `/app/data/opportunities.db`;
- in versioned mode, the selected release was produced as a cold, sidecar-free snapshot rather than copied inconsistently from a live WAL database; in legacy mode, preserve any required sidecars and permissions.

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
- the `/srv/european-tech-opportunities-2027/data` database bind mount;
- image targets and service names;
- `SITE_URL` and, after rollout, `OPPORTUNITIES_RELEASE_ROOT=/app/data` for **every** site instance;
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

Before opening an issue, reduce the problem to the smallest safe reproduction you can. A useful report includes:

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
