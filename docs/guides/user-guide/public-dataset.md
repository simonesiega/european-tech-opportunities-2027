# Public dataset and API contracts (v1)

[← Documentation hub](../../README.md) · [Website guide](website.md) · [Security policy](../../../SECURITY.md)

The canonical machine-readable contract is served at [`/schemas/opportunities-v1.schema.json`](https://techopportunities.eu/schemas/opportunities-v1.schema.json), which is also its JSON Schema `$id`. The [repository schema](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/schemas/opportunities-v1.schema.json) is the source file copied verbatim into the read-only site image. It describes three read-only representations of the **same currently open listing facts**, plus their dataset metadata. The root validates the JSON download; named definitions validate parsed CSV and API response bodies. These projections are not lifecycle backups or inputs to collection or classification.

| Representation | Location | Schema entry point | Shape |
|---|---|---|---|
| JSON download | [`/open-opportunities.json`](https://techopportunities.eu/open-opportunities.json) | Root (`#/$defs/jsonDataset`) | Unpaginated snake_case array |
| CSV download | [`/open-opportunities.csv`](https://techopportunities.eu/open-opportunities.csv) | `#/$defs/csvDataset` | Parsed `{ "header": [...], "rows": [[...], ...] }` |
| API | [`/api/v1/opportunities`](https://techopportunities.eu/api/v1/opportunities) | `#/$defs/apiResponse` | Paginated success or JSON error object |
| Dataset metadata | [`/dataset-metadata.json`](https://techopportunities.eu/dataset-metadata.json) | `#/$defs/metadata` | Version, UTC generation time, counts, and download hashes |

The three **synthetic, non-live examples** below are also maintained as separate, test-validated files under `schemas/examples/`. The JSON Schema reuses common field definitions rather than maintaining three unrelated sets of constraints. Schema validation covers structures and field types; the pipeline additionally validates SQLite provenance, sanitized output, and exact file content.

## JSON download

[Complete example file](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/schemas/examples/open-opportunities-v1.json):

```json
[
  {
    "linkedin_job_id": "1000000001",
    "company": "Example Labs",
    "title": "Software Engineering Intern 2027",
    "location": "Berlin, Germany",
    "link": "https://www.linkedin.com/jobs/view/1000000001",
    "category": "software-engineering",
    "industries": "Software Development",
    "employment_type": "internship",
    "start_date": "June 2027"
  },
  {
    "linkedin_job_id": "1000000002",
    "company": "Example Data",
    "title": "Graduate Data Engineer 2027",
    "location": "Paris, France",
    "link": "https://www.linkedin.com/jobs/view/1000000002",
    "category": "data-engineering",
    "industries": null,
    "employment_type": "new-grad",
    "start_date": null
  }
]
```

The download contains every open listing at generation time, in deterministic publication order. IDs are decimal **strings**, not JavaScript numbers; `link` is a canonical public HTTPS LinkedIn listing URL. `employment_type` is `internship` or `new-grad`. `industries` and `start_date` may be `null`; the other fields are required strings. No status, first-seen timestamp, provenance, search history, database path, or diagnostics are exported. An empty dataset is `[]`. Output is UTF-8 with a final newline.

## CSV download

[Complete example file](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/schemas/examples/open-opportunities-v1.csv) containing the **same two rows in the same order**:

```csv
linkedin_job_id,company,title,location,link,category,industries,employment_type,start_date
1000000001,Example Labs,Software Engineering Intern 2027,"Berlin, Germany",https://www.linkedin.com/jobs/view/1000000001,software-engineering,Software Development,internship,June 2027
1000000002,Example Data,Graduate Data Engineer 2027,"Paris, France",https://www.linkedin.com/jobs/view/1000000002,data-engineering,,new-grad,
```

The header is always present, even for an empty dataset. CSV uses UTF-8, LF record endings, and standard CSV quoting for commas, quotes, and embedded newlines. Optional JSON `null` values become empty cells. Text cells starting with `=`, `+`, `-`, `@`, a tab, or a carriage return receive a leading apostrophe **in CSV only** to prevent spreadsheet formula interpretation. Do not assume that every CSV cell is a byte-for-byte copy of the JSON text.

JSON Schema cannot parse CSV bytes: `#/$defs/csvDataset` validates the **decoded representation** `{ "header": [column names], "rows": [[cell strings], ...] }` after a strict CSV parse. It requires the fixed header, nine cells per row, numeric ID, canonical URL shape, and employment type. Pipeline validation also compares exact bytes against the canonical SQLite projection, including CSV quoting and formula neutralization.

## API response

The unauthenticated, read-only API shares the listing facts but has a **different representation**: camelCase names, `firstSeenAt`, and pagination. [Complete example file](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/schemas/examples/api-opportunities-v1.json):

```json
{
  "version": "v1",
  "pagination": {"page": 1, "pageSize": 10, "total": 2, "totalPages": 1},
  "data": [
    {
      "linkedinJobId": "1000000001",
      "company": "Example Labs",
      "title": "Software Engineering Intern 2027",
      "location": "Berlin, Germany",
      "link": "https://www.linkedin.com/jobs/view/1000000001",
      "category": "software-engineering",
      "industries": "Software Development",
      "employmentType": "internship",
      "startDate": "June 2027",
      "firstSeenAt": "2026-07-17T12:00:00.000000+00:00"
    },
    {
      "linkedinJobId": "1000000002",
      "company": "Example Data",
      "title": "Graduate Data Engineer 2027",
      "location": "Paris, France",
      "link": "https://www.linkedin.com/jobs/view/1000000002",
      "category": "data-engineering",
      "industries": null,
      "employmentType": "new-grad",
      "startDate": null,
      "firstSeenAt": "2026-07-16T12:00:00.000000+00:00"
    }
  ]
}
```

The example is illustrative, not live data. API `firstSeenAt` is always normalized to a UTC RFC 3339 timestamp with `T`, exactly six fractional digits, and an explicit `+00:00` offset; source microseconds are preserved (missing digits are zero-padded). SQLite's internal space-separated format is never part of the API contract. The timestamp is immutable after the first accepted observation and may reflect an approximate source posting age. `total` is the count **after filtering, before pagination**; `totalPages` is the ceiling of `total / pageSize`. An empty dataset has `totalPages: 0`. An out-of-range page has `data: []` with the requested page and actual filtered total. IDs remain strings. API sorting can differ from download ordering; compare by ID when reconciling representations.

### Query parameters

All parameters are optional and may appear at most once. Parameter names and exact-filter values are case-sensitive unless stated otherwise; `q` matching is case-insensitive. Unknown or repeated keys, invalid values, malformed encoding, control characters, or query strings over 2048 characters return `400`. Text values are at most 200 characters; supplied exact filters must be nonempty and have no leading or trailing whitespace. `q` ignores leading and trailing whitespace for matching. Parameters use URL encoding.

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

Filters combine with AND; a valid but unmatched country, company, or category produces an empty result rather than an error. Ties in every sort use descending numeric LinkedIn ID. First-seen windows are measured against the latest of the release's last successful collection time and its published listings' first-seen timestamps (or Unix epoch for an empty, never-collected dataset). This **snapshot-relative** reference makes identical releases reproducible; it is not a rolling wall-clock window. For live relative-to-now browsing, use the [website](website.md). No application submission, eligibility verification, or current availability guarantee is provided; check the original listing.

### Errors, methods, and caching

`GET` returns JSON; `HEAD` returns the same headers without a body. `OPTIONS` handles CORS preflight. `POST`, `PUT`, `PATCH`, and `DELETE` return `405 Method Not Allowed` with `Allow: GET, HEAD, OPTIONS`. No mutation method is implemented. Cross-origin browser GET/HEAD requests are allowed from any origin with `Access-Control-Allow-Origin: *` and no credentials; `If-None-Match` is permitted in preflight, and `ETag` and `Cache-Control` are exposed. No stable rate-limit contract is provided; clients should cache responses.

Invalid queries return `400`, `Cache-Control: no-store`, and a JSON error body:

```json
{"version":"v1","error":{"code":"invalid_query","message":"Invalid sort"}}
```

Unavailable canonical data returns `503`, `Cache-Control: no-store`, and:

```json
{"version":"v1","error":{"code":"unavailable","message":"Directory unavailable"}}
```

Errors contain no internal paths or stack traces. `#/$defs/apiResponse` accepts either a successful body or one of these error shapes. `HEAD`, `OPTIONS`, `304`, and `405` have no JSON body to validate. Supported preflights return `204`; disallowed methods or headers return `403`.

Successful responses use `Content-Type: application/json; charset=utf-8`, `Cache-Control: public, max-age=0, must-revalidate`, and a strong SHA-256 `ETag` of the **exact API JSON response bytes**. Supply `If-None-Match` (also accepting weak or comma-separated validators) to receive `304 Not Modified` without a body when unchanged. Equivalent query parameter orders or omitted defaults that produce identical output produce identical ETags. The ETag is a representation validator, **not** a release identifier.

Each API request pins the current atomic release pointer once, opens a short-lived read-only SQLite connection, then closes it; it never reads downloads as a source of truth or runs collection, migrations, or writes. Later requests may observe a newer release. The `/api/v1/` path and `version` field define the API's v1 contract; breaking changes require a new URL version.

## Metadata and integrity

`dataset-metadata.json` is generated by the Python export renderer alongside both downloads; it is **not** an API response or a fourth opportunity listing format. The [synthetic metadata example](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/schemas/examples/dataset-metadata-v1.json) contains counts and exact-byte hashes for the JSON and CSV examples above.

| Field | Meaning |
|---|---|
| `schema_version` | `v1`, the download contract version |
| `generated_at` | UTC ISO-8601 generation timestamp |
| `total` | Number of open rows in each download |
| `internship_count`, `new_grad_count` | Row counts by employment type, summing to `total` |
| `json_sha256`, `csv_sha256` | Lowercase SHA-256 of the **exact file bytes** (including final newline) |

The hashes are integrity checks, not signatures, and do not cover API responses. The JSON Schema checks metadata field types and shapes; the renderer and validator additionally enforce `internship_count + new_grad_count == total`, exact-byte hashes, and consistency with SQLite. Separate downloads across a production release-pointer cutover may span revisions; retry if the hashes do not match. Versioned deployment publishes all three files with SQLite in one release directory. Missing files fail closed instead of serving a stale export.

## Validation and compatibility

`uv run opportunities render` (or `export-public` for downloads only) generates the files from canonical SQLite. `uv run opportunities validate` checks the JSON download, parsed CSV, and metadata against the single schema, compares the downloads to SQLite, and checks counts and byte-level hashes. Python CI runs these checks against a synthetic migrated database. Site CI validates API success and error bodies and JSON downloads against the same schema using synthetic data. All four example files (JSON, CSV, API, and metadata) are checked against the schema and one another in offline tests. Never regenerate and commit README regions from an empty local database, or commit runtime exports.

Update the schema and focused acceptance/rejection tests together when publication fields change. A breaking change to downloads requires a new schema version; a breaking API change requires a new `/api/vN/` endpoint. Preserve v1 for existing consumers unless explicitly planning that migration.
