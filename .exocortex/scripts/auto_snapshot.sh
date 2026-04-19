#!/bin/bash
# auto_snapshot.sh — Autonomous exocortex snapshot agent
#
# Runs every 60 minutes via launchd. For each active project:
#   1. Checks if any IDE/editor/terminal is running (skips if machine idle)
#   2. Checks if the project has recent activity (commits or uncommitted changes)
#   3. Checks if a snapshot was written in the last 50 minutes (avoids duplicates)
#   4. Writes a minimal event file to .exocortex/events/ for /daily-end to consume
#
# Config: ~/.exocortex/config  (created by install_autosave.sh)
#   PROJECTS_ROOT=~/code        ← scans this directory for repos with .exocortex
#   SNAPSHOT_INTERVAL_MIN=50    ← minimum minutes between snapshots per repo
#   ACTIVE_HOURS_START=7        ← don't run before this hour (local time)
#   ACTIVE_HOURS_END=23         ← don't run after this hour (local time)
#
# Zero configuration required after install. Add new repos to PROJECTS_ROOT and
# they are picked up automatically. No per-repo changes needed.

set -eo pipefail

# ── Load config ───────────────────────────────────────────
CONFIG_FILE="$HOME/.exocortex/config"
PROJECTS_ROOT="$HOME"
SNAPSHOT_INTERVAL_MIN=50
ACTIVE_HOURS_START=7
ACTIVE_HOURS_END=23

if [ -f "$CONFIG_FILE" ]; then
    while IFS='=' read -r key value; do
        [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
        value="${value//\~/$HOME}"
        case "$key" in
            PROJECTS_ROOT)          PROJECTS_ROOT="$value" ;;
            SNAPSHOT_INTERVAL_MIN)  SNAPSHOT_INTERVAL_MIN="$value" ;;
            ACTIVE_HOURS_START)     ACTIVE_HOURS_START="$value" ;;
            ACTIVE_HOURS_END)       ACTIVE_HOURS_END="$value" ;;
        esac
    done < "$CONFIG_FILE"
fi

# ── Active hours gate ─────────────────────────────────────
CURRENT_HOUR=$(date '+%-H' 2>/dev/null || date '+%H' | sed 's/^0//')
if [ "$CURRENT_HOUR" -lt "$ACTIVE_HOURS_START" ] || [ "$CURRENT_HOUR" -ge "$ACTIVE_HOURS_END" ]; then
    exit 0  # Outside active hours — silent exit
fi

# ── Check if any dev tool is running ─────────────────────
# Only write snapshots when user is actually working.
# Checks for: VS Code, Cursor, Claude Code, terminal session with git
is_dev_active() {
    pgrep -x "Code" >/dev/null 2>&1 && return 0
    pgrep -x "Cursor" >/dev/null 2>&1 && return 0
    pgrep -x "code" >/dev/null 2>&1 && return 0
    pgrep -f "claude" >/dev/null 2>&1 && return 0
    # Check for active terminal with git processes
    pgrep -f "git (status|diff|commit|push|pull|log)" >/dev/null 2>&1 && return 0
    # Check if VS Code helper processes are running (headless / CLI)
    pgrep -f "vscode-server\|code-server\|code Helper" >/dev/null 2>&1 && return 0
    return 1
}

if ! is_dev_active; then
    exit 0  # No dev tool running — silent exit
fi

# ── Scan repos ────────────────────────────────────────────
SNAPSHOT_COUNT=0
NOW_EPOCH=$(date +%s)
NOW_TS=$(date '+%Y-%m-%d_%H-%M-%S')
TODAY=$(date '+%Y-%m-%d')
CURRENT_TIME=$(date '+%H:%M')

# Expand tilde in PROJECTS_ROOT before use
PROJECTS_ROOT="${PROJECTS_ROOT/#\~/$HOME}"

