#!/usr/bin/env bash
# Deploy validated SQLite and public exports as a single versioned VPS release.
set -euo pipefail

: "${VPS_SSH_PRIVATE_KEY:?VPS_SSH_PRIVATE_KEY is required}"
: "${VPS_SSH_KNOWN_HOSTS:?VPS_SSH_KNOWN_HOSTS is required}"
: "${VPS_HOST:?VPS_HOST is required}"
: "${VPS_USER:?VPS_USER is required}"
: "${VPS_PORT:=22}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
: "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required}"

if [[ ! "$VPS_HOST" =~ ^[A-Za-z0-9.-]+$ ]] \
  || [[ ! "$VPS_USER" =~ ^[A-Za-z_][A-Za-z0-9._-]*$ ]] \
  || [[ ! "$VPS_PORT" =~ ^[0-9]{1,5}$ ]] \
  || ((10#$VPS_PORT < 1 || 10#$VPS_PORT > 65535)) \
  || [[ ! "$GITHUB_RUN_ID" =~ ^[0-9]+$ ]] \
  || [[ ! "$GITHUB_RUN_ATTEMPT" =~ ^[0-9]+$ ]]; then
  echo "VPS deployment configuration is missing or invalid." >&2
  exit 2
fi
for required_file in data/opportunities.db \
  data/exports/open-opportunities.csv data/exports/open-opportunities.json; do
  if [[ ! -s "$required_file" ]]; then
    echo "Validated deployment file is missing or empty: $required_file" >&2
    exit 1
  fi
done
for sidecar in data/opportunities.db-wal data/opportunities.db-shm data/opportunities.db-journal; do
  if [[ -e "$sidecar" ]]; then
    echo "Checkpoint and close the local SQLite database before deployment." >&2
    exit 1
  fi
done

created_ssh_dir=false
if [[ -n "${CANONICAL_STATE_SSH_DIR:-}" ]]; then
  ssh_dir=$CANONICAL_STATE_SSH_DIR
else
  ssh_dir=$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/opportunities-deploy-ssh.XXXXXXXX")
  created_ssh_dir=true
fi
private_key="$ssh_dir/id_ed25519"
known_hosts="$ssh_dir/known_hosts"
root=/srv/european-tech-opportunities-2027/data
release_id="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
staging="$root/.incoming/$release_id"
ssh_target="${VPS_USER}@${VPS_HOST}"
ssh_options=(
  -i "$private_key" -p "$VPS_PORT" -o BatchMode=yes -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$known_hosts"
  -o ConnectTimeout=20 -o ConnectionAttempts=1
  -o ServerAliveInterval=15 -o ServerAliveCountMax=2
)
scp_options=(
  -i "$private_key" -P "$VPS_PORT" -o BatchMode=yes -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$known_hosts"
  -o ConnectTimeout=20 -o ConnectionAttempts=1
  -o ServerAliveInterval=15 -o ServerAliveCountMax=2
)
prepared=false
cleanup() {
  # Leave immutable releases untouched, even if pointer promotion was interrupted.
  if [[ "$prepared" == true && -s "$private_key" ]]; then
    ssh "${ssh_options[@]}" "$ssh_target" "rm -rf '$staging'" >/dev/null 2>&1 || true
  fi
  rm -f "$private_key" "$known_hosts"
  if [[ "$created_ssh_dir" == true ]]; then
    rmdir "$ssh_dir" 2>/dev/null || true
  fi
}

install -d -m 700 "$ssh_dir"
for credential in "$private_key" "$known_hosts"; do
  if [[ -e "$credential" || -L "$credential" ]]; then
    echo "SSH credential path already exists; use an empty dedicated directory." >&2
    exit 1
  fi
done
trap cleanup EXIT
printf '%s\n' "$VPS_SSH_PRIVATE_KEY" >"$private_key"
printf '%s\n' "$VPS_SSH_KNOWN_HOSTS" >"$known_hosts"
chmod 600 "$private_key" "$known_hosts"

database_sha=$(sha256sum data/opportunities.db | cut -d ' ' -f 1)
csv_sha=$(sha256sum data/exports/open-opportunities.csv | cut -d ' ' -f 1)
json_sha=$(sha256sum data/exports/open-opportunities.json | cut -d ' ' -f 1)

# A unique run/attempt owns its uploads. Do not overwrite a prior partial upload.
ssh "${ssh_options[@]}" "$ssh_target" \
  "test ! -e '$staging' && install -d -m 700 '$staging/exports'"
prepared=true
scp "${scp_options[@]}" data/opportunities.db "$ssh_target:$staging/opportunities.db"
scp "${scp_options[@]}" data/exports/open-opportunities.csv \
  "$ssh_target:$staging/exports/open-opportunities.csv"
scp "${scp_options[@]}" data/exports/open-opportunities.json \
  "$ssh_target:$staging/exports/open-opportunities.json"

# Only fixed paths, validated numeric IDs and locally computed digests enter this command.
ssh "${ssh_options[@]}" "$ssh_target" \
  "RELEASE_DATA_DIR='$root' RELEASE_ID='$release_id' DATABASE_SHA='$database_sha' CSV_SHA='$csv_sha' JSON_SHA='$json_sha' bash -s" \
  <scripts/activate_canonical_release.sh
