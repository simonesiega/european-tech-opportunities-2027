#!/usr/bin/env bash
# Run over the deployment SSH session. Publish one immutable release, then atomically switch current.
set -euo pipefail

: "${RELEASE_DATA_DIR:?}"
: "${RELEASE_ID:?}"
: "${DATABASE_SHA:?}"
: "${CSV_SHA:?}"
: "${JSON_SHA:?}"
: "${RELEASE_GROUP:=opportunities-site}"

if [[ "$RELEASE_DATA_DIR" != /* || "$RELEASE_DATA_DIR" == *".."* \
  || ! "$RELEASE_ID" =~ ^[0-9]+-[0-9]+$ \
  || ! "$RELEASE_GROUP" =~ ^[a-zA-Z_][a-zA-Z0-9_-]*$ ]]; then
  echo "Invalid release configuration." >&2
  exit 2
fi
for hash in "$DATABASE_SHA" "$CSV_SHA" "$JSON_SHA"; do
  if [[ ! "$hash" =~ ^[0-9a-f]{64}$ ]]; then
    echo "Invalid release checksum." >&2
    exit 2
  fi
done

root="$RELEASE_DATA_DIR"
staging="$root/.incoming/$RELEASE_ID"
releases="$root/releases"
release="$releases/$RELEASE_ID"
pointer="$root/current"
next_pointer="$root/.current-$RELEASE_ID"
lock="$root/.release-deploy.lock"

# Never remove an immutable release on failure: it may be in use by an active reader.
exec 9>"$lock"
flock -n 9 || { echo "Another release is being deployed." >&2; exit 1; }
if [[ ( -e "$pointer" && ! -L "$pointer" ) || ( -L "$pointer" && ! -e "$pointer" ) ]] \
  || { [[ -L "$pointer" ]] && [[ ! "$(readlink "$pointer")" =~ ^releases/[0-9]+-[0-9]+$ ]]; }; then
  echo "Release pointer is invalid; recover it manually." >&2
  exit 1
fi
if [[ -e "$release" || -L "$release" || -e "$next_pointer" || -L "$next_pointer" ]]; then
  echo "Release ID already exists; do not overwrite immutable state." >&2
  exit 1
fi

for sidecar in "$staging/opportunities.db-wal" "$staging/opportunities.db-shm" "$staging/opportunities.db-journal"; do
  if [[ -e "$sidecar" ]]; then
    echo "Staged SQLite sidecars are not supported." >&2
    exit 1
  fi
done
for entry in "opportunities.db:$DATABASE_SHA" \
  "exports/open-opportunities.csv:$CSV_SHA" \
  "exports/open-opportunities.json:$JSON_SHA"; do
  file="${entry%:*}"
  expected="${entry#*:}"
  if [[ ! -f "$staging/$file" || -L "$staging/$file" \
    || "$(sha256sum "$staging/$file" | cut -d ' ' -f 1)" != "$expected" ]]; then
    echo "Staged release is incomplete or failed checksum verification." >&2
    exit 1
  fi
done

# Retain the three expected digests alongside the release for offline inspection
# and rollback verification. This is not a substitute for the restricted snapshot.
printf '%s  %s\n' \
  "$DATABASE_SHA" opportunities.db \
  "$CSV_SHA" exports/open-opportunities.csv \
  "$JSON_SHA" exports/open-opportunities.json >"$staging/checksums.sha256"

# The deployment user owns releases for controlled maintenance; the site group
# can only traverse directories and read payloads, never write canonical state.
mkdir -p "$releases"
chgrp "$RELEASE_GROUP" "$releases" "$staging" "$staging/exports" \
  "$staging/opportunities.db" "$staging/exports/open-opportunities.csv" \
  "$staging/exports/open-opportunities.json" "$staging/checksums.sha256"
chmod 750 "$releases" "$staging" "$staging/exports"
chmod 640 "$staging/opportunities.db" "$staging/exports/open-opportunities.csv" \
  "$staging/exports/open-opportunities.json" "$staging/checksums.sha256"

# Promote the complete directory, then remove write bits before advertising it.
# The deployment owner can still change permissions for deliberate rollback or repair.
mv -T "$staging" "$release"
chmod 550 "$release" "$release/exports"
chmod 440 "$release/opportunities.db" "$release/exports/open-opportunities.csv" \
  "$release/exports/open-opportunities.json" "$release/checksums.sha256"

# Flush complete files and directory metadata before advertising this release. Both
# renames must be on the same host filesystem; the pointer rename is the cutover.
python3 - "$release" <<'PY'
import os
import sys
from pathlib import Path

release = Path(sys.argv[1])
for name in ("opportunities.db", "exports/open-opportunities.csv", "exports/open-opportunities.json", "checksums.sha256"):
    with (release / name).open("rb") as stream:
        os.fsync(stream.fileno())
for directory in (release / "exports", release):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
PY
python3 - "$releases" <<'PY'
import os
import sys

fd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
try:
    os.fsync(fd)
finally:
    os.close(fd)
PY
trap 'rm -f "$next_pointer"' EXIT
ln -s "releases/$RELEASE_ID" "$next_pointer"
mv -Tf "$next_pointer" "$pointer"
python3 - "$releases" "$root" <<'PY'
import os
import sys

for directory in sys.argv[1:]:
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
PY
printf 'Activated release %s. Preserve previous releases for reader drain and rollback.\n' "$RELEASE_ID"
