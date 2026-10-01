# GitHub workflows

[← Documentation home](../docs/README.md) · [Maintainer handbook](../docs/maintainers/README.md) · [Automation](../docs/maintainers/operations/automation.md) · [Repository scripts](../scripts/SCRIPT.md)

The project's GitHub workflows check contributions, update job listings, and publish the website and documentation. This inventory explains what each workflow does and when it runs. The [automation guide](../docs/maintainers/operations/automation.md) owns setup, permissions, recovery, and deployment procedures.

You can follow runs and read their results in the repository's **Actions** tab. **PR** means pull request, and **manual** means someone with the necessary repository permissions starts a run using **Run workflow**. Scheduled times are in **UTC**, though runs may start later.

## Checks for contributions

These checks help catch problems before a change is merged. They use test data rather than the live jobs database and do not collect listings from LinkedIn.

| Workflow | When it runs | What it checks |
|---|---|---|
| [Python CI](workflows/python-ci.yml) | PR, push to `main`, manual | Python code quality, automated tests, test coverage, performance benchmarks, database upgrades, and generated-data validation. Also checks documentation links. |
| [Site CI](workflows/site-ci.yml) | PR, push to `main`, manual | Website code quality, the production build, browser behavior, accessibility, and Lighthouse scores. |
| [Docker CI](workflows/docker-ci.yml) | PR, push to `main`, manual | Workflow and container configuration, production-image builds, SPDX SBOMs and build evidence, and high/critical vulnerabilities with available fixes. Uploads evidence for 30 days and attests those files on `main`. Also tests database access, downloads, redirects, and security headers. |
| [CodeQL](workflows/codeql.yml) | PR, push to `main`, Monday 05:31, manual | Potential security problems in Python and TypeScript. Results appear in GitHub code scanning. |
| [Gitleaks](workflows/gitleaks.yml) | PR, push to `main`, manual | Accidentally committed credentials and other secrets. Checks new commits on pushes and PRs, or the fetched history on manual runs. Sensitive finding values are redacted. |
| [Dependency Review](workflows/dependency-review.yml) | PR only | Newly introduced dependencies with known high/critical vulnerabilities, including development dependencies. It does not audit every dependency already in the project. |
| [OpenSSF Scorecard](workflows/scorecard.yml) | Saturday 06:17, manual from `main` | Repository security and supply-chain practices. Publishes a public assessment and supported code-scanning findings; individual findings do not automatically block merging. |

If a check fails on your contribution, open its run in **Actions** and look for the failed step. For local test commands, see the [testing guide](../docs/maintainers/engineering/testing.md).

## Documentation

| Workflow | When it runs | What it does |
|---|---|---|
| [Documentation site](workflows/documentation.yml) | PR, push to `main`, manual | Checks Markdown, terminology, and local links, then builds the documentation. Successful runs on `main` publish it to GitHub Pages; PR runs only check the proposed changes. |
| [Documentation links](workflows/docs-links.yml) | Wednesday 06:41, manual | Checks links in the root Markdown files and documentation, including external websites. Individual LinkedIn job links are excluded because they can expire or reject automated checks. Runs separately from PR checks so external outages do not block contributions. |

## Listing updates and deployment

Maintainers use these workflows to update listings, verify backups, and publish reviewed data. Manual runs must use the `main` branch. Collection and availability checks require current permission to access LinkedIn; starting a workflow does not grant that permission.

| Workflow | When it runs | What it does |
|---|---|---|
| [Nightly full update](workflows/nightly.yml) | Daily at 04:23 | Checks stored listings for availability, then collects new results. Saves a database snapshot and opens or updates one README-only PR. Requests automatic merging after validation, subject to required checks and reviews. Retains the aggregate collection-quality report separately. Does not deploy the website. |
| [Scrape jobs or deploy reviewed state](workflows/scrape.yml) | Manual | Normally collects listings and opens a README PR for manual review, without running a full availability check; collection runs retain a separate aggregate quality report. Selecting `deploy_to_vps=true` instead publishes already-reviewed data to the website without contacting LinkedIn. |
| [Check job availability](workflows/check-availability.yml) | Manual | Checks stored listings without discovering new jobs. Removes confirmed unavailable listings and keeps those whose availability is uncertain. Saves a snapshot and opens a README PR for manual review. |
| [Add manually reviewed jobs](workflows/add-job.yml) | Manual, with `jobs_json` | Validates and adds a batch of 1–10 listings independently reviewed by a maintainer. Saves a snapshot and opens a dated README PR for manual review. Does not contact LinkedIn or deploy the website. |
| [Verify canonical state recovery](workflows/canonical-state-drill.yml) | Manual | Restores a database snapshot, checks it, and verifies that a newly published snapshot can be restored. Does not contact LinkedIn, but **does publish a snapshot**: it is not a dry run. Its optional `adopt_public_review_seal` mode proposes the initial README state-verification marker; `recover_readme_proposal` instead recreates a missing or closed state proposal for manual review. These mutually exclusive modes do not publish snapshots or deploy. |

