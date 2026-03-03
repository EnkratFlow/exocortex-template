#!/bin/bash
# Shared test utilities for exocortex install.sh test suite
# Source this file at the top of run_tests.sh — do not execute directly.

TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Global counters: tests (one per test function)
SUITE_PASS=0
SUITE_FAIL=0

# Per-test assertion counters — reset by begin_test()
TEST_PASS=0
TEST_FAIL=0

# ── Assertions ──────────────────────────────────────────────────────────────────

assert_file_exists() {
    local label="$1" path="$2"
    if [ -e "$path" ]; then
        echo "    ✅ $label"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — not found: $path"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

assert_file_missing() {
    local label="$1" path="$2"
    if [ ! -e "$path" ]; then
        echo "    ✅ $label"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — unexpectedly exists: $path"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

assert_file_contains() {
    local label="$1" path="$2" pattern="$3"
    if grep -q "$pattern" "$path" 2>/dev/null; then
        echo "    ✅ $label"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — '$pattern' not found in $path"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

assert_file_not_contains() {
    local label="$1" path="$2" pattern="$3"
    if ! grep -q "$pattern" "$path" 2>/dev/null; then
        echo "    ✅ $label"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — '$pattern' unexpectedly found in $path"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

# Assert file hash is unchanged (pass the hash captured BEFORE the operation)
assert_hash_unchanged() {
    local label="$1" path="$2" expected="$3"
    local actual
    actual=$(file_hash "$path")
    if [ "$actual" = "$expected" ]; then
        echo "    ✅ $label — byte-for-byte identical"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — CHANGED"
        echo "       expected: $expected"
        echo "       actual:   $actual"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

# Assert file hash has CHANGED (used for system file update test)
assert_hash_changed() {
    local label="$1" path="$2" old_hash="$3"
    local actual
    actual=$(file_hash "$path")
    if [ "$actual" != "$old_hash" ]; then
        echo "    ✅ $label — was updated"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — NOT updated (hash still matches old value)"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

# Assert file now matches the template version exactly
assert_matches_template() {
    local label="$1" path="$2" template_path="$3"
    local actual expected
    actual=$(file_hash "$path")
    expected=$(file_hash "$template_path")
    if [ "$actual" = "$expected" ]; then
        echo "    ✅ $label — matches template"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — does NOT match template"
        echo "       file:     $actual"
        echo "       template: $expected"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

assert_manifest_exists() {
    local label="$1" dir="$2"
    local mf="$dir/.exocortex/.install-manifest"
    if [ -f "$mf" ]; then
        local count
        count=$(grep -c "^[^#]" "$mf" 2>/dev/null || echo 0)
        echo "    ✅ $label — $count files tracked"
        TEST_PASS=$((TEST_PASS+1))
    else
        echo "    ❌ $label — manifest not found at $mf"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

assert_manifest_missing_pattern() {
    local label="$1" dir="$2" pattern="$3"
    local mf="$dir/.exocortex/.install-manifest"
    if ! grep -q "$pattern" "$mf" 2>/dev/null; then
        echo "    ✅ $label"
        TEST_PASS=$((TEST_PASS+1))
    else
        local match
        match=$(grep "$pattern" "$mf" | head -3)
        echo "    ❌ $label — manifest unexpectedly contains '$pattern':"
        echo "       $match"
        TEST_FAIL=$((TEST_FAIL+1))
    fi
}

# ── Helpers ─────────────────────────────────────────────────────────────────────

file_hash() {
    shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
}

# Patches REPO_URL to local file:// (repo is private on GitHub) and runs install.sh
# Passing "test-project" as $1 ensures fresh-install mode skips all read() prompts.
# Usage: run_install <project_dir> [template_dir]
run_install() {
    local dir="$1"
    local template="${2:-$TEMPLATE_DIR}"
    local patched
    patched=$(mktemp)
    sed "s|REPO_URL=\"https://github.com/EnkratFlow/exocortex-template.git\"|REPO_URL=\"file://${template}\"|" \
        "$template/install.sh" > "$patched"
    chmod +x "$patched"
    (cd "$dir" && bash "$patched" "test-project") > /dev/null 2>&1
    local rc=$?
    rm -f "$patched"
    return $rc
}

# Creates a minimal temp project: empty dir + git init (no .exocortex)
make_fresh_project() {
    local dir
    dir=$(mktemp -d)
    git -C "$dir" init -q
    git -C "$dir" commit --allow-empty -m "init" -q
    echo "$dir"
}

# Creates a temp project and runs a full fresh install on it, returning a baseline dir
make_installed_project() {
    local dir
    dir=$(make_fresh_project)
    run_install "$dir"
    echo "$dir"
}

# Writes a manifest entry for a file:  "<filepath> <hash>"
# Usage: write_manifest_entry <manifest_path> <filepath> <hash>
write_manifest_entry() {
    local manifest="$1" filepath="$2" hash="$3"
    echo "${filepath} ${hash}" >> "$manifest"
}

# ── Test lifecycle ───────────────────────────────────────────────────────────────

begin_test() {
    TEST_NAME="$1"
    TEST_PASS=0
    TEST_FAIL=0
    printf "\n  ▶  %s\n" "$TEST_NAME"
}

end_test() {
    if [ "$TEST_FAIL" -eq 0 ]; then
        printf "  ✅ PASS  (%d assertions)\n" "$TEST_PASS"
        SUITE_PASS=$((SUITE_PASS+1))
    else
        printf "  ❌ FAIL  (%d failed, %d passed)\n" "$TEST_FAIL" "$TEST_PASS"
        SUITE_FAIL=$((SUITE_FAIL+1))
    fi
}
