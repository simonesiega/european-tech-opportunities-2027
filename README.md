<h1 align="center">European Tech Opportunities 2027</h1>

<p align="center">
  <strong>Find validated technology internships and New Grad opportunities for the 2027 hiring cycle across Europe.</strong>
</p>

<p align="center">
  <a href="https://opportunities2027.simonesiega.com/">Directory</a> ·
  <a href="#run-locally">Run locally</a> ·
  <a href="docs/README.md">Documentation</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<!-- BEGIN OPPORTUNITY COUNTS -->
<p align="center">
  <strong>Last updated: September 12, 2026 at 09:09 UTC</strong><br>
  <img src="https://img.shields.io/badge/Total%20opportunities-718-2563eb?style=for-the-badge" alt="Total opportunities: 718" />
  <img src="https://img.shields.io/badge/Internships-318-16a34a?style=for-the-badge" alt="Internships: 318" />
  <img src="https://img.shields.io/badge/New%20Grad-400-9333ea?style=for-the-badge" alt="New Grad opportunities: 400" />
</p>
<!-- END OPPORTUNITY COUNTS -->

<p align="center">
  <a href="https://opportunities2027.simonesiega.com/"><strong>Open the searchable opportunity directory →</strong></a>
</p>

<p align="center">
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml/badge.svg" alt="Python CI status" />
  </a>
<!-- BEGIN PYTHON COVERAGE BADGE -->
  <a href="#python-quality-baseline">
    <img src="https://img.shields.io/badge/critical_path_coverage-90.1%25_%7C_82.7%25_branches-brightgreen" alt="Critical path coverage: 90.1%, including 82.7% branch coverage" />
  </a>
  <!-- END PYTHON COVERAGE BADGE -->
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/simonesiega/european-tech-opportunities-2027" alt="MIT license" />
  </a>
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/stargazers">
    <img src="https://img.shields.io/github/stars/simonesiega/european-tech-opportunities-2027?style=flat" alt="GitHub stars" />
  </a>
</p>

## Overview

European Tech Opportunities 2027 is an open-source data product that combines a searchable public directory with an automated collection, classification, and lifecycle pipeline. It removes common job-search noise—mixed hiring cycles, senior roles, unrelated positions, and unsupported locations—by publishing only listings that pass deterministic checks.

The project intentionally favors precision over coverage. Relevant listings may be absent when they fall outside the configured searches or do not provide enough evidence to satisfy every publication rule.

## Website preview

<p align="center">
  <img
    src="docs/assets/sites/White_theme.webp#gh-light-mode-only"
    alt="Searchable European Tech Opportunities 2027 directory in light mode"
    width="100%"
  />
  <img
    src="docs/assets/sites/Dark_theme.webp#gh-dark-mode-only"
    alt="Searchable European Tech Opportunities 2027 directory in dark mode"
    width="100%"
  />
</p>

The public directory has surpassed **1,000 unique visitors since launch**. It is the primary user interface, with full-text search; Internship and New Grad filtering; company, country, and category filters; sorting; pagination; light and dark themes; and direct links to the original listings.

## Opportunity directory

