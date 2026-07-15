# Search registry

[← README](../README.md)

The search registry defines how the pipeline discovers candidate LinkedIn listings. It does not decide which candidates are published; strict acceptance remains the classifier's responsibility.

## Layout and coverage

The loader scans YAML recursively under `configs/searches/`. The counts in this block are refreshed from the YAML files by `internships render` and checked by `internships validate`:

```text
configs/searches/
├── roles/       # 23 technology paths
├── companies/   # 12 targeted employers
└── countries/   # 33 country partitions
```

Current coverage:

| Group | Searches |
|---|---|
| Roles | artificial intelligence, cloud/DevOps/infrastructure, computer science, computer vision, cybersecurity, data engineering, data science, DevOps/SRE, embedded/firmware/robotics, firmware, hardware/semiconductor, machine learning, NLP, quantitative technology, research engineering, robotics, security engineering, semiconductor/silicon, site reliability, software development, software engineering, software technology, and software testing |
| Companies | Amazon, AMD, Apple, Arm, Bloomberg, Cisco, Google, Intel, Meta, Microsoft, NVIDIA, and Qualcomm |
| Countries | Austria, Belgium, Bulgaria, Croatia, Cyprus, Czechia, Denmark, Estonia, Finland, France, Germany, Greece, Hungary, Iceland, Ireland, Italy, Latvia, Lithuania, Luxembourg, Malta, Netherlands, Norway, Poland, Portugal, Romania, Serbia, Slovakia, Slovenia, Spain, Sweden, Switzerland, Ukraine, and the United Kingdom |

Coverage is intentionally explicit rather than mechanically exhaustive. Add a focused partition when broad ranking demonstrably misses relevant jobs; do not create hundreds of near-identical queries.

## Search YAML schema

One file defines one independent LinkedIn query:

```yaml
name: European software testing internships 2027
slug: software-testing
keywords: software test intern 2027
location: Europe
geo_id: "91000000"
company_names: []
workplace: any
date_posted: any
max_pages: 3
max_results: 75
max_rechecks: 15
enabled: true
verified_at: 2026-07-15
notes: Medium role tier covering QA and test automation.
```

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Human-readable query name, 1–200 characters. Placeholder names are rejected. |
| `slug` | kebab-case string | Stable database/configuration identity, at most 100 characters. |
| `keywords` | string | LinkedIn keyword query. Production searches include explicit internship terminology and `2027`. |
| `location` | string | LinkedIn location text, such as `Europe`, `France`, or `United Kingdom`. |
| `geo_id` | numeric string or null | Optional LinkedIn geographic ID. Europe-wide searches use `91000000`; country searches currently omit unverified IDs. |
| `company_names` | list of strings | Optional exact normalized company allowlist applied to parsed cards. Duplicates are normalized away. |
| `workplace` | `any`, `on-site`, `remote`, or `hybrid` | Optional LinkedIn workplace filter. |
| `date_posted` | `any`, `day`, `week`, or `month` | Optional LinkedIn age filter. Production searches currently use `any` so early 2027 postings are not hidden. |
| `max_pages` | integer 1–10 | Maximum 25-card pages requested. |
| `max_results` | integer 1–250 | Maximum eligible cards whose details may be considered; cannot exceed `max_pages × 25`. |
| `max_rechecks` | integer 0–250 | Maximum active known jobs absent from current eligible cards to recheck. |
| `enabled` | boolean | Disabled searches load and validate but are not selected for collection. |
| `verified_at` | ISO date or null | Date the configuration was reviewed; not proof of current endpoint availability or permission. |
| `notes` | string or null | Short scope or tuning rationale, at most 500 characters. |

Unknown fields are rejected.

## Registry validation

`load_search_registry()` performs deterministic validation before network access:

1. The configured directory must exist.
2. Every `.yml` and `.yaml` file below it must contain a mapping.
3. Every mapping must satisfy `LinkedInSearchConfig`.
4. Slugs must be unique across all subdirectories.
5. Query identities must be unique.
6. The output is sorted by slug.

A query identity combines normalized:

```text
keywords | location | geo_id | workplace | date_posted | company_names
```

This prevents different filenames from silently issuing the same request. Role filenames are also checked by the production config test against `InternshipCategory`; adding a role requires a matching enum value.

## How pagination limits work

LinkedIn guest search pages use 25-card offsets. The collector requests at most `max_pages` and selects at most `max_results` eligible cards.

Pagination stops early only when:

- a page contains no cards;
- a page has no previously unseen raw job IDs;
- the eligible-card result limit has been reached.

