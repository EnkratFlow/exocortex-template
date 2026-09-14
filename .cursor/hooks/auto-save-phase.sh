#!/bin/bash
# Reminder-only phase hook. It never writes, saves, checkpoints, synchronizes,
# chooses a provider, or claims authority. Unknown input shapes fail silent.
# The filename is retained only for editor compatibility; "auto-save" is a
# legacy name and does not describe this reminder-only behavior.

set -u

input="$(command cat)"
if [[ -z "$input" ]]; then
  exit 0
fi

desc="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    value = json.load(sys.stdin)
except (json.JSONDecodeError, TypeError):
    raise SystemExit(0)
paths = (
    ("description",), ("subagent_description",), ("agent_description",),
    ("task_description",), ("name",), ("subagent", "description"),
    ("input", "description"),
)
for path in paths:
    current = value
    for key in path:
        if not isinstance(current, dict):
            current = None
            break
        current = current.get(key)
    if isinstance(current, str) and current:
        print(current)
        break
' 2>/dev/null || true)"

if [[ ! "$desc" =~ [Pp]hase[[:space:]-]*[0-9]+ ]]; then
  exit 0
fi

clean_desc="$(printf '%s' "$desc" | tr -d '\n\r"' | head -c 200)"
python3 - "$clean_desc" <<'PY'
import json
import sys

description = sys.argv[1]
message = (
    f'Phase complete: "{description}". Consider whether a local narrative '
    'save would improve handoff quality. Do not save automatically. A save is '
    'not a lifecycle checkpoint and never authorizes external sync.'
)
print(json.dumps({"followup_message": message}, sort_keys=True))
PY
