#!/bin/bash
# Outputs JSON with git state and last work context

BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
UNCOMMITTED=$(git status --short 2>/dev/null | wc -l | xargs)

# Get last work from SESSION_CONTEXT (RIGHT NOW section)
LAST_WORK=""
STATUS=""

if [ -f ".exocortex/SESSION_CONTEXT.md" ]; then
  # Extract work focus line
  LAST_WORK=$(sed -n '/## 🟢 RIGHT NOW/,/^##/p' .exocortex/SESSION_CONTEXT.md | grep -i "work focus\|active work" | head -1 | sed 's/^.*: //' | sed 's/\*\*//g')
  
  # Extract status line
  STATUS=$(sed -n '/## 🟢 RIGHT NOW/,/^##/p' .exocortex/SESSION_CONTEXT.md | grep -i "^Status:" | head -1 | sed 's/^.*: //' | sed 's/🟢 //g' | sed 's/🔄 //g' | sed 's/⏸️ //g')
fi

# Get last event date/time
LAST_EVENT=""
if [ -d ".exocortex/events" ]; then
  LAST_EVENT=$(ls -t .exocortex/events/*.md 2>/dev/null | head -1 | xargs basename | sed 's/_macbook.*//; s/_guys.*//; s/_desktop.*//' | sed 's/_/ /g')
fi

# Output JSON
cat << EOF
{
  "last_work": "${LAST_WORK:-Unknown}",
  "status": "${STATUS:-Unknown}",
  "uncommitted_count": $UNCOMMITTED,
  "branch": "$BRANCH",
  "last_event": "${LAST_EVENT:-Unknown}"
}
EOF
