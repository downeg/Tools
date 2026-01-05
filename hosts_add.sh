#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <fqdn> <ip>"
  echo "Example: $0 host.example.local 10.10.10.10"
}

if [[ $# -ne 2 ]]; then
  usage >&2
  exit 1
fi

fqdn="$1"
ip="$2"

# Basic IPv4 sanity check (not exhaustive).
if [[ ! "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "Error: '$ip' does not look like an IPv4 address." >&2
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
ts="$(date +'%Y%m%d-%H%M%S')"
backup_file="${backup_dir}/hosts.${ts}"

# Ensure sudo is available and authenticate up-front (prompts for password if needed).
if ! command -v sudo >/dev/null 2>&1; then
  echo "Error: sudo is not installed." >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  sudo -v
fi

# Create backup directory with safe permissions and correct ownership.
sudo install -d -m 700 -o "$invoking_user" -g "$invoking_user" "$backup_dir"

# Backup /etc/hosts (preserve mode/ownership/timestamps where possible).
sudo cp -a /etc/hosts "$backup_file"
sudo chown "$invoking_user:$invoking_user" "$backup_file"

# Append mapping only if the exact mapping is not already present.
if sudo grep -qE "^${ip}[[:space:]]+${fqdn}([[:space:]]+|$)" /etc/hosts; then
  echo "Entry already present: ${ip} ${fqdn}"
else
  printf "%s\t%s\n" "$ip" "$fqdn" | sudo tee -a /etc/hosts >/dev/null
  echo "Appended: ${ip} ${fqdn}"
fi

echo "Backup created: ${backup_file}"
