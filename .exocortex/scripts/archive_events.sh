#!/bin/bash
# Archives events older than 7 days to keep events/ directory clean
# Run manually or via cron job (monthly recommended)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXOCORTEX_DIR="$(dirname "$SCRIPT_DIR")"
EVENTS_DIR="$EXOCORTEX_DIR/events"
ARCHIVE_DIR="$EXOCORTEX_DIR/events/archive"

echo "📦 Archiving old events..."

# Create archive directory if it doesn't exist
mkdir -p "$ARCHIVE_DIR"

# Find events older than 7 days
if date -v-7d &>/dev/null; then
    # macOS
    SEVEN_DAYS_AGO=$(date -v-7d +%s)
else
    # Linux
    SEVEN_DAYS_AGO=$(date -d "7 days ago" +%s)
fi

ARCHIVED_COUNT=0

# Process each event file
for EVENT_FILE in "$EVENTS_DIR"/*.md; do
    # Skip if no files found
    [ -e "$EVENT_FILE" ] || continue

    # Skip if already in archive
    [[ "$EVENT_FILE" == *"/archive/"* ]] && continue

    # Get file modification time
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        FILE_TIME=$(stat -f %m "$EVENT_FILE")
    else
        # Linux
        FILE_TIME=$(stat -c %Y "$EVENT_FILE")
    fi

    # Check if older than 7 days
    if [ "$FILE_TIME" -lt "$SEVEN_DAYS_AGO" ]; then
        # Extract date from filename (YYYY-MM-DD_HH-MM-SS_...)
        FILENAME=$(basename "$EVENT_FILE")
        DATE_PART=${FILENAME:0:10}  # Extract YYYY-MM-DD
        YEAR=${DATE_PART:0:4}
        MONTH=${DATE_PART:5:2}

        # Create year/month archive directory
        DEST_DIR="$ARCHIVE_DIR/$YEAR/$MONTH"
        mkdir -p "$DEST_DIR"

        # Move file to archive
        mv "$EVENT_FILE" "$DEST_DIR/"
        echo "  ✓ Archived: $FILENAME → archive/$YEAR/$MONTH/"
        ARCHIVED_COUNT=$((ARCHIVED_COUNT + 1))
    fi
done

if [ "$ARCHIVED_COUNT" -eq 0 ]; then
    echo "✓ No events older than 7 days to archive"
else
    echo "✅ Archived $ARCHIVED_COUNT event(s) older than 7 days"
    echo ""
    echo "Archive structure:"
    tree -L 3 "$ARCHIVE_DIR" 2>/dev/null || find "$ARCHIVE_DIR" -type d | head -10
fi

echo ""
echo "Active events (last 7 days):"
ls -1 "$EVENTS_DIR"/*.md 2>/dev/null | wc -l | xargs echo "  Total:" || echo "  Total: 0"
