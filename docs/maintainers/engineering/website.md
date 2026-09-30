# Website engineering

[← Maintainer handbook](../README.md) · [Architecture](architecture.md) · [Testing](testing.md) · [User-facing directory guide](../../users/browsing/directory.md)

The Next.js site is a read-only presentation layer. `site/src/lib/` owns server queries and pure helpers; client components own browser interaction. Keep strict TypeScript, semantic controls, Tailwind utilities, minimal global CSS, and safe external URLs. The [publication map](../../assets/diagram/README.md#website-and-publication) separates server reads, generated downloads, and browser-local state.

## Read-only database contract

`getDirectoryData` opens a short-lived `node:sqlite` connection with `readOnly: true`, selects open rows ordered by first-seen time and descending ID, and reads the latest **successful** collection timestamp. A later failed run cannot imply fresher data. React request caching shares the query between metadata and the page. Null-prototype SQLite rows become plain objects before crossing the Server Component boundary. Every listing URL must be canonical HTTPS LinkedIn and match its numeric ID.

In versioned mode, `OPPORTUNITIES_RELEASE_ROOT/current` resolves **once per server operation** to a release under `releases/`. Invalid/missing pointers fail closed rather than using legacy paths. The selected release must remain available until readers drain. Separate requests can span a cutover; a page followed by a download is not a pinned transaction.

The website never collects, classifies, migrates, generates exports, or writes SQLite. The [API](../../users/data/api.md) reuses the same query; fixed download routes serve three Python-generated files. RSS (`/feed.xml`) and Atom (`/atom.xml`) routes also reuse the read-only open-row query, serialize only the latest 50 matches, and accept exact `type`, `country`, and `category` filters. Their query parser rejects unknown or repeated keys, output is XML-escaped, and GET/HEAD responses support conditional caching; there is no subscription state or notification service. See the [user guide](../../users/browsing/directory.md#subscribe-to-new-opportunities) for URLs and filter examples. [Configuration](../getting-started/configuration.md#website-settings) owns runtime variables; [Automation](../operations/automation.md#vps-deployment) owns release publication.

## Local state contract

`local-opportunity-state.ts` owns pure parsing, pruning, toggling, and visit-baseline decisions. `use-local-opportunities.ts` owns browser storage and React synchronization. `opportunities-directory-state` version 1 contains `lastVisitAt`, optional nullable `previousVisitAt`, and `saved`, `hidden`, `applied` arrays of numeric job-ID strings. No listing metadata, notes, résumés, or application details are stored.

- Hydration loads storage only in the browser; SSR cannot depend on visitor state.
- Parsing deduplicates and prunes IDs not present in current open data. Unsupported/corrupt records reset safely.
- A visit resumes across reloads/tabs until 30 minutes without a load or local action. Older v1 records without `previousVisitAt` upgrade locally. First visits have no previous baseline.
- New means immutable first-seen time strictly after that baseline. Hidden rows never appear in All, Saved, Applied, or New.
- Local view choice is not serialized into a public URL. Public filters and sorting still apply inside each local list.
- Open tabs synchronize local changes and clearing through storage events. Each action rereads stored IDs before toggling, preserving sequential edits made elsewhere. Simultaneous writes are still last-writer-wins; local storage is not a transactional collaboration service.
- Storage failures keep consecutive actions usable in memory. Clearing site data removes the lists; there is no backend copy.

Browser lists are explicitly supported; **server-stored** applications, authentication, uploaded content, or canonical write APIs are not. See the canonical [privacy notice](../../../PRIVACY.md), and preserve these boundaries in network-level browser tests.

## URL and presentation state

| Parameter | Directory meaning |
|---|---|
| `q`, `company`, `country`, `category`, `type` | Search and exact filter selections |
| `first-seen` | `24-hours`, `7-days`, `30-days`, relative to directory request time |
| `sort` | Company, role, location, first-seen; `-asc` / `-desc` |
| `page-size` | 10, 20, 30, 50, 100 |
| `page` | Positive one-based page, constrained to displayed results |

Defaults are omitted. Search typing replaces history; other controls push history. Filter/sort/page-size changes reset to page one. Reset clears public filters and page, preserving sort, page size and unrelated parameters. Local-list changes constrain the displayed page without rewriting the public URL.

Pagination links have real `href`s. Without JavaScript, crawlers can follow the unfiltered default view through its pages. Unknown browser parameters are ignored/constrained; the API instead [rejects invalid input](../../users/data/api.md#query-parameters). Shared filtering helpers must not erase this intentional distinction or the API's snapshot-relative recency contract.

## Accessibility

Maintain labeled search/filter controls, semantic table headers, `aria-sort`, pressed states, meaningful external link text, status announcements and visible focus. Keyboard activation must preserve focus after local actions; when a row disappears, move focus to the relevant list control. Escape dismisses More actions and restores its trigger; outside focus/pointer or scrolling dismisses the floating menu. Mobile users must be able to reach actions through table scrolling without document-level overflow.

Automated axe scans cover normal, filtered, empty, dark, and open-menu states. They do not replace keyboard or assistive-technology review. [Testing](testing.md) owns commands and thresholds, not the user guide.

## Search and social metadata

The unfiltered default `/` and valid `/?page=N` views self-canonicalize and are indexable. Search/filter/alternate sort or page-size/out-of-range views use `noindex, follow` and `/` as canonical. The site emits title/description, Open Graph, a generated 1200×630 image, large-card metadata, robots, sitemap, manifest, and escaped JSON-LD.

JSON-LD describes the `WebSite` and `Dataset`, Europe, cycle 2027, MIT license, maintainer, daily update schedule, latest successful collection and both download distributions. It does not claim complete individual `JobPosting` markup. Serialization must escape `<` so hostile listing-like text cannot end the script element.

`SITE_URL` is a validated origin; production requires exact `https://techopportunities.eu`. Robots and sitemap resolve it at request time, even if built with localhost. The former hostname redirects with permanent 308 while preserving path/query; [Deployment](../operations/deployment.md#dokploy-deployment) owns routing.

## Browser integrations and security headers

Production sends CSP and HSTS in addition to content-type, referrer, framing, cross-origin and permissions headers. `next.config.ts` is executable policy; Docker smoke tests cover production headers.

Umami loads only in production with canonical `SITE_URL`: script origin `https://cloud.umami.is`, event origin `https://gateway.umami.is`. Local tests/demo use loopback and block external browser requests. Local-list IDs and visit timestamps must not enter analytics payloads. Theme storage uses the separate `opportunities-theme` key.

Before adding analytics, advertising, error tracking, authentication, forms or another browser integration, document visitor data flow, retention, consent/disclosure, and client-visible variables; review [Security](../../../SECURITY.md) and update [Privacy](../../../PRIVACY.md). Never put secrets in `NEXT_PUBLIC_*` values.
