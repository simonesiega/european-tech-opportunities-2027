# European Tech Opportunities 2027 Search Registry Guide

[← Documentation](../README.md) · [CLI reference](cli.md) · [Architecture](../development/architecture.md)

The search registry controls **discovery**, not publication. Every new candidate found through LinkedIn guest search must still pass deterministic posting-date, employment-type, seniority, cycle, technology, and European-location checks before entering canonical SQLite state.

<p align="center">
  <img
    src="../../photo/internship/Amazon_example.webp"
    alt="Example public LinkedIn internship listing used as a discovery candidate"
    width="720"
  />
</p>

A search establishes provenance and defines where the pipeline looks. It never proves that a listing is eligible.

## Contents

- [Registry layout](#registry-layout)
- [Search groups](#search-groups)
- [YAML schema](#yaml-schema)
- [Validation rules](#validation-rules)
- [Query identity](#query-identity)
- [Pagination and prefiltering](#pagination-and-prefiltering)
- [Limit tiers](#limit-tiers)
- [Add a role search](#add-a-role-search)
- [Add an employer search](#add-an-employer-search)
- [Add a country search](#add-a-country-search)
- [Review a change](#review-a-change)

## Registry layout

The loader scans `configs/searches/` recursively:

```text
configs/searches/
├── roles/       # 23 technology paths
├── companies/   # 33 targeted employers
└── countries/   # 33 country partitions
```

Generated documentation may display the current count for each group. `opportunities render` refreshes owned counts, and `opportunities validate` compares them with the effective registry.

Do not edit generated counts manually.

## Search groups

| Group | Purpose |
|---|---|
| Roles | Discover coherent technology disciplines such as software engineering, cybersecurity, data, AI/ML, hardware, robotics, and quantitative technology |
| Companies | Add a targeted discovery path for selected employers |
| Countries | Partition discovery across explicitly supported European countries |

Coverage is intentionally explicit and bounded. Prefer a focused missing partition over many overlapping searches that increase request cost without meaningful discovery value.

A listing discovered by several searches keeps each provenance association but remains one canonical job identified by its numeric LinkedIn job ID.

## YAML schema

Example role search:

```yaml
name: European software testing internships and New Grad roles 2027
slug: software-testing
keywords: 'software test (intern OR "new grad" OR graduate OR "early career" OR "entry level")'
location: Europe
geo_id: "91000000"
company_names: []
workplace: any
date_posted: cycle
max_pages: 3
max_results: 75
max_rechecks: 15
enabled: true
verified_at: 2026-07-17
notes: Medium role tier covering QA and test automation.
```

| Field | Type or allowed values | Meaning |
|---|---|---|
| `name` | String, 1–200 characters | Human-readable search name; placeholders are rejected |
| `slug` | Lowercase kebab-case, at most 100 characters | Stable persisted search identity |
| `keywords` | String, 2–300 characters | LinkedIn keyword query |
| `location` | String, 1–200 characters | Europe or explicit country location text |
| `geo_id` | Numeric string or `null` | Optional independently verified LinkedIn geography ID |
| `company_names` | Up to 50 strings, each 1–200 characters | Exact normalized employer allowlist |
| `workplace` | `any`, `on-site`, `remote`, `hybrid` | Optional workplace filter |
| `date_posted` | `any`, `day`, `week`, `month`, `cycle` | Listing-age filter; `cycle` dynamically covers every posting since May 1, 2026 |
| `max_pages` | Integer, 1–10 | Maximum number of 25-card result pages |
| `max_results` | Integer, 1–250 | Maximum eligible detail candidates; no greater than pages × 25 |
| `max_rechecks` | Integer, 0–250 | Absent known jobs that may receive bounded detail rechecks |
| `enabled` | Boolean | Whether normal collection selects the search |
| `verified_at` | ISO date or `null` | Date the configuration itself was reviewed |
| `notes` | String or `null`, at most 500 characters | Scope, tier, and tuning rationale |

Unknown fields are rejected.

`verified_at` documents configuration review. It does not prove that LinkedIn currently returns results, that the search remains productive, or that collection is authorized.

## Validation rules

Before network access, the registry loader requires:

1. an existing search directory;
2. mapping-shaped YAML files;
3. valid `LinkedInSearchConfig` fields;
4. globally unique slugs;
5. globally unique effective query identities;
6. deterministic slug ordering;
7. valid role-category mappings where required;
8. result limits within page capacity.

Conventions:

- filenames and slugs remain stable lowercase kebab-case;
- role filenames map to `OpportunityCategory`;
- every query requests both internship and New Grad terminology without requiring a year;
- every production search uses the dynamic `cycle` posting filter, covering May 1, 2026 through collection time;
- employer searches use exact normalized `company_names`;
- country searches use explicit country location text;
- numeric geography IDs are never invented;
- `notes` explain scope and tuning without unsupported coverage claims.

Validate locally:

```bash
uv run opportunities searches
uv run pytest tests/unit/test_config.py
```

Contribution requirements are defined in [`CONTRIBUTING.md`](../../../CONTRIBUTING.md#adding-or-changing-a-search).

## Query identity

An effective query identity combines normalized values of:

```text
keywords
location
geo_id
workplace
date_posted
company_names
```

Two files cannot issue the same effective request under different filenames or slugs.

The slug is persisted as the search identity. Prefer changing tunable fields without renaming an existing slug.

Disabling or deleting a search:

- preserves its historical run records;
- prevents future selection;
- does not directly close associated jobs.

Job closure depends on repeated explicit detail-page unavailability across every active association, not registry deletion.

## Pagination and prefiltering

LinkedIn guest search uses 25-card offsets.

Collection stops when:

- the page is empty;
- the page contains no unseen raw job IDs;
- the eligible-result limit is reached;
- the page limit is reached.

A page containing cards but no title-explicit internship or New Grad matches does **not** stop pagination.

Before detail requests, search cards pass two low-cost checks:

1. exact normalized employer allowlist matching, when configured;
2. explicit internship or New Grad terminology in the title.

These checks reduce unnecessary detail requests. Final acceptance still occurs only after detail parsing, normalization, and deterministic classification.

## Limit tiers

`opportunities searches` displays limits as:

```text
P/R/C
```

Where:

- `P` = maximum pages;
- `R` = maximum eligible detail results;
- `C` = maximum absent known-job rechecks.

| Tier | Pages | Results | Rechecks | Intended use |
|---|---:|---:|---:|---|
| High | 4 | 100 | 20–25 | Repeatedly demonstrated yield |
| Medium | 3 | 75 | 15–20 | Broad market or employer programme |
| Specialized | 2 | 50 | 10 | Narrow role or employer |
| Minimal | 1 | 25 | 5 | New, unobserved, or low-volume partition |

Limits control request cost, not listing quality.

Start with the smallest defensible tier. Tune only after several successful authorized runs; do not raise all searches because of one low-yield snapshot.

Global diagnostic overrides belong to [Configuration](../getting-started/configuration.md#search-limit-overrides).

## Add a role search

1. Create `configs/searches/roles/<slug>.yml`.
2. Choose one coherent technology discipline.
3. Include the standard internship/New Grad Boolean terms without a year restriction.
4. Use the verified Europe geography configuration for Europe-wide discovery.
5. Start with the smallest defensible tier.
6. Explain role scope and tuning in `notes`.
7. Add the filename value to `OpportunityCategory` when introducing a category.
8. Add or update registry and classifier tests.

Example path:

```text
configs/searches/roles/software-testing.yml
```

Do not create several near-identical searches only to broaden wording. Prefer one focused query plus classifier improvements supported by tests.

## Add an employer search

Place employer searches under:

```text
configs/searches/companies/
```

Requirements:

- prefix the slug with `company-`;
- use broad but explicit keywords that include both internship and New Grad terms;
- omit `2027` so current yearless vacancies are discoverable, and use `date_posted: cycle` to cover the complete May 1 publication window;
- list legitimate LinkedIn employer-name variants in `company_names`;
- retain exact matching after normalization;
- do not use substring matching;
- start conservatively and increase limits only after repeated evidence.

Example:

```yaml
name: Amazon internships and New Grad roles 2027
slug: company-amazon
keywords: 'Amazon (intern OR "new grad" OR graduate OR "early career" OR "entry level")'
location: Europe
geo_id: "91000000"
company_names:
  - Amazon
  - Amazon Web Services
workplace: any
date_posted: cycle
max_pages: 2
max_results: 50
max_rechecks: 10
enabled: true
verified_at: 2026-07-17
notes: Targeted employer discovery with exact normalized company matching.
```

The allowlist restricts discovery. It does not bypass classification. Listings must be discovered from search results and pass every publication check.

## Add a country search

Place country searches under:

```text
configs/searches/countries/
```

Requirements:

- prefix the slug with `country-`;
- use the explicit country name as `location`;
- omit `geo_id` unless independently verified;
- include both internship and New Grad terminology without a year restriction;
- start unobserved or low-volume countries at the minimal tier;
- avoid claiming complete national coverage.

Example:

```yaml
name: Portugal technology internships and New Grad roles 2027
slug: country-portugal
keywords: 'software (intern OR "new grad" OR graduate OR "early career" OR "entry level")'
location: Portugal
geo_id: null
company_names: []
workplace: any
date_posted: cycle
max_pages: 1
max_results: 25
max_rechecks: 5
enabled: true
verified_at: 2026-07-17
notes: Initial low-volume country partition.
```

Country candidates remain subject to the same European-location and technology-role classifier rules.

## Review a change

Run:

```bash
uv run opportunities searches
uv run pytest tests/unit/test_config.py
git diff -- configs/searches/
```

Only with express authorization, preview one search without persistence:

```bash
uv run opportunities search-test <slug>
```

Confirm that the slug and query identity are unique, geography and employer values are justified, limits use the smallest defensible tier, the review date is accurate, and relevant tests pass.

Do not require reviewers or CI to contact LinkedIn. Search files do not grant authorization, and an access block or challenge is a stop condition.
