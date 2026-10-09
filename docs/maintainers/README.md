# Maintainer handbook

[← Documentation home](../README.md) · [Using the product](../users/README.md) · [Contributing](../../CONTRIBUTING.md) · [Security](../../SECURITY.md)

This handbook covers development, system contracts, validation, and production operations. Use disposable databases with synthetic listings for development. Before production work, confirm the required approval, a verified recovery source, and exclusive writer access. If you want to browse roles or download listings, start with the [user guides](../users/README.md).

## Develop offline

1. Follow [local setup](getting-started/setup.md); do not use production SQLite or enable collection.
2. Read [architecture and invariants](engineering/architecture.md) before changing boundaries.
3. Add a test for the behavior at risk, implement the smallest robust change, and run the [affected validation gates](engineering/testing.md#validation-paths).
4. Update the relevant guide, review the complete diff, and follow [the contribution workflow](../../CONTRIBUTING.md).

## Getting started

| Area | Guide |
|---|---|
| Tools and first local launch | [Setup](getting-started/setup.md) |
| Paths, precedence, limits, and authorization variables | [Configuration reference](getting-started/configuration.md) |

## Engineering

| Area | Guide |
|---|---|
| Ownership, dependency direction, and generated projections | [Architecture and invariants](engineering/architecture.md) |
| Visual subsystem maps and implementation links | [Repository maps](../assets/diagram/README.md) · [Diagram source](../assets/diagram/source.md) |
| Acceptance and rejection evidence | [Classification](engineering/classification.md) |
| Discovery YAML, query identities, and request tiers | [Search registry](engineering/search-registry.md) |
| Read-only queries, browser state, URL behavior, and metadata | [Website engineering](engineering/website.md) |
| Behavior contracts, test placement, and validation commands | [Testing strategy](engineering/testing.md) |
| Shared writing style, navigation, and generated regions | [Documentation maintenance](engineering/documentation.md) |
| Public images, diagrams, and tour reproduction | [Visual assets](../assets/README.md) |
| Promotional film source recovery, editing, and replacement | [Video maintenance](../assets/promo/maintainers/VIDEO.md) |

## Operate and recover

| Task | Procedure |
|---|---|
| Inspect commands, inputs, side effects, and exit codes | [CLI reference](operations/cli.md) |
| Configure CI, schedules, protected environments, or snapshot storage | [Automation](operations/automation.md) |
| Review a collected state and publish it | [Post-nightly runbook](operations/automation.md#post-nightly-production-runbook) |
| Understand closure, timestamps, schema, or migrations | [Database and lifecycle](operations/database.md) |
| Back up or restore canonical history | [Database recovery](operations/database.md#backup) |
| Build images, set permissions, or release the application | [Containers and deployment](operations/deployment.md) |
| Roll back the served projection | [Release-pointer rollback](operations/automation.md#coordinated-first-rollout-and-rollback) |
| Diagnose a failure without losing evidence | [Operator troubleshooting](operations/troubleshooting.md) |

For file-by-file inventories, use [GitHub workflows](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/WORKFLOWS.md), [repository scripts](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/scripts/SCRIPT.md), and [test inventory](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/tests/TEST.md). These references open on GitHub and describe individual entry points; use the guides above for step-by-step procedures.

An upstream block, failed migration, invalid snapshot, or mismatched reviewed projection is a **stop condition**, not permission to rebuild or bypass checks. No guide grants source-access authorization.

## Releases

See the [v1.0.0 release notes](../releases/v1.0.0.md) for stable product scope and compatibility. Release preparation does not authorize publication or deployment.

## Agents and policy ownership

Coding agents start with the root [agent guidelines](../../AGENTS.md), then load only the relevant guides. Root [Security](../../SECURITY.md), [Privacy](../../PRIVACY.md), [Contributing](../../CONTRIBUTING.md), [Code of Conduct](../../CODE_OF_CONDUCT.md), and [License](../../LICENSE) remain canonical. Do not copy policies into new pages.