for repo_dir in "$PROJECTS_ROOT"/*/; do
    [ -d "$repo_dir" ] || continue
    [ -d "${repo_dir}.exocortex" ] || continue
    [ -d "${repo_dir}.exocortex/events" ] || continue
    git -C "$repo_dir" rev-parse --git-dir >/dev/null 2>&1 || continue

    REPO_NAME=$(basename "$repo_dir")
    EVENTS_DIR="${repo_dir}.exocortex/events"

    # ── Skip if snapshot already written in last N minutes ──
    LAST_SNAPSHOT=$(ls -t "$EVENTS_DIR"/*_autosave.md 2>/dev/null | head -1)
    if [ -n "$LAST_SNAPSHOT" ]; then
        LAST_MTIME=$(stat -f %m "$LAST_SNAPSHOT" 2>/dev/null || stat -c %Y "$LAST_SNAPSHOT" 2>/dev/null || echo 0)
        MINUTES_AGO=$(( (NOW_EPOCH - LAST_MTIME) / 60 ))
        if [ "$MINUTES_AGO" -lt "$SNAPSHOT_INTERVAL_MIN" ]; then
            continue  # Recent snapshot exists — skip
        fi
    fi

    # ── Check for activity (uncommitted files OR recent commits) ──
    UNCOMMITTED=$(git -C "$repo_dir" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    RECENT_COMMITS=$(git -C "$repo_dir" log --since="8 hours ago" --oneline 2>/dev/null | wc -l | tr -d ' ')

    if [ "$UNCOMMITTED" -eq 0 ] && [ "$RECENT_COMMITS" -eq 0 ]; then
        continue  # No activity in this repo — skip silently
    fi

    # ── Gather state ─────────────────────────────────────
    BRANCH=$(git -C "$repo_dir" branch --show-current 2>/dev/null || echo "unknown")
    LAST_3_COMMITS=$(git -C "$repo_dir" log --oneline -3 2>/dev/null | sed 's/^/  /' || echo "  (none)")
    MODIFIED_FILES=$(git -C "$repo_dir" status --porcelain 2>/dev/null | head -10 | sed 's/^/  /' || echo "  (none)")

    # Recent Claude Code activity for this project (last 2 hours)
    CLAUDE_ACTIVITY=""
    CLAUDE_HISTORY="$HOME/.claude/history.jsonl"
    if [ -f "$CLAUDE_HISTORY" ]; then
        TWO_HOURS_AGO=$((NOW_EPOCH - 7200))
        CLAUDE_COUNT=$(python3 -c "
import json, sys
count = 0
try:
    with open('$CLAUDE_HISTORY') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            obj = json.loads(line)
            ts = obj.get('timestamp', 0) / 1000
            display = str(obj.get('display',''))
            if ts > $TWO_HOURS_AGO and len(display) > 15 and display.strip() not in ['/save','/work','/daily-end','']:
                count += 1
except: pass
print(count)
" 2>/dev/null || echo "0")
        if [ "$CLAUDE_COUNT" -gt 0 ]; then
            CLAUDE_ACTIVITY="  Claude Code: $CLAUDE_COUNT message(s) in the last 2 hours"
        fi
    fi

    # ── Write event file ─────────────────────────────────
    EVENT_FILE="$EVENTS_DIR/${TODAY}_${NOW_TS}_autosave.md"

    cat > "$EVENT_FILE" << EVENTEOF
---
date: $TODAY
time: $CURRENT_TIME
type: auto-snapshot
editor: autosave
repo: $REPO_NAME
---

# Auto-snapshot — $TODAY $CURRENT_TIME

## Git State
- Branch: $BRANCH
- Uncommitted changes: $UNCOMMITTED file(s)
- Recent commits (last 8h): $RECENT_COMMITS

## Last 3 Commits
$LAST_3_COMMITS

## Modified Files
$MODIFIED_FILES
$([ -n "$CLAUDE_ACTIVITY" ] && echo -e "\n## Claude Code Activity\n$CLAUDE_ACTIVITY" || true)

## Note
This snapshot was created automatically. For a richer event with decisions and
context, run /save while in your AI session, or /daily-end at end of day.
EVENTEOF

    SNAPSHOT_COUNT=$((SNAPSHOT_COUNT + 1))
done

# ── Optional macOS notification ───────────────────────────
# Fires after writing snapshots — reminds user to run /save for richer context.
# Stays silent if no snapshots were written (no active repos found).
if [ "$SNAPSHOT_COUNT" -gt 0 ]; then
    if command -v osascript >/dev/null 2>&1; then
        osascript -e "display notification \"Auto-snapshot saved for $SNAPSHOT_COUNT project(s). Run /save in your AI session for richer context.\" with title \"Exocortex\" subtitle \"Auto-snapshot\"" 2>/dev/null || true
    fi
fi

exit 0
