#!/bin/bash
# Read-only inventory only. Public-v2 updates one exact repository per work item.

set -euo pipefail
ROOT="${1:-}"
[ -n "$ROOT" ] && [ -d "$ROOT" ] || { echo "Usage: update-all-repos.sh ROOT --dry-run" >&2; exit 2; }
[ "${2:-}" = "--dry-run" ] || {
    echo "Denied: batch repository mutation and --yes are retired." >&2
    echo "Run one pinned safe-update rehearsal per repository." >&2
    exit 2
}

find "$ROOT" -maxdepth 4 -type d -name .exocortex -prune 2>/dev/null \
    | sed 's|/\.exocortex$||' \
    | sort -u
echo "Read-only inventory complete; no repository was changed."
