<h1 align="center">European Tech Internships 2027</h1>

<p align="center">
  An open-source directory and data pipeline for discovering 2027 technology internships across Europe through conservative, rule-based filtering.
</p>

<p align="center">
  <a href="https://internship2027.simonesiega.com/"><strong>Open the internship directory →</strong></a>
</p>

<p align="center">
  <a href="https://github.com/simonesiega/european-tech-internships-2027/actions/workflows/python-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-internships-2027/actions/workflows/python-ci.yml/badge.svg" alt="Python CI status" />
  </a>
  <a href="https://github.com/simonesiega/european-tech-internships-2027/actions/workflows/site-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-internships-2027/actions/workflows/site-ci.yml/badge.svg" alt="Website CI status" />
  </a>
  <a href="https://github.com/simonesiega/european-tech-internships-2027/actions/workflows/docker-ci.yml">
    <img src="https://github.com/simonesiega/european-tech-internships-2027/actions/workflows/docker-ci.yml/badge.svg" alt="Docker CI status" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/simonesiega/european-tech-internships-2027" alt="MIT license" />
  </a>
</p>

<p align="center">
  <sub>Python 3.12 · TypeScript · Next.js 16 · SQLite · Bun · Docker · GitHub Actions</sub>
</p>

## Website preview

<p align="center">
  <img
    src="docs/photo/sites/White_theme.webp#gh-light-mode-only"
    alt="European Tech Internships directory in light theme"
    width="100%"
  />
  <img
    src="docs/photo/sites/Dark_theme.webp#gh-dark-mode-only"
    alt="European Tech Internships directory in dark theme"
    width="100%"
  />
</p>

The website is the primary way to use the project. It provides full-text search, filters, sorting, pagination, light and dark themes, and direct links to the original listings.

## Why this project exists

General job searches frequently mix different internship cycles, senior roles, non-European locations, and unrelated positions. This project favors precision over coverage: listings with ambiguous year, role, seniority, or location evidence are excluded instead of being guessed.

## Engineering highlights

- **End-to-end product:** bounded asynchronous Python collection pipeline and a server-rendered TypeScript/Next.js directory.
- **Deterministic filtering:** explicit rules for internship type, cycle, technology category, seniority, and European location.
- **Reliable lifecycle state:** transactional SQLite persistence with provenance, first/last-seen timestamps, and conservative closure handling.
- **Production workflow:** strict typing, offline tests, Alembic migrations, Docker builds, scheduled collection, validation, backups, and atomic deployment.

## Contents

- [Internship directory](#internship-directory)
- [Publication rules](#publication-rules)
- [How it works](#how-it-works)
- [Run locally](#run-locally)
- [Documentation](#documentation)
- [Responsible operation](#responsible-operation)
- [Contributing](#contributing)
- [License](#license)
- [Contributors](#contributors)

## Internship directory

Browse every listing currently marked open at [internship2027.simonesiega.com](https://internship2027.simonesiega.com/). Coverage is intentionally conservative rather than exhaustive: listings outside the configured searches, or without sufficient explicit evidence, may not appear.

The repository shows only the bounded preview below so the landing page remains readable as canonical state grows.

<!-- BEGIN INTERNSHIPS -->
**Open internships:** 51<br>
**Last successful collection:** July 17, 2026 at 21:22 UTC

Browse and filter the complete directory at **[https://internship2027.simonesiega.com/](https://internship2027.simonesiega.com/)**.

Showing the 10 most recently discovered of 51 open internships:

| Company | Title | Location | Listing |
|---|---|---|---|
| Autodesk | Software Engineering Intern Summer 2027 | Oslo, Oslo, Norway | [View](<https://www.linkedin.com/jobs/view/4441319217>) |
| Autodesk | Software Engineering Intern Summer 2027 | Oslo, Oslo, Norway | [View](<https://www.linkedin.com/jobs/view/4441306714>) |
| Revolut | Internship Programme 2027: Information Security Engineer \(Operations\) | Spain | [View](<https://www.linkedin.com/jobs/view/4433230335>) |
| hackajob | Internship Programme 2027: Software Engineer \(Java\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4429227768>) |
| hackajob | Internship Programme 2027: Software Engineer \(iOS\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4429249232>) |
| hackajob | Internship Programme 2027: Information Security Engineer \(Appsec\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4433610667>) |
| Revolut | Internship Programme 2027: Software Engineer \(Android\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4419099439>) |
| Revolut | Internship Programme 2027: Software Engineer \(Frontend\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4419099411>) |
| Revolut | Internship Programme 2027: Software Engineer \(Python\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4419094634>) |
| Revolut | Internship Programme 2027: Software Engineer \(Java\) | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4419091723>) |
<!-- END INTERNSHIPS -->

Listings can change or expire. Verify the role, eligibility requirements, location, deadline, compensation, and visa or work-authorization requirements on the original listing before applying.

Missing a relevant internship? [Suggest a listing](https://github.com/simonesiega/european-tech-internships-2027/issues/new?template=add-internship.yml).

## Publication rules

A listing is published only when all five checks pass:

| Check | Required evidence |
|---|---|
| Internship | The title explicitly contains configured internship, placement, or co-op terminology. |
| Seniority | The title contains no configured senior-level or management terminology. |
| 2027 cycle | `2027` appears in the title or explicit internship-cycle context; graduation year alone is ignored. |
| Technology role | The title, or a narrowly allowed description fallback, matches a configured technology category. |
| European location | The parsed location explicitly resolves to Europe or a supported European country. |

Ambiguous cycle, role, seniority, or geography is excluded. Search-page disappearance never closes a role; closure requires repeated explicit detail-page `404` or `410` evidence across every active search association.

## How it works

<div align="center">
<pre>
validated search definitions
↓
bounded LinkedIn guest HTML collection
↓
strict deterministic classification
↓
transactional SQLite lifecycle state
↓
┌──────────────────────┬──────────────────────┐
│ searchable website   │ README preview       │
│ all open roles       │ 10 recent roles      │
└──────────────────────┴──────────────────────┘
</pre>
</div>

SQLite is the canonical store. The website and README are read-only projections of accepted jobs and their lifecycle state.

See the [architecture guide](docs/md/development/architecture.md) for the complete data flow, component boundaries, and extension policy.

## Run locally

Requirements: Python 3.12+, [`uv`](https://docs.astral.sh/uv/), and Git.

```bash
git clone https://github.com/simonesiega/european-tech-internships-2027.git
cd european-tech-internships-2027
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
  <a href="https://github.com/simonesiega/european-tech-internships-2027/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=simonesiega/european-tech-internships-2027&max=24&columns=12" alt="Contributors" />
  </a>
</p>