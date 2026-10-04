# Contributing to European Tech Opportunities 2027

[← Project README](README.md) · [Documentation home](docs/README.md) · [Maintainer handbook](docs/maintainers/README.md) · [Security policy](SECURITY.md) · [Code of Conduct](CODE_OF_CONDUCT.md)

Contribute a focused fix, test, accessibility improvement, search definition, or documentation update. This guide owns the contribution workflow; the maintainer handbook owns implementation and operating procedures.

## Suggest a listing or report a problem

You do not need to install the project or write code:

- [Suggest a listing](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=add-position.yml) with its public URL and evidence of eligibility. Suggestions are reviewed before publication.
- [Report a product problem](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=bug-report.yml) with reproducible steps and sanitized screenshots.
- [Propose a feature](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=feature-request.yml) by explaining the user need and relevant compatibility or safety concerns.
- Report vulnerabilities **privately** through the [security policy](SECURITY.md), not a public issue or pull request.

For help using the directory, start with the [user guides](docs/users/README.md).

## Make a code or documentation change

1. Search existing issues and read the relevant guide below. Discuss architectural, schema, source-access, lifecycle, deployment, or trust-boundary changes before implementation.
2. Fork the repository and branch from `main`. Recommended prefixes are `feat/`, `fix/`, `docs/`, `test/`, and `chore/`, followed by a short kebab-case description.
3. Follow [local setup](docs/maintainers/getting-started/setup.md). Use `uv` for Python and Bun inside `site/`; keep source collection disabled and use disposable synthetic data.
4. Reproduce the issue offline, make one focused change, and add or update tests for observable behavior.
5. Run the narrowest relevant test first, then every affected validation gate. Update the canonical documentation when behavior or operating expectations change.
6. Inspect the complete diff and open a pull request using the repository template. State what changed, why, what is out of scope, safety and compatibility impact, and the exact checks run.

Coding agents must also follow the root [agent guidelines](AGENTS.md) and any nested instructions before editing. Do not load unrelated personal context or skills.

> [!IMPORTANT]
> LinkedIn access requires express authorization. Public pages, environment flags, and participation in this project do not grant permission. Normal development and review require no live source access.

## Choose the correct path

