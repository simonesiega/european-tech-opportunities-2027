# Troubleshooting

[← README](../README.md)

Start with the command's exit code and the first sanitized error. Avoid deleting SQLite state, weakening filters, or bypassing the authorization gate as a shortcut.

## Exit codes

| Code | Meaning | First action |
|---:|---|---|
| `0` | Success. | No recovery required. |
| `1` | Complete collection failure or validation inconsistency. | Inspect per-search errors or validation output; preserve state. |
| `2` | Partial collection or command/configuration rejection. | Read the command-specific error. For a partial scrape, identify successful searches before rerunning only the failed ones. |
| `3` | Database missing required tables or not at migration head. | Run `db-upgrade` against the same database URL. |

When `scrape` exits with code `2` because of a partial run, successful searches remain committed while failed searches do not mutate their job lifecycle. Other commands may use code `2` for invalid input, configuration errors, disabled collection, or an unknown search.

## Establish the effective environment

From the repository root:

```bash
uv --version
uv run python --version
uv run internships --help
uv run internships searches
```

Confirm:

- commands run from the expected checkout;
- `.env` points to the intended database, README, and config directories;
- process environment is not unexpectedly overriding `.env`;
- an optional settings YAML is the intended file;
- Docker commands use container paths, not host paths.

Do not paste complete environment output into an issue. Report only relevant, non-sensitive values.

## Database is not migrated

Message:

```text
Database is not migrated. Run `uv run internships db-upgrade`.
```

Run:

```bash
uv run internships db-upgrade
uv run internships stats
```

If it persists:

1. confirm `INTERNSHIPS_DATABASE_URL` is identical for both commands;
2. check whether a process environment value overrides `.env`;
3. verify you are in the repository root;
4. run `uv run python scripts/check_migrations.py` to verify committed migrations;
5. preserve a database backup before attempting repair.

