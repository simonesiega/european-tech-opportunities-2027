# European Tech Opportunities 2027 Installation Guide

[← Documentation hub](../../README.md) · [Configuration](configuration.md) · [CLI reference](../user-guide/cli.md) · [Development guide](../development/development.md) · [Open the opportunity directory](https://opportunities2027.simonesiega.com/)

You do not need to install the project to browse internships. Use the [live directory](https://opportunities2027.simonesiega.com/).

This is the canonical installation guide for the project. It covers local installation, database initialization, the first website launch, and basic verification. Runtime settings, production operation, and contribution procedures belong to their dedicated guides.

## Requirements

| Tool | Version | Required for |
|---|---:|---|
| Python | 3.12+ (CI baseline: 3.12) | Pipeline, CLI, tests, and migrations |
| `uv` | 0.11.6 recommended | Locked Python environment and commands |
| Git | Current supported release | Repository checkout |
| Node.js | 22.13+ | Website builds and production-style local startup with unflagged `node:sqlite` support |
| Bun | 1.4.2 | Website dependency installation, tests, and development |
| GNU Make | Optional | Python validation shortcuts; direct `uv` commands are documented too |
| Docker | Optional | Container and deployment workflows |

Confirm the required tools:

```bash
python --version
uv --version
git --version
node --version
bun --version
```

Docker is not required for ordinary local Python or website development. Installation, local website development, and the default test paths require no LinkedIn access.

## Clone the repository

```bash
git clone https://github.com/simonesiega/european-tech-opportunities-2027.git
cd european-tech-opportunities-2027
```

Run the remaining Python commands from the repository root unless a section explicitly changes directory.

## Install the Python project

Install the exact locked development environment:

```bash
uv sync --frozen --dev
```

Create the local environment file.

Linux or macOS:

```bash
cp .env.example .env
```

Windows Command Prompt:

```bat
copy .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

The default configuration keeps LinkedIn collection disabled. Review the [configuration guide](configuration.md) before changing runtime values.

## Initialize the local database

Create or upgrade the SQLite schema:

```bash
uv run opportunities db-upgrade
```

Verify that the search registry and database load:

```bash
uv run opportunities searches
uv run opportunities stats
```

The default database is created at:

```text
data/opportunities.db
```

A new local database intentionally contains no listings. Use the hosted directory for current public data.

> [!IMPORTANT]
> Do not render and commit the README preview from an empty local database. Exact projection rendering requires representative canonical state.

## Run the website

Install the website dependencies:

```bash
cd site
bun install --frozen-lockfile
```

Create the website environment file.

Linux or macOS:

```bash
cp .env.example .env.local
```

Windows Command Prompt:

```bat
copy .env.example .env.local
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

For local development, make sure `site/.env.local` uses the local origin:

```dotenv
SITE_URL=http://localhost:3000
OPPORTUNITIES_DATABASE_PATH=../data/opportunities.db
OPPORTUNITIES_PUBLIC_EXPORT_DIR=../data/exports
```

Start the development server:

```bash
bun run dev
```

Open:

```text
http://localhost:3000
```

The website reads SQLite and pipeline-generated public exports in read-only mode. An empty directory is valid when the local database contains no open listings; run `uv run opportunities export-public` from the repository root to create empty local CSV/JSON projections when testing the download routes.

After stopping the development server, return to the repository root:

```bash
cd ..
```

## Verify the installation

From the repository root, verify the Python project:

```bash
uv run opportunities --help
uv run opportunities stats
uv run pytest -m "not live and not performance"
```

Install Chromium once before running the complete website validation path:

```bash
cd site
bunx playwright install chromium
```

Then verify the website:

```bash
bun run ci
cd ..
```

`bun run ci` checks formatting, linting, strict TypeScript, the production Next.js build, Bun unit tests, Playwright browser behavior, and axe-core accessibility against a generated SQLite fixture.

The complete engineering validation matrix is documented in the [development guide](../development/development.md#validation-paths).

## Docker

Docker is optional for local development and is not required to run either the Python project or the website directly.

For image builds, Compose services, volumes, permissions, local container access, and Dokploy deployment, use the [Docker and deployment guide](../operations/docker.md).
