# Testing strategy and quality gates

[← Maintainer handbook](../README.md) · [Local setup](../getting-started/setup.md) · [Architecture](architecture.md) · [Contributing](../../../CONTRIBUTING.md)

Test the contract that can hurt a user or canonical state, not incidental markup. Tests run offline with synthetic data by default. No normal gate requires source authorization, production data, or a running production service.

## What earns a test

| Risk | Contract | Best layer |
|---|---|---|
| Wrong roles published | Acceptance plus adjacent rejection cases; type/seniority/category/cycle/date/geography boundaries | Parameterized classifier and parser units |
| Valid history lost | Search failure isolation, absence safety, confirmations, reopening, stale evidence and monotonic timestamps | Repository + pipeline integration on migrated SQLite |
| Schema drift | Fresh/repeat upgrades, representative prior rows, preserved provenance, foreign keys and CHECK constraints | Migration integration and ORM comparison |
| Public/private data mixed | Explicit allowlists; CSV formula neutralization; JSON/schema/metadata hashes; URL-ID agreement | Python serialization contracts + HTTP API/download integration |
| Broken recovery | WAL-aware backup, manifest integrity, fail-closed restore, immutable release and atomic pointer | Snapshot integration + Linux shell tests |
| Silent collection drift | Large volume/acceptance shifts, empty searches, disappearing categories, parser field gaps, and country-mix changes | Pure data-quality analysis tests + bounded SQLite-baseline integration |
| Browser choices lost | Versioning, corruption, pruning, visit boundaries, storage denial, reloads and tab interaction | Pure state units + browser journeys |
| Divergent URLs/data | Filters, recency boundaries, deterministic sort/pagination, history, equivalent-query ETags | Shared-helper units/properties + HTTP/browser contracts |
| Inaccessible key actions | Keyboard save/apply/hide/restore, focus recovery, usable mobile scrolling, clear empty states | Playwright + axe |
| Deployment assumptions broken | Read-only mount, runtime origin, production headers, fixed downloads, standalone startup | Docker smoke + production build + Lighthouse |
| Docs leak private files | Public staging allowlist, symlink rejection, generated ownership, source/rendered links | Offline tooling tests + strict docs build |

Keep regressions near their owner. Assert resulting state and public responses rather than exact private helper calls, CSS classes, column widths, or generic framework behavior. Do not delete useful failure-path tests merely to lower the count. Coverage is a backstop, not a substitute for evidence-boundary tests.

## Suite map

The source-adjacent [test inventory and review](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/tests/TEST.md) explains every Python and website test, parameterized boundaries, and the cleanup decisions. Update it when adding, removing, moving, or changing a test's purpose.

- `tests/unit/`: classifier, transport, parser, config, serialization, snapshots, tooling and migration contracts. Shell tests use fake SSH/SFTP against disposable files.
- `tests/integration/`: CLI, repository, pipeline, availability, data-quality baseline persistence and README lifecycle behavior.
- `tests/benchmarks/`: offline parsing and full classifier decisions; compare only equivalent environments.
- `site/tests/unit/`: URL/API/state/serialization helpers, seeded bounded `fast-check` query-parser properties, and isolated startup/tooling regressions.
- `site/tests/e2e/`: HTTP contracts and representative browser journeys against synthetic SQLite and exports, including axe scans.

Do not use component string snapshots as substitutes for interaction tests. In particular, “button contains label” assertions do not demonstrate that saving persists, keyboard focus survives, or a private ID stays off the network.

## Validation paths

Run the smallest focused check first, then every affected gate. Commands below run from the repository root unless shown otherwise.

### Python and documentation

```bash
uv sync --frozen --dev
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest -m "not live and not performance" --cov \
  --cov-report=term-missing \
  --cov-report=xml:quality-reports/coverage.xml \
  --cov-report=json:quality-reports/coverage.json \
  --cov-report=html:quality-reports/coverage-html
uv run python scripts/docs/coverage_docs.py
uv run python scripts/database/check_migrations.py
uv run python scripts/docs/check_docs.py
uv run --frozen python scripts/docs/lint_docs.py
uv run --frozen --group docs python scripts/docs/build_docs.py
uv run --frozen --group docs python scripts/docs/check_built_docs.py
git diff --check
```

