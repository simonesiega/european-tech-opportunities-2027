<h1 align="center">
  Security Policy
</h1>

<p align="center">
  Responsible disclosure and safe-operation guidance for European Tech Internships 2027.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/security-private%20reporting-red" alt="Private vulnerability reporting" />
  <img src="https://img.shields.io/badge/LinkedIn-disabled%20by%20default-0A66C2?logo=linkedin&logoColor=white" alt="LinkedIn collection disabled by default" />
  <img src="https://img.shields.io/badge/supported-main%20%7C%200.1.x-brightgreen" alt="Supported versions: main and 0.1.x" />
  <a href="LICENSE"><img src="https://img.shields.io/github/license/simonesiega/european-tech-internships-2027" alt="MIT license" /></a>
</p>

## Supported versions

Security fixes are handled for the current `main` branch and latest `0.1.x` release.

| Version | Support |
|---|---|
| `main` | Supported for unreleased fixes. |
| Latest `0.1.x` release | Supported. |
| Older commits/releases | Best effort only. |

## Reporting a vulnerability

Do not open a public issue for a vulnerability or include exploitation details in a public pull request.

Report privately through either channel:

| Channel | Contact |
|---|---|
| GitHub private vulnerability reporting | [Open a private security advisory](https://github.com/simonesiega/european-tech-internships-2027/security/advisories/new) |
| Email | [simonesiega1@gmail.com](mailto:simonesiega1@gmail.com) |

Do not send real credentials, cookies, account sessions, private HTML, unredacted environment files, or a production database. Use synthetic data and redact local paths, query strings, identifiers, and headers unless they are essential to understanding the issue.

A useful report includes:

| Field | Details |
|---|---|
| Summary | A concise description of the vulnerability. |
| Impact | Data, command, workflow, or trust boundary affected. |
| Reproduction | Minimal deterministic steps using synthetic or redacted data. |
| Environment | OS, Python version, project version/commit, and execution path. |
| Preconditions | Required configuration, permissions, and attacker access. |
| Suggested mitigation | Optional, but helpful if you have a safe fix. |

## What to expect

The maintainer will:

1. acknowledge the report when reasonably possible;
2. investigate and attempt to reproduce it;
3. assess impact and affected versions;
4. coordinate remediation and tests;
5. agree on disclosure timing before publishing details.

No guaranteed response or remediation deadline is promised. Please avoid public disclosure until a fix is available or disclosure has been coordinated.

## Security model

The supported pipeline is deliberately narrow:

```text
permission-gated LinkedIn guest HTML
                 ↓
       strict local processing
                 ↓
        local SQLite state
                 ↓
       generated README table
```

### Operation matrix

| Operation | Reads | Writes | Network |
|---|---|---|---|
| `db-upgrade` | Alembic configuration and migration files | SQLite schema/version | None |
| `searches` / `stats` | YAML configuration and optional SQLite state | Nothing | None |
| `search-test` | YAML rules and public LinkedIn guest HTML | Nothing persistent | LinkedIn only after authorization gate |
| `scrape` | YAML rules, SQLite known jobs, LinkedIn guest HTML | SQLite and normally README | LinkedIn only after authorization gate |
| `render` | Open SQLite jobs and README markers | README via atomic replacement | None |
| `validate` | SQLite state and README | Nothing | None |
| Manual collection workflow | Repository, cached SQLite, authorized LinkedIn HTML | Cache, artifact, optional README pull request | GitHub and LinkedIn |

### Source-access boundary

The project does not require, accept, or implement:

- LinkedIn usernames or passwords;
- session cookies, authentication headers, or account tokens;
- browser automation or logged-in browsing;
- CAPTCHA solving or challenge bypass;
- private/internal LinkedIn APIs;
- proxy rotation, fingerprint evasion, or anti-bot bypasses;
- redirect-based endpoint discovery;
- collection from unrelated providers.

LinkedIn collection is blocked unless `INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true`. This is a local safety interlock, not permission. Operators are responsible for obtaining and retaining express authorization and for complying with applicable terms, policies, law, and collection limits.

Do not remove, weaken, or silently default this gate to true.

### Network safeguards

The HTTP transport is designed for bounded, identifiable access:

- no redirects;
- explicit connection and overall timeouts;
- bounded connection count and search concurrency;
- host-level request pacing;
- finite retries with exponential backoff;
- bounded `Retry-After` handling;
- bounded response size checked before and after reading;
- HTML/text content-type validation;
- retry only for transport/timeouts, HTTP 429, and HTTP 5xx;
- sanitized error codes and messages rather than response bodies;
- an identifying project/version user agent.

A parser or transport change must preserve these limits. An upstream block or challenge is a signal to stop, not a problem to bypass.

### Local data safeguards

`data/internships.db` is canonical lifecycle state. It contains public job metadata, search provenance, timestamps, and run diagnostics. It should not contain LinkedIn credentials or cookies, but it is operationally important and should still be handled carefully.

- The database and SQLite sidecar files are ignored by Git.
- `.env` and `configs/settings.yml` are ignored by Git.
- README output contains only company, title, location, and public LinkedIn link.
- Search errors are truncated and sanitized before persistence.
- README writes use a same-directory temporary file and atomic replacement.
- SQLite writes use short transactions per completed search.
- Failed searches record failure diagnostics but do not alter that search's job lifecycle.
- Closure requires repeated explicit detail-page unavailability; search absence is ignored.

Back up SQLite before migration recovery, manual repair, or a workflow state rebuild. Do not upload production databases to public issues. Operational details are documented in [Database lifecycle](docs/database.md).

### Automation safeguards

The collection workflow is manual-only and guarded by the repository variable `LINKEDIN_CRAWL_AUTHORIZED=true`. It has no unattended schedule.

The workflow may upload `data/internships.db` and `README.md` as a GitHub Actions artifact retained for 30 days. Repository administrators must ensure artifact visibility and access controls are appropriate for the repository. The optional pull request commits only `README.md`, not SQLite state.

The `allow_state_rebuild` input can delete incompatible cached state. It is a recovery mechanism, not a normal migration strategy, and should be used only after a backup. See [Automation](docs/automation.md).

### Container safeguards

The production image:

- uses Python 3.12 through the configured `uv` base image;
- installs the frozen lockfile without development dependencies;
- runs as an unprivileged user;
- mounts configuration read-only in Compose;
- persists only explicitly mounted data and README paths.

Containerization does not grant source authorization and does not make collection anonymous. Protect the Docker daemon and mounted host directories according to your environment. See [Docker](docs/docker.md).

## What to report

Relevant security reports include:

- a way to bypass or default-enable the LinkedIn authorization gate;
- credentials, cookies, environment values, or private paths exposed in output or logs;
- unexpected requests to a non-LinkedIn host or unsafe redirect behavior;
- unbounded retries, concurrency, response reads, or filesystem writes;
- malicious HTML causing code execution, arbitrary file access, or unsafe output injection;
- markdown injection that escapes the generated four-column table;
- SQL injection or unsafe dynamic SQL;
- path traversal through configurable paths or temporary-file handling;
- a failed search incorrectly mutating or closing jobs;
- migration behavior that corrupts or silently discards canonical state;
- workflow behavior that publishes `.env`, SQLite state, or sensitive artifacts unexpectedly;
- dependency or container compromise affecting the supported execution path.

## Usually not a security vulnerability

The following are generally operational or data-quality issues unless they cross a security boundary:

- a legitimate internship being missed by strict filtering;
- a public listing being categorized incorrectly;
- LinkedIn changing guest-page markup;
- an authorized request receiving HTTP 429, 403, or a challenge page;
- duplicate public listings with distinct LinkedIn job IDs;
- stale README output that is corrected by `render` and `validate`;
- collection being unavailable because permission has not been obtained.

Report these through normal issues with sanitized details.

## Secret-handling expectations

Never commit or paste into issues, tests, fixtures, screenshots, logs, or documentation:

- `.env` contents;
- credentials or access tokens for any service;
- LinkedIn cookies or browser storage;
- GitHub tokens or Actions secrets;
- private proxy URLs;
- unredacted authenticated HTML;
- production database files when they contain non-public operational context.

If a secret is committed, assume it is compromised: revoke or rotate it immediately, then remove it from current files and repository history as appropriate. Deleting it in a later commit is not sufficient.

## Dependency and release hygiene

- Keep `uv.lock` committed and use `uv sync --frozen` in CI and reproducible environments.
- Review automated dependency updates before merging.
- Run Ruff, strict mypy, offline tests, migration consistency, package builds, and container smoke tests for release changes.
- Do not publish artifacts from a dirty or unvalidated tree.
- Keep release/version references synchronized across `pyproject.toml`, `uv.lock`, package metadata, user agent, and documentation.

## Responsible disclosure

Please act in good faith, avoid accessing data that is not yours, minimize collection, and stop testing once a vulnerability is demonstrated. Do not disrupt LinkedIn, GitHub Actions, or other users. Coordinated disclosure helps protect operators and contributors while a fix is prepared.
