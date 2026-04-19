#!/bin/bash
# Morning context loader - provides comprehensive startup context
# Used by /work command for full context awareness

echo "=== MORNING CONTEXT SCAN ==="
echo

# Enhanced date/time context
TODAY=$(date '+%Y-%m-%d')
DAY_OF_WEEK=$(date '+%A')
TIME_NOW=$(date '+%H:%M')

echo "🗓️  $DAY_OF_WEEK, $TODAY at $TIME_NOW"
echo

# Yesterday's completed work summary
echo "✅ Yesterday's Activity:"
if git rev-parse --git-dir >/dev/null 2>&1; then
    YESTERDAY_COMMITS=$(git log --since="2 days ago" --until="yesterday" --oneline 2>/dev/null | head -3)
    if [ -n "$YESTERDAY_COMMITS" ]; then
        echo "$YESTERDAY_COMMITS" | sed 's/^/   /'
    else
        echo "   No commits yesterday"
    fi
else
    echo "   Git not available"
fi
echo

# Today's git activity (if any)
TODAY_COMMITS=$(git log --since="today" --oneline 2>/dev/null | head -2)
if [ -n "$TODAY_COMMITS" ]; then
    echo "📝 Today's Progress:"
    echo "$TODAY_COMMITS" | sed 's/^/   /'
    echo
fi

# Load current task status
echo "📋 Current Task Status:"
if [ -f ".exocortex/scripts/get_next_task.sh" ]; then
    .exocortex/scripts/get_next_task.sh | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'   Next: {data[\"task_title\"]}')
    if data['section'] != 'none':
        print(f'   Status: {data[\"section\"]}')
except:
    print('   No tasks found')
"
else
    echo "   Task script not available"
fi
echo

# Show recent context (last few days)
echo "🧠 Recent Context:"
if [ -f ".exocortex/scripts/get_rightnow_memory.py" ]; then
    python3 .exocortex/scripts/get_rightnow_memory.py | head -n 10
else
    echo "   Memory system not available"
fi
echo

# Check for urgent interrupts
if [ -f ".exocortex/control/INTERRUPTS.md" ]; then
    INTERRUPT_COUNT=$(grep "^## " .exocortex/control/INTERRUPTS.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$INTERRUPT_COUNT" -gt 0 ]; then
        echo "⚠️  Interrupts: $INTERRUPT_COUNT items captured"
        echo "   Use '/groom' to process them"
        echo
    fi
fi

# Check for open decisions
if [ -f ".exocortex/OPEN_DECISIONS.md" ]; then
    DECISION_COUNT=$(grep "^## " .exocortex/OPEN_DECISIONS.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$DECISION_COUNT" -gt 0 ]; then
        echo "🤔 Open Decisions: $DECISION_COUNT items need resolution"
        echo
    fi
fi

echo "=== READY TO START WORK ==="
echo
echo "Next steps:"
echo "  • '/work' - Load full context and start working"
echo "  • '/groom' - Process captured interrupts" 
echo "  • '/scrum' - Detailed daily standup format"