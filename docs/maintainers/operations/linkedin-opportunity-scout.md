# Research overlooked LinkedIn opportunities

[← Maintainer handbook](../README.md) · [Prompt templates](linkedin-opportunity-scout-prompts.md) · [Classification](../engineering/classification.md) · [Public API](../../users/data/api.md) · [Manual addition](automation.md#manual-job-addition) · [Security](../../../SECURITY.md)

Use the shared `linkedin-opportunity-scout` Codex skill to research public LinkedIn internships and New Grad roles, compare them with every published open listing, and save evidence for human review. Research remains read-only with respect to canonical state. No LLM service, API key, scheduler, or background agent is required.

## Contents

- [Invoke the skill](#invoke-the-skill)
- [Current context map](#current-context-map)
- [Research and local artifacts](#research-and-local-artifacts)
- [Prepare and submit approved jobs](#prepare-and-submit-approved-jobs)
- [Troubleshooting and maintenance](#troubleshooting-and-maintenance)

## Invoke the skill

Open this checkout in a Codex environment with repository-local skill discovery and enter:

```text
$linkedin-opportunity-scout
Research overlooked European technology opportunities using the current rules.
Write a report and stop before submitting anything.
```

The tracked entry point is [SKILL.md](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.agents/skills/linkedin-opportunity-scout/SKILL.md). Codex discovers its `name` and `description` metadata in `.agents/skills/linkedin-opportunity-scout/`. If the current session predates the skill, restart or refresh skill discovery. If the environment lacks that facility, explicitly ask it to read that entry point; this is a fallback, not proof of native invocation support.

For reusable research, review, preparation, submission, and follow-up requests, use the [scout prompt templates](linkedin-opportunity-scout-prompts.md). Replace their placeholders and send only the prompt for the action you intend to authorize.

The skill uses the active session's available research tools. A local synthetic test cannot establish that compliant LinkedIn browsing is available in another Codex environment. Missing browsing or GitHub tools do not justify installing a scraper or requesting source credentials.

## Current context map

Read these current owners each invocation; do not copy their rules into prompts or helpers.

| Question | Authoritative files |
|---|---|
| Permissions and source access | Root `AGENTS.md`, `SECURITY.md`; [authorization and HTTP settings](../getting-started/configuration.md#http-policy) |
| Accepted types, categories, and exclusions | `configs/categories.yml`, `src/opportunities/config/rules.py`, `models/enums.py`, `pipeline/classification.py`; [classification guide](../engineering/classification.md) |
| Cycle and posting evidence | `config/policy.py`, `config/settings.py`, `scrapers/linkedin.py`, `pipeline/classification.py` under `src/opportunities/` |
| European evidence and title normalization | `normalization/location.py`, `normalization/geography.json`, `normalization/title.py` under `src/opportunities/` |
| Identity, normalized records, and duplicates | `utils/url.py`, `models/raw.py`, `models/job.py` under `src/opportunities/`; numeric LinkedIn IDs, never fuzzy title matching |
| Existing coverage and bounded discovery | `configs/searches/`, `config/search_registry.py`, `models/search.py`, `scrapers/linkedin.py`, `scrapers/http.py`, `pipeline/runner.py`; [registry guide](../engineering/search-registry.md) |
| Public collection and freshness | [API](../../users/data/api.md), [downloads](../../users/data/data.md), `schemas/opportunities-v1.schema.json`, `site/src/lib/opportunity-api.ts`, `opportunity-status.ts`, `opportunity-status-data.ts` |
| Manual validation and historical state | `src/opportunities/manual_jobs.py`, `cli/app.py`, `database/repository.py`; [CLI](cli.md#add-jobs), [lifecycle](database.md#manual-job-insertion) |
| Publication and review barriers | `.github/workflows/add-job.yml`, `reusable-process-state.yml`, `reusable-readme-pr.yml`; [automation](automation.md), [deployment](deployment.md) |

Paths shortened within the Python package are relative to `src/opportunities/`. The helper defaults to checked-in categories and `Settings().target_cycle`, without loading `.env` or operator settings. The command exposes no rule or cycle override. Changing the cycle setting alone is not a supported product rollover.

## Research and local artifacts

Choose a bounded research budget and several coverage-informed queries rather than replaying every configured search. Investigate unlisted employers, specialized disciplines, individual cities/countries, placements, alternative titles, and narrower terms. Suggestions to change registry coverage belong in the report; research does not edit production search YAML.

Reports and prepared batches live in the Git-ignored directory:

```text
reports/linkedin-opportunity-scout/YYYY-MM-DDTHHMMSSZ/
  dataset.json
  research.json
  report.md
  batch-01.json
```

Use UTC and a suffix on collision. The helper refuses to overwrite existing outputs. Keep earlier reports when refreshing evidence. These artifacts are not database snapshots or production data. Retain only minimal public text and short evidence quotations, not raw HTML, cookies, private data, or credentials. Git-ignore is not encryption.

### Retrieve all existing open IDs

Read the [API contract](../../users/data/api.md) before retrieval. From the repository root:

```bash
uv run python scripts/research/scout.py dataset \
  --directory reports/linkedin-opportunity-scout/2026-10-20T120000Z
```

The helper requests `https://techopportunities.eu/api/v1/status`, then every unfiltered `https://techopportunities.eu/api/v1/opportunities` page with `page-size=100` and an explicit stable sort, then status again. It validates the shared schema, page numbers, totals, exact expected lengths, unique IDs, matching canonical URLs, and unchanged status. It also requires the complete API ID set to equal a full public JSON export whose exact bytes match the status hash; status brackets alone could miss a transient publication followed by rollback. Empty datasets still require a valid empty page. It saves no partial result. Requests are serial, unauthenticated, timeout-bounded, without redirects or ambient proxies; response sizes and the 100-page research budget are bounded. There are no automatic retries.

A page ETag identifies only that response. Status brackets identify the deployed release, hash, and freshness; they are not a server-side multi-request lock. A release change, malformed response, incomplete page, duplicate identity, or API/export mismatch fails the read. Wait and retry at most once on publication drift. Never poll to overcome denials.

The approved complete public fallback is:

```bash
uv run python scripts/research/scout.py dataset --export \
  --directory reports/linkedin-opportunity-scout/2026-10-20T120000Z
```

This requests the full `/open-opportunities.json`, verifies its exact SHA-256 against status, validates the download schema, IDs and count, and requires unchanged status before/after. Use it for unavailable/incomplete API pagination, the research page limit, or fixed-path mode (`release: null`), where API pages cannot be pinned reliably. It is bounded to 64 MiB. Status itself verifies metadata and export integrity; no protected snapshot is needed.

If both fail, use `report --without-dataset`. Existing-count and novelty claims then remain unknown. Never treat errors as empty state. The public collection contains only open listings: absence does not prove an ID is absent from canonical history. Closed canonical rows can still cause an atomic manual batch rejection.

### Verify source evidence

Follow [Security](../../../SECURITY.md#collection-boundary). Public search-index discovery can guide research, but snippets do not verify a listing. LinkedIn alone supplies listing publication evidence. Other recruitment platforms are not eligible sources.

The policy prohibits browser-based collection, even if a session exposes a browser tool. Use public research tools only if their access mode is known to comply; do not assume a generic fetch tool disables redirects, cookies, or authentication. If automated requests are needed, use approved project interfaces with express source permission and their authorization interlock. Do not enable source access merely to finish a task. An approved `search-test` preview needs disposable configuration and permission; never use `scrape` for read-only research.

Denials, challenges, rate limits, and disallowed redirects stop source requests; do not switch tools to evade them. A numeric public-listing 301 is inconclusive, never proof of availability or closure; ignore its destination/body and do not retry it. Record unavailable detail access honestly. A zero-finding or conditional-only report remains useful.

### Verify availability

Record an `availability` object for every observation. Its `basis` and nonempty `evidence` establish an availability state only when `directly_verified` is true. Include the exact listing reference, a short quotation or HTTP observation, and verification time. These are session attestations, not authenticated machine proof.

| Basis | Required source evidence | Availability |
|---|---|---|
| `accepting_applications` | An affirmative, current LinkedIn statement that this exact listing is accepting applications | Open |
| `closure_alert` | A scoped LinkedIn closure alert recognized by the existing pure detector | Closed |
| `http_404` / `http_410` | That status returned directly by an approved request for the exact listing | Closed |
| `unknown` or missing evidence | Inaccessible, ambiguous, unverified, or insufficient evidence | Unknown |

A narrow contradiction guard makes an `accepting_applications` claim unknown and review-required if its quotation explicitly says applications are not or no longer being accepted, or records HTTP 404/410. It does not establish actual closure from unscoped words, and a verified positive observation cannot silently override that contradictory verified quotation. Unverified snippets still cannot override verified details. This guard is not general language understanding or evidence authentication.

A recognizable detail page, Apply button, search card, absence of a closure warning, or old application wording in a description does not prove current acceptance. No automatic open-status detector is provided. If no affirmative current acceptance evidence is available, retain unknown availability: the candidate remains conditional and cannot be batched, even when its employment-policy checks pass.

For public HTML already obtained with permission through approved interfaces, `src/opportunities/scout.py::availability_from_public_html` calls the existing pure `has_closed_application_notice`. A scoped alert returns closure evidence; other nonblocked HTML remains unknown. Source challenges propagate the existing stop error, never an availability result. It makes no requests and never infers open status. Do not retain the HTML in the ledger. The production availability audit, network policy, and canonical lifecycle rules are unchanged; never invoke that audit during research.

If verified open and closed observations disagree, retain both and require review. Neither last-observation ordering nor a positive statement overrides known contradictory evidence. An unverified snippet cannot override a verified detail observation.

### Record and assess candidates

Save a `research.json` ledger. This synthetic example shows a complete candidate; it is not a real discovery:

```json
{
  "executed_at": "2026-10-20T12:00:00+00:00",
  "strategies": ["Narrow firmware placements in European cities; budget: 4 queries, 12 candidate IDs"],
  "limitations": ["Synthetic example only; no source access"],
  "registry_suggestions": ["Evaluate narrower firmware placement wording before proposing a registry change"],
  "candidates": [
    {
      "url": "https://www.linkedin.com/jobs/view/1000000001",
      "listing": {
        "source_job_id": "1000000001",
        "company": "Example Labs",
        "title": "Firmware Intern 2027",
        "locations": ["Berlin, Germany"],
        "application_url": "https://www.linkedin.com/jobs/view/1000000001",
        "description": "Internship starting summer 2027."
      },
      "directly_verified": false,
      "availability": {
        "basis": "unknown",
        "evidence": "Source not accessed; current acceptance not established"
      },
      "location_cycle_evidence": "Synthetic location: Berlin, Germany; title opportunity cycle: 2027",
      "supporting_evidence": "Synthetic listing text only; no verified LinkedIn details",
      "uncertainties": ["Source not accessed"]
    }
  ]
}
```

Use `listing: null` for an inaccessible candidate whose employer/title/location cannot be established. Do not fill required source facts with invented placeholders. A partially evidenced but valid listing may retain missing locations or description; record each material uncertainty. Posting evidence, when present, requires an explicit timezone and must not be future-dated. Preserve the observation time used to interpret relative ages and label approximations; lower-bound or malformed ages provide no exact date. Graduation eligibility does not establish an internship cycle, and EMEA/worldwide language does not establish Europe.

Set `directly_verified` to the JSON boolean `true` only for a directly verified LinkedIn source observation; strings and numbers are rejected rather than coerced. A verified HTTP absence can use `listing: null`; do not invent identity fields from a failed response. This flag is a session attestation, not independent authentication or an AI confidence score. Evidence fields must state explicit location and cycle/posting conditions, short supporting quotations, source references, verification time, and any missing information. Unknown facts remain unknown.

```bash
uv run python scripts/research/scout.py report \
  --directory reports/linkedin-opportunity-scout/2026-10-20T120000Z
```

The helper first groups every observation by numeric ID, then reconciles evidence in a stable order independent of arrival order. Directly verified observations take precedence over unverified snippets; preliminary facts and uncertainties remain visible but cannot fill missing verified facts. Known facts must agree under both the cleaned case-folded text and the project's actual classifier normalization. This preserves harmless capitalization/whitespace and compatible Unicode forms, without treating a Unicode expansion as sufficient equivalence when the classifier interprets the alternatives differently. Completed observations also pass through the actual title/location normalization and classifier before being treated as compatible; omissions use agreeing verified facts, never snippet facts. Reconciliation preserves already-validated model fields without decoding HTML entities again, so a singleton or repeated observation cannot gain eligibility through an extra cleanup pass. Case-sensitive country-code interpretations must agree even when text comparison keys match. Missing fields can complement agreeing facts; conflicting nonempty title, employer, location, description, posting time, or optional metadata values require review. Title differences preserve seniority, type, and cycle conflicts; punctuation remains significant. Different nonempty descriptions are conservatively reviewed rather than concatenated. Verified free-text uncertainties remain blocking until explicitly resolved by a fresh review.

Record each observation separately, including its references and uncertainty. Additional observations of the same ID count as repeated IDs, not discarded evidence: the primary row preserves both stronger and superseded evidence. Missing availability can be completed by verified positive evidence, but conflicting verified open/closed states remain unknown and block batching. Resolve verified contradictions in an explained new ledger/revision after rechecking the source, preserving the original ledger/report. Do not silently remove inconvenient evidence or assume the latest observation wins. Explain the new source check, observation time, and why previous evidence no longer applies. A new directory or resolution label alone does not prove that review occurred: the helpers do not authenticate source claims, cross-revision history, or fresh verification.

The helper then normalizes reconciled facts, compares against the full public ID set, and applies the real classifier and publication model. Closed listings are rejected even if their title/location are eligible. Unknown availability, conflicts, unverified, missing, future-dated, or uncertain evidence stay conditional. Verified rule failures are rejected. A classifier pass on supplied facts is not source verification. Description-based acceptance may pass research but fail manual insertion: the existing CLI deliberately classifies without a description. Do not modify the indexed title or invent a posting date to overcome that distinction.

### Report and approval boundary

The report separates confirmed, further-review, and rejected candidates. Every primary table has exactly these five columns:

| Employer / indexed title | LinkedIn URL | Location and cycle evidence | Conditional classification | Supporting evidence and uncertainty |
|---|---|---|---|---|

Each unique nonduplicate candidate gets one row with a clickable canonical LinkedIn URL. Preserve normalized indexed employer/title, explicit evidence conditions, actual taxonomy values, deterministic outcome, and uncertainty. Repeated IDs are removed from candidate tables and summarized separately; their observations and meaningful differences remain in the primary row's evidence. Availability state, basis, source evidence, and unresolved conflicts appear in the final column. Description excerpts are bounded; the original ledger retains the full supplied text.

Include execution time, dataset retrieval/status fields, number of existing open positions examined, strategies and budgets, candidate observations, duplicate removals, confirmed/conditional/rejected counts, access limitations, registry suggestions, manually compatible count, and required batch count. Counts refer to the recorded ledger, not invisible search-engine totals. Report unknown counts as unknown. Keep evidence references in the last column; source text is escaped to preserve Markdown structure.

After writing the report, present its path, verified and uncertain counts, limitations, and required batches. Explicitly ask which IDs the user approves. Stop without canonical writes, workflow dispatch, pull requests, merge, or deployment. Research is useful without publication approval.

## Prepare and submit approved jobs

### Prepare exact compatible batches

After approval of specific candidates, reread the three workflow files and the [automation](automation.md#manual-job-addition) and [CLI](cli.md#add-jobs) owners. Compare current `main` workflow content if the checkout differs. Refresh public deduplication and source evidence, preserve the original report, and record changed or withdrawn candidates in a new run directory. Stop and ask if current verification is unavailable.

```bash
uv run python scripts/research/scout.py batches \
  --directory reports/linkedin-opportunity-scout/2026-10-20T120000Z \
  --approved-ids 1000000001,1000000002
```

Only explicitly selected, confirmed, explicitly open, conflict-free, manually compatible IDs enter batches. Preparation independently reconciles and reassesses `research.json` against the current dataset/rules; it never reads or trusts a displayed report status or a stored manual record. A changed ledger, known closure, unknown availability, or unresolved conflict cannot use an earlier report to bypass validation. The helper reuses `manual_jobs.parse_manual_batch`, the same pure schema/classifier validation as `add-jobs`; it neither loads settings nor opens SQLite. It reports skipped candidates and reasons. Zero accepted jobs produces zero batches. Batches split on both job count and exact UTF-8 byte size; large Unicode fields can require smaller batches. Every file is a UTF-8 JSON array of at most 10 jobs, at most 64 KiB, with required `url`, `company`, `title`, `location`, `category`, `employment_type` and optional `industries`, `start_date`, `posted_at`. No description, evidence, approval, or report fields enter workflow JSON. Missing facts are not invented.

Local validation cannot check private historical closed IDs. The protected workflow remains authoritative and rejects a closed-ID batch atomically. Do not access production state to preflight research or silently remove a failing entry and redispatch.

### Verify authenticated GitHub access

Use the user's existing authenticated connection. For GitHub CLI, inspect without printing tokens:

```bash
gh auth status --hostname github.com
gh api user --jq .login
gh api repos/simonesiega/european-tech-opportunities-2027 \
  --jq '{full_name, default_branch, permissions}'
gh workflow view add-job.yml -R simonesiega/european-tech-opportunities-2027 --ref main --yaml
```

Confirm the active account is the intended user, the exact target repository is correct, and repository permission permits workflow dispatch (normally write/maintain/admin) with Actions write authorization for the connection/token. Repository write permission alone does not prove a fine-grained token has Actions write. If permissions cannot be verified, ask the user to verify them or use the Actions UI; do not probe with an unauthorized dispatch. Never print token values, hardcode credentials, change accounts silently, or ask for tokens in tracked files. An integration connection and the CLI can use different accounts.

Inspect open state-review proposals and active/pending canonical-state workflows before dispatch. No competing update may be dispatched to bypass the one-writer lock. The workflow's restore/migrate/render comparison against reviewed `main` is the final readiness gate, not a locally guessed snapshot check.

### Obtain dispatch approval and run one batch

> [!WARNING]
> `add-job.yml` writes approved jobs to canonical SQLite and publishes a verified protected snapshot **before** creating/updating its generated README review PR. This is not a harmless source-code PR operation. Closing the PR does not undo the canonical mutation.

Show selected IDs, batch contents, validation results, target repository/ref, and these side effects. Obtain explicit approval to dispatch that exact batch. Candidate review/preparation permission alone is not dispatch permission. ID selection does not bind later field changes: obtain renewed approval for changed batch contents, and verify the final file still matches the reviewed bytes immediately before dispatch. This remains a session/human approval boundary, not software authentication of consent.

Only after approval, use the supported workflow:

```bash
gh workflow run add-job.yml \
  -R simonesiega/european-tech-opportunities-2027 --ref main \
  --field jobs_json=@reports/linkedin-opportunity-scout/2026-10-20T120000Z/batch-01.json
```

The workflow serializes canonical work through `opportunity-collection`, restores and verifies the snapshot, migrates, checks reviewed state, validates and atomically inserts the batch through `Repository`, regenerates and validates projections, publishes and round-trip verifies the snapshot, and hands six public READMEs to the existing PR workflow. No LinkedIn access is performed. The generated `automated/manual-jobs-YYYY-MM-DD` PR uses the run's Europe/Rome date, awaits normal validation, and never requests auto-merge.

Identify the exact dispatch run from its creation time, actor, event, workflow, and `main` SHA; do not select an unrelated latest run. Inspect its outcome, sanitized artifact, resulting PR scope/head, and validation checks. Record run and PR URLs beside the report. If dispatch returns an uncertain result, reconcile existing runs before any retry: state may already have changed. A failed proposal after successful snapshot publication requires the documented [read-only proposal recovery](automation.md#recover-a-missing-readme-state-proposal), not another insertion.

If tools or permissions prevent dispatch, provide the exact prepared JSON and these manual steps: **Actions → Add manually reviewed jobs → Run workflow → main**, paste one array into `jobs_json`, and run only after reviewing the state-changing warning. The user must still review the resulting README PR and checks.

### Multiple batches and completion

Never dispatch batches concurrently. Process one batch, inspect its run and README PR/checks, and leave merge to the user. Wait until that reviewed state is properly merged and fresh `main` is ready for a new mutation. An open, closed-unmerged, or failed proposal does not clear the reviewed-state barrier. Obtain approval for each later dispatch, refresh evidence/deduplication, and start a fresh run from current `main`; do not rerun an old workflow commit to bypass review.

Report submitted IDs, skipped IDs and reasons, batch sizes, validation results/failures, workflow/PR URLs, review status, and remaining steps. Merge and deployment remain separate user decisions. After merge, the supported [deployment-only operation](automation.md#deployment-only-path) publishes reviewed state; the skill must not execute it without separate approval. Do not call jobs live until [production verification](automation.md#verify-the-deployed-dataset) succeeds.

## Troubleshooting and maintenance

- **No compliant LinkedIn access:** keep candidates unverified, explain tool/policy restrictions, and generate the report. Never use authenticated browsers or a substitute scraper.
- **API drift or failure:** `[dataset_changed]` permits waiting and retrying at most once. `[export_required]` directs a hash-checked `dataset --export` read. `[http_429]` means stop requests and respect the rate limit, not immediate retry/fallback. `[public_timeout]` saved no complete dataset. Other `[invalid_input_or_data]` failures need input/contract/output-access review; use the export only where appropriate, or report with `--without-dataset`. Messages contain bounded categories, never exception contents. Never claim newness from partial data.
- **Closed or unresolved evidence:** keep the listing rejected or conditional. Missing closure warnings do not prove acceptance. Preserve contradictory verified observations and explain any fresh source review before preparing additions.
- **Local validation failure:** inspect current evidence and rules, preserve failed inputs, and report the missing/conflicting condition. Do not weaken classification. `[approval_required]` requires explicit candidate selection; `[invalid_approval]` requires unique known IDs not already published. `[invalid_options]` means flags belong to another command: `--export` is dataset-only, `--without-dataset` report-only, and `--approved-ids` batches-only. These preflight failures do not initiate public reads.
- **Existing dataset, report, or batches:** `[output_exists]` means preserve them; choose a new timestamp/suffix and regenerate from reviewed inputs. An existing dataset output is rejected before any HTTP request.
- **Missing uv/tools:** follow [local setup](../getting-started/setup.md), or produce a report manually following the same contract. Disclose unrun validation and do not label candidates confirmed without deterministic checks.
- **GitHub denied or account uncertain:** stop at prepared JSON and use the authenticated Actions UI after user review. Do not broaden permissions automatically.
- **Unmerged state or failed publication:** follow [automation recovery](automation.md#recover-a-missing-readme-state-proposal); no direct SQL, snapshot access for research, PR workaround, or repeated dispatch.

The tracked skill is an explicit exception to the otherwise ignored personal skills area. Personal routers, unrelated skills, context notes, and all reports remain ignored. The helpers have no dispatch code or source transport. Maintain their offline tests in the [test inventory](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/tests/TEST.md), run the [Python/docs gate](../engineering/testing.md#python-and-documentation), and keep skill references synchronized with owner paths.
