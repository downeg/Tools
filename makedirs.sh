#!/usr/bin/env bash
# makedirs.sh — create a pentest workspace directory structure.

set -euo pipefail

usage() {
  echo "Usage: $0 <directory-name>" >&2
  exit 1
}

# Require exactly one argument.
[[ $# -eq 1 ]] || usage

ROOT="$1"

# Reject empty/whitespace-only.
[[ -n "${ROOT//[[:space:]]/}" ]] || usage

# Create root and subdirectories.
mkdir -p -- "$ROOT"/{enum,loot,exploit,privesc,proof,report}
