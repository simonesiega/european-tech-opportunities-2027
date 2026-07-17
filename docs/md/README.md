# European Tech Internships 2027 Documentation

[← Project README](../../README.md) · [Open the internship directory](https://internship2027.simonesiega.com/)

This documentation is organized by task. The website is the primary public interface; the remaining guides explain how to run, operate, and extend the data pipeline safely.

## Start here

- **Looking for an internship?** Open the [live directory](https://internship2027.simonesiega.com/) or read the [website guide](user-guide/website.md).
- **Running the project locally?** Start with [installation](getting-started/installation.md) and [configuration](getting-started/configuration.md).
- **Operating a deployment?** Read [automation](operations/automation.md), [database](operations/database.md), and [Docker and deployment](operations/docker.md).
- **Contributing code?** Begin with [architecture](development/architecture.md) and [`CONTRIBUTING.md`](../../CONTRIBUTING.md).

## Getting started

| Guide | Use it when |
|---|---|
| [Installation](getting-started/installation.md) | Setting up Python, `uv`, Bun, SQLite, or the local website for the first time. |
| [Configuration](getting-started/configuration.md) | Configuring paths, limits, HTTP controls, logging, and reviewing the LinkedIn authorization gate. |

## Using the project

| Guide | Covers |
|---|---|
| [Website](user-guide/website.md) | Search, filters, sorting, pagination, themes, public data, and read-only local or production behavior. |
| [CLI reference](user-guide/cli.md) | Commands, options, network behavior, and exit codes. |
| [Search registry](user-guide/search-registry.md) | Search groups, YAML schema, validation, tiers, and adding a query. |

## Operating production

| Guide | Covers |
|---|---|
| [Automation](operations/automation.md) | Validation CI, permission-gated scheduled collection, manual dispatch, caching, artifacts, and VPS deployment. |
| [Database](operations/database.md) | Schema, lifecycle, provenance, migrations, backup, and restore. |
| [Docker and deployment](operations/docker.md) | Production images, Compose, volumes, Dokploy, and permissions. |
| [Troubleshooting](operations/troubleshooting.md) | Exit codes, common failures, diagnosis, and safe recovery. |

## Developing

| Guide | Covers |
|---|---|
| [Architecture](development/architecture.md) | Data flow, component boundaries, classification, persistence, and projections. |
| [Development](development/development.md) | Repository layout, tests, quality gates, fixtures, migrations, and review workflow. |
| [Contributing](../../CONTRIBUTING.md) | Contribution boundaries, pull-request expectations, and checklists. |
| [Security](../../SECURITY.md) | Responsible disclosure, trust boundaries, and safe operation. |

## Visual assets

Project screenshots, source-listing examples, and identity assets live under [`docs/photo/`](../photo/):

```text
photo/
├── internship/   # source-listing examples
├── logo/         # project identity
└── sites/        # website previews
```

Use repository-relative paths, descriptive alt text, and WebP for new raster images. Never commit screenshots containing credentials, cookies, private browser data, or authenticated LinkedIn content.

## Documentation conventions

- Commands are shown from the repository root unless a guide says otherwise.
- Keep internal repository links relative.
- Use `https://internship2027.simonesiega.com/` for links to the public directory.
- Never edit generated README internship rows manually.
- Examples must preserve the authorization and one-writer safety model.