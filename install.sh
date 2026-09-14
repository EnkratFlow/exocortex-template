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
[ -f "$SOURCE_ROOT/SHA256SUMS" ] || fail "local template source is missing SHA256SUMS"
SOURCE_SUMS_DIGEST="$(shasum -a 256 "$SOURCE_ROOT/SHA256SUMS" 2>/dev/null | awk '{print $1}')"
[ "$SOURCE_SUMS_DIGEST" = "$CANDIDATE_DIGEST" ] || fail "local template candidate digest does not match the separately approved digest"

TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/exocortex-install.XXXXXX")"
SOURCE_COPY="$TMP_ROOT/source"
MANIFEST_NEW="$TMP_ROOT/manifest-new"
LISTED_SUMS="$TMP_ROOT/listed-sums"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$SOURCE_COPY"
: > "$MANIFEST_NEW"
: > "$LISTED_SUMS"

# Copy without repository metadata or credential files. This is staging only;
# target mutation starts after the complete integrity check.
if command -v rsync >/dev/null 2>&1; then
    rsync -a --exclude='.git' --exclude='.env' --exclude='*/.env' \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
        "$SOURCE_ROOT/" "$SOURCE_COPY/"
else
    (cd "$SOURCE_ROOT" && tar cf - --exclude='.git' --exclude='.env' --exclude='*/.env' \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' .) \
        | (cd "$SOURCE_COPY" && tar xf -)
fi
STAGED_SUMS_DIGEST="$(shasum -a 256 "$SOURCE_COPY/SHA256SUMS" 2>/dev/null | awk '{print $1}')"
[ "$STAGED_SUMS_DIGEST" = "$CANDIDATE_DIGEST" ] || fail "staged template changed after candidate approval"

file_hash() {
    shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
}

is_data_relpath() {
    case "$1" in
        SESSION_CONTEXT.md|SESSION_CONTEXT.local.md|TODO.md|LESSONS.md|PROJECT_MEMORY.md|OPEN_DECISIONS.md|subconscious_patterns.md|.env|.project-name|.install-manifest|.hub_enabled|.hub_disabled)
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
    case "$rel" in
        SHA256SUMS|.git|.git/*|.env|*/.env|__pycache__/*|*/__pycache__/*|*.pyc|*.pyo) return 1 ;;
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

ADAPTER_GENERATOR="$SOURCE_COPY/.exocortex/scripts/generate_command_adapters.py"
ADAPTER_MATRIX="$SOURCE_COPY/.exocortex/provider-adapters.json"
RETIREMENTS="$TMP_ROOT/legacy-retirements.tsv"
[ -f "$ADAPTER_GENERATOR" ] || fail "template source is missing the provider-adapter generator"
[ -f "$ADAPTER_MATRIX" ] || fail "template source is missing the provider-adapter matrix"
command -v python3 >/dev/null 2>&1 || fail "python3 is required to validate provider adapters"
python3 "$ADAPTER_GENERATOR" --check >/dev/null \
    || fail "generated provider adapters do not match the canonical 24-command registry"
python3 - "$ADAPTER_MATRIX" > "$RETIREMENTS" <<'PY'
import json, re, sys
from pathlib import PurePosixPath

matrix = json.load(open(sys.argv[1], encoding='utf-8'))
legacy_items = matrix.get('legacy_retirements')
windsurf_items = matrix.get('windsurf_retirements')
if not isinstance(legacy_items, list) or len(legacy_items) != 24:
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
    if legacy in seen or not re.fullmatch(r'\.agents/skills/[a-z0-9-]+/SKILL\.md', replacement):
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
[ "$(wc -l < "$RETIREMENTS" | tr -d ' ')" = "49" ] \
    || fail "provider-adapter retirement matrix is incomplete"

MANIFEST=".exocortex/.install-manifest"
IS_UPDATE=false
[ -d .exocortex ] && IS_UPDATE=true

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
    local legacy replacement replacement_source_hash replacement_target_hash
    local current_hash installed_hash
    while IFS=$'\t' read -r legacy replacement; do
        [ -n "$legacy" ] || fail "invalid legacy retirement row"
        [ -e "$legacy" ] || continue
        assert_safe_target_file_path "$legacy"
        installed_hash="$(manifest_get "$legacy")"
        if [ -n "$replacement" ]; then
            assert_safe_target_file_path "$replacement"
            if [ ! -f "$SOURCE_COPY/$replacement" ] || [ ! -f "$replacement" ]; then
                [ -n "$installed_hash" ] && record_manifest "$legacy" "$installed_hash"
                echo "EXOCORTEX_ADAPTER_COLLISION_PRESERVED: $legacy (canonical replacement unavailable: $replacement)"
                continue
            fi
            replacement_source_hash="$(file_hash "$SOURCE_COPY/$replacement")"
            replacement_target_hash="$(file_hash "$replacement")"
            if [ "$replacement_source_hash" != "$replacement_target_hash" ]; then
                [ -n "$installed_hash" ] && record_manifest "$legacy" "$installed_hash"
                echo "EXOCORTEX_ADAPTER_COLLISION_PRESERVED: $legacy (customized replacement preserved: $replacement)"
                continue
            fi
        fi
        current_hash="$(file_hash "$legacy")"
        if [ -n "$installed_hash" ] && [ "$current_hash" = "$installed_hash" ]; then
            rm -- "$legacy"
            echo "retired template-managed legacy adapter: $legacy"
        else
            [ -n "$installed_hash" ] && record_manifest "$legacy" "$installed_hash"
            echo "EXOCORTEX_ADAPTER_COLLISION_PRESERVED: $legacy (customized or unknown legacy adapter)"
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

safe_copy_file() {
    local source_file="$1"
    local target_file="$2"
    [ -f "$source_file" ] || return 0
    ensure_target_parent "$target_file"
    assert_safe_target_file_path "$target_file"
    local source_hash current_hash installed_hash
    source_hash="$(file_hash "$source_file")"
    if [ ! -e "$target_file" ]; then
        cp "$source_file" "$target_file"
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
        cp "$source_file" "$target_file"
        record_manifest "$target_file" "$source_hash"
    else
        [ -n "$installed_hash" ] && record_manifest "$target_file" "$installed_hash"
        echo "preserve user-modified or unknown file: $target_file"
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
retire_legacy_adapters
safe_copy_dir "$SOURCE_COPY/.cursor" .cursor
safe_copy_dir "$SOURCE_COPY/.github/skills" .github/skills
safe_copy_file "$SOURCE_COPY/.github/copilot-instructions.md" .github/copilot-instructions.md
safe_copy_dir "$SOURCE_COPY/.claude/skills" .claude/skills

if [ -f "$SOURCE_COPY/VERSION" ]; then
    safe_copy_file "$SOURCE_COPY/VERSION" .exocortex/.version
fi

if [ -d .exocortex/scripts ]; then
    assert_safe_target_path .exocortex/scripts
    find .exocortex/scripts -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod +x {} \;
fi
if [ -d .cursor/hooks ]; then
    assert_safe_target_path .cursor/hooks
    find .cursor/hooks -type f -name '*.sh' -exec chmod +x {} \;
fi

GITIGNORE=.gitignore
ensure_target_parent "$GITIGNORE"
assert_safe_target_file_path "$GITIGNORE"
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

if [ "$IS_UPDATE" = false ]; then
    bash "$SOURCE_COPY/init-project.sh" "$PROJECT_NAME"
fi

echo "Exocortex install complete."
echo "Global editor, launchd, provider, credential, deployment, and external-sync actions: not attempted."
