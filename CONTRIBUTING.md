# Contributing to European Tech Opportunities 2027

[← Project README](README.md) · [Documentation hub](docs/README.md) · [Security policy](SECURITY.md) · [Privacy notice](PRIVACY.md) · [Code of Conduct](CODE_OF_CONDUCT.md)

Thank you for contributing. This file is the contributor entry point; detailed setup, architecture, operation, and feature behavior live in the linked canonical guides.

> [!IMPORTANT]
> LinkedIn access requires express authorization. Public pages, environment flags, and participation in this project do not grant permission.

## Start here

1. Search existing issues and the [documentation hub](docs/README.md).
2. Fork the repository and branch from `main`.
3. Follow the [installation guide](docs/guides/getting-started/installation.md).
4. Reproduce the issue offline and make one focused change.
5. Add tests for observable behavior and run every affected validation path.
6. Open a pull request that explains the problem, solution, safety impact, and validation performed.

Recommended branch prefixes are `feat/`, `fix/`, `docs/`, `test/`, and `chore/`, followed by a short kebab-case description.

### Local setup

Python:

```bash
uv sync --frozen --dev
cp .env.example .env
uv run opportunities db-upgrade
```

Website:

```bash
cd site
bun install --frozen-lockfile
bunx playwright install chromium
```

Use the [installation guide](docs/guides/getting-started/installation.md) for complete setup, platform-specific instructions, Docker, and verification.

## Choose the correct path

| Change | Read first | Minimum validation |
|---|---|---|
| Python, CLI, classification, persistence | [Development](docs/guides/development/development.md) | `make check` or its documented `uv` equivalent |
| Website | [Website](docs/guides/user-guide/website.md) | `cd site && bun run ci` |
| Search YAML | [Search registry](docs/guides/user-guide/search-registry.md) | Registry command and config tests |
| Schema or migration | [Database](docs/guides/operations/database.md) | Fresh and representative upgrades plus migration checks |
| Docker or automation | [Docker](docs/guides/operations/docker.md) and [Automation](docs/guides/operations/automation.md) | Compose validation and affected build or runtime checks |
| Documentation only | [Documentation hub](docs/README.md) | Documentation validation and `git diff --check` |

Discuss changes to architecture, source access, canonical identity, lifecycle rules, schema design, deployment, or trust boundaries before implementation. Small fixes and documentation improvements can normally go directly to a pull request.

## Project contracts

Preserve these invariants:

1. SQLite is the lifecycle source of truth.
2. Numeric LinkedIn job IDs are canonical identities.
3. Ambiguous type, role, seniority, cycle, or geography is excluded; a listing without explicit target-cycle evidence also requires eligible posting-date evidence.
4. Search-page disappearance never closes a listing.
5. Failed searches do not mutate that search's lifecycle state.
6. The repository layer is the sole application writer.
7. Requests and processing remain authorized, unauthenticated, bounded, and deterministic.
8. The website, bounded README, and sanitized public exports remain read-only projections.

Do not add credentials, sessions, browser automation, private APIs, CAPTCHA handling, proxy evasion, concurrent writers, mutation APIs, or user-submitted data without explicit architecture and security review.

See [Architecture](docs/guides/development/architecture.md) and the [Security policy](SECURITY.md) for the complete trust and component boundaries.

## Code expectations

- Keep business behavior under `src/opportunities/`, not workflows or ad-hoc scripts.
- Keep transport, parsing, classification, persistence, and presentation separate.
- Use repository methods for writes and Alembic for schema evolution.
- Keep Python strictly typed and TypeScript strict.
- Use UTC-aware timestamps and deterministic ordering.
- Reject unknown external input where appropriate.
- Sanitize errors; never log response bodies, credentials, cookies, headers, or environment dumps.
- Avoid broad lint, type, test, or coverage suppressions.
- Keep changes focused and avoid unrelated cleanup.

## Data collection and classification

### Adding or changing a search

Follow the [search registry guide](docs/guides/user-guide/search-registry.md). A search must:

- use the correct role, company, or country directory;
- have a stable, unique lowercase kebab-case slug and query identity;
- include Internship and New Grad terms without requiring a year;
- use the dynamic `cycle` posting filter;
- use exact normalized employer names where applicable;
- use only independently verified geography IDs;
- start with the smallest defensible limits;
- explain scope and tuning in `notes`.

Validate with:

```bash
uv run opportunities searches
uv run pytest tests/unit/test_config.py -q
```

An authorized maintainer may additionally run `uv run opportunities search-test <slug>`. Reviewers and CI must not require live LinkedIn access.

### Changing classification

Classification rules live in `configs/categories.yml`; deterministic logic lives in `src/opportunities/pipeline/classification.py`.

Add nearby acceptance and rejection tests. Preserve:

