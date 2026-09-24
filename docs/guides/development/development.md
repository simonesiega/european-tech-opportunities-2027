# European Tech Opportunities 2027 Development Guide

[← Documentation hub](../../README.md) · [Architecture](architecture.md) · [Contributing](../../../CONTRIBUTING.md) · [Security policy](../../../SECURITY.md)

This is the canonical development guide for the project. It covers the local engineering workflow, repository structure, coding standards, tests, fixtures, and validation paths. Contribution policy and pull-request requirements live in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md).

## Contents

- [Toolchain](#toolchain)
- [Repository layout](#repository-layout)
- [Development workflow](#development-workflow)
- [Make commands](#make-commands)
- [Validation paths](#validation-paths)
- [Code style](#code-style)
- [Testing](#testing)
- [Fixtures and live tests](#fixtures-and-live-tests)
- [README and documentation changes](#readme-and-documentation-changes)
- [Final review](#final-review)

## Toolchain

- Python 3.12 and `uv` 0.11.6;
- Pydantic, HTTPX, Beautiful Soup, SQLAlchemy, Alembic, Typer, and Rich;
- pytest with branch coverage and microbenchmarks, Ruff, and strict mypy;
- Node.js 22.13 or newer with unflagged `node:sqlite` support, Bun 1.4.2, strict TypeScript, Tailwind CSS 4, ESLint, Prettier, and Next.js 16;
- GNU Make for optional command shortcuts, and Docker for container and production-path validation.

These versions define the supported local and CI development environment. Container build and runtime versions are pinned independently; the [Docker guide](../operations/docker.md#image-targets) and root `Dockerfile` are authoritative for container versions.

Install the locked dependencies:

```bash
uv sync --frozen --dev
cd site
bun install --frozen-lockfile
bunx playwright install chromium
cd ..
```

Normal tests and builds require no LinkedIn access. First-time setup belongs in [Installation](../getting-started/installation.md), and runtime settings in [Configuration](../getting-started/configuration.md).

## Repository layout

```text
.
├── .github/actions/         # repository-owned composite CI setup
├── .github/workflows/       # validation, collection, maintenance
├── configs/                 # classification and search YAML
├── data/                    # ignored SQLite runtime state
├── docs/                    # Markdown guides and visual assets
├── migrations/              # Alembic history
├── scripts/                 # operational helpers and validation checks
├── site/                    # Next.js website and Playwright tests
├── src/opportunities/       # Python package
├── tests/                   # unit, integration, and fixtures
├── CONTRIBUTING.md           # contributor workflow and project contracts
├── PRIVACY.md                # website visitor-data and analytics disclosure
├── SECURITY.md               # security reporting and trust boundaries
├── Makefile                  # development and validation shortcuts
├── README.md                 # public project overview and generated previews
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

Component ownership and dependency direction are defined in [Architecture](architecture.md#component-map).

## Development workflow

<div align="center">
<pre>
reproduce offline
↓
add or update a failing test
↓
implement the smallest robust change
↓
run focused checks
↓
run every affected validation path
↓
update the canonical documentation
↓
review the diff for secrets and generated state
</pre>
</div>

Keep pull requests focused. Avoid combining unrelated parser, schema, search, website, deployment, and formatting changes.

## Make commands

GNU Make provides the shortcuts below. On Windows or another environment without Make, use the equivalent `uv` commands in [Validation paths](#validation-paths).

| Command | Purpose |
|---|---|
| `make install` | Install Python development dependencies |
| `make lock` | Verify that `uv.lock` matches project metadata |
| `make migrate` | Upgrade the configured local database |
| `make render` | Regenerate the README, registry documentation, and public CSV/JSON projections from representative state |
| `make validate` | Validate SQLite state and every generated projection |
| `make searches` | Inspect the effective search registry |
| `make stats` | Inspect aggregate database state |
| `make format` | Apply Ruff formatting and safe fixes |
| `make lint` | Run Ruff formatting and lint checks |
| `make typecheck` | Run strict mypy |
| `make test` | Run offline functional pytest |
| `make coverage` | Enforce critical-path coverage, write reports, and refresh README metrics |
| `make benchmark` | Measure offline LinkedIn parsing and classification performance |
| `make test-live` | Explicitly select authorization-gated live tests |
| `make migrations` | Check Alembic and ORM consistency |
| `make docs` | Validate documentation links, images, and anchors |
| `make check` | Run the main Python and documentation quality gate |

> [!IMPORTANT]
> A fresh database contains no listings. Do not render and commit the README preview from empty local state.

## Validation paths

Run every validation path affected by the change. `make check` covers the Python and documentation quality gate; website and container validation are separate. Use the full cross-project sequence before releases or for changes spanning multiple components.

### Python and documentation

```bash
make check
```

Equivalent checks:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run python -c "from pathlib import Path; Path('quality-reports').mkdir(exist_ok=True)"
uv run pytest -m "not live and not performance" --cov \
  --cov-report=term-missing \
  --cov-report=xml:quality-reports/coverage.xml \
  --cov-report=json:quality-reports/coverage.json \
  --cov-report=html:quality-reports/coverage-html
uv run python scripts/coverage_docs.py
uv run python scripts/check_migrations.py
uv run python scripts/check_docs.py
git diff --check
```

Run `uv build` when changing packaging, dependencies, metadata, entry points, or release behavior.

### Website validation

```bash
cd site
bun run ci
```

This verifies Prettier, ESLint, strict TypeScript, the production Next.js build, Bun unit tests, and Playwright browser behavior in Chromium against a temporary synthetic SQLite fixture under `site/tests/e2e/.tmp/`. Playwright also runs axe-core WCAG 2.0, 2.1, and 2.2 A/AA scans for the normal, filtered, empty-result, and dark-mode directory states. The fixture and test artifacts are ignored by Git.

Run a focused browser test with:

```bash
cd site
bun run test:e2e -- --grep "shareable URL"
```

The website CI workflow installs Chromium before running this path.

### Database migrations

```bash
uv run opportunities db-upgrade
uv run python scripts/check_migrations.py
```

Test a fresh database and, when existing state changes, a representative backup. Migration design and recovery belong to [Database lifecycle](../operations/database.md#migrations).

### README, public exports, and generated documentation

Do not render from an empty database and commit the result.

With representative canonical state:

```bash
uv run opportunities render
uv run opportunities validate
uv run pytest tests/integration/test_readme.py -q
```

Generated files must be updated through their owning commands rather than edited manually. Public exports are written under the configured export directory and must contain only the approved field allowlist.

### Containers

```bash
docker compose config
docker compose build
docker compose run --rm opportunities --help
```

Run affected smoke tests when changing image stages, runtime users, mounts, volumes, SQLite paths, permissions, or standalone website output. Operational container procedures belong to [Docker](../operations/docker.md).

GitHub Actions changes must also pass the pinned `actionlint` check in `docker-ci.yml`. VPS restore/deployment shell tests and release-pointer tests require Linux and are skipped on Windows; run them in Linux CI (or an isolated Linux container) before rollout. Docker smoke tests must use disposable synthetic state, not local canonical data. For canonical-state automation, review the operator wrapper, called workflow, protected environment, any sanitized handoff artifact, and referenced shell script together. Keep repository write and validation-dispatch permissions confined to the README pull-request job, keep VPS secrets in main-only environments, and never place canonical SQLite in Actions cache or artifacts.

### Full cross-project validation

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run python -c "from pathlib import Path; Path('quality-reports').mkdir(exist_ok=True)"
uv run pytest -m "not live and not performance" --cov \
  --cov-report=term-missing \
  --cov-report=xml:quality-reports/coverage.xml \
  --cov-report=json:quality-reports/coverage.json \
  --cov-report=html:quality-reports/coverage-html
uv run python scripts/coverage_docs.py
uv run pytest tests/benchmarks --benchmark-only
uv run python scripts/check_migrations.py
uv run python scripts/check_docs.py
cd site && bun run ci && cd ..
docker compose config
git diff --check
```

## Code style

### Python

- Use Python 3.12 syntax, UTF-8, LF endings, and the configured Ruff line length.
- Prefer precise domain models and protocols over broad `Any`.
- Use UTC-aware datetimes at domain boundaries.
- Validate external input and reject unknown fields.
- Keep functions explicit and repository transactions short.
- Keep SQL writes inside repository methods and migrations.
- Sanitize errors; never expose response bodies, credentials, or environment dumps.
- Avoid speculative abstractions and broad lint or type suppressions.

### Website code style

- Keep server and SQLite access under `site/src/lib`.
- Keep browser interaction in client components.
- Keep SQLite read-only and TypeScript strict.
- Use Tailwind utility classes for component styling; keep `globals.css` limited to Tailwind import, shared tokens, theme state, and base document rules.
- Preserve semantic HTML, keyboard access, responsive layouts, and validated HTTPS links.
- Do not add lifecycle mutation APIs, forms, authentication, or user-provided content without architecture and security review.

## Testing

Tests should assert observable behavior rather than internal execution order.

Use temporary paths, fixed UTC timestamps, synthetic IDs, injected clients, and minimal sanitized fixtures.

Unit coverage includes:

- configuration and search-registry validation;
- normalization and classifier decisions;
- HTTP authorization, pacing, retries, timeouts, and response bounds;
- LinkedIn card/detail parsing, pagination, and rechecks;
- path utilities and migration idempotency.

Integration coverage includes:

- CLI preconditions and exit codes;
- persistence and failure isolation;
- provenance and monotonic timestamps;
- closure confirmation and rediscovery;
- README and public-export rendering and validation;
- ORM and Alembic agreement.

`make coverage` measures branch coverage for classification, collection orchestration, availability auditing, and repository lifecycle state. The combined threshold is 85%; terminal, XML, JSON, and HTML reports are written under the ignored `quality-reports/` directory.

The command also refreshes the generated coverage table in the root README from the JSON report, so it may intentionally modify `README.md`. CI requires the committed metrics to match its report, publishes the reports as a 30-day artifact, and includes the coverage table in its job summary. The current measured values are summarized in the root [Python quality baseline](../../../README.md#python-quality-baseline).

`make benchmark` runs two offline microbenchmarks against representative fixtures: LinkedIn search-page parsing and a complete classifier decision. Benchmark JSON is written to `quality-reports/benchmark.json` and published with the CI quality reports. Results are intended for trend comparison across equivalent runners, not as portable absolute timing guarantees.

Website changes must preserve read-only access, empty state, shareable URL filters, search, sorting, pagination, accessibility, responsive behavior, safe URLs, crawler metadata, and the production build. Playwright coverage should assert observable browser behavior against synthetic offline data.

Focused example:

```bash
uv run pytest tests/unit/test_linkedin.py -q
```

## Fixtures and live tests

For LinkedIn guest-markup changes:

1. reproduce only with express authorization;
2. reduce the example to minimal structural HTML;
3. remove personal, tracking, authenticated, and unrelated data;
4. use synthetic IDs;
5. add a failing regression test;
6. preserve challenge detection and structured-field boundaries;
7. test malformed and missing-field behavior.

Never commit authenticated pages, cookies, headers, account data, or browser captures. Follow [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#changing-linkedin-parsing) and [`SECURITY.md`](../../../SECURITY.md).

Live tests are skipped unless both variables are explicitly enabled:

```text
OPPORTUNITIES_LIVE_TESTS=1
OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true
```

Select the live marker deliberately with:

```bash
make test-live
```

These variables do not grant permission. CI does not run live tests, and an access block or challenge is a stop condition.

## README and documentation changes

The root README contains one opportunity-count marker pair and one opportunity-preview marker pair. `src/opportunities/readme.py` owns the opportunity metadata, latest successful collection time, website link, and bounded previews of five internships and five New Grad opportunities. `src/opportunities/public_exports.py` separately owns the sanitized open-opportunity CSV and JSON projections.

Coverage markers surround the quality table owned by `scripts/coverage_docs.py`. `make coverage` refreshes it from `quality-reports/coverage.json`, while CI uses `--check` to reject stale committed metrics.

Do not edit any generated region or reproduce a complete marker pair in examples.

Task-oriented Markdown belongs under `docs/guides/`; visual assets belong under `docs/assets/`. Contributor-facing documentation conventions are canonical in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#documentation-changes).

Validate documentation with:

```bash
make docs
git diff --check
```

## Final review

When packaging or container behavior changes, also run:

```bash
uv build
docker compose build
docker compose run --rm opportunities --help
docker compose config
```

Before committing:

```bash
git status --short
git diff --check
git diff
```

Confirm that:

- affected tests and validation paths pass;
- documentation matches the behavior;
- generated files were updated through their owner;
- lockfile changes are intentional;
- no `.env`, local settings, database, SQLite sidecar, credential, authenticated HTML, log, cache, or build artifact is staged.

The pull-request checklist is in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#pull-requests).