`make check` wraps this gate; `make coverage` refreshes the coverage table here. CI uses `scripts/docs/coverage_docs.py --check`, so refresh metrics after changing measured paths. [Documentation maintenance](documentation.md) owns the shared writing style, lint/build inputs, and generated regions. The documentation checks include diagram Markdown and the workflow, script, and test inventories; they do not regenerate the root README.

### Website validation

```bash
cd site
bun install --frozen-lockfile
bunx playwright install chromium
bun run ci
```

This runs Prettier, ESLint, strict TypeScript, the production Next.js build, Bun unit tests, and Playwright/axe against disposable synthetic state in `site/tests/e2e/.tmp/`. Browser tests use a separate development build directory.

Status fault-injection tests start the built standalone server on loopback port `3101` with a temporary fixture copy outside the development server's watched directories. Cases restore their own changes and run sequentially without skipping independent tests after a failure. Linux also exercises release cutover and missing-pointer rejection. Run `bun run build` before selecting these production tests with `test:e2e`; `bun run ci` already includes that build.

Focused examples:

```bash
uv run pytest tests/unit/test_classification.py tests/unit/test_linkedin.py -q
uv run pytest tests/integration/test_runner.py tests/integration/test_availability.py -q
cd site
bun run test:e2e -- --grep "shareable URL"
```

### Lighthouse and production build

After `bun run ci`, from `site/` in a POSIX shell:

```bash
OPPORTUNITIES_DATABASE_PATH="$(pwd)/tests/e2e/.tmp/opportunities.db" \
OPPORTUNITIES_PUBLIC_EXPORT_DIR="$(pwd)/tests/e2e/.tmp" \
CHROME_PATH="$(bun -e 'import {chromium} from "@playwright/test"; console.log(chromium.executablePath())')" \
  bun run lighthouse
```

Use native absolute paths on Windows. Lighthouse audits the built standalone homepage and indexable second page twice each. Thresholds: performance ≥0.80, accessibility/best practices/SEO ≥0.95, CLS ≤0.1, total blocking time ≤400 ms. Optional analytics endpoints are blocked. Filtered views are deliberately non-indexable and remain covered by Playwright/axe, not an inappropriate SEO threshold. Reports are ignored locally and retained seven days in CI on failure.

### Migrations, exports, and packaging

`scripts/database/check_migrations.py` upgrades an isolated database and compares ORM metadata to Alembic head. Migration tests also cover representative prior state; never rewrite applied history.

The integration suite generates README and CSV/JSON/metadata projections in temporary directories and validates them against migrated synthetic SQLite and the shared schema. API HTTP tests validate responses against the same schema. Never run `render` against an empty local database and commit the resulting product preview. With reviewed representative state only, use `opportunities render` followed by `opportunities validate`.

Run `uv build` for packaging, dependencies, entry points or public package metadata changes.

### Containers and security

```bash
docker compose config --quiet
docker compose build
docker compose run --rm opportunities --help
```

