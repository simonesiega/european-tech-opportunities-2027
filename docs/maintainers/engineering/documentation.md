# Documentation maintenance

[← Maintainer handbook](../README.md) · [Testing](testing.md) · [Visual assets](../../assets/README.md) · [Repository maps](../../assets/diagram/README.md)

Keep each topic with its canonical owner, use the shared style below, and validate both repository links and the published site. User tasks and maintainer procedures share formatting, not assumed technical knowledge.

## One concept, one owner

- Root `README.md`: product showcase and renderer-owned public counts, review seal, and listing preview. Keep detailed procedures in the guides.
- `docs/README.md`: documentation router for both audiences, repository references, and visual maps.
- `docs/users/README.md`: user router; `browsing/` owns directory use, browser lists, and help; `data/` owns downloads and API usage. No CLI setup or production operations.
- `docs/maintainers/README.md`: maintainer router; `getting-started/` owns setup and configuration; `engineering/` owns architecture, classification, search definitions, website development, testing, and documentation; `operations/` owns the CLI, automation, database lifecycle, deployment, and recovery.
- Root policy files: canonical contribution/security/privacy/community/license text. Link rather than duplicate.
- Root `AGENTS.md`: coding-agent entry point and safety constraints, with links into this handbook.
- `docs/assets/`: the asset catalog, sanitized visuals, and editable diagram sources; never browser profiles or raw recordings.
- `.github/WORKFLOWS.md` and `scripts/SCRIPT.md`: source-adjacent inventories. Detailed operational procedures remain in the handbook.

Link to the owner rather than copying procedures. Update `docs/README.md`, the relevant audience index, `mkdocs.yml`, and inbound references when adding or moving a public guide. The workflow and script inventories remain GitHub-only: link to their source on GitHub from published docs rather than broadening the staging allowlist to include implementation files. `scripts/docs/build_docs.py` creates redirects for former `docs/guides/` pages and flat `docs/maintainers/` and `docs/users/` guide URLs. Keep every destination pointed directly at its current topic page, not another redirect. Old section anchors may no longer apply.

## Shared writing style

| Element | Convention |
|---|---|
| Title | One short, sentence-case H1; use a task title for instructions and a topic title for references |
| Navigation | Put a back link immediately below the title, then a few related guides separated by `·` |
| Introduction | State the reader's goal, scope, and important boundary before detailed steps |
| Headings | Use sentence case and sequential levels; long references and runbooks get a Contents list |
| Procedures | Use numbered steps for ordered actions and bullets for independent checks; indent nested code blocks by four spaces for GitHub and MkDocs |
| Tables | Use descriptive headers and concise cells; fragments do not need final periods |
| Terminology | Use GitHub, LinkedIn, SQLite, Next.js, Node.js, and README; preserve exact code names |
| Product labels | Bold exact UI labels such as **Employment type**, **Internship**, and **New Grad** |
| Code and paths | Use inline code for identifiers, paths, variables, and literal values; label fenced code blocks |
| Commands | Assume the repository root and a POSIX shell unless stated otherwise; show directory changes and platform alternatives |
| Prose | Use direct language, active voice, and consistent serial commas; avoid repeated project-name introductions |
| Links and images | Use descriptive link text and meaningful alt text; prefer Markdown over layout-only HTML |
| Callouts | Use GitHub `NOTE`, `IMPORTANT`, or `WARNING` alerts sparingly for context, requirements, or risks |

User guides explain visible tasks, expected results, and recovery choices without requiring implementation knowledge. API and dataset references may include technical examples, but must not require the collection toolchain. Maintainer guides name owners, preconditions, side effects, verification steps, and stop conditions; link to user guides for public behavior instead of repeating them.

Root policies retain their authoritative wording and the contribution template retains its form structure. Agent instructions remain a technical entry point. Do not reformat generated regions, code examples, legal text, or exact UI labels merely to make them resemble prose.

