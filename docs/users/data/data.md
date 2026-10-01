# Get the dataset

[← User guide](../README.md) · [Public API](api.md) · [Questions](../browsing/help.md)

Download all currently open opportunities — free, without an account or API key.

**[Download CSV →](https://techopportunities.eu/open-opportunities.csv)** · **[Download JSON →](https://techopportunities.eu/open-opportunities.json)** · [Metadata and hashes](https://techopportunities.eu/dataset-metadata.json)

## Choose a format

| Use case | Choose |
|---|---|
| Open listings in a spreadsheet | CSV; import as UTF-8 and keep job IDs as text |
| Analyze all listings in a script | JSON; one unpaginated array |
| Fetch a filtered page in an application | [Public API](api.md); camelCase fields and pagination |

Downloads contain every open listing at generation time, **not** your current search results or saved list. They contain no visitor data or private application history. They are current snapshots, not a complete historical dataset.

## Fields

| Download field | Meaning |
|---|---|
| `linkedin_job_id` | Numeric job ID stored as a string |
| `company`, `title`, `location` | Public listing text |
| `link` | Canonical HTTPS LinkedIn URL matching the ID |
| `category` | Technology category slug |
| `industries` | Optional source industries text |
| `employment_type` | `internship` or `new-grad` |
| `start_date` | Optional stated month/season and year |

JSON uses `null` for missing optional fields; CSV uses an empty cell. No status, observation timestamps, provenance, search history, closure evidence, diagnostics, or internal paths are included. For the public first-seen date, use the [API](api.md#response).

Synthetic example (not a live listing):

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
  }
]
```

## CSV details

The fixed header is:

```csv
linkedin_job_id,company,title,location,link,category,industries,employment_type,start_date
```

CSV uses UTF-8, LF record endings, and standard quoting for commas, quotes, and embedded newlines. Text starting with `=`, `+`, `-`, `@`, tab, or carriage return receives a leading apostrophe to prevent spreadsheet formula interpretation. This protection applies only to CSV: do not expect every cell to equal JSON text byte for byte.

JSON is UTF-8 with a final newline. Both downloads use deterministic newest-first publication order. Compare by ID when reconciling with the API, which supports different sorting. An empty JSON download is `[]`; an empty CSV still has its header.

## Check a download's integrity

Fetch [dataset-metadata.json](https://techopportunities.eu/dataset-metadata.json) alongside the files. It contains:

| Field | Meaning |
|---|---|
| `schema_version` | `v1` |
| `generated_at` | UTC generation time, not a per-listing freshness guarantee |
| `total` | Number of rows in each download |
| `internship_count`, `new_grad_count` | Counts that sum to `total` |
| `json_sha256`, `csv_sha256` | Lowercase SHA-256 of exact UTF-8 file bytes, including final newline |

Compute SHA-256 before editing or resaving the download. A mismatch can mean a publication occurred between requests: fetch the metadata and downloads again. Hashes detect mismatched bytes; they are not signatures and do not validate API responses. Missing files return `503` rather than stale fallback content.

To identify the dataset currently served by production, use the [status endpoint](api.md#check-production-freshness). It exposes the successful collection time, generation time, open count, verified JSON hash, and dataset release identifier without returning internal paths.

## Schema, examples, and reuse

The [v1 JSON Schema](https://techopportunities.eu/schemas/opportunities-v1.schema.json) is the machine-readable contract. Its root validates the JSON download; `#/$defs/csvDataset` validates decoded `{ "header": [...], "rows": [[...]] }`, `#/$defs/apiResponse` validates listing API bodies, `#/$defs/statusResponse` validates production status, and `#/$defs/metadata` validates the manifest.

[Complete synthetic examples](https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/schemas/examples) are tested against that same schema. Breaking download changes require a new schema version; existing v1 consumers should not need to infer field changes.

The project uses the [MIT License](../../../LICENSE); third-party listing content remains subject to its owners' rights and terms. Verify availability and eligibility at the original source. These files contain only the public fields listed above, not the project's internal history of listing updates or availability checks.

Maintaining exports? See [projection ownership](../../maintainers/engineering/architecture.md#public-projections) and [contract testing](../../maintainers/engineering/testing.md).
