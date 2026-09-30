# Use the public API

[← User guide](../README.md) · [Complete downloads](data.md) · [Get help](../browsing/help.md)

Query open opportunities at **[`https://techopportunities.eu/api/v1/opportunities`](https://techopportunities.eu/api/v1/opportunities)**. No account or API key is required. This is a read-only listing service; it cannot save roles or submit applications.

## Make a request

Get internships in Germany, newest first:

```bash
curl --get 'https://techopportunities.eu/api/v1/opportunities' \
  --data-urlencode 'country=Germany' \
  --data-urlencode 'type=internship' \
  --data-urlencode 'page-size=20'
```

Browser JavaScript:

```javascript
const query = new URLSearchParams({ country: "Germany", type: "internship" });
const response = await fetch(
  `https://techopportunities.eu/api/v1/opportunities?${query}`,
);
if (!response.ok) {
  throw new Error(`Directory returned ${response.status}`);
}
const { data, pagination } = await response.json();
```

Prefer the [complete JSON download](data.md) for bulk analysis instead of repeatedly fetching every page.

## Response

Synthetic example, shortened to one role:

```json
{
  "version": "v1",
  "pagination": {
    "page": 1,
    "pageSize": 10,
    "total": 1,
    "totalPages": 1
  },
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
    }
  ]
}
```

The API uses **camelCase**, unlike the snake_case downloads. IDs are strings. `industries` and `startDate` can be `null`. `firstSeenAt` is immutable and may reflect approximate source posting age. It is UTC RFC 3339 with `T`, exactly six fractional digits, and `+00:00`; SQLite's internal timestamp representation is not part of this contract.

`total` counts matches **before pagination**. An empty result has `totalPages: 0`. An out-of-range page returns `data: []` with the requested page and actual filtered total. No private lifecycle or operational fields are returned.

## Query parameters

All parameters are optional and may appear only once.

| Parameter | Values | Default |
|---|---|---|
| `q` | Case-insensitive substring across company, title, category, industries, type, location | All |
| `country` | Exact country token; multi-location roles may match several countries | All |
| `company` | Exact company name | All |
| `category` | Exact category slug | All |
| `type` | `internship`, `new-grad` | Both |
| `first-seen` | `24-hours`, `7-days`, `30-days` | All |
| `sort` | `company-asc/desc`, `role-asc/desc`, `location-asc/desc`, `first-seen-asc/desc` | `first-seen-desc` |
| `page` | Integer 1–10000 | `1` |
| `page-size` | Integer 1–100 | `10` |

Use a complete sort value such as `company-asc`, not the abbreviated `asc/desc` notation above. Filters combine with AND. Exact filters and parameter names are case-sensitive. A valid but unmatched filter returns an empty result, not an error. Sort ties use descending numeric LinkedIn ID.

Text values are limited to 200 characters. Exact filters must be nonempty and have no surrounding whitespace; `q` ignores surrounding whitespace. URL-encode values. Unknown/repeated keys, invalid values or encoding, control characters, and query strings longer than 2048 characters return `400`.

**Recency is snapshot-relative**, measured against the later of the latest successful collection and the newest first-seen timestamp in that release (Unix epoch for an empty, never-collected dataset). Both window boundaries are inclusive. This makes unchanged data reproducible; use the [website](../browsing/directory.md) for recency relative to the directory request time.

## Cache responses responsibly

Successful responses have `Content-Type: application/json; charset=utf-8`, `Cache-Control: public, max-age=0, must-revalidate`, and a strong SHA-256 `ETag` of the exact response bytes. Send it in `If-None-Match` on your next request to receive `304 Not Modified` without a body when unchanged. Weak and comma-separated validators are accepted. Equivalent queries producing identical output have identical ETags.

An ETag identifies a response, **not** a complete release. Separate requests, including pages, may cross a publication. No stable rate-limit contract is promised; cache responses and avoid aggressive polling.

## Methods, errors, and cross-origin use

`GET` returns JSON. `HEAD` returns the same headers without a body. `OPTIONS` supports preflight. Mutation methods (`POST`, `PUT`, `PATCH`, `DELETE`) return `405` with `Allow: GET, HEAD, OPTIONS`.

Cross-origin GET/HEAD is allowed with `Access-Control-Allow-Origin: *`, without credentials. Preflight permits `If-None-Match`; `ETag` and `Cache-Control` are exposed. Supported preflight returns `204`; disallowed methods/headers return `403`.

Errors use `Cache-Control: no-store`:

```json
{
  "version": "v1",
  "error": {
    "code": "invalid_query",
    "message": "Invalid sort"
  }
}
```

Invalid input returns `400`. Unavailable data returns `503` with code `unavailable` and message `Directory unavailable`. Do not interpret a failure as an empty dataset. Errors expose no internal paths or stack traces. `HEAD`, `OPTIONS`, `304`, and `405` have no JSON body.

## Compatibility

[JSON Schema](https://techopportunities.eu/schemas/opportunities-v1.schema.json) definition `#/$defs/apiResponse` validates success and error bodies. [Full synthetic example](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/schemas/examples/api-opportunities-v1.json).

The URL `/api/v1/` and response `version` define this contract. Breaking API changes require a new URL version. The API reads canonical data, never browser lists. For implementation and security boundaries, see [website engineering](../../maintainers/engineering/website.md).
