# Diagram source

[← Repository maps](README.md) · [Visual assets](../README.md) · [Rendering profile](#rendering-profile)

This file owns the five SVGs in `svg/`: their labels, relationships, accessibility descriptions, and rendering configuration. Use the [annotated maps](README.md) to explore the architecture and the [rendering profile](#rendering-profile) to regenerate assets after a source change.

The colors, grouped components, directed relationships, and clickable code links follow [GitDiagram's](https://github.com/ahmedkhaleel2004/gitdiagram) visual approach. Solid arrows carry data or artifacts; dashed arrows indicate configuration, orchestration, or a supporting dependency. These are subsystem maps, not exhaustive import graphs.

## Repository overview

```mermaid
flowchart TB
    accTitle: European Tech Opportunities 2027 — repository overview
    accDescr: Configuration and the CLI drive permission-gated collection with persistent oldest-completed search rotation and a separate bounded availability audit. Repository is the only application writer to canonical SQLite. HTTP 429 stops source requests; completed searches can publish only after quality and integrity gates and manual review. Other source denials and all audit denials block publication. The website, API, exports, and README are read-only projections.

    subgraph CONTROL["Configuration and<br/>entry points"]
        CONFIG["Searches + classification rules<br/>configs/"]
        CLI["CLI + runtime settings<br/>cli/ · config/"]
        CONFIG -.-> CLI
    end

    subgraph PYTHON["Python pipeline<br/>src/opportunities/"]
        COLLECT["Rotate searches → collect → classify<br/>scrapers/ · normalization/ · pipeline/"]
        AUDIT["Bounded due-job availability audit<br/>pipeline/availability.py"]
        REPO{{"Repository<br/>Only application writer"}}
        DOMAIN["Typed records + shared helpers<br/>models/ · utils/"]
        COLLECT -->|accepted jobs + search outcomes| REPO
        AUDIT -->|confirmed availability evidence| REPO
        DOMAIN -.-> COLLECT
    end

    subgraph STATE["Canonical lifecycle state"]
        DB[("SQLite lifecycle + provenance<br/>Search rotation + quality baselines")]
        MIGRATIONS["Schema evolution<br/>migrations/ · database/"]
        MIGRATIONS -.->|Alembic upgrades| DB
    end

    subgraph PUBLIC["Read-only publication"]
        WEB["Next.js directory + v1 API<br/>site/src/"]
        EXPORTS["Sanitized CSV / JSON + metadata<br/>public_exports.py · schemas/"]
        PREVIEW["README preview + full-state seal<br/>readme.py"]
        LOCAL["Saved / applied / hidden + visit state<br/>Browser localStorage only"]
        EXPORTS -->|fixed download routes| WEB
        WEB <-->|local interactions only| LOCAL
    end

    subgraph SUPPORT["Operations and<br/>repository foundations"]
        OPS["Protected automation + recovery<br/>Full / partial / blocked publication gates<br/>.github/workflows/ · scripts/"]
        TESTS["Offline tests + synthetic fixtures<br/>tests/ · site/tests/ · scripts/testing/"]
        DOCS["Guides + public visuals<br/>docs/ · scripts/docs/"]
        BUILD["Packages + containers<br/>pyproject.toml · site/package.json<br/>Dockerfile · docker-compose.yml"]
        POLICY["Security + privacy + contribution rules<br/>Root policies · .github/ controls"]
    end

    CLI -.->|scrape| COLLECT
    CLI -.->|check-availability| AUDIT
    CLI -.->|offline reviewed input; same classifier| REPO
    REPO -->|transactional lifecycle writes| DB
    DB -->|open rows; server-only query| WEB
    DB -->|approved public fields| EXPORTS
    DB -->|bounded preview; complete review seal| PREVIEW
    OPS -.->|one-writer orchestration| CLI
    TESTS -.->|verify invariants| PYTHON
    TESTS -.->|verify read-only behavior| PUBLIC
    BUILD -.-> CLI
    BUILD -.-> WEB
    POLICY -.-> OPS
    DOCS -.->|explain contracts| POLICY

    click CONFIG "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/configs"
    click CLI "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/cli/app.py"
    click COLLECT "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/runner.py"
    click AUDIT "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/availability.py"
    click REPO "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/database/repository.py"
    click DOMAIN "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/src/opportunities/models"
    click DB "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/database/models.py"
    click MIGRATIONS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/migrations"
    click WEB "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/site/src"
    click EXPORTS "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/public_exports.py"
    click PREVIEW "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/readme.py"
    click LOCAL "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/lib/local-opportunity-state.ts"
    click OPS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/.github/workflows"
    click TESTS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/tests"
    click DOCS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/docs"
    click BUILD "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/Dockerfile"
    click POLICY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/SECURITY.md"

    classDef blue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
    classDef mint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
    classDef amber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
    classDef teal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
    classDef rose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
    classDef indigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
    class CONFIG,CLI blue
    class COLLECT,AUDIT,DOMAIN mint
    class REPO,DB,MIGRATIONS amber
    class WEB,EXPORTS,PREVIEW,LOCAL teal
    class OPS rose
    class TESTS,DOCS,BUILD,POLICY indigo
```

## Collection and lifecycle

```mermaid
flowchart TB
    accTitle: Collection and lifecycle — evidence before persistence
    accDescr: Search YAML selects discovery scope, not publication eligibility. SQLite completion timestamps prioritize never-completed and oldest-completed searches. Authorized bounded HTTP stops all subsequent requests on denial. Successful searches persist independently; failed and skipped searches record diagnostics without lifecycle evidence or scheduling advancement. HTTP 429 can qualify as partial publication only after completed searches and all quality and integrity gates; partial runs never establish full-registry baselines. The separate bounded availability audit preserves inconclusive rows and blocks publication on any source denial.

    subgraph INPUT["What to run"]
        SEARCHES["Discovery YAML<br/>configs/searches/<br/>companies/ · countries/ · roles/"]
        RULES["Acceptance rules + cycle policy<br/>configs/categories.yml<br/>config/rules.py · policy.py"]
        SETTINGS["Settings + search registry<br/>config/settings.py<br/>config/search_registry.py"]
        ENTRY["Command entry point<br/>__main__.py → cli/app.py"]
        SEARCHES -.-> SETTINGS
        SETTINGS -.-> ENTRY
    end

    subgraph FETCH["Bounded public<br/>source access"]
        RUNNER["CollectionPipeline<br/>pipeline/runner.py<br/>Bounded concurrency; isolated outcomes"]
        ROTATION["Persistent search rotation<br/>searches.last_completed_at<br/>Never completed → oldest completed"]
        HTTP["Authorization interlock + HTTP bounds<br/>scrapers/http.py<br/>No cookies or redirects; stop on denial"]
        SOURCE(["LinkedIn guest HTML<br/>External source; permission required"])
        CARDS["Search cards + company/title prefilters<br/>scrapers/linkedin.py"]
        DETAILS["Validated details + numeric identity<br/>scrapers/linkedin.py<br/>Shared requests; bounded known-ID rechecks"]
        RUNNER -.->|orchestrates| HTTP
        SOURCE -->|bounded responses| HTTP
        HTTP -->|search HTML| CARDS
        CARDS -->|eligible IDs| DETAILS
        HTTP -->|detail HTML| DETAILS
    end

    subgraph DECIDE["Deterministic<br/>acceptance<br/>No network or SQL"]
        NORMALIZE["Normalize title + European locations<br/>normalization/title.py · location.py"]
        CLASSIFY["Classifier<br/>pipeline/classification.py<br/>Type · seniority · tech · cycle/date · geography"]
        ACCEPTED["Accepted DiscoveredJob records<br/>models/job.py"]
        EXCLUDED["Ambiguous or out-of-scope evidence<br/>Exclude; do not publish"]
        NORMALIZE --> CLASSIFY
        CLASSIFY -->|include| ACCEPTED
        CLASSIFY -->|stable exclusion reason| EXCLUDED
    end

    subgraph PERSIST["Repository owns<br/>lifecycle writes"]
        OUTCOMES["Search outcomes in finish-time order<br/>pipeline/runner.py<br/>Full 0 / partial 4 / blocked 1"]
        QUALITY["Aggregate collection-quality gate<br/>pipeline/data_quality.py<br/>429 partial needs completed searches + gate<br/>Only full-registry success builds baselines"]
        REPOSITORY{{"Repository transactions<br/>database/repository.py"}}
        DATABASE[("Canonical SQLite<br/>database/models.py · session.py<br/>Lifecycle + provenance + search rotation")]
        OUTCOMES -->|success: jobs + completion time; failure/skipped: diagnostics only| REPOSITORY
        REPOSITORY --> DATABASE
    end

    subgraph MAINTENANCE["Separate<br/>maintenance paths"]
        AUDIT["Bounded due-job audit<br/>pipeline/availability.py<br/>50 jobs by default; five-day minimum"]
        MANUAL["Reviewed offline add-job / add-jobs<br/>cli/app.py<br/>No invented provenance or manual reopen"]
    end

    ENTRY -.-> RUNNER
    DATABASE -->|completion timestamps| ROTATION
    ROTATION -.->|stable oldest-first priority| RUNNER
    OUTCOMES -->|completed-search metrics| QUALITY
    QUALITY -.->|gate publication; no lifecycle rollback| ENTRY
    ENTRY -.-> AUDIT
    ENTRY -.-> MANUAL
    RULES -.-> CLASSIFY
    DETAILS --> NORMALIZE
    ACCEPTED --> OUTCOMES
    DETAILS -->|known-ID rechecks: explicit 404/410 evidence| OUTCOMES
    RUNNER -->|denied or skipped: no negative evidence| OUTCOMES
    AUDIT -.->|uses same bounded transport| HTTP
    AUDIT -->|keep/reopen; explicit unavailability deletes; uncertainty preserves| REPOSITORY
    MANUAL -.->|reuses acceptance checks| CLASSIFY
    MANUAL -->|validated batch; one transaction| REPOSITORY

    click SEARCHES "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/configs/searches"
    click RULES "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/configs/categories.yml"
    click SETTINGS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/src/opportunities/config"
    click ENTRY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/cli/app.py"
    click RUNNER "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/runner.py"
    click ROTATION "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/database/repository.py"
    click QUALITY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/data_quality.py"
    click HTTP "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/scrapers/http.py"
    click SOURCE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/SECURITY.md"
    click CARDS "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/scrapers/linkedin.py"
    click DETAILS "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/scrapers/linkedin.py"
    click NORMALIZE "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/src/opportunities/normalization"
    click CLASSIFY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/classification.py"
    click ACCEPTED "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/models/job.py"
    click EXCLUDED "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/classification.py"
    click OUTCOMES "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/runner.py"
    click REPOSITORY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/database/repository.py"
    click DATABASE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/database/models.py"
    click AUDIT "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/pipeline/availability.py"
    click MANUAL "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/cli/app.py"

    classDef blue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
    classDef mint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
    classDef amber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
    classDef rose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
    classDef indigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
    class SEARCHES,RULES,SETTINGS,ENTRY blue
    class RUNNER,HTTP,CARDS,DETAILS,NORMALIZE,CLASSIFY,ACCEPTED,OUTCOMES,QUALITY mint
    class REPOSITORY,DATABASE,ROTATION amber
    class SOURCE,EXCLUDED rose
    class AUDIT,MANUAL indigo
```

## Website and publication

```mermaid
flowchart TB
    accTitle: Website and publication — read-only server, private browser state
    accDescr: SQLite supplies open rows to Python projection renderers and to a server-only Next.js query shared by the page and public API. The website serves fixed generated download files; it does not create them. Browser-local lists never enter the database, URLs, API, or analytics. In versioned deployment mode each server operation resolves the release pointer once.

    subgraph DATA["Publication inputs"]
        DB[("Canonical SQLite<br/>Open jobs + last successful collection")]
        RELEASE["Versioned release selection<br/>site/src/lib/release-path.ts<br/>Resolve current once per operation"]
        SCHEMA["Public v1 contracts + examples<br/>schemas/"]
    end

    subgraph PYTHON["Python-generated<br/>projections<br/>src/opportunities/"]
        RENDER["Bounded preview + full-state review seal<br/>readme.py"]
        README["README.md<br/>At most five newest jobs per type"]
        EXPORT["Allowlisted fields + spreadsheet-safe CSV<br/>public_exports.py"]
        FILES["Generated CSV / JSON + metadata<br/>data/exports/ · ignored runtime files"]
        RENDER --> README
        EXPORT --> FILES
    end

    subgraph SERVER["Next.js server<br/>No canonical writes"]
        QUERY["Shared read-only SQLite query<br/>site/src/lib/opportunities.ts<br/>node:sqlite · readOnly: true"]
        PAGE["Directory page + layout<br/>site/src/app/page.tsx · layout.tsx"]
        API["GET /api/v1/opportunities<br/>app/api/v1/opportunities/route.ts<br/>lib/opportunity-api.ts"]
        DOWNLOAD["Fixed CSV / JSON / metadata routes<br/>site/src/lib/public-export.ts"]
        SCHEMAROUTE["GET /schemas/opportunities-v1.schema.json<br/>site/src/app/schemas/"]
        SEO["Metadata + sitemap + robots + JSON-LD<br/>app/ · lib/structured-data.ts<br/>lib/site-url.ts · site-config.ts"]
        QUERY --> PAGE
        QUERY -->|bounded query; explicit public fields| API
        SEO -.-> PAGE
    end

    subgraph BROWSER["React browser<br/>interaction · site/src/"]
        DIRECTORY["Opportunity directory<br/>components/opportunities/<br/>Table · filters · sorting · pagination"]
        HELPERS["URL + presentation helpers<br/>lib/opportunity-filter.ts · opportunity-sort.ts<br/>opportunity-presentation.ts · listing-url.ts"]
        UI["Shared UI + theme + layout<br/>components/ui/ · theme/ · layout/<br/>types/ · app/globals.css"]
        LISTS["Local list parsing + synchronization<br/>lib/local-opportunity-state.ts<br/>use-local-opportunities.ts"]
        STORAGE[("Browser localStorage<br/>Saved / applied / hidden IDs + visit times<br/>Never sent to server or analytics")]
        ANALYTICS(["Production-only Umami integration<br/>Not connected to private lists"])
        HELPERS -.-> DIRECTORY
        UI -.-> DIRECTORY
        DIRECTORY <-->|browser actions| LISTS
        LISTS <--> STORAGE
    end

    DB --> RENDER
    DB --> EXPORT
    DB --> QUERY
    RELEASE -.->|select database| QUERY
    RELEASE -.->|select export directory| DOWNLOAD
    SCHEMA -.->|validate exports| EXPORT
    SCHEMA --> SCHEMAROUTE
    FILES -->|serve existing bytes| DOWNLOAD
    PAGE -->|public rows as props| DIRECTORY
    PAGE -.->|production origin only| ANALYTICS

    click DB "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/database/models.py"
    click RELEASE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/lib/release-path.ts"
    click SCHEMA "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/schemas"
    click RENDER "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/readme.py"
    click README "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/README.md"
    click EXPORT "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/public_exports.py"
    click FILES "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/docs/users/data/data.md"
    click QUERY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/lib/opportunities.ts"
    click PAGE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/app/page.tsx"
    click API "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/app/api/v1/opportunities/route.ts"
    click DOWNLOAD "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/lib/public-export.ts"
    click SCHEMAROUTE "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/site/src/app/schemas"
    click SEO "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/lib/structured-data.ts"
    click DIRECTORY "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/site/src/components/opportunities"
    click HELPERS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/site/src/lib"
    click UI "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/site/src/components"
    click LISTS "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/components/opportunities/use-local-opportunities.ts"
    click STORAGE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/lib/local-opportunity-state.ts"
    click ANALYTICS "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/app/layout.tsx"

    classDef blue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
    classDef mint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
    classDef amber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
    classDef teal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
    classDef rose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
    classDef indigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
    class DB,RELEASE amber
    class SCHEMA,SEO indigo
    class RENDER,EXPORT mint
    class README,FILES,QUERY,PAGE,API,DOWNLOAD,SCHEMAROUTE teal
    class DIRECTORY,HELPERS,UI,LISTS,STORAGE blue
    class ANALYTICS rose
```

## Automation and deployment

```mermaid
flowchart TB
    accTitle: Automation and deployment — protected state, reviewed publication
    accDescr: Scheduled or manual workflows serialize canonical operations through a shared writer lock. The reusable processor restores verified state, migrates, requires the reviewed README to match, and executes selected CLI phases. Full or eligible partial collection, including HTTP 429 partial results, must pass quality, SQLite integrity, projection, and snapshot checks. Other source denials, all audit denials, and failed validation block publication. Scheduling progress travels only with verified SQLite snapshots. A separate job receives only the README: full nightly collections retain automatic merging after checks, while partial proposals require manual review and merge. Unmerged or rejected state blocks subsequent ordinary mutations and deployment.

    subgraph TRIGGERS["Operator-facing<br/>workflows<br/>.github/workflows/"]
        NIGHTLY["nightly.yml<br/>Availability audit → scrape"]
        MANUAL["scrape.yml · check-availability.yml<br/>add-job.yml<br/>Explicitly selected dataset updates"]
    end

    subgraph PROCESS["Protected canonical<br/>processing<br/>One shared writer lock"]
        RESTORE["Verify + restore durable state<br/>scripts/database/<br/>restore_canonical_state.sh · bootstrap_sqlite.py"]
        PROCESSOR["reusable-process-state.yml<br/>Migrate → require matching reviewed README<br/>Selected CLI phases; source stops on denial"]
        GATES{"Publication eligibility + validation<br/>Full or partial with completed searches<br/>429 may qualify; other source/audit denials block<br/>Quality + SQLite integrity + projections"}
        BLOCKED["Blocking failure: no publication<br/>Audit denial; other source denial; no success<br/>Failed quality, integrity, or projection checks"]
        SNAPSHOTS["Create / publish / round-trip verify<br/>database/snapshots.py<br/>scripts/database/canonical_snapshot.py<br/>canonical_state_store.sh"]
        STORE[("Restricted VPS snapshot store<br/>Immutable SQLite + manifests<br/>Verified latest pointer")]
        RESTORE --> PROCESSOR
        PROCESSOR --> GATES
        GATES -->|eligible full or partial; checkpoint| SNAPSHOTS
        GATES -->|reject| BLOCKED
        SNAPSHOTS --> STORE
    end

    subgraph REVIEW["GitHub review handoff<br/>No database or<br/>VPS credentials"]
        HANDOFF["README-only handoff + outcome output<br/>Sanitized exports + aggregate quality report<br/>No SQLite or manifests in artifacts"]
        PR["reusable-readme-pr.yml<br/>README-only pull request<br/>Dispatch and await validation workflows"]
        MERGED["Matching README + full-state seal in main<br/>Full nightly: existing automatic-merge policy<br/>Partial: manual review and merge required"]
        HANDOFF --> PR --> MERGED
    end

    subgraph DEPLOYMENT["Separate manual<br/>deployment<br/>Protected production<br/>environment"]
        DEPLOY["scrape.yml with deployment mode<br/>Restore reviewed state; no source access<br/>Validate → snapshot → upload"]
        ACTIVATE["scripts/deployment/<br/>deploy_canonical_state.sh<br/>activate_canonical_release.sh<br/>Lock + checksums + atomic pointer switch"]
        RELEASE[("Immutable release<br/>SQLite + CSV / JSON + metadata<br/>data/current → releases/run-attempt")]
        SITE["Read-only Next.js readers<br/>site/src/lib/release-path.ts<br/>Old releases retained for in-flight readers"]
        DEPLOY --> ACTIVATE --> RELEASE --> SITE
    end

    NIGHTLY -.-> RESTORE
    MANUAL -.-> RESTORE
    SNAPSHOTS -->|only after verified publication| HANDOFF
    MERGED -.->|required review; does not auto-deploy| DEPLOY
    STORE -->|verified restore| DEPLOY

    click NIGHTLY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/workflows/nightly.yml"
    click MANUAL "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/WORKFLOWS.md"
    click RESTORE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/scripts/database/restore_canonical_state.sh"
    click PROCESSOR "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/workflows/reusable-process-state.yml"
    click GATES "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/workflows/reusable-process-state.yml"
    click BLOCKED "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/docs/maintainers/operations/automation.md"
    click SNAPSHOTS "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/database/snapshots.py"
    click STORE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/scripts/database/canonical_state_store.sh"
    click HANDOFF "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/workflows/reusable-process-state.yml"
    click PR "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/workflows/reusable-readme-pr.yml"
    click MERGED "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/README.md"
    click DEPLOY "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/workflows/scrape.yml"
    click ACTIVATE "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/scripts/deployment"
    click RELEASE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/docs/maintainers/operations/automation.md"
    click SITE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/src/lib/release-path.ts"

    classDef blue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
    classDef amber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
    classDef teal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
    classDef rose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
    classDef indigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
    class NIGHTLY,MANUAL blue
    class RESTORE,PROCESSOR,GATES,SNAPSHOTS,STORE amber
    class BLOCKED rose
    class HANDOFF,PR,MERGED indigo
    class DEPLOY,ACTIVATE rose
    class RELEASE,SITE teal
```

The diagram traces dataset updates and deployment. `canonical-state-drill.yml` reuses the processor for recovery verification without source access; its normal mode publishes a verified snapshot without a README PR. Its one-time seal-adoption mode and its separate README-recovery mode instead propose README-only PRs without snapshot publication or deployment. Verified snapshots, including search-rotation timestamps, are also the normal input to the next update's restore step; that feedback arrow is omitted for readability. An unmerged or rejected partial proposal does not authorize another update: the reviewed-state barrier still stops ordinary mutation and deployment. Snapshot-verification failure prevents the README handoff; scheduling metadata is never restored separately from its database.

## Testing, documentation, and tooling

```mermaid
flowchart TB
    accTitle: Repository foundations — tests, documentation, tooling, and policy
    accDescr: Frozen Python and Bun toolchains support offline test suites, synthetic browser fixtures, and container smoke checks. Documentation is checked and allowlist-staged separately for GitHub Pages. Domain models, utility functions, migrations, public schemas, policies, and contribution controls define the contracts verified by CI. Normal CI performs no LinkedIn collection and never receives canonical production state.

    subgraph TOOLCHAIN["Reproducible<br/>development"]
        PYTHON["Python + uv<br/>pyproject.toml · uv.lock<br/>Ruff · mypy · pytest · Alembic"]
        BUN["Node.js + Bun<br/>site/package.json · bun.lock<br/>TypeScript · ESLint · Prettier · Playwright"]
        DOCKER["CLI + site container targets<br/>Dockerfile · docker-compose.yml<br/>Unprivileged runtime; site data mount read-only"]
        MAKE["Local validation entry points<br/>Makefile · site/package.json"]
        MAKE -.-> PYTHON
        MAKE -.-> BUN
        PYTHON ~~~ BUN ~~~ DOCKER
    end

    subgraph CONTRACTS["Shared contracts<br/>Supporting modules"]
        MODELS["Domain records + enums<br/>src/opportunities/models/<br/>Raw / discovered / stored jobs + searches"]
        UTILS["Small shared utilities<br/>src/opportunities/utils/<br/>Concurrency · atomic files · time · text · URL · logging"]
        SCHEMA["Database + public contracts<br/>migrations/ · alembic.ini<br/>schemas/ · site/src/types/"]
        POLICIES["Project policies + contribution controls<br/>AGENTS.md · CONTRIBUTING.md · SECURITY.md<br/>PRIVACY.md · CODE_OF_CONDUCT.md · LICENSE<br/>.github/ templates · CODEOWNERS · Dependabot"]
        MODELS ~~~ UTILS ~~~ SCHEMA ~~~ POLICIES
    end

    subgraph QUALITY["Offline verification<br/>.github/workflows/"]
        PYTEST["Python tests<br/>tests/unit/ · integration/ · benchmarks/<br/>tests/fixtures/ · conftest.py · shell_helpers.py"]
        FIXTURE["Synthetic SQLite + public exports<br/>scripts/testing/create_site_fixture.py<br/>site/tests/e2e/create-fixture.mjs"]
        SITETEST["Website unit + browser tests<br/>site/tests/unit/ · e2e/<br/>Accessibility · local-state privacy · API contracts"]
        CI["Validation workflows<br/>python-ci.yml · site-ci.yml · docker-ci.yml<br/>CodeQL · Gitleaks · dependency review · Scorecard"]
        FIXTURE --> SITETEST
        PYTEST --> CI
        SITETEST --> CI
    end

    subgraph DOCS["Documentation<br/>and public visuals<br/>Separate publication"]
        GUIDES["User tasks + maintainer handbook<br/>docs/users/ · docs/maintainers/"]
        GENERATED["Registry counts + coverage region<br/>src/opportunities/search_registry_docs.py<br/>scripts/docs/coverage_docs.py"]
        MEDIA["Sanitized public visuals<br/>docs/assets/<br/>site/scripts/record-demo.mjs"]
        DOCSTOOLS["Check links → lint → allowlist-stage → build<br/>scripts/docs/ · mkdocs.yml<br/>documentation.yml · docs-links.yml"]
        PAGES["Public documentation<br/>GitHub Pages; publish only from main"]
        GENERATED --> GUIDES
        GUIDES --> DOCSTOOLS
        MEDIA --> DOCSTOOLS
        DOCSTOOLS --> PAGES
    end

    PYTHON -.-> PYTEST
    BUN -.-> SITETEST
    DOCKER -.->|container smoke + security checks| CI
    MODELS -.-> PYTEST
    UTILS -.-> PYTEST
    SCHEMA -.-> PYTEST
    SCHEMA -.-> SITETEST
    POLICIES -.-> CI
    POLICIES -->|approved public documents only| DOCSTOOLS
    FIXTURE -.->|fixed synthetic demo mode| MEDIA
    PYTEST -->|coverage report input| GENERATED

    click PYTHON "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/pyproject.toml"
    click BUN "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/site/package.json"
    click DOCKER "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/Dockerfile"
    click MAKE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/Makefile"
    click MODELS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/src/opportunities/models"
    click UTILS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/src/opportunities/utils"
    click SCHEMA "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/schemas"
    click POLICIES "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/AGENTS.md"
    click PYTEST "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/tests"
    click FIXTURE "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/scripts/testing/create_site_fixture.py"
    click SITETEST "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/site/tests"
    click CI "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/.github/workflows"
    click GUIDES "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/docs/README.md"
    click GENERATED "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/src/opportunities/search_registry_docs.py"
    click MEDIA "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/docs/assets"
    click DOCSTOOLS "https://github.com/simonesiega/european-tech-opportunities-2027/tree/main/scripts/docs"
    click PAGES "https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/.github/workflows/documentation.yml"

    classDef blue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
    classDef mint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
    classDef amber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
    classDef teal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
    classDef rose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
    classDef indigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
    class PYTHON,BUN,MAKE blue
    class MODELS,UTILS mint
    class SCHEMA,FIXTURE amber
    class PYTEST,SITETEST,CI indigo
    class DOCKER,POLICIES rose
    class GUIDES,GENERATED,MEDIA,DOCSTOOLS,PAGES teal
```

## Rendering profile

The committed assets use Mermaid 11.12.0 and the ELK layout loader 0.1.7. Register the ELK loader before rendering, or use a Mermaid renderer with ELK support. Render the five blocks into `svg/` in order as `repository.svg`, `collection.svg`, `website.svg`, `automation.svg`, and `foundations.svg`. Invisible `~~~` links only control placement; they do not add architectural relationships.

Keep the explicit `<br/>` breaks in group headings: Mermaid's cluster renderer wraps headings more narrowly than ELK's initial label measurement. Short, explicit lines let ELK reserve their full height, preventing headings from overlapping the first component box. After rendering, check group headings against component boxes as well as node and edge labels.

Use this shared configuration, a white SVG background, and system fonts. Retain the accessibility titles/descriptions and HTTPS code links. Do not embed scripts, external resources, or HTML labels in the exported SVGs.

Mermaid's strict mode does not activate `click` directives. For the standalone export, use the explicit node-to-URL mappings in each block to wrap each corresponding node in one native SVG link after rendering. Keep `securityLevel: "strict"`; do not enable JavaScript callbacks or a looser rendering mode to restore links. Each link needs its HTTPS `href`, `target="_blank"`, `rel="noopener noreferrer"`, an accessible name, and `tabindex="0"` for explicit keyboard focus. Separate label lines with spaces in the accessible name. Check for nested anchors, unexpected URLs, scripts, and network requests when opening the exported file.

```json
{
  "layout": "elk",
  "elk": {
    "mergeEdges": false,
    "nodePlacementStrategy": "NETWORK_SIMPLEX"
  },
  "startOnLoad": false,
  "securityLevel": "strict",
  "theme": "base",
  "look": "classic",
  "htmlLabels": false,
  "deterministicIds": true,
  "deterministicIDSeed": "european-tech-opportunities-2027",
  "flowchart": {
    "htmlLabels": false,
    "curve": "linear",
    "nodeSpacing": 35,
    "rankSpacing": 55,
    "padding": 18,
    "wrappingWidth": 340,
    "subGraphTitleMargin": { "top": 8, "bottom": 24 }
  },
  "themeVariables": {
    "fontFamily": "Segoe UI, Arial, sans-serif",
    "fontSize": "18px",
    "background": "#ffffff",
    "primaryColor": "#f8fafc",
    "primaryTextColor": "#0f172a",
    "primaryBorderColor": "#64748b",
    "lineColor": "#475569",
    "clusterBkg": "#f8fafc",
    "clusterBorder": "#cbd5e1",
    "edgeLabelBackground": "#ffffff",
    "tertiaryColor": "#f8fafc"
  },
  "themeCSS": ".cluster rect { rx: 10px; ry: 10px; } .cluster-label text { font-weight: 600; } .node rect { rx: 6px; ry: 6px; } .edgeLabel text { font-size: 15px; } a:hover .label-container, a:focus .label-container { stroke-width: 3px; }"
}
```

### Refresh native link accessibility

After adding native SVG links, run this from the repository root to set their accessible names and keyboard focus from the Mermaid node labels. It requires the existing links to match the source mappings and changes only anchor attributes, not rendered geometry. If labels, relationships, or layout changed, render with Mermaid first; this step alone cannot update the drawing.

```bash
uv run --frozen python - <<'PY'
import html
import re
from pathlib import Path

root = Path("docs/assets/diagram")
blocks = re.findall(r"```mermaid\n(.*?)\n```", (root / "source.md").read_text(encoding="utf-8"), re.S)
names = ("repository", "collection", "website", "automation", "foundations")
outputs = []
for name, block in zip(names, blocks, strict=True):
    links = dict(re.findall(r'click (\w+) "([^"]+)"', block))
    labels = dict(re.findall(r'^\s*(\w+)[\[({]+"([^"\n]+)"', block, re.M))
    seen = []

    def refresh(match):
        tag = match.group()
        node = match.group(1)
        url = html.unescape(re.search(r'\shref\s*=\s*"([^"]+)"', tag).group(1))
        if url != links[node]:
            raise ValueError(f"Unexpected SVG link for {node}: {name}")
        label = labels[node].replace("<br/>", " ")
        seen.append(node)
        tag = re.sub(r'\s(?:aria-label|tabindex)="[^"]*"', "", tag)
        accessible_name = html.escape(label + " — open source on GitHub", quote=True)
        return tag[:-1] + f' tabindex="0" aria-label="{accessible_name}">'

    path = root / "svg" / f"{name}.svg"
    anchor = r'<a\s[^>]*>(?=\s*<g\s[^>]*\bid="flowchart-(\w+)-\d+"[^>]*>)'
    updated = re.sub(anchor, refresh, path.read_text(encoding="utf-8"))
    if sorted(seen) != sorted(links):
        raise ValueError(f"SVG links do not match Mermaid source: {name}")
    outputs.append((path, updated))

for path, updated in outputs:
    path.write_text(updated, encoding="utf-8", newline="\n")
PY
```

Verify all links are reachable with Tab and show a visible focus indicator. Open a link with Enter only when external navigation is intended.
