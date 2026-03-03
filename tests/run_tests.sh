#!/bin/bash
# Exocortex install.sh test suite

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=helpers.sh
source "$TESTS_DIR/helpers.sh"

echo ""
echo "🧪 Exocortex install.sh test suite"
echo "   Template: $TEMPLATE_DIR"
echo "══════════════════════════════════════════════════════"

# ──────────────────────────────────────────────────────────────────────────────
# Test 1 — Fresh install
# Scenario: no .exocortex exists. install.sh runs in fresh-install mode.
# Expects: all skeleton dirs/files installed, manifest created.
# ──────────────────────────────────────────────────────────────────────────────
test_01_fresh_install() {
    begin_test "T01: fresh install creates complete skeleton"

    local dir
    dir=$(make_fresh_project)
    run_install "$dir"

    assert_file_exists  ".exocortex/ dir"            "$dir/.exocortex"
    assert_file_exists  "AI_BOOTSTRAP.md"            "$dir/.exocortex/AI_BOOTSTRAP.md"
    assert_file_exists  "SESSION_CONTEXT.md"         "$dir/.exocortex/SESSION_CONTEXT.md"
    assert_file_exists  "TODO.md"                    "$dir/.exocortex/TODO.md"
    assert_file_exists  "LESSONS.md"                 "$dir/.exocortex/LESSONS.md"
    assert_file_exists  "events/ dir"                "$dir/.exocortex/events"
    assert_file_exists  ".cursor/commands/"          "$dir/.cursor/commands"
    assert_file_exists  ".github/skills/"            "$dir/.github/skills"
    assert_file_exists  ".claude/skills/"            "$dir/.claude/skills"
    assert_manifest_exists "manifest seeded"         "$dir"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Test 2 — Update, no manifest: user files skipped, new template files installed
# Scenario: .exocortex exists with user data but NO manifest (first-time re-run
#           on a project created before the manifest feature was introduced).
# Expects: user data untouched, new template files (cursor/github/claude) installed,
#          manifest created.
# ──────────────────────────────────────────────────────────────────────────────
test_02_update_no_manifest() {
    begin_test "T02: update, no manifest — user files skipped, new files installed"

    local dir
    dir=$(make_fresh_project)

    # Simulate an existing project: .exocortex/ with user data, no manifest
    mkdir -p "$dir/.exocortex"
    printf '# SESSION CONTEXT\nT02_CANARY_SESSION — must survive\n' > "$dir/.exocortex/SESSION_CONTEXT.md"
    printf '# TODO\nT02_CANARY_TODO — must survive\n'              > "$dir/.exocortex/TODO.md"
    printf '# LESSONS\nT02_CANARY_LESSONS — must survive\n'        > "$dir/.exocortex/LESSONS.md"
    printf '# PROJECT MEMORY\nT02_CANARY_MEMORY — must survive\n'  > "$dir/.exocortex/PROJECT_MEMORY.md"

    local h_session h_todo h_lessons h_memory
    h_session=$(file_hash "$dir/.exocortex/SESSION_CONTEXT.md")
    h_todo=$(file_hash "$dir/.exocortex/TODO.md")
    h_lessons=$(file_hash "$dir/.exocortex/LESSONS.md")
    h_memory=$(file_hash "$dir/.exocortex/PROJECT_MEMORY.md")

    run_install "$dir"

    # User data files: byte-for-byte identical
    assert_hash_unchanged "SESSION_CONTEXT.md unchanged" "$dir/.exocortex/SESSION_CONTEXT.md" "$h_session"
    assert_hash_unchanged "TODO.md unchanged"            "$dir/.exocortex/TODO.md"            "$h_todo"
    assert_hash_unchanged "LESSONS.md unchanged"         "$dir/.exocortex/LESSONS.md"         "$h_lessons"
    assert_hash_unchanged "PROJECT_MEMORY.md unchanged"  "$dir/.exocortex/PROJECT_MEMORY.md"  "$h_memory"

    # Canary content still present (belt + suspenders)
    assert_file_contains  "SESSION_CONTEXT content intact"  "$dir/.exocortex/SESSION_CONTEXT.md" "T02_CANARY_SESSION"
    assert_file_contains  "TODO content intact"              "$dir/.exocortex/TODO.md"            "T02_CANARY_TODO"
    assert_file_contains  "LESSONS content intact"           "$dir/.exocortex/LESSONS.md"         "T02_CANARY_LESSONS"
    assert_file_contains  "PROJECT_MEMORY content intact"    "$dir/.exocortex/PROJECT_MEMORY.md"  "T02_CANARY_MEMORY"

    # New files should have been installed (didn't exist before)
    assert_file_exists    "AI_BOOTSTRAP.md installed"    "$dir/.exocortex/AI_BOOTSTRAP.md"
    assert_file_exists    ".cursor/commands installed"   "$dir/.cursor/commands"
    assert_file_exists    ".github/skills installed"     "$dir/.github/skills"
    assert_file_exists    ".claude/skills installed"     "$dir/.claude/skills"
    assert_manifest_exists "manifest seeded"             "$dir"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Test 3 — Update WITH manifest: system file updated when template has changed
# Scenario: a system file has "old" content; manifest records the old hash;
#           template now has new content. install.sh should update the file.
# The install.sh branch: current_hash == manifest_hash → safe to overwrite with template.
# ──────────────────────────────────────────────────────────────────────────────
test_03_system_file_updates() {
    begin_test "T03: update + manifest — outdated system file is updated to template"

    local dir
    dir=$(make_fresh_project)
    mkdir -p "$dir/.exocortex"

    # Write "old" content for a known system file
    local system_file="$dir/.exocortex/COMMAND_SYSTEM.md"
    printf '# OLD VERSION\nThis is the old content before the template update.\n' > "$system_file"
    local old_hash
    old_hash=$(file_hash "$system_file")

    # Create a manifest that records the old hash as what was installed.
    # install.sh stores paths relative to the project root (e.g. ".exocortex/COMMAND_SYSTEM.md"),
    # so the manifest entry must use the same relative form.
    local manifest="$dir/.exocortex/.install-manifest"
    printf '# Exocortex install manifest — do not edit manually\n' > "$manifest"
    write_manifest_entry "$manifest" ".exocortex/COMMAND_SYSTEM.md" "$old_hash"

    run_install "$dir"

    # File should now match the template version
    assert_matches_template "COMMAND_SYSTEM.md updated to template" \
        "$system_file" \
        "$TEMPLATE_DIR/.exocortex/COMMAND_SYSTEM.md"

    # Old hash should be gone
    assert_hash_changed "COMMAND_SYSTEM.md hash changed from old" "$system_file" "$old_hash"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Test 4 — Update WITH manifest: user-modified system file is preserved
# Scenario: user has added custom content to a normally-system-managed file.
#           install.sh should detect the drift from the manifest hash and skip.
# The install.sh branch: current_hash != manifest_hash → user-modified → skip.
# ──────────────────────────────────────────────────────────────────────────────
test_04_user_modified_preserved() {
    begin_test "T04: update + manifest — user-modified file is never overwritten"

    local dir
    dir=$(make_installed_project)   # Fresh install → seeds manifest

    # User modifies a system file after installation
    local system_file="$dir/.exocortex/COMMAND_SYSTEM.md"
    printf '\n\n## My Custom Section\nT04_CUSTOM_CONTENT — must survive\n' >> "$system_file"
    local modified_hash
    modified_hash=$(file_hash "$system_file")

    # Second install run — sees: current_hash != manifest_hash → skip
    run_install "$dir"

    assert_hash_unchanged "user-modified file preserved"         "$system_file" "$modified_hash"
    assert_file_contains  "custom content still present"         "$system_file" "T04_CUSTOM_CONTENT"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Test 5 — Idempotent: two consecutive runs produce identical state
# Scenario: run install.sh twice on the same project.
# Expects: all file hashes identical between run 1 and run 2.
# ──────────────────────────────────────────────────────────────────────────────
test_05_idempotent() {
    begin_test "T05: idempotent — two runs produce identical state"

    local dir
    dir=$(make_fresh_project)
    run_install "$dir"   # Run 1

    # Capture hashes after run 1
    local h_bootstrap h_manifest h_session
    h_bootstrap=$(file_hash "$dir/.exocortex/AI_BOOTSTRAP.md")
    h_manifest=$(file_hash "$dir/.exocortex/.install-manifest")
    h_session=$(file_hash "$dir/.exocortex/SESSION_CONTEXT.md")

    run_install "$dir"   # Run 2

    assert_hash_unchanged "AI_BOOTSTRAP.md unchanged run1→run2"   "$dir/.exocortex/AI_BOOTSTRAP.md"       "$h_bootstrap"
    assert_hash_unchanged "manifest unchanged run1→run2"           "$dir/.exocortex/.install-manifest"     "$h_manifest"
    assert_hash_unchanged "SESSION_CONTEXT.md unchanged run1→run2" "$dir/.exocortex/SESSION_CONTEXT.md"    "$h_session"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Test 6 — Critical data files: all 4 memory files preserved across update
# Scenario: the 4 files that hold irreplaceable user context must NEVER be touched.
# Tests both hash integrity and byte-level content preservation.
# ──────────────────────────────────────────────────────────────────────────────
test_06_critical_data_files() {
    begin_test "T06: critical data files (SESSION_CONTEXT, TODO, LESSONS, PROJECT_MEMORY) preserved"

    local dir
    dir=$(make_fresh_project)
    mkdir -p "$dir/.exocortex"

    # Write distinctive canary content to each critical file
    printf '# SESSION CONTEXT\n## 🟢 RIGHT NOW\nT06: CANARY_SESSION=abc123\n'   > "$dir/.exocortex/SESSION_CONTEXT.md"
    printf '# TODO\n## 🟧 In Progress\n- [ ] T06: CANARY_TODO=xyz789\n'          > "$dir/.exocortex/TODO.md"
    printf '# LESSONS\n- T06: CANARY_LESSONS=def456\n'                            > "$dir/.exocortex/LESSONS.md"
    printf '# PROJECT MEMORY\nT06: CANARY_MEMORY=ghi012\n'                        > "$dir/.exocortex/PROJECT_MEMORY.md"

    local h_s h_t h_l h_m
    h_s=$(file_hash "$dir/.exocortex/SESSION_CONTEXT.md")
    h_t=$(file_hash "$dir/.exocortex/TODO.md")
    h_l=$(file_hash "$dir/.exocortex/LESSONS.md")
    h_m=$(file_hash "$dir/.exocortex/PROJECT_MEMORY.md")

    run_install "$dir"

    # Hash checks
    assert_hash_unchanged "SESSION_CONTEXT.md hash"  "$dir/.exocortex/SESSION_CONTEXT.md"  "$h_s"
    assert_hash_unchanged "TODO.md hash"              "$dir/.exocortex/TODO.md"             "$h_t"
    assert_hash_unchanged "LESSONS.md hash"           "$dir/.exocortex/LESSONS.md"          "$h_l"
    assert_hash_unchanged "PROJECT_MEMORY.md hash"    "$dir/.exocortex/PROJECT_MEMORY.md"   "$h_m"

    # Content checks
    assert_file_contains  "SESSION_CONTEXT canary"   "$dir/.exocortex/SESSION_CONTEXT.md"  "CANARY_SESSION=abc123"
    assert_file_contains  "TODO canary"               "$dir/.exocortex/TODO.md"             "CANARY_TODO=xyz789"
    assert_file_contains  "LESSONS canary"            "$dir/.exocortex/LESSONS.md"          "CANARY_LESSONS=def456"
    assert_file_contains  "PROJECT_MEMORY canary"     "$dir/.exocortex/PROJECT_MEMORY.md"   "CANARY_MEMORY=ghi012"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Test 7 — Events preserved: real event files are byte-for-byte untouched
# Scenario: user has existing event files (session diary entries) in events/.
#           These are the most irreplaceable data — once gone, they are gone forever.
# Expects: every event file identical before and after install.
# ──────────────────────────────────────────────────────────────────────────────
test_07_events_preserved() {
    begin_test "T07: event files preserved — byte-for-byte untouched"

    local dir
    dir=$(make_fresh_project)
    mkdir -p "$dir/.exocortex/events"

    # Write realistic event files with canary content
    printf '# Session 2026-02-28\n## What happened\nT07_EVENT_1: Completed feature X.\n' \
        > "$dir/.exocortex/events/2026-02-28-session.md"
    printf '# Session 2026-03-01\n## What happened\nT07_EVENT_2: Fixed critical bug Y.\n' \
        > "$dir/.exocortex/events/2026-03-01-session.md"

    local h_e1 h_e2
    h_e1=$(file_hash "$dir/.exocortex/events/2026-02-28-session.md")
    h_e2=$(file_hash "$dir/.exocortex/events/2026-03-01-session.md")

    run_install "$dir"

    assert_file_exists    "event 1 still exists"              "$dir/.exocortex/events/2026-02-28-session.md"
    assert_file_exists    "event 2 still exists"              "$dir/.exocortex/events/2026-03-01-session.md"
    assert_hash_unchanged "event 1 byte-for-byte"             "$dir/.exocortex/events/2026-02-28-session.md" "$h_e1"
    assert_hash_unchanged "event 2 byte-for-byte"             "$dir/.exocortex/events/2026-03-01-session.md" "$h_e2"
    assert_file_contains  "event 1 content intact"            "$dir/.exocortex/events/2026-02-28-session.md" "T07_EVENT_1"
    assert_file_contains  "event 2 content intact"            "$dir/.exocortex/events/2026-03-01-session.md" "T07_EVENT_2"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Test 8 — Events not in manifest: event files are never manifest-tracked
# Scenario: if event files were added to the manifest, future install runs could
#           misclassify them as "unmodified system files" and overwrite them.
#           This test locks that door permanently.
# Expects: no "events/" entry in .install-manifest (except .gitkeep is allowed).
# ──────────────────────────────────────────────────────────────────────────────
test_08_events_not_in_manifest() {
    begin_test "T08: event files never appear in install manifest"

    local dir
    dir=$(make_fresh_project)
    mkdir -p "$dir/.exocortex/events"

    # Create event files BEFORE install (simulating existing project)
    printf '# Session 2026-03-02\nT08_EVENT: pre-existing event.\n' \
        > "$dir/.exocortex/events/2026-03-02-session.md"

    run_install "$dir"

    # The specific event file must not appear in manifest
    local manifest="$dir/.exocortex/.install-manifest"
    assert_manifest_missing_pattern \
        "user event file not in manifest" \
        "$dir" \
        "2026-03-02-session.md"

    # Run install a SECOND time — event still preserved (not overwritten even
    # with a manifest now present for other files)
    local h_event
    h_event=$(file_hash "$dir/.exocortex/events/2026-03-02-session.md")
    run_install "$dir"

    assert_hash_unchanged "event preserved across second install" \
        "$dir/.exocortex/events/2026-03-02-session.md" "$h_event"
    assert_file_contains  "event content intact after second install" \
        "$dir/.exocortex/events/2026-03-02-session.md" "T08_EVENT"

    rm -rf "$dir"
    end_test
}

# ──────────────────────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────────────────────

test_01_fresh_install
test_02_update_no_manifest
test_03_system_file_updates
test_04_user_modified_preserved
test_05_idempotent
test_06_critical_data_files
test_07_events_preserved
test_08_events_not_in_manifest

echo ""
echo "══════════════════════════════════════════════════════"
if [ "$SUITE_FAIL" -eq 0 ]; then
    echo "  ✅ ALL $SUITE_PASS TESTS PASSED"
else
    echo "  ❌ $SUITE_FAIL FAILED, $SUITE_PASS PASSED"
fi
echo "══════════════════════════════════════════════════════"
echo ""

exit "$SUITE_FAIL"
