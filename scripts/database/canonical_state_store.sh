#!/usr/bin/env bash
# Restore and publish canonical SQLite snapshots through a restricted SFTP account.
set -euo pipefail

operation=${1:-}
if [[ "$operation" != "restore" && "$operation" != "publish" ]]; then
  echo "Usage: $0 restore|publish" >&2
  exit 2
fi

: "${VPS_BACKUP_HOST:?VPS_BACKUP_HOST is required}"
: "${VPS_BACKUP_USER:=opportunities-backup}"
: "${VPS_BACKUP_PORT:=22}"
: "${VPS_BACKUP_SSH_KEY:=$HOME/.ssh/id_backup_ed25519}"
: "${VPS_BACKUP_KNOWN_HOSTS:=$HOME/.ssh/known_hosts}"
: "${VPS_BACKUP_REMOTE_ROOT:=/state}"
: "${CANONICAL_STATE_PREFIX:=canonical-state}"
: "${CANONICAL_STATE_RETENTION_DAYS:=365}"
: "${CANONICAL_STATE_DATABASE:=data/opportunities.db}"
: "${RUNNER_TEMP:=/tmp}"

if [[ ! "$VPS_BACKUP_HOST" =~ ^[A-Za-z0-9.-]+$ ]] \
  || [[ ! "$VPS_BACKUP_USER" =~ ^[A-Za-z_][A-Za-z0-9._-]*$ ]] \
  || [[ ! "$VPS_BACKUP_PORT" =~ ^[0-9]{1,5}$ ]] \
  || ((10#$VPS_BACKUP_PORT < 1 || 10#$VPS_BACKUP_PORT > 65535)); then
  echo "VPS backup SSH configuration is invalid." >&2
  exit 2
fi
if [[ ! "$VPS_BACKUP_REMOTE_ROOT" =~ ^/[A-Za-z0-9._/-]+$ ]] \
  || [[ "$VPS_BACKUP_REMOTE_ROOT" == */ ]] \
  || [[ "$VPS_BACKUP_REMOTE_ROOT" == *".."* ]]; then
  echo "VPS_BACKUP_REMOTE_ROOT is invalid." >&2
  exit 2
fi
if [[ ! "$CANONICAL_STATE_PREFIX" =~ ^[A-Za-z0-9._/-]+$ ]] \
  || [[ "$CANONICAL_STATE_PREFIX" == /* ]] \
  || [[ "$CANONICAL_STATE_PREFIX" == */ ]] \
  || [[ "$CANONICAL_STATE_PREFIX" == *"//"* ]] \
  || [[ "$CANONICAL_STATE_PREFIX" == *".."* ]]; then
  echo "CANONICAL_STATE_PREFIX is invalid." >&2
  exit 2
fi
if [[ ! "$CANONICAL_STATE_RETENTION_DAYS" =~ ^[0-9]{1,4}$ ]] \
  || ((10#$CANONICAL_STATE_RETENTION_DAYS < 1 || 10#$CANONICAL_STATE_RETENTION_DAYS > 3650)); then
  echo "CANONICAL_STATE_RETENTION_DAYS must be between 1 and 3650." >&2
  exit 2
fi
if [[ ! -s "$VPS_BACKUP_SSH_KEY" || ! -s "$VPS_BACKUP_KNOWN_HOSTS" ]]; then
  echo "Restricted VPS backup SSH key and known_hosts file are required." >&2
  exit 1
fi
if ! command -v sftp >/dev/null 2>&1; then
  echo "OpenSSH sftp is required for canonical state storage." >&2
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required for canonical snapshot verification." >&2
  exit 1
fi

work_dir=${CANONICAL_STATE_WORK_DIR:-$RUNNER_TEMP/canonical-state}
remote_base="$VPS_BACKUP_REMOTE_ROOT/$CANONICAL_STATE_PREFIX"
latest_manifest="$work_dir/latest.json"
remote_latest="$remote_base/latest.json"
mkdir -p "$work_dir"

sftp_command=(
  sftp -q -b -
  -i "$VPS_BACKUP_SSH_KEY"
  -P "$VPS_BACKUP_PORT"
  -o BatchMode=yes
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes
  -o "UserKnownHostsFile=$VPS_BACKUP_KNOWN_HOSTS"
  -o ConnectTimeout=20
  -o ConnectionAttempts=1
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=2
  "$VPS_BACKUP_USER@$VPS_BACKUP_HOST"
)

snapshot_tool() {
  uv run python scripts/database/canonical_snapshot.py "$@"
}

reject_sidecars() {
  # A raw .db checksum does not cover uncheckpointed WAL transactions. Never
  # restore over live sidecars or promote a snapshot-copy beside them.
  local sidecar
  for sidecar in "${CANONICAL_STATE_DATABASE}-wal" \
    "${CANONICAL_STATE_DATABASE}-shm" "${CANONICAL_STATE_DATABASE}-journal"; do
    if [[ -e "$sidecar" || -L "$sidecar" ]]; then
      echo "Canonical SQLite sidecar exists; preserve and checkpoint state before retrying." >&2
      return 1
    fi
  done
}

raw_sftp() {
  "${sftp_command[@]}"
}

run_sftp() {
  if [[ "$operation" != publish ]]; then
    raw_sftp
    return $?
  fi
  # This boundary is used only by the read-only pre-publication pointer fetch.
  local batch attempt status
  batch=$(cat)
  for attempt in 1 2 3; do
    if publication_command inspect-pointer "$remote_latest" "$batch"; then
      cat "$work_dir/sftp-result"
      return 0
    else
      status=$?
    fi
    publication_retry "$attempt" "$status" || return 1
  done
}

# shellcheck source=scripts/database/sftp_publication.sh
source "$(dirname "${BASH_SOURCE[0]}")/sftp_publication.sh"

set_output() {
  local name=$1
  local value=$2
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf '%s=%s\n' "$name" "$value" >>"$GITHUB_OUTPUT"
  fi
}

# Return 1 for proven absence and 2 for failures; callers must distinguish them.
fetch_latest_manifest() {
  local listing_file="$work_dir/remote-listing.txt"
  rm -f "$latest_manifest" "$listing_file"
  # List each prefix segment; a failed download cannot prove a new store is absent.
  local directory="$VPS_BACKUP_REMOTE_ROOT"
  local part
  local -a parts
  IFS='/' read -r -a parts <<<"$CANONICAL_STATE_PREFIX"
  for part in "${parts[@]}"; do
    printf 'cd "%s"\nls -1 "%s"\n' "$directory" "$directory" \
      | run_sftp >"$listing_file" || return 2
    if ! grep -Fxq "$directory/$part" "$listing_file" \
      && ! grep -Fxq "$part" "$listing_file"; then
      return 1
    fi
    directory="$directory/$part"
  done
  printf 'cd "%s"\nls -1 "%s"\n' "$remote_base" "$remote_base" \
    | run_sftp >"$listing_file" || return 2
  if grep -Fxq "$remote_latest" "$listing_file" \
    || grep -Fxq 'latest.json' "$listing_file"; then
    printf 'get "%s" "%s"\n' "$remote_latest" "$latest_manifest" \
      | run_sftp || return 2
    if [[ ! -s "$latest_manifest" ]]; then
      echo "VPS snapshot manifest is empty; preserve state and investigate." >&2
      return 2
    fi
    return 0
  fi
  if grep -Fxq "$remote_base/snapshots" "$listing_file" \
    || grep -Fxq 'snapshots' "$listing_file"; then
    echo "VPS snapshot history exists but latest.json is absent; recover the pointer instead of seeding new state." >&2
    return 2
  fi
  return 1
}

download_snapshot() {
  local database_key=$1
  local destination=$2
  local remote_database="$VPS_BACKUP_REMOTE_ROOT/$database_key"
  local sidecar
  for sidecar in "${destination}-wal" "${destination}-shm" "${destination}-journal"; do
    if [[ -e "$sidecar" || -L "$sidecar" ]]; then
      echo "Staged SQLite restore has sidecars; preserve them for investigation." >&2
      return 1
    fi
  done
  if [[ -e "$destination" || -L "$destination" ]]; then
    echo "Staged SQLite restore already exists; preserve it for investigation." >&2
    return 1
  fi
  printf 'get "%s" "%s"\n' "$remote_database" "$destination" | run_sftp
}

restore_state() {
  reject_sidecars
  local status
  if fetch_latest_manifest; then
    status=0
  else
    status=$?
  fi
  if ((status == 1)); then
    echo "No VPS canonical snapshot exists yet; verify any existing candidate or use live-database bootstrap."
    set_output state_source "no-vps-snapshot"
    return 0
  fi
  if ((status != 0)); then
    return "$status"
  fi

  local database_key
  database_key=$(snapshot_tool key --manifest "$latest_manifest" --kind database)
  if [[ -e "$CANONICAL_STATE_DATABASE" || -L "$CANONICAL_STATE_DATABASE" ]]; then
    if [[ -s "$CANONICAL_STATE_DATABASE" ]] \
      && snapshot_tool verify \
        --database "$CANONICAL_STATE_DATABASE" \
        --manifest "$latest_manifest" \
        --expected-database-key "$database_key" >/dev/null 2>&1; then
      echo "Existing database matches the latest verified VPS snapshot."
      set_output state_source "verified-existing-database"
      return 0
    fi
    echo "Local canonical state differs from the latest snapshot; preserve it for investigation." >&2
    return 1
  fi

  mkdir -p "$(dirname "$CANONICAL_STATE_DATABASE")"
  local restored_database="${CANONICAL_STATE_DATABASE}.sftp-restore-${GITHUB_RUN_ID:-local}"
  download_snapshot "$database_key" "$restored_database"
  snapshot_tool verify \
    --database "$restored_database" \
    --manifest "$latest_manifest" \
    --expected-database-key "$database_key"
  mv -f "$restored_database" "$CANONICAL_STATE_DATABASE"
  echo "Restored canonical SQLite state from the restricted VPS snapshot account."
  set_output state_source "vps-snapshot"
}

publish_state() {
  reject_sidecars
  : "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required for snapshot publication}"
  : "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required for snapshot publication}"
  : "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required for snapshot publication}"
  if [[ ! -s "$CANONICAL_STATE_DATABASE" ]]; then
    echo "Canonical database is missing or empty: $CANONICAL_STATE_DATABASE" >&2
    exit 1
  fi

  local status=1

  local publish_dir="$work_dir/publish"
  local snapshot_database="$publish_dir/opportunities.snapshot.db"
  local snapshot_manifest="$publish_dir/manifest.json"
  mkdir -p "$publish_dir"
  # Retain a completed local bundle so the exact immutable key survives retries.
  if [[ -e "$snapshot_database" || -e "$snapshot_manifest" ]]; then
    snapshot_tool verify --database "$snapshot_database" --manifest "$snapshot_manifest"
    if ! cmp -s "$CANONICAL_STATE_DATABASE" "$snapshot_database"; then
      # The bundle normalizes WAL mode to DELETE. Compare the same normalized
      # backup, not the original header, without modifying the working database.
      local comparison_database="$work_dir/resume-comparison.db"
      if [[ -e "$comparison_database" || -L "$comparison_database" ]]; then
        echo "Resume comparison already exists; preserve and investigate." >&2
        return 1
      fi
      uv run python -c '
import sqlite3, sys
from pathlib import Path
with sqlite3.connect(Path(sys.argv[1]).resolve().as_uri() + "?mode=ro", uri=True) as source:
    with sqlite3.connect(sys.argv[2]) as destination:
        source.backup(destination)
        destination.execute("PRAGMA journal_mode=DELETE")
' "$CANONICAL_STATE_DATABASE" "$comparison_database"
      if ! cmp -s "$comparison_database" "$snapshot_database"; then
        echo "Retained publication bundle differs from canonical state; preserve and investigate." >&2
        return 1
      fi
      rm "$comparison_database"
    fi
  else
    if fetch_latest_manifest; then
      status=0
    else
      status=$?
    fi
    if ((status != 0 && status != 1)); then
      return "$status"
    fi

    local -a create_arguments=(
      create
      --database "$CANONICAL_STATE_DATABASE"
      --snapshot "$snapshot_database"
      --manifest "$snapshot_manifest"
      --key-prefix "$CANONICAL_STATE_PREFIX"
      --retention-days "$CANONICAL_STATE_RETENTION_DAYS"
      --repository "$GITHUB_REPOSITORY"
      --run-id "$GITHUB_RUN_ID"
      --run-attempt "$GITHUB_RUN_ATTEMPT"
    )
    if ((status == 0)); then
      create_arguments+=(--previous-manifest "$latest_manifest")
    fi
    snapshot_tool "${create_arguments[@]}"
  fi

  local database_key
  local manifest_key
  database_key=$(snapshot_tool key --manifest "$snapshot_manifest" --kind database)
  manifest_key=$(snapshot_tool key --manifest "$snapshot_manifest" --kind manifest)
  if [[ "$database_key" != "$CANONICAL_STATE_PREFIX/"*"-run-$GITHUB_RUN_ID-attempt-$GITHUB_RUN_ATTEMPT.db" ]]; then
    echo "Publication bundle belongs to another run/attempt; preserve and investigate." >&2
    return 1
  fi
  local remote_database="$VPS_BACKUP_REMOTE_ROOT/$database_key"
  local remote_manifest="$VPS_BACKUP_REMOTE_ROOT/$manifest_key"
  local upload_suffix=".upload-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"

  publication_directories "$database_key"
  publication_file "$snapshot_database" "$remote_database" "$remote_database$upload_suffix"
  publication_file "$snapshot_manifest" "$remote_manifest" "$remote_manifest$upload_suffix"

  # Round-trip immutable snapshot files before changing latest.json.
  local verification_dir="$work_dir/restore-verification"
  local verified_database="$verification_dir/opportunities.db"
  local verified_manifest="$verification_dir/manifest.json"
  rm -rf "$verification_dir"
  mkdir -p "$verification_dir"
  publication_download "$remote_manifest" "$verified_manifest" round-trip-manifest
  publication_download "$remote_database" "$verified_database" round-trip-database
  snapshot_tool verify \
    --database "$verified_database" \
    --manifest "$verified_manifest" \
    --expected-database-key "$database_key"
  OPPORTUNITIES_DATABASE_URL="sqlite:///$verified_database" \
    uv run opportunities stats >/dev/null

  local latest_upload="$remote_latest$upload_suffix"
  publication_file "$verified_manifest" "$remote_latest" "$latest_upload" true "$latest_manifest"
  local promoted_manifest="$verification_dir/latest.json"
  publication_download "$remote_latest" "$promoted_manifest" confirm-latest
  if ! cmp -s "$verified_manifest" "$promoted_manifest"; then
    echo "Promoted VPS latest manifest did not round-trip exactly." >&2
    exit 1
  fi

  # Keep the canonical working copy byte-identical to the verified snapshot.
  local canonical_copy="${CANONICAL_STATE_DATABASE}.snapshot-copy"
  cp "$verified_database" "$canonical_copy"
  mv -f "$canonical_copy" "$CANONICAL_STATE_DATABASE"

  cp "$verified_manifest" "$latest_manifest"
  echo "Published and restore-verified VPS snapshot: $database_key"
  set_output snapshot_database "$snapshot_database"
  set_output snapshot_manifest "$snapshot_manifest"
  set_output snapshot_key "$database_key"
}

if [[ "$operation" == "restore" ]]; then
  restore_state
else
  publish_state
fi