Browse the complete live collection at **[opportunities2027.simonesiega.com](https://opportunities2027.simonesiega.com/)**. The repository keeps only the five most recently posted opportunities of each employment type as a lightweight preview; use the website for the complete searchable collection.

<!-- BEGIN OPPORTUNITIES -->
**Open opportunities:** 718 (Internships: 318 · New Grad: 400)<br>
**Last successful collection:** September 12, 2026 at 09:09 UTC

Browse and filter the complete directory at **[https://opportunities2027.simonesiega.com/](https://opportunities2027.simonesiega.com/)**.

### Latest New Grad opportunities

Showing the 5 most recently posted of 400 open New Grad opportunities:

| Company | Title | Location | Listing |
|---|---|---|---|
| ClearScore | Graduate Software Engineer | London, England, United Kingdom | [View](<https://www.linkedin.com/jobs/view/4466410753>) |
| Content Guru | Graduate Quality Assurance Engineer | Porto, Porto, Portugal | [View](<https://www.linkedin.com/jobs/view/4466340971>) |
| Julius Baer | University Graduate – Data Engineer 100% \(f/m/d\) | Luxembourg | [View](<https://www.linkedin.com/jobs/view/4466329677>) |
| NXP Semiconductors | Graduate AI and Software Engineer - Automotive MPUs | Glasgow, Scotland, United Kingdom | [View](<https://www.linkedin.com/jobs/view/4466307687>) |
| Tenth Revolution Group | Graduate Developer | Oslo, Norway | [View](<https://www.linkedin.com/jobs/view/4464201092>) |

### Latest internships

Showing the 5 most recently posted of 318 open internships:

| Company | Title | Location | Listing |
|---|---|---|---|
| TXT Quence | Junior Software Engineer \(Internship\) | Cologno Monzese, Lombardy, Italy | [View](<https://www.linkedin.com/jobs/view/4464894787>) |
| Nokia | AI Software Engineer – Intern | Vimercate, Lombardy, Italy | [View](<https://www.linkedin.com/jobs/view/4464205151>) |
| Quinten Health | Data Scientist Internship \(6 months\) | Paris, Île-de-France, France | [View](<https://www.linkedin.com/jobs/view/4464892171>) |
| MakiPeople | Security Engineer - Final year Intern | Paris, Île-de-France, France | [View](<https://www.linkedin.com/jobs/view/4466313142>) |
| Amadeus | Internship - Security engineer | Villeneuve-Loubet, Provence-Alpes-Côte d'Azur, France | [View](<https://www.linkedin.com/jobs/view/4464547228>) |
<!-- END OPPORTUNITIES -->

Listings can change or expire. Verify the role, eligibility requirements, location, deadline, compensation, and visa or work-authorization requirements on the original listing before applying.

Missing a relevant opportunity? [Suggest a listing](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=add-position.yml).

## Publication rules

A listing is published only when all six checks pass:

| Check | Required evidence |
|---|---|
| Employment type | The title explicitly identifies either an internship (including placement or co-op) or a New Grad role. Internship terminology takes precedence if both appear. |
| Posting date | LinkedIn’s relative posting age resolves to May 1, 2026 or later; missing or older posting metadata is excluded for new listings. |
| Seniority | The title contains no configured senior-level or management terminology. |
| 2027 cycle | Explicit `2027` evidence is accepted; an otherwise eligible listing with no explicit cycle year is accepted when posted on or after May 1, 2026, while any explicit conflicting cycle year—including 2025 or 2026—is rejected. Graduation-year eligibility alone is ignored for internships. |
| Technology role | The title, or a narrowly allowed description fallback, matches a configured technology category. |
| European location | The parsed location explicitly resolves to Europe or a supported European country. |

Ambiguous evidence is excluded rather than guessed. Search-page absence never closes a listing; only explicit unavailability evidence can change lifecycle state. See [Architecture](docs/guides/development/architecture.md) and [Database lifecycle](docs/guides/operations/database.md) for the exact acceptance and closure rules.

## Engineering highlights

- **End-to-end data product:** bounded asynchronous Python collection and a searchable server-rendered TypeScript/Next.js opportunity directory.
- **Deterministic classification:** explicit rules assign `internship` or `new-grad`, then verify posting recency, cycle, technology category, seniority, and European location.
- **Transactional lifecycle state:** SQLite persistence records provenance, first/last-seen timestamps, isolated search outcomes, conservative closure evidence, and daily full-state availability checks.
- **Tested web application:** query-parameter-backed filtering, sortable and paginated results, unit tests, Playwright end-to-end coverage, TypeScript checks, and production-build validation.
- **Production engineering:** Alembic migrations, scheduled automation, restore-verified timestamped backups, atomic deployment, strict typing, CI across Python/site/containers, thresholded branch coverage, and parsing/classification benchmarks.

### Python quality baseline

The offline suite measures critical classification and lifecycle paths and enforces the configured combined coverage threshold.

<!-- BEGIN PYTHON COVERAGE -->
| Metric | Current | Required |
|---|---:|---:|
| Combined statement and branch coverage | 90.1% | ≥ 85.0% |
| Branch coverage | 82.7% | Reported |
| Classifier branch coverage | 97.5% | Reported |
<!-- END PYTHON COVERAGE -->

The badge and table are generated from the same coverage report used by the quality gate. Run `make coverage` after changing Python behavior or tests.

[Python CI](https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml) verifies that committed metrics are current and publishes the complete statement, branch, and per-module coverage reports alongside parsing and classification benchmarks. Compare benchmark timings only across equivalent environments.

[Site CI](https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/site-ci.yml) separately enforces formatting, linting, TypeScript type checking, a production build, unit tests, and Playwright end-to-end tests.

## How it works

<div align="center">
<pre>
validated search definitions
↓
bounded LinkedIn guest HTML collection
↓
strict type and technology classification
↓
transactional SQLite lifecycle state
↓
┌──────────────────────┬──────────────────────┐
│ searchable website   │ README preview       │
│ all open listings    │ 5/type latest rows   │
└──────────────────────┴──────────────────────┘
</pre>
</div>

SQLite is the canonical store. The website and README are read-only projections of accepted listings and their lifecycle state.

See the [architecture guide](docs/guides/development/architecture.md) for the complete data flow, component boundaries, and extension policy.

## Run locally

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), and Git.

```bash
git clone https://github.com/simonesiega/european-tech-opportunities-2027.git
cd european-tech-opportunities-2027
uv sync --frozen --dev
cp .env.example .env
uv run opportunities db-upgrade
uv run opportunities stats
```

A fresh local database intentionally contains no listings. Use the hosted directory for current data.

Continue with the [installation guide](docs/guides/getting-started/installation.md) for the local website, Windows commands, Docker, and verification. Runtime settings are documented in [configuration](docs/guides/getting-started/configuration.md), and CLI commands in the [CLI reference](docs/guides/user-guide/cli.md).

## Documentation

Use the [documentation hub](docs/README.md) to find the canonical guide for each task.

| Area | Canonical guides |
|---|---|
| Setup | [Installation](docs/guides/getting-started/installation.md) · [Configuration](docs/guides/getting-started/configuration.md) |
| Using the project | [Website](docs/guides/user-guide/website.md) · [CLI](docs/guides/user-guide/cli.md) · [Search registry](docs/guides/user-guide/search-registry.md) |
| Production operation | [Automation](docs/guides/operations/automation.md) · [Database](docs/guides/operations/database.md) · [Docker](docs/guides/operations/docker.md) · [Troubleshooting](docs/guides/operations/troubleshooting.md) |
| Development | [Architecture](docs/guides/development/architecture.md) · [Development](docs/guides/development/development.md) · [Contributing](CONTRIBUTING.md) |

## Responsible operation

> [!IMPORTANT]
> LinkedIn collection is disabled by default. Public accessibility is not authorization to automate access. The authorization interlock records an operator decision; it does not grant permission.

The project does not use credentials, sessions, browser automation, private endpoints, proxies, CAPTCHA bypasses, or anti-bot evasion. It is not affiliated with or endorsed by LinkedIn or any listed employer.

Read [`SECURITY.md`](SECURITY.md) before operating collection infrastructure.

## Contributing

Focused improvements to strict classification, sanitized parser fixtures, search coverage, lifecycle safety, tests, website usability, and documentation are welcome.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request. Participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Licensed under the [MIT License](LICENSE).

## Contributors

<p align="center">
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=simonesiega/european-tech-opportunities-2027&max=24&columns=12" alt="Contributors" />
  </a>
</p>
