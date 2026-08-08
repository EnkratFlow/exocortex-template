#!/bin/bash
# Exocortex public-v2 installer. It installs one pinned local source into the
# current project, preserves project data, and never changes global state.

set -euo pipefail

PROJECT_NAME="${1:-$(basename "$PWD")}"
SOURCE_INPUT="${EXOCORTEX_LOCAL_SOURCE:-}"
CANDIDATE_DIGEST="${EXOCORTEX_CANDIDATE_DIGEST:-}"
TARGET_ROOT="$(pwd -P)"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

sha256_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" 2>/dev/null | awk '{print $1}'
    else
        fail "shasum or sha256sum is required"
    fi
}

if [ -z "$SOURCE_INPUT" ]; then
    fail "EXOCORTEX_LOCAL_SOURCE must name an exact pinned local template; unpinned remote install is disabled"
fi
[ -d "$SOURCE_INPUT" ] || fail "local template source is not a directory"
[ -f "$SOURCE_INPUT/install.sh" ] || fail "local template source is missing install.sh"
[ "$TARGET_ROOT" != "/" ] || fail "refusing to install into filesystem root"
[ "$TARGET_ROOT" != "${HOME:-/__no_home__}" ] || fail "refusing to install into the user home directory"

SOURCE_ROOT="$(cd "$SOURCE_INPUT" && pwd -P)"
[ "$SOURCE_ROOT" != "$TARGET_ROOT" ] || fail "template source and install target must be different directories"
case "$SOURCE_ROOT/" in "$TARGET_ROOT/"*) fail "template source must not be inside the install target" ;; esac
case "$TARGET_ROOT/" in "$SOURCE_ROOT/"*) fail "install target must not be inside the template source" ;; esac
[[ "$CANDIDATE_DIGEST" =~ ^[0-9a-f]{64}$ ]] || fail "EXOCORTEX_CANDIDATE_DIGEST must be the separately approved SHA-256 of SHA256SUMS"
[ -f "$SOURCE_ROOT/SHA256SUMS" ] && [ ! -L "$SOURCE_ROOT/SHA256SUMS" ] \
    || fail "local template source is missing a regular non-symlink SHA256SUMS"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/exocortex-install.XXXXXX")"
SOURCE_COPY="$TMP_ROOT/source"
MANIFEST_NEW="$TMP_ROOT/manifest-new"
LISTED_SUMS="$TMP_ROOT/listed-sums"
APPROVED_SUMS="$TMP_ROOT/SHA256SUMS.approved"
APPROVED_PUBLIC_CHECKER="$TMP_ROOT/check-public-release.approved.py"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$SOURCE_COPY" "$TMP_ROOT/home" "$TMP_ROOT/tmp"
chmod 0700 "$TMP_ROOT"
: > "$MANIFEST_NEW"
: > "$LISTED_SUMS"

# Copy the approved manifest into the private installer directory before using
# it as authority. Any concurrent source change can then only make later staged
# validation fail; it cannot change which checker bytes are authorized.
cp "$SOURCE_ROOT/SHA256SUMS" "$APPROVED_SUMS"
chmod 0600 "$APPROVED_SUMS"
SOURCE_SUMS_DIGEST="$(sha256_file "$APPROVED_SUMS")"
[ "$SOURCE_SUMS_DIGEST" = "$CANDIDATE_DIGEST" ] || fail "local template candidate digest does not match the separately approved digest"

command -v python3 >/dev/null 2>&1 || fail "python3 is required to validate the candidate"
HOST_PYTHON="$(command -v python3)"
case "$HOST_PYTHON" in /*) ;; *) fail "python3 must resolve to an absolute host path" ;; esac
SANITIZED_PATH="$(dirname "$HOST_PYTHON"):/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin"
run_candidate_python() {
    (
        cd "$TMP_ROOT"
        env -i \
            PATH="$SANITIZED_PATH" \
            HOME="$TMP_ROOT/home" \
            TMPDIR="$TMP_ROOT/tmp" \
            LC_ALL=C LANG=C PYTHONDONTWRITEBYTECODE=1 \
            "$HOST_PYTHON" -I "$@"
    )
}

run_trusted_python() {
    (
        cd "$TMP_ROOT"
        env -i \
            PATH="$SANITIZED_PATH" \
            HOME="$TMP_ROOT/home" \
            TMPDIR="$TMP_ROOT/tmp" \
            LC_ALL=C LANG=C PYTHONDONTWRITEBYTECODE=1 \
            "$HOST_PYTHON" -I "$@"
    )
}

# Bind the release-surface checker to the already approved manifest before
# executing it, then reject forbidden tracked or untracked source data before
# any source byte is staged. Output contains metadata only, never matches.
PUBLIC_CHECKER_REL="scripts/check-public-release.py"
PUBLIC_CHECKER="$SOURCE_ROOT/$PUBLIC_CHECKER_REL"
[ -f "$PUBLIC_CHECKER" ] && [ ! -L "$PUBLIC_CHECKER" ] \
    || fail "local template source is missing the public-release checker"
EXPECTED_CHECKER_HASH="$(awk -v path="$PUBLIC_CHECKER_REL" 'substr($0,67)==path {print substr($0,1,64)}' "$APPROVED_SUMS")"
[[ "$EXPECTED_CHECKER_HASH" =~ ^[0-9a-f]{64}$ ]] \
    || fail "public-release checker is not uniquely bound by SHA256SUMS"
cp "$PUBLIC_CHECKER" "$APPROVED_PUBLIC_CHECKER"
chmod 0600 "$APPROVED_PUBLIC_CHECKER"
[ "$(sha256_file "$APPROVED_PUBLIC_CHECKER")" = "$EXPECTED_CHECKER_HASH" ] \
    || fail "public-release checker does not match the approved manifest"
run_candidate_python "$APPROVED_PUBLIC_CHECKER" --root "$SOURCE_ROOT" --source-tree \
    || fail "template source violates the public-release boundary"

# Copy without repository metadata or credential files. Source validation above
# makes exclusions defense in depth rather than silent omission. This is staging only;
# target mutation starts after the complete integrity check.
if command -v rsync >/dev/null 2>&1 && [ "${EXOCORTEX_FORCE_TAR_STAGE:-0}" != "1" ]; then
    rsync -a --exclude='.git' --exclude='.env' --exclude='.envrc' \
        --exclude='*/.env' --exclude='*/.envrc' \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
        "$SOURCE_ROOT/" "$SOURCE_COPY/"
