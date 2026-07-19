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
| `nightly.yml` | 03:00 UTC daily | Availability audit followed by scrape, with one combined review pull request |
| `scrape.yml` | Manual | Scrape-only update with its own review pull request; reviewed deployment |
| `check-availability.yml` | Manual | Full-state availability-only audit with its own review pull request |
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

The nightly, scrape-only, and availability-only workflows require this repository variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

When the variable is missing or has another value, the workflow stops before LinkedIn network access.

> [!IMPORTANT]
> This variable is an operator attestation, not permission. Enable it only after express authorization has been obtained, and disable it immediately when authorization is absent, uncertain, expired, or withdrawn.

Local and Docker interlocks are documented in [Configuration](../getting-started/configuration.md#authorization-interlocks). The complete source-access boundary is defined in [`SECURITY.md`](../../../SECURITY.md).

## Schedule and concurrency

The nightly full update runs once per day:

```yaml
schedule:
  - cron: "0 3 * * *"

concurrency:
  group: internship-collection
  cancel-in-progress: false
```

The nominal scheduled time is 03:00 UTC. It completes the availability audit before starting the scrape. GitHub Actions may start scheduled jobs later than the configured time.

Collection and database-maintenance workflows share `internship-collection`. This prevents overlapping canonical writers while allowing the read-only website to continue serving requests.

## Manual collection inputs

Two workflows can be run independently from the Actions tab:

- **Check job availability** checks all existing rows and opens an availability-only pull request.
- **Scrape jobs only** runs only the scrape and opens a scrape-only pull request.

The scrape workflow inputs are:

| Input | Default | Effect |
|---|---:|---|
| `open_pull_request` | `true` | Create or update the scrape-only README pull request |
| `allow_state_rebuild` | `false` | Permit fresh-state recovery after available sources are reviewed |
| `deploy_to_vps` | `false` | Skip collection and atomically deploy reviewed cached SQLite state that validates against `main` |

The availability workflow exposes only the guarded `allow_state_rebuild` recovery input and always proposes changes in its own pull request. VPS deployment is allowed only from `main` when a manual scrape-workflow run explicitly sets `deploy_to_vps=true`; scheduled runs stop after preserving state and opening the combined review pull request.

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
check every stored job's LinkedIn detail page
↓
delete explicit 404/410 rows and refresh README
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

The scheduled workflow validates resulting state only after both ordered phases complete, then opens one combined pull request. A manual invocation of either workflow runs and proposes only that workflow's phase.

A partial collection preserves successful search transactions. Failed searches record diagnostics but do not apply absence, unavailability, or closure evidence.

The availability pass visits the LinkedIn detail page for every stored job. A valid HTML response keeps or reopens the row, while an explicit HTTP `404` or `410` deletes it and its search provenance. Authentication failures, rate limits, server errors, malformed responses, and transport failures are inconclusive: the workflow reports them but preserves those rows. All requests remain behind the LinkedIn authorization interlock and existing pacing limits.

## Exit-code handling

| CLI exit code | Workflow behavior |
|---:|---|
| `0` | Continue after complete success |
| `1` | Stop because every selected search failed |
| `2` | Continue after a partial scrape or availability audit; confirmed changes remain valid and inconclusive rows are preserved |
| `3` | Stop because schema or state preconditions failed |

Validation must pass after complete or partial success.

Command-level semantics are documented in the [CLI reference](../user-guide/cli.md#exit-codes).

## State continuity and artifacts

Each state-writing workflow restores the newest compatible cache using:

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

Artifact names are:

```text
opportunities-nightly-state-<run-id>
opportunities-state-<run-id>
opportunities-availability-state-<run-id>
```

The configured retention period is 30 days.

When VPS deployment is requested and no compatible cache exists, the workflow can bootstrap from the current VPS database after verifying SQLite integrity.

Canonical backup, sidecar, migration, and restoration rules belong to the [database lifecycle guide](database.md).

## README update pull requests

Each path uses a separate reusable review branch:

```text
automated/nightly-full-update  # availability followed by scrape
automated/availability-update  # manually requested availability only
automated/scrape-update        # manually requested scrape only
```

Only `README.md` is committed. SQLite state is never committed.

The generated block remains bounded to ten recently posted open jobs, regardless of the size of canonical state.

Review and merge the pull request manually. Scheduled runs do not deploy to the VPS. After accepting the pull request, start a manual run from `main` with `deploy_to_vps=true` to publish the reviewed canonical state. Deployment-mode runs skip collection and availability requests, then require the merged README to validate exactly against restored cached SQLite before deployment. The pull request contains the human-readable README projection; SQLite remains in the protected cache/artifact/deployment path and is never committed. Do not edit generated rows manually; change the renderer or canonical state instead.

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

After a review pull request is merged, a deployment-mode run restores its cached database, skips all new collection, and validates it against `main`. It then:

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