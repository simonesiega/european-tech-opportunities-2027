# Changelog

All notable changes to European Tech Opportunities 2027 are documented in this file.

## [Unreleased]

### Added

- Add a manual `skip_availability` option to the nightly workflow; scheduled runs always audit stored jobs before scraping.
- Add Italian, French, German, Spanish, and Simplified Chinese READMEs to the documentation site, with reciprocal language navigation and synchronized generated data.

### Changed

- Make default Compose pipeline startup show help instead of upgrading SQLite; migrations remain explicit maintenance commands.
- Run scheduled full updates every three UTC days with a fixed cadence across month boundaries; retain additional manual updates for busy hiring periods and keep source-access safeguards unchanged.
- Allow HTTP 429-only partial availability audits to retain completed checks through validated, manual-review publication while skipping all subsequent source requests and nightly scraping.
- Refresh localized README counts, review seals, and opportunity previews alongside English in dataset automation, preserving localized presentation and authored text.

### Fixed

- Document the GitHub-only operating loop, ongoing maintenance, and statistics ownership; align database auditing guidance with the three-day update cadence.
- Correct the privacy notice's README image-provider disclosure.
- Reuse fixed-locale sort collators, normalize distinct locations once, and avoid repeating unfiltered hydration sorting to reduce large-directory rendering work.
- Reject namesake cities with unrecognized geographic qualifiers and require technical evidence for generic research roles; exclude nontechnical roles despite software keywords.
- Normalize country names, codes, and city-only or remote aliases across directory, API, and feed filters without broadening multi-location queries; resolve the shared vocabulary in development builds.
- Reject C0/C1 control characters in listing API queries.
- Keep approved public-listing HTTP 301 responses from blocking validated HTTP 429 partial availability publication, without treating redirects as confirmed checks or masking independent failures.
- Preserve independent in-flight and interrupted-retry failures after a sibling source stop so HTTP 429 cannot incorrectly authorize partial publication; retain denial classification when response cleanup fails.
- Keep RSS and Atom ordering consistent with the directory and API, including microsecond timestamps and numeric job-ID ties.
- Count nested search YAML files in generated registry documentation and check Python lockfile consistency in CI.
- Include the changelog in documentation checks and show feeds and dataset status in repository maps.
- Clarify scheduled collection versus reviewed production deployment, multilingual README handoffs, and first-seen preview ordering.
- Block collection publication after unexpected, parsing, or unrelated transport failures, including concurrent failures alongside HTTP 429, while preserving completed search transactions.

### Removed

- Remove the standalone promotional MP3 from the public tree and documentation allowlists; document Pixabay soundtrack permissions while preserving the scored film.

### Security

- Remove Lighthouse's vulnerable `extract-zip` dependency through a pinned upstream Puppeteer upgrade, retaining the performance gate and dependency alerts.
- Reject nonregular public downloads without blocking on named pipes, preserving sanitized GET and HEAD failures.
- Preserve pre-existing snapshot-replacement staging, aliases, and sidecars before storage access; create final local staging exclusively.
- Replace inline-script CSP permission with per-request nonces while preserving theme, analytics, and directory hydration.
- Bound concurrent dataset-status reads and reject oversized or nonregular files before hashing, without blocking on named pipes or caching health assertions.
- Exclude local logs, uv caches, and Lighthouse reports from container build contexts.

## [1.0.0] - 2026-10-07

### Added

