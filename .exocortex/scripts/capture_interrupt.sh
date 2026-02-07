#!/bin/bash
# Capture interrupt during active work
# Usage: capture_interrupt.sh "interrupt text" [type]

INTERRUPT_TEXT="$1"
INTERRUPT_TYPE="${2:-GENERAL}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
INTERRUPTS_FILE=".exocortex/control/INTERRUPTS.md"

if [ -z "$INTERRUPT_TEXT" ]; then
    echo "Usage: capture_interrupt.sh 'interrupt description' [type]"
    echo "Types: BUG, IDEA, THOUGHT, CONCERN, QUESTION"
    exit 1
fi

# Ensure interrupts file exists
if [ ! -f "$INTERRUPTS_FILE" ]; then
    cat > "$INTERRUPTS_FILE" << 'EOF'
---
# INTERRUPTS

**Purpose:** Capture ideas, issues, observations, and concerns discovered during active execution without disrupting current work.

This file is a **parking lot**, not a commitment list.

## What Belongs Here
- Ideas discovered mid-task
- Potential refactors or improvements
- Bugs noticed but not addressed
- Architecture or design concerns
- Questions that require later thought
- "This feels wrong" observations

**Authority:** Human-only. This file has no governance power.
---

EOF
fi

# Add the interrupt
echo "## $TIMESTAMP | $INTERRUPT_TYPE | $INTERRUPT_TEXT" >> "$INTERRUPTS_FILE"
echo

# Success message
echo "✓ Interrupt captured: $INTERRUPT_TEXT"
echo "  Type: $INTERRUPT_TYPE"
echo "  File: $INTERRUPTS_FILE"
echo "  Use '/groom' to process interrupts later"