#!/bin/bash
# End of Day — Data Gathering Script
# Collects structured facts for AI reflection. No AI calls, no interactive prompts.
# Output is consumed by the daily-end.json AI step.
#
# Gathers: today's events (full content), git activity, TODO state,
#          interrupts, uncommitted changes, session timing.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXOCORTEX_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$EXOCORTEX_DIR")"
EVENTS_DIR="$EXOCORTEX_DIR/events"
TODAY=$(date '+%Y-%m-%d')

cd "$PROJECT_ROOT"

echo "=== END OF DAY DATA: $TODAY ==="
echo ""

# ── 1. Today's Events (full content for AI to mine) ───────
echo "## TODAY'S EVENTS"
TODAY_EVENTS=$(find "$EVENTS_DIR" -maxdepth 1 -name "${TODAY}*.md" -type f 2>/dev/null | sort)
EVENT_COUNT=0
if [ -n "$TODAY_EVENTS" ]; then
    EVENT_COUNT=$(echo "$TODAY_EVENTS" | wc -l | tr -d ' ')
fi

if [ "$EVENT_COUNT" -gt 0 ]; then
    echo "Found $EVENT_COUNT event(s) for $TODAY:"
    echo ""
    for EVENT_FILE in $TODAY_EVENTS; do
        BASENAME=$(basename "$EVENT_FILE")
        echo "--- EVENT: $BASENAME ---"
        # Print the event body (skip metadata block, skip trailing Git State)
        sed -n '/^---$/,/^## Git State/{/^---$/d; /^## Git State/d; p;}' "$EVENT_FILE" | head -80
        echo ""
    done
else
    echo "No events recorded today."
    echo ""
fi

# ── 2. Git Activity ────────────────────────────────────────
echo "## GIT ACTIVITY"
if git rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo "Branch: $BRANCH"
    echo ""

    # Today's commits (with full message first line)
    TODAY_COMMITS=$(git log --since="$TODAY 00:00" --format="%h %s" 2>/dev/null || true)
    if [ -n "$TODAY_COMMITS" ]; then
        COMMIT_COUNT=$(echo "$TODAY_COMMITS" | wc -l | tr -d ' ')
        echo "Commits today ($COMMIT_COUNT):"
        echo "$TODAY_COMMITS" | sed 's/^/  /'
    else
        echo "No commits today."
    fi
    echo ""

    # Aggregate diff stats for today's commits
    FIRST_COMMIT_TODAY=$(git log --since="$TODAY 00:00" --reverse --format="%H" 2>/dev/null | head -1)
    if [ -n "$FIRST_COMMIT_TODAY" ]; then
        echo "Aggregate diff stats:"
        git diff --stat "${FIRST_COMMIT_TODAY}^..HEAD" 2>/dev/null | tail -3 | sed 's/^/  /' || echo "  (could not compute)"
    fi
    echo ""

    # Uncommitted changes
    MODIFIED_COUNT=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MODIFIED_COUNT" -gt 0 ]; then
        echo "⚠️  Uncommitted changes: $MODIFIED_COUNT file(s)"
        git status --porcelain 2>/dev/null | head -15 | sed 's/^/  /'
        if [ "$MODIFIED_COUNT" -gt 15 ]; then
            echo "  ... and $((MODIFIED_COUNT - 15)) more"
        fi
    else
        echo "✅ Working tree clean."
    fi
else
    echo "Not a git repository."
fi
echo ""

# ── 3. TODO State ──────────────────────────────────────────
echo "## TODO STATE"
TODO_FILE="$EXOCORTEX_DIR/TODO.md"
if [ -f "$TODO_FILE" ]; then
    # In Progress
    IN_PROGRESS=$(sed -n '/## 🟧 In Progress/,/^## /p' "$TODO_FILE" | grep "^- " | grep -v "empty" || true)
    if [ -n "$IN_PROGRESS" ]; then
        IN_PROGRESS_COUNT=$(echo "$IN_PROGRESS" | wc -l | tr -d ' ')
        echo "In Progress ($IN_PROGRESS_COUNT):"
        echo "$IN_PROGRESS" | sed 's/^/  /'
    else
        echo "In Progress: (none)"
    fi
    echo ""

    # Ready count
    READY_COUNT=$(sed -n '/## 🟨 Ready/,/^## /p' "$TODO_FILE" 2>/dev/null | grep -c "^\- \[" 2>/dev/null || true)
    READY_COUNT=${READY_COUNT:-0}
    echo "Ready queue: $READY_COUNT item(s)"
    echo ""

    # Done section (recent completions)
    DONE_ITEMS=$(sed -n '/## ✅ Done/,/^## /p' "$TODO_FILE" | grep "^\- " | head -5 || true)
    if [ -n "$DONE_ITEMS" ]; then
        DONE_COUNT=$(echo "$DONE_ITEMS" | wc -l | tr -d ' ')
        echo "Recently completed ($DONE_COUNT):"
        echo "$DONE_ITEMS" | sed 's/^/  /'
    fi
else
    echo "No TODO.md found."
fi
echo ""

