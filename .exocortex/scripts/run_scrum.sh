#!/bin/bash
# Daily scrum/standup routine
# Classic format: Yesterday/Today/Blockers

echo "=== DAILY STANDUP ==="
echo

# Get date context
YESTERDAY=$(date -d 'yesterday' '+%Y-%m-%d' 2>/dev/null || date -v-1d '+%Y-%m-%d')
TODAY=$(date '+%Y-%m-%d')

echo "📅 Standup for $TODAY"
echo

# YESTERDAY: What did I do?
echo "✅ YESTERDAY ($YESTERDAY):"
if [ -f ".exocortex/scripts/get_rightnow_memory.py" ]; then
    # Get recent work and filter for yesterday
    YESTERDAY_WORK=$(python3 .exocortex/scripts/get_rightnow_memory.py | grep -A2 -B1 "$YESTERDAY" | head -n 5)
    if [ -n "$YESTERDAY_WORK" ]; then
        echo "$YESTERDAY_WORK" | sed 's/^/   /'
    else
        echo "   No recorded activity found for yesterday"
    fi
else
    echo "   Memory system not available"
fi

# Check git commits from yesterday
if git rev-parse --git-dir >/dev/null 2>&1; then
    YESTERDAY_COMMITS=$(git log --since="$YESTERDAY 00:00" --until="$TODAY 00:00" --oneline 2>/dev/null)
    if [ -n "$YESTERDAY_COMMITS" ]; then
        echo "   Git commits:"
        echo "$YESTERDAY_COMMITS" | sed 's/^/     /' | head -n 3
    fi
fi

echo

# TODAY: What will I do?
echo "🎯 TODAY ($TODAY):"
if [ -f ".exocortex/scripts/get_next_task.sh" ]; then
    NEXT_TASK=$(.exocortex/scripts/get_next_task.sh)
    echo "$NEXT_TASK" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f'   Focus: {data[\"task_title\"]}')
    if data['task_description']:
        print(f'   Details: {data[\"task_description\"]}')
    print(f'   Status: {data[\"section\"]}')
except:
    print('   No current task defined')
"
else
    echo "   Task system not available"
fi

# Check TODO for additional ready items
if [ -f ".exocortex/TODO.md" ]; then
    READY_COUNT=$(sed -n '/## 🟨 Ready/,/^## /p' .exocortex/TODO.md | grep "^- " | grep -v "empty" | wc -l | tr -d ' ')
    if [ "$READY_COUNT" -gt 1 ]; then
        echo "   Also ready: $((READY_COUNT - 1)) additional tasks"
    fi
fi

echo

# BLOCKERS: What's in the way?
echo "🚧 BLOCKERS:"

BLOCKERS_FOUND=0

# Check open decisions
if [ -f ".exocortex/OPEN_DECISIONS.md" ]; then
    DECISION_COUNT=$(grep "^## " .exocortex/OPEN_DECISIONS.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$DECISION_COUNT" -gt 0 ]; then
        echo "   $DECISION_COUNT open decisions need resolution"
        BLOCKERS_FOUND=1
    fi
fi

# Check urgent interrupts
if [ -f ".exocortex/control/INTERRUPTS.md" ]; then
    INTERRUPT_COUNT=$(grep "^## " .exocortex/control/INTERRUPTS.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$INTERRUPT_COUNT" -gt 5 ]; then
        echo "   $INTERRUPT_COUNT interrupts captured - may need grooming"
        BLOCKERS_FOUND=1
    fi
fi

# Check for blocked tasks in TODO
if [ -f ".exocortex/TODO.md" ]; then
    BLOCKED_COUNT=$(sed -n '/## 🚫 Blocked/,/^## /p' .exocortex/TODO.md | grep "^- " | grep -v "empty" | wc -l | tr -d ' ')
    if [ "$BLOCKED_COUNT" -gt 0 ]; then
        echo "   $BLOCKED_COUNT tasks currently blocked"
        BLOCKERS_FOUND=1
    fi
fi

if [ "$BLOCKERS_FOUND" -eq 0 ]; then
    echo "   No significant blockers identified"
fi

echo
echo "=== STANDUP COMPLETE ==="
echo
echo "Next steps:"
echo "  • '/work' - Start working on today's focus"
echo "  • '/groom' - Process interrupts if needed"
echo "  • Check OPEN_DECISIONS.md for resolution items"