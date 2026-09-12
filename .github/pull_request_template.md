## Summary

<!-- What changed, why was the previous behavior insufficient, and what is intentionally out of scope? -->

## Related issue

<!-- Use “Closes #123”, link the issue, or write “Not applicable” for a small self-contained change. -->

## Scope and safety

<!-- Describe lifecycle, canonical-state, source-access, privacy, security, and compatibility implications. State “No impact” where appropriate. -->

## Validation

<!-- List the exact commands/checks you ran and their results. Explain any check that was not run. Do not report a check as passing unless you ran it. -->

## Screenshots

<!-- For visible website changes, include sanitized desktop/mobile and light/dark evidence when relevant. Store committed documentation assets under docs/assets/. Otherwise write “Not applicable.” -->

## Review checklist

<!-- Check each applicable item. Leave non-applicable items unchecked; explain unusual omissions above. -->

### General

- [ ] The change is focused and contains no unrelated cleanup.
- [ ] Tests were added or updated for observable behavior changes.
- [ ] Checks for every affected component pass.
- [ ] Documentation matches the implemented behavior.
- [ ] Generated files were updated only through their owning commands.
- [ ] No `.env`, database, SQLite sidecar, credential, cookie, private HTML, log, cache, or build artifact is included.
- [ ] Lockfile changes are intentional and correspond to dependency or metadata changes.
- [ ] This contribution follows the [Code of Conduct](https://github.com/simonesiega/european-tech-opportunities-2027/blob/main/CODE_OF_CONDUCT.md).

### Architecture and source access

- [ ] Canonical SQLite state, lifecycle protections, and the website's read-only contract remain intact.
- [ ] Source requests remain permission-gated, unauthenticated, and bounded.
- [ ] No unauthorized live LinkedIn access was performed.

### When applicable

- [ ] Schema changes include a new Alembic migration and migration tests; no applied migration was rewritten.
- [ ] Search changes use a unique bounded query, include rationale in `notes`, and pass config validation.
- [ ] Classification changes include nearby acceptance and rejection tests and preserve conservative evidence requirements.
- [ ] Visible website changes preserve accessibility, responsive behavior, safe links, and empty states.
