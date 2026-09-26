# Public opportunities API (v1)

[← Documentation hub](../../README.md) · [Website guide](website.md) · [Security policy](../../../SECURITY.md)

The unauthenticated, read-only endpoint `https://techopportunities.eu/api/v1/opportunities` lists currently open opportunities from the same canonical SQLite release as the website. `GET` retrieves data, `HEAD` retrieves headers without a body, and `OPTIONS` handles CORS preflight; `POST`, `PUT`, `PATCH`, and `DELETE` return `405 Method Not Allowed` with `Allow: GET, HEAD, OPTIONS`. It does not accept applications, verify eligibility, or guarantee availability. **Apply and verify requirements on the original listing.** No credentials, cookies, or API key are required.

Cross-origin browser requests are intentionally supported from any origin: responses set `Access-Control-Allow-Origin: *` and never allow credentials. CORS preflight allows `GET` and `HEAD`, with `If-None-Match` for conditional requests; the `ETag` and `Cache-Control` response headers are exposed to browser clients. No origin allowlist or authentication is used. No stable rate-limit contract is currently provided; clients should cache responses and avoid unnecessary requests.

## Query parameters

All parameters are optional and may appear at most once. Parameter names and exact-filter values are case-sensitive unless stated otherwise; `q` matching is case-insensitive. Unknown parameters, repeated keys, invalid values, malformed encoding, control characters, or query strings over 2048 characters return `400`. Text values must be at most 200 characters; exact filters must be nonempty and must not have leading or trailing whitespace when supplied. `q` ignores leading and trailing whitespace when matching. Parameters use URL encoding.

| Name | Meaning | Default |
|---|---|---|
| `country` | Exact country token from the listing location; semicolon-separated locations can match multiple countries | All |
| `company` | Exact company name | All |
| `category` | Exact category slug | All |
| `type` | `internship` or `new-grad` | Both |
| `q` | Case-insensitive substring search across company, title, category, industries, type, and location | All |
| `first-seen` | `24-hours`, `7-days`, or `30-days`, inclusive of both boundaries | All |
| `sort` | `company-asc`, `company-desc`, `role-asc`, `role-desc`, `location-asc`, `location-desc`, `first-seen-asc`, or `first-seen-desc` | `first-seen-desc` |
| `page` | One-based integer, 1–10000 | `1` |
| `page-size` | Integer, 1–100 (never more than 100 rows per response) | `10` |

Filters combine with AND; an exact but unmatched country, company, or category produces an empty result rather than an error. Ties in every sort use descending numeric LinkedIn job ID. Unlike the interactive website, the API does not silently clamp out-of-range pages: they return an empty `data` array with the requested page and actual count. Empty datasets have `totalPages: 0`.

First-seen windows are measured against the latest of the release's last successful collection time and its published listings' first-seen timestamps (or Unix epoch for an empty, never-collected dataset). This **snapshot-relative** reference makes identical releases reproducible; it is not a rolling wall-clock window. For live relative-to-now browsing, use the [website](website.md). First-seen estimates are approximate, not employer-supplied dates.

## Response

```http
GET /api/v1/opportunities?country=Germany&type=internship&page-size=2
```

```json
{
  "version": "v1",
  "pagination": {"page": 1, "pageSize": 2, "total": 1, "totalPages": 1},
  "data": [
    {
      "linkedinJobId": "1000000001",
      "company": "Example Labs",
      "title": "Software Engineering Intern 2027",
      "location": "Berlin, Germany",
      "link": "https://www.linkedin.com/jobs/view/1000000001",
      "category": "software-engineering",
      "industries": null,
      "employmentType": "internship",
      "startDate": null,
      "firstSeenAt": "2026-07-17T12:00:00+00:00"
    }
  ]
}
```

The example is illustrative, not live data. Successful responses use `Content-Type: application/json; charset=utf-8`. `total` is the count *after filtering, before pagination*. `totalPages` is the ceiling of `total / pageSize`. `data` contains only currently open listings. IDs are strings, not JavaScript numbers. `company`, `title`, and `location` are normalized publication text; `link` is the validated canonical HTTPS source URL. `category` is the project's technology classification; `industries` is structured source metadata or `null`. `employmentType` is `internship` or `new-grad`; `startDate` is an explicitly extracted month/season and year or `null`. `firstSeenAt` is the immutable first-seen timestamp (which can reflect an approximate source posting age). No status, closure history, search provenance, diagnostics, database information, or operational fields are returned. Never interpret a listing as an eligibility or availability guarantee.

Invalid requests return HTTP `400` with `Cache-Control: no-store`:

```json
{"version":"v1","error":{"code":"invalid_query","message":"Invalid sort"}}
```

Unavailable canonical data returns HTTP `503`, `Cache-Control: no-store`, and `{"version":"v1","error":{"code":"unavailable","message":"Directory unavailable"}}`. Errors do not contain internal paths or stack traces. `POST`, `PUT`, `PATCH`, and `DELETE` return `405 Method Not Allowed` with `Allow: GET, HEAD, OPTIONS`; no mutation method is implemented. `OPTIONS` returns `204` for supported preflights and `403` for disallowed methods or headers.

## Caching and releases

Successful responses send `Cache-Control: public, max-age=0, must-revalidate` and a strong SHA-256 `ETag` of the exact JSON response bytes. Supply `If-None-Match` (including a weak validator or comma-separated validator list) to receive `304 Not Modified` with no body, the same ETag, and Cache-Control when the representation is unchanged. Query parameter ordering or omitted defaults that produce identical output produce identical ETags. An ETag is a representation validator, not a release identifier: if two releases produce the same response they can share an ETag.

Each request pins one atomic release pointer, opens a short-lived read-only SQLite connection, and closes it without running collection, migrations, or writes. Later requests can observe a newer release; CSV/JSON downloads and website views are separate projections of the same canonical state, not independent data stores. Cross-request atomicity is not promised.

The `/api/v1/` path and the `version` field define the v1 contract. Additive changes must not change the meaning or type of existing fields; breaking changes require a new URL version. No application submission or eligibility verification is provided by this API.
