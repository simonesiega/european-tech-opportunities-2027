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
  || [[ ! "$VPS_BACKUP_PORT" =~ ^[0-9]{1,5}$ ]]; then
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
  || [[ "$CANONICAL_STATE_PREFIX" == *".."* ]]; then
  echo "CANONICAL_STATE_PREFIX is invalid." >&2
  exit 2
fi
if [[ ! "$CANONICAL_STATE_RETENTION_DAYS" =~ ^[0-9]+$ ]] \
  || ((CANONICAL_STATE_RETENTION_DAYS < 1 || CANONICAL_STATE_RETENTION_DAYS > 3650)); then
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
  "$VPS_BACKUP_USER@$VPS_BACKUP_HOST"
)

snapshot_tool() {
  uv run python scripts/canonical_snapshot.py "$@"
}

run_sftp() {
  "${sftp_command[@]}"
}

set_output() {
  local name=$1
  local value=$2
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf '%s=%s\n' "$name" "$value" >>"$GITHUB_OUTPUT"
  fi
}

fetch_latest_manifest() {
  local listing_file="$work_dir/remote-listing.txt"
  rm -f "$latest_manifest" "$listing_file"
  {
    printf 'ls "%s"\n' "$VPS_BACKUP_REMOTE_ROOT"
    printf '%s\n' "-get \"$remote_latest\" \"$latest_manifest\""
    printf '%s\n' "-ls -1 \"$remote_base/snapshots\""
  } | run_sftp >"$listing_file"

  if [[ -s "$latest_manifest" ]]; then
    return 0
  fi
  if grep -Eq '(^|/)(19|20)[0-9]{2}([[:space:]]|/|$)' "$listing_file"; then
    echo "VPS snapshot history exists but latest.json is absent; recover the pointer instead of seeding new state." >&2
    return 2
  fi
  return 1
}

download_snapshot() {
  local database_key=$1
  local destination=$2
  local remote_database="$VPS_BACKUP_REMOTE_ROOT/$database_key"
  rm -f "$destination"
  printf 'get "%s" "%s"\n' "$remote_database" "$destination" | run_sftp
}

restore_state() {
  local status
  if fetch_latest_manifest; then
    status=0
  else
    status=$?
  fi
  if ((status == 1)); then
    echo "No VPS canonical snapshot exists yet; retaining the cache or using live-database bootstrap."
    set_output state_source "no-vps-snapshot"
    return 0
  fi
  if ((status != 0)); then
    return "$status"
  fi

  local database_key
  database_key=$(snapshot_tool key --manifest "$latest_manifest" --kind database)
  if [[ -s "$CANONICAL_STATE_DATABASE" ]] \
    && snapshot_tool verify \
      --database "$CANONICAL_STATE_DATABASE" \
      --manifest "$latest_manifest" \
      --expected-database-key "$database_key" >/dev/null 2>&1; then
    echo "Cache matches the latest verified VPS snapshot."
    set_output state_source "verified-cache"
    return 0
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

append_remote_mkdirs() {
  local key=$1
  local path="$VPS_BACKUP_REMOTE_ROOT"
  local directory=${key%/*}
  local part
  local -a parts
  IFS='/' read -r -a parts <<<"$directory"
  for part in "${parts[@]}"; do
    path="$path/$part"
    printf '%s\n' "-mkdir \"$path\""
  done
  printf 'ls "%s"\n' "$path"
}

publish_state() {
  : "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required for snapshot publication}"
  : "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required for snapshot publication}"
  : "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required for snapshot publication}"
  if [[ ! -s "$CANONICAL_STATE_DATABASE" ]]; then
    echo "Canonical database is missing or empty: $CANONICAL_STATE_DATABASE" >&2
    exit 1
  fi

  local status
  if fetch_latest_manifest; then
    status=0
  else
    status=$?
  fi
  if ((status != 0 && status != 1)); then
    return "$status"
  fi

  local publish_dir="$work_dir/publish"
  local snapshot_database="$publish_dir/opportunities.snapshot.db"
  local snapshot_manifest="$publish_dir/manifest.json"
  rm -rf "$publish_dir"
  mkdir -p "$publish_dir"

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

  local database_key
  local manifest_key
  database_key=$(snapshot_tool key --manifest "$snapshot_manifest" --kind database)
  manifest_key=$(snapshot_tool key --manifest "$snapshot_manifest" --kind manifest)
  local remote_database="$VPS_BACKUP_REMOTE_ROOT/$database_key"
  local remote_manifest="$VPS_BACKUP_REMOTE_ROOT/$manifest_key"
  local upload_suffix=".upload-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"

  {
    append_remote_mkdirs "$database_key"
    printf 'put "%s" "%s%s"\n' "$snapshot_database" "$remote_database" "$upload_suffix"
    printf 'rename "%s%s" "%s"\n' "$remote_database" "$upload_suffix" "$remote_database"
    printf 'put "%s" "%s%s"\n' "$snapshot_manifest" "$remote_manifest" "$upload_suffix"
    printf 'rename "%s%s" "%s"\n' "$remote_manifest" "$upload_suffix" "$remote_manifest"
  } | run_sftp

  # Round-trip immutable snapshot files before changing latest.json.
  local verification_dir="$work_dir/restore-verification"
  local verified_database="$verification_dir/opportunities.db"
  local verified_manifest="$verification_dir/manifest.json"
  rm -rf "$verification_dir"
  mkdir -p "$verification_dir"
  {
    printf 'get "%s" "%s"\n' "$remote_manifest" "$verified_manifest"
    printf 'get "%s" "%s"\n' "$remote_database" "$verified_database"
  } | run_sftp
  snapshot_tool verify \
    --database "$verified_database" \
    --manifest "$verified_manifest" \
    --expected-database-key "$database_key"
  OPPORTUNITIES_DATABASE_URL="sqlite:///$verified_database" \
    uv run opportunities stats >/dev/null

  local latest_upload="$remote_latest$upload_suffix"
  {
    printf 'put "%s" "%s"\n' "$verified_manifest" "$latest_upload"
    printf 'rename "%s" "%s"\n' "$latest_upload" "$remote_latest"
  } | run_sftp
  local promoted_manifest="$verification_dir/latest.json"
  printf 'get "%s" "%s"\n' "$remote_latest" "$promoted_manifest" | run_sftp
  if ! cmp -s "$verified_manifest" "$promoted_manifest"; then
    echo "Promoted VPS latest manifest did not round-trip exactly." >&2
    exit 1
  fi

  # Keep cache, artifact, and deployment files byte-identical to the verified snapshot.
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
