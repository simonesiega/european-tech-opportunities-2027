# Docker

[← README](../README.md)

Docker is an optional reproducible runtime. Local development and CI can use `uv` directly; Docker does not change collection authorization, classification, or database lifecycle rules.

## Image design

[`Dockerfile`](../Dockerfile) uses:

```text
ghcr.io/astral-sh/uv:python3.12-bookworm-slim
```

Build sequence:

1. Set `/app` as the working directory.
2. Copy `pyproject.toml`, `uv.lock`, README, and license.
3. Install frozen production dependencies without installing the project, allowing dependency-layer reuse.
4. Copy Alembic configuration/migrations, search/classification configuration, and source.
5. Install the project from the frozen lockfile without development dependencies.
6. Create unprivileged user/group `internships` with UID/GID `10001:10001`.
7. Create and assign `/app/data` to that user.
8. Run all commands as the unprivileged user.

Runtime environment:

| Variable | Value | Purpose |
|---|---|---|
| `PYTHONUNBUFFERED` | `1` | Send logs/output immediately. |
| `PYTHONDONTWRITEBYTECODE` | `1` | Avoid runtime `.pyc` writes. |
| `UV_COMPILE_BYTECODE` | `1` | Compile dependencies during installation. |
| `UV_LINK_MODE` | `copy` | Avoid cross-filesystem link warnings and coupling. |

The entry point is:

```text
uv run --no-sync internships
```

The default command is `--help`. `--no-sync` prevents runtime dependency mutation.

The image contains code, migrations, configs, README, and dependencies. It does not contain `data/internships.db`, `.env`, development tools, or local build artifacts.

## Build and inspect

```bash
docker build --tag european-tech-internships-2027:local .
docker run --rm european-tech-internships-2027:local --help
```

Or with Compose:

```bash
docker compose build
docker compose run --rm internships --help
```

No LinkedIn request occurs for these commands.

## Compose service

[`docker-compose.yml`](../docker-compose.yml) defines a one-shot CLI service named `internships`.

Important settings:

```yaml
environment:
  INTERNSHIPS_DATABASE_URL: sqlite:////app/data/internships.db
  INTERNSHIPS_SEARCH_CONFIG_DIR: /app/configs/searches
  INTERNSHIPS_CATEGORY_CONFIG_PATH: /app/configs/categories.yml
  INTERNSHIPS_README_PATH: /workspace/README.md
volumes:
  - ./data:/app/data
  - ./configs:/app/configs:ro
  - ./:/workspace
init: true
```

| Host path | Container path | Mode | Purpose |
|---|---|---|---|
| `./data` | `/app/data` | read/write | Canonical SQLite database and sidecars. |
| `./configs` | `/app/configs` | read-only | Search and classification configuration. |
| `./` | `/workspace` | read/write | Repository working tree used for atomic replacement of `README.md`. |

Mounting the repository directory instead of `README.md` alone is intentional. The renderer creates a temporary sibling file and then atomically replaces the README; an individual file bind mount can prevent that replacement. The application should modify only `/workspace/README.md`.

`init: true` adds a small init process for correct signal forwarding and child reaping.

Compose reads `.env` when present and passes `INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED`, defaulting to false. The service's explicit absolute container paths override local host paths from `.env`.

## Initialize a fresh mounted database

From the repository root:

```bash
mkdir -p data
docker compose run --rm internships db-upgrade
docker compose run --rm internships render
docker compose run --rm internships validate
docker compose run --rm internships stats
```

Run Compose from the repository root. The committed `README.md` is available at `/workspace/README.md` through the repository-directory mount.

## Offline commands

```bash
docker compose run --rm internships searches
docker compose run --rm internships stats
docker compose run --rm internships render
docker compose run --rm internships validate
```

These commands do not contact LinkedIn.

## Authorized collection

Docker does not grant permission or anonymity. The same express LinkedIn authorization requirement applies.

Only after permission, configure the host `.env`:

```dotenv
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true
```

Test one non-persisting search:

```bash
docker compose run --rm internships search-test company-amazon
```

Then one persisted search:

```bash
docker compose run --rm internships scrape --search company-amazon
```

Or all enabled searches:

```bash
docker compose run --rm internships scrape
```

Changes to `/app/data/internships.db` and `/workspace/README.md` persist on the host.

To override the gate for one command without changing `.env`:

```bash
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true docker compose run --rm internships scrape --search company-amazon
```

Use that only after documented permission. The environment value remains an interlock, not authorization.

## Linux bind-mount permissions

