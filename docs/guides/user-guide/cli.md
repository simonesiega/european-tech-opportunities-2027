# European Tech Opportunities 2027 CLI Reference

[← Documentation hub](../../README.md) · [Installation](../getting-started/installation.md) · [Configuration](../getting-started/configuration.md) · [Troubleshooting](../operations/troubleshooting.md) · [Security policy](../../../SECURITY.md)

This is the canonical CLI reference for the project. The `opportunities` CLI manages database migrations, search inspection, authorized collection, canonical SQLite state, validation, generated documentation, and sanitized public data projections.

Show the command overview:

```bash
uv run opportunities --help
```

General form:

```text
uv run opportunities [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

Select an optional settings file:

```bash
uv run opportunities --settings configs/settings.local.yml stats
```

The global `--settings` option must appear before the command name.

## Contents

- [Command overview](#command-overview)
- [`db-upgrade`](#db-upgrade)
- [`searches`](#searches)
- [`search-test`](#search-test)
- [`scrape`](#scrape)
- [`add-job`](#add-job)
- [`add-jobs`](#add-jobs)
- [`check-availability`](#check-availability)
- [`render`](#render)
- [`export-public`](#export-public)
- [`stats`](#stats)
- [`validate`](#validate)
- [Exit codes](#exit-codes)
- [Command side effects](#command-side-effects)
- [Common command sequences](#common-command-sequences)

## Command overview

| Command | Purpose |
|---|---|
| `db-upgrade` | Create or upgrade the configured database schema |
| `searches` | Inspect the effective search registry and available run health |
| `search-test` | Run one authorized search without persistence |
| `scrape` | Run authorized collection and persist independent search outcomes |
| `add-job` | Add a known LinkedIn listing to canonical state without search provenance |
| `add-jobs` | Validate and add a bounded batch of reviewed listings in one transaction |
| `check-availability` | Audit every stored LinkedIn listing and delete explicitly unavailable rows |
| `render` | Regenerate owned README, search-registry documentation, and public data projections |
| `export-public` | Regenerate only the sanitized public CSV and JSON projections |
| `stats` | Display aggregate canonical state |
| `validate` | Check schema, lifecycle invariants, and generated projections |

Configuration sources and precedence are documented in [Configuration](../getting-started/configuration.md).

## `db-upgrade`

```bash
uv run opportunities db-upgrade
```

Creates or upgrades the configured database to the single Alembic head.

It:

- loads Alembic configuration and revisions;
- creates missing tables;
- applies pending migrations;
- performs no LinkedIn network access;
- does not render the README.

Run it before commands that require canonical database state.

Migration design, backup, and recovery belong to the [database lifecycle guide](../operations/database.md#migrations).

## `searches`

```bash
uv run opportunities searches
```

Displays the effective search registry, including:

- configured search slugs and whether each is enabled;
- location scope;
- effective page, result, and recheck limits;
- latest run status;
- found and accepted counts when migrated state is available.

It performs no network access and does not modify SQLite.

Use it after changing search YAML or global search-limit overrides.

Search schema and tuning are documented in the [search registry guide](search-registry.md).

## `search-test`

```bash
uv run opportunities search-test <slug>
```

Runs one enabled search without persistence.

It:

- requires the LinkedIn authorization interlock;
- performs bounded LinkedIn guest-page requests;
- parses, normalizes, and classifies candidates;
- prints the result and diagnostics;
- does not write SQLite;
- does not update the README.

Use it for one authorized parser, query, or classification preview before persisted collection.

> [!IMPORTANT]
> The interlock is a safety gate, not permission. Source authorization requirements are defined in [`SECURITY.md`](../../../SECURITY.md).

## `scrape`

Run every enabled search:

```bash
uv run opportunities scrape
```

Run one selected search:

```bash
uv run opportunities scrape --search company-amazon
```

Persist state without modifying the README:

```bash
uv run opportunities scrape --no-render
```

The command:

1. verifies authorization and migration preconditions;
2. loads and synchronizes the complete search registry;
3. selects every enabled search or one requested slug;
4. fetches, parses, normalizes, and classifies candidates;
5. commits each search outcome independently;
6. updates provenance and explicit lifecycle evidence;
7. renders the owned README, search-registry documentation, and public CSV/JSON projections unless `--no-render` is set.

A partial run preserves successful search transactions.

A failed search:

- records bounded diagnostics;
- does not apply absence evidence;
- does not increment unavailability confirmations;
- does not close jobs.

Use `--no-render` where canonical state should change without modifying generated files in the Git working tree, such as a website-only VPS.

The collection lifecycle is documented in [Architecture](../development/architecture.md#failure-isolation) and [Database lifecycle](../operations/database.md#successful-search-transaction).

## `add-job`

Maintainers can add a known LinkedIn listing without running collection:

```bash
uv run opportunities add-job \
  --url https://www.linkedin.com/jobs/view/1234567890 \
  --company "Example Technology" \
  --title "Software Engineering Intern 2027" \
  --location "London, UK" \
  --category software-engineering \
  --employment-type internship