### How updates reach the website

1. An update workflow saves the new database state and proposes the corresponding README changes.
2. The README PR goes through validation and review. Nightly updates can merge automatically if all configured requirements are met; other listing updates require a manual merge.
3. After the matching PR is merged, a maintainer runs **Scrape jobs or deploy reviewed state** from `main` with `deploy_to_vps=true` to publish that data.

Merging a listing-update PR does not deploy the website automatically. If the saved data does not match the reviewed README, further updates and deployment stop until the difference is resolved. For a missing or closed proposal, follow [README proposal recovery](../docs/maintainers/operations/automation.md#recover-a-missing-readme-state-proposal) rather than rerunning collection.

The downloadable files attached to dataset runs contain only the public README, CSV/JSON listings, and dataset metadata. They are available for 30 days and are **not database backups**. Collection workflows retain a separate aggregate-only quality report for 30 days; it contains no listing content. The live database is not uploaded to GitHub artifacts.

For setup, input examples, approvals, and recovery instructions, see the [automation guide](../docs/maintainers/operations/automation.md). Source-access requirements are explained in the [security policy](../SECURITY.md).

## Shared workflows

The listing workflows use these two helpers. You do not need to start them separately; they run as part of the workflow you selected.

| Workflow | What it does |
|---|---|
| [Reusable canonical-state processing](workflows/reusable-process-state.yml) | Restores and checks the database, performs the requested update or recovery operation, and saves verified results. Also handles deployment when requested. |
| [Reusable README pull request](workflows/reusable-readme-pr.yml) | Creates or updates a PR containing only the generated README changes. Starts Python CI, Site CI, Docker CI, CodeQL, Gitleaks, and Documentation site checks on that commit, then waits for their results before requesting any automatic merge. |

## Other GitHub features

These files support contributions and workflow setup but are not separate workflows you can run.

| File | Purpose |
|---|---|
| [Python setup action](actions/setup-python/action.yml) | Gives workflows a consistent Python environment and installs the project's locked dependencies. |
| [Dependabot](dependabot.yml) | Proposes weekly dependency updates for the website, Python, GitHub Actions, and Docker. Does not merge or deploy updates. |
| [Code owners](CODEOWNERS) | Identifies `@simonesiega` as the default reviewer for repository changes. Whether approval is required depends on the repository's review settings. |
| [Listing suggestion](ISSUE_TEMPLATE/add-position.yml) | Lets you suggest a public listing for review. Submitting an issue does not add it to the directory automatically. |
| [Bug report](ISSUE_TEMPLATE/bug-report.yml) | Helps you describe a problem, how to reproduce it, and the expected behavior. Use private reporting for security vulnerabilities, and never include credentials or private data. |
| [Feature request](ISSUE_TEMPLATE/feature-request.yml) | Helps you explain a user need, your proposed improvement, and any safety or compatibility concerns. |
| [Issue chooser](ISSUE_TEMPLATE/config.yml) | Offers the issue forms and links to private vulnerability reporting, documentation, and the Code of Conduct. |
| [PR template](pull_request_template.md) | Provides a checklist for explaining your changes, testing, and review considerations. |
| [Terminology rule](vale/styles/Project/Terminology.yml) | Checks consistent spellings such as GitHub, LinkedIn, SQLite, and Next.js in documentation. |
| [Directory-label rule](vale/styles/Project/DirectoryLabels.yml) | Checks that standalone Internship and New Grad headings match the names used in the directory. |
