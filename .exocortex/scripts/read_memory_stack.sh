#!/bin/bash
# Reads all memory files in order, outputs content + metadata JSON.
# Warns when the derived Session Context is older than its event evidence.

set -u

EXOCORTEX=".exocortex"

if [ -d "$EXOCORTEX/events" ]; then
  if [ ! -f "$EXOCORTEX/SESSION_CONTEXT.md" ]; then
    if [ -n "$(find "$EXOCORTEX/events" -maxdepth 1 -type f -name '*.md' -print -quit 2>/dev/null)" ]; then
      echo "MEMORY_FRESHNESS_WARNING: Session Context is missing; use the events as current evidence and refresh context only if explicitly requested." >&2
    fi
  elif [ -n "$(find "$EXOCORTEX/events" -maxdepth 1 -type f -name '*.md' -newer "$EXOCORTEX/SESSION_CONTEXT.md" -print -quit 2>/dev/null)" ]; then
    echo "MEMORY_FRESHNESS_WARNING: newer project events exist; Session Context is derived and stale. Prefer the events and live Git state, and refresh context only if explicitly requested." >&2
  fi
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
