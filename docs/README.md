# Documentation

**[Open European Tech Opportunities →](https://techopportunities.eu/)** · [Project showcase](../README.md) · [Searchable docs](https://docs.techopportunities.eu/)

Find validated 2027 technology internships and New Grad roles across Europe. You do not need an account, an installation, or technical knowledge to use the directory.

## Using the product

Guides for job seekers and anyone using the public data.

### Browsing

| Task | Guide |
|---|---|
| Find a role and share a search | [Browse, search, and filter](users/browsing/directory.md) |
| Keep track of roles privately | [Saved, applied, hidden, and new](users/browsing/lists.md) |
| Understand missing jobs, dates, or a problem | [Questions and troubleshooting](users/browsing/help.md) |

### Data

| Task | Guide |
|---|---|
| Download listings for a spreadsheet or script | [Get the dataset](users/data/data.md) |
| Query listings from another application | [Use the public API](users/data/api.md) |

[Start the user guide →](users/README.md) · [Privacy notice](../PRIVACY.md)

## Maintaining the project

Set up a development environment, understand how listings are validated, or operate the service. These guides are for contributors and maintainers; you do not need them to browse the directory.

### Getting started

| Task | Guide |
|---|---|
| Set up an offline development environment | [Local setup](maintainers/getting-started/setup.md) |
| Choose settings, paths, and request limits | [Configuration reference](maintainers/getting-started/configuration.md) |

### Engineering

| Task | Guide |
|---|---|
| Understand ownership and safety contracts | [Architecture and invariants](maintainers/engineering/architecture.md) |
| Change acceptance rules or discovery | [Classification](maintainers/engineering/classification.md) · [Search registry](maintainers/engineering/search-registry.md) |
| Change the website without changing canonical state | [Website engineering](maintainers/engineering/website.md) |
| Test a change | [Testing strategy and gates](maintainers/engineering/testing.md) |
| Update docs or reproduce public visuals | [Documentation maintenance](maintainers/engineering/documentation.md) · [Visual assets](assets/README.md) |
| Recreate, edit, or replace the promotional film | [Video maintenance](assets/promo/maintainers/VIDEO.md) |

### Operations

| Task | Guide |
|---|---|
| Inspect commands and their side effects | [CLI reference](maintainers/operations/cli.md) |
| Configure workflows and protected environments | [Automation and operations](maintainers/operations/automation.md) |
| Preserve, migrate, or recover canonical state | [Database and lifecycle](maintainers/operations/database.md) |
| Build containers and release the application | [Containers and deployment](maintainers/operations/deployment.md) |
| Diagnose an operational failure | [Operator troubleshooting](maintainers/operations/troubleshooting.md) |

[Open the maintainer handbook →](maintainers/README.md)

## Repository maps

[Read the annotated maps](assets/diagram/README.md) for explanations, a legend, and clickable implementation links. All five diagrams are generated from the [editable Mermaid source](assets/diagram/source.md). Follow its [rendering profile](assets/diagram/source.md#rendering-profile) to regenerate them.

| View | Full-size diagram |
|---|---|
| How the whole repository fits together | [Repository overview](assets/diagram/svg/repository.svg) |
| How evidence becomes accepted lifecycle state | [Collection and lifecycle](assets/diagram/svg/collection.svg) |
| How public data reaches users and browser-local lists stay private | [Website and publication](assets/diagram/svg/website.svg) |
| How protected updates, review, and deployment connect | [Automation and deployment](assets/diagram/svg/automation.svg) |
| How tests, documentation, and tooling support the system | [Repository foundations](assets/diagram/svg/foundations.svg) |

## Releases

[v1.0.0 release notes](releases/v1.0.0.md) summarize the first stable product, compatibility, and operating boundaries.

## Repository references

Find individual workflows, scripts, and tests in these GitHub references. For setup and step-by-step procedures, use the maintainer guides above.

| Task | Reference |
|---|---|
| Identify a workflow, trigger, or shared action | [GitHub workflows](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/WORKFLOWS.md) |
| Choose a repository script and understand its effects | [Repository scripts](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/scripts/SCRIPT.md) |
| Understand every test and the behavior it protects | [Test inventory and review](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/tests/TEST.md) |
| Find coding-agent instructions and safety boundaries | [Agent guidelines](../AGENTS.md) |

## Policies and community

The root policy files remain authoritative: [Contributing](../CONTRIBUTING.md), [Security](../SECURITY.md), [Privacy](../PRIVACY.md), [Code of Conduct](../CODE_OF_CONDUCT.md), and [MIT License](../LICENSE).

[Suggest a listing](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=add-position.yml) · [Report a product problem](https://github.com/simonesiega/european-tech-opportunities-2027/issues/new?template=bug-report.yml). Report security issues **privately**, using the security policy.
