# Set up a local development environment

[← Maintainer handbook](../README.md) · [Configuration](configuration.md) · [CLI reference](../operations/cli.md) · [Testing](../engineering/testing.md)

You do not need to install the project to browse internships. Use the [live directory](https://techopportunities.eu/).

Install the development tools, initialize disposable local SQLite state, and launch the website without collecting listings. Runtime settings, production operations, and contribution procedures have separate guides.

## Requirements

| Tool | Version | Required for |
|---|---:|---|
| Python | 3.12+ (CI baseline: 3.12) | Pipeline, CLI, tests, and migrations |
| `uv` | 0.11.6 recommended | Locked Python environment and commands |
| Git | Current supported release | Repository checkout |
| Node.js | 22.13+ | Website builds and production-style local startup with unflagged `node:sqlite` support |
| Bun | 1.4.2 | Website dependency installation, tests, and development |
| GNU Make | Optional | Python validation shortcuts; direct `uv` commands are documented too |
| Docker | Current supported release | Documentation lint and optional container and deployment checks |

Confirm the required tools:

```bash
python --version
uv --version
git --version
node --version
bun --version
```

Docker is not required for ordinary local Python or website development, but the complete `make check` and `make docs-site` gates include the Docker-based documentation linters. Installation, local website development, and the default test paths require no LinkedIn access.

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

For realistic **synthetic** listings without collection, run `bun run test:e2e:setup` from `site/`. This requires the Python environment above and uses real migrations, repository writes, and export serialization. For an interactive session, point the site at absolute paths to `site/tests/e2e/.tmp/opportunities.db` and `site/tests/e2e/.tmp/`, with `OPPORTUNITIES_RELEASE_ROOT` unset. These disposable files are never production state. [Tour reproduction](../../assets/README.md#reproduce-safely) runs an isolated fixed-clock instance automatically.

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

The complete engineering validation matrix is documented in the [testing guide](../engineering/testing.md#validation-paths).

## Docker

Docker is optional for running the Python project or website directly. It is required for the pinned documentation linters included in the full validation gates.

For image builds, Compose services, volumes, permissions, local container access, and Dokploy deployment, use the [containers and deployment guide](../operations/deployment.md).
