#!/usr/bin/env bash
# Restore canonical state from the restricted snapshot store, with a verified live fallback.
set -euo pipefail

: "${VPS_BACKUP_SSH_PRIVATE_KEY:?VPS_BACKUP_SSH_PRIVATE_KEY is required}"
: "${VPS_SSH_KNOWN_HOSTS:?VPS_SSH_KNOWN_HOSTS is required}"
: "${VPS_BACKUP_HOST:?VPS_BACKUP_HOST is required}"
: "${VPS_BACKUP_USER:=opportunities-backup}"
: "${VPS_BACKUP_PORT:=22}"
: "${CANONICAL_STATE_DATABASE:=data/opportunities.db}"

created_ssh_dir=false
if [[ -n "${CANONICAL_STATE_SSH_DIR:-}" ]]; then
  ssh_dir=$CANONICAL_STATE_SSH_DIR
else
  ssh_dir=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/opportunities-restore-ssh.XXXXXXXX")
  created_ssh_dir=true
fi
backup_key="$ssh_dir/id_backup_ed25519"
live_key="$ssh_dir/id_ed25519"
known_hosts="$ssh_dir/known_hosts"
bootstrap_download="${CANONICAL_STATE_DATABASE}.bootstrap-${GITHUB_RUN_ID:-local}"

cleanup() {
  rm -f "$backup_key" "$live_key" "$known_hosts"
  if [[ "$created_ssh_dir" == true ]]; then
    rmdir "$ssh_dir" 2>/dev/null || true
  fi
}

install -d -m 700 "$ssh_dir"
for credential in "$backup_key" "$live_key" "$known_hosts"; do
  if [[ -e "$credential" || -L "$credential" ]]; then
    echo "SSH credential path already exists; use an empty dedicated directory." >&2
    exit 1
  fi
done
trap cleanup EXIT
printf '%s\n' "$VPS_BACKUP_SSH_PRIVATE_KEY" >"$backup_key"
printf '%s\n' "$VPS_SSH_KNOWN_HOSTS" >"$known_hosts"
chmod 600 "$backup_key" "$known_hosts"

verify_database() {
  local database_path=$1
  uv run python - "$database_path" <<'PY'
import sys
from pathlib import Path

from opportunities.database.snapshots import SnapshotError, inspect_database

try:
    inspect_database(Path(sys.argv[1]))
except (OSError, SnapshotError) as exc:
    raise SystemExit(f"Canonical state candidate failed recovery checks: {exc}") from exc
PY
}

VPS_BACKUP_SSH_KEY="$backup_key" \
VPS_BACKUP_KNOWN_HOSTS="$known_hosts" \
  bash scripts/canonical_state_store.sh restore

if [[ -e "$CANONICAL_STATE_DATABASE" || -L "$CANONICAL_STATE_DATABASE" ]]; then
  if [[ ! -s "${CANONICAL_STATE_WORK_DIR:-${RUNNER_TEMP:-/tmp}/canonical-state}/latest.json" ]]; then
    echo "Local state without a durable snapshot cannot be used as a bootstrap source." >&2
    exit 1
  fi
  if verify_database "$CANONICAL_STATE_DATABASE"; then
    echo "Using canonical state restored from restricted VPS snapshot storage."
    exit 0
  fi
  echo "Existing canonical state is invalid; preserve it for investigation instead of bootstrapping over it." >&2
  exit 1
fi

: "${VPS_SSH_PRIVATE_KEY:?VPS_SSH_PRIVATE_KEY is required when durable snapshot state is absent}"
: "${VPS_HOST:?VPS_HOST is required when durable snapshot state is absent}"
: "${VPS_USER:?VPS_USER is required when durable snapshot state is absent}"
: "${VPS_PORT:=22}"

if [[ ! "$VPS_HOST" =~ ^[A-Za-z0-9.-]+$ ]] \
  || [[ ! "$VPS_USER" =~ ^[A-Za-z_][A-Za-z0-9._-]*$ ]] \
  || [[ ! "$VPS_PORT" =~ ^[0-9]{1,5}$ ]] \
  || ((10#$VPS_PORT < 1 || 10#$VPS_PORT > 65535)); then
  echo "VPS bootstrap configuration is missing or invalid." >&2
  exit 2
fi

printf '%s\n' "$VPS_SSH_PRIVATE_KEY" >"$live_key"
chmod 600 "$live_key"
mkdir -p "$(dirname "$CANONICAL_STATE_DATABASE")"
for sidecar in "${bootstrap_download}-wal" "${bootstrap_download}-shm" "${bootstrap_download}-journal"; do
  if [[ -e "$sidecar" || -L "$sidecar" ]]; then
    echo "Bootstrap staging has SQLite sidecars; preserve them for investigation." >&2
    exit 1
  fi
done
if [[ -e "$bootstrap_download" || -L "$bootstrap_download" ]]; then
  echo "Bootstrap staging already exists; preserve it for investigation." >&2
  exit 1
fi

# After the first versioned publication the fixed legacy database can be stale,
# even if old site instances still read it. Never bootstrap from that file.
ssh \
  -i "$live_key" -p "$VPS_PORT" -o BatchMode=yes -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$known_hosts" \
  -o ConnectTimeout=20 -o ConnectionAttempts=1 \
  "${VPS_USER}@${VPS_HOST}" \
  'test ! -e /srv/european-tech-opportunities-2027/data/current && test ! -L /srv/european-tech-opportunities-2027/data/current && test ! -d /srv/european-tech-opportunities-2027/data/releases' || {
    echo "Cannot bootstrap from legacy state when versioned publication exists (or SSH failed)." >&2
    exit 1
  }

ssh \
  -i "$live_key" \
  -p "$VPS_PORT" \
  -o BatchMode=yes \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes \
  -o "UserKnownHostsFile=$known_hosts" \
  -o ConnectTimeout=20 \
  -o ConnectionAttempts=1 \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=2 \
  "${VPS_USER}@${VPS_HOST}" \
  python3 - /srv/european-tech-opportunities-2027/data/opportunities.db \
  < scripts/bootstrap_sqlite.py >"$bootstrap_download"

verify_database "$bootstrap_download"
mv -f "$bootstrap_download" "$CANONICAL_STATE_DATABASE"
echo "Bootstrapped canonical state from the reviewed live VPS database."
