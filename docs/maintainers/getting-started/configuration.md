# Configuration reference

[← Maintainer handbook](../README.md) · [Local setup](setup.md) · [CLI reference](../operations/cli.md) · [Security policy](../../../SECURITY.md)

Configure the Python pipeline and Next.js website using the paths, precedence rules, request limits, lifecycle settings, and authorization interlocks below.

The pipeline builds one immutable Pydantic settings object before executing a command. Unknown YAML fields and invalid setting values fail early instead of being silently ignored. Only supported `OPPORTUNITIES_*` environment variables are loaded; unrelated variables are ignored.

Complete [local setup](setup.md) before configuring a new environment.

## Contents

- [Configuration precedence](#configuration-precedence)
- [Settings-file selection](#settings-file-selection)
- [Core local configuration](#core-local-configuration)
- [Environment reference](#environment-reference)
- [Settings YAML](#settings-yaml)
- [Search-limit overrides](#search-limit-overrides)
- [HTTP policy](#http-policy)
- [Database paths](#database-paths)
- [Website settings](#website-settings)
- [Authorization interlocks](#authorization-interlocks)
- [Environment-specific guidance](#environment-specific-guidance)
- [Validate configuration](#validate-configuration)

## Configuration precedence

Values are applied from lowest to highest priority:

```text
built-in defaults
↓
.env
↓
settings YAML
↓
process environment
(highest priority)
```

A process-environment value overrides the same setting from YAML, `.env`, or built-in defaults.

Prefer one clear source for each setting. Define the same value in several layers only when the override is intentional and documented.

## Settings-file selection

The optional settings YAML is selected in this order:

1. global CLI option `opportunities --settings <path> <command>`;
2. process variable `OPPORTUNITIES_SETTINGS_FILE`;
3. `.env` value `OPPORTUNITIES_SETTINGS_FILE`;
4. `configs/settings.yml`, when present.

The global option must appear before the subcommand:

```bash
uv run opportunities --settings configs/settings.local.yml stats
```

Relative paths resolve from the current working directory. Run commands from the repository root unless every configured path is absolute.

## Core local configuration

A typical local `.env` contains:

```dotenv
OPPORTUNITIES_DATABASE_URL=sqlite:///data/opportunities.db
OPPORTUNITIES_README_PATH=README.md
OPPORTUNITIES_PUBLIC_EXPORT_DIR=data/exports
OPPORTUNITIES_SEARCH_CONFIG_DIR=configs/searches
OPPORTUNITIES_CATEGORY_CONFIG_PATH=configs/categories.yml
OPPORTUNITIES_TARGET_CYCLE=2027
OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=false
```

`configs/categories.yml` defines separate title keywords for internships and New Grad roles. Accepted employment types are fixed to `internship` and `new-grad`; source-site full-time, part-time, or contract criteria are not published as employment types.

`.env` and `configs/settings.yml` are ignored by Git, but may still contain operationally sensitive values.

Do not commit, paste, or attach them to public issues.

## Environment reference

### Paths and classification

| Variable | Default | Validation and behavior |
|---|---:|---|
| `OPPORTUNITIES_DATABASE_URL` | `sqlite:///data/opportunities.db` | Valid SQLite SQLAlchemy URL; other database backends are rejected |
| `OPPORTUNITIES_SEARCH_CONFIG_DIR` | `configs/searches` | Recursive YAML search-registry directory |
| `OPPORTUNITIES_CATEGORY_CONFIG_PATH` | `configs/categories.yml` | Classification-rules file |
| `OPPORTUNITIES_README_PATH` | `README.md` | Existing UTF-8 file containing exactly one opportunity-count marker pair and one opportunity-preview marker pair |
| `OPPORTUNITIES_PUBLIC_EXPORT_DIR` | `data/exports` | Directory for generated `open-opportunities.csv`, `open-opportunities.json`, and `dataset-metadata.json`; each file is replaced atomically |
| `OPPORTUNITIES_TARGET_CYCLE` | `2027` | Integer from 2020 through 2100 |
| `OPPORTUNITIES_SETTINGS_FILE` | unset | Selects an optional settings YAML file |

The 2027 publication floor (May 1, 2026) and `date_posted: cycle` search window are fixed policy. Changing `OPPORTUNITIES_TARGET_CYCLE` alone does not retarget the whole project to a later hiring cycle; review the classifier, search registry, tests, and public copy together before a rollover.

### Search limits

| Variable | Default | Validation and behavior |
|---|---:|---|
| `OPPORTUNITIES_SEARCH_MAX_PAGES` | unset | Global override from 1 through 10 pages |
| `OPPORTUNITIES_SEARCH_MAX_RESULTS` | unset | Global override from 1 through 250 and no greater than pages × 25 |
| `OPPORTUNITIES_SEARCH_MAX_RECHECKS` | unset | Global override from 0 through 250 known-job rechecks |

### HTTP transport and safety

| Variable | Default | Validation and behavior |
|---|---:|---|
| `OPPORTUNITIES_REQUEST_TIMEOUT_SECONDS` | `20` | HTTPX read, write, and pool timeout greater than 0 and at most 120 seconds per operation; not a total-request deadline |
| `OPPORTUNITIES_CONNECT_TIMEOUT_SECONDS` | `10` | Connection timeout greater than 0 and at most 60 seconds |
| `OPPORTUNITIES_MAX_RETRIES` | `3` | Retry count from 0 through 10 |
| `OPPORTUNITIES_RETRY_BACKOFF_SECONDS` | `0.5` | Exponential base delay from 0 through 30 seconds |
| `OPPORTUNITIES_RATE_LIMIT_SECONDS` | `2.0` | Minimum same-host request-start interval from 0 through 60 seconds |
| `OPPORTUNITIES_MAX_CONCURRENCY` | `3` | Concurrent searches and connections from 1 through 16 |
| `OPPORTUNITIES_MAX_RESPONSE_BYTES` | `15000000` | Declared and actual response limit from 10,000 through 100,000,000 bytes |
| `OPPORTUNITIES_USER_AGENT` | project identifier | Identifying request value from 20 through 300 characters |
| `OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED` | `false` | LinkedIn-request interlock; it does not grant permission |

### Lifecycle and logging

| Variable | Default | Validation and behavior |
|---|---:|---|
| `OPPORTUNITIES_AVAILABILITY_INTERVAL_DAYS` | `5` | Minimum days between non-denial audit attempts, from 1 through 365 |
| `OPPORTUNITIES_AVAILABILITY_MAX_JOBS` | `50` | Maximum due jobs selected per audit, from 1 through 1,000; excess jobs remain deferred |
| `OPPORTUNITIES_CLOSURE_CONFIRMATION_RUNS` | `2` | Required explicit unavailability confirmations from 1 through 10 |
| `OPPORTUNITIES_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |

Environment strings are converted into their declared types by Pydantic. Invalid configuration exits with code `2` before collection begins.

## Settings YAML

Start from `configs/settings.example.yml`. The example below mirrors the supported settings in that file:

```yaml
database_url: sqlite:///data/opportunities.db
readme_path: README.md
public_export_dir: data/exports
search_config_dir: configs/searches
category_config_path: configs/categories.yml
target_cycle: 2027

request_timeout_seconds: 20
connect_timeout_seconds: 10
max_retries: 3
retry_backoff_seconds: 0.5
rate_limit_seconds: 2
max_concurrency: 3
max_response_bytes: 15000000

availability_interval_days: 5
availability_max_jobs: 50
closure_confirmation_runs: 2
linkedin_crawl_authorized: false
user_agent: european-tech-opportunities-2027/1.0.0 (+https://github.com/simonesiega/european-tech-opportunities-2027)
log_level: INFO
```

Use a settings file explicitly:

```bash
uv run opportunities --settings configs/settings.local.yml stats
```

YAML keys are validated. Unknown fields and invalid values fail before command execution.

Do not duplicate identical values across `.env`, YAML, and process variables unless the precedence is deliberate.

## Search-limit overrides

Individual search files contain evidence-based limits. Global overrides exist for bounded diagnostics and controlled operational experiments, not as a replacement for tuning the search registry.

Example:

```dotenv
OPPORTUNITIES_SEARCH_MAX_PAGES=2
OPPORTUNITIES_SEARCH_MAX_RESULTS=50
OPPORTUNITIES_SEARCH_MAX_RECHECKS=10
```

Rules:

- pages replace every configured search's `max_pages`;
- results replace every configured search's `max_results`;
- when only pages change, existing result limits are capped to page capacity;
- rechecks replace every configured search's `max_rechecks`;
- results greater than pages × 25 are rejected.

Overrides do not enable disabled searches; collection still selects only enabled entries. Review the [search registry guide](../engineering/search-registry.md#limit-tiers) before changing production limits.

## HTTP policy

The transport retries only:

- connection or transport failures;
- timeouts;
- HTTP `5xx`.

For zero-based retry number `n`, the base delay is:

```text
retry_backoff_seconds × 2^n
```

The retry delay is the greater of the exponential backoff and a valid `Retry-After` value, capped at 60 seconds. HTTP redirects outside the [public-listing `301` exception](../../../SECURITY.md#public-listing-redirects), `401`, `403`, and `429` stop further requests through the same fetcher without retrying; requests already in flight may finish. A detected denial remains a stop condition even if closing its response fails. Operators must review access before another collection run.

The transport also enforces:

- the fixed `www.linkedin.com` HTTPS host before any request;
- disabled redirects;
- direct requests from its managed client, ignoring ambient proxy variables;
- rejection of preconfigured Cookie headers and source response cookies;
- bounded waits for connection, read, write, and pool operations, not a wall-clock deadline for the complete response;
- bounded concurrency and same-host pacing;
- response-size checks before and after reading;
- HTML or plain-text content-type validation;
- sanitized errors without response-body logging.

Increasing concurrency does not disable per-host pacing.

Do not increase concurrency, retries, or request limits to bypass throttling, access blocks, or challenge pages. The complete source-access boundary is defined in [`SECURITY.md`](../../../SECURITY.md).

## Database paths

### Relative SQLite path

```dotenv
OPPORTUNITIES_DATABASE_URL=sqlite:///data/opportunities.db
```

### Absolute Linux path

```dotenv
OPPORTUNITIES_DATABASE_URL=sqlite:////srv/opportunities/opportunities.db
```

### Absolute Windows path

```dotenv
OPPORTUNITIES_DATABASE_URL=sqlite:///C:/data/opportunities.db
```

Only SQLite URLs are supported. The engine creates the parent directory and enables SQLite foreign keys.

Do not run independent writers against the same canonical SQLite file. The website opens the database read-only.

Schema, migrations, backup, restoration, and lifecycle rules belong to the [database lifecycle guide](../operations/database.md).

## Website settings

The Next.js website uses these runtime or build variables:

| Variable | Default | Purpose |
|---|---|---|
| `OPPORTUNITIES_DATABASE_PATH` | `../data/opportunities.db` | Read-only SQLite file when versioned mode is disabled |
| `OPPORTUNITIES_PUBLIC_EXPORT_DIR` | `../data/exports` | Read-only generated CSV/JSON and dataset metadata directory when versioned mode is disabled |
| `OPPORTUNITIES_SCHEMA_PATH` | `../schemas/opportunities-v1.schema.json` | Fixed read-only v1 schema file served at `/schemas/opportunities-v1.schema.json`; the site image sets this to its copy of the repository source |
| `OPPORTUNITIES_RELEASE_ROOT` | unset or empty | When nonempty, resolve `<root>/current` once per server operation and read the database or exports from that release; an invalid or missing pointer fails closed, without using the legacy paths |
| `SITE_URL` | `http://localhost:3000` | HTTP(S) origin used by metadata, structured data, robots, and the sitemap; credentials, paths, queries, fragments, and the legacy redirect hostname are rejected. The production hostname `techopportunities.eu` requires the exact HTTPS origin (no custom port). |

Create the local website environment file:

```bash
cd site
cp .env.example .env.local
```

For local development, set the values in `site/.env.local` to the local origin and database path:

```dotenv
SITE_URL=http://localhost:3000
OPPORTUNITIES_DATABASE_PATH=../data/opportunities.db
OPPORTUNITIES_PUBLIC_EXPORT_DIR=../data/exports
```

`SITE_URL` falls back to `http://localhost:3000` when unset. Unless `OPPORTUNITIES_RELEASE_ROOT` is set, the database and export paths fall back to `../data/opportunities.db` and `../data/exports` respectively.

After the [coordinated production rollout](../operations/automation.md#coordinated-first-rollout-and-rollback), the container uses:

```dotenv
SITE_URL=https://techopportunities.eu
OPPORTUNITIES_RELEASE_ROOT=/app/data
OPPORTUNITIES_SCHEMA_PATH=/app/schemas/opportunities-v1.schema.json
```

For each directory or download request, the site selects a release once and reads its database or exports through `/app/data/current/`. A page and a later download may select different releases during a cutover. Compose still supplies the legacy fixed-path variables for local development and migration; setting `OPPORTUNITIES_RELEASE_ROOT` takes precedence over both. The site must retain a read-only bind mount containing **both** `current` and `releases/`. Do not enable versioned mode until the first release has been deployed and verified.

Authentication, user-provided content, write APIs, or other mutation paths require an explicit architecture and security review.

## Authorization interlocks

The local application and Docker pipeline use:

```text
OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true
```

The GitHub nightly, scrape-only, and availability-only workflows use the non-secret repository variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

VPS credentials are not repository variables or repository-level secrets. Production automation reads them from the main-only `canonical-state` and `production` GitHub environments described in the [automation guide](../operations/automation.md#protected-environments-and-repository-settings).

These values are separate because they protect different execution environments.

> [!IMPORTANT]
> Neither value grants permission to access LinkedIn. They only record an operator decision after express authorization has already been obtained.

Keep both false or unset when authorization is absent, uncertain, expired, or withdrawn. Disable them immediately when authorization changes.

Workflow behavior is documented in [Automation](../operations/automation.md#collection-authorization), and the complete security boundary in [`SECURITY.md`](../../../SECURITY.md).

## Environment-specific guidance

### Local development

- Use `.env`.
- Keep LinkedIn collection disabled.
- Use the default local SQLite path.
- Use fixture-based offline tests.
- Do not render the committed README from empty state.

### Continuous integration

- Use explicit workflow environment values.
- Use frozen dependency installs.
- Keep validation workflows offline.
- Expose only the variables required by each job.
- Never enable collection in normal CI.

### Production collection

- Keep the operator authorization attestation in the `LINKEDIN_CRAWL_AUTHORIZED` repository variable.
- Keep VPS credentials only in the main-only `canonical-state` and `production` GitHub environments, never at repository scope.
- Allow `canonical-state` to run unattended for the nightly schedule and require approval on `production` when practical.
- Keep request limits conservative.
- Preserve the one-writer model.
- Back up SQLite before recovery or rebuild operations.
- Configure the restricted SFTP-only VPS snapshot account, keep canonical SQLite out of Actions cache and artifacts, and review deployment and secret visibility.

### Production website

- Mount SQLite read-only.
- Set `SITE_URL` to the canonical HTTPS origin.
- Do not expose collector authorization variables to the website.
- Never place secrets in client-visible `NEXT_PUBLIC_*` values.

## Validate configuration

Verify that the effective Python configuration loads and that the expected search registry and database are selected:

```bash
uv run opportunities stats
uv run opportunities searches
```

Validate a specific settings YAML:

```bash
uv run opportunities --settings configs/settings.local.yml stats
```

A configuration error reports a sanitized diagnostic and exits before network access.

For symptom-based diagnosis and safe recovery, use the [troubleshooting guide](../operations/troubleshooting.md#configuration-failures).
