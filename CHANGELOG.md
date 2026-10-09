# Changelog

All notable changes to European Tech Opportunities 2027 are documented in this file.

## [Unreleased]

### Breaking Changes

### Added

### Changed

### Fixed

### Removed

### Security

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
