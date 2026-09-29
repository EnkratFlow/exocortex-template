#!/bin/bash
# Reads all memory files in order, outputs content + metadata JSON.
# Warns when the derived Session Context is older than its event evidence.

set -u

EXOCORTEX=".exocortex"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# A read-only failure is a warning, not authority to mutate or skip orientation.
PYTHONDONTWRITEBYTECODE=1 python3 "$SCRIPT_DIR/refresh_rollups.py" --check --project-root "$PWD" >/dev/null 2>&1
freshness_status=$?
if [ "$freshness_status" -ne 0 ]; then
  echo "MEMORY_FRESHNESS_WARNING: generated context coverage is stale or unverified; inspect refresh_rollups.py --check --json and reconcile source events with live Git." >&2
fi

# Count files and lines
FILE_COUNT=0
LINE_COUNT=0
MEMORY_CONTENT=""

# Read each file
for file in MEMORY.md PROJECT_MEMORY.md LESSONS.md SESSION_CONTEXT.md TODO.md; do
  if [ -f "$EXOCORTEX/$file" ]; then
    FILE_COUNT=$((FILE_COUNT + 1))
    LINES=$(wc -l < "$EXOCORTEX/$file" | xargs)
    LINE_COUNT=$((LINE_COUNT + LINES))
    
    echo "=== $file ==="
    cat "$EXOCORTEX/$file"
    echo ""
  fi
done

# Output metadata as JSON at end
echo "---METADATA---"
echo "{\"file_count\": $FILE_COUNT, \"line_count\": $LINE_COUNT}"
