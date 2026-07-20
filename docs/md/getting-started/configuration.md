# European Tech Opportunities 2027 Configuration Guide

[← Documentation](../README.md) · [Installation](installation.md) · [CLI reference](../user-guide/cli.md)

This guide documents how the Python pipeline and Next.js website load configuration, how overrides are resolved, and which settings control paths, search limits, networking, lifecycle behavior, logging, and source authorization.

The pipeline builds one immutable Pydantic settings object before executing a command. Unknown fields and invalid values fail early instead of being silently ignored.

Complete the [installation guide](installation.md) before configuring a new environment.

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

<div align="center">
<pre>
built-in defaults
↓
.env
↓
settings YAML
↓
process environment
</pre>
</div>

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
| `OPPORTUNITIES_README_PATH` | `README.md` | Existing UTF-8 file containing exactly one opportunity marker pair |
| `OPPORTUNITIES_TARGET_CYCLE` | `2027` | Integer from 2020 through 2100 |
| `OPPORTUNITIES_SETTINGS_FILE` | unset | Selects an optional settings YAML file |

### Search limits

| Variable | Default | Validation and behavior |
|---|---:|---|
| `OPPORTUNITIES_SEARCH_MAX_PAGES` | unset | Global override from 1 through 10 pages |
| `OPPORTUNITIES_SEARCH_MAX_RESULTS` | unset | Global override from 1 through 250 and no greater than pages × 25 |
| `OPPORTUNITIES_SEARCH_MAX_RECHECKS` | unset | Global override from 0 through 250 known-job rechecks |

### HTTP transport and safety

| Variable | Default | Validation and behavior |
|---|---:|---|
| `OPPORTUNITIES_REQUEST_TIMEOUT_SECONDS` | `20` | Overall timeout greater than 0 and at most 120 seconds |
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
| `OPPORTUNITIES_CLOSURE_CONFIRMATION_RUNS` | `2` | Required explicit unavailability confirmations from 1 through 10 |
| `OPPORTUNITIES_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |

Environment strings are converted into their declared types by Pydantic. Invalid configuration exits with code `2` before collection begins.

## Settings YAML

Start from `configs/settings.example.yml`:

```yaml
database_url: sqlite:///data/opportunities.db
readme_path: README.md
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

closure_confirmation_runs: 2
linkedin_crawl_authorized: false
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

- pages replace every enabled search’s `max_pages`;
- results replace every enabled search’s `max_results`;
- when only pages change, existing result limits are capped to page capacity;
- rechecks replace every enabled search’s `max_rechecks`;
- results greater than pages × 25 are rejected.

Review the [search registry guide](../user-guide/search-registry.md#limit-tiers) before changing production limits.

## HTTP policy

The transport retries only:

- connection or transport failures;
- timeouts;
- HTTP `429`;
- HTTP `5xx`.

For zero-based retry number `n`, the base delay is:

```text
retry_backoff_seconds × 2^n
```

A valid `Retry-After` value can add at most 60 seconds.

The transport also enforces:

- the fixed `www.linkedin.com` HTTPS host before any request;
- disabled redirects;
- bounded connection and overall timeouts;
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

The Next.js website uses two runtime or build variables:

| Variable | Default | Purpose |
|---|---|---|
| `OPPORTUNITIES_DATABASE_PATH` | `../data/opportunities.db` | Read-only SQLite file used by server requests |
| `SITE_URL` | `http://localhost:3000` | Canonical public origin used by metadata |

Create the local website environment file:

```bash
cd site
cp .env.example .env.local
```

The production container reads:

```text
/app/data/opportunities.db
```

Production uses:

```dotenv
SITE_URL=https://opportunities2027.simonesiega.com
OPPORTUNITIES_DATABASE_PATH=/app/data/opportunities.db
```

The website must retain read-only database access.

Authentication, user-provided content, write APIs, or other mutation paths require an explicit architecture and security review.

## Authorization interlocks

The local application and Docker pipeline use:

```text
OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true
```

The GitHub nightly, scrape-only, and availability-only workflows use the repository variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

These values are separate because they protect different execution environments.

> [!IMPORTANT]
> Neither value grants permission to access LinkedIn. They only record an operator decision after express authorization has already been obtained.

Keep both false or unset when authorization is absent, uncertain, expired, or withdrawn. Disable them immediately when authorization changes.

Workflow behavior is documented in [Automation](../operations/automation.md#collection-authorization), and the complete security boundary in [`SECURITY.md`](../../../SECURITY.md).

## Environment-specific guidance

### Local development

- use `.env`;
- keep LinkedIn collection disabled;
- use the default local SQLite path;
- use fixture-based offline tests;
- do not render the committed README from empty state.

### Continuous integration

- use explicit workflow environment values;
- use frozen dependency installs;
- keep validation workflows offline;
- expose only the variables required by each job;
- never enable collection in normal CI.

### Production collection

- store authorization state in the protected execution environment;
- keep request limits conservative;
- preserve the one-writer model;
- back up SQLite before recovery or rebuild operations;
- configure the restricted SFTP-only VPS snapshot account and review snapshot, artifact, cache, deployment, and secret visibility.

### Production website

- mount SQLite read-only;
- set `SITE_URL` to the canonical HTTPS origin;
- do not expose collector authorization variables to the website;
- never place secrets in client-visible `NEXT_PUBLIC_*` values.

## Validate configuration

Verify the effective Python configuration:

```bash
uv run opportunities stats
uv run opportunities searches
```

Validate a specific settings YAML:

```bash
uv run opportunities --settings configs/settings.local.yml stats
```

A configuration error reports the invalid field or value and exits before network access.

For symptom-based diagnosis and safe recovery, use the [troubleshooting guide](../operations/troubleshooting.md#configuration-failures).
