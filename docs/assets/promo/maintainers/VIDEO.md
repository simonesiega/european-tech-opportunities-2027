# Maintain the promotional video

[← Visual assets](../../README.md) · [Documentation home](../../../README.md) · [Maintainer handbook](../../../maintainers/README.md) · [Documentation maintenance](../../../maintainers/engineering/documentation.md)

Recreate, revise, review, and replace the 51-second promotional film without changing the product or losing approved work. This runbook is primarily for coding agents. It records revision 15, the source requirements, the approved presentation, and the checks required for a future update.

> [!IMPORTANT]
> This asset-only handoff contains the finished MP4, the original MP3, the contact sheet, and this guide. It does **not** contain the editable renderer, capture scripts, player, or captured frames. A clean checkout cannot reproduce the film from these three media files alone. Recover the separate authoring bundle before following the rendering commands; do not invent missing scripts or claim that the older product-tour recorder creates this film.

## Contents

- [Start here](#start-here)
- [Assets and provenance](#assets-and-provenance)
- [Recover and preserve the authoring bundle](#recover-and-preserve-the-authoring-bundle)
- [Recreate the film](#recreate-the-film)
- [Choose the smallest update](#choose-the-smallest-update)
- [Timeline and descriptive transcript](#timeline-and-descriptive-transcript)
- [Appearance and camera](#appearance-and-camera)
- [Real interface state and capture](#real-interface-state-and-capture)
- [Pointer and scroll choreography](#pointer-and-scroll-choreography)
- [Soundtrack](#soundtrack)
- [Verification and review](#verification-and-review)
- [Replace, publish, and roll back](#replace-publish-and-roll-back)
- [Troubleshooting](#troubleshooting)

## Start here

1. Read the root [agent guidelines](../../../../AGENTS.md), [security policy](../../../../SECURITY.md), and [media publication rules](../../README.md#publication-safety). Check for nested agent instructions and relevant local context.
2. Confirm the requested change and the intended worktree with `git worktree list`, `git branch --show-current`, and `git status --short --untracked-files=all`. Do not switch branches, reset files, clean worktrees, restage another person's work, commit, or publish without authorization.
3. Identify whether the task needs only documentation, an audio remux, an editorial re-render, or new interface captures. Use the [update matrix](#choose-the-smallest-update); do not regenerate unrelated inputs.
4. Preserve the approved outputs and source before running anything that overwrites them. Keep the source MP3 input-only. Compare the complete Git index, not just the files being edited.
5. Use only fictional fixture data and the isolated production-built application. No collection commands, LinkedIn requests, production SQLite, credentials, browser profiles, or source-access authorization changes are needed.
6. Stop if source provenance, fixture state, soundtrack rights, or the meaning of the requested behavior is unclear. Technical validation is not permission to change the approved design or publish the recording.

## Assets and provenance

Paths in this table are relative to `docs/assets/promo/`.

| Asset                                                | Purpose                                                           | Revision 15 specification                                                     |
| ---------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| [Main film](../european-tech-opportunities-2027.mp4) | Delivery master with music                                        | 51 seconds; 1920 × 1080; 60 fps; 3,060 frames; 10,386,902 bytes               |
| [Contact sheet](../storyboard.webp)                  | Static, no-motion overview; not an animation or editable timeline | Fourteen sampled frames; 1280 × 2758; 243,474 bytes                           |
| [Original soundtrack](../soundtrack.mp3)             | Unmodified input recording                                        | Approximately 145.68 seconds; MP3; 44.1 kHz stereo; 256 kb/s; 4,661,916 bytes |

Baseline SHA-256 values identify these delivered files, not every possible re-encode:

```text
2dffbca95e0a3348ef50b69e29a3b78d3b2d343a56466d5b5038c2259d71a211  european-tech-opportunities-2027.mp4
1e5c391be1d443f9a31f4cbf09b19784082dd56529cae72c437f36874ad4c4b2  storyboard.webp
b7a0f7ece3aa86d491cec2f2b6d95595b51b8e3897dd8bfe27d140073e7776c9  soundtrack.mp3
```

The master uses H.264 High, level 4.2, `yuv420p`, BT.709, fast-start metadata, and one AAC LC stereo track at 48 kHz with a 192 kb/s target. The encoder uses libx264, `slow`, CRF 18, four threads, and a two-second GOP. Container metadata and chapters are stripped. This is a high-quality film, not the older sub-1-MiB README animation.

The captured application revision is `48ac7135f868e1e82133081c57f64cbd2e7d5a7f`. That is the **application source revision**, not a commit containing the final authoring bundle. The showcase-assets branch was created separately from `main`; rebuilding its current application code may change the interface.

The interface is the real, unmodified production application, captured in Chromium on Windows with 24 fictional listings. The Safari-style browser frame, pointer paths, headlines, and camera movement are illustrated/editorial elements, not native Safari footage or human-recorded pointer input. No stock footage, AI-synthesized scenes, narration, or additional sound effects are used.

Keep this disclosure beside every published copy. The film intentionally has no burned-in demo label. The [transcript below](#timeline-and-descriptive-transcript) and contact sheet supply context and a no-motion alternative; the separate authoring player is not part of this asset-only handoff.

The [root README showcase](../../../../README.md#growing-across-europe) uses a bare GitHub attachment URL for GitHub's native video player. Keep that URL on its own line rather than wrapping it in Markdown link syntax or restoring the repository-relative HTML video element. The adjacent Markdownlint `MD034` exception applies only to that URL. Do not promise autoplay or automatic looping. The documentation site retains the separate MP4 link, transcript, and static overview; preserve those links and the fictional-data/artwork disclosure when editing the showcase.

## Recover and preserve the authoring bundle

### Locate the correct working revision

At this handoff, the editable revision 15 bundle remains under `docs/assets/promo/` in the separate `feat/promotional-video` worktree, conventionally named `european-tech-internships-2027-promotional-video`. Use `git worktree list` to locate it; do not assume a machine-specific absolute path.

The final source is working-tree content, not a published branch snapshot. Its Git index contains an older staged restoration. Checking out that branch elsewhere, using `git show`, or copying only staged files does **not** recover revision 15. Do not reset or restage the original worktree to simplify its status.

A verified local backup also exists at `docs/assets/promo/.work/revisions/distinct-lists-v15/` in that authoring worktree. It contains 26 bundle files, 1,491 capture-directory files, provenance, and review evidence. Earlier revision backups remain there; do not overwrite them. The 1,491-file inventory includes retained captures, not just the frames referenced by the current manifest.

If the worktree or backup is unavailable, ask the maintainer for a reviewed authoring archive. The MP4 and contact sheet cannot recover the exact source, layers, fixture, or choreography. Before retiring the original workstation/worktree, retain a durable, checksum-verified authoring archive or separately reviewed source commit. Record its retrievable location and revision here once one exists; a branch name or local backup alone is not durable distribution.

### Required bundle and ownership

All paths below are relative to the **authoring** `docs/assets/promo/`, not this asset-only checkout. They are code references, not links to nonexistent published files.

| Owner                                                                             | Responsibility                                                                                                               |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `.gitignore`, `package.json`, `bun.lock`                                          | Local-only working directories, pinned dependencies, and command entrypoints                                                 |
| `scripts/common.mjs`                                                              | Workspace paths, loopback origin, fixed clock, subprocess environment, and cache isolation                                   |
| `scripts/prepare.mjs`                                                             | Guarded copy of clean tracked application inputs, isolated dependency installation, fixture generation, and production build |
| `scripts/fixture.py`                                                              | Fictional rows, real migrations, repository writes, and sanitized public exports                                             |
| `scripts/capture.mjs`                                                             | Genuine control interactions, viewport/hover/scroll captures, geometry, state assertions, and manifest                       |
| `scripts/motion.mjs`                                                              | Single timeline: chapters, copy, emphasis, states, clicks, cursor paths, scrolls, camera, closing, and duration              |
| `scripts/film.mjs`                                                                | Canvas composition, font registration, headline layout, browser aperture, cursor, review times, and closing text             |
| `scripts/background.mjs`                                                          | Original static graphite artwork and neutral editorial colors                                                                |
| `scripts/browser-frame.mjs`                                                       | Illustrated Safari-style toolbar, geometry, and centered domain                                                              |
| `scripts/audio.mjs`                                                               | Soundtrack settings, filters, guarded remux, and source/video integrity checks                                               |
| `scripts/render.mjs`                                                              | Stills, contact sheet, poster, draft/master encoding, and soundtrack attachment                                              |
| `scripts/film.test.mjs`, `scripts/audio.test.mjs`                                 | Visual/state/motion and audio regressions                                                                                    |
| `scripts/verify.mjs`                                                              | Full decode, browser playback, player/transcript checks, and generated `validation.json`                                     |
| `index.html`, `README.md`, `STORYBOARD.md`                                        | Local review player, descriptive transcript, source-bundle instructions, and shot list                                       |
| `licenses/Geist-OFL.txt`, `licenses/Space-Grotesk-OFL.txt`                        | Font license notices retained with source                                                                                    |
| `soundtrack.mp3`, master MP4, `poster.webp`, `storyboard.webp`, `validation.json` | Input recording and reviewed/generated outputs                                                                               |
| `.work/captures/`, including `manifest.json`                                      | Reusable real screenshots, hit regions, UI state, and frame selection metadata                                               |
| `.work/source-revision.txt`                                                       | Application commit actually used to prepare the captured UI                                                                  |

Retain the capture manifest and its referenced image files together. Keep the original MP3 and font notices with the archive. Dependencies, the copied app, disposable SQLite, caches, logs, and scratch frames belong only in ignored authoring directories; they must not enter the public docs tree.

Before an edit, take a new, uniquely named backup and hash its files. Save `git ls-files --stage -z` as binary data plus branch, HEAD, and working status. Compare the same NUL-delimited output afterward; omitting `-z` produces a false index mismatch. Never overwrite an earlier approved backup.

## Recreate the film

### Requirements and preflight

Use the [local development toolchain](../../../maintainers/getting-started/setup.md): Node.js 22.13+, Bun, `uv`, Git, and Chromium for the pinned Playwright version. The authoring bundle was tested with Node.js 22.20.0 and Bun 1.3.14 on Windows.

| Authoring dependency        | Pinned version |
| --------------------------- | -------------- |
| `@fontsource/geist`         | `5.3.0`        |
| `@fontsource/space-grotesk` | `5.3.0`        |
| `@napi-rs/canvas`           | `1.0.10`       |
| `@playwright/test`          | `1.63.0`       |
| `ffmpeg-static`             | `5.3.0`        |
| `prettier`                  | `3.9.6`        |

Recover `bun.lock`; do not recreate the dependency graph from this table. Keep the original bundled FFmpeg/font/browser versions for a faithful rebuild. Fresh captures may vary with browser/platform rasterization, and re-encoded MP4 hashes are not a cross-platform reproducibility promise.

Choose the application revision deliberately:

- For a historical reconstruction, retain the recorded application commit and original captures. Re-rendering preserved inputs avoids unintended interface changes.
- For a future product update, use a reviewed, clean target application commit, rebuild its isolated copy, and recapture. Review any changed labels, geometry, fixture APIs, or counts before changing assertions.

The preparation guard checks `site/`, `src/`, `migrations/`, `configs/`, `schemas/`, the root README, `pyproject.toml`, `uv.lock`, `alembic.ini`, and `.python-version` against HEAD. Do not bypass a dirty-input failure or falsely label a dirty build with a clean commit hash.

### Full preparation, capture, and render

Run the following only in a maintainer-approved **authoring checkout with the recovered bundle**, starting at its repository root. These commands are not runnable from the asset-only showcase checkout.

```bash
set -eu
cd docs/assets/promo
test -f scripts/prepare.mjs
test -f scripts/motion.mjs
test -f package.json
test -f bun.lock
test -f soundtrack.mp3
mkdir -p .cache/bun .cache/browsers .work/tmp
export BUN_INSTALL_CACHE_DIR="$PWD/.cache/bun"
export PLAYWRIGHT_BROWSERS_PATH="$PWD/.cache/browsers"
export TMPDIR="$PWD/.work/tmp"
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
bun install --frozen-lockfile
bunx playwright install chromium
node scripts/prepare.mjs
node scripts/capture.mjs
node --test scripts/film.test.mjs scripts/audio.test.mjs
node scripts/render.mjs --stills
node scripts/render.mjs
node scripts/verify.mjs
node node_modules/prettier/bin/prettier.cjs --check scripts package.json index.html README.md STORYBOARD.md
```

Use a POSIX shell or Git Bash on Windows. For PowerShell, enter the recovered promo directory and use this preflight/environment setup instead of the Bash setup:

```powershell
$ErrorActionPreference = 'Stop'
foreach ($file in @('scripts/prepare.mjs', 'scripts/motion.mjs', 'package.json', 'bun.lock', 'soundtrack.mp3')) {
    if (-not (Test-Path -Path $file -PathType Leaf)) {
        throw "Missing required authoring file: $file"
    }
}
New-Item -ItemType Directory -Force .cache/bun, .cache/browsers, .work/tmp | Out-Null
$env:BUN_INSTALL_CACHE_DIR = Join-Path $PWD '.cache/bun'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $PWD '.cache/browsers'
$env:TMPDIR = Join-Path $PWD '.work/tmp'
$env:TMP = $env:TMPDIR
$env:TEMP = $env:TMPDIR
```

Then run the Bun and Node commands above in order. In PowerShell, check `$LASTEXITCODE` after each native command and stop on any nonzero result; `$ErrorActionPreference` alone does not make native commands fail fast in every PowerShell version.

Retain the browser-path variable for capture and verification. Installation may access package/browser registries; capture accesses only loopback. Direct Node entrypoints avoid the previously observed Bun 1.3 Windows script-launcher crash while retaining Bun for dependency management.

The commands have these side effects:

1. Preparation copies tracked inputs, excluding environment files, to `.work/project/`; installs Python under `.work/venv/`; creates `.work/fixture/`; and builds `.work/project/site/`. It does not build the original `site/` or touch canonical SQLite.
2. Fixture generation replaces only its disposable promo database. Stop readers first; SQLite sidecars are a stop condition. Never generalize that deletion to canonical state.
3. Capture starts the isolated app on `http://127.0.0.1:3417`, refuses an occupied port, records screenshots and `.work/captures/manifest.json`, and closes its server/browser. Do not run preparation concurrently with capture.
4. `--stills` overwrites the authoring `poster.webp` and `storyboard.webp` and writes ignored review JPEGs. Inspect these before the full encode.
5. Full rendering overwrites those stills and the master MP4, then attaches music. It is not an atomic replacement of the previous delivery master; keep a backup and work in the authoring workspace.
6. Verification overwrites the authoring `validation.json` after successful checks. Do not hand-edit its success flags, source revision, frame totals, or checksums.

For an editorial-only update with preserved inputs, skip preparation and capture. They are unnecessary and can overwrite approved screenshots.

## Choose the smallest update

| Requested change                                      | Edit in the authoring bundle                                                                                                       | Required regeneration                                                                      |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Headline wording, emphasis, reveal, or reading hold   | `motion.mjs`; matching transcript/shot list and assertions                                                                         | Stills, master, tests, verification; reuse captures if timings and UI state stay unchanged |
| Closing copy, links, or composition                   | `motion.mjs`, `film.mjs`; `browser-frame.mjs` for the address                                                                      | Stills/master; check the actual product repository URL and safe margins                    |
| Cursor destination, curve, click timing, or scrolling | `motion.mjs`, synchronized `capture.mjs` and tests                                                                                 | Recapture affected genuine hover/scroll states, then render and verify                     |
| Saved/applied target or displayed fixture rows        | `fixture.py`, explicit row selectors/state assertions in `capture.mjs`                                                             | Rebuild fixture/app as needed, recapture, render, and verify all downstream views          |
| Product interface update                              | Clean reviewed application revision; then capture selectors/geometry if required                                                   | Prepare, capture, render, and complete review                                              |
| Typography, browser artwork, or background            | `film.mjs`, `motion.mjs`, `browser-frame.mjs`, or `background.mjs`                                                                 | Explicit design approval, visual regressions, stills, master, and review                   |
| Gain or fade only                                     | `audio.mjs`, audio assertions, soundtrack description                                                                              | Audio-only remux, audio tests, verification; preserve encoded video                        |
| Duration or chapter order                             | Timeline plus states, moves, clicks, scrolls, focus, Theme, closing, transcript, review times, tests, and verification assumptions | Recapture where timing/state changes; full render and soundtrack review                    |
| Documentation only                                    | This guide and affected indexes                                                                                                    | Source/rendered docs checks; no media regeneration                                         |

Useful authoring commands:

```bash
node scripts/render.mjs --stills
node scripts/render.mjs --draft
node scripts/render.mjs --audio-only
```

`--draft` writes a 30 fps, CRF 23, `veryfast` review copy to `.work/draft.mp4`; it also regenerates the authoring stills. It is not the delivery master, and the current master verifier expects 60 fps. `--audio-only` replaces the master audio without redrawing stills or video. Combining `--draft --audio-only` targets an existing draft. A normal full render already attaches music; do not remux it again needlessly.

When introducing a new presentation revision, update the report generator and relevant documentation/tests, then generate the report. Do not change revision 15 baseline hashes merely to make a mismatched input appear valid. Keep historical and replacement provenance distinguishable.

## Timeline and descriptive transcript

The table describes the complete visible sequence. Bold text is the emphasized part of each headline. Supporting context is a transcript, **not** a second burned-in caption line.

| Time       | Visible headline or composition     | Genuine action and supporting context                                                                                                                                                    |
| ---------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0–3.6s     | 2027 tech roles. **Across Europe.** | Enter the directory; pointer movement overlaps the initial scroll. The broader product offers validated internships and New Grad roles; the 24 displayed fixture listings are fictional. |
| 3.6–8.2s   | **Search** for your next role.      | Zoom in, arrive directly, and type `engineer`; 24 → 19 total matches. Search covers role, company, and location. Return to wide.                                                         |
| 8.2–11.2s  | Start with a **company** you like.  | Choose Lumen Cloud; 19 → 4 matches.                                                                                                                                                      |
| 11.2–14.2s | Choose **where** to work.           | Select Germany in **Location**; 4 → 3 matches.                                                                                                                                           |
| 14.2–17.5s | Find **your kind of work.**         | Select Software Engineering in **Category**; 3 → 2 matches.                                                                                                                              |
| 17.5–20.5s | **Save** a good find.               | Save the Berlin Software Engineering Intern. The mark stays in this browser; no account is required.                                                                                     |
| 20.5–23.4s | Know where you’ve **applied.**      | Mark the different Munich Graduate Software Engineer applied. This records a local mark; it does not submit an application.                                                              |
| 23.4–27.8s | **New** since your last visit.      | Approach **Reset** directly, clear public filters, and open **New** to show four roles newly seen since the prior browser visit.                                                         |
| 27.8–30.8s | **Saved and applied.** At a glance. | Scroll to the top while approaching the saved count. Open the one-role Saved list, then the different one-role Applied list.                                                             |
| 30.8–34.3s | Your view. **Light or dark.**       | Move directly to Theme and switch to dark mode. Applied stays selected.                                                                                                                  |
| 34.3–41.4s | **Open data.** Ready to build with. | Zoom into CSV/JSON, hover each, return to wide, scroll down, and hover Public API. No completed download or API interaction is fabricated.                                               |
| 41.4–51s   | Smaller browser and closing copy    | Return to the top while the pointer exits, recede, and reveal the four closing lines. Hold the completed composition for 3.1 seconds. Applied remains selected.                          |

The source player also carries “Hundreds of validated internships and New Grad roles,” “Updated daily,” and “Free CSV, JSON, and public API access.” These describe the product, not fixture counts or real-time collection. Recheck claims against reviewed public evidence and the current documented schedule before a future release. Do not collect live source data for a video or invent counts to support a claim.

The approved closing copy is:

1. `European Tech Opportunities 2027`
2. `Your next role starts here.`
3. `techopportunities.eu`
4. `github.com/simonesiega/european-tech-opportunities-2027`

Check the repository address against `site/src/lib/project-links.ts` in the application revision being captured. The closing must finish on the product, not black.

## Appearance and camera

### Editorial design

- Keep the static, original graphite-fold artwork. Do not replace it with stock imagery, an enlarged thumbnail, animated lighting, random texture, particles, flares, or perspective effects.
- Use mixed-case, single-line 56 px headlines centered at x = 960 with baseline y = 112. Neutral text uses Geist 400, tracking −0.8, and `#c8c8ce`; emphasis uses Space Grotesk Medium 500, tracking −0.9, and `#ffffff`.
- Keep the 1 px emphasis underline at y = 130, white at 30% opacity. The headline clip is x = 240, y = 46, width = 1440, height = 96.
- Reveal each word over 360 ms with 40 ms staggering, an 11 px masked rise, and scale 0.985 → 1. Exit over 300 ms. The underline grows from chapter start + 0.22s to + 0.82s. After entry, every headline pixel stays still until exit; there is no reading-phase drift.
- Keep the restored “Saved and applied. At a glance.” headline. Do not revive the superseded caption-free version, green emphasis, uppercase keyword stacks, bottom feature captions, or editorial corner labels.
- Retain the original illustrated Safari-style single-tab toolbar and centered domain. Its design width is 1728 px, toolbar height 60 px, and centered address-field width 760 px. It is artwork, not an Apple affiliation or native-capture claim.

The baseline background RGBA SHA-256 is `e3c31dee88af5e2c00fce7cb42097314f808eed086cc1b3c01da4cf11eb0a431`. It belongs to uncompressed artwork pixels, not the encoded video file. Do not update that regression hash without an intentional design change.

### Browser and focus geometry

Camera keys are `[time in seconds, browser width, top y]`, centered horizontally in the 1920 × 1080 canvas:

```text
[0,     1728, 212]
[1.3,   1728, 212]
[2.9,   1856, 184]
[41.62, 1856, 184]
[44.08, 1440,  64]
[51,    1440,  64]
```

The main browser leaves 32 px of background at each side and at least 58 px below. The final aperture is x = 240, y = 64, width = 1440, height = 650, with a 50 px toolbar.

| Close-up | Start → settled | Release → wide | Scale | Viewport anchor |
| -------- | --------------- | -------------- | ----- | --------------- |
| Search   | 2.95 → 3.95s    | 7.06 → 7.96s   | 1.55× | `[0, 250]`      |
| CSV/JSON | 33.92 → 34.7s   | 37.14 → 38.05s | 1.48× | `[1440, 132]`   |

Scale the page, toolbar, pointer, and hit geometry uniformly inside the rounded browser aperture. Keep the artwork/headline fixed, targets visible, source scale at or below 2×, and camera stationary during clicks. `frameAt()` owns the aperture; `panelAt()` applies focus; `projectPoint()` maps CSS viewport coordinates to screen pixels. Never stretch or redraw the website to fit a close-up.

### Theme and closing

The website/toolbar Theme dissolve is 32.805–33.085s, exactly 280 ms. Background colors and result state do not change. Never use a dissolve to hide a scroll jump or replace one result set with another.

| Closing element              | Reveal interval |
| ---------------------------- | --------------- |
| Project name                 | 44.25–44.9s     |
| Closing sentence             | 44.82–45.6s     |
| Website                      | 45.72–46.52s    |
| Website underline            | 45.95–46.85s    |
| Repository address and arrow | 46.72–47.9s     |
| Completed composition        | Hold 47.9–51s   |

Keep the existing neutral closing colors and gentler masked rises. Do not recolor the ending when changing headline emphasis.

## Real interface state and capture

Capture uses a fresh Chromium context at 1440 × 600 CSS pixels, device scale 2, producing 2880 × 1200 screenshots. Set locale `en-GB`, timezone UTC, light theme initially, reduced motion for the source UI, and blocked service workers.

The fixed clock is `2026-10-02T12:00:00.000Z`; the previous browser visit is `2026-10-01T12:00:00.000Z`. Seed `opportunities-directory-state` with version 1, that `lastVisitAt`, and empty `saved`, `applied`, and `hidden` arrays. Set `opportunities-theme` to `light`. Use disposable browser-local state only; never read a person's real saved/applied lists.

The fixture owner creates 24 invented rows with numeric IDs `1000000001` through `1000000024` through real Alembic migrations and `Repository` methods, then generates/validates CSV and JSON through the real exporter. Preserve its row order, dates, categories, employment types, and the fictional Lumen Cloud Brussels role when reproducing the baseline. That company membership enables the real 19 → 4 → 3 → 2 filter progression.

| Local mark | Explicit ID  | Company     | Role and location                             | Expected state            |
| ---------- | ------------ | ----------- | --------------------------------------------- | ------------------------- |
| Saved      | `1000000001` | Lumen Cloud | Software Engineering Intern — Berlin, Germany | Saved true; applied false |
| Applied    | `1000000006` | Lumen Cloud | Graduate Software Engineer — Munich, Germany  | Saved false; applied true |

Use explicit row-action locators, not `.first()` for both actions:

```javascript
page.locator('[data-local-id="1000000001"][data-local-action=saved]');
page.locator('[data-local-id="1000000006"][data-local-action=applied]');
```

Find the numbered buttons by accessible names matching `/^View \d+ saved opportunities$/` and `/^View \d+ applied opportunities$/`. Assert their pressed state, count, row IDs, titles, locations, and local marks. The capture manifest measures row data from the actual table; if the column layout changes, update extraction against the product implementation, not guessed cell positions.

The required progression is Search → Company → Location → Category → Save → Applied → Reset → New → Saved count → Applied count → Theme → Open data. Search has 19 total matches, not necessarily 19 visible rows: the default page contains ten rows. New contains four; each local list contains one **different** role. Applied remains selected through Theme, exports, the ending, and any generated poster. Do not hover, click, or secretly restore **View all opportunities** between the counts and Theme or afterward.

Native selectors use real clicks and keyboard type-ahead; browser-owned popup menus are not fabricated. Capture real focused, pressed, hover, and selected states. The export/API endpoints are checked for local HTTP 200 separately; the film only hovers their links.

`common.mjs` removes inherited `OPPORTUNITIES_` and `LINKEDIN_` variables, redirects fixture/cache paths, and sets the loopback site URL. Browser routing allows only GET/HEAD to the loopback origin. Assert no blocked external requests or page errors and an unchanged fixture database checksum after capture. Keep these guards rather than solving a failure by enabling external requests or weakening policy.

## Pointer and scroll choreography

### Motion rules

Use deterministic, individually shaped cubic curves, varied off-center landings, 65–150 ms decision pauses, and 65–90 ms presses. Retain human-like slower approaches without random jitter. Only Company and CSV have joined landing corrections; Search and Reset do not.

- Search travels from 4.08–4.73s to `[270.8, 252.5]`, with handles `[0.29, 0.78]`, arc `[-4, 1.5]`, and tempo `[0.16, -0.08]`. It arrives without overshoot/reversal. Click 4.83–4.905s; begin typing at 5.13s and finish `engineer` at 6.2s. Keep the landing still until typing starts.
- Save responds at 18.96s. Hold until 21.225s, then move directly to the second row's Applied control at `[1343.7, 438.35]`, arriving at 21.585s. Applied responds at 21.78s.
- Approach Reset directly from 23.755–24.34s and click at 24.455s. No loop, orbit, or intermediate parking stop. Open New at 26.27–26.35s.
- Approach Saved count from 27.82–29.22s; click at 29.33–29.405s. Approach Applied count from 29.75–30.29s; click at 30.4–30.475s.
- Move from Applied count directly to Theme from 30.72–32.64s; click at 32.73–32.805s. Do not insert an empty midpoint stop or View all detour.
- Approach CSV from 34.8–35.55s, JSON from 36.2–36.82s, and Public API from 37.46–39.83s. Exit from 40.83–43.56s while returning to the top.

Arrow, I-beam, and hand shapes follow measured real hit regions. CSS viewport coordinates must be projected through the same camera transform as the page. Keep 1.6–2.64-second main result holds, approximately 1.47 seconds after New before approaching counts, and 0.64–1-second data-link hovers; reading pauses are not slow mouse presses.

The easing function is clamped quintic smoothstep, `t³ × (t × (6t − 15) + 10)`. Joined correction curves use cumulative arc length, 100 samples per cubic, and continuous tangent directions. Preserve speed regressions below 2,000 viewport px/s and 2,800 screen px/s. Always await asynchronous `film.draw()` before reading pixels or encoding a frame.

### Combined pointer and scroll captures

There are 12 standalone recorded approaches with 551 hover frames and four combined sequences with 544 frames. Standalone move captures do not replace simultaneous page/hover changes during scrolls.

| Sequence     | Actual scroll | Combined capture interval | Page offset          | Frames |
| ------------ | ------------- | ------------------------- | -------------------- | ------ |
| `to-filters` | 2.2–2.9s      | 0.4–2.9s                  | 0 → 64 px            | 151    |
| `to-counts`  | 27.9–28.6s    | 27.82–29.22s              | 64 → 0 px            | 85     |
| `to-api`     | 38.12–39.22s  | 37.46–39.83s              | 0 → document maximum | 143    |
| `to-hero`    | 41.48–42.68s  | 40.83–43.56s              | Document maximum → 0 | 165    |

`SCROLLS.start/end` delimit page movement; `capture` includes pointer lead-in and follow-through. At each sample, scroll to the timeline-derived offset, move the real browser pointer, wait two animation frames, measure geometry, and capture the viewport. Record file, time, pointer, scroll offset, fixed-header position, and hit regions. Assert browser-local state is unchanged throughout.

`imageAt()` must prioritize the combined sequence over standalone pointer frames for its full capture interval. Otherwise a static-page hover screenshot can overwrite a scrolling frame and create a jump. Keep the pointer moving during every actual scroll, not move–park–scroll–resume.

Finish the upward scroll **before** opening the one-row lists. In the baseline, selecting a short list at scroll 64 clamped the page to scroll 14 and moved the count target; scrolling to zero first prevents this. Measure future document geometry rather than hiding clamping with a dissolve or cursor teleport.

## Soundtrack

Use the first 51 seconds of the supplied MP3 without looping or speed changes. Keep −3 dB gain, a 0.5-second fade-in, a four-second half-sine fade at 46.75–50.75s, and 0.25 seconds of silence before the cut. No additional narration or effects.

The exact baseline filter is:

```text
atrim=start=0:end=51,asetpts=PTS-STARTPTS,volume=-3dB,afade=t=in:st=0:d=0.5,afade=t=out:st=46.75:d=4:curve=hsin
```

The fade start is derived as `DURATION - fadeOutSeconds - endSilenceSeconds`. If duration changes, review the new musical ending instead of keeping hard-coded timestamps or cutting an audible waveform.

`addSoundtrack()` rejects the source MP3 as an output, hashes the MP3 and encoded H.264 stream, writes to an ignored temporary MP4, maps only `0:v:0` and `1:a:0`, copies video with `-c:v copy`, and encodes AAC. It verifies source/video integrity before replacing the destination and cleans its temporary directory. Reapplying it replaces audio rather than stacking tracks. Do not overwrite, normalize, trim, or delete the original MP3.

Revision 15 measured mean volume −16.3 dBFS and peak −2.3 dBFS. The verifier requires audible audio with at least 1 dB of peak headroom; the tail test requires progressive decay and silence before the final frame. Browser audio decoding and automated level checks are not a listening review.

The repository's [MIT license](../../../../LICENSE) does **not** grant rights to this supplied recording. No soundtrack license accompanied the original file. Confirm rights for distribution of both the scored MP4 and original MP3 before publication. Keep the source bundle's SIL Open Font License notices when retaining or sharing the renderer/fonts.

## Verification and review

### Authoring gates

1. Run `node --test scripts/film.test.mjs scripts/audio.test.mjs` in the recovered bundle. Revision 15 had 46 visual and four audio tests. Preserve their behavior contracts, not an arbitrary test count.
2. Regenerate the master and run `node scripts/verify.mjs`. Require complete audio/video decode, 3,060 frames at 60 fps, the expected dimensions/codec, fast-start, exactly one audio track, audible levels/headroom, and successful full browser playback.
3. Check the authoring player has native playback and volume controls, no autoplay, correct chapter seeks/transcript/links, no mobile overflow at 390 px, and no external browser requests or page errors. Do not claim these player checks ran from this asset-only checkout; its `index.html` is intentionally absent.
4. Assert the real filter counts, distinct Saved/Applied rows, browser-local marks, unchanged fixture checksum, no View all detour, persistent Applied view, real hit targets, and fixed header.
5. Inspect all-frame aperture bounds, focus targets, click-time camera stability, cursor velocity, simultaneous scroll/pointer samples, headline margins/contrast/static reading holds, and the identical settled ending. Keep source-state assertions even if the encoded result looks plausible.
6. Compare preserved inputs against the prior approved revision. For audio-only work, prove encoded video bytes/packets are unchanged. For visual-only work, compare source MP3 and expected audio packets/timestamps; do not confuse full-MP4, video-stream, audio-stream, and uncompressed-artwork hashes.
7. Review text from the **encoded** MP4, not only canvas output. Revision 15's optional Windows OCR review recognized 26 headline, closing, control, and distinct-role phrases. OCR is extra evidence, not a portable build prerequisite or a substitute for viewing.
8. Watch the full film with sound, inspect the contact sheet, and obtain human review of pacing, legibility, truthful states, and the final music fade. Do not claim human artistic/listening approval from automated checks.

The contact sheet samples `2, 6.8, 10.75, 13.6, 16.8, 19.65, 22.7, 27.45, 29.65, 30.65, 33.9, 37.1, 40.4, 49` seconds. The authoring poster uses `DURATION - 2`, currently 49s. For encoded review, inspect the different list rows at 29.65s and 30.65s and the native count text at 32.1s, after the pointer has moved away.

### Asset-only and documentation gates

From the showcase repository root, media can be independently hashed without the renderer:

```bash
uv run --frozen python - <<'PY'
from hashlib import sha256
from pathlib import Path

root = Path("docs/assets/promo")
for name in ("european-tech-opportunities-2027.mp4", "storyboard.webp", "soundtrack.mp3"):
    data = (root / name).read_bytes()
    print(name, len(data), sha256(data).hexdigest())
PY
```

With FFmpeg available, a standalone full-decode smoke check is:

```bash
ffmpeg -hide_banner -v error -xerror \
  -i docs/assets/promo/european-tech-opportunities-2027.mp4 -f null -
```

This does not replace the authoring state, choreography, or player tests. For changed publication docs or media, run from the showcase repository root:

```bash
uv run --frozen pytest tests/unit/test_docs_site.py tests/unit/test_docs_lint.py -q
uv run --frozen python scripts/docs/check_docs.py
uv run --frozen python scripts/docs/lint_docs.py
uv run --frozen --group docs python scripts/docs/build_docs.py
uv run --frozen --group docs python scripts/docs/check_built_docs.py
git diff --check
```

The lint command requires Docker and its pinned images; retain its read-only/no-network container options. If a dependency/tool is unavailable, report that limitation instead of claiming the check passed. Source checks validate local links and heading anchors; the strict build and rendered checker validate the published paths, media links, anchors, and public-file boundary. They do not guarantee every external website remains reachable; [documentation maintenance](../../../maintainers/engineering/documentation.md#source-and-rendered-checks) explains the separate external-link workflow.

## Replace, publish, and roll back

1. Render and approve in the separate authoring workspace. Back up the previous MP4/contact sheet and review evidence before replacing delivery files; never use the publication directory as a scratch renderer workspace.
2. Copy only the reviewed master and regenerated contact sheet into their stable paths. Copy `soundtrack.mp3` only when initially transferring the unchanged source or when an explicitly approved, licensed replacement is intended. Verify source/destination SHA-256 values after copying.
3. Keep authoring source, lockfile, font notices, captures/manifest, application revision, validation report, and approval evidence together in the separate durable archive. Record the new presentation revision and intentional changes. Do not publish runtime data or `.work/` backups.
4. Update this guide's current specifications, transcript, baseline hashes, and provenance when the approved master changes. Update the [asset catalog](../../README.md), [documentation router](../../../README.md), [maintainer index](../../../maintainers/README.md), and MkDocs navigation if paths or guide ownership change. Preserve existing filenames unless migration is intentional.
5. Keep a descriptive transcript, fictional-data/artwork disclosure, and no-motion contact sheet next to the film. Use ordinary playback controls if embedding it later; do not add autoplay, tracking, or links to the absent authoring player/poster.
6. Confirm recording distribution rights and run the source/rendered documentation gates. The docs publisher permits this exact `docs/assets/promo/soundtrack.mp3`; it does not permit arbitrary audio files, source scripts, HTML players, lockfiles, or working directories. Do not broaden the public boundary to publish the authoring bundle.
7. Review `git status --short --untracked-files=all`, `git diff --check`, and the full diff; verify the original authoring worktree and index remain unchanged. Stage only explicitly approved files, and commit or publish only when authorized.
8. To roll back, restore the last approved media pair and matching documentation/provenance from the verified archive in the publication worktree, then rerun checks. Do not use a broad Git reset/clean or delete any canonical state.

For a handoff, state the source and presentation revisions, changed/unchanged assets, actual commands/results, hash verification, remaining limitations, and whether any staging, commit, or publication occurred. Preserve the original MP3 and earlier reviewed revisions.

## Troubleshooting

| Symptom                                                              | Correct response                                                                                                                                                                                                              |
| -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/motion.mjs`, `package.json`, or capture manifest is missing | This may be the asset-only checkout. Recover the reviewed authoring bundle; do not substitute the older 25-second recorder or reconstruct fake interface frames.                                                              |
| Checking out `feat/promotional-video` does not yield revision 15     | The final source was working-tree content with an older staged index. Obtain the working-tree archive/backup, not a staged or HEAD-only export.                                                                               |
| Preparation refuses dirty application inputs                         | Stop and identify the intended reviewed source revision. Do not disable the provenance guard or overwrite another agent's edits.                                                                                              |
| Port 3417 is occupied                                                | Identify the process and stop only your own fixture server. Do not attach to an unrelated service or kill an unknown process.                                                                                                 |
| Fixture sidecars exist                                               | Close the isolated server/readers before rebuilding the disposable fixture. Do not apply deletion advice to canonical databases.                                                                                              |
| Bun's Windows script launcher crashes                                | Keep frozen Bun dependencies and use the direct Node entrypoints above. Do not upgrade the toolchain as an unrelated fix.                                                                                                     |
| Chromium is missing                                                  | Install the pinned browser with `bunx playwright install chromium`; use the same `PLAYWRIGHT_BROWSERS_PATH` afterward.                                                                                                        |
| Pointer lands on the wrong control after a UI update                 | Recapture measured geometry and inspect the actual accessible labels/row IDs. Update choreography and regression tests together; never paint false feedback.                                                                  |
| Count click jumps the viewport                                       | Finish the scroll to zero before opening a shorter list. Preserve combined captures and inspect document height/clamping.                                                                                                     |
| Scrolling briefly freezes or jumps                                   | Check `imageAt()` priority and full `SCROLLS.capture` intervals. Do not overlay a static-page hover frame during scrolling.                                                                                                   |
| Both local lists show the same role                                  | Check explicit IDs and genuine local state. Saved must be Berlin ID `1000000001`; Applied must be Munich ID `1000000006` unless a new fixture is explicitly approved.                                                         |
| Render hangs or exhausts memory                                      | Check encoder failure handling, await `film.draw()`, and retain the six-image decoded-image LRU rather than loading all Retina captures.                                                                                      |
| Soundtrack ends abruptly or gains another audio track                | Recheck the derived half-sine fade and explicit stream maps. Use the guarded audio owner, leave the MP3 untouched, and listen to the ending.                                                                                  |
| Docs build rejects promo contents                                    | Build from the asset-only publication checkout. Do not copy `.work/`, dependencies, source scripts, player, or lockfile into its docs tree. Only the specifically cataloged MP3 is exempt from the visual-format restriction. |
| Links pass locally but fail after publishing                         | Run the strict staged build and rendered-link checker; use repository-relative links, include the new guide in navigation, and avoid links to authoring-only files.                                                           |
