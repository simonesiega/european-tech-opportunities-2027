# European Tech Opportunities 2027 Automation Guide

[← Documentation](../README.md) · [Database lifecycle](database.md) · [Docker and deployment](docker.md)

This guide documents the GitHub Actions workflows that validate the project, collect internship and New Grad data, preserve canonical SQLite state, update the README preview, perform bounded maintenance, and optionally deploy validated state to the VPS.

Validation and collection remain separate: normal CI is offline and never contacts LinkedIn.

## Contents

- [Workflow overview](#workflow-overview)
- [Validation workflows](#validation-workflows)
- [Collection authorization](#collection-authorization)
- [Schedule and concurrency](#schedule-and-concurrency)
- [Manual collection inputs](#manual-collection-inputs)
- [Collection workflow](#collection-workflow)
- [Exit-code handling](#exit-code-handling)
- [State continuity and artifacts](#state-continuity-and-artifacts)
- [README update pull requests](#readme-update-pull-requests)
- [VPS deployment](#vps-deployment)
- [Database maintenance](#database-maintenance)
- [Recovery and state rebuilds](#recovery-and-state-rebuilds)
- [Disabling collection](#disabling-collection)
- [Operational checklist](#operational-checklist)

## Workflow overview

| Workflow | Trigger | Responsibility |
|---|---|---|
| `python-ci.yml` | Push to `main`, pull request, manual | Python formatting, linting, typing, offline tests, migrations, and generated-document checks |
| `site-ci.yml` | Push to `main`, pull request, manual | Prettier, ESLint, strict TypeScript, and the Next.js production build |
| `docker-ci.yml` | Push to `main`, pull request, manual | Pipeline and website image builds plus migrated read-only SQLite smoke tests |
| `scrape.yml` | Every six hours, manual | Permission-gated collection, validation, state preservation, optional README pull request, and optional VPS deployment |
| `backfill-posted-at.yml` | Manual | Preview or apply bounded first-seen corrections from current VPS state, preserve artifacts, cache corrected state, and optionally deploy it |
| `clear-database-columns.yml` | Manual | Bounded cleanup of selected optional fields, validation, preservation, and optional deployment |

Workflow files under `.github/workflows/` are the executable source of truth. Update this guide when triggers, inputs, outputs, retention, or deployment behavior changes.

## Validation workflows

The three validation workflows require no LinkedIn access:

- **Python CI** validates the pipeline, CLI, migrations, lifecycle behavior, README projection, and documentation contracts.
- **Site CI** validates formatting, linting, strict TypeScript, and the production Next.js build.
- **Docker CI** validates supported container builds and read-only website access to migrated SQLite state.

Third-party actions should remain pinned to immutable revisions where practical. Runtime and package-manager versions should be explicit rather than resolved through latest-release APIs.

Equivalent local commands are documented in the [development guide](../development/development.md#validation-paths).

## Collection authorization

The collection workflow requires this repository variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

When the variable is missing or has another value, the workflow stops before LinkedIn network access.

> [!IMPORTANT]
> This variable is an operator attestation, not permission. Enable it only after express authorization has been obtained, and disable it immediately when authorization is absent, uncertain, expired, or withdrawn.

Local and Docker interlocks are documented in [Configuration](../getting-started/configuration.md#authorization-interlocks). The complete source-access boundary is defined in [`SECURITY.md`](../../../SECURITY.md).

## Schedule and concurrency

The collection workflow uses:

```yaml
schedule:
  - cron: "0 */6 * * *"

concurrency:
  group: internship-collection
  cancel-in-progress: false
```

Nominal scheduled times are:

- 00:00 UTC;
- 06:00 UTC;
- 12:00 UTC;
- 18:00 UTC.

GitHub Actions may start scheduled jobs later than the configured time.

Collection and database-maintenance workflows share `internship-collection`. This prevents overlapping canonical writers while allowing the read-only website to continue serving requests.

## Manual collection inputs

Run the workflow from:

**Actions → Collect internships → Run workflow**

| Input | Default | Effect |
|---|---:|---|
| `open_pull_request` | `false` | Create or update the generated README-preview pull request |
| `allow_state_rebuild` | `false` | Permit fresh-state recovery after available sources are reviewed |
| `deploy_to_vps` | `false` | Atomically deploy the validated SQLite database to the configured VPS volume |

VPS deployment is allowed only from `main`.

Enable only the outputs needed for the run. A normal manual collection should not request a rebuild or deployment without a specific operational reason.

## Collection workflow

<div align="center">
<pre>
authorization check
↓
checkout + pinned runtime setup
↓
optional verified SSH setup
↓
restore compatible SQLite cache
↓
optional VPS bootstrap when cache is absent
↓
database migration
↓
bounded collection + classification
↓
isolated transactional persistence
↓
README projection + validation
↓
SQLite WAL checkpoint
↓
cache + retained artifact
↓
optional README pull request
↓
optional atomic VPS deployment
</pre>
</div>

The workflow validates resulting state before publication or deployment.

A partial collection preserves successful search transactions. Failed searches record diagnostics but do not apply absence, unavailability, or closure evidence.

## Exit-code handling

| CLI exit code | Workflow behavior |
|---:|---|
| `0` | Continue after complete success |
| `1` | Stop because every selected search failed |
| `2` | Continue after partial success; successful search transactions remain valid |
| `3` | Stop because schema or state preconditions failed |

Validation must pass after complete or partial success.

Command-level semantics are documented in the [CLI reference](../user-guide/cli.md#exit-codes).

## State continuity and artifacts

The workflow restores the newest compatible cache using:

```text
opportunities-db-
```

New cache keys are run-specific:

```text
opportunities-db-<run-id>
```

A cache supports continuity and performance, but is not a durable backup.

After checkpointing SQLite write-ahead state, the workflow uploads an artifact containing:

- `data/opportunities.db`;
- `README.md`.

Artifact name:

```text
opportunities-state-<run-id>
```

The configured retention period is 30 days.

When VPS deployment is requested and no compatible cache exists, the workflow can bootstrap from the current VPS database after verifying SQLite integrity.

Canonical backup, sidecar, migration, and restoration rules belong to the [database lifecycle guide](database.md).

## README update pull requests

When `open_pull_request=true`, the workflow updates the reusable branch:

```text
automated/readme-update
```

Only `README.md` is committed. SQLite state is never committed.

The generated block remains bounded to ten recently posted open jobs, regardless of the size of canonical state.

Review the pull request normally before merging. Do not edit generated rows manually; change the renderer or canonical state instead.

## VPS deployment

### Required secrets

| Secret | Purpose |
|---|---|
| `VPS_HOST` | Deployment host |
| `VPS_USER` | Dedicated SSH user |
| `VPS_SSH_PRIVATE_KEY` | Ed25519 private key |
| `VPS_SSH_KNOWN_HOSTS` | Pre-verified SSH host-key entry |

### Repository variables

| Variable | Required | Default or example |
|---|---:|---|
| `VPS_DOCKER_VOLUME` | Yes | `project_internships-data` |
| `VPS_SSH_PORT` | No | `22` |

### Deployment sequence

The workflow:

1. uploads the validated database to a run-specific remote temporary path;
2. compares local and remote SHA-256 checksums;
3. acquires a VPS `flock`;
4. preserves the current canonical file as `opportunities.db.previous`;
5. copies the upload to a temporary file inside the Docker volume;
6. applies UID/GID `10001:10001` and mode `0640`;
7. removes stale SQLite sidecars while no database connection is writing;
8. atomically renames the temporary database into place;
9. verifies the final checksum;
10. removes the remote upload.

The website opens a new read-only SQLite connection on the next request and observes the deployed database without an application restart or mutation endpoint.

Compose topology, volume permissions, Dokploy routing, and container diagnostics belong to the [Docker and deployment guide](docker.md).

## Database maintenance

### Posting-date backfill

Use **Actions → Backfill LinkedIn posting dates → Run workflow** after the backfill code is merged to `main`. The workflow always downloads current canonical state directly from the VPS rather than preferring an Actions cache.

Run `mode: dry-run` first. Review the logs and download the `opportunities-before-posting-backfill-<run-id>` artifact. Dry-run mode never saves a cache or deploys state.

Then run `mode: apply` from `main`. Keep `limit` at `250` for the current database, use `offset` only for additional deterministic batches, and enable `deploy_to_vps` only after reviewing the preview. Apply mode:

1. migrates the isolated working copy;
2. runs `internships backfill-posted-at`;
3. validates the database and generated README;
4. checkpoints and integrity-checks SQLite;
5. retains before-and-after artifacts;
6. saves corrected state under the normal `opportunities-db-` cache prefix;
7. optionally uses the same checksum, lock, previous-file backup, and atomic replacement contract as collection deployment.

After a successful apply, manually rerun `scrape.yml`. Request VPS deployment on that collection run if the backfill workflow did not already deploy. The collection workflow restores the corrected cache, performs complete collection, validates the result, and refreshes normal canonical continuity.

### Optional-field cleanup

The manual `clear-database-columns.yml` workflow can clear selected optional fields:

- `Industries`;
- `Employment type`;
- `Start date`.

The workflow:

1. runs only from `main`;
2. requires at least one selected field;
3. retrieves canonical VPS state;
4. preserves before-and-after artifacts;
5. checks SQLite integrity;
6. saves the validated result to workflow cache;
7. optionally deploys the cleaned database.

A later collection repopulates a cleared field only when acceptable source evidence is available.

Use this workflow for bounded data repair, not schema evolution. Schema changes require Alembic migrations and follow [Database lifecycle](database.md#migrations).

## Recovery and state rebuilds

Normal workflow migrations use:

```bash
uv run internships db-upgrade
```

A migration failure stops the workflow.

Setting `allow_state_rebuild=true` permits incompatible cached state and sidecars to be discarded before creating a new database. A rebuild loses:

- original first-seen history;
- search provenance;
- closure confirmations;
- run diagnostics.

Treat rebuilding as emergency recovery, never routine migration.

Before enabling it, review the newest compatible cache, retained artifacts, the VPS canonical file, and separately maintained backups. Follow [Database lifecycle](database.md#restore) and [Troubleshooting](troubleshooting.md#github-actions-and-deployment).

## Disabling collection

Set the repository variable to `false` or remove it:

```text
LINKEDIN_CRAWL_AUTHORIZED
```

Scheduled and manual collection runs then stop at the authorization gate without contacting LinkedIn.

Do not bypass the gate by hardcoding an enabled value in workflow or application code.

## Operational checklist

Before changing or manually running automation, confirm:

- [ ] Offline validation CI remains separate from collection.
- [ ] LinkedIn authorization is current and recorded outside the repository.
- [ ] Collection and maintenance retain the shared one-writer concurrency group.
- [ ] Third-party actions remain pinned where practical.
- [ ] Logs contain no secrets, GitHub contexts, HTML bodies, `.env` values, or database rows.
- [ ] SQLite is checkpointed and validated before cache, artifact, or deployment publication.
- [ ] State-rebuild operations have a reviewed recovery source.
- [ ] VPS host keys are pre-verified.
- [ ] Deployment remains checksum-verified, locked, and atomic.
- [ ] SQLite state is never committed to Git.
- [ ] Artifact visibility, environment protection, and SSH access follow least privilege.