Run container checks only with disposable synthetic mounts; default Compose paths describe production topology. [Docker CI](../operations/automation.md#validation-workflows) adds Actionlint, zizmor, Hadolint, Trivy fixable high/critical scanning, production-target SPDX SBOMs, and migrated read-only site/export/header smoke tests. Main-only GitHub attestations bind the SBOM and build-evidence files to their workflow; [Containers and deployment](../operations/deployment.md#sbom-and-build-provenance) documents their scope and verification. Linux restore/deploy/release-pointer tests are skipped on Windows: run them in isolated Linux before release. A skipped test is not a pass.

CodeQL, Gitleaks, Dependency Review and Scorecard have distinct roles in [Automation](../operations/automation.md). Run available local dependency/static analysis too; disclose unfixed findings rather than suppressing them. Patched `brace-expansion`, `tmp`, and CommonJS-compatible `uuid` overrides support older development dependencies; remove only after upstream fixes and rerunning the audit.

Lighthouse's transitive `basic-ftp` is pinned to `6.2.1` to fix [GHSA-c475-qrg2-pj4r](https://github.com/advisories/GHSA-c475-qrg2-pj4r), a directory-listing parser denial of service. It retains the CommonJS API used by `get-uri` and adopts v6's safer default of rejecting separate transfer hosts. An offline subprocess test checks the client API surface and bounds malformed-listing parsing without opening an FTP connection. Remove the override once upstream selects a patched version and the audit and Lighthouse checks pass.

Lighthouse's development-only `extract-zip` dependency currently has two unpatched high-severity symlink traversal advisories: [GHSA-jmr9-qjv8-65gv](https://github.com/advisories/GHSA-jmr9-qjv8-65gv) and [GHSA-7pqw-9j4j-h8q3](https://github.com/advisories/GHSA-7pqw-9j4j-h8q3). Local/CI audits use an already installed Chromium via `CHROME_PATH`; never download/extract untrusted browser archives. These packages are not standalone website runtime dependencies, but the findings remain open and must not be suppressed as fixed.

### Benchmarks

```bash
uv run pytest tests/benchmarks --benchmark-only \
  --benchmark-json=quality-reports/benchmark.json
```

Two hot-path benchmarks cover guest search parsing and classification. They are trend evidence, not portable absolute performance promises. Run them for parser/classifier changes and repository-wide reviews.

## Coverage baseline

Branch-aware coverage measures classification, collection-level data-quality checks, collection orchestration, availability, and repository lifecycle logic. The configured combined threshold remains **85%**. Reports live in ignored `quality-reports/`; Python CI retains them for 30 days and publishes a job summary. This table is generated from the same report, not hand-maintained.

<!-- BEGIN PYTHON COVERAGE -->
| Metric | Current | Required |
|---|---:|---:|
| Combined statement and branch coverage | 99.1% | ≥ 85.0% |
| Branch coverage | 98.2% | Reported |
| Classifier branch coverage | 97.5% | Reported |
<!-- END PYTHON COVERAGE -->

## Fixtures and live tests

Use fixed UTC clocks, numeric synthetic IDs, temporary paths, injected clients, and minimal sanitized HTML. Preserve malformed/missing-field and challenge cases. Do not capture authenticated HTML, cookies, headers, or private browser state.

Collection workflows retain `data-quality-report.json` as a separate artifact. Its checks use synthetic offline tests; no normal validation job enables LinkedIn access. The report contains only aggregate counts, rates, search slugs, and check outcomes.

For non-live Python tests, `tests/conftest.py` clears inherited application and deployment settings, provides a temporary working directory and home, and rejects real HTTPX transports. Injected mock transports still exercise authorization, response bounds and retries. Use explicit repository paths for checked-in fixtures; do not rely on the caller's working directory or `.env`. The HTTPX guard is not a general socket or subprocess sandbox.

Linux shell tests use `tests/shell_helpers.py` to give subprocesses an environment allowlist, temporary home and working files, offline uv settings, and blocking SSH/SCP/SFTP fallbacks. Tests needing transport behavior provide fake binaries ahead of those blockers. Subprocess timeouts bound failures; lock tests synchronize on acquisition rather than sleeping and hoping the lock is held.

README validation workflow regressions also require Bash and `jq`; they skip when either tool is unavailable. They execute the checked-in workflow scripts with fake GitHub CLI calls and real `jq` filters against synthetic PR metadata and run records. They never dispatch workflows, push branches, merge PRs, or contact GitHub.

Live tests require the exact marker selection `-m live` plus both `OPPORTUNITIES_LIVE_TESTS=1` and `OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true`. Other marker expressions cannot enable them. These flags do not grant permission. Normal CI never enables them; an access challenge is a stop condition.

## Final review

Inspect `git status --short`, `git diff --check`, and the complete diff. Confirm generated boundaries, lockfile intent, docs, lifecycle/security/privacy invariants, and every affected gate. Record the exact commands, failures, skips, environment limitations, and remaining risks. Never claim checks that did not run.