## Diagrams and media

The [repository maps](../../assets/diagram/README.md) are five complementary views, not one exhaustive graph. Edit [source.md](../../assets/diagram/source.md), keep explicit group-heading line breaks, and regenerate into `docs/assets/diagram/svg/` using its rendering profile. Preserve accessibility descriptions, keyboard-usable links, and clear spacing between headings, boxes, and edge labels.

The [asset catalog](../../assets/README.md) distinguishes checked-in visuals from reproduction recipes. Do not link to missing recordings or describe planned media as already published. Add a new asset to the catalog and navigation only after it exists and has been reviewed.

## Generated-content boundaries

| Content | Owner | Update / validate |
|---|---|---|
| README count, seal, and preview regions | `src/opportunities/readme.py` | `opportunities render` / `opportunities validate`, with representative reviewed state only |
| Registry layout counts | `src/opportunities/search_registry_docs.py` | Same commands, from configured YAML |
| Public CSV/JSON and dataset metadata | `src/opportunities/public_exports.py` | `opportunities export-public` / `opportunities validate` |
| Coverage region in `testing.md` | `scripts/docs/coverage_docs.py` | `make coverage`; CI uses `--check` |
| Five repository-map SVGs | `docs/assets/diagram/source.md` | Regenerate using the shared profile; validate layout, links, and accessibility |
| Product tour outputs, when generated | `site/scripts/record-demo.mjs` | [Media reproduction](../../assets/README.md#reproduce-safely) |

Never manually change generated counts, dates, rows, seals, export bytes, or coverage values. Do not reproduce complete generated marker pairs in examples. The README's existing published regions can be moved **unchanged** during a layout refactor; no production database is needed. Never render the committed preview from an empty local database.

## Source and rendered checks

```bash
uv run python scripts/docs/check_docs.py
uv run --frozen python scripts/docs/lint_docs.py
uv run --frozen --group docs python scripts/docs/build_docs.py
uv run --frozen --group docs python scripts/docs/check_built_docs.py
git diff --check
```

`make docs-site` wraps these checks. Source validation covers maintained root Markdown, agent guidance, workflow/script inventories, Markdown templates, and docs, including diagram sources, image links, and heading anchors. Rendered validation checks anchors, local links, image/video references, and the public-file boundary. The scheduled Lychee workflow separately checks external URLs; expired/blocked numeric source listing URLs are excluded, not fetched during ordinary tests.

Markdownlint and Vale run from digest-pinned containers with read-only mounts and no networking. The existing exceptions in `.markdownlint-cli2.jsonc` are scoped to deliberate formatting: unwrapped prose, compact tables, generated HTML, compact agent instructions, and the title-free pull-request template. Do not weaken checks to silence a real failure. Vale checks canonical names and standalone directory labels, not third-party job-title spelling; generated regions and code are excluded.

## Publishing boundary

The build stages only public Markdown, approved root policies, and visual asset formats in a temporary directory. **Never set MkDocs `docs_dir` to the repository root**: it contains private runtime state. Symlinks and unexpected files fail the build. The website favicon is copied verbatim; GitHub alerts are translated only in staged Markdown. Build output under `build/docs-site/` is ignored.

The documentation workflow strictly builds and validates pull requests but deploys only from `main`. It has no canonical-state access. [Automation](../operations/automation.md#validation-workflows) owns GitHub Pages/DNS setup, permissions, and artifact publication. No repository setting is changed by the build script.

## Visual review

Preview changed pages at approximately 830px content width in light and dark GitHub-like surroundings, then check the built documentation on desktop and mobile. Inspect diagrams at preview and full size for clipped labels, group-heading overlaps, arrows, and readable text. When publishing a tour, play the complete MP4, inspect animation duration/dimensions/size, and check the poster/animation link. Use the real production-built application with deterministic synthetic data, loopback-only requests, and a fresh browser context. Never record production lists, cookies, profiles, or database state.