A page containing cards but no internship-title matches does **not** stop pagination. Raw IDs still advance repeat detection, allowing a later page to contain eligible internships.

Before detail requests, cards must pass:

- exact company allowlist matching for employer searches;
- configured internship-title terminology.

The complete classifier still runs after detail parsing. The card prefilter is a request-saving optimization, not final acceptance.

## Page/result/recheck tiers

`internships searches` displays limits as `P/R/C`: pages, results, and known-job rechecks.

| Tier | Pages | Results | Rechecks | Intended use |
|---|---:|---:|---:|---|
| High | 4 | 100 | 20–25 | Demonstrated yield or broad dominant role. |
| Medium | 3 | 75 | 15–20 | Large market or broad employer programme. |
| Specialized | 2 | 50 | 10 | Narrow role/employer or medium-low country. |
| Minimal | 1 | 25 | 5 | Country with no current observed position. |

The tiers control cost; they are not rankings of countries, employers, or internship quality.

Initial observations reviewed on July 15, 2026 were concentrated in Portugal, Poland, Spain, Germany, Ireland, Netherlands, and Slovakia. Category observations were concentrated in software, cybersecurity, data science, research, and quantitative technology. Market size informed medium starting tiers where current strict observations were absent.

These are starting limits. Reassess after several successful, authorized runs using latest found/accepted counts:

```bash
uv run internships searches
```

Do not increase a limit based on one result snapshot. LinkedIn ranking changes, repeated pages are common, and a larger broad query can cost more without improving unique strict matches.

Global page, result, and recheck overrides are documented in [Configuration](configuration.md). They replace per-file tuning and are best reserved for diagnostics.

## Group-specific guidance

### Role searches

Place role files under `configs/searches/roles/`.

- Use one coherent technology path per query.
- Avoid stuffing several unrelated specialties into one keyword string.
- Add the filename's value to `InternshipCategory`.
- Add category keywords only when they improve acceptance safely; discovery and classification are separate.
- Specialized disciplines normally start at 2 pages / 50 results / 10 rechecks.

### Company searches

Place employer files under `configs/searches/companies/`.

- Prefix the slug with `company-` even though the filename is only the employer name.
- Use broad employer discovery such as `Company intern 2027` rather than unnecessarily requiring `software`.
- Add every legitimate parsed LinkedIn company-name variant to `company_names`.
- Keep the allowlist exact after text normalization; do not use substring matching.
- Start at a medium or specialized tier unless repeated yield supports more.

Example:

```yaml
name: Amazon European technology internships 2027
slug: company-amazon
keywords: Amazon intern 2027
location: Europe
geo_id: "91000000"
company_names:
  - Amazon
  - Amazon Web Services (AWS)
workplace: any
date_posted: any
max_pages: 3
max_results: 75
max_rechecks: 15
enabled: true
verified_at: 2026-07-15
notes: Medium employer tier; targeted ranking path for a large internship programme.
```

### Country searches

Place country files under `configs/searches/countries/`.

- Prefix the slug with `country-`.
- Use the explicit country name for `location`.
- Do not invent numeric LinkedIn geo IDs; omit `geo_id` unless independently verified.
- Start unobserved low-volume countries at 1 page / 25 results / 5 rechecks.
- Increase only after repeated strict yield supports the additional requests.

## Adding a search

1. Choose `roles/`, `companies/`, or `countries/`.
2. Copy the nearest existing file with a similar scope and tier.
3. Give it a unique stable slug and query identity.
4. Include `2027` and explicit internship terminology in keywords.
5. Select the smallest defensible tier.
6. Explain the scope/tier in `notes`.
7. For a role, add the exact filename value to `InternshipCategory`.
8. Run offline validation:

```bash
uv run internships searches
uv run pytest tests/unit/test_config.py
```

9. Only with express LinkedIn permission, preview one query without persistence:

```bash
uv run internships search-test <slug>
```

10. Document authorized manual observations in the pull request without including private or authenticated data.

## Changing or disabling a search

Slugs are persisted identities. Prefer changing tunable fields without renaming a slug. A rename creates a new search identity and leaves the old database row disabled on the next synchronization.

Set `enabled: false` when a search should remain documented but not run. Deleting a YAML file also causes its synchronized database search row to become disabled; it does not delete run history, jobs, or provenance.

Search changes affect discovery only. Existing jobs close solely through the explicit lifecycle process in [Database lifecycle](database.md), never because a query was removed or returned no card.

## Responsible operation

Search files are configuration, not authorization. Do not run `search-test`, `scrape`, or live tests without express LinkedIn permission. Keep queries bounded, respect the default pacing, and treat blocks or challenge pages as a reason to stop.
