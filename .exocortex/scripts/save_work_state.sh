#!/bin/bash
# Save current work state - quick checkpoint
# Usage: save_work_state.sh [optional description]

WORK_STATE_DESC="$1"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
SESSION_CONTEXT=".exocortex/SESSION_CONTEXT.md"

echo "=== SAVING WORK STATE ==="
echo

# Detect current context
CURRENT_BRANCH=""
MODIFIED_FILES=""
CURRENT_DIR=$(basename "$PWD")

if git rev-parse --git-dir >/dev/null 2>&1; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    MODIFIED_FILES=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
fi

echo "📍 Current Context:"
echo "   Directory: $CURRENT_DIR"
if [ -n "$CURRENT_BRANCH" ]; then
    echo "   Git branch: $CURRENT_BRANCH"
fi
if [ "$MODIFIED_FILES" -gt 0 ]; then
    echo "   Modified files: $MODIFIED_FILES"
fi
echo

# Get current work description if not provided
if [ -z "$WORK_STATE_DESC" ]; then
    echo "💭 Current work state (one sentence):"
    read -p "   What are you focused on right now? " WORK_STATE_DESC
    echo
fi

if [ -z "$WORK_STATE_DESC" ]; then
    echo "❌ No work state description provided"
    exit 1
fi

# Prepare the right now update
RIGHT_NOW_UPDATE="**$TIMESTAMP**: $WORK_STATE_DESC"

if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ]; then
    RIGHT_NOW_UPDATE="$RIGHT_NOW_UPDATE (branch: $CURRENT_BRANCH)"
fi

if [ "$MODIFIED_FILES" -gt 0 ]; then
    RIGHT_NOW_UPDATE="$RIGHT_NOW_UPDATE [$MODIFIED_FILES modified files]"
fi

echo "📝 Work state to save:"
echo "   $RIGHT_NOW_UPDATE"
echo

# Update SESSION_CONTEXT.md if it exists
if [ -f "$SESSION_CONTEXT" ]; then
    # Create backup
    cp "$SESSION_CONTEXT" "${SESSION_CONTEXT}.backup"

    # Add to RIGHT NOW section. Use awk instead of sed to safely handle
    # user input that may contain sed metacharacters (/, \, &, newlines).
    if grep -q "## 🟢 RIGHT NOW" "$SESSION_CONTEXT"; then
        TMP_CTX=$(mktemp)
        awk -v entry="$RIGHT_NOW_UPDATE" '
            /^## 🟢 RIGHT NOW/ { print; print ""; print entry; next }
            { print }
        ' "$SESSION_CONTEXT" > "$TMP_CTX" && mv "$TMP_CTX" "$SESSION_CONTEXT"
        echo "✅ Updated SESSION_CONTEXT.md"
    else
        echo "⚠️  SESSION_CONTEXT.md exists but no RIGHT NOW section found"
        echo "   Adding to end of file..."
        printf '\n## 🟢 RIGHT NOW\n\n%s\n' "$RIGHT_NOW_UPDATE" >> "$SESSION_CONTEXT"
        echo "✅ Added RIGHT NOW section to SESSION_CONTEXT.md"
    fi
else
    echo "⚠️  SESSION_CONTEXT.md not found - creating basic version"
    
    cat > "$SESSION_CONTEXT" << EOF
# Session Context

Generated: $TIMESTAMP

## 🟢 RIGHT NOW

$RIGHT_NOW_UPDATE

## Recent Activity

No previous activity recorded.
EOF
    
    echo "✅ Created SESSION_CONTEXT.md"
fi

echo
echo "=== WORK STATE SAVED ==="
echo
echo "Next steps:"
echo "  • Continue current work"
echo "  • '/work' to reload context after break"
echo "  • '/daily-end' at end of session"

# Optional: Ask about quick lesson learned
echo
echo "💡 Quick lesson learned? (optional, press enter to skip):"
read -p "   " LESSON

if [ -n "$LESSON" ]; then
    LESSONS_FILE=".exocortex/docs/LESSONS.md"
    if [ ! -f "$LESSONS_FILE" ]; then
        echo "# Lessons Learned" > "$LESSONS_FILE"
        echo >> "$LESSONS_FILE"
    fi
    
    echo "- **$TIMESTAMP**: $LESSON" >> "$LESSONS_FILE"
    echo "✅ Lesson saved to $LESSONS_FILE"
fi