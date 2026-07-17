<h1 align="center">
  Security Policy
</h1>

<p align="center">
  Responsible disclosure and security boundaries for European Tech Internships 2027.
</p>

<p align="center">
  <img
    src="https://img.shields.io/badge/security-private%20reporting-red"
    alt="Private vulnerability reporting"
  />
  <img
    src="https://img.shields.io/badge/supported-main%20%7C%20latest%20release-brightgreen"
    alt="Supported versions: main and latest release"
  />
  <a href="LICENSE">
    <img
      src="https://img.shields.io/github/license/simonesiega/european-tech-internships-2027?color=blue"
      alt="MIT license"
    />
  </a>
</p>

## Contents

- [Supported versions](#supported-versions)
- [Reporting a vulnerability](#reporting-a-vulnerability)
- [What to expect](#what-to-expect)
- [Security model](#security-model)
- [What to report](#what-to-report)
- [Usually not a security vulnerability](#usually-not-a-security-vulnerability)
- [Secret handling](#secret-handling)
- [Dependency and release security](#dependency-and-release-security)
- [Responsible disclosure](#responsible-disclosure)

## Supported versions

Security fixes are developed against `main` and, when practical, applied to the latest published release.

| Version | Support |
|---|---|
| `main` | Supported for unreleased fixes |
| Latest published release | Supported |
| Older releases and commits | Best effort only |

## Reporting a vulnerability

Do not open a public issue, discussion, or pull request containing vulnerability details.

Report privately through either channel:

| Channel | Contact |
|---|---|
| GitHub private vulnerability reporting | [Open a private security advisory](https://github.com/simonesiega/european-tech-internships-2027/security/advisories/new) |
| Email | [simonesiega1@gmail.com](mailto:simonesiega1@gmail.com) |

Suggested email subject:

```text
[SECURITY] Brief vulnerability summary
```

A useful report includes:

| Field | Details |
|---|---|
| Summary | Concise description of the issue |
| Impact | Affected data, command, workflow, website surface, or trust boundary |
| Reproduction | Minimal deterministic steps using synthetic or redacted data |
| Environment | OS, runtime version, project version or commit, and execution path |
| Preconditions | Required configuration, permissions, and attacker access |
| Suggested mitigation | Optional safe fix or design recommendation |

Do not send real credentials, cookies, account sessions, private HTML, unredacted environment files, production databases, or SQLite sidecars. Redact local paths, query strings, identifiers, and headers unless they are essential to understanding the issue.

## What to expect

The maintainer will make a reasonable effort to:

1. acknowledge complete reports;
2. investigate and reproduce the issue;
3. assess impact and affected versions;
4. coordinate remediation and regression tests;
5. agree on disclosure timing before publication.

Response and remediation times depend on severity, reproducibility, and maintainer availability. No fixed service-level agreement is provided.

Avoid public disclosure until a fix is available or disclosure has been coordinated.

## Security model

The supported system is deliberately narrow:

<div align="center">
<pre>
permission-gated LinkedIn guest HTML
↓
bounded local parsing and classification
↓
canonical SQLite lifecycle state
↓
read-only website + bounded README preview
</pre>
</div>

### Core security boundaries

| Surface | Security contract |
|---|---|
| Source access | Public LinkedIn guest HTML only, and only after the authorization gate |
| Authentication | No LinkedIn credentials, sessions, cookies, or account tokens |
| Transport | Fixed HTTPS endpoints, disabled redirects, bounded pacing, concurrency, retries, timeouts, and response sizes |
| Processing | Local deterministic parsing and classification; sanitized errors without response-body logging |
| Persistence | SQLite is canonical; writes use controlled repository transactions and migrations |
| Website | Read-only SQLite access; no lifecycle mutation API |
| README | Bounded generated projection written through atomic replacement |
| Automation | Offline validation CI remains separate from permission-gated collection |
| Containers | Unprivileged processes and explicit mounts do not expand source authorization |

The detailed runtime behavior is documented in the [architecture](docs/md/development/architecture.md), [configuration](docs/md/getting-started/configuration.md), [database](docs/md/operations/database.md), [automation](docs/md/operations/automation.md), and [Docker](docs/md/operations/docker.md) guides.

### Source-access boundary

The project does not require, accept, or implement:

- LinkedIn usernames or passwords;
- session cookies, browser storage, authentication headers, or account tokens;
- logged-in or browser-based collection;
- CAPTCHA solving or challenge bypass;
- private or internal LinkedIn APIs;
- proxy rotation, fingerprint evasion, or anti-bot bypasses;
- redirect-based endpoint discovery;
- collection from unrelated providers.

LinkedIn requests are blocked unless the appropriate authorization interlock is enabled.

> [!IMPORTANT]
> An authorization variable is an operator safety interlock, not permission. Operators are responsible for obtaining and retaining express authorization and for complying with applicable policies, terms, laws, and collection limits.

Do not remove, weaken, bypass, or silently default an authorization gate to true.

An upstream block or challenge is a stop condition, not a problem to evade.

### Data and website boundary

`data/internships.db` contains public listing metadata plus operational lifecycle history. It should never contain credentials, sessions, or authenticated HTML, but it is still sensitive operational state.

The website must remain a read-only projection:

- it must not run migrations or collection commands;
- it must not insert, update, close, or reopen jobs;
- it must not expose database paths, environment values, stack traces, or server configuration;
- database values must not be rendered as untrusted raw HTML;
- external listing links must remain validated public HTTPS URLs.

Changes that add authentication, forms, user-provided content, write APIs, saved application data, or administrative mutation paths expand the trust boundary and require explicit architecture and security review.

## What to report

Relevant security reports include:

- bypassing or default-enabling an authorization gate;
- credentials, cookies, environment values, private paths, or secrets exposed in output or logs;
- unexpected requests to another host or unsafe redirect behavior;
- unbounded retries, concurrency, response reads, query sizes, or filesystem writes;
- malicious source HTML causing code execution, arbitrary file access, or unsafe output injection;
- Markdown injection escaping the generated internship table;
- SQL injection or unsafe dynamic SQL;
- path traversal through configuration or temporary-file handling;
- failed searches incorrectly mutating or closing jobs;
- migrations corrupting or silently discarding canonical state;
- workflows publishing `.env`, SQLite state, credentials, or sensitive artifacts unexpectedly;
- unsafe artifact, cache, backup, or deployment access controls;
- dependency, workflow, or container compromise affecting a supported execution path;
- stored or reflected script injection in the website;
- unsafe rendering of listing fields;
- external links being rewritten to unsafe schemes or destinations;
- the website writing to SQLite or exposing local database contents;
- server failures revealing environment variables, filesystem paths, or internal configuration.

## Usually not a security vulnerability

These are normally operational or data-quality issues unless they cross a security boundary:

- a legitimate internship being missed by strict filtering;
- a public listing being classified incorrectly;
- LinkedIn changing guest-page markup;
- an authorized request receiving HTTP `429`, `403`, a timeout, or a challenge page;
- duplicate public listings with distinct LinkedIn job IDs;
- a stale README projection corrected by `render` and `validate`;
- collection remaining unavailable because authorization was not obtained;
- a listing closing later than expected under the conservative confirmation model.

Report these through normal GitHub issues using sanitized details.

## Secret handling

Never commit or paste into issues, pull requests, tests, fixtures, screenshots, logs, or documentation:

- `.env` contents;
- credentials or access tokens;
- LinkedIn cookies, sessions, or browser storage;
- GitHub tokens or Actions secrets;
- deployment SSH keys or private host configuration;
- private proxy URLs;
- authenticated or private HTML;
- production databases or SQLite sidecars.

Use synthetic values and minimal sanitized fixtures.

If a secret is committed, assume it is compromised:

1. revoke or rotate it immediately;
2. remove it from current files;
3. remove it from repository history where appropriate;
4. review logs, artifacts, caches, and deployments for additional exposure.

Deleting a secret in a later commit is not sufficient.

## Dependency and release security

- Keep `uv.lock` and `site/bun.lock` committed.
- Use frozen installs in CI and reproducible environments.
- Keep third-party GitHub Actions pinned to immutable revisions where practical.
- Review automated dependency updates before merging.
- Run the validation paths relevant to the release.
- Do not publish packages, images, or deployment artifacts from a dirty or unvalidated tree.
- Keep release and version references synchronized across project metadata, lockfiles, user agents, and documentation.
- Protect package-publishing credentials, deployment keys, workflow environments, artifacts, caches, and backups with least-privilege access.

## Responsible disclosure

Act in good faith and test only against systems and data you own or are explicitly authorized to test.

- Minimize requests and data access.
- Prefer local fixtures and synthetic state.
- Do not access, modify, retain, or disclose data belonging to other people.
- Do not degrade availability, exhaust quotas, or interfere with active workflows.
- Stop testing after the vulnerability has been demonstrated.
- Do not use a vulnerability to bypass LinkedIn or third-party access controls.
- Coordinate public disclosure with the maintainer.

These guidelines do not authorize testing against LinkedIn, GitHub, the production VPS, or any other third-party system.

Coordinated disclosure helps protect users, operators, and contributors while a fix is prepared.