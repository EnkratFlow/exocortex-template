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

# ── POST to RAG API if key is configured ────────────────────────────────────
# Resolves key from env vars or ~/.exocortex/.env — silently skips if not set.
_load_rag_key() {
    local env_file="${HOME}/.exocortex/.env"
    [[ -z "${RAG_API_KEY:-}" ]] && \
        RAG_API_KEY="$(grep -m1 '^RAG_API_KEY_PERSONAL=' "$env_file" 2>/dev/null | cut -d= -f2- | tr -d "'\"" || true)"
    [[ -z "${RAG_API_KEY:-}" ]] && \
        RAG_API_KEY="$(grep -m1 '^ENKRATFLOW_RAG_API_KEY=' "$env_file" 2>/dev/null | cut -d= -f2- | tr -d "'\"" || true)"
    [[ -z "${RAG_API_KEY:-}" ]] && \
        RAG_API_KEY="$(grep -m1 '^RAG_API_KEY=' "$env_file" 2>/dev/null | cut -d= -f2- | tr -d "'\"" || true)"
}

_load_rag_key
RAG_API_URL="${RAG_API_URL:-$(grep -m1 '^RAG_API_URL=' "${HOME}/.exocortex/.env" 2>/dev/null | cut -d= -f2- | tr -d "'\"" || true)}"
RAG_API_URL="${RAG_API_URL:-https://rag-e-api.enkratflow.ai}"
PROJECT="${PROJECT:-$(basename "$PWD")}"

if [[ -n "${RAG_API_KEY:-}" ]]; then
    CONTENT="# Interrupt: ${INTERRUPT_TYPE} — ${TIMESTAMP}

${INTERRUPT_TEXT}

**Type:** ${INTERRUPT_TYPE}
**Project:** ${PROJECT}
**Captured:** ${TIMESTAMP}"

    PAYLOAD="$(python3 -c "
import json, sys
payload = {
    'content': sys.stdin.read(),
    'title': 'Interrupt: ${INTERRUPT_TYPE} — ${TIMESTAMP}',
    'metadata': {
        'source': 'exocortex_interrupt',
        'client': 'capture_interrupt',
        'project': '${PROJECT}',
        'interrupt_type': '${INTERRUPT_TYPE}',
        'memory_tier': 'hot',
    }
}
print(json.dumps(payload))
" <<< "$CONTENT")"

    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "${RAG_API_URL}/api/rag/ingest" \
        -H "Authorization: Bearer ${RAG_API_KEY}" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        --max-time 10 2>/dev/null || echo "000")

    if [[ "$HTTP_STATUS" =~ ^2 ]]; then
        echo "  ✓ Synced to RAG API"
    else
        echo "  ⚠ RAG sync skipped (status: ${HTTP_STATUS}) — will retry on next bulk sync"
    fi
else
    echo "  — RAG sync skipped (no key set — add RAG_API_KEY to ~/.exocortex/.env)"
fi