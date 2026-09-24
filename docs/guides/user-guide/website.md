# European Tech Opportunities 2027 Website Guide

[← Documentation hub](../../README.md) · [CLI reference](cli.md) · [Search registry](search-registry.md) · [Docker and deployment](../operations/docker.md) · [Security policy](../../../SECURITY.md) · [Privacy notice](../../../PRIVACY.md) · [Open the live site](https://opportunities2027.simonesiega.com/)

This is the canonical website guide for the project. The [live website](https://opportunities2027.simonesiega.com/) is the primary public interface: it exposes every currently open Internship and New Grad opportunity from canonical SQLite state, while the root README intentionally shows bounded previews for both types.

## Contents

- [Interface](#interface)
- [Search, filters, and sorting](#search-filters-and-sorting)
- [Displayed fields](#displayed-fields)
- [Public data downloads](#public-data-downloads)
- [Data interpretation](#data-interpretation)
- [Accessibility and responsive behavior](#accessibility-and-responsive-behavior)
- [Shareable directory URLs](#shareable-directory-urls)
- [Search and social metadata](#search-and-social-metadata)
- [Read-only database contract](#read-only-database-contract)
- [Local website development](#local-website-development)
- [Production runtime](#production-runtime)
- [Data refresh](#data-refresh)
- [Privacy and browser integrations](#privacy-and-browser-integrations)

## Interface

<p align="center">
  <img
    src="../../assets/sites/White_theme.webp"
    alt="European Tech Opportunities directory in light theme"
    width="49%"
  />
  <img
    src="../../assets/sites/Dark_theme.webp"
    alt="European Tech Opportunities directory in dark theme"
    width="49%"
  />
</p>

The directory provides:

- free-text search;
- company, country, technology-category, employment-type, and first-seen recency filters;
- sortable columns;
- pagination with selectable page size;
- light and dark themes stored as browser preferences;
- direct links to public source listings;
- downloadable sanitized CSV and JSON datasets;
- shareable directory URLs covering filters, sorting, page size, and pagination;
- a live result count, equal to the total open-opportunity count when no filters are active;
- the latest successful collection time.

The website supports browsing and comparison only. Applications are completed through the original employer or LinkedIn listing.

## Search, filters, and sorting

Free-text search covers:

- company;
- role title;
- technology category;
- industries;
- employment type;
- location.

Filters can be combined by:

- company;
- country;
- technology category;
- employment type, using a single-select choice of Internship or New Grad;
- first-seen recency, using Last 24 hours, Last 7 days, or Last 30 days.

Sortable columns include:

- company;
- role;
- location;
- first-seen date.

Search, filtering, sorting, page size, and pagination affect only the displayed result set. The table defaults to newest first with 10 rows per page and offers 10, 20, 30, 50, or 100 rows per page. None of this presentation state mutates lifecycle state or influences collection.

The complete directory view is encoded in the URL so its filters, sorting, page size, and current page can be bookmarked or shared. Default values are omitted to keep shared URLs concise.

A browser interaction or URL state is not lifecycle evidence, collection input, or a pipeline instruction.

## Displayed fields

| Column | Source and behavior |
|---|---|
| Company | LinkedIn detail heading, with search-card fallback |
| Role | Normalized detail title, with search-card fallback |
| Category | Deterministic internal technology classification |
| Industries | Structured LinkedIn `Industries` criterion |
| Employment type | Deterministic title classification; always `Internship` or `New Grad` |
| Location | Normalized explicit detail or search-card location |
| Start date | Explicit month or season plus year from title or narrow start-date context |
| First seen | LinkedIn relative posting-age estimate or reviewed manual posting timestamp when supplied at insertion; otherwise the first accepted observation; immutable afterward |

The website renders normalized publication fields rather than raw source HTML.

External application links are validated canonical LinkedIn HTTPS URLs whose numeric path matches the stored job identity.

## Public data downloads

Two download controls appear immediately to the left of the open-role count:

- **Download CSV** → `/open-opportunities.csv`;
- **Download JSON** → `/open-opportunities.json`.

Both files contain every currently open opportunity at generation time. Their fixed schema includes only LinkedIn job ID, company, title, location, canonical listing URL, category, industries, employment type, and start date. They exclude status, first/last-seen and update timestamps, provenance, search runs, closure evidence, diagnostics, and all other lifecycle or operational state.

The Python pipeline generates and validates both files from SQLite. CSV output neutralizes cells that spreadsheet applications could interpret as formulas. The website serves the generated files as read-only attachments and returns a generic unavailable response when a file is absent; it never creates exports from browser input.

Downloads represent the latest deployed projection, not a backup or complete historical dataset. In versioned production mode the database and exports share one atomic release-pointer cutover; each request pins a release once, but a page and a later download may straddle the cutover. Legacy fixed-path mode remains available only for migration/local development. See [Rollout and rollback](../operations/automation.md#coordinated-first-rollout-and-rollback).

## Data interpretation

`Not specified` means that optional structured metadata such as industries was absent, unsupported, or not accepted by the parser. Employment type is required for every published row.

The project does not infer structured values from arbitrary description keywords merely to fill missing cells.

The website does not claim:

- application eligibility;
- visa sponsorship;
- compensation;
- remote-work eligibility;
- application deadlines;
- continued availability beyond the source listing;
- complete coverage of European technology internships.

Verify role requirements, location, deadline, compensation, work authorization, and current availability on the original listing before applying.

For a new row, `First seen` uses LinkedIn's relative posting age when available, or a reviewed manual posting timestamp if the listing was added offline; otherwise it uses the first accepted observation. A relative-age estimate is approximate, not an exact employer-supplied date. Later observations never rewrite `first_seen_at`.

A listing may disappear from search results without being marked closed. Closure follows the explicit lifecycle rules in [Database lifecycle](../operations/database.md#closure-lifecycle).

## Accessibility and responsive behavior

Website changes should preserve:

- semantic headings, landmarks, tables, labels, and controls;
- keyboard access to interactive elements;
- visible focus behavior;
- meaningful link and button text;
- readable light and dark themes;
- responsive layouts for desktop, tablet, and mobile widths;
- usable empty, loading, and no-result states;
- stable search, filter, sort, and pagination behavior.

The empty directory is a valid state when the configured database contains no open listings.

Playwright runs axe-core WCAG 2.0, 2.1, and 2.2 A/AA checks against the normal directory, a filtered view, an empty-result view, and dark mode. These automated checks complement rather than replace keyboard and assistive-technology review.

## Shareable directory URLs

The directory recognizes these query parameters:

| Parameter | Meaning |
|---|---|
| `q` | Free-text search |
| `company` | Exact company option |
| `country` | Exact country option |
| `category` | Exact internal technology category |
| `type` | Exact normalized employment type: `internship` or `new-grad` |
| `first-seen` | Recency window based on `first_seen_at`: `24-hours`, `7-days`, or `30-days` |
| `sort` | Sort field and direction, such as `first-seen-desc`, `company-asc`, `role-desc`, or `location-asc` |
| `page-size` | Rows per page: `10`, `20`, `30`, `50`, or `100` |
| `page` | One-based result page |

For example:

```text
https://opportunities2027.simonesiega.com/?country=Germany&type=internship&first-seen=7-days&sort=first-seen-desc
```

Selecting a filter, sorting a column, changing page size, or moving between pages updates browser history, and browser back/forward navigation restores the complete earlier view. Search typing replaces the current history entry to avoid creating one entry per keystroke. Changing filters, sorting, or page size returns the view to page one. Reset removes the filter parameters and current page while preserving sorting, page size, and unrelated parameters.

Pagination renders sequential links with real `href` values. Crawlers and browsers without JavaScript can follow the unfiltered default view from page one through later result pages; client-side navigation preserves the same URLs for interactive use.

The first-seen filter uses the immutable `first_seen_at` value relative to the directory request time. For a new listing, that value is initialized from LinkedIn's relative posting age or a reviewed manual posting timestamp when supplied, and otherwise from the project's first accepted observation. Relative-age estimates are approximate, not precise employer-supplied dates.

Unsupported filter, sort, page-size, and page values are ignored or safely constrained. Query parameters are untrusted presentation input and never reach a database write path.

## Search and social metadata

The website publishes:

- self canonical URLs for the unfiltered default view (`/` and valid `/?page=2` onward), so each result page can be discovered separately;
- `noindex, follow` on search, filter, alternate sort, alternate page-size, and out-of-range page views, with `/` as their canonical URL;
- descriptive title, description, authorship, and crawler directives;
- Open Graph and large-card social metadata;
- a generated 1200 × 630 social preview image;
- `/robots.txt`, `/sitemap.xml`, and `/manifest.webmanifest` metadata routes;
- schema.org JSON-LD describing the directory as a `WebSite` and the downloadable collection as a `Dataset`, including its Europe coverage, 2027 cycle, MIT license, maintainer, daily update schedule, latest successful collection time, and CSV/JSON distributions.

The structured data describes the directory-level dataset only. It does not emit `JobPosting` records for individual source listings because the directory does not own or expose every field required for compliant job-posting markup.

`SITE_URL` must contain the canonical public origin so absolute metadata, sitemap, structured-data download, and crawler URLs are correct in production. The robots and sitemap routes render at request time from the runtime value; a build made with a local origin must not leave either route pointing to localhost after deployment.

## Read-only database contract

Website database access lives under:

```text
site/src/lib/
```

`site/src/lib/opportunities.ts` opens SQLite in read-only mode and queries currently open jobs newest-first by `first_seen_at`, with LinkedIn job ID as the stable tie-breaker.

It also reads the latest successful collection timestamp from `search_runs` for public status metadata; a later failed run cannot make the displayed data appear fresher.

The root page is dynamically rendered. Each server request resolves `OPPORTUNITIES_RELEASE_ROOT/current` once when versioned mode is enabled, then opens and closes a short-lived read-only database connection within that immutable release. An invalid/missing pointer is an error, never a fallback to a stale legacy file.

The website:

- never runs migrations;
- never inserts, updates, closes, or reopens jobs;
- never performs LinkedIn requests;
- never treats browser activity as lifecycle state;
- never exposes a mutation API;
- serves only the two fixed generated public-export filenames;
- observes a newly deployed database and exports on subsequent requests.

The Python pipeline is the sole application writer.

Authentication, user-provided content, saved application state, write endpoints, or administrative mutation interfaces require an explicit architecture and security decision before implementation.

## Local website development

A fresh local database intentionally contains no listings, and the website must render that valid empty state correctly.

For installation, database initialization, environment-file creation, and first launch, use [Installation](../getting-started/installation.md#run-the-website).

Website runtime variables are documented in [Configuration](../getting-started/configuration.md#website-settings). Components use Tailwind CSS utility classes; `site/src/app/globals.css` owns only the Tailwind import, shared design tokens, theme selectors, and base document rules.

Install the Playwright Chromium browser once, then run the complete website checks:

```bash
cd site
bunx playwright install chromium
bun run ci
```

`bun run ci` checks formatting, lint, strict TypeScript, the production build, Bun unit tests, Playwright browser behavior, and axe-core accessibility scans against a generated temporary SQLite fixture. It does not contact LinkedIn.

The complete validation path and coding expectations are documented in [Development](../development/development.md#website-validation).

## Production runtime

The root Dockerfile’s `site` target:

1. installs dependencies from the frozen Bun lockfile in a disposable Alpine build stage;
2. builds Next.js standalone output under Node.js 26;
3. copies only required standalone and static output into a Debian 13 slim runtime image;
4. installs exact reviewed Debian security revisions and removes npm from the runtime;
5. runs as UID/GID `10001:10001`;
6. reads the selected versioned SQLite release from a read-only bind mount after the coordinated rollout (legacy fixed paths until then);
7. listens on container port `3000`.

Every route receives defensive content-type, referrer, framing, cross-origin, and permissions headers. Production additionally sends a Content Security Policy and `Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`; Docker CI smoke-tests both production-only headers.

After the [coordinated first rollout](../operations/automation.md#coordinated-first-rollout-and-rollback), production sets:

```dotenv
SITE_URL=https://opportunities2027.simonesiega.com
OPPORTUNITIES_RELEASE_ROOT=/app/data
```

Compose also supplies `OPPORTUNITIES_DATABASE_PATH=/app/data/opportunities.db` and `OPPORTUNITIES_PUBLIC_EXPORT_DIR=/app/data/exports` for legacy mode. When release-root mode is enabled, these fixed paths are ignored; do not use them as a fallback if `current` is missing or invalid. `SITE_URL` defines the canonical public origin used by website metadata.

A reverse proxy such as Dokploy routes the public domain to the `site` service on container port `3000`; a fixed host port is not required.

Image targets, volumes, permissions, and routing are documented in [Docker and deployment](../operations/docker.md#dokploy-deployment).

## Data refresh

The website never collects, migrates, or synchronizes data itself.

Normal automation keeps collection/review and production deployment separate:

1. the controlled pipeline writer performs availability auditing and/or collection;
2. the resulting state and public exports are validated, then SQLite is checkpointed and published as a verified durable snapshot;
3. the owned README projection is proposed through the scoped automation pull request;
4. after review and merge, deployment-only automation restores the reviewed durable state, regenerates the public exports, and validates every projection against `main`;
5. deployment verifies checksums, publishes the database and downloads together under `data/releases/<id>`, and atomically switches `data/current` to that release; the legacy fixed files are not replaced.

In versioned mode, each new website request resolves the current release and reads it without an application rebuild, write endpoint, or in-process migration. Requests that span a cutover may see different releases.

Do not run a second local or VPS collector while GitHub Actions owns canonical state.

Workflow orchestration belongs to [Automation](../operations/automation.md), and canonical state recovery to [Database lifecycle](../operations/database.md).

## Privacy and browser integrations

The canonical production layout loads the hosted Umami analytics script from `https://cloud.umami.is/script.js`, sends analytics events to `https://gateway.umami.is`, and restricts collection to `opportunities2027.simonesiega.com`. The production Content Security Policy permits only those distinct script and connection origins. The script is rendered only when `NODE_ENV` is `production` and the configured `SITE_URL` hostname is that canonical domain, so it is absent from development, tests, and noncanonical deployments. The project-wide disclosure of infrastructure processing, analytics fields, local browser storage, external links, retention, and visitor choices is in [`PRIVACY.md`](../../../PRIVACY.md). This third-party browser integration must remain within privacy and security review.

The directory itself requires no:

- account;
- login;
- application form;
- LinkedIn credential;
- uploaded résumé;
- saved personal profile.

No internship application is submitted through this project.

Before changing analytics or adding advertising, authentication, forms, error tracking, or another browser integration:

1. document the complete data flow;
2. identify data collected from visitors;
3. review client-visible environment variables;
4. define retention, consent, and disclosure requirements;
5. update security and privacy documentation;
6. prevent exposure of database paths, secrets, or operational metadata.

Security-sensitive changes must follow [`SECURITY.md`](../../../SECURITY.md).
