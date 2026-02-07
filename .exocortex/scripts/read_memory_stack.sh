#!/bin/bash
# Reads all memory files in order, outputs content + metadata JSON

EXOCORTEX=".exocortex"

# Count files and lines
FILE_COUNT=0
LINE_COUNT=0
MEMORY_CONTENT=""

# Read each file
for file in MEMORY.md PROJECT_MEMORY.md LESSONS.md SESSION_CONTEXT.md TODO.md; do
  if [ -f "$EXOCORTEX/$file" ]; then
    FILE_COUNT=$((FILE_COUNT + 1))
    LINES=$(wc -l < "$EXOCORTEX/$file" | xargs)
    LINE_COUNT=$((LINE_COUNT + LINES))
    
    echo "=== $file ==="
    cat "$EXOCORTEX/$file"
    echo ""
  fi
done

# Output metadata as JSON at end
echo "---METADATA---"
echo "{\"file_count\": $FILE_COUNT, \"line_count\": $LINE_COUNT}"
