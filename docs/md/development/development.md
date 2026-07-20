# European Tech Opportunities 2027 Development Guide

[← Documentation](../README.md) · [Architecture](architecture.md) · [Contributing](../../../CONTRIBUTING.md)

This guide covers the local engineering workflow, repository structure, coding standards, tests, fixtures, and validation paths. Contribution policy and pull-request requirements live in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md).

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
- Node.js 20.9 or newer, Bun 1.3.14, strict TypeScript, Tailwind CSS 4, ESLint, Prettier, and Next.js 16;
- GNU Make for optional command shortcuts, and Docker for container and production-path validation.

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
├── .github/workflows/       # validation, collection, maintenance
├── configs/                 # classification and search YAML
├── data/                    # ignored SQLite runtime state
├── docs/                    # Markdown guides and visual assets
├── migrations/              # Alembic history
├── scripts/                 # migration and documentation checks
├── site/                    # Next.js website and Playwright tests
├── src/opportunities/       # Python package
├── tests/                   # unit, integration, and fixtures
├── CONTRIBUTING.md
├── SECURITY.md
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
| `make render` | Regenerate the README preview from representative state |
| `make validate` | Validate SQLite state and generated projections |
| `make searches` | Inspect the effective search registry |
| `make stats` | Inspect aggregate database state |
| `make format` | Apply Ruff formatting and safe fixes |
| `make lint` | Run Ruff formatting and lint checks |
| `make typecheck` | Run strict mypy |
| `make test` | Run offline functional pytest |
| `make coverage` | Enforce critical lifecycle/classification branch coverage and write reports |
| `make benchmark` | Measure offline LinkedIn parsing and classification performance |
| `make test-live` | Explicitly select authorization-gated live tests |
| `make migrations` | Check Alembic and ORM consistency |
| `make docs` | Validate documentation links, images, and anchors |
| `make check` | Run the main Python and documentation pipeline |

> [!IMPORTANT]
> A fresh database contains no listings. Do not render and commit the README preview from empty local state.

## Validation paths

Run every path affected by the change. Use the full cross-project sequence before releases or for changes spanning multiple components.

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
uv run pytest -m "not live and not performance" --cov
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

This verifies Prettier, ESLint, strict TypeScript, the production Next.js build, Bun unit tests, and Playwright browser behavior in Chromium against a temporary synthetic SQLite fixture under `site/tests/e2e/.tmp/`. The fixture and test artifacts are ignored by Git.

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

### README preview and generated documentation

Do not render from an empty database and commit the result.

With representative canonical state:

```bash
uv run opportunities render
uv run opportunities validate
uv run pytest tests/integration/test_readme.py -q
```

Generated files must be updated through their owning commands.

### Containers

```bash
docker compose config
docker compose build
docker compose run --rm opportunities --help
```

Run affected smoke tests when changing image stages, runtime users, mounts, volumes, SQLite paths, permissions, or standalone website output. Operational container procedures belong to [Docker](../operations/docker.md).

### Full cross-project validation

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest -m "not live and not performance" --cov
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
- README rendering and validation;
- ORM and Alembic agreement.

`make coverage` measures branch coverage for classification, collection orchestration,
availability auditing, and repository lifecycle state. The combined threshold is 85%; terminal,
XML, JSON, and HTML reports are written under the ignored `quality-reports/` directory. CI also
publishes these files as a 30-day artifact and includes the coverage table in its job summary.
The current measured values are summarized in the root
[Python quality baseline](../../../README.md#python-quality-baseline).

`make benchmark` runs two offline microbenchmarks against representative fixtures: LinkedIn
search-page parsing and a complete classifier decision. Benchmark JSON is written to
`quality-reports/benchmark.json` and published with the CI quality reports. Results are intended
for trend comparison across equivalent runners, not as portable absolute timing guarantees.

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

The root README contains one generated marker pair. The renderer owns the open-position metadata, latest successful collection time, website link, and bounded previews of ten internships and ten New Grad positions.

Do not edit generated rows or include a second complete marker pair in examples.

Task-oriented Markdown belongs under `docs/md/`; visual assets belong under `docs/photo/`.

Keep links relative, commands executable from the stated directory, anchors stable, alt text descriptive, and claims aligned with implemented behavior.

Run:

```bash
make docs
git diff --check
```

## Final review

When changing packaging or containers:

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
