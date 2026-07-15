<h1 align="center">
  Contributing to European Tech Internships 2027
</h1>

<p align="center">
  Guidelines for safe, focused, and evidence-based contributions.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white" alt="Python 3.12 or newer" />
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="Pull requests welcome" />
  <a href="LICENSE"><img src="https://img.shields.io/github/license/simonesiega/european-tech-internships-2027" alt="MIT license" /></a>
  <a href="https://github.com/simonesiega/european-tech-internships-2027/issues"><img src="https://img.shields.io/github/issues/simonesiega/european-tech-internships-2027" alt="Open issues" /></a>
</p>

Thank you for improving the project. Read [`README.md`](README.md) first, especially its scope, lifecycle, and authorization sections.

> [!IMPORTANT]
> Never access LinkedIn automatically while developing this project unless you have express permission. Public pages, a local environment flag, and an open-source contribution do not provide authorization.

## Contents

- [Quick start](#quick-start)
- [Ways to contribute](#ways-to-contribute)
- [Issues and design changes](#issues-and-design-changes)
- [Development setup](#development-setup)
- [Project boundaries](#project-boundaries)
- [Code guidelines](#code-guidelines)
- [Adding or changing a search](#adding-or-changing-a-search)
- [Changing classification](#changing-classification)
- [Changing LinkedIn parsing](#changing-linkedin-parsing)
- [Database and migrations](#database-and-migrations)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull requests](#pull-requests)
- [Security](#security)
- [Community](#community)

## Quick start

| Step | Action |
|---:|---|
| 1 | Fork the repository and create a branch from `main`. |
| 2 | Install the locked Python 3.12 development environment with `uv`. |
| 3 | Make one focused, testable change. |
| 4 | Run the complete local validation pipeline. |
| 5 | Open a pull request that explains the behavior and rationale. |

Suggested branch names:

| Change | Pattern | Example |
|---|---|---|
| Feature | `feat/` | `feat/add-compiler-search` |
| Bug fix | `fix/` | `fix/linkedin-location-parser` |
| Documentation | `docs/` | `docs/clarify-lifecycle` |
| Maintenance | `chore/` | `chore/update-dependencies` |
| Tests | `test/` | `test/add-pagination-coverage` |

## Ways to contribute

High-value contributions include:

- correcting strict internship, cycle, technology, or geography classification;
- adding a focused role, employer, or country query with justified limits;
- improving parser resilience using sanitized fixture HTML;
- strengthening database lifecycle and migration safety;
- improving deterministic error handling and observability;
- expanding offline tests for edge cases and regressions;
- correcting documentation without weakening responsible-use requirements.

The repository intentionally does not accept alternative job providers, browser automation, account-based collection, private endpoints, or unrelated output formats in the focused `0.1.x` architecture.

## Issues and design changes

Search [existing issues](https://github.com/simonesiega/european-tech-internships-2027/issues) before opening a duplicate.

A useful bug report includes:

| Field | What to provide |
|---|---|
| Expected behavior | The strict result or state transition that should occur. |
| Actual behavior | What happened instead. |
| Reproduction | Minimal offline steps, command, search slug, or sanitized fixture. |
| Environment | OS, Python version, `uv --version`, and project version/commit. |
| Diagnostics | Sanitized error code or output; never include secrets or private data. |

Open an issue before substantial architecture, schema, lifecycle, source-policy, or classification changes. Small search additions, tests, and documentation fixes can normally go directly to a pull request.

Security vulnerabilities must not be reported publicly. Follow [`SECURITY.md`](SECURITY.md).

## Development setup

Requirements:

- Python 3.12 or newer;
- [`uv`](https://docs.astral.sh/uv/);
- Git;
- Docker only if changing or validating the container path.

Clone your fork and install exact locked dependencies:

```bash
git clone https://github.com/<your-user>/european-tech-internships-2027.git
cd european-tech-internships-2027
uv sync --frozen --dev
```

Create local configuration:

```bash
cp .env.example .env
uv run internships db-upgrade
uv run internships render
uv run internships validate
```

Leave this setting false unless you personally have express permission:

```dotenv
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=false
```

All normal development and automated tests are designed to run without LinkedIn access.

## Project boundaries

Read [Architecture](docs/architecture.md) and [Database lifecycle](docs/database.md) before changing component boundaries or persisted behavior.

The supported architecture is:

```text
LinkedIn guest HTML → strict classification → SQLite → README
```

Preserve these invariants:

1. **SQLite is canonical.** README rows are never a second source of truth.
2. **One canonical ID.** Distinct numeric LinkedIn IDs remain distinct jobs.
3. **Strict acceptance.** Unknown cycle, ambiguous role, or unknown geography means exclusion.
4. **Safe closure.** Search-page absence cannot close a job.
5. **Transactional isolation.** A failed search must not mutate that search's job state.
6. **One public shape.** The generated table has exactly company, title, location, and link.
7. **No credentials.** Collection must remain unauthenticated and permission-gated.
8. **Bounded access.** Requests, responses, retries, concurrency, and query sizes remain limited.
9. **Deterministic output.** Rendering and validation must be stable and reproducible.
10. **One writer.** Do not introduce concurrent SQLite writers into the supported workflow.

## Code guidelines

Keep changes small, typed, deterministic, and easy to review.

| Area | Guideline |
|---|---|
| CLI | Keep commands and exit-code behavior in `src/internships/cli/app.py`; put business logic elsewhere. |
| Configuration | Validate external input with Pydantic and reject unknown fields. Do not silently accept malformed YAML. |
| Collection | Keep LinkedIn parsing in `scrapers/linkedin.py` and transport policy in `scrapers/http.py`. |
| Classification | Keep acceptance deterministic and explain exclusions with stable reasons. |
| Persistence | Use repository methods and short SQLAlchemy transactions; do not write ad hoc SQL in the pipeline. |
| Rendering | Preserve atomic replacement and exactly one marker pair. |
| Errors | Store and display sanitized error categories, not raw response bodies or sensitive exception context. |
| Types | Maintain strict mypy; avoid `Any`, unchecked casts, and broad suppressions. |
| Tests | Add a regression test for every behavior change. Tests must be offline by default. |

Use UTC-aware timestamps. Keep files UTF-8 with LF endings. Follow the existing Ruff formatting rather than manually aligning Python code.

## Adding or changing a search

[Search registry](docs/search-registry.md) is the canonical schema and tuning reference. The contributor requirements below summarize the review process.

Choose the appropriate recursive registry directory:

```text
configs/searches/roles/
configs/searches/companies/
configs/searches/countries/
```

A search file uses this schema:

```yaml
name: European compiler internships 2027
slug: compiler-engineering
keywords: compiler intern 2027
location: Europe
geo_id: "91000000"
company_names: []
workplace: any
date_posted: any
max_pages: 2
max_results: 50
max_rechecks: 10
enabled: true
verified_at: 2026-07-15
notes: Specialized role tier; reassess after several successful runs.
```

Requirements:

- filename and `slug` must be stable, lowercase kebab-case;
- role filenames must have a matching value in `InternshipCategory`;
- keywords must explicitly include `2027` and internship terminology;
- Europe-wide queries use the verified LinkedIn Europe geo ID `91000000`;
- country queries use a country-specific `location` and omit an unverified numeric geo ID;
- employer queries use `company_names` as an exact normalized allowlist;
- `max_results` cannot exceed `max_pages × 25`;
- do not duplicate an existing query identity;
- `verified_at` records the date the configuration itself was reviewed, not proof of ongoing LinkedIn availability;
- notes should explain scope or tier, not make unsupported coverage claims.

Choose conservative limits:

| Tier | Pages | Results | Rechecks |
|---|---:|---:|---:|
| High | 4 | 100 | 20–25 |
| Medium | 3 | 75 | 15–20 |
| Specialized | 2 | 50 | 10 |
| Minimal/unobserved | 1 | 25 | 5 |

Prefer a focused query over increasing every global limit. Use `uv run internships searches` after successful authorized runs to compare found and accepted counts. Do not tune from one snapshot.

After changing YAML, run:

```bash
uv run internships searches
uv run pytest tests/unit/test_config.py
```

An authorized maintainer may additionally run a single non-persisting preview:

```bash
uv run internships search-test <slug>
```

Do not require reviewers or CI to access LinkedIn.

## Changing classification

Classification rules live in [`configs/categories.yml`](configs/categories.yml); deterministic logic lives in `src/internships/pipeline/classification.py`.

When changing a rule:

1. describe the false positive or false negative;
2. add representative acceptance and rejection tests;
3. preserve title-explicit internship requirements;
4. preserve explicit 2027 evidence;
5. preserve explicit European geography;
6. verify broader keywords do not admit senior or non-technical roles;
7. update `InternshipCategory` and role-registry tests when adding a role path.

Do not weaken a global rule solely to include one ambiguous listing. A precise false negative is safer than publishing an unrelated role.

## Changing LinkedIn parsing

Parser changes must use local fixtures and remain compatible with bounded public HTML collection.

- Add the smallest sanitized fixture needed to reproduce the markup variation.
- Use synthetic LinkedIn IDs and remove personal or tracking data where possible.
- Do not commit cookies, headers, account IDs, access tokens, full browser captures, or private HTML.
- Do not add login flows, browser automation, CAPTCHA handling, private endpoints, proxy rotation, fingerprint evasion, or anti-bot bypasses.
- Preserve search-card title prefiltering and detail-page response handling.
- Ensure malformed HTML fails one search safely rather than corrupting persisted state.

If a live site change cannot be represented safely in a fixture, describe the structure without including sensitive data and coordinate privately with a maintainer.

## Database and migrations

See [Database lifecycle](docs/database.md) for the complete schema, closure algorithm, backup, and recovery model.

SQLAlchemy models describe current schema intent. Alembic migrations describe how real databases reach that schema without losing canonical state.

When changing persisted schema:

1. update `src/internships/database/models.py`;
2. add a new file under `migrations/versions/`;
3. do not rewrite a migration that may already have been applied;
4. make upgrades preserve existing lifecycle data;
5. add repository and migration tests;
6. run the migration consistency check against a fresh database;
7. test upgrading a representative backup when the change is non-trivial.

Required commands:

```bash
uv run internships db-upgrade
uv run python scripts/check_migrations.py
```

Never commit `data/internships.db`. Never ask users to delete canonical state as the default upgrade strategy.

## Testing

See [Development](docs/development.md) for test organization, fixtures, focused commands, package builds, and Docker smoke tests.

Run the full local quality pipeline before requesting review:

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

Or run the main checks with:

```bash
make check
```

Test expectations:

- unit and integration tests run offline and deterministically;
- network behavior uses injected fake clients or fixture fetchers;
- filesystem and database tests use temporary paths;
- lifecycle tests cover success, partial failure, closure confirmation, and rediscovery where relevant;
- parser changes include representative local HTML fixtures;
- timestamps remain monotonic under concurrently completed searches;
- README tests assert exact four-column output and marker behavior.

The live smoke test is skipped unless both variables are explicitly set:

```text
INTERNSHIPS_LIVE_TESTS=1
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true
```

These flags do not provide permission. Do not run the live test without express authorization.

If changing Docker, also run:

```bash
docker build --tag european-tech-internships-2027:dev .
docker run --rm european-tech-internships-2027:dev --help
docker compose config
```

## Documentation

Detailed operational references live under `docs/` and are indexed from the README. Update the relevant guide rather than expanding the README with internal detail.

Update documentation whenever you change:

- installation or configuration;
- CLI commands, flags, output, or exit codes;
- search schema or tuning guidance;
- classification or lifecycle behavior;
- database schema or migration procedure;
- workflow, Docker, source-access, or security behavior.

Keep examples executable and use placeholders for private values. Keep exactly one README internship marker pair and never edit generated rows manually.

## Pull requests

Use a concise title such as:

```text
fix: preserve pagination after filtered search cards
feat: add bounded compiler internship search
docs: clarify closure confirmation behavior
```

A pull request description should explain:

- what changed;
- why the existing behavior was insufficient;
- safety or lifecycle implications;
- tests performed;
- documentation updated;
- whether any authorized manual validation occurred.

### Checklist

Before requesting review, confirm:

- [ ] The change is focused and contains no unrelated cleanup.
- [ ] The title and description explain behavior and rationale.
- [ ] Strict scope and database lifecycle invariants remain intact.
- [ ] Tests were added or updated for behavior changes.
- [ ] Offline quality checks pass.
- [ ] Schema changes include a new migration and migration tests.
- [ ] Search limits are evidence-based and bounded.
- [ ] Documentation matches the implemented behavior.
- [ ] No `.env`, database, credentials, cookies, private HTML, or generated build artifacts are staged.
- [ ] No unauthorized live LinkedIn access was performed.
- [ ] `uv.lock` changed only when dependencies or project metadata required it.

Maintainers may request a smaller change if a pull request combines unrelated parser, schema, configuration, and documentation work.

## Security

If you discover a vulnerability, authorization bypass, unsafe network behavior, state-corruption path, or sensitive-data exposure, do not open a public issue. Follow the private reporting instructions in [`SECURITY.md`](SECURITY.md).

## Community

Be clear, respectful, and constructive in issues, pull requests, and reviews. Critique code and behavior, not people. Harassment, discriminatory conduct, and attempts to pressure contributors into bypassing source policies are not acceptable.

## Contact

- GitHub: [@simonesiega](https://github.com/simonesiega)
- Email: [simonesiega1@gmail.com](mailto:simonesiega1@gmail.com)

Thanks for contributing responsibly.
