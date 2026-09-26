# European Tech Opportunities 2027 Documentation

[← Project README](../README.md) · [Contributing](../CONTRIBUTING.md) · [Security policy](../SECURITY.md) · [Privacy notice](../PRIVACY.md) · [Open the opportunity directory](https://techopportunities.eu/)

The live website is the primary interface for browsing opportunities. This documentation is the canonical reference for setup, CLI usage, search configuration, production operation, architecture, development, and project policies.

## Start here

- **Looking for a role?** Open the [live opportunity directory](https://techopportunities.eu/) or read the [website guide](guides/user-guide/website.md).
- **Running locally?** Start with [installation](guides/getting-started/installation.md) and [configuration](guides/getting-started/configuration.md).
- **Using the CLI or changing searches?** Read the [CLI reference](guides/user-guide/cli.md) and [search registry guide](guides/user-guide/search-registry.md).
- **Operating production?** Use [automation](guides/operations/automation.md), [database and lifecycle](guides/operations/database.md), [Docker and deployment](guides/operations/docker.md), and [troubleshooting](guides/operations/troubleshooting.md).
- **Contributing?** Read [`CONTRIBUTING.md`](../CONTRIBUTING.md), then use the [development](guides/development/development.md) and [architecture](guides/development/architecture.md) guides.

## Setup

| Guide | Use it when |
|---|---|
| [Installation](guides/getting-started/installation.md) | Setting up Python, `uv`, Bun, SQLite, the local website, or optional Docker tooling. |
| [Configuration](guides/getting-started/configuration.md) | Configuring paths, limits, HTTP controls, logging, website settings, and authorization interlocks. |

## Using the project

| Guide | Covers |
|---|---|
| [Website](guides/user-guide/website.md) | Search, filters, sorting, pagination, themes, sanitized CSV/JSON downloads, and read-only behavior. |
| [CLI reference](guides/user-guide/cli.md) | Commands, options, side effects, network behavior, and exit codes. |
| [Search registry](guides/user-guide/search-registry.md) | Search groups, YAML schema, validation, limit tiers, and query changes. |

## Operating production

| Guide | Covers |
|---|---|
| [Automation](guides/operations/automation.md) | Validation CI, scheduled collection, durable snapshots, artifacts, and VPS deployment. |
| [Database and lifecycle](guides/operations/database.md) | Schema, persistence, provenance, lifecycle state, migrations, backup, and restore. |
| [Docker and deployment](guides/operations/docker.md) | Images, Compose, volumes, permissions, containers, and Dokploy. |
| [Troubleshooting](guides/operations/troubleshooting.md) | Exit codes, common failures, diagnosis, and safe recovery. |

## Developing

| Guide | Covers |
|---|---|
| [Architecture](guides/development/architecture.md) | Complete data flow, component boundaries, classification, persistence, failure isolation, and projections. |
| [Development](guides/development/development.md) | Repository workflow, implementation details, tests, fixtures, quality gates, and validation paths. |

## Project policies

| Document | Covers |
|---|---|
| [Contributing](../CONTRIBUTING.md) | Contributor workflow, coding expectations, validation, documentation rules, and pull-request requirements. |
| [Security policy](../SECURITY.md) | Vulnerability reporting, source-access boundaries, trust boundaries, secrets, and safe operation. |
| [Privacy notice](../PRIVACY.md) | Website infrastructure, analytics, browser storage, external services, and visitor choices. |
| [Code of Conduct](../CODE_OF_CONDUCT.md) | Community standards, conduct reporting, and enforcement. |

## Visual assets

Screenshots, sanitized listing examples, and project identity assets live under [`docs/assets/`](assets/):

```text
assets/
├── listings/     # sanitized public listing examples
├── logo/         # project identity
└── sites/        # website previews
```

Documentation contributions should follow the [documentation guidelines](../CONTRIBUTING.md#documentation-changes).
