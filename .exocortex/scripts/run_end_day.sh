#!/bin/bash
# End of day workflow
# Reviews work and provides closure

echo "=== END OF DAY WORKFLOW ==="
echo

TODAY=$(date '+%Y-%m-%d')
echo "📅 Closing day: $TODAY"
echo

# Review today's activity
echo "📝 Today's Activity:"
if [ -f ".exocortex/scripts/get_rightnow_memory.py" ]; then
    TODAY_WORK=$(python3 .exocortex/scripts/get_rightnow_memory.py | grep "$TODAY")
    if [ -n "$TODAY_WORK" ]; then
        echo "$TODAY_WORK" | sed 's/^/   /'
    else
        echo "   No recorded activity for today"
    fi
else
    echo "   Memory system not available"
fi
echo

# Check git commits today
if git rev-parse --git-dir >/dev/null 2>&1; then
    TODAY_COMMITS=$(git log --since="$TODAY 00:00" --oneline 2>/dev/null)
    if [ -n "$TODAY_COMMITS" ]; then
        echo "📊 Git Activity Today:"
        echo "$TODAY_COMMITS" | sed 's/^/   /' | head -n 5
        echo
    fi
fi

# Check current work state
MODIFIED_FILES=""
CURRENT_BRANCH=""
if git rev-parse --git-dir >/dev/null 2>&1; then
    MODIFIED_FILES=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
fi

echo "📍 Current State:"
if [ "$MODIFIED_FILES" -gt 0 ]; then
    echo "   ⚠️  $MODIFIED_FILES uncommitted changes"
    echo "   Consider: git add . && git commit -m 'End of day checkpoint'"
fi
if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ]; then
    echo "   📍 On branch: $CURRENT_BRANCH"
fi
echo

# Check for captured interrupts
if [ -f ".exocortex/control/INTERRUPTS.md" ]; then
    INTERRUPT_COUNT=$(grep "^## " .exocortex/control/INTERRUPTS.md 2>/dev/null | wc -l | tr -d ' ')
    if [ "$INTERRUPT_COUNT" -gt 0 ]; then
        echo "💡 $INTERRUPT_COUNT interrupts captured today"
        echo "   Consider running '/groom' to process them"
        echo
    fi
fi

# Review TODO status
if [ -f ".exocortex/TODO.md" ]; then
    IN_PROGRESS_COUNT=$(sed -n '/## 🟧 In Progress/,/^## /p' .exocortex/TODO.md | grep "^- " | grep -v "empty" | wc -l | tr -d ' ')
    READY_COUNT=$(sed -n '/## 🟨 Ready/,/^## /p' .exocortex/TODO.md | grep "^- " | grep -v "empty" | wc -l | tr -d ' ')
    
    echo "📋 TODO Status:"
    echo "   In Progress: $IN_PROGRESS_COUNT"
    echo "   Ready: $READY_COUNT"
    echo
fi

# Suggest next steps
echo "=== END OF DAY COMPLETE ==="
echo
echo "🌅 Tomorrow morning:"
echo "   • '/morning' - Start with morning workflow"
echo "   • '/scrum' - Detailed daily standup"
echo "   • '/work' - Load context and begin work"
echo

if [ "$MODIFIED_FILES" -gt 0 ]; then
    echo "⚠️  Don't forget to commit your changes!"
fi

# Optional: Create end-of-day event
if [ -f ".exocortex/scripts/create_event.sh" ]; then
    echo "📓 Create end-of-day event? (y/n):"
    read -p "   " CREATE_EVENT
    if [ "$CREATE_EVENT" = "y" ] || [ "$CREATE_EVENT" = "Y" ]; then
        .exocortex/scripts/create_event.sh "End of day - $TODAY"
    fi
fi