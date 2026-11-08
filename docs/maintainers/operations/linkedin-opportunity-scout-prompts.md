# Use the LinkedIn scout prompts

[← Maintainer handbook](../README.md) · [Scout runbook](linkedin-opportunity-scout.md) · [Security](../../../SECURITY.md)

Copy one prompt for the task you want, replace its placeholders, and send it in your repository's assistant session. These templates invoke the shared `linkedin-opportunity-scout` skill; the [runbook](linkedin-opportunity-scout.md) remains the owner of the procedure, evidence requirements, and stop conditions.

Reading this page is not approval to execute its examples. Only an explicit message from you can approve a particular action. Research, batch preparation, workflow dispatch, merge, and deployment are separate decisions; do not paste the whole page as one instruction.

## Contents

- [Before you start](#before-you-start)
- [Research](#research)
- [Review and refresh](#review-and-refresh)
- [Prepare approved jobs](#prepare-approved-jobs)
- [Submit one reviewed batch](#submit-one-reviewed-batch)
- [Follow the workflow and PR](#follow-the-workflow-and-pr)
- [Prepare a later batch](#prepare-a-later-batch)
- [Handle a failed or uncertain submission](#handle-a-failed-or-uncertain-submission)
- [Plan deployment](#plan-deployment)

## Before you start

Use a current checkout containing the skill and follow [local setup](../getting-started/setup.md). Open a fresh session if the skill is not discovered. If native invocation is unavailable, ask the assistant to read `.agents/skills/linkedin-opportunity-scout/SKILL.md` and follow it for the selected task.

Replace every placeholder used by your chosen prompt. An unresolved placeholder should cause the assistant to ask, not guess.

| Placeholder | What to provide |
|---|---|
| `<max-search-queries>` | Maximum discovery queries for this session, not a target number of findings |
| `<max-candidate-ids>` | Maximum distinct LinkedIn candidate IDs to investigate; this does not limit comparison against the complete published dataset |
| `<focus>` | Countries, cities, employers, or technical disciplines to prioritize within current eligibility rules |
| `<linkedin-urls>` | A list of public LinkedIn listing URLs with independently evidenced numeric IDs |
| `<run-directory>` | An existing research directory under ignored `reports/linkedin-opportunity-scout/` |
| `<candidate-ids>` | Specific candidate IDs to inspect or recheck, without approving them for addition |
| `<approved-job-ids>` | Comma-separated job IDs you explicitly select for preparation |
| `<batch-file>` | Exact prepared JSON file you have reviewed, under the ignored research directory |
| `<reviewed-batch-sha256>` | SHA-256 of the exact reviewed batch bytes, shown during preparation |
| `<target-repository>` | Intended GitHub repository in `owner/repository` form |
| `<workflow-run-url>` | Exact manual-add workflow run to inspect, not an unrelated latest run |
| `<readme-pr-url>` | Exact generated README review PR associated with the relevant batch |

The budgets narrow research; they cannot increase repository request limits. None of these prompts grants LinkedIn source permission or enables its authorization interlock. If compliant source access is unavailable, expect uncertain or zero confirmed findings rather than a substitute scraper. See the [source-access boundary](linkedin-opportunity-scout.md#verify-source-evidence).

## Research

### General discovery

**Case:** Start a broad research session without preparing additions or changing canonical state.

```text
$linkedin-opportunity-scout

Research overlooked European technology internships and New Grad roles using
current repository rules. Read the skill, scout runbook, and current policy owners
before choosing queries; do not rely on remembered eligibility rules.

Use at most <max-search-queries> targeted discovery queries and investigate at most
<max-candidate-ids> distinct candidate IDs. Prioritize justified gaps in configured
coverage rather than replaying every production search. These are limits, not quotas.
Compare candidates against the complete, consistency-checked published open dataset.

Use only policy-compliant tools. Do not enable LinkedIn source authorization,
change settings, or treat search snippets as direct verification. Require explicit
current acceptance evidence; preserve unknown facts and contradictory observations.

Save research.json and an evidence-based report.md in a new ignored UTC run directory.
Show the report path, findings, limitations, manually addable count, and batch count.
If the dataset is unavailable, report unknown novelty; do not assume it is empty.
Stop before preparing batches, dispatching workflows, creating PRs, merging, or deploying.
```

**Expect:** A report separating confirmed, conditional, rejected, and duplicate findings, with no canonical mutation. A zero-finding report is valid.

### Focused coverage gaps

**Case:** Investigate a particular geography, employer group, or technical discipline without changing acceptance rules.

```text
$linkedin-opportunity-scout

Research overlooked opportunities with this focus: <focus>.
Use current repository eligibility rules and inspect relevant configured searches
before selecting narrower, complementary queries. The focus is a discovery filter,
not permission to accept an otherwise ineligible role or edit the search registry.

Use at most <max-search-queries> discovery queries and investigate at most
<max-candidate-ids> distinct candidate IDs. Compare against the complete validated
published open dataset, not the README preview or a partial cache.

Follow the skill's source-access and evidence requirements. Do not enable LinkedIn
source authorization or infer current acceptance from an Apply button or snippet.
Record unsupported locations, unclear cycles, inaccessible details, and conflicts honestly.
Save a new ignored research ledger and report with findings and coverage suggestions.
Show evidence, limitations, manually addable count, and required batch count.
Stop before batch preparation or any GitHub, canonical-state, merge, or deployment mutation.
```

**Expect:** A focused report and proposed coverage improvements, not changes to production search configuration.

### Known listing URLs

**Case:** Assess listings you already found instead of asking for broader discovery.

```text
$linkedin-opportunity-scout

Assess only these LinkedIn listings:
<linkedin-urls>

Investigate at most <max-candidate-ids> distinct IDs; ask me to select a subset if
the supplied list exceeds that budget. Do not expand into unrelated discovery.
Validate each listing's numeric identity without following source redirects or
inventing a canonical ID. Compare against the complete published open dataset.

Read current rules and use only compliant source access already permitted by policy.
Do not enable LinkedIn source authorization. For each listing, distinguish directly
verified facts from snippets, missing evidence, and unresolved contradictions.
Check explicit current acceptance separately from eligibility and manual compatibility.

Save a new ignored ledger and report, preserving unavailable listings as uncertain
or explicitly closed where supported. Show the report path and each ID's outcome.
Do not prepare additions, dispatch, open PRs, merge, or deploy.
```

**Expect:** Evidence-based outcomes for the supplied listings only. Supplying a URL does not approve adding its job.

## Review and refresh

### Review a saved report offline

**Case:** Understand the findings before deciding which jobs, if any, to approve.

```text
$linkedin-opportunity-scout

Review the saved report, research.json, and any dataset.json in <run-directory>.
Use current repository rules to explain the recorded findings without making new
network requests or overwriting any existing artifacts.

Explain which IDs are confirmed, conditional, rejected, or duplicates; identify
missing evidence, availability uncertainty, conflicting observations, and any
research acceptance that fails title-only manual insertion. Do not trust report
labels instead of checking the underlying ledger and deterministic assessment.

Separate what was established at the recorded observation time from what would
need a fresh check now. Do not claim the saved dataset or source evidence is current.
If a local input or tool is unavailable, report that limitation rather than guessing.
Give me a concise decision summary and the evidence needed for unresolved candidates.
This is review only: do not prepare batches, dispatch, change canonical state, or publish.
```

**Expect:** An explanation of the saved evidence, not a new source-verification claim or approval inferred from your interest in a candidate.

### Recheck selected candidates

**Case:** Resolve uncertainty or refresh older evidence before selecting jobs.

```text
$linkedin-opportunity-scout

Recheck candidate IDs <candidate-ids> from <run-directory> using current rules.
Limit any additional discovery to <max-search-queries> queries; investigate only
the selected IDs. This is not approval to add them.

Refresh the complete published open dataset and source facts only through permitted
interfaces. Do not enable LinkedIn source authorization or switch tools to evade a block.
If current verification is unavailable, retain the uncertainty and explain what is missing.

Preserve the original ledger and report. Save any refreshed assessment in a new ignored
UTC run directory, explaining what was rechecked, when, and why earlier evidence does
or does not still apply. Never resolve contradictions by silently dropping observations.

Show changed outcomes, newly published duplicates, unresolved issues, and manual
compatibility. Stop before batch preparation, dispatch, PR creation, merge, or deployment.
```

**Expect:** A separate evidence revision and an explanation of changed outcomes. A new directory alone is not proof of fresh verification.

## Prepare approved jobs

**Case:** You have reviewed the findings and selected specific IDs, but have not approved submission.

```text
$linkedin-opportunity-scout

I approve only IDs <approved-job-ids> from <run-directory> for local batch preparation.
This does not authorize workflow dispatch, canonical writes, PR creation, merge, or deployment.

Follow the current skill and runbook. Refresh complete public deduplication and reverify
source facts as permitted, preserving the original report in its original directory.
Do not enable LinkedIn source authorization. If freshness cannot be checked, stop and ask.
Withdraw duplicates, closed, uncertain, conflicting, or manually incompatible candidates;
do not replace them with other IDs or alter genuine titles to make validation pass.

Independently reassess the ledger and use the shared manual validator to prepare exact
JSON batches of at most 10 jobs and 64 KiB each. Keep outputs in a new ignored run revision.
Show each batch path, selected IDs, full JSON, job count, exact UTF-8 byte size, SHA-256,
validation result, intended target <target-repository>, and main ref. Explain every skipped ID.

Explain that dispatch writes canonical state and publishes a protected snapshot before
creating or updating its generated README review PR. Ask for approval of one exact batch
and stop. Do not submit any batch or infer consent for later batches.
```

**Expect:** Reviewed `batch-01.json`, and additional files if needed, plus a separate dispatch question. The digest identifies reviewed bytes; it is not software authentication of consent.

## Submit one reviewed batch

**Case:** You have inspected one exact batch and intend to authorize its state-changing submission.

> [!WARNING]
> Send this prompt only when you intend to dispatch. The workflow writes canonical state and publishes its snapshot **before** opening or updating the README review PR. Closing the PR does not undo those writes.

```text
$linkedin-opportunity-scout

I explicitly approve dispatching only <batch-file>, with reviewed SHA-256
<reviewed-batch-sha256>, to <target-repository> through add-job.yml on main.
I understand that this writes canonical SQLite and publishes a protected snapshot
before creating or updating the generated README review PR.

Before dispatch, verify the file matches the exact reviewed bytes and independently
reassess the underlying evidence, complete deduplication, and manual validation under
the current workflow contract. Do not enable LinkedIn source authorization. If facts
cannot be reverified as required, content changes, or validation fails, stop and ask;
do not silently rewrite, substitute, or submit a different batch.

Verify the authenticated GitHub identity, intended repository, Actions permissions,
and absence of a conflicting pending canonical-state update or unmerged state proposal.
Do not read production state, change credentials, or bypass the reviewed-state barrier.
If access or tools are insufficient, provide the exact JSON and documented Actions UI steps.

Dispatch this one batch only. Identify its exact run and resulting README PR, report
validation or pending checks, and preserve run and PR references beside the report.
If dispatch is uncertain, reconcile its result before any retry. Do not submit another
batch, merge, enable auto-merge, deploy, or claim the jobs are live.
```

**Expect:** If processing succeeds and projections change, the existing workflow opens or updates a scoped README review PR. A failed or uncertain run may already have published canonical state; use the [reconciliation prompt](#handle-a-failed-or-uncertain-submission) instead of resubmitting.

## Follow the workflow and PR

**Case:** A batch has been submitted and you want its current status without another mutation.

```text
$linkedin-opportunity-scout

Inspect this exact submitted batch run: <workflow-run-url>.
Locate its associated README review PR, if one exists, and verify the relationship
using the run, actor, workflow, main SHA, and proposal metadata rather than the latest run.

Report processing, snapshot publication, proposal creation, and required validation
statuses separately. Check the PR scope and current head. Identify failed, pending,
missing, or stale checks without treating skipped or unrun work as passed.

Use read-only GitHub metadata and sanitized public artifacts. Do not access canonical
state, print private logs, redispatch workflows, rerun jobs, or change the PR.
Explain whether manual review can proceed, whether another batch must wait, and what
still needs separate deployment and production verification. Do not merge or deploy.
```

**Expect:** Exact run/PR links, a current check summary, and the next human decision. Workflow success is not proof that the website serves the new jobs.

## Prepare a later batch

**Case:** A previous README proposal has been merged and you want to prepare the next selected IDs.

```text
$linkedin-opportunity-scout

The previous batch's README proposal is <readme-pr-url>.
Verify it was properly reviewed and merged, current main includes that reviewed state,
and no conflicting canonical update or unresolved proposal is pending.
A closed-but-unmerged PR or a failed workflow is not permission to continue.

If ready, I approve only the remaining IDs <approved-job-ids> from <run-directory>
for refreshed local preparation. Recheck public deduplication, permitted source evidence,
current rules, and manual compatibility. Preserve earlier artifacts in a new ignored revision.
Do not enable LinkedIn source authorization; if freshness cannot be established, stop.

Show the next eligible batch's exact JSON, IDs, count, byte size, SHA-256, validation,
and intended target <target-repository> on main. Explain skipped IDs and remaining batches.
Ask for separate approval to dispatch that exact batch, then stop. Do not dispatch,
reuse prior batch consent, merge, deploy, or bypass the reviewed-state barrier.
```

**Expect:** A freshly checked next batch, or a clear reason it must wait. Earlier approval does not carry over to the next dispatch.

## Handle a failed or uncertain submission

**Case:** A dispatch timed out, processing failed, or the expected PR did not appear.

```text
$linkedin-opportunity-scout

Reconcile this failed or uncertain submission: <workflow-run-url>.
Use read-only GitHub metadata and sanitized public artifacts to identify the exact
batch run and any associated README proposal. Do not guess from an unrelated latest run.

Distinguish known completed phases, known failures, and unknown results. In particular,
check whether snapshot publication may have succeeded before proposal creation failed.
Never infer that a missing PR or failed run means canonical state was unchanged.

Preserve existing evidence and explain the applicable recovery procedure from the
current automation guide, including whether a missing README proposal needs its
separate read-only recovery workflow. Ask for any minimal sanitized information you lack.

Do not redispatch the addition, rerun a workflow, launch recovery, open a competing PR,
inspect production state, edit the database or generated READMEs, merge, or deploy.
Give me the safest next action and its side effects; wait for specific approval.
```

**Expect:** A diagnosis and approval-gated recovery recommendation, not another insertion. The [automation recovery guide](automation.md#recover-a-missing-readme-state-proposal) owns the procedure.

## Plan deployment

**Case:** The README proposal is merged and you want to understand the remaining publication steps.

```text
$linkedin-opportunity-scout

Review the merged README proposal <readme-pr-url> and its batch run <workflow-run-url>.
Using current repository documentation and read-only metadata, explain the supported
deployment-only path and the verification needed before calling these jobs live.

Separate canonical snapshot publication, merged README review, website deployment,
and production dataset verification. Identify any failed or pending prerequisite
and the exact action that would need separate approval.

This is planning only. Do not dispatch a deployment or recovery workflow, connect to
production, read private settings or snapshots, collect LinkedIn data, or mutate GitHub.
Do not claim production serves the jobs from a successful addition run or merged PR alone.
Stop with the next operator steps and links to their canonical procedures.
```

**Expect:** A publication checklist, not a deployment. Follow [deployment-only operation](automation.md#deployment-only-path) and [production verification](automation.md#verify-the-deployed-dataset) with separate operational approval.
