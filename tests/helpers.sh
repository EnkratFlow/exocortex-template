#!/bin/bash
set -u

TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PASS=0
FAIL=0

ok() { echo "  PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }

assert_true() {
    local label="$1"; shift
    if "$@"; then ok "$label"; else bad "$label"; fi
}

assert_file() { [ -f "$2" ] && ok "$1" || bad "$1"; }
assert_dir() { [ -d "$2" ] && ok "$1" || bad "$1"; }
assert_contains() { grep -Fq "$3" "$2" 2>/dev/null && ok "$1" || bad "$1"; }
assert_not_contains() { ! grep -Fq "$3" "$2" 2>/dev/null && ok "$1" || bad "$1"; }

hash_file() { shasum -a 256 "$1" | awk '{print $1}'; }

new_target() {
    local target
    target="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-target.XXXXXX")"
    git -C "$target" init -q
    printf '%s\n' "$target"
}

run_install() {
    local target="$1" source="${2:-$TEMPLATE_DIR}" fake_home="$3" approved_digest
    if [ "$#" -ge 4 ]; then
        approved_digest="$4"
    else
        approved_digest="$(hash_file "$source/SHA256SUMS")"
    fi
    mkdir -p "$fake_home"
    (cd "$target" && HOME="$fake_home" EXOCORTEX_LOCAL_SOURCE="$source" EXOCORTEX_CANDIDATE_DIGEST="$approved_digest" bash "$source/install.sh" test-project)
}

finish_suite() {
    echo "Installer suite: $PASS passed, $FAIL failed"
    [ "$FAIL" -eq 0 ]
}
