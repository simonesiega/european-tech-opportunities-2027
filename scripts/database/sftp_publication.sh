#!/usr/bin/env bash
# Sourced by canonical_state_store.sh; all commands have explicit status handling.
: "${work_dir:?Publication work directory is required}"

publication_command() {
  local phase=$1 object=$2 command=$3 status
  if printf '%s\n' "$command" | raw_sftp >"$work_dir/sftp-result" 2>"$work_dir/sftp-error"; then
    return 0
  else
    status=$?
  fi
  echo "Publication phase=$phase object=${object#"$VPS_BACKUP_REMOTE_ROOT/"} failed (status=$status)." >&2
  # 255 also covers authentication and host-key errors. Only known transport
  # diagnostics qualify; never print the raw host-sensitive SSH diagnostic.
  if ((status == 255)) && grep -Eiq 'connection (closed|reset|timed out)|broken pipe|operation timed out|connection refused|no route to host' "$work_dir/sftp-error" \
    && ! grep -Eiq 'permission denied|host key|authentication|bad permissions' "$work_dir/sftp-error"; then
    return 255
  fi
  return 1
}

publication_retry() {
  local attempt=$1 status=$2
  if ((status != 255 || attempt >= 3)); then
    echo "Publication stopped; preserve local bundle and remote staging for investigation." >&2
    return 1
  fi
  echo "Transient transport failure; retry $((attempt + 1))/3 after remote-state reconciliation." >&2
  sleep "$((attempt * 2))"
}

# A successful parent listing, never a failed get, proves absence.
publication_exists() {
  local object=$1 phase=$2
  local status
  if publication_command "$phase" "$object" "ls -1 \"${object%/*}\""; then
    :
  else
    status=$?
    if ((status == 255)); then return 255; fi
    return 2
  fi
  grep -Fxq "$object" "$work_dir/sftp-result" || grep -Fxq "${object##*/}" "$work_dir/sftp-result"
}

publication_download() {
  local object=$1 destination=$2 phase=$3 attempt status
  for attempt in 1 2 3; do
    if publication_command "$phase" "$object" "get \"$object\" \"$destination\""; then
      return 0
    else
      status=$?
    fi
    publication_retry "$attempt" "$status" || return 1
  done
}

publication_directories() {
  local key=$1 path="$VPS_BACKUP_REMOTE_ROOT" part attempt status
  local -a parts
  IFS='/' read -r -a parts <<<"${key%/*}"
  for part in "${parts[@]}"; do
    path="$path/$part"
    for attempt in 1 2 3; do
      if publication_exists "$path" directories; then
        # cd proves an existing entry really is a traversable directory.
        if publication_command directories "$path" "cd \"$path\""; then
          break
        else
          status=$?
        fi
      else
        status=$?
        if ((status == 1)); then
          if publication_command directories "$path" "mkdir \"$path\""; then
            break
          else
            status=$?
          fi
        fi
      fi
      publication_retry "$attempt" "$status" || return 1
    done
  done
}

publication_file() {
  local source=$1 final=$2 temporary=$3 mutable=${4:-false} previous=${5:-}
  local attempt status final_exists temporary_exists
  for attempt in 1 2 3; do
    final_exists=false
    temporary_exists=false
    if publication_exists "$final" inspect-final; then
      final_exists=true
    else
      status=$?
      if ((status != 1)); then
        publication_retry "$attempt" "$status" || return 1
        continue
      fi
    fi
    if publication_exists "$temporary" inspect-staging; then
      temporary_exists=true
    else
      status=$?
      if ((status != 1)); then
        publication_retry "$attempt" "$status" || return 1
        continue
      fi
    fi
    echo "Publication object=${final#"$VPS_BACKUP_REMOTE_ROOT/"} final=$final_exists staging=$temporary_exists." >&2
    if [[ "$final_exists" == true ]]; then
      publication_download "$final" "$work_dir/remote-comparison" inspect-content || return 1
      if cmp -s "$source" "$work_dir/remote-comparison"; then
        echo "Publication phase already complete; recovered verified remote object." >&2
        if [[ "$temporary_exists" == true ]]; then
          publication_download "$temporary" "$work_dir/remote-comparison" inspect-leftover || return 1
          local leftover_size
          leftover_size=$(wc -c <"$work_dir/remote-comparison")
          if ! cmp -s -n "$leftover_size" "$source" "$work_dir/remote-comparison"; then
            echo "Conflicting leftover staging; preserve and investigate." >&2
            return 1
          fi
          echo "Verified leftover staging prefix; preserving it for manual cleanup." >&2
        fi
        return 0
      fi
      if [[ "$mutable" != true ]]; then
        echo "Immutable remote object conflict; refusing overwrite." >&2
        return 1
      fi
      if [[ ! -s "$previous" ]] || ! cmp -s "$previous" "$work_dir/remote-comparison"; then
        echo "Latest pointer changed unexpectedly; refusing rollback or overwrite." >&2
        return 1
      fi
    fi
    if [[ "$temporary_exists" == true ]]; then
      publication_download "$temporary" "$work_dir/remote-comparison" inspect-staging-content || return 1
    fi
    if [[ "$temporary_exists" != true ]] || ! cmp -s "$source" "$work_dir/remote-comparison"; then
      # Repair only a proven truncated prefix of this bundle, never unknown bytes.
      if [[ "$temporary_exists" == true ]]; then
        local staged_size source_size
        staged_size=$(wc -c <"$work_dir/remote-comparison")
        source_size=$(wc -c <"$source")
        if ((staged_size >= source_size)) || ! cmp -s -n "$staged_size" "$source" "$work_dir/remote-comparison"; then
          echo "Conflicting staging object; preserve and investigate." >&2
          return 1
        fi
      fi
      if publication_command upload "$temporary" "put \"$source\" \"$temporary\""; then
        :
      else
        status=$?
        publication_retry "$attempt" "$status" || return 1
        continue
      fi
      publication_download "$temporary" "$work_dir/remote-comparison" verify-staging || return 1
      if ! cmp -s "$source" "$work_dir/remote-comparison"; then
        echo "Uploaded staging bytes differ; refusing promotion." >&2
        return 1
      fi
    fi
    if publication_command promote "$final" "rename \"$temporary\" \"$final\""; then
      publication_download "$final" "$work_dir/remote-comparison" confirm-promotion || return 1
      if cmp -s "$source" "$work_dir/remote-comparison"; then
        return 0
      fi
      echo "Promoted bytes differ; refusing further publication." >&2
      return 1
    else
      status=$?
    fi
    publication_retry "$attempt" "$status" || return 1
  done
  echo "Publication confirmation exhausted." >&2
  return 1
}