else
    (cd "$SOURCE_ROOT" && tar cf - --exclude='.git' --exclude='.env' \
        --exclude='.envrc' --exclude='*/.env' --exclude='*/.envrc' \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' .) \
        | (cd "$SOURCE_COPY" && tar xpf -)
fi
STAGED_LINK="$(find "$SOURCE_COPY" -type l -print -quit 2>/dev/null)" \
    || fail "staged template topology could not be inspected safely"
[ -z "$STAGED_LINK" ] || fail "staged template contains a symlink: ${STAGED_LINK#"$SOURCE_COPY/"}"
[ -f "$SOURCE_COPY/SHA256SUMS" ] && [ ! -L "$SOURCE_COPY/SHA256SUMS" ] \
    || fail "staged SHA256SUMS must be a regular non-symlink file"
STAGED_SUMS_DIGEST="$(sha256_file "$SOURCE_COPY/SHA256SUMS")"
[ "$STAGED_SUMS_DIGEST" = "$CANDIDATE_DIGEST" ] || fail "staged template changed after candidate approval"

file_hash() {
    sha256_file "$1"
}

file_mode() {
    run_trusted_python -c 'import os,stat,sys; print(format(stat.S_IMODE(os.stat(sys.argv[1]).st_mode), "04o"))' "$TARGET_ROOT/$1"
}

file_link_count() {
    run_trusted_python -c 'import os,sys; print(os.lstat(sys.argv[1]).st_nlink)' "$TARGET_ROOT/$1"
}

COPY_COUNT=0
INSTALL_FAULT_AFTER="${EXOCORTEX_TEST_INSTALL_FAULT_AFTER_COPIES:-0}"
if ! [[ "$INSTALL_FAULT_AFTER" =~ ^[0-9]+$ ]]; then
    fail "test install fault count must be a non-negative integer"
fi
if [ "$INSTALL_FAULT_AFTER" -gt 0 ] && [ "${EXOCORTEX_TEST_MODE:-0}" != "1" ]; then
    fail "test install fault injection requires EXOCORTEX_TEST_MODE=1"
fi

record_copy_and_maybe_fault() {
    COPY_COUNT=$((COPY_COUNT + 1))
    if [ "$INSTALL_FAULT_AFTER" -gt 0 ] && [ "$COPY_COUNT" -ge "$INSTALL_FAULT_AFTER" ]; then
        fail "injected test-only install fault after $COPY_COUNT copies"
    fi
}

is_legacy_session_context_backup_relpath() {
    case "$1" in
        SESSION_CONTEXT_BACKUP_*.md)
            case "$1" in */*) return 1 ;; *) return 0 ;; esac
            ;;
    esac
    return 1
}

is_data_relpath() {
    is_legacy_session_context_backup_relpath "$1" && return 0
    [ "$1" = ".env.example" ] && return 1
    case "$1" in
        SESSION_CONTEXT.md|SESSION_CONTEXT.md.backup|SESSION_CONTEXT.local.md|TODO.md|LESSONS.md|PROJECT_MEMORY.md|OPEN_DECISIONS.md|subconscious_patterns.md|.env|.env.*|.envrc|*/.env|*/.env.*|*/.envrc|.project-name|.install-manifest|.hub_enabled|.hub_disabled)
            return 0 ;;
        events/*|archive/*|hub/*|local/*|planning/*|work-items/*)
            return 0 ;;
        control/ACTIVE_WORK.md|control/BRANCH_POLICY.md|control/REPO_STATE.md|control/EXECUTOR_REGISTRY.json|control/EXTERNAL_SYNC_POLICY.json|control/INTERRUPTS.md|control/BACKLOG.md|control/ROADMAP.md|control/ARCH_OVERVIEW.md|control/REPO_ORGANIZATION_REPORT.md)
            return 0 ;;
        *) return 1 ;;
    esac
}

is_integrity_scope() {
    local rel="$1"
    [ "$rel" = ".exocortex/.env.example" ] && return 0
    case "$rel" in
        SHA256SUMS|.git|.git/*|.env|.env.*|.envrc|*/.env|*/.env.*|*/.envrc|__pycache__/*|*/__pycache__/*|*.pyc|*.pyo) return 1 ;;
        .exocortex/*)
            local exo_rel="${rel#.exocortex/}"
            is_data_relpath "$exo_rel" && return 1
            return 0 ;;
        *) return 0 ;;
    esac
}

verify_integrity() {
    local sums="$SOURCE_COPY/SHA256SUMS"
    [ -f "$sums" ] || fail "SHA256SUMS is required"
    [ -s "$sums" ] || fail "SHA256SUMS is empty"

    local line hash rel actual
    while IFS= read -r line || [ -n "$line" ]; do
        [ -z "$line" ] && continue
        case "$line" in \#*) continue ;; esac
        [[ "$line" =~ ^[0-9a-f]{64}\ \ [^/].*$ ]] || fail "malformed SHA256SUMS entry"
        hash="${line:0:64}"
        rel="${line:66}"
        case "/$rel/" in */../*|*/./*) fail "unsafe SHA256SUMS path" ;; esac
        [ "$rel" != "SHA256SUMS" ] || fail "SHA256SUMS cannot checksum itself"
        is_integrity_scope "$rel" || fail "checksum entry is outside the public code-plane scope: $rel"
        if grep -Fqx "$rel" "$LISTED_SUMS"; then
            fail "duplicate SHA256SUMS path: $rel"
        fi
        echo "$rel" >> "$LISTED_SUMS"
        [ -f "$SOURCE_COPY/$rel" ] || fail "checksum-listed file is missing: $rel"
        actual="$(file_hash "$SOURCE_COPY/$rel")"
        [ "$actual" = "$hash" ] || fail "checksum mismatch: $rel"
    done < "$sums"

    while IFS= read -r file; do
        rel="${file#$SOURCE_COPY/}"
        is_integrity_scope "$rel" || continue
        grep -Fqx "$rel" "$LISTED_SUMS" || fail "code-plane file missing from SHA256SUMS: $rel"
    done < <(find "$SOURCE_COPY" -type f | sort)
}

verify_integrity

verify_file_modes() {
    run_trusted_python - "$SOURCE_COPY" <<'PY'
import re
import stat
import sys
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1]).resolve(strict=True)
sums = root / "SHA256SUMS"
modes = root / "FILEMODES"
if modes.is_symlink() or not modes.is_file():
    raise SystemExit("FILEMODES must be a regular non-symlink file")

checksum_paths = []
for line in sums.read_text(encoding="utf-8").splitlines():
    match = re.fullmatch(r"[0-9a-f]{64}  ([^/].*)", line)
    if match is None:
        raise SystemExit("invalid SHA256SUMS while validating file modes")
    checksum_paths.append(match.group(1))

mode_records = {}
mode_paths = []
for line in modes.read_text(encoding="utf-8").splitlines():
    match = re.fullmatch(r"(0644|0755)  ([^/].*)", line)
    if match is None:
        raise SystemExit("malformed FILEMODES entry")
    mode_text, relative = match.groups()
    path = PurePosixPath(relative)
    if relative in mode_records or ".." in path.parts or "." in path.parts:
        raise SystemExit("unsafe or duplicate FILEMODES path")
    mode_records[relative] = int(mode_text, 8)
    mode_paths.append(relative)

expected_mode_paths = set(checksum_paths) | {"SHA256SUMS"}
if (
    checksum_paths != sorted(checksum_paths)
    or mode_paths != sorted(mode_paths)
    or set(mode_records) != expected_mode_paths
):
    raise SystemExit("FILEMODES must bind the sorted SHA256SUMS paths plus SHA256SUMS itself")

for relative in sorted(expected_mode_paths):
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"FILEMODES path is not a regular file: {relative}")
    actual = stat.S_IMODE(path.stat().st_mode)
    if actual != mode_records[relative]:
        raise SystemExit(f"FILEMODES mismatch: {relative}")
PY
}

verify_file_modes || fail "candidate file-mode inventory failed validation"

ADAPTER_GENERATOR="$SOURCE_COPY/.exocortex/scripts/generate_command_adapters.py"
ADAPTER_MATRIX="$SOURCE_COPY/.exocortex/provider-adapters.json"
RETIREMENTS="$TMP_ROOT/legacy-retirements.tsv"
[ -f "$ADAPTER_GENERATOR" ] || fail "template source is missing the provider-adapter generator"
[ -f "$ADAPTER_MATRIX" ] || fail "template source is missing the provider-adapter matrix"
run_candidate_python "$ADAPTER_GENERATOR" --check >/dev/null \
    || fail "generated provider adapters do not match the canonical 24-command registry"
MODEL_REGISTRY_TOOL="$SOURCE_COPY/.exocortex/scripts/model_registry.py"
[ -f "$MODEL_REGISTRY_TOOL" ] || fail "template source is missing the offline model-registry validator"
run_candidate_python "$MODEL_REGISTRY_TOOL" validate-sources \
    --project-root "$SOURCE_COPY" \
    --sources .exocortex/model-source-registry.json >/dev/null \
    || fail "model source registry failed structural validation"
run_candidate_python "$MODEL_REGISTRY_TOOL" validate-catalog \
    --project-root "$SOURCE_COPY" \
    --sources .exocortex/model-source-registry.json \
    --catalog .exocortex/model-routing-catalog.json >/dev/null \
    || fail "model routing catalog failed structural validation"
run_trusted_python - "$ADAPTER_MATRIX" > "$RETIREMENTS" <<'PY'
import json, re, sys
from pathlib import PurePosixPath

matrix = json.load(open(sys.argv[1], encoding='utf-8'))
legacy_items = matrix.get('legacy_retirements')
windsurf_items = matrix.get('windsurf_retirements')
if not isinstance(legacy_items, list) or len(legacy_items) != 55:
    raise SystemExit('invalid legacy retirement matrix')
if not isinstance(windsurf_items, list) or len(windsurf_items) != 25:
    raise SystemExit('invalid Windsurf retirement matrix')
seen = set()
for item in legacy_items:
    if not isinstance(item, dict):
        raise SystemExit('invalid legacy retirement entry')
    legacy = item.get('path')
    replacement = item.get('replacement')
    if not isinstance(legacy, str) or not isinstance(replacement, str):
        raise SystemExit('invalid legacy retirement path')
    for value in (legacy, replacement):
        path = PurePosixPath(value)
        if value.startswith('/') or '..' in path.parts or '\t' in value or '\n' in value:
            raise SystemExit('unsafe legacy retirement path')
    if legacy in seen or not (
        re.fullmatch(r'\.agents/skills/[a-z0-9-]+/SKILL\.md', replacement)
        or re.fullmatch(r'\.claude/skills/[a-z0-9-]+/SKILL\.md', replacement)
        or replacement in {'CLAUDE.md', '.cursor/rules/plan-orchestrate.mdc'}
    ):
        raise SystemExit('invalid legacy retirement mapping')
    seen.add(legacy)
    print(f'{legacy}\t{replacement}')
for legacy in windsurf_items:
    if not isinstance(legacy, str):
        raise SystemExit('invalid Windsurf retirement path')
    path = PurePosixPath(legacy)
    if legacy.startswith('/') or '..' in path.parts or '\t' in legacy or '\n' in legacy:
        raise SystemExit('unsafe Windsurf retirement path')
    if legacy in seen or not (
        re.fullmatch(r'\.windsurf/workflows/[a-z0-9-]+\.md', legacy)
        or legacy == '.windsurfrules'
    ):
        raise SystemExit('invalid Windsurf retirement mapping')
    seen.add(legacy)
    print(f'{legacy}\t')
PY
[ "$(wc -l < "$RETIREMENTS" | tr -d ' ')" = "80" ] \
    || fail "provider-adapter retirement matrix is incomplete"

MANIFEST=".exocortex/.install-manifest"

manifest_get() {
    local key="$1 "
    [ -f "$MANIFEST" ] && awk -v k="$key" 'index($0,k)==1{print $2;exit}' "$MANIFEST" || true
}

record_manifest() {
    local path="$1" digest="$2" next="$TMP_ROOT/manifest-next"
    awk -v k="$path " 'index($0,k)!=1' "$MANIFEST_NEW" > "$next"
    printf '%s %s\n' "$path" "$digest" >> "$next"
    mv "$next" "$MANIFEST_NEW"
}

retire_legacy_adapters() {
    local phase="${1:-}" legacy replacement replacement_source_hash replacement_target_hash
    local current_hash current_mode installed_hash
    case "$phase" in pre|post) ;; *) fail "invalid legacy retirement phase" ;; esac
    while IFS=$'\t' read -r legacy replacement; do
        [ -n "$legacy" ] || fail "invalid legacy retirement row"
        # This path is both a historical retirement and the current Cursor
        # adapter destination. Retire its manifest-owned predecessor before
        # copying the replacement so an already-current file is never removed.
        if [ "$phase" = pre ] && [ "$legacy" != ".cursor/skills/onboard/SKILL.md" ]; then
            continue
        fi
        if [ "$phase" = post ] && [ "$legacy" = ".cursor/skills/onboard/SKILL.md" ]; then
            continue
        fi
        [ -e "$legacy" ] || continue
        assert_safe_target_file_path "$legacy"
        installed_hash="$(manifest_get "$legacy")"
        if [ -n "$replacement" ]; then
            assert_safe_target_file_path "$replacement"
            if [ ! -f "$SOURCE_COPY/$replacement" ] || [ ! -f "$replacement" ]; then
                [ -n "$installed_hash" ] && record_manifest "$legacy" "$installed_hash"
                echo "EXOCORTEX_ADAPTER_COLLISION_PRESERVED: $legacy (canonical replacement unavailable: $replacement)"
                report_preserved_legacy_command_drift "$legacy"
                continue
            fi
            replacement_source_hash="$(file_hash "$SOURCE_COPY/$replacement")"
            replacement_target_hash="$(file_hash "$replacement")"
            if [ "$replacement_source_hash" != "$replacement_target_hash" ]; then
                [ -n "$installed_hash" ] && record_manifest "$legacy" "$installed_hash"
                echo "EXOCORTEX_ADAPTER_COLLISION_PRESERVED: $legacy (customized replacement preserved: $replacement)"
                report_preserved_legacy_command_drift "$legacy"
                continue
            fi
        fi
        current_hash="$(file_hash "$legacy")"
        current_mode="$(file_mode "$legacy")"
        if [ -n "$installed_hash" ] \
            && [ "$current_hash" = "$installed_hash" ] \
            && [ "$current_mode" = "0644" ]; then
            rm -- "$legacy"
            echo "retired template-managed legacy adapter: $legacy"
        else
            [ -n "$installed_hash" ] && record_manifest "$legacy" "$installed_hash"
            echo "EXOCORTEX_ADAPTER_COLLISION_PRESERVED: $legacy (customized bytes/mode or unknown legacy adapter)"
            report_preserved_legacy_command_drift "$legacy"
        fi
    done < "$RETIREMENTS"
}

assert_safe_target_path() {
    local rel="$1" current="$TARGET_ROOT" part index=0
    local -a parts
    case "$rel" in
        ""|/*|.|..|../*|*/../*|*/..) fail "unsafe install target path: $rel" ;;
    esac
    IFS='/' read -r -a parts <<< "$rel"
    for part in "${parts[@]}"; do
        [ -n "$part" ] && [ "$part" != "." ] && [ "$part" != ".." ] || fail "unsafe install target path: $rel"
        current="$current/$part"
        [ ! -L "$current" ] || fail "refusing target path with symlink component: $rel"
        if [ -e "$current" ] && [ "$index" -lt "$(( ${#parts[@]} - 1 ))" ]; then
            [ -d "$current" ] || fail "target ancestor is not a directory: $rel"
        fi
        index=$((index + 1))
    done
}

