# European Tech Opportunities 2027 Docker and Deployment Guide

[← Documentation](../README.md) · [Website](../user-guide/website.md) · [Automation](automation.md)

This guide documents the project’s Docker image targets, Compose topology, local container workflow, mounts, runtime permissions, Dokploy configuration, and container-specific production behavior.

Docker does not change the authorization, lifecycle, or one-writer contracts.

## Contents

- [Image targets](#image-targets)
- [Build images](#build-images)
- [Compose topology](#compose-topology)
- [Start the website locally](#start-the-website-locally)
- [Run pipeline commands](#run-pipeline-commands)
- [Authorized collection](#authorized-collection)
- [Dokploy deployment](#dokploy-deployment)
- [Volume permissions](#volume-permissions)
- [Run without Compose](#run-without-compose)
- [Production maintenance](#production-maintenance)
- [Troubleshooting](#troubleshooting)

## Image targets

The root `Dockerfile` produces two final targets:

| Target | Runtime | Responsibility |
|---|---|---|
| `internships` | Python 3.12 through the configured `uv` base image | CLI commands, migrations, collection, validation, and README rendering |
| `site` | Node 26 Alpine with Next.js standalone output | Read-only website server on port `3000` |

Both final images run as an unprivileged user:

```text
UID 10001
GID 10001
```

The images install only the dependencies required by their target and use the committed lockfiles for reproducible builds.

## Build images

Build the pipeline image:

```bash
docker build \
  --target internships \
  --tag european-tech-opportunities-27-cli:local \
  .
```

Verify its entry point:

```bash
docker run --rm \
  european-tech-opportunities-27-cli:local \
  --help
```

Build the website image:

```bash
docker build \
  --target site \
  --tag european-tech-opportunities-27-site:local \
  .
```

Build and inspect the supported Compose project:

```bash
docker compose build
docker compose run --rm internships --help
docker compose config
```

The complete image and Compose checks are listed in the [development guide](../development/development.md#containers).

## Compose topology

```text
internships service ── read/write ─┐
                                   ├─ internships-data volume
site service ───────── read-only ──┘
```

The pipeline service uses:

| Source | Destination | Mode | Purpose |
|---|---|---|---|
| `./configs` | `/app/configs` | Read-only | Search and classification YAML |
| Repository root | `/workspace` | Read/write | Atomic README projection replacement |
| `internships-data` | `/app/data` | Read/write | Canonical SQLite state |

The website service mounts only the database volume and opens SQLite in read-only mode.

The Compose startup path applies the idempotent database upgrade before the website is started.

Expected container database URLs:

```text
pipeline: sqlite:////app/data/opportunities.db
website:  /app/data/opportunities.db
```

Only the controlled pipeline service may mutate canonical state.

## Start the website locally

Build and start the website service:

```bash
docker compose up --detach --build site
```

Inspect the service:

```bash
docker compose ps
docker compose logs site
```

The default Compose configuration exposes the website inside the container network rather than publishing a fixed host port.

For direct browser access during local development:

- use the Bun workflow from [Installation](../getting-started/installation.md#run-the-website); or
- add a local-only Compose override mapping host port `3000` to container port `3000`.

Do not commit a production fixed-port mapping when Dokploy or another reverse proxy owns routing.

Stop the Compose project without deleting the named volume:

```bash
docker compose down
```

Do not add `--volumes` unless deleting local canonical state is intentional.

## Run pipeline commands

Run offline commands through the pipeline service:

```bash
docker compose run --rm internships db-upgrade
docker compose run --rm internships searches
docker compose run --rm internships stats
```

When representative canonical state is available:

```bash
docker compose run --rm internships render
docker compose run --rm internships validate
```

These commands do not contact LinkedIn.

A new named volume contains no listings. Do not render and commit the README projection from empty state.

CLI command behavior is documented in the [CLI reference](../user-guide/cli.md).

## Authorized collection

Collection requires both express authorization and the application interlock.

Test one search without persistence:

```bash
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true \
  docker compose run --rm internships \
  search-test company-amazon
```

Persist one bounded search:

```bash
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true \
  docker compose run --rm internships \
  scrape --search company-amazon
```

On a website-only VPS, `scrape --no-render` avoids modifying the deployment working tree when README rendering is not part of that execution path.

Do not run an independent local or VPS collector while GitHub Actions owns canonical state.

> [!IMPORTANT]
> The environment variable is a safety interlock, not permission. Do not enable it without express authorization.

Exact interlock behavior belongs to [Configuration](../getting-started/configuration.md#authorization-interlocks), and the complete access boundary to [`SECURITY.md`](../../../SECURITY.md).

## Dokploy deployment

Production directory:

**https://internship2027.simonesiega.com/**

Configure Dokploy to:

1. deploy the Compose project;
2. build the `site` image target;
3. assign the public domain to the `site` service;
4. route traffic to container port `3000`;
5. avoid publishing a conflicting fixed host port;
6. preserve the `internships-data` named volume;
7. set the canonical website origin.

Required website environment:

```dotenv
SITE_URL=https://internship2027.simonesiega.com
INTERNSHIPS_DATABASE_PATH=/app/data/opportunities.db
```

The site service must receive the database volume as read-only.

The GitHub Actions collection workflow replaces the SQLite file inside the named volume through verified SSH, checksum comparison, locking, correct ownership, and atomic rename.

The website opens a new short-lived read-only connection for each server request, so deployed state becomes visible without:

- a write API;
- an application migration endpoint;
- a rebuild;
- an in-process state synchronization service.

Workflow-side secrets, checksums, artifacts, rebuild controls, and deployment sequencing are documented in [Automation](automation.md#vps-deployment).

## Volume permissions

The images expect required files to be owned by or accessible to:

```text
UID 10001
GID 10001
```

The website requires read access to the SQLite database and its parent directory.

README rendering additionally requires write and execute access to the mounted repository directory because the renderer:

1. creates a same-directory temporary file;
2. writes the generated block;
3. atomically renames the temporary file over `README.md`.

A narrow Linux ACL can grant the required access:

```bash
sudo setfacl -m u:10001:rwx .
sudo setfacl -m u:10001:rw README.md
```

For a production database deployed by automation, the expected ownership and mode are:

```text
10001:10001
0640
```

Do not use `chmod 777`, run the full application as root, or make the Docker socket broadly accessible to avoid correcting ownership.

## Run without Compose

Create the persistent named volume:

```bash
docker volume create internships-data
```

Run the migration with explicit mounts:

```bash
docker run --rm \
  -e INTERNSHIPS_README_PATH=/workspace/README.md \
  -v internships-data:/app/data \
  -v "$(pwd)/configs:/app/configs:ro" \
  -v "$(pwd):/workspace" \
  european-tech-opportunities-27-cli:local \
  db-upgrade
```

Inspect the initialized database:

```bash
docker run --rm \
  -e INTERNSHIPS_README_PATH=/workspace/README.md \
  -v internships-data:/app/data \
  -v "$(pwd)/configs:/app/configs:ro" \
  -v "$(pwd):/workspace" \
  european-tech-opportunities-27-cli:local \
  stats
```

Reuse the same mounts for other pipeline commands.

A named volume survives `--rm`, but remains operational state rather than a backup. Backup and restore procedures belong to [Database lifecycle](database.md#backup).

## Production maintenance

Use this order for production state changes:

<div align="center">
<pre>
migrate
↓
collect or repair
↓
validate
↓
checkpoint and back up
↓
deploy atomically
</pre>
</div>

After changing Dockerfile or Compose behavior, run:

```bash
uv lock --check

cd site
bun install --frozen-lockfile
bun run ci
cd ..

docker compose build
docker compose run --rm internships --help
docker compose config
```

Preserve:

- one canonical writer;
- the read-only website mount;
- the named SQLite volume;
- UID/GID `10001:10001`;
- frozen dependency installation;
- no secrets in build arguments or image layers;
- no production databases copied into images.

Run every affected check from the [development validation matrix](../development/development.md#validation-paths).

## Troubleshooting

For empty or unmigrated volumes, SQLite read permissions, README atomic replacement, Compose expansion, image startup, or Dokploy routing problems, use the [Docker failures section of the troubleshooting guide](troubleshooting.md#docker-failures).

Workflow-side deployment failures belong to [GitHub Actions and deployment troubleshooting](troubleshooting.md#github-actions-and-deployment).