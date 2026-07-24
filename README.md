<h1 align="center">European Tech Opportunities 2027</h1>

<p align="center">
  An open-source directory and data pipeline for discovering 2027 technology internships and New Grad positions across Europe through conservative, rule-based filtering.
</p>

<!-- BEGIN OPPORTUNITY COUNTS -->
<p align="center">
  <strong>Last updated: July 24, 2026 at 06:37 UTC</strong><br>
  <img src="https://img.shields.io/badge/Total%20opportunities-512-2563eb?style=for-the-badge" alt="Total opportunities: 512" />
  <img src="https://img.shields.io/badge/Internships-294-16a34a?style=for-the-badge" alt="Internships: 294" />
  <img src="https://img.shields.io/badge/New%20Grad-218-9333ea?style=for-the-badge" alt="New Grad opportunities: 218" />
</p>
<!-- END OPPORTUNITY COUNTS -->

<p align="center">
  <a href="https://opportunities2027.simonesiega.com/"><strong>Open the opportunity directory →</strong></a>
</p>

<p align="center">
  <a href="#opportunity-directory"><strong>View the opportunity directory in this README ↓</strong></a>
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
  <a href="#python-quality-baseline">
    <img src="https://img.shields.io/badge/critical_path_coverage-89.8%25_%7C_81.5%25_branches-brightgreen" alt="Critical path coverage: 89.8%, including 81.5% branch coverage" />
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
- **Reliable lifecycle state:** transactional SQLite persistence with provenance, first/last-seen timestamps, conservative closure handling, and daily full-state availability checks.
- **Production workflow:** strict typing, thresholded branch coverage with published reports, parsing/classification benchmarks, Alembic migrations, scheduled collection, restore-verified timestamped SQLite snapshots, and atomic deployment.

### Python quality baseline

The current offline suite reports the following coverage for the critical classification and
lifecycle paths:

| Metric | Current | Required |
|---|---:|---:|
| Combined statement and branch coverage | 89.8% | ≥ 85.0% |
| Branch coverage | 81.5% | Reported |
| Classifier branch coverage | 95.0% | Reported |

[Python CI](https://github.com/simonesiega/european-tech-opportunities-2027/actions/workflows/python-ci.yml)
publishes the complete HTML, XML, and JSON coverage reports plus parsing and classification
benchmark results for every run. Benchmark timings remain in the reports because absolute values
vary by runner; compare them only across equivalent environments.

## Contents

- [Python quality baseline](#python-quality-baseline)
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

Browse every internship and New Grad listing currently marked open at [opportunities2027.simonesiega.com](https://opportunities2027.simonesiega.com/). Coverage is intentionally conservative rather than exhaustive: listings outside the configured searches, or without sufficient explicit evidence, may not appear.

The repository shows only the latest ten positions of each employment type so the landing page remains readable as canonical state grows.

<!-- BEGIN OPPORTUNITIES -->
**Open positions:** 512 (Internships: 294 · New Grad: 218)<br>
**Last successful collection:** July 24, 2026 at 06:37 UTC

Browse and filter the complete directory at **[https://opportunities2027.simonesiega.com/](https://opportunities2027.simonesiega.com/)**.

### Latest New Grad positions

Showing the 10 most recently posted of 218 open New Grad positions:

| Company | Title | Location | Listing |
|---|---|---|---|
| Bending Spoons | Graduate AI software engineer | Germany | [View](<https://www.linkedin.com/jobs/view/4442665833>) |
| Bending Spoons | Graduate software engineer | Warsaw, Mazowieckie, Poland | [View](<https://www.linkedin.com/jobs/view/4442665825>) |
| Bending Spoons | Graduate software engineer | Barcelona, Catalonia, Spain | [View](<https://www.linkedin.com/jobs/view/4442664794>) |
| Bending Spoons | Graduate AI software engineer | Pisa, Tuscany, Italy | [View](<https://www.linkedin.com/jobs/view/4442685039>) |
| Bending Spoons | Graduate AI software engineer | Turin, Piedmont, Italy | [View](<https://www.linkedin.com/jobs/view/4442672459>) |
| Bending Spoons | Graduate software engineer | Seville, Andalusia, Spain | [View](<https://www.linkedin.com/jobs/view/4442668684>) |
| Bending Spoons | Graduate AI software engineer | Milan, Lombardy, Italy | [View](<https://www.linkedin.com/jobs/view/4442662836>) |
| Bending Spoons | Graduate AI software engineer | Wrocław, Dolnośląskie, Poland | [View](<https://www.linkedin.com/jobs/view/4442683107>) |
| Bending Spoons | Graduate AI software engineer | France | [View](<https://www.linkedin.com/jobs/view/4442665826>) |
| Bending Spoons | Graduate AI software engineer | Ireland | [View](<https://www.linkedin.com/jobs/view/4442661954>) |

### Latest internships

Showing the 10 most recently posted of 294 open internships:

| Company | Title | Location | Listing |
|---|---|---|---|
| Jack &amp; Jill | Full Stack AI Engineer Intern at early-stage climate tech AI startup | United Kingdom | [View](<https://www.linkedin.com/jobs/view/4443438994>) |
| Descartes Systems Group | Software R&amp;D Intern | Žilina, Zilina, Slovakia | [View](<https://www.linkedin.com/jobs/view/4444218643>) |
| FORGIS | Automation &amp; Robotics Engineer, Intern | Zurich, Zurich, Switzerland | [View](<https://www.linkedin.com/jobs/view/4443165172>) |
| Capgemini | Intern Data Engineer | Warsaw, Mazowieckie, Poland | [View](<https://www.linkedin.com/jobs/view/4443946590>) |
| Miele | UX Research Intern | Amsterdam, North Holland, Netherlands | [View](<https://www.linkedin.com/jobs/view/4443173182>) |
| BrainBite | Gen AI Developer \(Internship\) | Netherlands | [View](<https://www.linkedin.com/jobs/view/4443391203>) |
| Harmattan AI | Embedded Software Engineer Intern | Paris, Île-de-France, France | [View](<https://www.linkedin.com/jobs/view/4443924514>) |
| VanMoof | Internship Embedded Software Engineer \(Amsterdam\) | Amsterdam, North Holland, Netherlands | [View](<https://www.linkedin.com/jobs/view/4443911993>) |
| NATO | Internship | Paris, Île-de-France, France | [View](<https://www.linkedin.com/jobs/view/4443133950>) |
| CloudLinux | C Developer Intern \(worldwide, remote\) | Warsaw, Mazowieckie, Poland | [View](<https://www.linkedin.com/jobs/view/4441046113>) |
<!-- END OPPORTUNITIES -->

Listings can change or expire. Verify the role, eligibility requirements, location, deadline, compensation, and visa or work-authorization requirements on the original listing before applying.

Missing a relevant position? [Suggest a listing](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=add-position.yml).

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

Ambiguous posting date, employment type, role, seniority, or geography is excluded for new listings. A missing cycle year is allowed only with an eligible posting date; a conflicting explicit cycle year is always excluded. Search-page disappearance never closes a role. Collection closure requires repeated explicit detail-page `404` or `410` evidence across every active search association; a separate daily audit checks the LinkedIn detail page for every stored row and deletes rows only after an explicit `404` or `410`. Other HTTP or transport failures are preserved for later review.

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
uv run opportunities db-upgrade
uv run opportunities stats
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
