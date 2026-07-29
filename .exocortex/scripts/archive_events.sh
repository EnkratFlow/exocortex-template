#!/bin/bash
# Read-only archive preview. Moving project memory requires a separate guarded
# writer capability and is intentionally not available through this adapter.

set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EVENTS="$ROOT/.exocortex/events"
count=0
if [[ -d "$EVENTS" ]]; then
  count="$(find "$EVENTS" -type f -name '*.md' -mtime +30 -print 2>/dev/null | wc -l | tr -d ' ')"
fi
echo "Read-only archive preview: $count event(s) are older than 30 days."
echo "No file was moved or deleted; guarded archive mutation is not authorized."
exit 2