- Added a searchable directory of validated European technology internships and New Grad roles for the 2027 hiring cycle, with country, company, category, employment-type, and first-seen filters.
- Added deterministic sorting, pagination, and shareable search URLs, with responsive layouts, light and dark themes, keyboard navigation, and visible focus.
- Added browser-only saved, applied, and hidden lists, plus indicators for opportunities discovered since the previous visit, without accounts or device synchronization.
- Added complete CSV and JSON downloads, checksum metadata, shared JSON Schema, and a read-only v1 public API with filtering, sorting, pagination, cache validators, and dataset freshness status.
- Added RSS and Atom feeds for recent open opportunities, with optional employment-type, country, and category filters.
- Added a bounded Python collection pipeline with normalization and deterministic checks for employment type, seniority, technology, hiring cycle, posting date, and European geography.
- Added canonical SQLite lifecycle history, transactional repository writes, Alembic migrations, search provenance, and conservative availability checks that never treat search disappearance alone as closure evidence.
- Added maintainer-only offline insertion of individual listings or reviewed batches, without inventing collection provenance or reopening closed rows.
- Added automated data-quality drift detection with aggregate reports, baseline warm-up, warning thresholds, and blocking publication gates.
- Added read-only website, API, feed, download, and bounded README projections of canonical state, with a review seal covering the complete public directory.
- Added scheduled collection and availability workflows, verified snapshot recovery, reviewed-state deployment, and atomic release activation with rollback.
- Added user guides, a maintainer handbook, release notes, repository diagrams, and a MkDocs documentation site at `docs.techopportunities.eu`.
- Added offline unit and integration tests, strict typing, schema validation, browser journeys, accessibility checks, parser/classifier benchmarks, and Lighthouse performance regression checks.
- Added coverage enforcement and generated coverage documentation, migration checks, container smoke tests, and source and rendered documentation validation.
- Added an MIT license, contribution guidelines, a Code of Conduct, security and privacy policies, and issue and pull-request templates.

### Changed

- Expanded the original internships-only project to include New Grad opportunities and renamed the Python package and CLI to `opportunities`.
- Moved the public directory to `techopportunities.eu` and added canonical URLs, shareable directory views, and search-engine metadata.
- Replaced fixed discovery dates with cycle-aware posting windows while keeping discovery configuration separate from deterministic acceptance rules.
- Reorganized documentation into user and maintainer guides, with task-oriented navigation and redirects from older guide URLs.
- Bounded scheduled availability audits to 250 due listings per run with a five-day interval, instead of checking the complete directory every night.

### Fixed

- Fixed mobile export controls, directory header layout shifts, and filtered views losing the total open-role count.
- Fixed server-rendered HTML publishing fabricated saved, applied, hidden, and new-role counts before browser-local state was available.
- Fixed Atom feed validation by supplying the required author metadata.
- Fixed nightly validation races by waiting for checks on the exact generated pull-request head before requesting auto-merge.
- Fixed missing README proposals blocking later updates by adding recovery from verified canonical state without bypassing public-state review.
- Fixed approved numeric public-listing HTTP `301` responses to remain inconclusive, preserving listings and unrelated checks without following redirects or inspecting their destinations or bodies.
- Fixed snapshot SFTP publication after transient disconnects with bounded retries, byte-verified reconciliation, and refusal to overwrite conflicting objects or newer state.
- Fixed public downloads to stream from opened regular files, bound memory use, support body-free HEAD responses, and preserve sanitized unavailable responses.

### Security

- Required express source permission for collection, with bounded unauthenticated requests and no source accounts, private APIs, or anti-bot bypasses.
- Stopped follow-on source processing and publication after authentication denials, rate limits, challenges, and blocking redirects.
- Kept personal lists and visit timestamps in browser storage, outside SQLite, shared URLs, public data, and analytics.
- Added validated public listing links, spreadsheet-safe CSV text, explicit public field allowlists, bounded API inputs, defensive website headers, and sanitized errors.
- Added unprivileged containers, read-only website database access, verified snapshots, and atomic dataset publication, keeping canonical databases and manifests outside public artifacts and caches.
- Rejected unexpected SQLite snapshot sidecars so unhashed WAL or journal state cannot silently enter verification or publication.
- Restricted Python package resources to checked-in configuration, migrations, and schemas, excluding ignored operator settings, credentials, and runtime state.
- Added CodeQL, Gitleaks, Dependency Review, zizmor, OpenSSF Scorecard, and container vulnerability checks, with pinned workflow dependencies and least-privilege permissions.
- Added production-container SPDX SBOMs, checksum-backed build evidence, and main-branch-only GitHub attestations.
- Updated `brace-expansion` and `sharp` to patched releases and retained dependency overrides for affected transitive packages.
