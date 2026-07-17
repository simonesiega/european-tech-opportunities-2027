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

Thank you for improving the project. Read [`README.md`](README.md) before contributing, then use the [documentation hub](docs/md/README.md) to find the canonical technical guide for your change.

> [!IMPORTANT]
> Never automate LinkedIn access while developing this project unless you have express permission. Public pages, environment flags, and an open-source contribution do not provide authorization.

## Contents

- [Contribution workflow](#contribution-workflow)
- [Choose your contribution path](#choose-your-contribution-path)
- [Good contributions](#good-contributions)
- [Issues and design changes](#issues-and-design-changes)
- [Project boundaries](#project-boundaries)
- [Code expectations](#code-expectations)
- [Adding or changing a search](#adding-or-changing-a-search)
- [Changing classification](#changing-classification)
- [Changing LinkedIn parsing](#changing-linkedin-parsing)
- [Database and migrations](#database-and-migrations)
- [Website changes](#website-changes)
- [Testing and validation](#testing-and-validation)
- [Documentation changes](#documentation-changes)
- [Pull requests](#pull-requests)
- [Security and community](#security-and-community)

## Contribution workflow

| Step | Action |
|---:|---|
| 1 | Search existing issues and documentation. |
| 2 | Fork the repository and create a branch from `main`. |
| 3 | Install only the tools required for the change. |
| 4 | Make one focused, testable change. |
| 5 | Run the checks for every affected component. |
| 6 | Open a pull request explaining the behavior, rationale, and validation. |

Suggested branch names:

| Change | Pattern | Example |
|---|---|---|
| Feature | `feat/` | `feat/add-compiler-search` |
| Bug fix | `fix/` | `fix/linkedin-location-parser` |
| Documentation | `docs/` | `docs/clarify-lifecycle` |
| Maintenance | `chore/` | `chore/update-dependencies` |
| Tests | `test/` | `test/add-pagination-coverage` |

Use the [installation guide](docs/md/getting-started/installation.md) for local setup and the [development guide](docs/md/development/development.md) for repository structure, coding conventions, test organization, and complete validation commands.

## Choose your contribution path

| Change | Canonical guide | Minimum validation |
|---|---|---|
| Python pipeline, CLI, classification, or persistence | [Development](docs/md/development/development.md) | `make check` |
| Website or UI | [Website](docs/md/user-guide/website.md) and [Development](docs/md/development/development.md) | `cd site && bun run ci` |
| Search configuration | [Search registry](docs/md/user-guide/search-registry.md) | `internships searches` and focused config tests |
| Database schema or migrations | [Database lifecycle](docs/md/operations/database.md) | Migration consistency and upgrade tests |
| Documentation only | [Documentation hub](docs/md/README.md) | Documentation checks and `git diff --check` |
| Docker or deployment | [Docker](docs/md/operations/docker.md) and [Automation](docs/md/operations/automation.md) | Image or Compose checks for the affected path |

Run broader checks when a change crosses component boundaries. Documentation-only changes do not require unrelated package builds, migrations, or application tests.

## Good contributions

High-value contributions include:

- correcting strict internship, cycle, technology, seniority, or geography classification;
- adding a focused role, employer, or country search with justified limits;
- improving parser resilience with sanitized fixture HTML;
- strengthening database lifecycle, migration, or recovery safety;
- improving deterministic error handling and observability;
- improving website accessibility, responsiveness, usability, or performance;
- expanding offline regression coverage;
- correcting documentation without weakening responsible-operation requirements.

Additional providers, authenticated or browser-based collection, private endpoints, concurrent writers, user-submitted data, and new canonical output formats are outside the current architecture. Discuss them before implementation.

## Issues and design changes

Search [existing issues](https://github.com/simonesiega/european-tech-internships-2027/issues) before opening a duplicate.

A useful bug report includes:

| Field | What to provide |
|---|---|
| Expected behavior | The result or state transition that should occur |
| Actual behavior | What happened instead |
| Reproduction | Minimal offline steps, command, slug, or sanitized fixture |
| Environment | OS, runtime and package-manager versions, and project commit |
| Diagnostics | First sanitized error or exit code |

Open an issue before substantial changes to architecture, source-access policy, canonical identity, lifecycle behavior, schema design, classification policy, deployment, or trust boundaries.

Small tests, documentation fixes, focused parser corrections, and well-scoped search additions can normally go directly to a pull request.

Security vulnerabilities must be reported privately through [`SECURITY.md`](SECURITY.md).

## Project boundaries

The supported data flow is:

<div align="center">
<pre>
permission-gated LinkedIn guest HTML
↓
strict deterministic classification
↓
canonical transactional SQLite state
↓
read-only website + bounded README preview
</pre>
</div>

Preserve these invariants:

1. **SQLite is canonical.** README rows and browser state are never lifecycle sources.
2. **Numeric job IDs are canonical identities.** Similar display fields do not merge distinct IDs.
3. **Acceptance remains strict.** Ambiguous cycle, role, seniority, or geography means exclusion.
4. **Closure remains conservative.** Search-page absence cannot close a job.
5. **Search outcomes remain isolated.** A failed search cannot mutate that search’s lifecycle state.
6. **The README remains bounded.** It contains one generated marker pair and at most ten jobs.
7. **Source access remains permission-gated and unauthenticated.**
8. **Requests and processing remain bounded and deterministic.**
9. **The website remains a read-only projection.**
10. **The supported workflow retains one canonical writer.**

Read the [architecture guide](docs/md/development/architecture.md) before changing these contracts.

## Code expectations

Keep changes small, typed, deterministic, and easy to review.

| Area | Expectation |
|---|---|
| CLI | Keep orchestration, output, and exit-code behavior in the CLI layer; put business rules elsewhere |
| Configuration | Validate external input and reject unknown fields |
| Collection | Keep transport policy separate from LinkedIn parsing |
| Classification | Preserve deterministic decisions and stable exclusion reasons |
| Persistence | Use repository methods, short transactions, and Alembic migrations |
| Rendering | Preserve one marker pair, atomic replacement, and the bounded preview |
| Website | Preserve read-only SQLite access, strict TypeScript, accessibility, and safe links |
| Errors | Expose sanitized categories, never raw response bodies or secret context |
| Tests | Add a regression test for every behavior change; keep tests offline by default |

Use UTC-aware timestamps, UTF-8, LF endings, and the project’s Ruff and Prettier formatting. Do not add broad type, lint, or test suppressions to avoid fixing a real issue.

## Adding or changing a search

The [search registry guide](docs/md/user-guide/search-registry.md) is the canonical reference for YAML fields, query identity, directory conventions, pagination, and limit tiers.

A search contribution must:

- use the correct role, company, or country directory;
- keep a stable, unique lowercase kebab-case slug;
- use an effective query identity not already present;
- include explicit internship terminology and `2027`;
- use exact normalized company names for employer searches;
- avoid invented geography IDs;
- start with the smallest defensible request tier;
- explain scope and tuning in `notes`;
- update category mapping and tests when introducing a role category.

Run:

```bash
uv run internships searches
uv run pytest tests/unit/test_config.py
```

An authorized maintainer may additionally run one non-persisting preview:

```bash
uv run internships search-test <slug>
```

Do not require reviewers or CI to contact LinkedIn.

## Changing classification

Classification configuration lives in `configs/categories.yml`; deterministic logic lives in `src/internships/pipeline/classification.py`.

A classification change must:

1. describe the false positive or false negative;
2. add nearby acceptance and rejection tests;
3. preserve title-explicit internship evidence;
4. preserve explicit target-cycle evidence;
5. preserve explicit European geography;
6. verify that senior and non-technical roles remain excluded;
7. update category and search-registry tests when adding a role path.

Do not weaken a global rule solely to include one ambiguous listing. Precision is an intentional product decision.

## Changing LinkedIn parsing

Parser changes must use local sanitized fixtures and preserve the bounded public-HTML collection model.

- Reduce the example to the smallest structural HTML required.
- Use synthetic job IDs and remove tracking or personal data.
- Never commit credentials, cookies, headers, account identifiers, full browser captures, or authenticated HTML.
- Do not add login flows, browser automation, CAPTCHA services, private endpoints, proxy rotation, fingerprint evasion, or anti-bot bypasses.
- Preserve challenge detection, title prefiltering, response bounds, and explicit unavailability handling.
- Ensure malformed markup fails safely without corrupting persisted state.
- Add regression coverage for changed and missing-field cases.

When a live variation cannot be represented safely, describe the structure privately without sharing sensitive source material.

## Database and migrations

The [database lifecycle guide](docs/md/operations/database.md) is the canonical reference for schema, provenance, closure, migrations, backups, and restoration.

A persisted-schema change must:

- update the SQLAlchemy models;
- add a new Alembic revision;
- preserve existing lifecycle state;
- provide a practical downgrade where possible;
- add repository and migration tests;
- test a fresh database;
- test a representative backup when existing state changes;
- pass the migration consistency check.

Never rewrite an applied migration, commit `data/internships.db`, or ask users to delete canonical state as the default upgrade strategy.

## Website changes

Website contributions must preserve:

- read-only SQLite access;
- valid empty-state behavior;
- search, filters, sorting, and pagination;
- responsive layouts;
- semantic HTML and keyboard accessibility;
- safe public HTTPS listing links;
- strict TypeScript and production build behavior.

Run:

```bash
cd site
bun run ci
```

Authentication, forms, user-provided content, write APIs, saved user data, or administrative mutation paths require an explicit architecture and security review before implementation.

## Testing and validation

Use the [development guide](docs/md/development/development.md) for complete validation paths and focused commands.

General expectations:

- run checks for every affected component;
- keep unit and integration tests deterministic and offline;
- use temporary paths, synthetic IDs, fixed timestamps, and injected fetchers;
- test meaningful state and observable behavior;
- add parser fixtures for markup changes;
- test success and failure isolation for lifecycle changes;
- test fresh and representative databases for migrations;
- update generated files only through their owning commands.

Common minimum checks:

```bash
make check
```

```bash
cd site && bun run ci
```

```bash
docker compose config
```

Do not render and commit the README preview from an empty development database.

Live tests remain disabled unless both safety variables are explicitly enabled, and those variables still do not provide permission.

## Documentation changes

Task-oriented guides live under `docs/md/`, and visual assets live under `docs/photo/`.

Update the canonical guide whenever behavior changes. Avoid copying complete procedures into several files.

Keep:

- internal repository links relative;
- commands executable from their documented working directory;
- heading anchors stable when other files link to them;
- image alt text descriptive;
- public claims aligned with implemented behavior;
- examples consistent with authorization and one-writer constraints.

The root README contains one generated internship marker pair. Never edit generated rows manually or include a second complete marker pair in examples.

For documentation-only changes, run the documentation checks and:

```bash
git diff --check
```

## Pull requests

Use a concise title such as:

```text
fix: preserve pagination after filtered search cards
feat: add bounded compiler internship search
docs: clarify closure confirmation behavior
```

The pull request description should explain:

- what changed;
- why the previous behavior was insufficient;
- safety, lifecycle, or compatibility implications;
- tests and checks performed;
- documentation updated;
- whether any authorized manual validation occurred.

Before requesting review, confirm:

- [ ] The change is focused and contains no unrelated cleanup.
- [ ] The title and description explain behavior and rationale.
- [ ] Architecture and lifecycle invariants remain intact.
- [ ] Tests were added or updated for behavior changes.
- [ ] Checks for every affected component pass.
- [ ] Schema changes include a new migration and migration tests.
- [ ] Search limits remain justified and bounded.
- [ ] Documentation matches implemented behavior.
- [ ] Generated files were updated through their owning commands.
- [ ] No `.env`, database, credential, cookie, private HTML, or build artifact is staged.
- [ ] No unauthorized live LinkedIn access was performed.
- [ ] Lockfiles changed only when their corresponding dependencies or metadata changed.

Maintainers may request a smaller pull request when unrelated parser, schema, configuration, website, and documentation changes are combined.

## Security and community

Report vulnerabilities, authorization bypasses, unsafe network behavior, state-corruption paths, or sensitive-data exposure privately through [`SECURITY.md`](SECURITY.md).

Be clear, respectful, and constructive in issues, pull requests, and reviews. Critique code and behavior, not people. Harassment, discriminatory conduct, or pressure to bypass source policies is not acceptable.

Contact:

- GitHub: [@simonesiega](https://github.com/simonesiega)
- Email: [simonesiega1@gmail.com](mailto:simonesiega1@gmail.com)

Thanks for contributing responsibly.