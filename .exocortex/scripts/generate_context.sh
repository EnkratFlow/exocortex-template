#!/bin/bash
# Generates SESSION_CONTEXT.md from events/ as an explicit derived-view refresh.
# Event creation, /save, /work, and handoff do not invoke it implicitly.

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXOCORTEX_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$EXOCORTEX_DIR")"
EVENTS_DIR="$EXOCORTEX_DIR/events"
OUTPUT_FILE="$EXOCORTEX_DIR/SESSION_CONTEXT.md"

# Find events from last 7 days (short-term memory)
# macOS date command compatibility
if date -v-7d &>/dev/null; then
    # macOS
    SEVEN_DAYS_AGO=$(date -v-7d +%Y-%m-%d)
else
    # Linux
    SEVEN_DAYS_AGO=$(date -d "7 days ago" +%Y-%m-%d)
fi

echo "📅 Finding events since $SEVEN_DAYS_AGO..."

# Find all event files within last 7 days, sorted by timestamp (newest first)
EVENTS=$(find "$EVENTS_DIR" -maxdepth 1 -name "*.md" -type f -newermt "$SEVEN_DAYS_AGO" 2>/dev/null | sort -r)

# Count events
EVENT_COUNT=$(echo "$EVENTS" | grep -c "." || echo "0")

if [ "$EVENT_COUNT" -eq 0 ]; then
    echo "⚠️  No events found in last 7 days"
    exit 0
fi

echo "✓ Found $EVENT_COUNT event(s) in last 7 days"

# Read project name (written by init-project.sh)
PROJECT_NAME=$(cat "$EXOCORTEX_DIR/.project-name" 2>/dev/null || basename "$PROJECT_ROOT")

# Generate SESSION_CONTEXT.md
cat > "$OUTPUT_FILE" << 'HEADER'
# SESSION_CONTEXT – REPLACE_PROJECT

**Last Updated:** REPLACE_DATE
**Generated from events:** Last 7 days (REPLACE_COUNT events)

---

## 🟢 RIGHT NOW

HEADER

# Replace placeholders
sed -i.bak "s/REPLACE_DATE/$(date '+%B %d, %Y')/g" "$OUTPUT_FILE"
sed -i.bak "s/REPLACE_COUNT/$EVENT_COUNT/g" "$OUTPUT_FILE"
sed -i.bak "s/REPLACE_PROJECT/$PROJECT_NAME/g" "$OUTPUT_FILE"
rm -f "$OUTPUT_FILE.bak"

# Add events to SESSION_CONTEXT (most recent first).
# Use `while read` rather than `for FILE in $EVENTS` so event paths that
# contain spaces (e.g. a project installed at "My Project/.exocortex/") are
# preserved as single entries instead of being word-split on whitespace.
FIRST_EVENT=true
while IFS= read -r EVENT_FILE; do
    [ -z "$EVENT_FILE" ] && continue
    if [ "$FIRST_EVENT" = false ]; then
        echo "" >> "$OUTPUT_FILE"
        echo "---" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
    fi
    FIRST_EVENT=false

    # Extract metadata
    TIMESTAMP=$(grep "^timestamp:" "$EVENT_FILE" | cut -d' ' -f2)
    MACHINE=$(grep "^machine:" "$EVENT_FILE" | cut -d' ' -f2)
    EDITOR=$(grep "^editor:" "$EVENT_FILE" | cut -d' ' -f2)
    BRANCH=$(grep "^branch:" "$EVENT_FILE" | cut -d' ' -f2)

    # Format timestamp for display
    if [ "$(uname)" = "Darwin" ]; then
        # macOS
        DISPLAY_TIME=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$TIMESTAMP" "+%B %d at %I:%M %p" 2>/dev/null || echo "$TIMESTAMP")
    else
        # Linux
        DISPLAY_TIME=$(date -d "$TIMESTAMP" "+%B %d at %I:%M %p" 2>/dev/null || echo "$TIMESTAMP")
    fi

    echo "**Event:** $DISPLAY_TIME • $MACHINE • $EDITOR • Branch: \`$BRANCH\`" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"

    # Add event content (skip metadata section - everything after first ---)
    sed -n '/^---$/,//p' "$EVENT_FILE" | tail -n +2 >> "$OUTPUT_FILE"
done <<< "$EVENTS"

# Add footer with older history reference
cat >> "$OUTPUT_FILE" << 'FOOTER'

---

## 📅 OLDER HISTORY

For work older than 7 days, use the `/history` command.

You can also browse events manually:
```bash
ls -lt .exocortex/events/
```

Or search for keywords:
```bash
grep -r "authentication" .exocortex/events/
```

---

## 📚 RECENT WORK (Last 7 Days)

The sections above show your active work from the last 7 days. This is your **short-term memory** - the context you need to stay in flow.

For older work (7+ days), that content has been moved to **long-term memory**. Use the `/history` command to search through it.

**Phase 2 (Future):** When RAG API integration is complete, you'll be able to query semantically:
- "What did I work on related to trading psychology?"
- "Show me all authentication work across projects"
- "When did I last work on circuit breaker?"

---

**Session Status:** Active development. Event system operational.
FOOTER

echo "✅ SESSION_CONTEXT.md regenerated from $EVENT_COUNT event(s)"
