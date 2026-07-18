<h1 align="center">European Tech Opportunities 2027</h1>

<p align="center">
  An open-source directory and data pipeline for discovering 2027 technology internships and New Grad positions across Europe through conservative, rule-based filtering.
</p>

<p align="center">
  <a href="https://internship2027.simonesiega.com/"><strong>Open the opportunity directory →</strong></a>
</p>

<p align="center">
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml/badge.svg" alt="Python CI status" />
  </a>
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/site-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/site-ci.yml/badge.svg" alt="Website CI status" />
  </a>
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/docker-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/docker-ci.yml/badge.svg" alt="Docker CI status" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/simonesiega/european-tech-opportunities-2027" alt="MIT license" />
  </a>
</p>

<p align="center">
  <sub>Python 3.12 · TypeScript · Next.js 16 · Tailwind CSS 4 · SQLite · Bun · Docker · GitHub Actions</sub>
</p>

## Website preview

<p align="center">
  <img
    src="docs/photo/sites/White_theme.webp#gh-light-mode-only"
    alt="European Tech Opportunities directory in light theme"
    width="100%"
  />
  <img
    src="docs/photo/sites/Dark_theme.webp#gh-dark-mode-only"
    alt="European Tech Opportunities directory in dark theme"
    width="100%"
  />
</p>

The website is the primary way to use the project. It provides full-text search, an Internship/New Grad filter, company, location, and category filters, sorting, pagination, themes, and direct links to the original listings.

## Why this project exists

General job searches frequently mix different hiring cycles, senior roles, non-European locations, and unrelated positions. This project favors precision over coverage: listings with ambiguous year, opportunity type, role, seniority, or location evidence are excluded instead of being guessed.

## Engineering highlights

- **End-to-end product:** bounded asynchronous Python collection pipeline and a server-rendered TypeScript/Next.js directory.
- **Deterministic filtering:** explicit rules classify every accepted role as either `internship` or `new-grad`, then verify posting recency, cycle, technology category, seniority, and European location.
- **Reliable lifecycle state:** transactional SQLite persistence with provenance, first/last-seen timestamps, and conservative closure handling.
- **Production workflow:** strict typing, offline tests, Alembic migrations, Docker builds, scheduled collection, validation, backups, and atomic deployment.

## Contents

