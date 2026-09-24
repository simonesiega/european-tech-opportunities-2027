# European Tech Opportunities 2027 Docker and Deployment Guide

[← Documentation hub](../../README.md) · [Website](../user-guide/website.md) · [Automation](automation.md) · [Database lifecycle](database.md) · [Troubleshooting](troubleshooting.md) · [Security policy](../../../SECURITY.md)

This is the canonical Docker and deployment guide for the project. It documents the Docker image targets, Compose topology, local container workflow, mounts, runtime permissions, Dokploy configuration, and container-specific production behavior.

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
- [Application release and rollback](#application-release-and-rollback)
- [Production maintenance](#production-maintenance)
- [Troubleshooting](#troubleshooting)

## Image targets

The root `Dockerfile` is the executable source of truth for image versions and produces two final targets:

| Target | Final runtime | Responsibility |
|---|---|---|
| `opportunities` | Python 3.14.7 on Debian 13 slim | CLI commands, migrations, collection, validation, and generated-document rendering |
| `site` | Node.js 26 on Debian 13 slim with Next.js standalone output | Read-only website server on port `3000` |

Disposable build stages use the digest-pinned `uv` 0.12.15 image, Bun 1.4.2 on Alpine, and Node.js 26 on Alpine. Package-manager binaries are omitted from the final images: the pipeline invokes the installed console script directly, and the website runtime omits npm.

Both final images run as an unprivileged user:

```text
UID 10001
GID 10001
```

The Compose services also drop all Linux capabilities and set `no-new-privileges`.

The images install only the dependencies required by their target and use committed lockfiles, versioned images, and immutable image digests for reproducible builds. Both Debian runtime targets install exact reviewed security revisions for `gzip`, PCRE2, SQLite, and Perl until those revisions are incorporated into the pinned base-image digests. Update the pins and package versions together; an unavailable exact package version is intentionally a build failure rather than a silent fallback.

## Build images

Build the pipeline image:

```bash
docker build \
  --target opportunities \
  --tag european-tech-opportunities-2027-cli:local \
  .
```

Verify its entry point:

```bash
docker run --rm \
  european-tech-opportunities-2027-cli:local \
  --help
```

Build the website image:

```bash
docker build \
  --target site \
  --tag european-tech-opportunities-2027-site:local \
  .
```

Build and inspect the supported Compose project:

```bash
docker compose build
docker compose run --rm opportunities --help
docker compose config
```

The complete image and Compose checks are listed in the [development guide](../development/development.md#containers).

## Compose topology

```text
opportunities service ── read/write ─┐
                                   ├─ /srv/european-tech-opportunities-2027/data
site service ───────── read-only ──┘   host bind mount
```

The pipeline service uses:

| Source | Destination | Mode | Purpose |
|---|---|---|---|
| `./configs` | `/app/configs` | Read-only | Search and classification YAML |
| Repository root | `/workspace` | Read/write | Atomic README and search-registry documentation replacement |
| `/srv/european-tech-opportunities-2027/data` | `/app/data` | Read/write | Canonical SQLite state |

The website service mounts only the same host state directory in read-only mode. With `OPPORTUNITIES_RELEASE_ROOT=/app/data` it reads the database and exports from one selected `current` release per server operation; without it, it continues to use the legacy fixed paths. Switch only after the coordinated rollout in [Automation](automation.md#coordinated-first-rollout-and-rollback).

Starting the website does **not** run a migration or initialize canonical state. In production, restore verified state before running `docker compose run --rm opportunities db-upgrade`, followed by `export-public`; in local development only, an intentionally empty database may be initialized explicitly. A missing or unmigrated production database is an operational failure, not a reason to create an empty history. Do not run a migration concurrently with the canonical-state workflow.

Expected container paths:

```text
pipeline database:      sqlite:////app/data/opportunities.db
site (legacy mode):     /app/data/opportunities.db and /app/data/exports/
site (versioned mode):  /app/data/current/opportunities.db and /app/data/current/exports/
```

The pipeline's working database and the site's versioned read-only release are separate copies. Do not point the pipeline writer at `current`.

Only the controlled pipeline service may mutate canonical state or replace generated exports. The `site` service has a read-only bind mount and a read-only SQLite connection, providing defense in depth.

## Start the website locally

For an intentionally empty **local-only** state directory, initialize the database and downloadable projections explicitly, then build and start the website service. In production, restore and verify existing canonical state first:

```bash
docker compose run --rm opportunities db-upgrade
docker compose run --rm opportunities export-public
docker compose up --detach --build site
```

Inspect the service:

```bash
docker compose ps
docker compose logs site
```

The default Compose configuration uses `SITE_URL=http://localhost:3000`, which keeps production-only analytics disabled, and exposes port `3000` only to the Compose network; it does not publish a fixed host port. Production must explicitly override `SITE_URL` with the canonical HTTPS origin at runtime. The Docker smoke test deliberately builds with the local default and serves with the production origin to verify that robots and sitemap do not retain the build-time URL.

For direct browser access during local development:

- use the Bun workflow from [Installation](../getting-started/installation.md#run-the-website); or
- add a local-only Compose override mapping host port `3000` to container port `3000`.

Do not commit a production fixed-port mapping when Dokploy or another reverse proxy owns routing.

Stop the Compose project:

```bash
docker compose down
```

Compose teardown leaves the bind-mounted host state directory in place. Deleting that directory is a separate, destructive action.

## Run pipeline commands

Run offline commands through the pipeline service:

```bash
docker compose run --rm opportunities db-upgrade
docker compose run --rm opportunities searches
docker compose run --rm opportunities stats
```

When representative canonical state is available:

```bash
docker compose run --rm opportunities render
docker compose run --rm opportunities validate
```

These commands do not contact LinkedIn.

A fresh host state directory intentionally contains no listings. Do not render and commit generated projections from empty state.

CLI command behavior is documented in the [CLI reference](../user-guide/cli.md).

## Authorized collection

Collection requires both express authorization and the application interlock.

Test one search without persistence:

```bash
OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true \
  docker compose run --rm opportunities \
  search-test company-amazon
```

Persist one bounded search:

```bash
OPPORTUNITIES_LINKEDIN_CRAWL_AUTHORIZED=true \
  docker compose run --rm opportunities \
  scrape --search company-amazon
```

On a website-only VPS, `scrape --no-render` avoids modifying generated files in the deployment working tree when rendering is not part of that execution path.

Do not run an independent local or VPS collector while GitHub Actions owns canonical state.

> [!IMPORTANT]
> The environment variable is a safety interlock, not permission. Do not enable it without express authorization.

Exact interlock behavior belongs to [Configuration](../getting-started/configuration.md#authorization-interlocks), and the complete access boundary to [`SECURITY.md`](../../../SECURITY.md).

## Dokploy deployment

Production site:

**https://opportunities2027.simonesiega.com/**

### Legacy deployment migration

Deployments created before the Opportunities rename must stop every writer, move existing canonical state into `/srv/european-tech-opportunities-2027/data`, and provision the restricted `opportunities-site` host group. For this **legacy fixed-path migration**, restart collection and the website only after both services resolve the same database file. Later versioned publication uses a separate read-only site release; follow [Coordinated first rollout and rollback](automation.md#coordinated-first-rollout-and-rollback).

### Dokploy configuration

Configure Dokploy to:

1. deploy the Compose project;
2. build the `site` image target;
3. assign the public domain to the `site` service;
4. route traffic to container port `3000`;
5. avoid publishing a conflicting fixed host port;
6. preserve `/srv/european-tech-opportunities-2027/data` as persistent host state;
7. set the canonical website origin.

Production website environment **after** the coordinated first rollout:

```dotenv
SITE_URL=https://opportunities2027.simonesiega.com
OPPORTUNITIES_RELEASE_ROOT=/app/data
```

Compose also supplies the fixed-path database and export variables for local/legacy mode; release-root mode takes precedence. The site service must receive the whole host state directory as a read-only bind mount.

The manual deployment mode in `scrape.yml` stages an immutable SQLite + CSV + JSON release through the main-only `production` GitHub environment, verified SSH, checksum comparison, locking, restricted permissions, and an atomic `current` symlink rename. The legacy fixed files are not replaced. Production **must** set `OPPORTUNITIES_RELEASE_ROOT=/app/data` only after the first release is verified and old site instances have drained. Keep old releases until active readers have closed.

The directory opens a new short-lived read-only SQLite connection for each request, while download routes open files from the selected release. Deployed state becomes visible without:

- a write API;
- an application migration endpoint;
- a rebuild;
- an in-process state synchronization service.

Workflow-side secrets, checksums, artifacts, recovery controls, and deployment sequencing are documented in [Automation](automation.md#vps-deployment).

## Volume permissions

The images expect required files to be owned by or accessible to:

```text
UID 10001
GID 10001
```

The website requires read access to the SQLite database, the generated exports, and their parent directories. When versioned mode is enabled it also needs traversal access to `/app/data/releases` and the selected release. Do not mount only the symlink target: the same directory must contain `current` and `releases`.

Generated-document rendering additionally requires write and execute access to the relevant parent directories. The CLI atomically replaces both the owned README regions and the generated registry-layout block in `docs/guides/user-guide/search-registry.md`.

A narrow Linux ACL can grant the required access without making the repository broadly writable:

```bash
sudo setfacl -m u:10001:rwx .
sudo setfacl -m u:10001:rw README.md
sudo setfacl -m u:10001:rx docs docs/guides
sudo setfacl -m u:10001:rwx docs/guides/user-guide
sudo setfacl -m u:10001:rw docs/guides/user-guide/search-registry.md
```

For a production release deployed by automation, the workflow assigns:

```text
release directories: group opportunities-site, mode 0550 (releases parent: 0750)
release database, exports, and checksums: group opportunities-site, mode 0440
```

The host data directory, `releases/`, and the selected release must be traversable by GID `10001`; symlink permissions themselves do not control traversal. The deployment user must own the data directory and have permission to create `.incoming`, `releases`, and the deployment lock.

The host-side `opportunities-site` group must map to GID `10001` so the unprivileged containers can access the bind-mounted file without broadening permissions.

Do not use `chmod 777`, run the full application as root, or make the Docker socket broadly accessible to avoid correcting ownership.

## Run without Compose

Create the persistent named volume:

```bash
docker volume create opportunities-data
```

Run the migration with explicit mounts:

```bash
docker run --rm \
  -e OPPORTUNITIES_README_PATH=/workspace/README.md \
  -v opportunities-data:/app/data \
  -v "$(pwd)/configs:/app/configs:ro" \
  -v "$(pwd):/workspace" \
  european-tech-opportunities-2027-cli:local \
  db-upgrade
```

Inspect the initialized database:

```bash
docker run --rm \
  -e OPPORTUNITIES_README_PATH=/workspace/README.md \
  -v opportunities-data:/app/data \
  -v "$(pwd)/configs:/app/configs:ro" \
  -v "$(pwd):/workspace" \
  european-tech-opportunities-2027-cli:local \
  stats
```

Reuse the same mounts for other pipeline commands.

A named volume survives `--rm`, but this standalone example is separate from the supported production host-bind topology and remains operational state rather than a backup. Backup and restore procedures belong to [Database lifecycle](database.md#backup).

## Application release and rollback

An application release changes the container image or Compose configuration. It is separate from the deployment-only canonical-state workflow, which publishes a reviewed database-and-exports release and switches `current` without rebuilding the website.

Before releasing an application revision:

1. start from a clean `main` checkout and record the commit SHA;
2. confirm Python, website, CodeQL, and Docker CI succeeded for that exact SHA;
3. confirm dependency and lockfile changes are intentional and reviewed;
4. verify `docker compose config`, both image builds, the CLI image entry point, the migrated read-only website smoke test, public downloads, and production security headers;
5. confirm the current database has a round-trip-verified durable snapshot and no canonical writer or deployment is active;
6. retain the previously working image or deployment revision for application rollback.

Release through the configured Dokploy project without changing the persistent host-state path or making the site mount writable. The application release must not initialize, replace, or downgrade canonical SQLite as a side effect.

After deployment, verify over HTTPS:

- the directory returns `200`, displays the expected count and last successful collection time, and supports filtering and pagination;
- `/robots.txt`, `/sitemap.xml`, `/open-opportunities.csv`, and `/open-opportunities.json` return the expected content and attachment headers;
- Content Security Policy, HSTS, content-type, framing, referrer, cross-origin, and permissions headers remain present;
- the site container is healthy, runs as UID/GID `10001:10001`, and can read but not write the mounted state;
- startup and request logs contain no secrets, paths, stack traces, database rows, or repeated errors.

If the application is unhealthy, roll back to the recorded prior image or deployment revision while preserving the host state directory. Do not roll back, delete, or recreate SQLite merely to match an older image. If the older image cannot read the current schema, stop the release and follow the verified database recovery and migration procedures rather than improvising a downgrade. Canonical-state rollback is a separate, evidence-preserving recovery decision documented in [Database lifecycle](database.md#restore).

## Production maintenance

Use this order for production state changes:

<div align="center">
<pre>
restore or migrate canonical state
↓
collect or repair through the controlled writer
↓
validate
↓
checkpoint + publish verified durable snapshot
↓
review and merge the README projection
↓
deploy the reviewed state and public exports
</pre>
</div>

Normal automation keeps collection and deployment separate: newly collected state is proposed through a README pull request and validated on its generated commit. A deployment-only run enters the protected `production` environment before accessing state, restores and validates reviewed durable state against `main` in that job, then switches the versioned release pointer. It does not replace the legacy fixed-path database.

After changing Dockerfile or Compose behavior, run:

```bash
uv lock --check

cd site
bun install --frozen-lockfile
bun run ci
cd ..

docker compose build
docker compose run --rm opportunities --help
docker compose config
```

Docker CI additionally runs Actionlint, Hadolint, and digest-pinned Trivy image scans. It rejects fixable high or critical image vulnerabilities and smoke-tests the migrated website, sanitized CSV/JSON downloads, production Content Security Policy, and HTTP Strict Transport Security headers.

Preserve:

- one canonical writer;
- the read-only website mount;
- the bind-mounted SQLite state directory;
- UID/GID `10001:10001`;
- frozen dependency installation and synchronized immutable image/package pins;
- no package-manager tooling in final runtime images;
- no secrets in build arguments or image layers;
- no production databases copied into images.

Run every affected check from the [development validation matrix](../development/development.md#validation-paths).

## Troubleshooting

For empty or unmigrated state directories, SQLite read permissions, generated-document atomic replacement, Compose expansion, image startup, or Dokploy routing problems, use the [Docker failures section of the troubleshooting guide](troubleshooting.md#docker-failures).

Workflow-side deployment failures belong to [GitHub Actions and deployment troubleshooting](troubleshooting.md#github-actions-and-deployment).