assert_safe_target_file_path() {
    local rel="$1"
    assert_safe_target_path "$rel"
    if [ -e "$rel" ] && [ ! -f "$rel" ]; then
        fail "target file path is not a regular file: $rel"
    fi
    if [ -e "$rel" ] && [ "$(file_link_count "$rel")" != "1" ]; then
        fail "target file path has external hard links: $rel"
    fi
}

assert_safe_target_dir_path() {
    local rel="$1"
    assert_safe_target_path "$rel"
    if [ -e "$rel" ] && [ ! -d "$rel" ]; then
        fail "target directory path is not a directory: $rel"
    fi
}

ensure_target_parent() {
    local rel="$1" parent parent_real
    assert_safe_target_path "$rel"
    parent="$(dirname "$rel")"
    if [ "$parent" != "." ]; then
        mkdir -p -- "$parent"
        assert_safe_target_path "$rel"
        parent_real="$(cd "$parent" && pwd -P)"
        case "$parent_real/" in "$TARGET_ROOT/"*) ;; *) fail "target parent escapes the install target: $rel" ;; esac
    fi
}

ensure_target_dir() {
    local rel="$1" resolved
    assert_safe_target_dir_path "$rel"
    mkdir -p -- "$rel"
    assert_safe_target_dir_path "$rel"
    resolved="$(cd "$rel" && pwd -P)"
    case "$resolved/" in "$TARGET_ROOT/"*) ;; *) fail "target directory escapes the install target: $rel" ;; esac
}

