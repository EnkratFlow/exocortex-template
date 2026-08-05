#!/bin/bash
# Creates an event file with auto-detected metadata.
# AI provides content body via stdin or --body-file.
# Handles: timestamp, machine, editor, branch, git state, and filename.
# Context refresh and external sync are always separate explicit actions.
#
# Usage:
#   echo "content" | bash .exocortex/scripts/create_event.sh
#   bash .exocortex/scripts/create_event.sh --body-file /tmp/event_body.md
#
# Output: prints the created event file path to stdout (last line)
# Prefer stdin when no caller-owned body file is needed. This helper never
# creates or leaves a preview/body file of its own.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXOCORTEX_DIR="$(dirname "$SCRIPT_DIR")"
EVENTS_DIR="$EXOCORTEX_DIR/events"

# ── Parse args ──────────────────────────────────────────────
BODY_FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --body-file)
      [ "$#" -ge 2 ] || { echo "Error: --body-file requires a path" >&2; exit 1; }
      BODY_FILE="$2"
      shift 2
      ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

# ── Read body content ───────────────────────────────────────
if [ -n "$BODY_FILE" ]; then
  BODY=$(cat "$BODY_FILE")
elif [ ! -t 0 ]; then
  BODY=$(cat)
else
  echo "Error: provide content via stdin or --body-file" >&2
  exit 1
fi

# ── Auto-detect metadata ───────────────────────────────────
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
FILE_TS=$(date -u +%Y-%m-%d_%H-%M-%S)

# Machine detection
ARCH=$(uname -m)
OS=$(uname -s)
if [ "$OS" = "Darwin" ]; then
  MACHINE="macbook"
elif [ "$OS" = "Linux" ]; then
  MACHINE="linux"
else
  MACHINE="unknown"
fi

# Editor detection (best effort)
if [ -n "${CURSOR_TRACE_ID:-}" ] || [ -n "${CURSOR_SESSION:-}" ]; then
  EDITOR_NAME="cursor"
elif [ -n "${VSCODE_PID:-}" ] || { [ -n "${TERM_PROGRAM:-}" ] && [ "$TERM_PROGRAM" = "vscode" ]; }; then
  EDITOR_NAME="vscode"
else
  EDITOR_NAME="cursor"  # default for this project
fi

# Git metadata
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
PROJECT=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "unknown")

# Git state (captured once, included in event)
GIT_LOG=$(git log --oneline -5 2>/dev/null || echo "(no commits)")
GIT_STATUS_SHORT=$(git status --short 2>/dev/null || echo "(no status)")
GIT_DIFF_STAT=$(git diff --stat 2>/dev/null || echo "(no changes)")

# ── Build event file ───────────────────────────────────────
mkdir -p "$EVENTS_DIR"

BASE_FILENAME="${FILE_TS}_${MACHINE}-${EDITOR_NAME}"
FILENAME="${BASE_FILENAME}.md"
EVENT_PATH="$EVENTS_DIR/$FILENAME"
COLLISION_INDEX=0
while ! (set -o noclobber; : > "$EVENT_PATH") 2>/dev/null; do
  COLLISION_INDEX=$((COLLISION_INDEX + 1))
  FILENAME="${BASE_FILENAME}_$(printf '%02d' "$COLLISION_INDEX").md"
  EVENT_PATH="$EVENTS_DIR/$FILENAME"
done

cat > "$EVENT_PATH" << METADATA_EOF
<!-- Event Metadata -->
timestamp: $TIMESTAMP
machine: $MACHINE
editor: $EDITOR_NAME
project: $PROJECT
branch: $BRANCH

---

METADATA_EOF

# Append AI-provided body
echo "$BODY" >> "$EVENT_PATH"

# Append git state section (so AI doesn't need to gather it)
cat >> "$EVENT_PATH" << GIT_EOF

## Git State

**Last Commits:**
$GIT_LOG

**Branch:** $BRANCH

**Uncommitted Changes:**
\`\`\`
$GIT_STATUS_SHORT
\`\`\`

**Diff Stats:**
\`\`\`
$GIT_DIFF_STAT
\`\`\`
GIT_EOF

# ── Output ──────────────────────────────────────────────────
echo "✅ Event saved: .exocortex/events/$FILENAME"
echo "$EVENT_PATH"
