#!/usr/bin/env bash
# Sync a single Exocortex event file directly to the EnkratFlow RAG API.
# Called after /save creates an event.
#
# Usage: sync_event_to_vault.sh <path_to_event_file>
# Example: sync_event_to_vault.sh .exocortex/events/2026-02-16_14-30-00.md
#
# Idempotent: safe to run multiple times on the same file.
# Does NOT block /save if the RAG API is unreachable (exits 0 on failure).
#
# Key resolution order:
#   1. ENKRATFLOW_RAG_API_KEY env var
#   2. RAG_API_KEY_PERSONAL in ~/.exocortex/.env
#   3. RAG_API_KEY in ~/.exocortex/.env or ./.env

set -euo pipefail

EVENT_FILE="${1:-}"
RAG_API_URL="${RAG_API_URL:-https://rag-e-api.enkratflow.ai}"
GLOBAL_ENV="${HOME}/.exocortex/.env"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] sync_event: $*"; }

# ── Resolve API key ──────────────────────────────────────────────────────────
load_key_from_file() {
    local file="$1" key_name="$2"
    [[ -f "$file" ]] && grep -m1 "^${key_name}=" "$file" 2>/dev/null | cut -d= -f2- | tr -d "'\"" || true
}

RAG_API_KEY="${ENKRATFLOW_RAG_API_KEY:-}"
if [[ -z "$RAG_API_KEY" ]]; then
    RAG_API_KEY="$(load_key_from_file "$GLOBAL_ENV" "RAG_API_KEY_PERSONAL")"
fi
if [[ -z "$RAG_API_KEY" ]]; then
    RAG_API_KEY="$(load_key_from_file "$GLOBAL_ENV" "ENKRATFLOW_RAG_API_KEY")"
fi
if [[ -z "$RAG_API_KEY" ]]; then
    RAG_API_KEY="$(load_key_from_file "$GLOBAL_ENV" "RAG_API_KEY")"
fi
if [[ -z "$RAG_API_KEY" ]]; then
    RAG_API_KEY="$(load_key_from_file ".env" "RAG_API_KEY")"
fi

if [[ -z "$RAG_API_KEY" ]]; then
    log "No RAG API key found — add RAG_API_KEY_PERSONAL to ~/.exocortex/.env"
    exit 0
fi

# ── Validate event file ──────────────────────────────────────────────────────
if [[ -z "$EVENT_FILE" ]]; then
    log "Usage: sync_event_to_vault.sh <path_to_event_file>"
    exit 0
fi

if [[ "$EVENT_FILE" != /* ]]; then
    EVENT_FILE="$(cd "$(dirname "$EVENT_FILE")" && pwd)/$(basename "$EVENT_FILE")"
fi

if [[ ! -f "$EVENT_FILE" ]]; then
    log "Event file not found: $EVENT_FILE"
    exit 0
fi

# ── Derive project name from path ────────────────────────────────────────────
# .exocortex/events/ lives inside the project directory
PROJECT="$(basename "$(cd "$(dirname "$EVENT_FILE")/../.." && pwd)")"

# ── POST to RAG API ──────────────────────────────────────────────────────────
CONTENT="$(cat "$EVENT_FILE")"
FILENAME="$(basename "$EVENT_FILE")"
TITLE="${FILENAME%.md}"

# Build JSON payload — jq not required, use python for safe escaping
PAYLOAD="$(python3 -c "
import json, sys
content = sys.stdin.read()
payload = {
    'content': content,
    'title': '$TITLE',
    'metadata': {
        'source': 'exocortex_event',
        'client': 'sync_event_to_vault',
        'project': '$PROJECT',
        'filename': '$FILENAME',
        'memory_tier': 'hot',
        'auto_tagged': True,
    }
}
print(json.dumps(payload))
" <<< "$CONTENT")"

HTTP_STATUS=$(curl -s -o /tmp/sync_event_response.json -w "%{http_code}" \
    -X POST "${RAG_API_URL}/api/rag/ingest" \
    -H "Authorization: Bearer ${RAG_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" \
    --max-time 15 2>/dev/null || echo "000")

if [[ "$HTTP_STATUS" =~ ^2 ]]; then
    DOC_ID=$(python3 -c "import json; d=json.load(open('/tmp/sync_event_response.json')); print(d.get('document_id','?'))" 2>/dev/null || echo "?")
    log "Ingested to RAG API OK (${HTTP_STATUS}, doc: ${DOC_ID}, project: ${PROJECT})"
elif [[ "$HTTP_STATUS" == "000" ]]; then
    log "RAG API unreachable — will be picked up by next bulk sync"
else
    BODY=$(cat /tmp/sync_event_response.json 2>/dev/null || echo "")
    log "RAG API returned ${HTTP_STATUS}: ${BODY} — will retry on next bulk sync"
fi

# ── Optional: copy to local vault if configured ──────────────────────────────
# Set EXOCORTEX_VAULT_DIR in ~/.exocortex/.env to enable local vault copies.
# Example: EXOCORTEX_VAULT_DIR=~/vault/exocortex_events
if [[ -n "${EXOCORTEX_VAULT_DIR:-}" ]]; then
    VAULT_RAW="${EXOCORTEX_VAULT_DIR}"
    if [[ -d "$(dirname "$VAULT_RAW")" ]]; then
        DEST_DIR="${VAULT_RAW}/$(date '+%Y/%m')"
        mkdir -p "$DEST_DIR"
        cp -p "$EVENT_FILE" "${DEST_DIR}/$(basename "$EVENT_FILE")" 2>/dev/null && log "Copied to vault" || true
    fi
fi

exit 0
