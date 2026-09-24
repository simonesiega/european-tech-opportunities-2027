# European Tech Opportunities 2027 Automation Guide

[← Documentation hub](../../README.md) · [Database lifecycle](database.md) · [Docker and deployment](docker.md) · [Troubleshooting](troubleshooting.md) · [Security policy](../../../SECURITY.md)

This is the canonical automation guide for the project. It documents the GitHub Actions workflows that validate the project, collect Internship and New Grad data, preserve canonical SQLite state, update the README preview, and deploy reviewed state to the VPS.

Validation and collection remain separate: normal CI never contacts LinkedIn.

## Contents

- [Workflow overview](#workflow-overview)
- [Validation workflows](#validation-workflows)
- [Reusable automation boundaries](#reusable-automation-boundaries)
- [Workflow permissions](#workflow-permissions)
- [Protected environments and repository settings](#protected-environments-and-repository-settings)
- [First production activation](#first-production-activation)
- [Collection authorization](#collection-authorization)
- [Schedule and concurrency](#schedule-and-concurrency)
- [Manual collection inputs](#manual-collection-inputs)
- [Manual job addition](#manual-job-addition)
- [Collection and deployment flow](#collection-and-deployment-flow)
- [Exit-code handling](#exit-code-handling)
- [State continuity and artifacts](#state-continuity-and-artifacts)
- [Restricted VPS snapshot configuration](#restricted-vps-snapshot-configuration)
- [README update pull requests](#readme-update-pull-requests)
- [Post-nightly production runbook](#post-nightly-production-runbook)
- [VPS deployment](#vps-deployment)
- [Coordinated first rollout and rollback](#coordinated-first-rollout-and-rollback)
- [Recovery and migration failures](#recovery-and-migration-failures)
- [Disabling collection](#disabling-collection)
- [Operational checklist](#operational-checklist)

## Workflow overview

| Workflow | Trigger | Responsibility |
|---|---|---|
| `python-ci.yml` | Push to `main`, pull request, manual | Python formatting, linting, typing, thresholded combined statement-and-branch coverage, parsing/classification benchmarks, migrations, and generated-document checks |
| `site-ci.yml` | Push to `main`, pull request, manual | Prettier, ESLint, strict TypeScript, the Next.js production build, unit tests, browser checks, and axe-core accessibility scans against synthetic SQLite state |
| `codeql.yml` | Push to `main`, pull request, Monday 05:31 UTC, manual | CodeQL `security-extended` analysis for Python and TypeScript, with findings uploaded to GitHub code scanning |
| `docker-ci.yml` | Push to `main`, pull request, manual | Action and Dockerfile linting, image builds and vulnerability scans, plus migrated read-only SQLite and production-header smoke tests |
| `canonical-state-drill.yml` | Manual | Recover, validate, republish, and round-trip a canonical snapshot without source access; its explicit adoption mode proposes the first public-state review seal without publishing a snapshot |
| `nightly.yml` | 04:23 UTC daily | Availability audit followed by scrape, with one narrowly scoped auto-merge pull request |
| `scrape.yml` | Manual | Scrape-only update with its own review pull request, or deployment-only publication of reviewed state from `main` |
| `check-availability.yml` | Manual | Full-state availability-only audit with its own review pull request |
| `add-job.yml` | Manual | Add 1–10 maintainer-reviewed listings to durable canonical state without source access, then open one README-only review pull request |

Two `workflow_call`-only files are implementation building blocks, not operator entry points: `reusable-process-state.yml` owns canonical restore, migration, selected source phases, validation, snapshot publication, optional protected deployment, and sanitized artifacts; `reusable-readme-pr.yml` owns the narrowly scoped README branch and pull-request mutation. The pinned Python/uv setup is shared through `.github/actions/setup-python/action.yml`.

Workflow files under `.github/workflows/` are the executable source of truth. Update this guide when triggers, inputs, outputs, retention, permissions, or deployment behavior changes.

## Validation workflows

The four validation workflows require no LinkedIn access:

- **Python CI** validates the pipeline, CLI, migrations, lifecycle behavior, README projection, and documentation contracts; it publishes critical-path coverage and benchmark reports for 30 days. Current measured values are summarized in the root [Python quality baseline](../../../README.md#python-quality-baseline).
- **Site CI** uses the documented Node.js and Bun versions to validate formatting, linting, strict TypeScript, the production Next.js build, unit tests, Playwright behavior, and axe-core accessibility checks against synthetic SQLite state.
- **CodeQL** runs GitHub's extended security query suite independently for Python and TypeScript on pushes, pull requests, manual runs, and every Monday at 05:31 UTC. It uses interpreted-language no-build extraction and uploads results only to GitHub code scanning.
- **Docker CI** runs `actionlint`, audits every workflow and composite action with blocking zizmor, and runs Hadolint. It builds both production targets, uses Trivy to reject high or critical vulnerabilities for which a fix is available, and verifies migration, read-only website access, public-export delivery, Content Security Policy, and HTTP Strict Transport Security. Unfixed findings are excluded from the image-vulnerability gate.

Validation jobs have explicit timeouts, cancel superseded runs only on the same workflow/ref, and checkout without persisted Git credentials. Third-party actions and CI tool images are pinned to immutable revisions where practical and should remain pinned. Runtime and package-manager versions should stay explicit rather than being resolved through latest-release APIs.

Equivalent local commands are documented in the [development guide](../development/development.md#validation-paths).

## Reusable automation boundaries

The operator-facing workflows remain small mode selectors:

- `nightly.yml` selects availability followed by scrape;
- `check-availability.yml` selects availability only;
- collection mode in `scrape.yml` selects scrape only;
- deployment mode in `scrape.yml` selects projection regeneration followed by deployment;
- `add-job.yml` selects one atomic manual batch upsert followed by full projection regeneration;
- `canonical-state-drill.yml` normally selects restore, export, validation, and round-trip publication without source access; its seal-adoption mode reads a verified snapshot and proposes a README-only baseline without durable publication.

All canonical-state modes call `reusable-process-state.yml`. This keeps restore/bootstrap, migration, CLI exit-code handling, validation, checkpoint, durable publication, and sanitized-artifact ordering identical, except that seal adoption deliberately skips durable publication. Deployment mode selects the `production` environment and runs the final locked deployment in that same protected job, so canonical SQLite never crosses jobs through a GitHub cache or artifact. `scripts/restore_canonical_state.sh` encapsulates restricted-snapshot reconciliation and the verified live-database fallback. `scripts/canonical_state_store.sh` owns immutable SFTP snapshot restore/publication. `scripts/deploy_canonical_state.sh` and `scripts/activate_canonical_release.sh` own locked, checksum-verified versioned deployment with a single atomic release-pointer cutover.

The wrappers, rather than the reusable processor, decide which source phase runs, which protected environment applies, and whether README mutation or deployment is needed. Canonical processing never pushes Git branches, and the README mutation workflow never receives VPS credentials or canonical SQLite state.

## Workflow permissions

Workflow defaults are read-only or empty. Permissions are elevated at job boundaries only:

| Job class | Token permissions | Credentials and data |
|---|---|---|
| Validation and canonical processing | `contents: read` | Source checkout; `canonical-state` jobs receive restore/publication credentials only |
| Protected deployment processing | `contents: read` | `production` job restores, validates, snapshots, and deploys without a database handoff artifact |
| README pull-request mutation | `actions: write`, `contents: write`, `pull-requests: write` | One-day `README.md` handoff only; no VPS credentials or SQLite artifact; explicitly dispatches validation on the generated commit |
| CodeQL analysis | `actions: read`, `contents: read`, `security-events: write` | Security-analysis upload only |

GitHub cache entries on the default branch are readable by pull-request workflows, including forks, and public-repository artifacts are available to anyone with repository read access. Canonical SQLite therefore never enters Actions cache or artifacts. Thirty-day artifacts contain only the already-public README and sanitized CSV/JSON projections; the one-day cross-job artifact contains only `README.md`. Checkout never persists Git credentials.

GitHub intentionally suppresses ordinary workflow recursion after a branch push made with `GITHUB_TOKEN`. After verifying that the automation pull request targets `main`, uses a same-repository fixed head branch and the expected title, and changes only `README.md`, the mutation workflow therefore dispatches `python-ci.yml`, `site-ci.yml`, `docker-ci.yml`, and `codeql.yml` explicitly on the generated head commit. It identifies those exact dispatch runs and waits for all four to succeed before requesting nightly auto-merge against that validated head SHA. This keeps the branch alive long enough for GitHub to create every job even when branch protection is missing or misconfigured; configured required checks and human review remain additional merge controls. Manual scrape and availability pull requests receive and await the same validation but still require human merge.

## Protected environments and repository settings

Production automation requires two GitHub environments. Restrict both environments to the `main` branch; do not allow arbitrary tags or branches.

| Environment | Used by | Secrets | Review policy |
|---|---|---|---|
| `canonical-state` | Restore, migration, authorized collection/audit or manual insertion, validation, and snapshot publication | `VPS_HOST`, `VPS_USER`, `VPS_SSH_PRIVATE_KEY`, `VPS_BACKUP_SSH_PRIVATE_KEY`, `VPS_SSH_KNOWN_HOSTS` | Must permit unattended scheduled runs; use a main-only branch policy and no required reviewer |
| `production` | Restore, validate, snapshot, and checksum-verified VPS deployment | `VPS_HOST`, `VPS_USER`, `VPS_SSH_PRIVATE_KEY`, `VPS_BACKUP_SSH_PRIVATE_KEY`, `VPS_SSH_KNOWN_HOSTS` | Main-only; a required maintainer approval is recommended |

`VPS_SSH_PRIVATE_KEY` is present in `canonical-state` only for the reviewed live-database bootstrap used when durable snapshot state is absent. Normal restore/publication uses the restricted backup key. Deployment mode needs both keys in `production`: the restricted key restores and republishes verified canonical state, while the deployment key performs the final replacement. After moving these values into environments, delete identically named repository secrets and remove this repository's access to equivalent organization secrets so another branch cannot access them outside environment protection.

Keep these non-secret values as repository variables:

| Variable | Required | Default |
|---|---:|---|
| `LINKEDIN_CRAWL_AUTHORIZED` | For source access | No enabled default |
| `VPS_BACKUP_USER` | No | `opportunities-backup` |
| `VPS_SSH_PORT` | No | `22` |
| `CANONICAL_STATE_RETENTION_DAYS` | No | `365` |

Repository configuration must also:

1. set the default `GITHUB_TOKEN` permission to read-only, permit GitHub Actions to create pull requests, and keep elevated permissions explicit at job boundaries;
2. require third-party Actions to use full-length commit SHAs and enable pull-request auto-merge;
3. protect `main` and require the check contexts emitted by the current workflows: `ruff`, `python`, `site`, `docker`, `Analyze (Python)`, and `Analyze (TypeScript)`;
4. prevent direct pushes and choose the review policy deliberately—if an approving review is required, the nightly pull request waits for that human review before auto-merge;
5. enable the dependency graph, Dependabot alerts, secret scanning and push protection, private vulnerability reporting, and CodeQL code scanning where GitHub makes those controls available;
6. retain Actions logs and the documented 30-day sanitized projection artifacts according to repository policy.

The environment branch rules are part of the security boundary, not optional documentation. Both reusable workflows also fail explicitly when `github.ref` is not `refs/heads/main`, including the repository-mutation boundary that does not receive environment secrets.

## First production activation

Complete this once before relying on the scheduled run:

1. merge the release commit into the default `main` branch before the scheduled time; schedules always use the default-branch workflow revision;
2. create and restrict the `canonical-state` and `production` environments exactly as described above, then remove broader copies of their secrets;
3. configure the repository variables and verify that `LINKEDIN_CRAWL_AUTHORIZED=true` reflects current express authorization rather than convenience;
4. enable Actions pull-request creation, auto-merge, branch protection, and all six required check contexts;
5. complete the [one-time public-state seal review](#first-public-state-review-seal) from `main`, then run **Verify canonical state recovery** with its default input; require successful migration, projection validation, round-trip snapshot verification, and the retained sanitized projection artifact;
6. only after that verified durable snapshot exists, delete every legacy `opportunities-db-*` Actions cache and legacy `opportunities-state-*` or `opportunities-nightly-state-*` artifact; these older state bundles are neither approved backups nor safe public artifacts;
7. confirm no local or VPS collector can write the same database and no stale operational workflow is still running or queued;
8. confirm **Nightly full update** is enabled and the repository is active enough for GitHub scheduled workflows.

Before switching an existing production website to versioned releases, complete the [coordinated first rollout](#coordinated-first-rollout-and-rollback); a successful recovery drill does not switch website readers or populate `data/current`. Do not use a live scrape as the first test of SSH, environment, snapshot, or branch-protection configuration. The recovery drill exercises those paths without LinkedIn access.

## First public-state review seal

The generated README now includes a hidden SHA-256 seal of every website-visible open row and the exact last successful collection time. The visible tables remain limited to five jobs per type. A below-preview title, location, category, or first-seen change therefore changes the README proposal and must be reviewed before deployment.

The existing committed README predates the seal. After merging the code change to `main`, run **Verify canonical state recovery** with `adopt_public_review_seal=true`. This mode restores a verified canonical snapshot, or validates a consistent live-database backup under the first-bootstrap rules, migrates its temporary working copy, checks that the old generated README matches apart from the new seal, and uploads sanitized projections. It performs no LinkedIn request and publishes no new durable snapshot or production release. It opens a manual-review, README-only `automated/public-review-seal` pull request. Inspect its sanitized CSV/JSON artifact and generated seal, then merge it. If the old README differs for any other reason, the run fails and the prior state proposal must be reconciled first. Until this baseline PR merges, normal mutation and deployment modes fail closed at the reviewed-state barrier. Subsequent recovery drills use the default input and continue round-trip snapshot verification.

## Collection authorization

Every nightly, scrape-only, or availability-only mode that accesses LinkedIn requires this repository variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

When the variable is missing or has another value, a LinkedIn-accessing run stops before network access. A manual scrape-workflow run with `deploy_to_vps=true` skips collection and availability requests, so deployment-only mode does not require this interlock.

> [!IMPORTANT]
> This variable is an operator attestation, not permission. Enable it only after express authorization has been obtained, and disable it immediately when authorization is absent, uncertain, expired, or withdrawn.

Local and Docker interlocks are documented in [Configuration](../getting-started/configuration.md#authorization-interlocks). The complete source-access boundary is defined in [`SECURITY.md`](../../../SECURITY.md).

## Schedule and concurrency

The nightly full update runs once per day:

```yaml
schedule:
  - cron: "23 4 * * *"

concurrency:
  group: opportunity-collection
  cancel-in-progress: false
```

The nominal scheduled time is 04:23 UTC. It completes the availability audit before starting the scrape. GitHub Actions may start scheduled jobs later than the configured time.

The nightly, scrape-only, availability-only, manual-add, recovery-drill, and deployment paths share `opportunity-collection`. This prevents overlapping writers and state replacement while allowing the read-only website to continue serving requests.

## Manual collection inputs

Two workflows can be run independently from the Actions tab:

- **Check job availability** checks all existing rows and opens an availability-only pull request.
- **Scrape jobs or deploy reviewed state** runs only the scrape and opens a scrape-only pull request when deployment mode is disabled.

The scrape workflow inputs are:

| Input | Default | Effect |
|---|---:|---|
| `deploy_to_vps` | `false` | Skip collection and deploy reviewed durable SQLite state through locked, checksum-verified versioned release publication after validation against `main` |

The availability workflow has no inputs and always proposes changes in its own pull request. Scrape-only collection also always opens a README proposal when public state changes; it cannot advance the snapshot without a review handoff. None of the manual workflows permits an automatic state rebuild: migration or canonical-state validation failures stop the run. VPS deployment is allowed only from `main` when a manual scrape-workflow run explicitly sets `deploy_to_vps=true`; scheduled runs preserve state and update the combined pull request but do not deploy.

## Manual job addition

Use **Add manually reviewed jobs** when a maintainer has independently reviewed 1–10 known public LinkedIn listings that should enter canonical state without running discovery. Run it from `main` once for the batch and paste a JSON array into `jobs_json`. Each object requires `url`, `company`, `title`, `location`, `category`, and `employment_type`; optional keys are `industries`, `start_date`, and `posted_at`. JSON names use underscores. The input is limited to 64 KiB and rejects unknown keys or duplicate LinkedIn IDs. See the [CLI batch example](../user-guide/cli.md#add-jobs) for the format.

The workflow acquires the shared `opportunity-collection` lock and enters the main-only `canonical-state` environment. It restores and verifies the latest canonical snapshot before migration, runs `opportunities add-jobs --no-render` against the batch, regenerates all normal projections, validates them, checkpoints SQLite, and publishes and restore-verifies one new durable snapshot. The CLI validates every entry and applies them in one repository transaction, so an invalid or closed job cannot leave a partial batch. It applies the deterministic classifier to operator-supplied title, location, employment type, category, cycle, and posting-date evidence; a maintainer must verify the source facts independently, because this offline path cannot authenticate them. It creates no synthetic search, search run, or provenance, performs no LinkedIn request, and does not require `LINKEDIN_CRAWL_AUTHORIZED=true`.

Only sanitized public projections are retained. A one-day README-only handoff is passed to the existing mutation workflow, which opens or updates `automated/manual-jobs-YYYY-MM-DD` with a title of the form `data: add manually reviewed jobs (YYYY-MM-DD)`. The date is the workflow run's creation date in Europe/Rome. The pull request changes only `README.md`, runs the normal validation workflows, and remains manual-review only; this path never requests auto-merge. Canonical SQLite is not uploaded as an artifact or cache entry and is not written directly to the live VPS database.

Submit all jobs intended for this pull request in the same run. The reviewed-state barrier blocks another canonical mutation while its README proposal is unmerged. After reviewing and merging that README pull request, deploy production separately through **Scrape jobs or deploy reviewed state** from `main` with `deploy_to_vps=true`. Deployment restores the latest snapshot pointer, which now contains the batch, and validation requires the merged README to match that state before the versioned release-pointer cutover. Running deployment before the README merge stops at projection validation rather than dropping or prematurely deploying the manual jobs.

## Collection and deployment flow

The state-writing workflows share the same recovery, migration, validation, snapshot, and one-writer guarantees, but their source phases differ.

### Collection/update path

<div align="center">
<pre>
authorization check
↓
checkout + pinned runtime setup
↓
restore the latest restricted VPS snapshot manifest and database
↓
optional verified VPS bootstrap when no durable source exists
↓
database migration
↓
availability audit, when selected
↓
bounded collection + classification, when selected
↓
isolated transactional persistence
↓
README + sanitized CSV/JSON projection validation
↓
SQLite WAL checkpoint
↓
timestamped SFTP snapshot + round-trip restore verification
↓
retained sanitized public-projection artifact
↓
one-day README-only handoff artifact
↓
separate least-privilege README pull-request job
</pre>
</div>

The nightly workflow runs availability first and collection second, then validates the combined state and opens one narrowly scoped pull request. The availability-only workflow skips collection; the scrape-only workflow skips the availability phase. A partial collection preserves successful search transactions. Failed searches record diagnostics but do not apply absence, unavailability, or closure evidence.

The manual-add workflow uses the same path but replaces all source phases with one repository-backed `add-jobs --no-render` batch operation followed by normal projection rendering. Its published snapshot advances the same `latest.json` pointer consumed by deployment, so a later deployment restores the reviewed batch instead of rebuilding state from the VPS database.

Before any canonical-state workflow performs a new mutation or deployment, the reusable processor renders the restored snapshot and requires its README projection to match the checked-out `main` README exactly. The generated seal covers the full website-visible state, including rows outside the bounded preview and exact first-seen and collection timestamps. This reviewed-state barrier prevents nightly, scrape-only, availability-only, another manual add, recovery, or deployment from consuming a snapshot whose public-state proposal has not yet been merged. The explicit one-time adoption mode accepts only the seal addition to an otherwise matching legacy README, creates a review PR, and cannot collect or deploy. If a proposal is rejected or closed without merging, subsequent canonical-state workflows fail closed until the reviewed state and durable snapshot are reconciled.

The availability pass visits the public listing for every stored job. A successful public page without a closure alert is then followed by guest detail validation. Successful validation keeps or reopens the row. An explicit HTTP `404` or `410` from either request, or a scoped public-page “No longer accepting applications” alert, deletes the row and its search provenance. Authentication failures, rate limits, server errors, malformed responses, and transport failures are inconclusive: the workflow reports them but preserves those rows. All requests remain behind the LinkedIn authorization interlock and existing pacing limits.

### Deployment-only path

A manual `scrape.yml` run from `main` with `deploy_to_vps=true` does not collect or audit LinkedIn. It follows a separate publication path:

<div align="center">
<pre>
restore reviewed durable SQLite state
↓
migrate + generate sanitized CSV/JSON exports
↓
validate README and exports against canonical state
↓
SQLite WAL checkpoint
↓
publish + round-trip verify canonical snapshot
↓
upload database + exports to a unique VPS staging directory
↓
acquire deployment lock, verify checksums and seal the release
↓
atomically switch the release pointer
</pre>
</div>

The deployment mode and README validation prevent newly collected state from being deployed before its README projection has been reviewed and merged. Keeping restore, validation, snapshot publication, and deployment in one approved `production` job avoids exposing the database through cross-job storage.

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

A dedicated, chrooted, SFTP-only VPS account stores recovery snapshots. Each state-writing workflow downloads `/state/canonical-state/latest.json`, validates its bounded manifest, downloads the referenced timestamped database, and verifies size, SHA-256, schema revision, collection timestamp, SQLite integrity, foreign keys, and required tables. Authentication, host-key, transfer, manifest, checksum, SQLite sidecar, or integrity failures stop the workflow rather than silently using stale state. A pre-existing local database that does not match the manifest also stops recovery without overwriting it. Local WAL/SHM/journal files and pre-existing restore or bootstrap staging files are preserved for inspection.

GitHub Actions cache is deliberately not used for canonical SQLite. GitHub documents that pull-request workflows, including forks, can read default-branch caches. During first-time bootstrap, when no snapshot manifest or history exists, the workflow may instead stream a consistent SQLite backup of the reviewed live database over SSH (including committed WAL changes, without copying sidecars). This requires Python 3 on the deployment host. The backup normalizes SQLite to DELETE journal mode so it can later be read as a cold file without WAL/SHM permissions. When no durable snapshot exists, a pre-existing local database is preserved but never accepted as a bootstrap source. The streamed candidate must independently pass integrity, foreign-key, required-table, and Alembic-revision checks before migration.

After validation and WAL checkpointing (and only when no live SQLite sidecars remain), publication creates a consistent SQLite backup through the SQLite backup API and normalizes its journal mode to DELETE before hashing, so the read-only site does not need writable WAL/SHM sidecars. Snapshot paths resemble:

```text
/state/canonical-state/snapshots/2026/07/20/20260720T030000.000000Z-run-123-attempt-1.db
/state/canonical-state/snapshots/2026/07/20/20260720T030000.000000Z-run-123-attempt-1.manifest.json
```

Every strict JSON manifest records the database path, byte size, SHA-256, Alembic revision, collection and creation timestamps, preceding database and manifest references, workflow source, and retention metadata.

Publication uploads new paths, downloads both files into a clean directory, verifies SQLite and application readability, and only then atomically renames a temporary `latest.json`. The working and deployment copies are byte-identical to the verified download. A failed transfer or verification leaves the prior pointer in place. The restricted account has no shell, sudo, forwarding, application-database access, or membership in `opportunities-site`.

Thirty-day GitHub artifacts contain only `README.md` and the sanitized CSV/JSON exports; they are verification outputs, not recovery sources. No production database or manifest is uploaded to Actions cache or artifacts. Repositories upgrading from an older cache/artifact state handoff must purge legacy `opportunities-db-*`, `opportunities-state-*`, and `opportunities-nightly-state-*` objects after the first restricted snapshot has passed the recovery drill. By default, VPS manifests declare a 365-day retention window; automation does not delete older snapshots. Capacity must be monitored and expiry reviewed manually after `retain_until`. Because snapshot storage is on the same VPS as production, it protects against accidental database replacement but not complete VPS, disk, or provider loss. Replication of encrypted or access-controlled snapshots to an independent host remains the recommended next durability layer.

Canonical backup, sidecar, migration, and restoration rules belong to the [database lifecycle guide](database.md).

## Restricted VPS snapshot configuration

The account is expected to be named `opportunities-backup`, chrooted at `/srv/opportunities-backup`, and forced into `internal-sftp -d /state`. Its writable directory is `/srv/opportunities-backup/state` with mode `0700`. The account must use a dedicated key, must not have sudo or shell access, and must not belong to `opportunities-site`.

### Dedicated `canonical-state` environment secret

| Secret | Purpose |
|---|---|
| `VPS_BACKUP_SSH_PRIVATE_KEY` | Dedicated unencrypted Ed25519 private key for the SFTP-only account |

The `canonical-state` and `production` environments also supply `VPS_HOST` and `VPS_SSH_KNOWN_HOSTS`; `production` needs the backup key so deployment mode can restore and republish state without a GitHub artifact. `VPS_SSH_PORT` remains a repository variable. The verified known-hosts entry is mandatory and host-key checking is strict.

### Snapshot repository variables

| Variable | Required | Default |
|---|---:|---|
| `VPS_BACKUP_USER` | No | `opportunities-backup` |
| `CANONICAL_STATE_RETENTION_DAYS` | No | `365` |

The private key is written only for restore/publication steps and removed with `known_hosts` afterward. The normal VPS deployment key remains separate. After configuring GitHub, complete the [one-time public-state seal review](#first-public-state-review-seal), then run **Verify canonical state recovery** with its default input. The default drill performs no LinkedIn access and seeds the first snapshot from the reviewed live database only when snapshot storage is empty.

## README update pull requests

Each path uses a separate review branch pattern:

```text
automated/nightly-full-update  # availability followed by scrape
automated/availability-update  # manually requested availability only
automated/scrape-update        # manually requested scrape only
automated/manual-jobs-YYYY-MM-DD # manually reviewed job batch
automated/public-review-seal   # one-time baseline from verified state
```

Only `README.md` is committed. SQLite state is never committed. Canonical processing uploads a one-day README-only handoff, then a separate job with `actions: write`, `contents: write`, and `pull-requests: write` downloads that file and performs the GitHub mutation and validation dispatch. Processing retains only `contents: read`; the mutation job receives no VPS credentials or state bundle.

The generated preview remains bounded to five recently discovered open opportunities per employment type, regardless of database size. The seal makes every public-directory change produce a README diff, even when all changed rows are outside that preview. Review the sanitized public CSV/JSON artifact linked from the pull-request body before merging a seal-only diff. Those downloads exclude first-seen timestamps, and the displayed collection time has minute precision; if the artifact does not explain the seal change, inspect the relevant values in protected canonical state before approving. The hash alone does not show which rows changed.

The nightly workflow creates or updates its fixed branch and requests a squash auto-merge. Before mutating an existing proposal, and again before dispatching validation or requesting auto-merge, it verifies the exact base branch, same-repository head branch, title, changed-file list, and expected head SHA; the pull request must target `main` and modify only `README.md`. It retries the post-push GitHub scope read briefly to tolerate API propagation, but never relaxes the expected scope. It then waits for the exact Python, site, Docker, and CodeQL dispatch runs on that head SHA to succeed and supplies the SHA to the merge request, so a later head change cannot use stale validation. If generated state already matches `main`, a matching stale automation pull request is closed rather than left eligible to merge. GitHub auto-merge must be enabled; required checks, up-to-date-branch rules, and review requirements remain recommended defense in depth. Scrape-only, availability-only, and manual-add pull requests receive the same dispatched validation but remain manual-review paths.

Scheduled runs do not deploy to the VPS. After the nightly pull request merges—or after a maintainer reviews and merges a manual update—start a manual scrape-workflow run from `main` with `deploy_to_vps=true` to publish the matching canonical state. Deployment mode skips collection and availability requests, then requires the merged README to validate exactly against restored durable SQLite before deployment. The pull request contains the human-readable README projection; SQLite remains inside protected snapshot storage and the approved production job and is never committed, cached, or uploaded as an artifact. Do not edit generated rows manually; change the renderer or canonical state instead.

## Post-nightly production runbook

Use this sequence after each scheduled collection. Do not deploy merely because the scheduled job started; deployment is permitted only after the matching README projection reaches `main`.

1. Open the **Nightly full update** run and confirm **Audit, collect, and preserve state** succeeded. Read the command summaries for partial availability or partial collection. A reported partial result is intentionally preserved and may proceed only because final validation and snapshot verification passed.
2. Confirm the run published the 30-day `opportunities-nightly-projections-<run-id>` sanitized projection artifact and completed round-trip snapshot verification. The artifact must not contain SQLite or a snapshot manifest.
3. Inspect the fixed `automated/nightly-full-update` pull request. It must target `main`, have the exact nightly title, and change only `README.md`.
4. Confirm the README mutation job identified and awaited the explicitly dispatched Python, site, Docker, and CodeQL runs on the pull-request head SHA. Do not bypass, re-label, or manually broaden the automation pull request to make auto-merge proceed.
5. Confirm the pull request squash-merged and that `main` now contains its generated count, timestamp, and preview. If branch protection requires review, inspect the README-only diff and approve it first. If it remains open afterward, diagnose the failed or missing required check before deployment.
6. From the Actions tab, run **Scrape jobs or deploy reviewed state** on `main` with `deploy_to_vps=true`.
7. Approve the `production` environment deployment if required. Confirm **Validate, preserve, and deploy reviewed state** restores and validates the matching state before its final deployment step. A README/database mismatch is a safety stop, usually meaning the matching projection was not merged or a newer snapshot exists.
8. Confirm staging, checksum verification, lock acquisition, immutable release publication, and the single pointer switch completed in the deployment log. Never print secrets or database rows while reviewing logs.
9. Verify the live directory and both fixed downloads over HTTPS. Check that the visible counts and last successful collection time match `main`, filtering and pagination still work, and CSV/JSON downloads return the expected attachment filenames.
10. Keep the nightly and deployment run IDs for the operational record. If authorization will not remain valid for the next scheduled run, immediately set `LINKEDIN_CRAWL_AUTHORIZED=false` or remove the variable.

If any step before deployment fails, leave production unchanged and diagnose the failed stage. If deployment fails, do not collect again as a repair strategy; inspect the lock, staged uploads, release directory, and `current` symlink. Before pointer promotion the previous release stays live; afterward select a verified prior release under the lock if rollback is required. Canonical snapshot recovery remains separate.

## VPS deployment

### Required `production` environment secrets

| Secret | Purpose |
|---|---|
| `VPS_HOST` | Deployment host |
| `VPS_USER` | Dedicated SSH user |
| `VPS_SSH_PRIVATE_KEY` | Ed25519 deployment private key |
| `VPS_BACKUP_SSH_PRIVATE_KEY` | Restricted snapshot key used to restore and republish validated state |
| `VPS_SSH_KNOWN_HOSTS` | Pre-verified SSH host-key entry |

### Repository variables

| Variable | Required | Default or example |
|---|---:|---|
| `VPS_SSH_PORT` | No | `22` |

### Deployment sequence

After a review pull request is merged, a deployment-mode run enters the approval-protected `production` environment, restores the verified durable database state, skips all new collection and availability requests, regenerates the sanitized public exports, validates every projection against `main`, and round-trip verifies a new snapshot. The same `contents: read` job then:

1. uploads the validated database, CSV, and JSON to an execution-specific staging directory under `data/.incoming/` (not to the legacy live paths);
2. under a nonblocking VPS `flock`, verifies all three SHA-256 digests again and rejects missing files, sidecars, pre-existing release IDs, and invalid pointers;
3. writes `checksums.sha256` for the three payloads, assigns `opportunities-site` group read access, renames the complete directory to `data/releases/<run-id>-<attempt>` on the same filesystem, makes it read-only to the site group, and flushes the published files and directories;
4. atomically renames a relative symlink `data/current` to point at the new immutable release, then flushes the directory; failed or completed client runs attempt to clean up their staging uploads, while published releases are never removed automatically. Releases are retained for in-flight readers and manual rollback. A failure after pointer promotion cannot be assumed to have left the old release live: inspect `current`.

The site resolves `current` **once per server operation** to a fixed release directory and opens its SQLite database or export there. A cutover cannot mix files *within one directory resolution*. Concurrent requests may span two revisions; a page followed by a separate download is **not** a pinned multi-request transaction. Do not garbage-collect a release until all readers of that release have drained. The fixed legacy paths remain unchanged and will become stale; follow the coordinated rollout below before claiming atomic publication.

### Coordinated first rollout and rollback

This is **not** a drop-in update for a VPS serving the old fixed paths:

1. Merge and validate the site release-reader and deployment scripts, then complete the one-time public-state seal review. Preserve the verified restricted snapshot and the old site configuration. Ensure the deployment user can create `data/.incoming`, `data/releases`, and `data/.release-deploy.lock`; the site group must be able to traverse the data directory.
2. Run deployment-only once while the old site still reads the unchanged legacy files. On the VPS, verify that `data/current` points to the new `releases/<id>` and run `(cd data/current && sha256sum -c checksums.sha256)`. Do not switch readers if deployment or verification fails.
3. Drain old site instances or temporarily remove traffic. Set `OPPORTUNITIES_RELEASE_ROOT=/app/data` on **every** site instance, restart them, and route traffic only to those instances. Confirm the directory and both HTTPS downloads reflect the reviewed release. Do not leave mixed legacy/new instances behind a load balancer.

After `current` exists, never use the fixed legacy database as a recovery source; restore a verified restricted snapshot instead. A missing snapshot pointer is a stop condition when `current` **or** the versioned `releases` directory exists, even if an old fixed file is present.

For rollback, stop new cutovers, confirm the desired prior release's database schema is readable by the running site and matches a verified restricted snapshot, and verify its three payload hashes with `(cd data/releases/<prior-id> && sha256sum -c checksums.sha256)`. Under the same `data/.release-deploy.lock` (nonblocking `flock`), create a fresh temporary relative symlink to `releases/<prior-id>` **in `data/`** and atomically `mv -Tf` it over `current`; flush the data directory and check the live site and both downloads. If a temporary symlink already exists, inspect it rather than overwriting it. Keep both releases until readers drain. This reverts the **served projection**, not the restricted snapshot history; reconcile that history deliberately before the next deployment. Do not roll back an application image that cannot read the chosen schema, or repoint the site to stale legacy paths. If the symlink is missing/invalid, the versioned site fails closed rather than falling back to legacy state.

Compose topology, volume permissions, Dokploy routing, and container diagnostics belong to the [Docker and deployment guide](docker.md).

## Recovery and migration failures

Normal workflow migrations use:

```bash
uv run opportunities db-upgrade
```

A migration, integrity, manifest, or canonical-state validation failure stops the workflow. Collection workflows do not expose a state-rebuild input and never delete restored state to recover automatically.

Preserve the failed state, then review durable snapshot history and manifests followed by retained versioned releases (or the legacy previous VPS database only if versioned publication has never occurred). Sanitized projection artifacts cannot restore lifecycle state. Restore a verified compatible snapshot rather than initializing an unrelated empty history. Any intentional rebuild is an exceptional manual recovery decision because it loses original first-seen history, search provenance, closure confirmations, and run diagnostics. Follow [Database lifecycle](database.md#restore) and [Troubleshooting](troubleshooting.md#github-actions-and-deployment).

## Disabling collection

Set the repository variable to `false` or remove it:

```text
LINKEDIN_CRAWL_AUTHORIZED
```

Scheduled and manual collection runs then stop at the authorization gate without contacting LinkedIn.

Do not bypass the gate by hardcoding an enabled value in workflow or application code.

## Operational checklist

Before changing or manually running automation, confirm:

- [ ] Validation CI remains separate from LinkedIn collection.
- [ ] LinkedIn authorization is current and recorded outside the repository.
- [ ] Nightly, scrape-only, availability-only, manual-add, recovery, and deployment paths retain the shared one-writer concurrency group.
- [ ] Third-party actions remain pinned where practical.
- [ ] Logs contain no secrets, GitHub contexts, HTML bodies, `.env` values, or database rows.
- [ ] SQLite is checkpointed and validated before durable snapshot or deployment publication.
- [ ] The SFTP-only account restrictions, host-key checks, manifest checksums, retention metadata, and automated restore verification remain enforced.
- [ ] Migration or state-validation failures stop without deleting restored canonical state.
- [ ] Manual recovery uses a reviewed, checksum-verified source.
- [ ] VPS host keys are pre-verified.
- [ ] Deployment remains checksum-verified and locked, with a single atomic versioned release pointer and coordinated site rollout.
- [ ] SQLite state is never committed to Git.
- [ ] Canonical processing remains read-only to GitHub; only the README mutation job has repository and pull-request write permissions.
- [ ] No canonical database or manifest enters GitHub cache or artifacts; only the README handoff expires after one day.
- [ ] `canonical-state` and `production` allow only `main`, and VPS secrets are unavailable to this repository outside those environments.
- [ ] The README mutation job has `actions: write` only to dispatch the four validation workflows on the generated commit.
- [ ] Artifact visibility, environment protection, and SSH access follow least privilege.
