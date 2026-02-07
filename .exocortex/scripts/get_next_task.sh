#!/bin/bash
# Parse TODO.md for next task (In Progress first, then Ready)

TODO_FILE=".exocortex/TODO.md"

if [ ! -f "$TODO_FILE" ]; then
  echo '{"task_title": "No TODO.md found", "task_description": "", "section": "none"}'
  exit 0
fi

# Check In Progress first
IN_PROGRESS=$(sed -n '/## 🟧 In Progress/,/^## /p' "$TODO_FILE" | grep "^- " | grep -v "empty" | head -1)

if [ -n "$IN_PROGRESS" ]; then
  # Extract title and description (format: "- [ ] Title — Description" or "- Title — Description")
  TASK=$(echo "$IN_PROGRESS" | sed 's/^- \[\?\w\?\] \?//')
  TITLE=$(echo "$TASK" | cut -d'—' -f1 | xargs)
  DESC=$(echo "$TASK" | cut -d'—' -f2- | xargs)
  SECTION="In Progress"
else
  # Fall back to Ready
  READY=$(sed -n '/## 🟨 Ready/,/^## /p' "$TODO_FILE" | grep "^- " | grep -v "empty" | head -1)
  TASK=$(echo "$READY" | sed 's/^- \[\?\w\?\] \?//')
  TITLE=$(echo "$TASK" | cut -d'—' -f1 | xargs)
  DESC=$(echo "$TASK" | cut -d'—' -f2- | xargs)
  SECTION="Ready"
fi

# If still empty, check for any non-empty task
if [ -z "$TITLE" ]; then
  TITLE="No active tasks"
  DESC="TODO is empty or all tasks completed"
  SECTION="none"
fi

# Output JSON (escape quotes in strings)
TITLE=$(echo "$TITLE" | sed 's/"/\\"/g')
DESC=$(echo "$DESC" | sed 's/"/\\"/g')

cat << EOF
{
  "task_title": "$TITLE",
  "task_description": "$DESC",
  "section": "$SECTION"
}
EOF
