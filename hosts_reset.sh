#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0"
  echo "Resets /etc/hosts by restoring ~/.hosts-backups/original (from the invoking user)."
}

if [[ $# -ne 0 ]]; then
  usage >&2
  exit 1
fi

# Determine the "real" user/home even if invoked via sudo.
invoking_user="${SUDO_USER:-$(id -un)}"
invoking_home="$(getent passwd "$invoking_user" | cut -d: -f6)"
if [[ -z "$invoking_home" || ! -d "$invoking_home" ]]; then
  echo "Error: could not determine home directory for user '$invoking_user'." >&2
  exit 1
fi

backup_dir="${invoking_home}/.hosts-backups"
original_file="${backup_dir}/original"
ts="$(date +'%Y%m%d-%H%M%S')"
backup_file="${backup_dir}/hosts.reset-backup.${ts}"

# Ensure sudo is available and authenticate up-front (prompts for password if needed).
if ! command -v sudo >/dev/null 2>&1; then
  echo "Error: sudo is not installed." >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  sudo -v
fi

# Ensure backup dir exists; enforce safe permissions/ownership.
sudo install -d -m 700 -o "$invoking_user" -g "$invoking_user" "$backup_dir"

if [[ ! -f "$original_file" ]]; then
  echo "Error: original hosts file not found at: $original_file" >&2
  echo "Create it first, e.g.: cp -a /etc/hosts ~/.hosts-backups/original" >&2
  exit 1
fi

# 1) Backup current /etc/hosts with timestamp.
sudo cp -a /etc/hosts "$backup_file"
sudo chown "$invoking_user:$invoking_user" "$backup_file"

# 2) Restore original into /etc/hosts (correct location), preserving original file metadata.
sudo cp -a "$original_file" /etc/hosts

echo "Backup of current hosts created: $backup_file"
echo "Restored original hosts from: $original_file -> /etc/hosts"
