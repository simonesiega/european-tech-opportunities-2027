# Development

[← README](../README.md)

This guide covers local setup, repository structure, tests, quality gates, migrations, builds, and the expected maintainer workflow.

## Requirements

- Python 3.12 or newer;
- [`uv`](https://docs.astral.sh/uv/);
- Git;
- Docker only for container changes or optional smoke testing.

The repository uses:

- Pydantic v2 for external configuration/domain validation;
- HTTPX and Beautiful Soup for bounded HTTP and HTML parsing;
- SQLAlchemy 2 and Alembic for SQLite persistence/schema history;
- Typer and Rich for the CLI;
- pytest, Ruff, and strict mypy for quality enforcement.

## Setup

Clone your fork or the main repository:

```bash
git clone https://github.com/simonesiega/european-tech-internships-2027.git
cd european-tech-internships-2027
uv sync --frozen --dev
```

Create local configuration and state:

```bash
cp .env.example .env || copy .env.example .env || Copy-Item .env.example .env
uv run internships db-upgrade
uv run internships render
uv run internships validate
```

Keep LinkedIn collection disabled for normal development:

```dotenv
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=false
```

Tests and migrations do not require LinkedIn access.

## Repository structure

```text
.
├── .github/
│   ├── dependabot.yml
│   └── workflows/
│       ├── ci.yml
│       └── scrape.yml
├── configs/
│   ├── categories.yml
│   ├── settings.example.yml
│   └── searches/
│       ├── roles/
│       ├── companies/
│       └── countries/
├── data/                         # ignored SQLite runtime state
├── docs/                         # detailed project documentation
├── migrations/
├── scripts/
├── src/internships/
├── tests/
├── CONTRIBUTING.md
├── Dockerfile
├── Makefile
├── README.md
├── SECURITY.md
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

## Development loop

A focused change normally follows:

```text
understand invariant and reproduce offline
        ↓
write or update a failing test
        ↓
implement the smallest change
        ↓
format + lint + type-check
        ↓
run focused tests, then full tests
        ↓
check migrations/README when relevant
        ↓
update documentation
        ↓
review staged diff for secrets and generated state
```

Avoid mixing parser, schema, search-registry, and unrelated cleanup in one pull request.

## Make targets

| Command | Runs |
|---|---|
| `make install` | `uv sync --dev` |
| `make migrate` | `internships db-upgrade` |
| `make scrape` | Full authorized scrape. Do not run without permission. |
| `make render` | README projection from open SQLite jobs. |
| `make validate` | Database/README invariant checks. |
| `make searches` | Effective registry and latest per-search health. |
| `make stats` | Pipeline statistics. |
| `make format` | Ruff formatter plus safe lint fixes. |
| `make lint` | Ruff format check and lint. |
| `make typecheck` | Strict mypy over source, tests, and scripts. |
| `make test` | Full pytest invocation; live test still skips unless explicitly enabled. |
| `make migrations` | Fresh Alembic/ORM consistency check. |
| `make check` | Lint, typecheck, tests, and migration consistency. |

`make check` is the normal pre-commit minimum. Release/container changes require additional checks below.

## Direct quality commands

Run the complete offline pipeline:

```bash
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest -m "not live"
uv run python scripts/check_migrations.py
uv run internships validate
uv build
```

What each gate catches:

| Gate | Purpose |
|---|---|
| `uv lock --check` | Project metadata and lockfile agree. |
| Ruff format | Python formatting is stable. |
| Ruff lint | Imports, correctness rules, modern Python, logging, and project lint policy pass. |
| strict mypy | Public/internal types agree without implicit `Any`. |
| offline pytest | Unit/integration behavior passes without LinkedIn access. |
| migration check | Fresh Alembic head and SQLAlchemy metadata are identical. |
| application validate | Local canonical state and README projection agree. |
| `uv build` | Source distribution and wheel include a usable package and README metadata. |

`internships validate` uses your configured local database. It complements tests; it is not a substitute for temporary-database integration coverage.

## Formatting and linting

Configuration lives in `pyproject.toml`.

Format:

```bash
uv run ruff format .
```

Apply safe lint fixes:

```bash
uv run ruff check --fix .
```

Review automatic fixes before committing. Do not add broad `noqa`, type ignores, or per-file exclusions to avoid addressing a real issue. Side-effect ORM model imports should be documented narrowly.

Code style:

- Python 3.12 syntax;
- line length 100;
- double quotes;
- LF endings;
- UTC-aware datetimes;
- immutable/frozen Pydantic configuration models;
- small explicit domain dataclasses;
- no print statements in application code (Rich/logging are used deliberately).

## Type checking

Strict mypy runs with Pydantic and SQLAlchemy plugins:

```bash
uv run mypy src tests scripts
```

Prefer precise protocols and injected dependencies over untyped mocks. The collector uses `TextFetcher` and pipeline uses `Scraper` protocols so tests can inject deterministic fakes without network access.

When a library lacks complete typing, isolate the exception in `pyproject.toml` rather than spreading `Any` through domain code.

## Test organization

### Unit tests

`tests/unit/` covers:

- classification cycle/title/category behavior;
- configuration precedence, validation, and registry invariants;
- HTTP authorization, response handling, pacing, and retry helpers;
- LinkedIn URL construction, parsing, filtering, pagination, and rechecks;
- migration upgrade idempotency;
- project-root discovery independent of directory depth.

### Integration tests

`tests/integration/` covers:

- CLI commands and exit preconditions;
- end-to-end pipeline persistence with injected scraping;
- incremental lifecycle and partial-run behavior;
- README rendering and exact validation;
- optional live smoke behavior.

### Shared fixtures

`tests/conftest.py` provides:

- project-root/config discovery;
- temporary SQLite repositories;
- deterministic HTML fixture loading;
- reusable search/settings factories.

HTML fixtures under `tests/fixtures/` should be minimal and sanitized. Use synthetic IDs and remove tracking/personal/authenticated data.

## Writing tests

A behavior change should include a regression test that fails before the implementation.

Guidelines:

- use `tmp_path` for databases, README files, and local configuration;
- use injected fetchers/clients instead of monkeypatching global network calls where practical;
- use fixed UTC timestamps for lifecycle assertions;
- assert externally meaningful state, not implementation call order alone;
- test both acceptance and nearby rejection for broader classifier keywords;
- verify failure paths do not mutate canonical state;
- avoid sleeps and real clocks;
- keep live access out of normal tests.

Run one file while iterating:

```bash
uv run pytest tests/unit/test_linkedin.py -q
```

Run one test:

```bash
uv run pytest tests/unit/test_classification.py::test_explicit_2027_software_internship_is_accepted -q
```

Then run the complete offline suite before review.

## Live smoke test

The live test is marked `live` and skipped unless both are set:

```text
INTERNSHIPS_LIVE_TESTS=1
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true
```

Even then, the variables are only interlocks. Run it only with express LinkedIn permission. CI never runs it.

The smoke test bounds the selected search to one page and one result. Do not expand live-test volume or make live access required for correctness.

## Parser fixture workflow

When LinkedIn guest markup changes:

1. reproduce the parser issue only under authorized access;
2. reduce the response to the smallest structural fixture;
3. replace IDs and remove query trackers/private or unrelated content;
4. add the fixture under `tests/fixtures/`;
5. write a failing parser/pipeline test;
6. update parsing without weakening block/challenge detection;
7. run malformed-majority and missing-field tests;
8. do not commit a complete authenticated page or browser capture.

Parser tests should prove stable extraction, safe skipping, warning behavior, and rejection when most content is malformed.

## Search and classification changes

For search YAML schema, tiers, and validation:

- [Search registry](search-registry.md)
- [Contributing: adding a search](../CONTRIBUTING.md#adding-or-changing-a-search)

For classification architecture:

- [Architecture: normalization and classification](architecture.md#normalization-and-classification-pipeline)
- `configs/categories.yml`
- `tests/unit/test_classification.py`

Every role filename must exist as an `InternshipCategory` value. Production config tests enforce the count, folder layout, enabled state, query terminology, capacities, company allowlists, and Europe geo ID.

## Migration workflow

Schema changes require both model and migration updates.

1. Back up any representative local database.
2. Update `src/internships/database/models.py`.
3. Create a new Alembic revision:

   ```bash
   uv run alembic revision -m "describe schema change"
   ```

4. Implement `upgrade()` and `downgrade()` deliberately; review autogenerated operations.
5. Upgrade a clean database and representative backup.
6. Add repository/migration tests.
7. Run:

   ```bash
   uv run python scripts/check_migrations.py
   ```

8. Render and validate against the upgraded representative database.

Do not edit a revision already applied outside your disposable local environment.

See [Database lifecycle](database.md#migrations).

## README development

The renderer owns only the marked internship block. Keep exactly one marker pair in `README.md`.

After changing README text:

```bash
uv run internships render
uv run internships validate
```

After changing renderer behavior, test:

- generated metadata from SQLite;
- exact four-column header;
- escaping of Markdown-sensitive values;
- safe links;
- stable ordering;
- missing/duplicate markers;
- atomic replacement behavior;
- exact SQLite/open-job equality.

Do not place a second complete marker pair in documentation examples inside README.

## Package build

Build both artifacts:

```bash
rm -f dist/*.whl dist/*.tar.gz || Remove-Item dist\*.whl, dist\*.tar.gz -ErrorAction SilentlyContinue
uv build
```

Smoke-test package metadata/import where appropriate. `dist/` is ignored and should not be committed.

When changing the version, keep these synchronized:

- `pyproject.toml`;
- `src/internships/__init__.py`;
- `uv.lock`;
- default/example user agents;
- README and Security version references;
- newly built artifact names.

## Docker checks

For Docker-related changes:

```bash
docker build --tag european-tech-internships-2027:dev .
docker run --rm european-tech-internships-2027:dev --help
docker compose config
```

A stronger clean-state smoke test should:

1. create a temporary Docker volume;
2. mount a temporary README copy;
3. run `db-upgrade`;
4. run `render`;
5. run `validate` and require zero jobs.

See [Docker](docker.md).

## Documentation checks

When editing documentation:

- verify every relative path exists;
- verify heading anchors used by cross-links;
- keep examples aligned with actual CLI help/config models;
- keep README at exactly one internship marker pair;
- use UTF-8 and LF endings;
- remove trailing whitespace;
- run README render/validation;
- avoid claims that deferred features are implemented.

Detailed material belongs in `docs/`; README should remain the concise landing page.

## Pre-commit review

Before staging:

```bash
git status --short
git diff --check
git diff
```

Confirm none of these are staged:

- `.env` or `configs/settings.yml`;
- `data/internships.db` or sidecars;
- `dist/` artifacts;
- logs, caches, or editor metadata;
- cookies, tokens, private HTML, or real authenticated headers.

Then inspect staged content:

```bash
git add <focused-files>
git diff --cached --check
git diff --cached
```

For pull-request expectations, see [`CONTRIBUTING.md`](../CONTRIBUTING.md).