| Change | Read first | Validation |
|---|---|---|
| Python or CLI | [Architecture](docs/maintainers/engineering/architecture.md) · [Testing](docs/maintainers/engineering/testing.md) | `make check` or its documented `uv` equivalent |
| Classification | [Classification evidence](docs/maintainers/engineering/classification.md) | Nearby acceptance and rejection tests, then the Python gate; benchmarks for hot-path changes |
| LinkedIn parser or transport | [Collection boundary](docs/maintainers/engineering/classification.md#collection-boundary) · [Security policy](SECURITY.md) | Minimal sanitized fixtures, parser/transport tests, then the Python gate |
| Website | [Website engineering](docs/maintainers/engineering/website.md) · [User behavior](docs/users/README.md) | `cd site && bun run ci` |
| Search YAML | [Search registry](docs/maintainers/engineering/search-registry.md) | Registry inspection and config tests below |
| Schema or migration | [Database and lifecycle](docs/maintainers/operations/database.md#migrations) | Fresh and representative upgrades, repository tests, and migration checks |
| Docker or automation | [Containers and deployment](docs/maintainers/operations/deployment.md) · [Automation](docs/maintainers/operations/automation.md) | Compose validation and affected image, workflow, and runtime checks |
| Documentation | [Documentation maintenance](docs/maintainers/engineering/documentation.md) | `make docs-site`, including both prose linters, plus `git diff --check` |

The [testing guide](docs/maintainers/engineering/testing.md#validation-paths) owns full commands, platform requirements, benchmarks, and optional checks. Run `uv build` for packaging, dependency, or entry-point changes. Do not claim an unrun or skipped check passed; explain limitations in the pull request. Reviewers and CI must not require live LinkedIn access.

## Project contracts

Preserve canonical SQLite state, numeric LinkedIn identity, conservative classification and closure, failed-search isolation, one controlled repository writer, authorized bounded unauthenticated source access, and read-only public projections.

The [architecture guide](docs/maintainers/engineering/architecture.md#architectural-principles) defines these invariants. The [security policy](SECURITY.md) defines prohibited source-access methods and trust boundaries. An upstream challenge, failed migration, invalid snapshot, or mismatched reviewed projection is a stop condition, not permission to bypass checks.

- Keep business behavior under `src/opportunities/`, not workflows or ad-hoc scripts.
- Keep transport, parsing, normalization, classification, persistence, and presentation separate.
- Use repository methods for application writes and new Alembic revisions for schema changes; never rewrite applied migrations.
- Preserve strict Python and TypeScript typing, UTC-aware domain timestamps, deterministic ordering, and sanitized errors.
- Avoid broad lint, type, test, or coverage suppressions and unrelated cleanup.
- Keep website SQLite access server-side and read-only. Preserve accessibility, responsive behavior, safe listing links, empty states, and shareable URLs.
- Keep saved/applied/hidden lists and visit state browser-only: never upload them or add them to public URLs, the API, or analytics. See the [privacy notice](PRIVACY.md).

Authentication, new providers, multiple writers, server-stored applications, user content, write APIs, or administrative mutation require explicit architecture and security review. LinkedIn credentials, sessions, authenticated browser collection, private endpoints, CAPTCHA solving, and evasion remain prohibited.

## Data collection and classification

### Adding or changing a search

Follow the [search registry schema and production conventions](docs/maintainers/engineering/search-registry.md#validation-rules). Keep slugs stable and effective queries unique, include Internship and New Grad terms without requiring a year, use the dynamic `cycle` posting filter, and justify conservative limits in `notes`. Employer allowlists require exact normalized names; geography IDs must be independently verified, never invented.

Validate offline:

```bash
uv run opportunities searches
uv run pytest tests/unit/test_config.py -q
```

If registry counts change, follow the [generated-content procedure](docs/maintainers/engineering/documentation.md#generated-content-boundaries); do not render the committed README from an empty local database. Only an expressly authorized operator may additionally preview one search with `opportunities search-test <slug>`.

### Changing classification

`configs/categories.yml` owns keywords; `src/opportunities/pipeline/classification.py` owns deterministic decisions. Preserve title-explicit type evidence, seniority exclusions, technology relevance, cycle/posting-date precedence, European geography, and stable exclusion reasons. Add adjacent positive and negative tests; do not weaken a global rule to admit one ambiguous listing. The [classification guide](docs/maintainers/engineering/classification.md) owns the exact evidence policy.

### Changing LinkedIn parsing

Use minimal sanitized guest-page fixtures with synthetic numeric IDs. Preserve independent detail identity, challenge detection, response bounds, title prefiltering, and explicit unavailability handling. Test changed, malformed, and missing-field cases. Do not commit full pages, tracking or personal data, cookies, headers, browser profiles, or authenticated HTML.

## Documentation and generated files

Use plain-language task guides under `docs/users/` and technical procedures under `docs/maintainers/`. Link to each topic's canonical owner instead of duplicating instructions. Follow the [shared writing style](docs/maintainers/engineering/documentation.md#shared-writing-style), and update the documentation router, audience index, and MkDocs navigation when adding or moving a public guide.

Generated README regions, registry counts, coverage metrics, public exports, diagrams, and media retain their [documented owners](docs/maintainers/engineering/documentation.md#generated-content-boundaries). Do not edit generated values manually or render the committed opportunity preview from empty development state. Keep public visual assets sanitized; read the [video runbook](docs/assets/promo/maintainers/VIDEO.md) before changing the promotional film.

## Before requesting review

Use a concise conventional title, such as `fix: preserve pagination after filtering`. Complete the pull-request template, including exact validation results and any omissions. For visible website changes, include sanitized desktop/mobile and light/dark evidence where relevant.

Inspect:

```bash
git status --short
git diff --check
git diff
```

Confirm the diff contains no `.env`, local settings, databases, SQLite sidecars, credentials, cookies, private HTML, logs, caches, quality reports, or build output. Lockfile, migration, generated-file, and documentation changes must be intentional. Preserve the [automation permission and state-handoff boundaries](docs/maintainers/operations/automation.md#workflow-permissions) when changing workflows.

All participation follows the [Code of Conduct](CODE_OF_CONDUCT.md). Use the [security policy](SECURITY.md) for private vulnerability disclosure.