- title-explicit Internship or New Grad evidence;
- seniority and technology-role exclusions;
- explicit target-cycle acceptance, acceptance without explicit opportunity-cycle evidence only with the May 1, 2026 posting-date floor, and conflicting-cycle rejection;
- explicit European geography;
- stable exclusion reasons.

Do not weaken a global rule to admit one ambiguous listing.

### Changing LinkedIn parsing

Use the smallest sanitized fixture that preserves the relevant guest-page structure. Use synthetic IDs and remove personal, tracking, authenticated, and unrelated data.

Preserve challenge detection, response limits, title prefiltering, and explicit unavailability handling. Test changed, malformed, and missing-field cases.

Never commit full pages, credentials, cookies, headers, browser captures, or authenticated HTML. Do not implement login, browser automation, CAPTCHA services, private endpoints, proxy rotation, fingerprint evasion, or anti-bot bypasses. An upstream challenge is a stop condition.

## Database and migrations

Follow the [database guide](docs/guides/operations/database.md). A schema change must:

1. update the SQLAlchemy models;
2. add a new Alembic revision without rewriting applied history;
3. preserve lifecycle state and provide a practical downgrade;
4. add repository and migration tests;
5. test fresh and representative prior databases;
6. pass migration consistency checks.

Never commit SQLite state or recommend deleting canonical state as the normal upgrade path.

## Website changes

Follow the [website guide](docs/guides/user-guide/website.md).

Preserve read-only server-side SQLite access, empty states, search, filters, sorting, pagination, shareable URLs, safe HTTPS links, responsive behavior, semantic HTML, keyboard access, and strict TypeScript.

Keep data helpers under `site/src/lib`, browser interaction in client components, Tailwind utilities in components, and global CSS minimal.

Authentication, forms, saved data, write APIs, or administrative mutation require prior architecture and security review.

## Testing and validation

Start with the narrowest relevant test, then run the complete affected gate.

| Change | Focused test |
|---|---|
| Search configuration | `uv run pytest tests/unit/test_config.py -q` |
| Classification | `uv run pytest tests/unit/test_classification.py -q` |
| Parsing or transport | `uv run pytest tests/unit/test_linkedin.py tests/unit/test_http.py -q` |
| Collection or lifecycle | `uv run pytest tests/integration/test_runner.py tests/integration/test_availability.py -q` |
| README rendering | `uv run pytest tests/integration/test_readme.py -q` |
| Models or migrations | `uv run pytest tests/unit/test_models.py tests/unit/test_migrations.py -q` |
| Website | `cd site && bun run ci` |

Tests must be offline and deterministic by default, assert observable behavior, use synthetic state, and cover relevant success and failure paths.

Run the full Python and documentation gate with:

```bash
make check
```

If Make is unavailable, use the exact commands in [Development](docs/guides/development/development.md#python-and-documentation). Run `make benchmark` for parser, normalization, or classifier hot paths.

Docker changes additionally require:

```bash
docker compose config
docker compose build
docker compose run --rm opportunities --help
```

Automation changes must pass the pinned `actionlint` check in `docker-ci.yml`. Preserve job-scoped least privilege, main-only environment secrets, the shared one-writer concurrency group, sanitized handoff artifacts, explicit validation of bot-generated commits, and the separation between canonical processing and GitHub mutation. Never place canonical SQLite in Actions cache or artifacts; protected deployment must consume state within its approved job.

Do not claim a check passed unless it ran. Explain omissions in the pull request. Live tests require deliberate selection and express authorization; environment interlocks do not grant permission.

## Documentation changes

Keep task guides under `docs/guides/` and assets under `docs/assets/`. Link to the canonical guide instead of duplicating procedures.

- Preserve README generated markers and never edit generated counts, timestamps, rows, coverage metrics, or public CSV/JSON exports manually.
- Render opportunity data only from representative canonical state; refresh coverage metrics with `make coverage`.
- Keep commands executable from their documented directory.
- Use repository-relative links, stable anchors, descriptive alt text, and sanitized assets.
- Keep claims aligned with implemented behavior and safety boundaries.

Validate documentation with:

```bash
uv run python scripts/check_docs.py
git diff --check
```

## Pull requests

Use a concise conventional title, such as `fix: preserve pagination after filtered cards`.

The description must cover:

- what changed and why;
- what is intentionally out of scope;
- lifecycle, source-access, privacy, security, and compatibility impact;
- exact checks run and any omitted checks;
- documentation, migration, lockfile, or screenshot changes where applicable.

Complete the repository pull-request template. Before review, inspect:

```bash
git status --short
git diff --check
git diff
```

Ensure no `.env`, database, sidecar, credential, cookie, private HTML, log, cache, report, or build artifact is included.

## Security and community

Report vulnerabilities privately through the [Security policy](SECURITY.md), not an issue or pull request.

All participation must follow the [Code of Conduct](CODE_OF_CONDUCT.md).
