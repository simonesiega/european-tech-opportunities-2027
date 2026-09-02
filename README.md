<h1 align="center">European Tech Opportunities 2027</h1>

<p align="center">
  An open-source opportunity directory and data pipeline for discovering validated 2027 technology internships and New Grad opportunities across Europe.
</p>

<!-- BEGIN OPPORTUNITY COUNTS -->
<p align="center">
  <strong>Last updated: September 2, 2026 at 09:00 UTC</strong><br>
  <img src="https://img.shields.io/badge/Total%20opportunities-658-2563eb?style=for-the-badge" alt="Total opportunities: 658" />
  <img src="https://img.shields.io/badge/Internships-294-16a34a?style=for-the-badge" alt="Internships: 294" />
  <img src="https://img.shields.io/badge/New%20Grad-364-9333ea?style=for-the-badge" alt="New Grad opportunities: 364" />
</p>
<!-- END OPPORTUNITY COUNTS -->

<p align="center">
  <a href="https://opportunities2027.simonesiega.com/"><strong>Open the searchable opportunity directory →</strong></a>
</p>

<p align="center">
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml/badge.svg" alt="Python CI status" />
  </a>
  <a href="#python-quality-baseline">
    <img src="https://img.shields.io/badge/critical_path_coverage-89.9%25_%7C_81.8%25_branches-brightgreen" alt="Critical path coverage: 89.9%, including 81.8% branch coverage" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/simonesiega/european-tech-opportunities-2027" alt="MIT license" />
  </a>
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/stargazers">
    <img src="https://img.shields.io/github/stars/simonesiega/european-tech-opportunities-2027?style=flat" alt="GitHub stars" />
  </a>
</p>

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

The live website is the primary user interface. It provides full-text search; Internship and New Grad filtering; company, country, and category filters; sorting; pagination; themes; and direct links to the original listings.

## Contents

- [Opportunity directory](#opportunity-directory)
- [Publication rules](#publication-rules)
- [Why this project exists](#why-this-project-exists)
- [Engineering highlights](#engineering-highlights)
- [How it works](#how-it-works)
- [Run locally](#run-locally)
- [Documentation](#documentation)
- [Responsible operation](#responsible-operation)
- [Contributing](#contributing)
- [License](#license)
- [Contributors](#contributors)

## Opportunity directory

Browse every open internship and New Grad listing at **[opportunities2027.simonesiega.com](https://opportunities2027.simonesiega.com/)**. Coverage is intentionally conservative rather than exhaustive: listings outside the configured searches, or without sufficient explicit evidence, may not appear.

The repository shows only the five latest opportunities of each employment type. Use the live directory for the complete searchable collection.

<!-- BEGIN OPPORTUNITIES -->
**Open opportunities:** 658 (Internships: 294 · New Grad: 364)<br>
**Last successful collection:** September 2, 2026 at 09:00 UTC

Browse and filter the complete directory at **[https://opportunities2027.simonesiega.com/](https://opportunities2027.simonesiega.com/)**.

### Latest New Grad opportunities

Showing the 5 most recently posted of 364 open New Grad opportunities:

| Company | Title | Location | Listing |
|---|---|---|---|
| Stripe | Software Engineer, New Grad | Bucharest, Bucharest, Romania | [View](<https://www.linkedin.com/jobs/view/4461530764>) |
| Stripe | Software Engineer, New Grad | Dublin, County Dublin, Ireland | [View](<https://www.linkedin.com/jobs/view/4461550377>) |
| Stripe | Software Engineer, New Grad - Frontend | Barcelona, Catalonia, Spain | [View](<https://www.linkedin.com/jobs/view/4461536634>) |
| Cisco | Software Engineer - Graduate - Lysaker, Norway | Norway | [View](<https://www.linkedin.com/jobs/view/4460031780>) |
| Bending Spoons | Graduate software engineer | Cracow, Małopolskie, Poland | [View](<https://www.linkedin.com/jobs/view/4459760721>) |

### Latest internships

Showing the 5 most recently posted of 294 open internships:

| Company | Title | Location | Listing |
|---|---|---|---|
| Hewlett Packard Enterprise | Cloud Engineer - Intern Conversion | Galway, County Galway, Ireland | [View](<https://www.linkedin.com/jobs/view/4462069905>) |
| Deloitte | Cyber Security Intern - Start date as of February 2027 | Luxembourg, Luxembourg, Luxembourg | [View](<https://www.linkedin.com/jobs/view/4458882666>) |
| Hewlett Packard Enterprise | Software Engineering Intern | Galway, County Galway, Ireland | [View](<https://www.linkedin.com/jobs/view/4458236584>) |
| Stripe | Software Engineer, Intern \(Summer\) | Dublin, County Dublin, Ireland | [View](<https://www.linkedin.com/jobs/view/4460586029>) |
| Software Mind | Intern AI-Driven Software Engineer | Cracow, Małopolskie, Poland | [View](<https://www.linkedin.com/jobs/view/4460340088>) |
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

Ambiguous posting date, employment type, role, seniority, or geography is excluded for new listings. A missing cycle year is allowed only with an eligible posting date; a conflicting explicit cycle year is always excluded. Search-page disappearance never closes a role. Collection closure requires repeated explicit detail-page `404` or `410` evidence across every active search association. A separate daily audit checks each stored row through its public listing and, after a successful page without a closure alert, the guest detail endpoint. It permanently deletes a row after an explicit `404` or `410` from either request or a scoped “No longer accepting applications” alert; inconclusive HTTP, parsing, or transport failures preserve the row for later review.

## Why this project exists

General job searches frequently mix different hiring cycles, senior roles, non-European locations, and unrelated listings. This project favors precision over coverage: listings with ambiguous year, opportunity type, role, seniority, or location evidence are excluded instead of being guessed.

## Engineering highlights

- **End-to-end data product:** bounded asynchronous Python collection and a searchable server-rendered TypeScript/Next.js opportunity directory.
- **Deterministic classification:** explicit rules assign `internship` or `new-grad`, then verify posting recency, cycle, technology category, seniority, and European location.
- **Transactional lifecycle state:** SQLite persistence records provenance, first/last-seen timestamps, isolated search outcomes, conservative closure evidence, and daily full-state availability checks.
- **Production engineering:** Alembic migrations, scheduled automation, restore-verified timestamped backups, atomic deployment, strict typing, CI across Python/site/containers, thresholded branch coverage, and parsing/classification benchmarks.

### Python quality baseline

The current offline suite reports the following coverage for the critical classification and
lifecycle paths:

| Metric | Current | Required |
|---|---:|---:|
| Combined statement and branch coverage | 89.9% | ≥ 85.0% |
| Branch coverage | 81.8% | Reported |
| Classifier branch coverage | 95.0% | Reported |

[Python CI](https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml)
publishes the complete HTML, XML, and JSON coverage reports plus parsing and classification
benchmark results for every run. Benchmark timings remain in the reports because absolute values
vary by runner; compare them only across equivalent environments.

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

A fresh local database is expected to contain no listings. Use the hosted directory for current data.

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
