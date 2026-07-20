# European Tech Opportunities 2027 Installation Guide

[← Documentation](../README.md) · [Configuration](configuration.md) · [Open the opportunity directory](https://opportunities2027.simonesiega.com/)

You do not need to install the project to browse internships. Use the [live directory](https://opportunities2027.simonesiega.com/).

This guide covers local installation, database initialization, the first website launch, and basic verification. Runtime settings, production operation, and contribution procedures belong to their dedicated guides.

## Requirements

| Tool | Version | Required for |
|---|---:|---|
| Python | 3.12+ | Pipeline, CLI, tests, and migrations |
| `uv` | 0.11.6 recommended | Locked Python environment and commands |
| Git | Current supported release | Repository checkout |
| Bun | 1.3.14 | Website installation and development |
| Docker | Optional | Container and deployment workflows |

Confirm the required tools:

```bash
python --version
uv --version
git --version
bun --version
```

Docker is not required for ordinary local Python or website development.

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

A new local database is expected to contain no listings. Use the hosted directory for current public data.

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

Start the development server:

```bash
bun run dev
```

Open:

```text
http://localhost:3000
```

The website reads SQLite in read-only mode. An empty directory is valid when the local database contains no open listings.

Return to the repository root when finished:

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

Verify the website:

```bash
cd site
bun run ci
cd ..
```

`bun run ci` checks formatting, linting, strict TypeScript, the production Next.js build, Bun unit tests, and Playwright browser behavior against a generated SQLite fixture.

The complete engineering validation matrix is documented in the [development guide](../development/development.md#validation-paths).

## Docker

Docker is optional for local development.

For image builds, Compose services, volumes, permissions, local container access, and Dokploy deployment, use the [Docker and deployment guide](../operations/docker.md).