- [Opportunity directory](#opportunity-directory)
- [Publication rules](#publication-rules)
- [How it works](#how-it-works)
- [Run locally](#run-locally)
- [Documentation](#documentation)
- [Responsible operation](#responsible-operation)
- [Contributing](#contributing)
- [License](#license)
- [Contributors](#contributors)

## Opportunity directory

Browse every internship and New Grad listing currently marked open at [internship2027.simonesiega.com](https://internship2027.simonesiega.com/). Coverage is intentionally conservative rather than exhaustive: listings outside the configured searches, or without sufficient explicit evidence, may not appear.

The repository shows only the latest ten positions of each employment type so the landing page remains readable as canonical state grows.

<!-- BEGIN INTERNSHIPS -->
**Open positions:** 131 (Internships: 58 · New Grad: 73)<br>
**Last successful collection:** July 18, 2026 at 22:50 UTC

Browse and filter the complete directory at **[https://internship2027.simonesiega.com/](https://internship2027.simonesiega.com/)**.

### Latest New Grad positions

Showing the 10 most recently posted of 73 open New Grad positions:

| Company | Title | Location | Listing |
|---|---|---|---|
| Revolut | Graduate Programme 2027: Information Security Engineer \(Appsec\) | Spain | [View](<https://www.linkedin.com/jobs/view/4433222747>) |
| Revolut | Graduate Programme 2027: Information Security Engineer \(Appsec\) | Poland | [View](<https://www.linkedin.com/jobs/view/4433218761>) |
| Revolut | Graduate Programme 2027: Information Security Engineer \(Operations\) | Porto, Porto, Portugal | [View](<https://www.linkedin.com/jobs/view/4433212965>) |
| TNO | Entry-level Machine Learning Engineer | Groningen, Groningen, Netherlands | [View](<https://www.linkedin.com/jobs/view/4433880753>) |
| Revolut | Graduate Programme 2027: Information Security Engineer \(Operations\) | Spain | [View](<https://www.linkedin.com/jobs/view/4433224580>) |
| NTT DATA Europe &amp; Latam | New Graduate - Information Technology/STEM | Milan, Lombardy, Italy | [View](<https://www.linkedin.com/jobs/view/4255725429>) |
| AVEVA | Cloud Operations &amp; Infrastructure Graduate | Cambridge, England, United Kingdom | [View](<https://www.linkedin.com/jobs/view/4392878156>) |
| Autodesk | Graduate Software Engineer | Oslo, Oslo, Norway | [View](<https://www.linkedin.com/jobs/view/4441161003>) |
| Revolut | Graduate Programme 2027: Information Security Engineer \(Operations\) | Poland | [View](<https://www.linkedin.com/jobs/view/4433229338>) |
| Revolut | Graduate Programme 2027: Information Security Engineer \(Operations\) | Portugal | [View](<https://www.linkedin.com/jobs/view/4433217750>) |

### Latest internships

Showing the 10 most recently posted of 58 open internships:

| Company | Title | Location | Listing |
|---|---|---|---|
| Revolut | Internship Programme 2027: Information Security Engineer \(Appsec\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4433230351>) |
| Susquehanna International Group | Equity Research Internship: Summer 2027 | London, England, United Kingdom | [View](<https://www.linkedin.com/jobs/view/4439268761>) |
| Autodesk | Software Engineering Intern Summer 2027 | Oslo, Oslo, Norway | [View](<https://www.linkedin.com/jobs/view/4441319217>) |
| Autodesk | Software Engineering Intern Summer 2027 | Oslo, Oslo, Norway | [View](<https://www.linkedin.com/jobs/view/4441306714>) |
| Revolut | Internship Programme 2027: Information Security Engineer \(Operations\) | Spain | [View](<https://www.linkedin.com/jobs/view/4433230335>) |
| hackajob | Internship Programme 2027: Software Engineer \(Java\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4429227768>) |
| Susquehanna International Group | Quantitative Research Internship: Summer 2027 | Dublin, County Dublin, Ireland | [View](<https://www.linkedin.com/jobs/view/4438405881>) |
| Revolut | Internship Programme 2027: Information Security Engineer \(Operations\) | Portugal | [View](<https://www.linkedin.com/jobs/view/4433234118>) |
| Revolut | Internship Programme 2027: Information Security Engineer \(Operations\) | Porto, Porto, Portugal | [View](<https://www.linkedin.com/jobs/view/4433229421>) |
| Revolut | Internship Programme 2027: Information Security Engineer \(Appsec\) | Poland | [View](<https://www.linkedin.com/jobs/view/4433220754>) |
<!-- END INTERNSHIPS -->

Listings can change or expire. Verify the role, eligibility requirements, location, deadline, compensation, and visa or work-authorization requirements on the original listing before applying.

Missing a relevant position? [Suggest a listing](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=add-position.yml).

## Publication rules

A listing is published only when all six checks pass:

| Check | Required evidence |
|---|---|
| Employment type | The title explicitly identifies either an internship (including placement or co-op) or a New Grad role. Internship terminology takes precedence if both appear. |
| Posting date | LinkedIn’s relative posting age resolves to May 1, 2026 or later; missing or older posting metadata is excluded for new listings. |
| Seniority | The title contains no configured senior-level or management terminology. |
| 2027 cycle | Explicit `2027` evidence is accepted; an otherwise eligible listing with no explicit cycle year is accepted when posted on or after May 1, 2026, while any conflicting explicit cycle year is rejected. Graduation-year eligibility alone is ignored for internships. |
| Technology role | The title, or a narrowly allowed description fallback, matches a configured technology category. |
| European location | The parsed location explicitly resolves to Europe or a supported European country. |

Ambiguous posting date, employment type, role, seniority, or geography is excluded for new listings. A missing cycle year is allowed only with an eligible posting date; a conflicting explicit cycle year is always excluded. Search-page disappearance never closes a role; closure requires repeated explicit detail-page `404` or `410` evidence across every active search association.

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
│ all open roles       │ 10/type recent roles │
└──────────────────────┴──────────────────────┘
</pre>
</div>

SQLite is the canonical store. The website and README are read-only projections of accepted jobs and their lifecycle state.

See the [architecture guide](docs/md/development/architecture.md) for the complete data flow, component boundaries, and extension policy.

## Run locally

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), and Git.

```bash
git clone https://github.com/simonesiega/european-tech-opportunities-2027.git
cd european-tech-opportunities-2027
uv sync --frozen --dev
cp .env.example .env
uv run internships db-upgrade
uv run internships stats
```

A fresh local database is expected to contain no listings. Use the hosted directory for current data.

Continue with the [installation guide](docs/md/getting-started/installation.md) for the local website, Windows commands, Docker, and verification. Runtime settings are documented in [configuration](docs/md/getting-started/configuration.md), and CLI commands in the [CLI reference](docs/md/user-guide/cli.md).

## Documentation

The [documentation hub](docs/md/README.md) routes users, operators, and contributors to the appropriate guide.

| Area | Canonical guide |
|---|---|
| Setup and configuration | [Installation](docs/md/getting-started/installation.md) · [Configuration](docs/md/getting-started/configuration.md) |
| Using the project | [Website](docs/md/user-guide/website.md) · [CLI](docs/md/user-guide/cli.md) · [Search registry](docs/md/user-guide/search-registry.md) |
| Production operation | [Automation](docs/md/operations/automation.md) · [Database](docs/md/operations/database.md) · [Docker](docs/md/operations/docker.md) · [Troubleshooting](docs/md/operations/troubleshooting.md) |
| Development | [Architecture](docs/md/development/architecture.md) · [Development guide](docs/md/development/development.md) · [Contributing](CONTRIBUTING.md) |

## Responsible operation

> [!IMPORTANT]
> LinkedIn collection is disabled by default. Public accessibility is not authorization to automate access. The authorization interlock records an operator decision; it does not grant permission.

The project does not use credentials, sessions, browser automation, private endpoints, proxies, CAPTCHA bypasses, or anti-bot evasion. It is not affiliated with or endorsed by LinkedIn or any listed employer.

Read [`SECURITY.md`](SECURITY.md) before operating collection infrastructure.

## Contributing

Focused improvements to strict classification, sanitized parser fixtures, search coverage, lifecycle safety, tests, website usability, and documentation are welcome.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a pull request.

## License

Licensed under the [MIT License](LICENSE).

## Contributors

<p align="center">
  <a href="https://github.com/simonesiega/european-tech-opportunities-2027/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=simonesiega/european-tech-opportunities-2027&max=24&columns=12" alt="Contributors" />
  </a>
</p>