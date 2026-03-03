#!/bin/bash
# Post event summary to EnkratFlow-Project hub
# Called automatically by /save workflow
# Fail-safe: If hub doesn't exist, silently exits
# Respects .exocortex/.hub_disabled flag

set -e

EVENT_FILE="$1"
HUB_DIR="$HOME/EnkratFlow/EnkratFlow-Project/.exocortex/hub"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXOCORTEX_DIR="$(dirname "$SCRIPT_DIR")"

# Exit gracefully if hub is explicitly disabled
[ -f "$EXOCORTEX_DIR/.hub_disabled" ] && exit 0

# Exit gracefully if hub doesn't exist (fail-safe)
[ -d "$HUB_DIR" ] || exit 0

# Exit gracefully if event file doesn't exist
[ -f "$EVENT_FILE" ] || exit 0

# Detect project name
if git rev-parse --show-toplevel >/dev/null 2>&1; then
    PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel)")
else
    PROJECT_NAME="unknown"
fi

# Extract timestamp from event filename
# Format: 2026-01-25_14-30-00_machine.md -> 2026-01-25_14-30
FILENAME=$(basename "$EVENT_FILE")
TIMESTAMP=$(echo "$FILENAME" | cut -d'_' -f1-2)

# Extract summary from event file
# Look for "## Summary" section and get first non-empty line after it
SUMMARY=$(grep -A 3 "^## Summary" "$EVENT_FILE" 2>/dev/null | grep -v "^##" | grep -v "^$" | head -n 1 | cut -c1-100)

# Fallback: If no summary found, extract from "## Work Done" or first heading
if [ -z "$SUMMARY" ]; then
    SUMMARY=$(grep -A 3 "^## Work Done\|^## What Got Done\|^# " "$EVENT_FILE" 2>/dev/null | grep -v "^##\|^#" | grep -v "^$" | head -n 1 | cut -c1-100)
fi

# Final fallback: Use filename if still empty
if [ -z "$SUMMARY" ]; then
    SUMMARY="Work session"
fi

# Append to activity stream
echo "$TIMESTAMP | $PROJECT_NAME | $SUMMARY" >> "$HUB_DIR/activity_stream.txt"

# Update project snapshot (last known state)
echo "$TIMESTAMP | $SUMMARY" > "$HUB_DIR/projects/$PROJECT_NAME.txt"

exit 0
