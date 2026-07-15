# Configuration

[← README](../README.md)

The CLI uses one immutable Pydantic `Settings` object. Configuration is validated before a command runs, and unknown YAML fields are rejected.

## Loading and precedence

Values are applied in this order, from lowest to highest priority:

```text
built-in defaults
        ↓
.env
        ↓
optional settings YAML
        ↓
process environment
```

Process environment values always win.

The optional YAML path is selected in this order:

1. CLI option: `internships --settings <path> <command>`;
2. process `INTERNSHIPS_SETTINGS_FILE`;
3. `.env` value `INTERNSHIPS_SETTINGS_FILE`;
4. `configs/settings.yml` when that file exists;
5. no YAML file.

A selected YAML path must exist and contain a mapping.

Relative database and filesystem paths resolve from the command's working directory. Run commands from the repository root unless every path is absolute.

## Recommended setup

Copy the documented template:

```bash
cp .env.example .env
```

Windows Command Prompt:

```bat
copy .env.example .env
```

Keep local values in `.env`; it is ignored by Git. For advanced structured settings, copy `configs/settings.example.yml` to `configs/settings.yml`, which is also ignored.

Do not duplicate the same value across `.env`, YAML, and process environment unless you intentionally rely on precedence.

## Essential settings

```dotenv
INTERNSHIPS_DATABASE_URL=sqlite:///data/internships.db
INTERNSHIPS_README_PATH=README.md
INTERNSHIPS_SEARCH_CONFIG_DIR=configs/searches
INTERNSHIPS_CATEGORY_CONFIG_PATH=configs/categories.yml
INTERNSHIPS_TARGET_CYCLE=2027
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=false
```

`INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED` is an operator interlock, not legal or technical permission. Leave it false until LinkedIn has granted express authorization.

## Complete environment reference

| Environment variable | Setting field | Default | Validation and behavior |
|---|---|---:|---|
| `INTERNSHIPS_DATABASE_URL` | `database_url` | `sqlite:///data/internships.db` | Must contain `://`. SQLite is the supported canonical store. |
| `INTERNSHIPS_README_PATH` | `readme_path` | `README.md` | Must point to an existing README with exactly one generated marker pair when rendering. |
| `INTERNSHIPS_SEARCH_CONFIG_DIR` | `search_config_dir` | `configs/searches` | Must be a directory when searches are loaded; scanned recursively for YAML. |
| `INTERNSHIPS_CATEGORY_CONFIG_PATH` | `category_config_path` | `configs/categories.yml` | Must be valid classification-rule YAML when collection/classification runs. |
| `INTERNSHIPS_TARGET_CYCLE` | `target_cycle` | `2027` | Integer from 2020 through 2100. |
| `INTERNSHIPS_SEARCH_MAX_PAGES` | `search_max_pages` | unset | Optional integer 1–10 applied to every search. |
| `INTERNSHIPS_SEARCH_MAX_RESULTS` | `search_max_results` | unset | Optional integer 1–250 applied to every search; cannot exceed effective pages × 25. |
| `INTERNSHIPS_SEARCH_MAX_RECHECKS` | `search_max_rechecks` | unset | Optional integer 0–250 applied to every search. Zero disables known-job rechecks for that run. |
| `INTERNSHIPS_REQUEST_TIMEOUT_SECONDS` | `request_timeout_seconds` | `20` | Greater than 0 and at most 120 seconds. |
| `INTERNSHIPS_CONNECT_TIMEOUT_SECONDS` | `connect_timeout_seconds` | `10` | Greater than 0 and at most 60 seconds. |
| `INTERNSHIPS_MAX_RETRIES` | `max_retries` | `3` | Integer 0–10; retries timeout, transport, HTTP 429, and HTTP 5xx failures. |
| `INTERNSHIPS_RETRY_BACKOFF_SECONDS` | `retry_backoff_seconds` | `0.5` | Number 0–30; exponential base delay. |
| `INTERNSHIPS_RATE_LIMIT_SECONDS` | `rate_limit_seconds` | `2.0` | Number 0–60; minimum interval between request starts to the same host. |
| `INTERNSHIPS_MAX_CONCURRENCY` | `max_concurrency` | `3` | Integer 1–16; bounds concurrent searches, HTTP connections, and keep-alive connections. |
| `INTERNSHIPS_MAX_RESPONSE_BYTES` | `max_response_bytes` | `15000000` | Integer 10,000–100,000,000; enforced against declared and actual body size. |
| `INTERNSHIPS_CLOSURE_CONFIRMATION_RUNS` | `closure_confirmation_runs` | `2` | Integer 1–10; explicit detail-page unavailable confirmations required per active association. |
| `INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED` | `linkedin_crawl_authorized` | `false` | Must remain false without express LinkedIn permission. Enforced by CLI and transport. |
| `INTERNSHIPS_USER_AGENT` | `user_agent` | project/version URL | String 20–300 characters. Identifies authorized requests. |
| `INTERNSHIPS_LOG_LEVEL` | `log_level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`; normalized to uppercase. |
| `INTERNSHIPS_SETTINGS_FILE` | settings-file selector | unset | Optional path to advanced YAML; it is not itself a `Settings` field. |

