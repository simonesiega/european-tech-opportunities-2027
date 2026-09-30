# Visual assets

[← Documentation home](../README.md) · [Documentation maintenance](../maintainers/engineering/documentation.md) · [Repository maps](diagram/README.md)

Keep public visuals small, accessible, and separate from runtime data. The catalog below lists the checked-in assets; the product-tour section is a reproduction recipe, not a link to an existing recording.

## Current assets

| Asset | Purpose |
|---|---|
| [Repository maps](diagram/README.md) | Five annotated subsystem diagrams with links to implementation |
| [Diagram source](diagram/source.md) | Editable Mermaid blocks and the shared rendering profile |
| [Public listing example](listings/Amazon_example.webp) | Sanitized discovery example, not evidence of acceptance |
| [Project identity](logo/Opportunities.webp) | Current project logo |
| [Earlier internship identity](logo/Intern.webp) | Historical logo retained for reference |
| [Light preview](sites/White_theme.webp) · [Dark preview](sites/Dark_theme.webp) | Historical website captures, not a guarantee of the current interface |

## Repository maps

The [diagram guide](diagram/README.md) explains the repository, collection/lifecycle, website/publication, automation/deployment, and foundations views. Rendered files live under `diagram/svg/`; [Mermaid source](diagram/source.md) owns their labels, relationships, styling, and regeneration settings.

Edit the source, regenerate the affected SVGs, and check labels, group-heading clearance, code links, and accessibility metadata. Keep the SVGs self-contained: no scripts, embedded HTML, external resources, or private data. These detailed maps support the handbook; product-showcase media has separate ownership.

## Reproduce the product tour

> [!NOTE]
> The MP4, animated WebP, and poster are not currently checked in. The recipe below produces `demo/directory-tour.mp4`, `demo/directory-tour.webp`, and `demo/poster.webp`. Add playback links or embeds only after the files exist and pass review.

The recorder uses the **real, production-built application**, not a mockup. All 12 listings and browser choices are synthetic. No live collection, production database, authenticated browser profile, or external browser request is used. The caption and synthetic-data label are recording overlays, not product features. The planned 25-second tour has no audio.

| Time | Demonstrated action / caption |
|---|---|
| 0–3s | Find your next tech role in Europe |
| 3–6s | Type a role search |
| 6–9s | Filter by company to narrow the result set |
| 9–14s | Save a role and open the private shortlist |
| 14–17s | Mark the shortlisted role applied |
| 17–21s | Reset public filters and view roles new since the previous visit |
| 21–25s | Switch to dark mode; visit techopportunities.eu |

When publishing the tour, link the lightweight animation to the MP4 and offer the poster and transcript as no-motion alternatives. The MP4 supports normal playback controls when opened in a browser or the GitHub media viewer.

### Reproduce safely

Install the [local development toolchain](../maintainers/getting-started/setup.md), then:

```bash
uv sync --frozen --dev
cd site
bun install --frozen-lockfile
bunx playwright install chromium
bun run build
node scripts/record-demo.mjs
cd ..
```

The recorder creates fixed-clock synthetic SQLite through real Alembic migrations and `Repository` methods, then produces downloads through the real Python exporter. Fixture data lives only in ignored `site/tests/e2e/.tmp/demo/`. It starts the standalone app on loopback port 3200 with explicit synthetic paths, clears release-root overrides, disables production analytics with a loopback origin, and blocks every off-origin browser request. Close any fixture readers before regeneration. Browser context and server are closed afterward.

Raw video, timeline, screenshots, and diagnostics stay in ignored `quality-reports/demo/`. Do not commit that folder. The normal E2E fixture uses the same generator, but relative timestamps so request-time recency tests stay meaningful.

With FFmpeg 7.1 (libx264 and libwebp support), from the repository root:

```bash
mkdir -p docs/assets/demo
ffmpeg -y -sseof -26 -i quality-reports/demo/directory-tour-raw.webm \
  -t 25 -vf 'fps=20,scale=1280:720:flags=lanczos' \
  -c:v libx264 -crf 25 -preset slow -pix_fmt yuv420p \
  -movflags +faststart -an -map_metadata -1 docs/assets/demo/directory-tour.mp4
ffmpeg -y -i docs/assets/demo/directory-tour.mp4 \
  -vf 'fps=8,scale=960:540:flags=lanczos' -c:v libwebp_anim \
  -quality 65 -compression_level 6 -loop 0 -an -map_metadata -1 \
  docs/assets/demo/directory-tour.webp
ffmpeg -y -i quality-reports/demo/poster.png -vf 'scale=1280:720:flags=lanczos' \
  -c:v libwebp -quality 82 -map_metadata -1 docs/assets/demo/poster.webp
```

Trim the short browser-startup lead-in; the scripted journey holds for 26 seconds. Check the beginning/end after every re-recording. The final files remove creation metadata and include no audio. Target budgets: MP4 <1 MiB, animated WebP <1 MiB, poster <100 KiB. Inspect the complete playback, text readability at README width, crop, clicks, duration, and final call to action before replacement. Validate docs links after encoding.

## Publication safety

All new product captures must use synthetic data and a fresh browser context. Never add cookies, authenticated HTML, résumés, private environment details, or production snapshots. Prefer compressed final media over raw recordings.
