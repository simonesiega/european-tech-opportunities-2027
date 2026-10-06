# Repository scripts

[← Documentation home](../docs/README.md) · [Maintainer handbook](../docs/maintainers/README.md) · [Testing](../docs/maintainers/engineering/testing.md) · [GitHub workflows](../.github/WORKFLOWS.md)

This inventory identifies the repository scripts, their inputs, and their side effects. Use the offline checks during development; run state-transfer and deployment scripts only within the protected operational procedures linked below.

Run the example commands from the repository root. Python scripts use `uv`; see [local setup](../docs/maintainers/getting-started/setup.md) if you have not installed the development tools yet.

## Directory map

| Folder | Contents |
|---|---|
| [docs/](docs/) | Documentation checks, site builds, and coverage reports |
| [database/](database/) | Migration checks, database snapshots, and recovery |
| [deployment/](deployment/) | Upload and activation of reviewed website data |
| [testing/](testing/) | Synthetic listings for website tests and the product demo |

## Documentation

| Script | What it does |
|---|---|
| [check_docs.py](docs/check_docs.py) | Checks local links, images, and heading references in maintained docs, including diagram Markdown and the workflow/script inventories. Reports broken references without editing files. Does not check external websites. |
| [lint_docs.py](docs/lint_docs.py) | Checks Markdown formatting and project terminology with Markdownlint and Vale. Requires Docker and leaves source files unchanged. You can select just one tool with `markdownlint` or `vale`. |
| [build_docs.py](docs/build_docs.py) | Builds the public documentation into `build/docs-site/`, including redirects from older guide URLs. Rejects unexpected files and symbolic links. Builds locally; it does not publish the site. |
| [check_built_docs.py](docs/check_built_docs.py) | Checks links, anchors, images, and videos in the built documentation, along with the files allowed in the published site. Run it after a successful build. |
| [coverage_docs.py](docs/coverage_docs.py) | Updates the generated coverage table in the testing guide from `quality-reports/coverage.json`. Use `--check` to report stale figures without changing the guide. |

To check and build documentation:

```bash
uv run --frozen python scripts/docs/check_docs.py
uv run --frozen python scripts/docs/lint_docs.py
uv run --frozen --group docs python scripts/docs/build_docs.py
uv run --frozen --group docs python scripts/docs/check_built_docs.py
```

If you have Make installed, `make docs-site` runs the same sequence. The lint step needs a running Docker daemon; the build commands install the documentation dependencies through uv.

For coverage updates, `make coverage` runs the offline test suite, writes the reports, and refreshes the testing guide. After generating a report, you can check that the committed figures match it:

```bash
uv run --frozen python scripts/docs/coverage_docs.py --check
```

Do not edit generated coverage figures by hand. See [documentation maintenance](../docs/maintainers/engineering/documentation.md) for the full editing and publishing process.

## Database checks and sample data

These scripts use temporary or disposable databases, not production data. Neither contacts LinkedIn.

| Script | What it does |
|---|---|
| [check_migrations.py](database/check_migrations.py) | Creates a temporary database, applies the migrations, and checks that the resulting schema matches the application's database models. Does not upgrade your working database. |
| [create_site_fixture.py](testing/create_site_fixture.py) | Creates synthetic listings and matching CSV/JSON exports for website tests in `site/tests/e2e/.tmp/`. Replaces the disposable fixture database when rerun. With `--demo`, writes a separate fixed-date dataset under `.tmp/demo/` for recording the product tour. |

To check migrations:

```bash
uv run --frozen python scripts/database/check_migrations.py
```

Website browser tests prepare their fixture automatically. To recreate it yourself:

```bash
uv run --frozen python scripts/testing/create_site_fixture.py
```

Stop anything using the fixture database before regenerating it. If the script reports SQLite sidecar files, close the database rather than deleting those files while it is in use.

For the demo dataset, use:

```bash
uv run --frozen python scripts/testing/create_site_fixture.py --demo
```

See the [testing guide](../docs/maintainers/engineering/testing.md) for test commands and the [media guide](../docs/assets/README.md) for recording the tour.

## Backups, recovery, and deployment

Maintainers normally run these scripts through the protected GitHub workflows. They can access private database state, replace local files, publish backups, or change the data served by the website. They are **not general-purpose test commands**.

Before using them directly, follow the [automation guide](../docs/maintainers/operations/automation.md) and [database recovery instructions](../docs/maintainers/operations/database.md). Production operations require the configured credentials, verified SSH host keys, and the appropriate review and approval.

| Script | What it does |
|---|---|
| [restore_canonical_state.sh](database/restore_canonical_state.sh) | Restores the latest verified database snapshot. For first-time setup only, it can obtain a consistent backup of the legacy live database when no snapshot history or versioned deployment exists. Stops rather than overwriting conflicting local state. |
| [canonical_state_store.sh](database/canonical_state_store.sh) | Transfers snapshots through the restricted SFTP backup account. `restore` downloads and verifies saved state; `publish` uploads a snapshot and downloads it again for verification before marking it as latest. Publication retains the local bundle for resumption, reconciles partial remote uploads, and replaces the local working database with the verified copy. |
| [sftp_publication.sh](database/sftp_publication.sh) | Sourced helper for snapshot publication, not a standalone command. Inspects remote directories and final/staging objects, retries recognized transient transport failures within bounded attempts, and refuses conflicting immutable bytes or unexpected latest-pointer changes. |
| [canonical_snapshot.py](database/canonical_snapshot.py) | Creates and verifies database snapshots and their manifests, which record checksums and recovery metadata. Its `key` and `field` commands read selected manifest values. Used by the snapshot-storage script. |
| [bootstrap_sqlite.py](database/bootstrap_sqlite.py) | Streams a consistent backup of an existing database during first-time recovery, including committed changes still in SQLite's write-ahead log. Its output is binary database content, not text to display in a terminal. It does not initialize an empty database. |
| [deploy_canonical_state.sh](deployment/deploy_canonical_state.sh) | Validates the reviewed database and public exports, uploads them to the VPS, and calls the release-activation script. Publishes website data, not a new application build. |
| [activate_canonical_release.sh](deployment/activate_canonical_release.sh) | Runs on the VPS during deployment. Checks the uploaded files, prepares a read-only release, and switches the website to that release under a deployment lock. Keeps earlier releases available for rollback. |

For the snapshot tool's command options without accessing a database:

```bash
uv run --frozen python scripts/database/canonical_snapshot.py --help
```

Database snapshots contain operational history that is not included in public downloads. Keep snapshots and manifests in protected storage; do not attach them to public issues or upload them as GitHub artifacts.

For publication retry limits, staging-file handling, and same-run/attempt resumption boundaries, see [state continuity and artifacts](../docs/maintainers/operations/automation.md#state-continuity-and-artifacts).

If recovery or deployment stops because files, checksums, or database state do not match, preserve the files and follow the [troubleshooting guide](../docs/maintainers/operations/troubleshooting.md). Do not delete the database or retry against empty state as a shortcut.

## Supporting files

The `__init__.py` files in this directory and its Python subfolders let the test suite and other tools import these helpers. You do not need to run them.
