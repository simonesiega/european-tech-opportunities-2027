# AGENTS.md

## Purpose

This project (`european-tech-opportunities-2027`) is an open-source pipeline and searchable website for validated 2027 technology internships and New Grad opportunities across Europe.

The system uses bounded public LinkedIn guest HTML only when source access is explicitly authorized, applies deterministic classification, stores lifecycle state in canonical SQLite, and exposes that state through a read-only Next.js website plus a bounded README preview.

The project favors **precision, determinism, lifecycle safety, and responsible source access over maximum coverage**. Ambiguous opportunities should be excluded rather than guessed into the dataset.

### Core priorities

1. Preserve canonical data and lifecycle correctness.
2. Keep source access bounded, permission-gated, and unauthenticated.
3. Keep classification deterministic and conservative.
4. Keep the website and README read-only projections of SQLite.
5. Prefer focused, testable changes over broad abstractions.

If a tradeoff is required, choose correctness, safety, reproducibility, and explicit evidence over convenience or additional coverage.

## Agent Context and Skills

This repository may contain task-specific context under `.context/` and reusable procedures under `.agents/skills/`. Treat both as **lazy-loaded context**, not mandatory startup reading.

### `.context/`

- Inspect `.context/` filenames when the task could depend on prior project decisions or task-specific notes.
- If the user mentions a context file, topic, feature, decision, or keyword that clearly maps to a file there, read the matching file before editing.
- If the task clearly overlaps a context file without an exact match, read only the smallest relevant set.
- Do not load the whole directory by default.
- Context never overrides this file, repository behavior, `SECURITY.md`, or canonical documentation.
- If context conflicts with current code or docs, prefer current repository evidence and mention the mismatch.

### `.agents/skills/`

- Reusable skills live under `.agents/skills/<skill-name>/`; the entry point is normally `SKILL.md`.
- If the user names a skill, or the task clearly matches one, read its `SKILL.md` before acting.
- Follow referenced files only as needed; do not load unrelated skills.
- Skills do not override project safety boundaries or explicit user instructions.

Before editing a nested area, check whether it contains another `AGENTS.md`. If present, follow it in addition to this root file.

## High-Level Architecture

```text
configs/                         → Classification categories and search definitions
src/opportunities/config/        → Settings, rules, and search registry
src/opportunities/scrapers/      → Bounded HTTP transport and LinkedIn guest parsing
src/opportunities/normalization/ → Stable title, text, URL, and location normalization
src/opportunities/pipeline/      → Collection, classification, and availability checks
src/opportunities/database/      → Canonical SQLite models, repository, transactions
src/opportunities/cli/           → CLI orchestration, output, and exit codes
src/opportunities/readme.py      → Deterministic bounded README projection
migrations/                      → Alembic schema history
site/                            → Read-only Next.js opportunity directory
tests/                           → Offline unit, integration, fixture, migration, benchmark coverage
scripts/                         → Documentation and migration checks
docs/                            → Canonical task-oriented documentation
.github/workflows/               → Validation, collection, availability, backup, deployment automation
```

Runtime:

```text
search YAML + classification rules
→ bounded guest search HTML
→ title/company prefilters
→ bounded guest detail HTML
→ normalization + deterministic classification
→ transactional SQLite lifecycle state
→ website + bounded README preview
```

- Discovery is not acceptance.
- Numeric LinkedIn job IDs are canonical identities.
- SQLite is the lifecycle source of truth.
- The repository layer is the sole application writer.
- Search-page disappearance never closes a listing by itself.
- Failed searches must not mutate that search's lifecycle state.
- The website and README never classify jobs or mutate lifecycle state.

## Tech Stack

- Python 3.12+, `uv`, Pydantic, HTTPX, Beautiful Soup, SQLAlchemy, Alembic, Typer, Rich.
- pytest, pytest-cov, pytest-benchmark, Ruff, strict mypy.
- Node.js 22.13+, Bun, Next.js 16, React 19, TypeScript 5, Tailwind CSS 4.
- ESLint, Prettier, Playwright.
- SQLite is canonical; Alembic owns schema evolution.

## Canonical Documentation