# ── 4. Unresolved Interrupts ──────────────────────────────
echo "## UNRESOLVED INTERRUPTS"
INTERRUPTS_FILE="$EXOCORTEX_DIR/control/INTERRUPTS.md"
if [ -f "$INTERRUPTS_FILE" ]; then
    # Total interrupt headings
    TOTAL_INTERRUPTS=$(grep -c "^## [0-9]" "$INTERRUPTS_FILE" 2>/dev/null || true)
    TOTAL_INTERRUPTS=${TOTAL_INTERRUPTS:-0}
    RESOLVED=$(grep -c "Status.*✅" "$INTERRUPTS_FILE" 2>/dev/null || true)
    RESOLVED=${RESOLVED:-0}
    PENDING=$((TOTAL_INTERRUPTS - RESOLVED))

    echo "Total: $TOTAL_INTERRUPTS | Resolved: $RESOLVED | Pending: $PENDING"
    echo ""

    if [ "$PENDING" -gt 0 ]; then
        echo "Pending items (most recent):"
        # Show interrupt headers that are NOT followed by a ✅ resolved status
        # Simple approach: show the last 5 headers from the file
        grep "^## 2026" "$INTERRUPTS_FILE" | tail -5 | sed 's/^/  /'
    fi
else
    echo "No INTERRUPTS.md found."
fi
echo ""

# ── 5. Session Timing ─────────────────────────────────────
echo "## SESSION TIMING"
if [ "$EVENT_COUNT" -gt 0 ]; then
    FIRST_EVENT=$(echo "$TODAY_EVENTS" | head -1 | xargs basename 2>/dev/null)
    LAST_EVENT=$(echo "$TODAY_EVENTS" | tail -1 | xargs basename 2>/dev/null)
    FIRST_TIME=$(echo "$FIRST_EVENT" | cut -d'_' -f2 | tr '-' ':')
    LAST_TIME=$(echo "$LAST_EVENT" | cut -d'_' -f2 | tr '-' ':')
    echo "First event: $FIRST_TIME UTC"
    echo "Last event: $LAST_TIME UTC"
fi
FIRST_COMMIT_TIME=$(git log --since="$TODAY 00:00" --reverse --format="%ai" 2>/dev/null | head -1 | cut -d' ' -f2 | cut -d':' -f1-2)
LAST_COMMIT_TIME=$(git log --since="$TODAY 00:00" --format="%ai" 2>/dev/null | head -1 | cut -d' ' -f2 | cut -d':' -f1-2)
if [ -n "$FIRST_COMMIT_TIME" ]; then
    echo "First commit: $FIRST_COMMIT_TIME"
    echo "Last commit: $LAST_COMMIT_TIME"
fi
echo "Closing time: $(date '+%H:%M %Z')"
echo ""

echo "=== END OF DATA ==="

# ── 6. Other Active Projects ───────────────────────
# Scan sibling dirs in the same parent for other exocortex projects
# that had git commits today. Lets the AI update their memory too.
echo "## OTHER ACTIVE PROJECTS"
PARENT_DIR="$(dirname "$PROJECT_ROOT")"
CURRENT_PROJECT=$(basename "$PROJECT_ROOT")
FOUND_OTHER=0

for sibdir in "$PARENT_DIR"/*/; do
    [ -d "$sibdir" ] || continue
    sibname=$(basename "$sibdir")
    [ "$sibname" = "$CURRENT_PROJECT" ] && continue
    [ -d "${sibdir}.exocortex" ] || continue
    [ -d "${sibdir}.git" ] || git -C "$sibdir" rev-parse --git-dir >/dev/null 2>&1 || continue

    sibling_commits=$(git -C "$sibdir" log --since="$TODAY 00:00" --format="%h %s" 2>/dev/null || true)
    [ -z "$sibling_commits" ] && continue

    FOUND_OTHER=$((FOUND_OTHER + 1))
    commit_count=$(echo "$sibling_commits" | wc -l | tr -d ' ')
    echo ""
    echo "### $sibname ($commit_count commit(s) today)"
    echo "$sibling_commits" | head -10 | sed 's/^/  /'

    # Include their current memory context so AI can update it
    sib_ctx="${sibdir}.exocortex/SESSION_CONTEXT.md"
    sib_todo="${sibdir}.exocortex/TODO.md"
    if [ -f "$sib_ctx" ]; then
        echo ""
        echo "  SESSION_CONTEXT (RIGHT NOW section):"
        sed -n '/RIGHT NOW/,/^## /p' "$sib_ctx" 2>/dev/null | head -15 | sed 's/^/    /'
    fi
    if [ -f "$sib_todo" ]; then
        in_prog=$(sed -n '/## .*In Progress/,/^## /p' "$sib_todo" 2>/dev/null | grep '^- ' | head -5 || true)
        if [ -n "$in_prog" ]; then
            echo ""
            echo "  TODO (In Progress):"
            echo "$in_prog" | sed 's/^/    /'
        fi
    fi
done

if [ "$FOUND_OTHER" -eq 0 ]; then
    echo "None — all commits today were in $CURRENT_PROJECT."
fi
echo ""

echo "=== END OF FULL DATA ==="