The image runs as UID/GID `10001:10001`. On native Linux, bind mounts retain host ownership and mode bits. The container must be able to:

- create and write files under `./data`;
- read `README.md`;
- create a temporary sibling file in the repository root;
- atomically replace `README.md`.

Atomic replacement requires write and execute permission on the repository root, not only write permission on the README file.

Preferred options:

1. For local development, run the one-shot container as your host UID/GID.
2. Grant UID/GID `10001:10001` a narrow ACL on `data/`, `README.md`, and the repository root.

Example host-user command:

```bash
docker compose run --rm --user "$(id -u):$(id -g)" internships render
```

Example ACL approach on systems with `setfacl`:

```bash
sudo setfacl -R -m u:10001:rwx data
sudo setfacl -m d:u:10001:rwx data
sudo setfacl -m u:10001:rwx .
sudo setfacl -m u:10001:rw README.md
```

The host-user approach creates database and README changes as your user, which is usually preferable for local development. Keep one consistent ownership strategy.

Do not use `chmod 777` or run the complete container as root merely to hide a permission problem.

Docker Desktop on Windows/macOS mediates bind-mount permissions differently, but the repository directory must still be shared with Docker Desktop.

## Running without Compose

Create a named volume for SQLite, mount configuration read-only, and mount the repository directory for README generation:

```bash
docker volume create internships-data

docker run --rm \
  -e INTERNSHIPS_README_PATH=/workspace/README.md \
  -v internships-data:/app/data \
  -v "$(pwd)/configs:/app/configs:ro" \
  -v "$(pwd):/workspace" \
  european-tech-internships-2027:local db-upgrade
```

Repeat the same mounts for `render`, `validate`, and collection commands. On Windows, adapt shell path syntax or use Compose.

A named volume protects container data from `docker run --rm`, but it is not a backup. Export it or use SQLite's backup API as described in [Database lifecycle](database.md#backups).

## Configuration overrides

Pass process environment values with Compose:

```bash
INTERNSHIPS_LOG_LEVEL=DEBUG docker compose run --rm internships stats
```

PowerShell:

```powershell
$env:INTERNSHIPS_LOG_LEVEL = "DEBUG"
docker compose run --rm internships stats
Remove-Item Env:INTERNSHIPS_LOG_LEVEL
```

Or with `docker run`:

```bash
docker run --rm \
  -e INTERNSHIPS_DATABASE_URL=sqlite:////app/data/internships.db \
  -v internships-data:/app/data \
  european-tech-internships-2027:local stats
```

If overriding config or README paths, mount the matching files/directories too. Container-internal paths must not refer to host paths such as `C:\...`.

See [Configuration](configuration.md) for all values.

## Production operation

The image is a CLI job, not a long-running server. A production scheduler should execute one command, wait for its exit code, and preserve mounted state.

Recommended sequence:

```text
db-upgrade
    ↓
scrape
    ↓
validate
    ↓
SQLite backup/checkpoint
```

Do not run multiple scrape containers against the same SQLite mount. Use scheduler/concurrency controls to enforce one writer.

Capture normal stdout/stderr, but do not enable logging that prints environment files, response bodies, or mounted database content.

## Image maintenance

When dependencies, Python compatibility, or packaging changes:

```bash
uv lock --check
docker build --no-cache --tag european-tech-internships-2027:check .
docker run --rm european-tech-internships-2027:check --help
docker compose config
```

For a stronger smoke test, use a temporary volume and temporary README copy, migrate a clean database, render, and validate.

Review upstream base-image changes and consider immutable digest pinning for environments that require strict supply-chain reproducibility.

## Troubleshooting

### README rendering or replacement fails

Ensure Compose is run from the repository root and that the service mounts the repository directory:

```yaml
- ./:/workspace
```

Do not mount `README.md` as an individual file. The renderer creates a temporary sibling and atomically replaces the destination, which may fail when the destination itself is a file mount.

### Permission denied writing SQLite or README

Inspect ownership and directory permissions:

```bash
ls -ldn . README.md data
```

Use a narrow ACL or the host-user one-off approach above. Atomic replacement requires write and execute permission on the repository root because the renderer creates a temporary sibling file before replacing `README.md`.

### Container reports an unmigrated database

```bash
docker compose run --rm internships db-upgrade
```

Ensure every command uses the same `./data` mount.

### Configuration exists on host but not in container

Run:

```bash
docker compose config
```

Verify path expansion, `.env` values, and that `./configs` is mounted at `/app/configs`.

For additional application failures, see [Troubleshooting](troubleshooting.md).