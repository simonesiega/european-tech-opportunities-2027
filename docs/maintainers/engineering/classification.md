# Classification and collection evidence

[← Maintainer handbook](../README.md) · [Architecture](architecture.md) · [Search registry](search-registry.md) · [Lifecycle](../operations/database.md)

Classification is deterministic and conservative. Discovery candidates are not accepted records. `configs/categories.yml` owns keywords; `src/opportunities/pipeline/classification.py` owns decisions; transport and presentation do not classify. The [collection map](../../assets/diagram/README.md#collection-and-lifecycle) shows where these checks sit before persistence.

## Acceptance order

| Check | Acceptance boundary |
|---|---|
| Employment type | The normalized title explicitly identifies Internship or New Grad; internship terminology wins when both occur |
| Seniority | No configured senior/management exclusion in the title |
| Technology | A configured category in the title, or narrowly permitted description fallback |
| Cycle / posting date | Explicit target cycle, or no conflicting cycle with posting evidence on/after May 1, 2026 |
| Geography | Explicit European evidence after conservative normalization |

Unknown types/categories or ambiguous evidence are excluded with stable reasons. A global rule must not be weakened merely to admit one ambiguous listing.

## Cycle and date precedence

Title opportunity years have priority over description context. A conflicting title year rejects the listing; otherwise a target title year is enough. Without a title cycle, narrow opportunity-context years in the description are checked, with conflicting contextual years rejected. Without explicit cycle evidence, posting-date evidence must meet the fixed May 1, 2026 floor.

Internship graduation/eligibility years (for example, “graduating in 2027”) are not opportunity-cycle evidence. Title-explicit New Grad roles use title/contextual opportunity years as hiring-cycle evidence, so explicit 2025/2026 roles are rejected.

An explicit target-cycle listing does not require posting-age metadata. Relative posting ages are approximate: unknown or lower-bound ages such as `30+ days ago` are not fabricated into exact dates. Missing posting metadata for an existing job is not closure evidence.

Changing `OPPORTUNITIES_TARGET_CYCLE` alone does **not** roll the product forward: the posting floor, search window, public copy, fixtures and policy require a coordinated review.

## Category and geography

Configured categories are checked in stable configuration order, title before description. A description fallback is allowed only for generic technology titles; an unrelated explicit title cannot be converted into a tech role by incidental body keywords.

Location normalization recognizes supported countries, uppercase country tokens, and a conservative city fallback. Clear non-European qualifiers prevent namesake cities such as London, Ontario from becoming European evidence. `EMEA` alone is insufficient. Explicit European country evidence may support a mixed-location role; generic remote/global language alone is insufficient.

Optional industries come from structured criteria, not arbitrary description keywords. Start date requires an explicit month/season plus year in the title or a narrow start-date context. Missing optional metadata is not filled by guessing.

## Collection boundary

1. Enforce source authorization and fixed guest HTTPS endpoints.
2. Fetch bounded 25-card pages; stop on empty/repeated raw pages or configured caps, not merely on a page with no eligible titles.
3. Apply exact normalized company allowlists and title prefilters.
4. Fetch details, require independent title/company identity, normalize and classify.
5. Return isolated accepted records, warnings, and explicit unavailability evidence to persistence.

Malformed detail identity is not replaced by card identity. A majority-malformed page/search fails instead of masquerading as a successful empty result. Non-404/410 recheck transport failures fail the search, preserving its lifecycle state. Ambiguous recheck HTML is never closure evidence.

Known-job rechecks select a deterministic bounded lowest-ID subset; they are **not a rotating queue**. The separate full-state audit covers every stored job. See [Database lifecycle](../operations/database.md#daily-full-state-availability-audit) for its distinct deletion policy and [Configuration](../getting-started/configuration.md#http-policy) for retries, pacing, cookies and stop conditions.

## Change safely

Add nearby positive and negative tests for title/type, seniority, category fallback, conflicting/eligibility years, posting-floor boundaries, and namesake/ambiguous locations. Use fixed UTC clocks and synthetic HTML. Run classifier/parser tests first, then the full [Python gate and benchmarks](testing.md). No live request is necessary to develop or review a rule.
