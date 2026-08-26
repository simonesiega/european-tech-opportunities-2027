# European Tech Opportunities 2027 Documentation

[← Project README](../README.md) · [Open the opportunity directory](https://opportunities2027.simonesiega.com/)

The live website is the primary interface for browsing opportunities. These task-oriented guides explain how to use, run, operate, and develop the open-source opportunity directory and data pipeline.

## Start here

- **Looking for a role?** Open the [live opportunity directory](https://opportunities2027.simonesiega.com/) or read the [website guide](guides/user-guide/website.md).
- **Running locally?** Start with [installation](guides/getting-started/installation.md) and [configuration](guides/getting-started/configuration.md).
- **Operating production?** Read [automation](guides/operations/automation.md), [database and lifecycle](guides/operations/database.md), and [Docker and deployment](guides/operations/docker.md).
- **Contributing?** Read [`CONTRIBUTING.md`](../CONTRIBUTING.md), then use the [architecture](guides/development/architecture.md) and [development](guides/development/development.md) guides.

## Getting started

| Guide | Use it when |
|---|---|
| [Installation](guides/getting-started/installation.md) | Setting up Python, `uv`, Bun, SQLite, or the local website. |
| [Configuration](guides/getting-started/configuration.md) | Configuring paths, limits, HTTP controls, logging, website settings, and authorization interlocks. |

## Using the project

| Guide | Covers |
|---|---|
| [Website](guides/user-guide/website.md) | Search, filters, sorting, pagination, themes, public data, and read-only behavior. |
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
| [Architecture](guides/development/architecture.md) | Complete data flow, component boundaries, classification, persistence, and projections. |
| [Development](guides/development/development.md) | Repository workflow, implementation details, tests, fixtures, and quality gates. |
| [Contributing](../CONTRIBUTING.md) | Contributor workflow, standards, documentation rules, and pull-request expectations. |
| [Security](../SECURITY.md) | Responsible disclosure, collection authorization boundaries, trust boundaries, and safe operation. |
| [Code of Conduct](../CODE_OF_CONDUCT.md) | Community standards, conduct reporting, and enforcement. |

## Visual assets

Screenshots, sanitized listing examples, and project identity assets live under [`docs/assets/`](assets/):

```text
assets/
├── listings/     # sanitized public listing examples
├── logo/         # project identity
└── sites/        # website previews
```

Documentation contributors should follow the documentation guidelines in [`CONTRIBUTING.md`](../CONTRIBUTING.md#documentation-changes).
