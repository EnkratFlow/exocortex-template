#!/bin/bash
# Process interrupts from INTERRUPTS.md into BACKLOG.md or TODO.md
# This is a simplified version - the full version would be interactive

INTERRUPTS_FILE=".exocortex/control/INTERRUPTS.md"
BACKLOG_FILE=".exocortex/control/BACKLOG.md"

echo "=== GROOMING INTERRUPTS ==="
echo

if [ ! -f "$INTERRUPTS_FILE" ]; then
    echo "❌ No interrupts file found: $INTERRUPTS_FILE"
    exit 1
fi

# Count interrupts
INTERRUPT_COUNT=$(grep "^## " "$INTERRUPTS_FILE" 2>/dev/null | wc -l | tr -d ' ')

if [ "$INTERRUPT_COUNT" -eq 0 ]; then
    echo "✅ No interrupts to groom"
    exit 0
fi

echo "📋 Found $INTERRUPT_COUNT interrupts to review"
echo

# Show recent interrupts for context
echo "Recent interrupts:"
grep "^## " "$INTERRUPTS_FILE" | tail -n 5 | sed 's/^/   /'
echo

echo "💡 This is a simplified groom script."
echo "For full interactive grooming, use the AI command '/groom' which will:"
echo "   • Review each interrupt individually"
echo "   • Ask what to do with each one"
echo "   • Move items to BACKLOG, TODO, or delete them"
echo "   • Update all files with your decisions"
echo

echo "Quick actions available:"
echo "   • View all interrupts: cat $INTERRUPTS_FILE"
echo "   • Clear all interrupts: truncate -s 0 $INTERRUPTS_FILE" 
echo "   • Use '/groom' for full interactive processing"

# Ensure backlog file exists
if [ ! -f "$BACKLOG_FILE" ]; then
    cat > "$BACKLOG_FILE" << 'EOF'
# Control Center Backlog

**Purpose:** Investigated interrupts ready for TODO promotion

Items here have been reviewed and are waiting to become actionable tasks.

---

EOF
fi