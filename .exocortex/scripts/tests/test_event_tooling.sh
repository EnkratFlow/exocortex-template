#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/exo-event-test.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
PROJECT="$TMP/project"
FAKE_BIN="$TMP/bin"
CURL_LOG="$TMP/curl.log"
mkdir -p "$PROJECT/.exocortex/scripts" "$PROJECT/.exocortex/control" "$PROJECT/.exocortex/events" "$FAKE_BIN"
cp "$ROOT/.exocortex/scripts/create_event.sh" "$PROJECT/.exocortex/scripts/"
cp "$ROOT/.exocortex/scripts/generate_context.sh" "$PROJECT/.exocortex/scripts/"
cp "$ROOT/.exocortex/scripts/read_memory_stack.sh" "$PROJECT/.exocortex/scripts/"
cp "$ROOT/.exocortex/scripts/capture_interrupt.sh" "$PROJECT/.exocortex/scripts/"
cp "$ROOT/.exocortex/scripts/auto_snapshot.sh" "$PROJECT/.exocortex/scripts/"
cp "$ROOT/.exocortex/scripts/sync_event_to_vault.sh" "$PROJECT/.exocortex/scripts/"
cp "$ROOT/.exocortex/scripts/egress_guard.py" "$PROJECT/.exocortex/scripts/"
cp "$ROOT/.exocortex/scripts/authority_guard.py" "$PROJECT/.exocortex/scripts/"
printf '# Session Context\n' > "$PROJECT/.exocortex/SESSION_CONTEXT.md"
printf '# Project Memory\n' > "$PROJECT/.exocortex/PROJECT_MEMORY.md"
printf '# TODO\n' > "$PROJECT/.exocortex/TODO.md"
printf '# Lessons\n' > "$PROJECT/.exocortex/LESSONS.md"
printf '# Interrupts\n' > "$PROJECT/.exocortex/control/INTERRUPTS.md"
printf '# Narrative save fixture\n' > "$TMP/body.md"
printf '#!/bin/bash\nprintf "called\\n" >> "%s"\nexit 99\n' "$CURL_LOG" > "$FAKE_BIN/curl"
chmod +x "$FAKE_BIN/curl" "$PROJECT/.exocortex/scripts/"*.sh
git -C "$PROJECT" init -q
git -C "$PROJECT" -c user.email=test@example.invalid -c user.name=test add .
git -C "$PROJECT" -c user.email=test@example.invalid -c user.name=test commit -qm fixture

context_before="$(shasum -a 256 "$PROJECT/.exocortex/SESSION_CONTEXT.md" | awk '{print $1}')"
(cd "$PROJECT" && PATH="$FAKE_BIN:$PATH" bash .exocortex/scripts/create_event.sh --body-file "$TMP/body.md") >/dev/null
[ "$(find "$PROJECT/.exocortex/events" -type f -name '*.md' | wc -l | tr -d ' ')" = "1" ]
[ ! -e "$CURL_LOG" ]
context_after="$(shasum -a 256 "$PROJECT/.exocortex/SESSION_CONTEXT.md" | awk '{print $1}')"
[ "$context_before" = "$context_after" ]
[ ! -e "$PROJECT/.exocortex/SESSION_CONTEXT.regen.md" ]

freshness_output="$(cd "$PROJECT" && bash .exocortex/scripts/read_memory_stack.sh 2>&1 >/dev/null)"
grep -Fq 'MEMORY_FRESHNESS_WARNING:' <<< "$freshness_output"

(cd "$PROJECT" && PATH="$FAKE_BIN:$PATH" bash .exocortex/scripts/create_event.sh --body-file "$TMP/body.md") >/dev/null
[ "$(find "$PROJECT/.exocortex/events" -type f -name '*.md' | wc -l | tr -d ' ')" = "2" ]
(cd "$PROJECT" && bash .exocortex/scripts/generate_context.sh) >/dev/null
grep -Fq 'Narrative save fixture' "$PROJECT/.exocortex/SESSION_CONTEXT.md"
freshness_output="$(cd "$PROJECT" && bash .exocortex/scripts/read_memory_stack.sh 2>&1 >/dev/null)"
[ -z "$freshness_output" ]

if (cd "$PROJECT" && bash .exocortex/scripts/create_event.sh --body-file) >/dev/null 2>&1; then
    echo "missing --body-file value unexpectedly succeeded" >&2
    exit 1
fi
if (cd "$PROJECT" && bash .exocortex/scripts/create_event.sh --body-file "$TMP/body.md" --refresh-context) >/dev/null 2>&1; then
    echo "event helper unexpectedly accepted context-refresh authority" >&2
    exit 1
fi

(cd "$PROJECT" && PATH="$FAKE_BIN:$PATH" bash .exocortex/scripts/capture_interrupt.sh "fictional fixture" IDEA) >/dev/null
grep -Fq 'fictional fixture' "$PROJECT/.exocortex/control/INTERRUPTS.md"
[ ! -e "$CURL_LOG" ]

before="$(find "$PROJECT/.exocortex/events" -type f | wc -l | tr -d ' ')"
(cd "$PROJECT" && PATH="$FAKE_BIN:$PATH" bash .exocortex/scripts/auto_snapshot.sh) >/dev/null
after="$(find "$PROJECT/.exocortex/events" -type f | wc -l | tr -d ' ')"
[ "$before" = "$after" ]

if (cd "$PROJECT" && PATH="$FAKE_BIN:$PATH" bash .exocortex/scripts/sync_event_to_vault.sh .exocortex/events/missing.md) >/dev/null 2>&1; then
    echo "legacy implicit sync unexpectedly succeeded" >&2
    exit 1
fi
[ ! -e "$CURL_LOG" ]

echo "event tooling: local-only, separate-context, freshness, and reminder-only checks passed"