Read the relevant guide before broad, architectural, operational, schema, source-access, or release-relevant changes.
```text
README.md                                       → Product overview and public behavior
CONTRIBUTING.md                                 → Contribution workflow and project boundaries
SECURITY.md                                     → Source-access rules, trust boundaries, secrets
docs/README.md                                  → Documentation router
docs/guides/development/architecture.md         → Data flow, invariants, ownership
docs/guides/development/development.md          → Toolchain, tests, validation
docs/guides/user-guide/search-registry.md       → Search YAML schema and query rules
docs/guides/user-guide/website.md               → Website behavior and read-only contract
docs/guides/operations/database.md              → Schema, lifecycle, migrations, backup/restore
docs/guides/operations/automation.md            → CI, collection, snapshots, deployment
docs/guides/operations/docker.md                → Images, Compose, volumes, deployment
```
Keep deep details canonical in those guides. Summarize and link instead of duplicating them elsewhere.

## Repository Rules

- Use **uv** for Python dependency management and commands; prefer `uv sync --frozen --dev`.
- Use **Bun** inside `site/`; do not mix npm, pnpm, or Yarn into normal development.
- Keep business behavior under `src/opportunities/`, not workflow YAML or ad-hoc scripts.
- Keep transport policy separate from LinkedIn parsing.
- Keep classification independent from transport and presentation.
- Keep canonical writes inside repository methods and Alembic migrations.
- Keep website SQLite access read-only.
- Keep generated README regions owned by the renderer.
- Add or update tests whenever observable behavior changes.
- Keep offline deterministic tests as the default development path.
- Do not add broad lint, type, test, or coverage suppressions to avoid fixing a real issue.
- Read files in full before wide-ranging changes; do not rely only on search snippets.

## Architectural Invariants

1. **Canonical state:** SQLite is the lifecycle source of truth.
2. **Canonical identity:** numeric LinkedIn job IDs identify listings.
3. **Strict acceptance:** ambiguous posting evidence, type, role, seniority, cycle, or geography is excluded according to policy.
4. **Conservative closure:** search-page absence does not close a job.
5. **Failure isolation:** one failed search cannot corrupt another search's lifecycle state.
6. **One writer:** canonical application state has one controlled repository writer.
7. **Bounded access:** requests, retries, concurrency, pages, results, and response sizes remain limited.
8. **Unauthenticated access:** no LinkedIn credentials, sessions, cookies, browser storage, or private endpoints.
9. **Read-only projections:** the website and README do not mutate canonical state.
10. **Deterministic behavior:** classification, persistence, rendering, and validation are reproducible.

Do not intentionally alter these contracts without explicit user direction and review of `architecture.md` plus `SECURITY.md`.

## Source Access and Security

LinkedIn collection is disabled by default and requires an authorization interlock. The interlock records an operator decision; it does not itself grant permission.
Unless the task explicitly requires authorized live access:
- use offline fixtures and synthetic data;
- run non-live tests;
- avoid collection commands;
- do not enable authorization variables.

Never add or use LinkedIn credentials, session cookies, authenticated browser automation, private APIs, CAPTCHA solving, proxy rotation for evasion, fingerprint evasion, anti-bot bypasses, or redirect-based endpoint discovery.
An upstream block, challenge, or access denial is a stop condition, not a problem to bypass. Never weaken, bypass, delete, or silently default an authorization gate to true.
Never commit or expose `.env` contents, tokens, cookies, authenticated HTML, production databases, SQLite sidecars, SSH keys, private host configuration, or raw environment dumps. Use placeholders and minimal sanitized fixtures.

## Data and Persistence

- Persist lifecycle changes through `Repository` methods.
- Keep transactions focused and short.
- Preserve provenance and search isolation.
- Use UTC-aware timestamps at domain boundaries.
- Treat ambiguous availability failures as inconclusive, not closure evidence.
- A schema change requires a new Alembic revision.
- Never rewrite an applied migration.
- Test migrations on a fresh database and representative prior state when existing data changes.
- Do not recommend deleting canonical state as the normal upgrade strategy.

## Search and Classification

Search configuration controls where the project looks. Classification controls what it may publish.
For `configs/searches/` changes:

- follow the search-registry schema and directory conventions;
- keep slugs stable, unique, lowercase, and kebab-case;
- avoid duplicate effective query identities;
- preserve configured request limits;
- justify scope and tuning in `notes`;
- update focused config tests.

For classification changes:

- preserve deterministic decisions and stable exclusion reasons;
- add nearby acceptance and rejection tests;
- preserve employment-type, seniority, technology, cycle/posting-date, and European-location checks;
- do not weaken a global rule merely to include one ambiguous listing.
Precision is an intentional product decision.

## Website

- Keep SQLite access server-side and read-only.
- Keep data/query helpers under `site/src/lib`.
- Keep browser interaction in client components.
- Preserve strict TypeScript, empty-state behavior, search, filters, sorting, pagination, and shareable URLs unless intentionally changing them.
- Preserve semantic HTML, keyboard accessibility, responsive behavior, and safe HTTPS external links.
- Prefer Tailwind utilities for component styling; keep global CSS minimal.
- Do not add write APIs, authentication, administrative mutation, saved applications, or user-provided content without explicit architecture and security review.

## README and Generated Content

The root README contains generated opportunity regions owned by `src/opportunities/readme.py`.

- Do not manually edit generated count or preview regions.
- Do not reproduce complete generated marker pairs in examples.
- Do not render and commit the README from an empty local database.
- Update generated regions only through the owning render command with representative canonical state.
- Run validation after rendering.

## Code Standards

Long-term maintainability is a core priority. Before adding logic, identify the layer that owns the behavior. Duplicate classification, normalization, lifecycle, validation, or presentation logic across layers is a code smell.
Keep changes focused. Avoid combining unrelated parser, schema, search, website, deployment, formatting, and documentation work.

### Python

- Use Python 3.12 syntax, UTF-8, LF endings, and the configured Ruff line length.
- Prefer precise domain models and protocols over broad `Any`.
- Preserve strict mypy compatibility.
- Favor clear control flow, early returns, and small focused functions.
- Validate external input and reject unknown fields where appropriate.
- Keep SQL writes in repository methods or migrations.
- Sanitize errors; never log response bodies, credentials, cookies, headers, or environment dumps.
- Avoid speculative abstractions and unnecessary helpers.

### TypeScript / React

- Preserve strict TypeScript and existing import/component conventions.
- Keep server-only database behavior out of client components.
- Prefer small components and pure helpers.
- Keep user-visible links validated and safe.
- Do not introduce new state-management or UI libraries for trivial needs.
- Run Prettier rather than hand-formatting against project style.

## Testing and Validation

Run the smallest focused test first, then every validation path affected by the change.
Python/docs:
```bash
make check
```

Equivalent core checks:

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

Website:

```bash
cd site
bun run ci
```

Useful focused checks:

```bash
uv run pytest tests/unit/test_linkedin.py -q
uv run pytest tests/unit/test_config.py -q
uv run pytest tests/integration/test_readme.py -q
uv run opportunities searches
uv run opportunities db-upgrade
```

Run `uv build` for packaging/dependency/entry-point changes. Run `docker compose config` and relevant image checks for container or deployment changes.
Live tests are opt-in and authorization-gated. Do not run them unless the task explicitly requires authorized live access.

## Documentation and Final Review

- Update docs when behavior, configuration, commands, architecture, or operational expectations change.
- Put task-oriented guides under `docs/guides/` and visual assets under `docs/assets/`.
- Generated files must be updated through their owning command.
- Never stage `.env`, local settings, database files, SQLite sidecars, caches, build output, quality reports, or authenticated fixtures.
Before handing off a code change:

```bash
git status --short
git diff --check
git diff
```

Confirm that affected tests pass, lifecycle/security invariants remain intact, generated files were updated correctly, documentation matches behavior, lockfile changes are intentional, and no secrets or runtime artifacts are included.

## User Override

If user instructions conflict with repository conventions, clarify the intended override when it materially changes behavior, compatibility, architecture, or safety.
Do not override safety rules silently. If the request would expose secrets, weaken the source-access boundary, mutate read-only projections, or bypass lifecycle protections, explain the conflict and use the safest compatible approach.
