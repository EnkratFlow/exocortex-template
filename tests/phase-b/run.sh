#!/bin/bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TEMP_ROOT_INPUT="/tmp"
[ -d "$TEMP_ROOT_INPUT" ] || { echo "temporary root does not exist" >&2; exit 2; }
TEMP_ROOT="$(cd "$TEMP_ROOT_INPUT" && pwd -P)"
HOME_REAL=""
if [ -d "${HOME:-}" ]; then
    HOME_REAL="$(cd "$HOME" && pwd -P)"
fi
case "$ROOT/" in "$TEMP_ROOT/"*) echo "template root cannot be inside the evidence temporary root" >&2; exit 2 ;; esac
case "$TEMP_ROOT/" in "$ROOT/"*) echo "evidence temporary root cannot be inside the template" >&2; exit 2 ;; esac
if [ -n "$HOME_REAL" ]; then
    case "$HOME_REAL/" in "$TEMP_ROOT/"*) echo "user home cannot be inside the evidence temporary root" >&2; exit 2 ;; esac
    case "$TEMP_ROOT/" in "$HOME_REAL/"*) echo "evidence temporary root cannot be inside user home" >&2; exit 2 ;; esac
fi
if git -C "$TEMP_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "evidence temporary root cannot be an existing repository" >&2
    exit 2
fi
if [ "$#" -gt 1 ]; then
    echo "Usage: run.sh [NEW_ABSOLUTE_EVIDENCE_DIR]" >&2
    exit 2
fi

if [ "$#" -eq 1 ]; then
    EVIDENCE="$1"
    case "$EVIDENCE" in /*) ;; *) echo "evidence path must be absolute" >&2; exit 2 ;; esac
    [ ! -e "$EVIDENCE" ] || { echo "evidence path must not already exist" >&2; exit 2; }
    EVIDENCE_PARENT="$(dirname "$EVIDENCE")"
    [ -d "$EVIDENCE_PARENT" ] || { echo "evidence parent must already exist" >&2; exit 2; }
    EVIDENCE_PARENT_REAL="$(cd "$EVIDENCE_PARENT" && pwd -P)"
    [ "$EVIDENCE_PARENT_REAL" = "$TEMP_ROOT" ] || { echo "evidence must be an immediate child of the temporary root" >&2; exit 2; }
    case "$(basename "$EVIDENCE")" in exo-phase-b-evidence.*) ;; *) echo "invalid evidence directory name" >&2; exit 2 ;; esac
    EVIDENCE="$EVIDENCE_PARENT_REAL/$(basename "$EVIDENCE")"
    [ "$EVIDENCE" != "$ROOT" ] || { echo "evidence path cannot be the template root" >&2; exit 2; }
    [ "$EVIDENCE" != "${HOME:-/__no_home__}" ] || { echo "evidence path cannot be user home" >&2; exit 2; }
    mkdir "$EVIDENCE"
else
    EVIDENCE="$(mktemp -d "$TEMP_ROOT/exo-phase-b-evidence.XXXXXX")"
fi

FAKE_HOME="$EVIDENCE/fake-home"
DENY_BIN="$EVIDENCE/deny-bin"
PRIVATE_FINGERPRINT="$EVIDENCE/private-fingerprint.input"
umask 077
printf 'phase-b-private-%s-%s\n' "$$" "$(date -u +%s)" > "$PRIVATE_FINGERPRINT"
mkdir -p "$FAKE_HOME"
bash "$ROOT/tests/phase-b/fault_shims.sh" "$DENY_BIN" >/dev/null

python3 "$ROOT/tests/phase-b/hash_tree.py" "$ROOT" --output "$EVIDENCE/candidate-tree.json"

set +e
(cd "$ROOT" && HOME="$FAKE_HOME" PATH="$DENY_BIN:$PATH" EXOCORTEX_PRIVATE_FINGERPRINT_FILE="$PRIVATE_FINGERPRINT" bash tests/run_tests.sh) >"$EVIDENCE/installer.log" 2>&1
echo "$?" > "$EVIDENCE/installer.rc"
(cd "$ROOT" && HOME="$FAKE_HOME" PATH="$DENY_BIN:$PATH" EXOCORTEX_AUDIT_EVIDENCE_PATH="$EVIDENCE/egress-audit.jsonl" bash .exocortex/scripts/tests/test_orchestration_protocol.sh) >"$EVIDENCE/orchestration.log" 2>&1
echo "$?" > "$EVIDENCE/orchestration.rc"
(cd "$ROOT" && HOME="$FAKE_HOME" PATH="$DENY_BIN:$PATH" bash .exocortex/scripts/tests/test_event_tooling.sh) >"$EVIDENCE/event-tooling.log" 2>&1
echo "$?" > "$EVIDENCE/event-tooling.rc"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/phase-b/verify_evidence.py" "$EVIDENCE"
rc=$?
echo "Complete Exocortex safety evidence: $EVIDENCE"
exit "$rc"
