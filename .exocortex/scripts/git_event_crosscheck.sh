#!/usr/bin/env bash
# Cross-check one exact project-local event against live Git without mutation.

set -euo pipefail

EVENT=""
EXPECTED_SHA=""
EVENTS_DIR=".exocortex/events"

usage() {
  echo "Usage: $0 [--event <path> | --latest] [--expected-sha <40-char SHA>]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --event) EVENT="${2:-}"; shift 2 ;;
    --latest)
      EVENT="$(find "$EVENTS_DIR" -maxdepth 1 -type f -name '????-??-??_??-??-??_*.md' -print 2>/dev/null | LC_ALL=C sort | tail -1)"
      shift
      ;;
    --expected-sha) EXPECTED_SHA="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done

[[ -n "$EVENT" && -f "$EVENT" ]] || usage

EVENT_REAL="$(cd "$(dirname "$EVENT")" && pwd -P)/$(basename "$EVENT")"
EVENTS_REAL="$(cd "$EVENTS_DIR" && pwd -P)"
case "$EVENT_REAL" in
  "$EVENTS_REAL"/*) ;;
  *) echo '{"ok":false,"code":"event_outside_project_store"}'; exit 2 ;;
esac

HEAD_SHA="$(git rev-parse HEAD)"
BRANCH="$(git branch --show-current)"
DIRTY_COUNT="$(git status --porcelain | wc -l | tr -d ' ')"

if [[ -n "$EXPECTED_SHA" && ! "$EXPECTED_SHA" =~ ^[a-f0-9]{40}$ ]]; then
  echo '{"ok":false,"code":"invalid_expected_sha"}'
  exit 2
fi

if [[ -n "$EXPECTED_SHA" ]]; then
  if grep -Fq -- "$EXPECTED_SHA" "$EVENT"; then
    EXPECTED_PRESENT=true
  else
    EXPECTED_PRESENT=false
  fi
else
  EXPECTED_PRESENT=null
fi

python3 - "$EVENT_REAL" "$HEAD_SHA" "$BRANCH" "$DIRTY_COUNT" "$EXPECTED_SHA" "$EXPECTED_PRESENT" <<'PY'
import json, sys
event, head, branch, dirty, expected, present = sys.argv[1:]
print(json.dumps({
    "ok": present != "false",
    "event": event,
    "head_sha": head,
    "branch": branch,
    "dirty_count": int(dirty),
    "expected_sha": expected or None,
    "expected_sha_present": None if present == "null" else present == "true",
}, sort_keys=True))
PY

[[ "$EXPECTED_PRESENT" != false ]]