copy_with_bound_mode() {
    local source_file="$1"
    local target_file="$2"
    local source_rel expected_mode
    source_rel="${source_file#"$SOURCE_COPY/"}"
    expected_mode="$(awk -v p="$source_rel" 'substr($0,7)==p{print substr($0,1,4); exit}' "$SOURCE_COPY/FILEMODES")"
    [[ "$expected_mode" =~ ^0(644|755)$ ]] || fail "source file lacks a bound mode: $source_rel"
    cp -p "$source_file" "$target_file"
    chmod "$expected_mode" "$target_file"
    [ -f "$target_file" ] && [ ! -L "$target_file" ] \
        || fail "copied target is not a regular non-symlink file: $target_file"
    [ "$(file_hash "$target_file")" = "$(file_hash "$source_file")" ] \
        || fail "copied target bytes do not match the reviewed source: $target_file"
    [ "$(file_mode "$target_file")" = "$expected_mode" ] \
        || fail "copied target mode does not match the reviewed source: $target_file"
    record_copy_and_maybe_fault
}

is_generated_command_adapter() {
    local target_file="$1" command_name
    case "$target_file" in
        .agents/skills/*/SKILL.md)
            command_name="${target_file#.agents/skills/}"
            command_name="${command_name%/SKILL.md}"
            ;;
        .claude/skills/*/SKILL.md)
            command_name="${target_file#.claude/skills/}"
            command_name="${command_name%/SKILL.md}"
            ;;
        .cursor/skills/*/SKILL.md)
            command_name="${target_file#.cursor/skills/}"
            command_name="${command_name%/SKILL.md}"
            ;;
        *) return 1 ;;
    esac
    [ -f "$SOURCE_COPY/.exocortex/commands/$command_name.json" ]
}

is_command_authority_path() {
    case "$1" in
        AI_START_HERE.md|.exocortex/AI_BOOTSTRAP.md|.exocortex/COMMAND_SYSTEM.md|.exocortex/commands/*.json)
            return 0 ;;
    esac
    is_generated_command_adapter "$1"
}

is_root_instruction_adapter() {
    case "$1" in
        CLAUDE.md|AGENTS.md|.cursorrules|.rules|.github/copilot-instructions.md) return 0 ;;
        *) return 1 ;;
    esac
}

contains_known_stale_command_guidance() {
    LC_ALL=C grep -Eiq \
        'HYBRID[[:space:]]+PATTERN|sync_event_to_vault\.sh|/tmp/save_event\.md|Phase[[:space:]]+checkpoint|haiku[[:space:]-]+(tier[[:space:]-]+)?subagent|all[[:space:]]+20[[:space:]]+commands|strip[[:space:]]+(the[[:space:]]+)?/[[:space:]]*prefix' \
        "$1"
}

report_preserved_command_drift() {
    local target_file="$1"
    if is_command_authority_path "$target_file"; then
        echo "EXOCORTEX_COMMAND_AUTHORITY_COLLISION_PRESERVED: $target_file (reviewed reconciliation required before live apply)"
    elif is_root_instruction_adapter "$target_file" \
        && contains_known_stale_command_guidance "$target_file"; then
        echo "EXOCORTEX_STALE_COMMAND_GUIDANCE_PRESERVED: $target_file (matching command JSON remains authoritative; reviewed reconciliation required before live apply)"
    fi
}

report_preserved_legacy_command_drift() {
    case "$1" in
        .cursor/commands/*.md|.claude/commands/*.md|\
        .cursor/rules/00-ide-model-router.mdc|\
        .cursor/rules/01-project-bootstrap.mdc|\
        .cursor/rules/10-context-budget.mdc|\
        .cursor/rules/20-output-budget.mdc)
            echo "EXOCORTEX_COMMAND_AUTHORITY_COLLISION_PRESERVED: $1 (legacy command authority requires reviewed reconciliation)"
            ;;
    esac
}

safe_copy_file() {
    local source_file="$1"
    local target_file="$2"
    [ -f "$source_file" ] || return 0
    ensure_target_parent "$target_file"
    assert_safe_target_file_path "$target_file"
    local source_hash current_hash installed_hash
    source_hash="$(file_hash "$source_file")"
    if [ ! -e "$target_file" ]; then
        copy_with_bound_mode "$source_file" "$target_file"
        record_manifest "$target_file" "$source_hash"
        return 0
    fi
    [ -f "$target_file" ] || fail "target path is not a regular file: $target_file"
    [ ! -L "$target_file" ] || fail "refusing to replace symlink target: $target_file"
    current_hash="$(file_hash "$target_file")"
    installed_hash="$(manifest_get "$target_file")"
    if [ "$current_hash" = "$source_hash" ]; then
        record_manifest "$target_file" "$source_hash"
    elif [ -n "$installed_hash" ] && [ "$current_hash" = "$installed_hash" ]; then
        copy_with_bound_mode "$source_file" "$target_file"
        record_manifest "$target_file" "$source_hash"
    else
        [ -n "$installed_hash" ] && record_manifest "$target_file" "$installed_hash"
        echo "preserve user-modified or unknown file: $target_file"
        report_preserved_command_drift "$target_file"
    fi
}

safe_copy_dir() {
    local source_dir="$1"
    local target_dir="$2"
    [ -d "$source_dir" ] || return 0
    local source_file rel
    while IFS= read -r source_file; do
        rel="${source_file#$source_dir/}"
        if [ "$target_dir" = ".exocortex" ] && is_data_relpath "$rel"; then
            continue
        fi
        safe_copy_file "$source_file" "$target_dir/$rel"
    done < <(find "$source_dir" -type f | sort)
}

write_if_missing() {
    local target="$1"
    local content="$2"
    ensure_target_parent "$target"
    assert_safe_target_file_path "$target"
    if [ ! -e "$target" ]; then
        printf '%s\n' "$content" > "$target"
    fi
}

ensure_data_stubs() {
    local dir
    for dir in \
        .exocortex/events \
        .exocortex/control \
        .exocortex/local/protocol/capabilities \
        .exocortex/local/protocol/transactions \
        .exocortex/local/protocol/descriptors \
        .exocortex/local/protocol/payloads \
        .exocortex/local/protocol/audit; do
        ensure_target_dir "$dir"
    done

    write_if_missing .exocortex/SESSION_CONTEXT.md $'# Session Context\n\n## RIGHT NOW\n\n_No active session context yet._'
    write_if_missing .exocortex/TODO.md $'# TODO\n\n## Ready\n\n_No tasks captured yet._'
    write_if_missing .exocortex/LESSONS.md $'# Lessons\n\n_No lessons captured yet._'
    write_if_missing .exocortex/PROJECT_MEMORY.md $'# Project Memory\n\n_No project-specific memory captured yet._'
    write_if_missing .exocortex/OPEN_DECISIONS.md $'# Open Decisions\n\n_No open decisions captured yet._'
    write_if_missing .exocortex/control/INTERRUPTS.md $'# Interrupts\n\n_No interrupts captured yet._'
    write_if_missing .exocortex/control/BACKLOG.md $'# Backlog\n\n_No backlog items yet._'
    write_if_missing .exocortex/control/ROADMAP.md $'# Roadmap\n\n_No roadmap defined yet._'
    write_if_missing .exocortex/control/EXECUTOR_REGISTRY.json $'{\n  "schema_version": "public-v2",\n  "kind": "executor_registry",\n  "registry_version": 1,\n  "default_role": "read_only",\n  "executors": []\n}'
    write_if_missing .exocortex/control/EXTERNAL_SYNC_POLICY.json $'{\n  "schema_version": "public-v2",\n  "kind": "external_sync_policy",\n  "default": "deny",\n  "policy_version": 1,\n  "destinations": []\n}'
    write_if_missing .exocortex/.project-name "$PROJECT_NAME"
}

preflight_source_dir_targets() {
    local source_dir="$1" target_dir="$2" source_file rel
    [ -d "$source_dir" ] || return 0
    while IFS= read -r source_file; do
        rel="${source_file#$source_dir/}"
        if [ "$target_dir" = ".exocortex" ] && is_data_relpath "$rel"; then
            continue
        fi
        assert_safe_target_file_path "$target_dir/$rel"
    done < <(find "$source_dir" -type f | sort)
}

preflight_install_targets() {
    local rel dir legacy replacement
    preflight_source_dir_targets "$SOURCE_COPY/.exocortex" .exocortex
    for rel in AI_START_HERE.md AGENTS.md CLAUDE.md .rules; do
        [ -f "$SOURCE_COPY/$rel" ] && assert_safe_target_file_path "$rel"
    done
    assert_safe_target_file_path .cursorrules
    preflight_source_dir_targets "$SOURCE_COPY/.cursor" .cursor
    preflight_source_dir_targets "$SOURCE_COPY/.github/skills" .github/skills
    [ -f "$SOURCE_COPY/.github/copilot-instructions.md" ] && assert_safe_target_file_path .github/copilot-instructions.md
    preflight_source_dir_targets "$SOURCE_COPY/.claude/skills" .claude/skills
    preflight_source_dir_targets "$SOURCE_COPY/.agents" .agents
    while IFS=$'\t' read -r legacy replacement; do
        assert_safe_target_file_path "$legacy"
        [ -z "$replacement" ] || assert_safe_target_file_path "$replacement"
    done < "$RETIREMENTS"
    [ -f "$SOURCE_COPY/VERSION" ] && assert_safe_target_file_path .exocortex/.version
    for dir in \
        .exocortex/events \
        .exocortex/control \
        .exocortex/local/protocol/capabilities \
        .exocortex/local/protocol/transactions \
        .exocortex/local/protocol/descriptors \
        .exocortex/local/protocol/payloads \
        .exocortex/local/protocol/audit; do
        assert_safe_target_dir_path "$dir"
    done
    for rel in \
        .exocortex/SESSION_CONTEXT.md \
        .exocortex/TODO.md \
        .exocortex/LESSONS.md \
        .exocortex/PROJECT_MEMORY.md \
        .exocortex/OPEN_DECISIONS.md \
        .exocortex/control/INTERRUPTS.md \
        .exocortex/control/BACKLOG.md \
        .exocortex/control/ROADMAP.md \
        .exocortex/control/EXECUTOR_REGISTRY.json \
        .exocortex/control/EXTERNAL_SYNC_POLICY.json \
        .exocortex/.project-name \
        .gitignore \
        .exocortex/.install-manifest \
        .exocortex/.install-manifest.tmp; do
        assert_safe_target_file_path "$rel"
    done
}

preflight_install_targets
echo "Installing Exocortex from pinned local source into: $TARGET_ROOT"
safe_copy_dir "$SOURCE_COPY/.exocortex" .exocortex
ensure_data_stubs

for rel in AI_START_HERE.md AGENTS.md CLAUDE.md .rules; do
    safe_copy_file "$SOURCE_COPY/$rel" "$rel"
done
safe_copy_dir "$SOURCE_COPY/.agents" .agents
retire_legacy_adapters pre
safe_copy_dir "$SOURCE_COPY/.cursor" .cursor
safe_copy_dir "$SOURCE_COPY/.github/skills" .github/skills
safe_copy_file "$SOURCE_COPY/.github/copilot-instructions.md" .github/copilot-instructions.md
safe_copy_dir "$SOURCE_COPY/.claude/skills" .claude/skills
retire_legacy_adapters post
# Root Cursor rules are project-owned. They are never copied, normalized,
# retired, or manifest-tracked by an ordinary update, but known obsolete
# command mechanics are surfaced for a reviewed reconciliation.
[ ! -e .cursorrules ] || report_preserved_command_drift .cursorrules

if [ -f "$SOURCE_COPY/VERSION" ]; then
    safe_copy_file "$SOURCE_COPY/VERSION" .exocortex/.version
fi

# safe_copy_file preserves each reviewed source file's executable bits. Do not
# blanket-chmod helpers: that creates unreported mode-only target mutations and
# turns intentionally non-executable compatibility helpers into executables.

GITIGNORE=.gitignore
ensure_target_parent "$GITIGNORE"
assert_safe_target_file_path "$GITIGNORE"
gitignore_existed=false
[ -e "$GITIGNORE" ] && gitignore_existed=true
if ! grep -Fq '# BEGIN EXOCORTEX' "$GITIGNORE" 2>/dev/null; then
    {
        [ ! -s "$GITIGNORE" ] || echo
        echo '# BEGIN EXOCORTEX'
        echo '.exocortex/.env'
        echo '.exocortex/events/*.md'
        echo '!.exocortex/events/.gitkeep'
        echo '.exocortex/local/'
        echo '# END EXOCORTEX'
    } >> "$GITIGNORE"
fi
# This separate versioned block upgrades existing installations whose original
# managed block predates the complete project-data boundary. The entries are
# intentionally duplicated by the nested .exocortex/.gitignore as defense in
# depth if either ignore file is later customized.
if ! grep -Fq '# BEGIN EXOCORTEX PROJECT DATA' "$GITIGNORE" 2>/dev/null; then
    {
        echo
        echo '# BEGIN EXOCORTEX PROJECT DATA'
        echo '.exocortex/.env'
        echo '.exocortex/.env.*'
        echo '.exocortex/.envrc'
        echo '.exocortex/local/'
        echo '.exocortex/work-items/'
        echo '.exocortex/planning/'
        echo '.exocortex/archive/'
        echo '.exocortex/hub/'
        echo '.exocortex/.project-name'
        echo '.exocortex/.install-manifest'
        echo '.exocortex/.hub_enabled'
        echo '.exocortex/.hub_disabled'
        echo '.exocortex/SESSION_CONTEXT.md'
        echo '.exocortex/SESSION_CONTEXT.local.md'
        echo '.exocortex/SESSION_CONTEXT.md.backup'
        echo '.exocortex/SESSION_CONTEXT_BACKUP_*.md'
        echo '.exocortex/TODO.md'
        echo '.exocortex/LESSONS.md'
        echo '.exocortex/PROJECT_MEMORY.md'
        echo '.exocortex/OPEN_DECISIONS.md'
        echo '.exocortex/subconscious_patterns.md'
        echo '.exocortex/control/ACTIVE_WORK.md'
        echo '.exocortex/control/BRANCH_POLICY.md'
        echo '.exocortex/control/REPO_STATE.md'
        echo '.exocortex/control/EXECUTOR_REGISTRY.json'
        echo '.exocortex/control/EXTERNAL_SYNC_POLICY.json'
        echo '.exocortex/control/INTERRUPTS.md'
        echo '.exocortex/control/BACKLOG.md'
        echo '.exocortex/control/ROADMAP.md'
        echo '.exocortex/control/ARCH_OVERVIEW.md'
        echo '.exocortex/control/REPO_ORGANIZATION_REPORT.md'
        echo '.exocortex/events/'
        echo '# END EXOCORTEX PROJECT DATA'
    } >> "$GITIGNORE"
fi
if [ "$gitignore_existed" = false ]; then
    chmod 0644 "$GITIGNORE"
fi

ensure_target_dir .exocortex
ensure_target_parent "$MANIFEST"
ensure_target_parent "$MANIFEST.tmp"
if awk 'NF >= 2 && seen[$1]++ { found=1 } END { exit !found }' "$MANIFEST_NEW"; then
    fail "duplicate install-manifest path"
fi
{
    echo '# Exocortex install manifest - template code plane only'
    sort -u "$MANIFEST_NEW"
} > "$MANIFEST.tmp"
mv "$MANIFEST.tmp" "$MANIFEST"

echo "Exocortex install complete."
echo "Global editor, launchd, provider, credential, deployment, and external-sync actions: not attempted."