Do not delete `data/internships.db` merely to make the message disappear. See [Database recovery](#database-recovery).

## LinkedIn collection is disabled

Message:

```text
LinkedIn collection is disabled.
```

This is the correct default. `search-test`, `scrape`, and live tests require:

```dotenv
INTERNSHIPS_LINKEDIN_CRAWL_AUTHORIZED=true
```

Set it only after express LinkedIn permission. The value does not grant permission. If permission is absent, use offline fixtures and commands instead.

In GitHub Actions, the separate repository variable must be exactly:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

If absent, the collection job is skipped rather than failed.

## Unknown or disabled search

Message resembles:

```text
unknown or disabled search: <slug>
```

List exact enabled slugs:

```bash
uv run internships searches
```

Use the `slug` inside YAML, not the filename path. Company and country slugs include prefixes such as `company-amazon` and `country-finland`.

If the YAML says `enabled: false`, enable it only after reviewing its query and limits.

## Invalid search YAML

Common causes:

- unknown field;
- invalid kebab-case slug;
- `max_results > max_pages × 25`;
- malformed/non-mapping YAML;
- duplicate slug;
- duplicate query identity;
- invalid `workplace` or `date_posted` value;
- non-numeric `geo_id`.

Run:

```bash
uv run internships searches
uv run pytest tests/unit/test_config.py
```

The error includes the source file path and Pydantic validation details. See [Search registry](search-registry.md).

## Invalid settings

Configuration errors exit with code `2` before command work starts.

Check precedence:

```text
defaults < .env < settings YAML < process environment
```

Typical problems:

- database URL missing `://`;
- invalid boolean or integer;
- unsupported log level;
- result override larger than page capacity;
- selected YAML file missing or not a mapping;
- path points outside the current working directory unintentionally.

Temporarily remove duplicate overrides rather than guessing which source wins. See [Configuration](configuration.md).

## README marker error

Message:

```text
README must contain exactly one internship marker pair
```

The renderer requires exactly one opening `BEGIN INTERNSHIPS` HTML comment and one closing `END INTERNSHIPS` HTML comment.

Check counts without adding another marker to README documentation:

```bash
grep -c "BEGIN INTERNSHIPS" README.md
grep -c "END INTERNSHIPS" README.md
```

Both should print `1`. Restore the marker block from Git if necessary, then run:

```bash
uv run internships render
uv run internships validate
```

Do not place complete copies of the marker comments in README examples; the renderer counts the entire file.

## README and SQLite disagree

Validation reports that the generated block does not match open jobs or collection metadata.

Regenerate from canonical state:

```bash
uv run internships render
uv run internships validate
```

If disagreement remains:

1. verify `INTERNSHIPS_README_PATH` points to the file being inspected;
2. verify `INTERNSHIPS_DATABASE_URL` points to the intended database;
3. check write permissions in the README parent directory;
4. confirm no formatter or concurrent process edits the generated block;
5. stop concurrent writers;
6. preserve both files before deeper repair.

Never repair canonical state by manually editing generated metadata or table rows.

## A relevant-looking job is excluded

Strict exclusion is often expected. Verify all four requirements:

1. the **title** explicitly identifies an internship/placement/co-op;
2. `2027` is explicit in the title or internship-cycle description context;
3. the role has a recognized technology signal;
4. the location explicitly resolves to Europe/a supported European country.

Also check excluded seniority terminology. Full-time employment metadata or a description mentioning an internship cannot convert a non-intern title into one.

Use an authorized, non-persisting preview to inspect accepted totals:

```bash
uv run internships search-test <slug>
```

For classifier debugging, prefer local unit tests with a synthetic title, description, and normalized location. Do not weaken a global rule for one ambiguous listing.

## Search returns no accepted jobs

Possible explanations:

- LinkedIn currently has no explicitly advertised 2027 internships for the query;
- cards were ranked but their titles did not contain internship terminology;
- details lacked explicit 2027 cycle evidence;
- locations were unknown or outside Europe;
- roles were non-technical;
- an employer allowlist did not match the parsed company name;
- the guest endpoint returned changed markup or a block page.

Check `internships searches` after persisted runs for found/accepted counts. A high found count with zero accepted usually indicates strict filtering, not necessarily parser failure. A failed status indicates transport/parser diagnostics instead.

Do not increase every page limit before understanding which stage removed candidates.

## HTTP 429, timeout, or 5xx

The transport retries these failures finitely with exponential backoff. If the search still fails:

- stop repeated manual retries;
- retain conservative pacing;
- verify authorized access limits;
- retry the individual slug later rather than the full registry;
- do not add proxies, browser automation, CAPTCHA solving, fingerprint evasion, or private endpoints.

For diagnostics, a temporary higher timeout may be appropriate:

```dotenv
INTERNSHIPS_REQUEST_TIMEOUT_SECONDS=40
INTERNSHIPS_CONNECT_TIMEOUT_SECONDS=20
```

Do not increase concurrency to work around rate limiting.

## HTTP 403 or challenge/access page

The parser rejects known challenge and verification markers. Treat this as a stop condition.

- Do not bypass the challenge.
- Do not use an account, cookies, browser automation, proxies, or CAPTCHA services.
- Confirm authorization remains valid for the endpoint and access pattern.
- Disable collection until the issue is resolved with LinkedIn.

A changed legitimate HTML document can be investigated using sanitized offline fixtures, but live access policy remains unchanged.

## Partial scraping failures

A scrape exit code `2` means some searches succeeded and some failed.

The result table identifies each slug and error category. Recommended response:

1. let `validate` confirm committed state;
2. inspect failed slugs and common failure type;
3. avoid rerunning successful broad searches unnecessarily;
4. rerun one failed slug only when appropriate:

```bash
uv run internships scrape --search <failed-slug>
uv run internships validate
```

Failed searches do not count card absence or close jobs.

## All searches failed

Exit code `1` indicates no selected search succeeded.

Look for a shared cause:

- authorization removed/invalid for the environment;
- host/network outage;
- widespread HTTP block/challenge;
- invalid upstream markup;
- DNS/TLS failure;
- overly short timeout;
- common configuration path problem.

Do not render new lifecycle assumptions from an all-failed run. Existing canonical state remains the basis for README output.

## Job did not close

This is normally safe behavior. Search absence is ignored.

A job closes only after:

- its detail page explicitly returns `404`/`410` repeatedly;
- every active search association reaches `closure_confirmation_runs`;
- no association has rediscovered it.

`max_rechecks` bounds how many absent known jobs a search checks per run, so large queues can take several successful runs. Do not manually close jobs merely because ranking changed.

See [Database lifecycle](database.md#closure-algorithm).

## Unexpected closure or reopen

Stop collection and back up SQLite.

Inspect:

- configured `closure_confirmation_runs`;
- recent successful runs for every associated search;
- whether detail responses were explicit `404`/`410`;
- search configuration/slug changes;
- whether the job was rediscovered with the same numeric LinkedIn ID;
- clock/timestamp anomalies.

Open a bug with synthetic/reduced database evidence if lifecycle code violated the documented algorithm. If state corruption or an authorization/security boundary may be involved, report privately through [Security](../SECURITY.md).

## Timestamp validation failure

Message identifies a job whose `last_seen_at` precedes `first_seen_at`.

This should not occur because persistence uses monotonic maximum timestamps. Treat it as canonical state corruption or a regression:

1. stop writers;
2. back up the database;
3. record the job ID and timestamps;
4. run the test suite;
5. restore a known-good backup if necessary;
6. report the issue with sanitized state.

Do not rewrite timestamps without preserving evidence.

## Migration consistency fails

`scripts/check_migrations.py` reports either an unexpected Alembic version or ORM/schema differences.

- Confirm there is exactly one Alembic head.
- Ensure model changes have a new migration.
- Ensure the revision imports/registers current ORM tables.
- Do not edit an old applied revision to hide drift.
- Run the check from the repository root.

See [Database migrations](database.md#migrations) and [Development](development.md#migration-workflow).

## Database recovery

Before repair, stop every writer and create a backup with SQLite's backup API. Then:

```bash
uv run internships db-upgrade
uv run internships render
uv run internships validate
uv run internships stats
```

If migration fails, preserve the original file and error. Restore a known-good backup rather than starting empty. A fresh database loses discovery dates, provenance, closure confirmations, and run history.

The GitHub workflow's `allow_state_rebuild` has the same destructive consequence and should remain false during normal operation.

Full procedure: [Database restore and recovery](database.md#restore-and-recovery).

## GitHub collection job is skipped

Check the repository **variable**, not a secret or environment variable:

```text
LINKEDIN_CRAWL_AUTHORIZED=true
```

Variable names and value are case-sensitive in the workflow condition. Configure it only after express permission.

## GitHub cache is missing

Actions caches can expire or be evicted. Look for the most recent `internship-state-<run-id>` artifact, retained for 30 days by the workflow.

If neither cache nor backup exists, do not assume README can reconstruct lifecycle state. The README lacks IDs, closed jobs, provenance, and run history. A fresh database is a state rebuild and should be treated/documented as such.

See [Automation](automation.md#state-restore).

## Docker permission denied

The image runs as UID/GID `10001:10001`. It needs write access under `./data` and permission to create and replace files in the repository root mounted at `/workspace`.

Inspect numeric ownership and directory permissions:

```bash
ls -ldn . README.md data
```

Use narrow ownership/ACL changes or run a local one-off container as your host UID/GID. Do not use world-writable permissions as a blanket fix.

See [Docker Linux permissions](docker.md#linux-bind-mount-permissions).

## Docker sees the wrong database

Confirm all commands use the same mount and absolute container URL:

```bash
docker compose config
docker compose run --rm internships stats
```

The expected Compose URL is:

```text
sqlite:////app/data/internships.db
```

A host-relative SQLite URL inside the container can create a different database than expected.

## Asking for help

For a normal issue, include:

- command and exit code;
- expected and actual behavior;
- OS, Python, `uv`, and project version;
- affected search slug when relevant;
- sanitized error code/output;
- minimal offline reproduction or fixture.

Do not include `.env`, cookies, authenticated HTML, tokens, private paths, or a production database. Use private vulnerability reporting for security-sensitive behavior.