```

Required options are `--url`, `--company`, `--title`, `--location`, `--category`, and `--employment-type`. Optional metadata can be supplied with `--industries`, `--start-date`, and `--posted-at`; `--posted-at` requires an ISO-8601 timestamp with an explicit timezone, must not be in the future, and is normalized to UTC. A yearless title without eligible posting evidence is rejected. Use `--no-render` to update only SQLite.

The command:

- extracts the numeric identity from the canonical LinkedIn `/jobs/view/<id>` URL;
- validates and normalizes the row through `DiscoveredJob`, then applies the same deterministic classifier as collection (title, category, employment type, cycle/posting date, and European location) before writing;
- inserts or updates an open row through the repository; rejects a closed row, which must be reopened by valid discovery or a successful full-state availability audit;
- creates no search, search run, or `job_searches` provenance;
- performs no network access and does not require the LinkedIn authorization interlock;
- refreshes the README, search-registry documentation, and public CSV/JSON projections by default.

A manual insertion does not change the README's last successful collection timestamp. That timestamp remains derived from successful collection runs. The full availability audit includes manual rows, and a later ordinary scrape can attach real search provenance to the existing job.

## `add-jobs`

For several independently reviewed listings, place 1–10 jobs in a UTF-8 JSON array and run one batch:

```json
[
  {
    "url": "https://www.linkedin.com/jobs/view/1234567890",
    "company": "Example Technology",
    "title": "Software Engineering Intern 2027",
    "location": "London, UK",
    "category": "software-engineering",
    "employment_type": "internship"
  },
  {
    "url": "https://www.linkedin.com/jobs/view/2345678901",
    "company": "Example Research",
    "title": "Machine Learning New Grad 2027",
    "location": "Paris, France",
    "category": "machine-learning",
    "employment_type": "new-grad",
    "posted_at": "2026-09-24T10:00:00+02:00"
  }
]
```

```bash
uv run opportunities add-jobs --input manual-jobs.json
```

Each object uses the same required and optional fields as `add-job`; JSON field names use underscores for `employment_type`, `start_date`, and `posted_at`. The input must be no larger than 64 KiB. Unknown fields, duplicate LinkedIn IDs, invalid or closed jobs, and any failed classification reject the whole batch before a canonical transaction commits. The repository applies all accepted rows in one transaction. By default the command then refreshes the normal projections; `--no-render` changes only SQLite. It makes no LinkedIn request and creates no synthetic search provenance.

## `check-availability`

```bash
uv run opportunities check-availability
```

Check canonical state without updating generated documentation:

```bash
uv run opportunities check-availability --no-render
```

The command requires the LinkedIn authorization interlock and checks every job row, including rows currently marked closed. It requests the public listing first; a successful public page without a closure alert is then followed by guest detail validation. It then applies one transaction:

- successful public-page and detail-page validation keeps the row open or reopens it;
- HTTP `404` or `410` from either request permanently deletes the job and cascading search provenance;
- a scoped public-page “No longer accepting applications” alert also permanently deletes the job;
- authentication failures, rate limits, server errors, malformed responses, and transport failures preserve the row as inconclusive.

The command exits with code `2` when one or more checks are inconclusive. Confirmed results remain committed, and the default path refreshes the owned README, registry documentation, and public CSV/JSON projections. The nightly workflow runs this full audit once per day before scraping, opens or updates a tightly scoped README pull request, explicitly dispatches and awaits validation on that generated commit, and only then requests auto-merge. The availability-only workflow can run the same command manually and opens its own validated manual-review pull request.

## `render`

```bash
uv run opportunities render
```

Regenerates every owned projection from canonical SQLite state and the configured search registry.

The README projection includes:

- total open-job count;
- latest successful collection time;
- the public website link;
- at most five recently discovered internships and five recently discovered New Grad opportunities.

The generated registry-layout counts in [`search-registry.md`](search-registry.md) are refreshed from `configs/searches/` at the same time. Sanitized `open-opportunities.csv` and `open-opportunities.json` files are generated from all open rows using the fixed public-field allowlist.

The command:

- performs no network access;
- does not modify SQLite;
- writes the owned README regions through atomic replacement;
- refreshes the owned generated registry-layout block in `search-registry.md`;
- atomically replaces both public exports.

> [!IMPORTANT]
> A fresh local database contains no listings. Do not render and commit the preview from empty development state.

Do not edit generated counts, timestamps, opportunity rows, registry-layout counts, or public exports manually.

## `export-public`

```bash
uv run opportunities export-public
```

Generates only `open-opportunities.csv` and `open-opportunities.json` in the configured public-export directory. It reads currently open SQLite rows, serializes only the approved public opportunity fields, neutralizes spreadsheet formulas in CSV text, and atomically replaces both files.

This command performs no network access, does not modify SQLite or documentation, and is used by deployment-only automation after restoring reviewed canonical state. The exports omit lifecycle timestamps, status, provenance, runs, closure evidence, and diagnostics.

## `stats`

```bash
uv run opportunities stats
```

Displays aggregate canonical state, including:

- total, open, and closed jobs;
- configured searches;
- successful and failed search runs;
- latest successful collection.

It performs no network access and does not modify state.

Use it after migration, collection, restoration, or deployment to verify that the command is reading the intended database.

## `validate`

```bash
uv run opportunities validate
```

Checks:

- required database tables;
- the Alembic revision;
- monotonic lifecycle timestamps;
- exact README projection equality with canonical state;
- generated search-registry layout counts against the configured YAML files;
- exact public CSV and JSON equality with the approved fields from open SQLite rows.

Validation performs no network access and never repairs state automatically.

Run it only when the configured database contains the representative canonical state expected by the committed generated documentation.

For diagnosis, use [Troubleshooting](../operations/troubleshooting.md).

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Command completed successfully |
| `1` | Every selected search failed, or validation found an inconsistency |
| `2` | Partial scrape, availability audit with inconclusive checks, or rejected command/configuration input |
| `3` | Required database tables are missing or the schema is not at migration head |

After a partial scrape with exit code `2`:

- successful search transactions remain committed;
- failed searches retain diagnostics;
- failed searches do not mutate lifecycle state;
- validation should pass before publication or deployment.

GitHub Actions handling of these codes is documented in [Automation](../operations/automation.md#exit-code-handling).

## Command side effects

| Command | LinkedIn network | Writes SQLite | Writes projections |
|---|---:|---:|---:|
| `db-upgrade` | No | Schema only | No |
| `searches` | No | No | No |
| `search-test` | Yes, after authorization gate | No | No |
| `scrape` | Yes, after authorization gate | Yes | README + registry docs + public exports after at least one successful search |
| `scrape --no-render` | Yes, after authorization gate | Yes | No |
| `add-job` | No | Yes | README + registry docs + public exports |
| `add-job --no-render` | No | Yes | No |
| `add-jobs` | No | Yes, one transaction | README + registry docs + public exports |
| `add-jobs --no-render` | No | Yes, one transaction | No |
| `check-availability` | Yes, after authorization gate | Yes | README + registry docs + public exports |
| `check-availability --no-render` | Yes, after authorization gate | Yes | No |
| `render` | No | No | README + registry docs + public exports |
| `export-public` | No | No | Public exports only |
| `stats` | No | No | No |
| `validate` | No | No | No |

## Common command sequences

### Initialize a local database

```bash
uv run opportunities db-upgrade
uv run opportunities searches
uv run opportunities stats
```

A fresh database intentionally contains no listings.

### Inspect registry and canonical state

```bash
uv run opportunities searches
uv run opportunities stats
```

### Test one authorized search without persistence

```bash
uv run opportunities search-test <slug>
```

### Persist one authorized search

```bash
uv run opportunities scrape --search <slug>
uv run opportunities validate
```

Validation assumes that the configured SQLite database and generated README represent the same canonical state.

### Collect without modifying the README

```bash
uv run opportunities scrape --no-render
uv run opportunities stats
```

### Regenerate every projection from representative state

```bash
uv run opportunities render
uv run opportunities validate
```

### Regenerate only public downloads

```bash
uv run opportunities export-public
```

### Verify migrations during development

```bash
uv run opportunities db-upgrade
uv run python scripts/check_migrations.py
```

Valid slugs and query configuration are documented in the [search registry guide](search-registry.md). Complete engineering checks are documented in the [development guide](../development/development.md#validation-paths).