Pydantic parses environment strings into the declared types. Invalid values stop the CLI with configuration exit code `2` before collection starts.

## YAML settings

The YAML format uses field names without the `INTERNSHIPS_` prefix:

```yaml
database_url: sqlite:///data/internships.db
readme_path: README.md
search_config_dir: configs/searches
category_config_path: configs/categories.yml
target_cycle: 2027
request_timeout_seconds: 20
connect_timeout_seconds: 10
max_retries: 3
retry_backoff_seconds: 0.5
rate_limit_seconds: 2.0
max_concurrency: 3
max_response_bytes: 15000000
closure_confirmation_runs: 2
linkedin_crawl_authorized: false
user_agent: european-tech-internships-2027/0.1 (+https://github.com/simonesiega/european-tech-internships-2027)
log_level: INFO
```

Start from [`configs/settings.example.yml`](../configs/settings.example.yml). Do not commit `configs/settings.yml`.

Use an explicit file for one invocation:

```bash
uv run internships --settings configs/settings.local.yml stats
```

The global `--settings` option appears before the subcommand.

## Search-limit overrides

Search YAML files contain evidence-based per-query limits. Leave global overrides unset for normal production behavior.

For a deliberately uniform diagnostic run:

```dotenv
INTERNSHIPS_SEARCH_MAX_PAGES=2
INTERNSHIPS_SEARCH_MAX_RESULTS=50
INTERNSHIPS_SEARCH_MAX_RECHECKS=10
```

Effective behavior:

- global pages replace each file's `max_pages`;
- global results replace each file's `max_results`;
- if pages are overridden but results are not, file results are capped to the new page capacity;
- global rechecks replace each file's `max_rechecks`;
- effective results greater than effective pages × 25 are rejected.

Set page and result overrides together to avoid creating an invalid combination for low-page searches.

See [Search registry](search-registry.md) for per-query tiers and tuning.

## HTTP controls

### Timeouts

`request_timeout_seconds` configures the overall HTTPX timeout, while `connect_timeout_seconds` separately limits connection establishment. A timeout becomes a sanitized retryable `FetchError`.

### Pacing and concurrency

`max_concurrency` limits parallel searches and the HTTP connection pool. `rate_limit_seconds` spaces request starts to the same host even when several searches run concurrently.

Increasing concurrency does not remove host pacing. Do not increase either value merely to shorten a run; authorization may include stricter limits than the software defaults.

### Retries

The transport retries only:

- timeout errors;
- HTTP transport errors;
- HTTP `429`;
- HTTP `5xx`.

For a zero-based retry index `n`, beginning with `n = 0`, the delay is:

```text
retry_backoff_seconds × 2^n
```

A valid `Retry-After` response is honored with a maximum additional sleep of 60 seconds. Other non-2xx responses are not retried by default.

### Response bounds

`max_response_bytes` is checked against `Content-Length` when present and against the actual body after reading. Oversized responses are rejected before parsing. Only HTML and plain-text content types are accepted.

## Database URL

The supported default is a repository-relative SQLite file:

```dotenv
INTERNSHIPS_DATABASE_URL=sqlite:///data/internships.db
```

An absolute Unix path uses four slashes:

```dotenv
INTERNSHIPS_DATABASE_URL=sqlite:////srv/internships/data/internships.db
```

For Windows, SQLAlchemy accepts a forward-slash path such as:

```dotenv
INTERNSHIPS_DATABASE_URL=sqlite:///C:/data/internships.db
```

The engine creates the parent directory for file-backed SQLite URLs and enables foreign-key enforcement on every SQLite connection.

Do not point two independent collection processes at the same SQLite database. The supported model is one writer.

## README path

The README renderer requires:

- an existing UTF-8 file;
- exactly one `BEGIN INTERNSHIPS` HTML-comment marker;
- exactly one `END INTERNSHIPS` HTML-comment marker;
- write permission in the parent directory for atomic replacement.

Do not repeat the complete marker comments elsewhere in README text or examples. `validate` compares the generated block byte-for-byte after surrounding whitespace normalization.

## Authorization configuration

Local authorized operation:

```dotenv
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true
```

GitHub Actions uses a separate repository variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

Docker Compose passes the same `INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED` setting into the service.

None of these values grants permission. They should be enabled only after authorization has been documented for the relevant operator/environment. See [Automation](automation.md) and [Security](../SECURITY.md).

## Safe inspection

Show effective search limits without network access:

```bash
uv run internships searches
```

Show parsed settings carefully in your own debugging code, but never print or commit an entire `.env`. Although this project does not require LinkedIn credentials, local environment files can contain unrelated secrets.
