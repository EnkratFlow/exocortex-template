#!/bin/bash
# Quick status check - optimized for speed (sub-5 seconds)
# Provides essential info without deep processing

echo "=== BRIEF STATUS CHECK ==="
echo

# Current time and date context
NOW=$(date '+%H:%M')
TODAY=$(date '+%a %b %d')
echo "⏰ $TODAY at $NOW"

# Quick git status (no processing, just raw info)
if git rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    if [ "$UNCOMMITTED" -gt 0 ]; then
        echo "📝 Git: $BRANCH ($UNCOMMITTED uncommitted)"
    else
        echo "📝 Git: $BRANCH (clean)"
    fi
fi

# Quick task check (no JSON parsing, just raw output)
echo "📋 Task Status:"
if [ -f ".exocortex/scripts/get_next_task.sh" ]; then
    TASK_OUTPUT=$(.exocortex/scripts/get_next_task.sh 2>/dev/null | grep -E '"task_title":|"section":' | head -2)
    if [ -n "$TASK_OUTPUT" ]; then
        echo "   Next task available"
    else
        echo "   No active tasks"
    fi
else
    echo "   Task system unavailable"
fi

# Quick interrupt count
if [ -f ".exocortex/control/INTERRUPTS.md" ]; then
    INTERRUPTS=$(grep "^## " .exocortex/control/INTERRUPTS.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$INTERRUPTS" -gt 0 ]; then
        echo "⚠️  $INTERRUPTS captured interrupts (need '/groom')"
    fi
fi

# Quick decision count  
if [ -f ".exocortex/OPEN_DECISIONS.md" ]; then
    DECISIONS=$(grep "^## " .exocortex/OPEN_DECISIONS.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$DECISIONS" -gt 0 ]; then
        echo "🤔 $DECISIONS open decisions"
    fi
fi

# Memory system availability
if [ -f ".exocortex/scripts/get_rightnow_memory.py" ]; then
    echo "🧠 Memory system: ready"
else
    echo "🧠 Memory system: unavailable"
fi

echo
echo "=== READY FOR ACTION ==="