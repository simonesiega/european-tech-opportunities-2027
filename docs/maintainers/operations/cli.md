# CLI reference

[← Maintainer handbook](../README.md) · [Local setup](../getting-started/setup.md) · [Configuration](../getting-started/configuration.md) · [Troubleshooting](troubleshooting.md) · [Security policy](../../../SECURITY.md)

Use `opportunities` for schema upgrades, search inspection, authorized collection, reviewed offline additions, and public projection validation. Commands below run from the repository root; check [side effects](#command-side-effects) before operating on canonical state.

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

The global `--settings` option must appear before the command name. In this reference, **public exports** means all three generated files: `open-opportunities.csv`, `open-opportunities.json`, and `dataset-metadata.json`.

## Contents

- [Command overview](#command-overview)
- [`db-upgrade`](#db-upgrade)
- [`searches`](#searches)
- [`search-test`](#search-test)
- [`scrape`](#scrape)
- [Quality report](#quality-report)
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
| `scrape` | Run authorized collection, persist independent outcomes, and optionally check collection quality |
| `add-job` | Add a known LinkedIn listing to canonical state without search provenance |
| `add-jobs` | Validate and add a bounded batch of reviewed listings in one transaction |
| `check-availability` | Audit a bounded batch of due listings and delete explicitly unavailable rows |
| `render` | Regenerate owned README, search-registry documentation, and public data projections |
| `export-public` | Regenerate sanitized CSV/JSON downloads and their metadata manifest |
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

Migration design, backup, and recovery belong to the [database lifecycle guide](database.md#migrations).

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

Search schema and tuning are documented in the [search registry guide](../engineering/search-registry.md).

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

Persist state without refreshing generated projections:

```bash
uv run opportunities scrape --no-render
```

The canonical collection workflows also request a sanitized drift report:

```bash
uv run opportunities scrape --quality-report quality-reports/data-quality-report.json
```

The command:

1. verifies authorization and migration preconditions;
2. loads and synchronizes the complete search registry;
3. selects every enabled search or one requested slug;
4. fetches, parses, normalizes, and classifies candidates;
5. commits each search outcome independently;
6. updates provenance and explicit lifecycle evidence;
7. when `--quality-report` is supplied, compares aggregate counts, field completeness, category/country mix, and scraper warnings with prior aggregate observations, labels full versus partial registry scope, writes a JSON report, and stores a bounded aggregate baseline only after every enabled search succeeds and no blocking finding occurs;
8. renders the owned README, search-registry documentation, and all public exports after at least one successful search, unless `--no-render` is set.

A partial run preserves successful search transactions. Quality warnings are reported but do not block the scrape. Blocking drift (such as every enabled search unexpectedly returning zero candidates or an extreme acceptance-rate change) returns exit code `1`; the report is still written before the command exits, and projections are not refreshed. The gate runs after independent search transactions commit, so blocking drift withholds projection rendering but does not roll back those canonical transactions. The report contains aggregate metrics only, not listing content. CI retains it as a separate 30-day artifact.

A failed search:

- records bounded diagnostics;
- does not apply absence evidence;
- does not increment unavailability confirmations;
- does not close jobs.

Use `--no-render` where canonical state should change without refreshing any generated projection, including ignored public exports, such as a website-only VPS.

The collection lifecycle is documented in [Architecture](../engineering/architecture.md#failure-isolation) and [Database lifecycle](database.md#successful-search-transaction).

### Quality report

`--quality-report <path>` opts into the quality gate, including with `--no-render`. Without it, scrape behavior is unchanged. The versioned JSON report contains `status` (`passed`, `warning`, or `failed`), warning/blocking counts, stable finding codes, aggregate metrics, run scope, and baseline readiness. It never includes job IDs, listing text, raw warnings, source responses, or database paths. Failed-search metrics are unavailable, not fabricated zeros; collection totals cover successful searches only.

Comparisons require at least three usable observations from the latest five stored full-registry snapshots, all within the preceding 30 days. New or changed collection settings warm up a new baseline; search names, notes, and verification dates do not reset it. `baseline.status: warming_up` means historical comparisons are not ready, even if the report has no findings. Invalid or future-dated snapshots generate a warning and are ignored; expired snapshots are ignored. Only successful full-registry runs without blocking findings advance history. Warning-only runs can advance it, so review warnings rather than treating them as permanent protection against sustained drift.

| Check | Warning | Blocking |
|---|---|---|
| Candidate volume | ≥80% drop against the matching registry median, with baseline ≥10 candidates | Every enabled search returns zero against that baseline |
| One search becomes empty | Zero candidates after a positive matching median | No |
| Acceptance rate | Absolute change ≥40 percentage points | Absolute change ≥75 percentage points |
| Scraper warnings | At least 3 warnings and ≥25% of the larger of candidate, parsed-detail, and warning counts | No; parser/transport failures retain their existing search-failure behavior |
| Field missingness | Increase ≥40 percentage points, or newly reaching ≥99% missing | No |
| Category disappearance | No open rows for a category with historical median ≥3 | No |
| Country distribution | Total-variation distance ≥0.5, or fewer than 10 country observations remain against a sampled baseline | No |
| Failed searches | Any selected search fails | No selected search succeeds |

Acceptance uses parsed details, including bounded known-job rechecks, rather than search-card counts. Both the current sample and at least three matching historical samples must contain 10 classified records. Field comparisons require 10 open jobs for optional stored fields or 5 parsed details for parser fields in both the current and at least three historical samples. Country comparisons require at least 10 country observations per historical sample; multi-country listings count once per recognized country. Parser fields are description, industries, locations, posting time, and start date; stored optional fields are industries and start date. Missing optional metadata alone is not a cold-start error.

Per-search comparisons require matching effective settings. Registry volume and parser comparisons also require every enabled search to succeed. Open-dataset profiles always cover all open rows, including on a selected-search run, but require a matching registry baseline. Counts summed across searches are observations, not deduplicated jobs. Profile changes may reflect legitimate availability updates or manually reviewed additions and are warnings only.

A baseline-read, analysis, report-write, or baseline-persistence error fails closed with exit code `1`. The gate does not undo committed search transactions or prevent a separate explicit `render`; do not publish a blocked local collection. Inspect the retained report and compare its scope, sample sizes, and configuration before changing code. Reproduce suspected parsing changes with sanitized offline fixtures, then run the normal validation gates. Do not delete canonical state or disable source authorization to resolve an alert.

## `add-job`

Maintainers can add a known LinkedIn listing without running collection. Independently verify the public source facts first: this offline command validates supplied evidence but cannot authenticate it. The example below is synthetic:

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
- inserts or updates an open row through the repository; rejects a closed row, which must be reopened by valid discovery or a successful availability audit;
- creates no search, search run, or `job_searches` provenance;
- performs no network access and does not require the LinkedIn authorization interlock;
- refreshes the README, search-registry documentation, and all public exports by default.

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

Check canonical state without refreshing generated projections:

```bash
uv run opportunities check-availability --no-render
```

The command requires the LinkedIn authorization interlock and checks at most 250 due job rows by default, including closed rows. Each row becomes due five days after its last non-denial attempt; never-checked rows are eligible immediately. The [availability settings](../getting-started/configuration.md#lifecycle-and-logging) control the interval and cap. The summary reports due rows deferred by the cap; those rows stay unchanged and do not cause a partial-success exit. It requests the public listing first; a successful public page without a closure alert is then followed by guest detail validation. It then applies one transaction:

- successful public-page and detail-page validation keeps the row open or reopens it;
- HTTP `404` or `410` from either request permanently deletes the job and cascading search provenance;
- a scoped public-page “No longer accepting applications” alert also permanently deletes the job;
- authentication failures, rate limits, server errors, malformed responses, and transport failures preserve the row as inconclusive.

The command exits with code `2` when one or more checks are inconclusive without a source-access denial. This includes an [HTTP `301` from an approved numeric public listing](../../../SECURITY.md#public-listing-redirects): the affected row stays unchanged, its destination is never followed or used as evidence, and other checks continue. Confirmed results remain committed, and the default path refreshes the owned README, registry documentation, and all public exports. Any other redirect, authentication failure, rate limit, or access challenge detected by the transport instead returns code `1` and skips projection rendering. Already confirmed results remain in the working database, but automation stops before starting a new scraper or publishing a snapshot. Review source authorization before another run; do not automatically retry a denial. The nightly workflow runs this bounded audit once per day before scraping, opens or updates a tightly scoped README pull request, explicitly dispatches and awaits validation on that generated commit, and only then requests auto-merge. The availability-only workflow can run the same command manually and opens its own validated manual-review pull request.

## `render`

```bash
uv run opportunities render
```

Regenerates every owned projection from canonical SQLite state and the configured search registry.

The README projection includes:

- total open-job count;
- latest successful collection time;
- the public website link;
- a hidden SHA-256 review seal covering every website-visible open row and the exact latest successful collection timestamp;
- at most five internships and five New Grad opportunities ordered by immutable first-seen time, then descending ID text. The generated label says “most recently discovered,” but first-seen time can use approximate source posting age.

The generated registry-layout counts in [`search-registry.md`](../engineering/search-registry.md) are refreshed from `configs/searches/` at the same time. The CSV and JSON downloads are generated from all open rows using the fixed public-field allowlist. Their metadata manifest records the schema version, UTC generation time, counts, and SHA-256 hashes.

The command:

- performs no network access;
- does not modify SQLite;
- writes the owned README regions through atomic replacement;
- refreshes the owned generated registry-layout block in `search-registry.md`;
- atomically replaces each of the three public export files.

> [!IMPORTANT]
> A fresh local database contains no listings. Do not render and commit the preview from empty development state.

Do not edit generated counts, timestamps, opportunity rows, registry-layout counts, or public exports manually.

## `export-public`

```bash
uv run opportunities export-public
```

Generates `open-opportunities.csv`, `open-opportunities.json`, and `dataset-metadata.json` in the configured public-export directory. It reads open SQLite rows, selects only approved public fields, neutralizes spreadsheet formulas in CSV text, and atomically replaces each file. The manifest includes a fresh UTC generation time, schema version, counts, and hashes of the exact download bytes.

This command performs no network access, does not modify SQLite or documentation, and is used by deployment-only automation after restoring reviewed canonical state. Listing rows omit lifecycle timestamps, status, provenance, runs, closure evidence, and diagnostics. See the [download contract](../../users/data/data.md) for the separate row and manifest fields.

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

Use it after migration, collection, or restoration to check the configured pipeline database. In versioned production mode, `stats` does **not** inspect the website's selected `data/current` release; verify the served release and downloads using the [deployment checks](automation.md#post-nightly-production-runbook).

## `validate`

```bash
uv run opportunities validate
```

Checks:

- required database tables;
- the Alembic revision;
- monotonic lifecycle timestamps;
- exact README projection equality with canonical state, including the full-state review seal;
- generated search-registry layout counts against the configured YAML files;
- exact public CSV and JSON equality with the approved fields from open SQLite rows;
- v1 schema compliance for downloads and metadata, including manifest fields, UTC generation time, counts, and hashes.

Validation performs no network access and never repairs state automatically.

Run it only when the configured database contains the representative canonical state expected by the committed generated documentation.

For diagnosis, use [Troubleshooting](troubleshooting.md).

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Command completed successfully |
| `1` | All selected searches failed, the availability audit encountered a source-access denial, validation found an inconsistency, or the requested quality gate blocked or could not complete |
| `2` | Partial scrape, availability audit with inconclusive checks, or rejected command/configuration input |
| `3` | Required database tables are missing or the schema is not at migration head |

After a partial scrape with exit code `2`:

- successful search transactions remain committed;
- failed searches retain diagnostics;
- failed searches do not mutate lifecycle state;
- validation should pass before publication or deployment.

GitHub Actions handling of these codes is documented in [Automation](automation.md#exit-code-handling).

## Command side effects

| Command | LinkedIn network | Writes SQLite | Writes projections |
|---|---:|---:|---:|
| `db-upgrade` | No | Schema only | No |
| `searches` | No | No | No |
| `search-test` | Yes, after authorization gate | No | No |
| `scrape` | Yes, after authorization gate | Yes; optional bounded quality baseline | README + registry docs + public exports after a successful search and no requested quality block |
| `scrape --no-render` | Yes, after authorization gate | Yes; optional bounded quality baseline | No |
| `add-job` | No | Yes | README + registry docs + public exports |
| `add-job --no-render` | No | Yes | No |
| `add-jobs` | No | Yes, one transaction | README + registry docs + public exports |
| `add-jobs --no-render` | No | Yes, one transaction | No |
| `check-availability` | Yes, after authorization gate | Yes | README + registry docs + public exports unless source access is blocked |
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

### Collect without refreshing projections

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
uv run python scripts/database/check_migrations.py
```

Valid slugs and query configuration are documented in the [search registry guide](../engineering/search-registry.md). Complete engineering checks are documented in the [testing guide](../engineering/testing.md#validation-paths).
