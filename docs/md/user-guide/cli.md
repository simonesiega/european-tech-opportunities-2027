# European Tech Opportunities 2027 CLI Reference

[← Documentation](../README.md) · [Installation](../getting-started/installation.md) · [Configuration](../getting-started/configuration.md)

The `opportunities` CLI manages database migrations, search inspection, authorized collection, canonical SQLite state, validation, and generated documentation projections.

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
- [`check-availability`](#check-availability)
- [`render`](#render)
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
| `check-availability` | Check every stored LinkedIn detail page and delete explicit 404/410 rows |
| `render` | Regenerate the bounded README projection from SQLite |
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

Use it after changing search YAML, category mappings, or global limit overrides.

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
7. renders the README unless `--no-render` is set.

A partial run preserves successful search transactions.

A failed search:

- records bounded diagnostics;
- does not apply absence evidence;
- does not increment unavailability confirmations;
- does not close jobs.

Use `--no-render` where canonical state should change without modifying the Git working tree, such as a website-only VPS.

The collection lifecycle is documented in [Architecture](../development/architecture.md#failure-isolation) and [Database lifecycle](../operations/database.md#successful-search-transaction).

## `check-availability`

```bash
uv run opportunities check-availability
```

Check canonical state without updating generated documentation:

```bash
uv run opportunities check-availability --no-render
```

The command requires the LinkedIn authorization interlock and requests the LinkedIn detail page for every job row, including rows currently marked closed. It then applies one transaction:

- a valid HTML response keeps the row open or reopens it;
- HTTP `404` or `410` permanently deletes the job and cascading search provenance;
- authentication failures, rate limits, server errors, malformed responses, and transport failures preserve the row as inconclusive.

The command exits with code `2` when one or more checks are inconclusive. Confirmed results remain committed, and the default path refreshes the README projection. The nightly workflow runs this full audit once per day before scraping and opens or updates one combined pull request for manual review. The availability-only workflow can run the same command manually and opens its own pull request.

## `render`

```bash
uv run opportunities render
```

Regenerates generated documentation from canonical SQLite state.

The README projection includes:

- total open-job count;
- latest successful collection time;
- the public website link;
- at most ten recently posted internships and ten recently posted New Grad positions.

Generated search-registry counts are also updated where owned by the rendering path.

The command:

- performs no network access;
- does not modify SQLite;
- writes the owned README block through atomic replacement.

> [!IMPORTANT]
> A fresh local database contains no listings. Do not render and commit the preview from empty development state.

Do not edit generated rows manually.

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
- generated search-registry documentation counts.

Validation performs no network access and never repairs state automatically.

Run it only when the configured database contains the representative canonical state expected by the committed generated documentation.

For diagnosis, use [Troubleshooting](../operations/troubleshooting.md).

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Command completed successfully |
| `1` | Every selected search failed, or validation found an inconsistency |
| `2` | Partial scrape or availability audit, invalid command input, or configuration rejection |
| `3` | Required database tables are missing or the schema is not at migration head |

After a partial scrape with exit code `2`:

- successful search transactions remain committed;
- failed searches retain diagnostics;
- failed searches do not mutate lifecycle state;
- validation should pass before publication or deployment.

GitHub Actions handling of these codes is documented in [Automation](../operations/automation.md#exit-code-handling).

## Command side effects

| Command | LinkedIn network | Writes SQLite | Writes README |
|---|---:|---:|---:|
| `db-upgrade` | No | Schema only | No |
| `searches` | No | No | No |
| `search-test` | Yes, after authorization gate | No | No |
| `scrape` | Yes, after authorization gate | Yes | Normally |
| `scrape --no-render` | Yes, after authorization gate | Yes | No |
| `check-availability` | Yes, after authorization gate | Yes | Normally |
| `check-availability --no-render` | Yes, after authorization gate | Yes | No |
| `render` | No | No | Yes |
| `stats` | No | No | No |
| `validate` | No | No | No |

## Common command sequences

### Initialize a local database

```bash
uv run opportunities db-upgrade
uv run opportunities searches
uv run opportunities stats
```

A new database is expected to contain no listings.

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

### Regenerate documentation from representative state

```bash
uv run opportunities render
uv run opportunities validate
```

### Verify migrations during development

```bash
uv run opportunities db-upgrade
uv run python scripts/check_migrations.py
```

Valid slugs and query configuration are documented in the [search registry guide](search-registry.md). Complete engineering checks are documented in the [development guide](../development/development.md#validation-paths).
