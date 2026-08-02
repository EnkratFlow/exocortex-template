#!/bin/bash
# Rehearsed, protected-path-safe Exocortex update for one project.

set -euo pipefail

TEMPLATE_SOURCE=""
CANDIDATE_DIGEST=""
BACKUP_INPUT=""
APPLY=false
CAPABILITY=""
WORK_ITEM_ID=""
WORK_ITEM_REVISION=""
REQUEST_ID=""
SURFACE_ID=""
EXECUTOR_ID=""
ADAPTER_VERSION=""
RECONCILIATION_PLAN=""
ARCHIVE_TEST_FAULT="${EXOCORTEX_TEST_ARCHIVE_FAULT:-}"

fail() { echo "ERROR: $*" >&2; exit 1; }

sha256_file() {
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" 2>/dev/null | awk '{print $1}'
    else
        fail "shasum or sha256sum is required"
    fi
}

usage() {
    echo "Usage: safe-update.sh --template ABSOLUTE_PATH --candidate-digest SHA256 --backup-dir ABSOLUTE_PATH [--dry-run]" >&2
    echo "       safe-update.sh --template PATH --candidate-digest SHA256 --backup-dir PATH --apply --capability RELPATH --work-item-id ID --work-item-revision N --request-id ID --surface-id ID --executor-id ID --adapter-version VERSION" >&2
    echo "       Add --reconciliation-plan ABSOLUTE_PATH only for an exact separately reviewed target reconciliation." >&2
    exit 2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --template) TEMPLATE_SOURCE="${2:-}"; shift 2 ;;
        --candidate-digest) CANDIDATE_DIGEST="${2:-}"; shift 2 ;;
        --backup-dir) BACKUP_INPUT="${2:-}"; shift 2 ;;
        --dry-run) APPLY=false; shift ;;
        --apply) APPLY=true; shift ;;
        --capability) CAPABILITY="${2:-}"; shift 2 ;;
        --work-item-id) WORK_ITEM_ID="${2:-}"; shift 2 ;;
        --work-item-revision) WORK_ITEM_REVISION="${2:-}"; shift 2 ;;
        --request-id) REQUEST_ID="${2:-}"; shift 2 ;;
        --surface-id) SURFACE_ID="${2:-}"; shift 2 ;;
        --executor-id) EXECUTOR_ID="${2:-}"; shift 2 ;;
        --adapter-version) ADAPTER_VERSION="${2:-}"; shift 2 ;;
        --reconciliation-plan) RECONCILIATION_PLAN="${2:-}"; shift 2 ;;
        --help|-h) usage ;;
        *) usage ;;
    esac
done

[ -n "$TEMPLATE_SOURCE" ] || fail "--template is required; remote/latest update is disabled"
[ -n "$CANDIDATE_DIGEST" ] || fail "--candidate-digest is required"
[ -n "$BACKUP_INPUT" ] || fail "--backup-dir is required"
case "$TEMPLATE_SOURCE" in /*) ;; *) fail "--template must be absolute" ;; esac
case "$BACKUP_INPUT" in /*) ;; *) fail "--backup-dir must be absolute" ;; esac
[ -d "$TEMPLATE_SOURCE" ] && [ -f "$TEMPLATE_SOURCE/install.sh" ] || fail "invalid template source"
[[ "$CANDIDATE_DIGEST" =~ ^[0-9a-f]{64}$ ]] || fail "--candidate-digest must be a lowercase SHA-256 digest"
if [ -n "$ARCHIVE_TEST_FAULT" ]; then
    [ "${EXOCORTEX_TEST_MODE:-0}" = "1" ] \
        || fail "archive fault injection is available only in explicit test mode"
    [ "$APPLY" = true ] \
        || fail "archive fault injection requires an apply rehearsal"
    case "$ARCHIVE_TEST_FAULT" in
        substitute|corrupt|file-fsync|directory-fsync) ;;
        *) fail "unknown test-only archive fault" ;;
    esac
fi

PROJECT_ROOT="$(pwd -P)"
TEMPLATE_ROOT="$(cd "$TEMPLATE_SOURCE" && pwd -P)"
[ -d "$PROJECT_ROOT/.exocortex" ] || fail "run from an existing Exocortex project"
[ "$PROJECT_ROOT" != "/" ] || fail "refusing filesystem root"
[ "$PROJECT_ROOT" != "${HOME:-/__no_home__}" ] || fail "refusing user home"
[ "$PROJECT_ROOT" != "$TEMPLATE_ROOT" ] || fail "template and target must differ"
case "$TEMPLATE_ROOT/" in "$PROJECT_ROOT/"*) fail "template must not be inside the target" ;; esac
case "$PROJECT_ROOT/" in "$TEMPLATE_ROOT/"*) fail "target must not be inside the template" ;; esac
# An ignore rule cannot change Git's index. This is intentionally advisory:
# the protected sidecar stays untouched, and any Git cleanup remains a separate
# owner decision outside an Exocortex update.
TRACKED_PROTECTED_SIDECAR=false
if git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    && git -C "$PROJECT_ROOT" ls-files --error-unmatch -- .exocortex/SESSION_CONTEXT.md.backup >/dev/null 2>&1; then
    TRACKED_PROTECTED_SIDECAR=true
fi
TRACKED_LEGACY_SESSION_CONTEXT_BACKUP=false
if git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    && git -C "$PROJECT_ROOT" ls-files -- '.exocortex/SESSION_CONTEXT_BACKUP_*.md' | grep -q .; then
    TRACKED_LEGACY_SESSION_CONTEXT_BACKUP=true
fi

[ -f "$TEMPLATE_ROOT/SHA256SUMS" ] && [ ! -L "$TEMPLATE_ROOT/SHA256SUMS" ] \
    || fail "template SHA256SUMS must be a regular non-symlink file"
SOURCE_LINK="$(find "$TEMPLATE_ROOT" -path "$TEMPLATE_ROOT/.git" -prune -o -type l -print -quit 2>/dev/null)" \
    || fail "template source topology could not be inspected safely"
[ -z "$SOURCE_LINK" ] || fail "template source contains a symlink: ${SOURCE_LINK#"$TEMPLATE_ROOT/"}"
ACTUAL_CANDIDATE_DIGEST="$(sha256_file "$TEMPLATE_ROOT/SHA256SUMS")"
[ "$ACTUAL_CANDIDATE_DIGEST" = "$CANDIDATE_DIGEST" ] || fail "template does not match the separately approved candidate digest"
command -v python3 >/dev/null 2>&1 || fail "python3 is required to validate the candidate"

PYTHONDONTWRITEBYTECODE=1 python3 - "$TEMPLATE_ROOT" <<'PY' \
    || fail "template byte or file-mode inventory does not match the approved candidate"
import hashlib
import re
import stat
import sys
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1]).resolve(strict=True)
sums = root / "SHA256SUMS"
modes = root / "FILEMODES"
if sums.is_symlink() or not sums.is_file():
    raise SystemExit("SHA256SUMS must be a regular non-symlink file")
if modes.is_symlink() or not modes.is_file():
    raise SystemExit("FILEMODES must be a regular non-symlink file")

checksum_paths = []
for line in sums.read_text(encoding="utf-8").splitlines():
    match = re.fullmatch(r"([0-9a-f]{64})  ([^/].*)", line)
    if match is None:
        raise SystemExit("malformed SHA256SUMS entry")
    expected_hash, relative = match.groups()
    path = PurePosixPath(relative)
    candidate = root / relative
    if (
        relative in checksum_paths
        or ".." in path.parts
        or "." in path.parts
        or candidate.is_symlink()
        or not candidate.is_file()
    ):
        raise SystemExit("unsafe, duplicate, or missing checksum path")
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected_hash:
        raise SystemExit(f"checksum mismatch: {relative}")
    checksum_paths.append(relative)

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
    candidate = root / relative
    if stat.S_IMODE(candidate.stat().st_mode) != mode_records[relative]:
        raise SystemExit(f"FILEMODES mismatch: {relative}")
PY

# Retired provider paths and project-owned root Cursor rules remain update
# surfaces so rehearsals, authorization, backups, changed-path evidence, and
# rollback cover removals while ordinary updates preserve `.cursorrules`.
surface_paths=(.exocortex .agents .cursor .claude .github .windsurf AI_START_HERE.md AGENTS.md CLAUDE.md .cursorrules .windsurfrules .rules .gitignore)
protected_paths=(
    .exocortex/SESSION_CONTEXT.md
    .exocortex/SESSION_CONTEXT.md.backup
    .exocortex/SESSION_CONTEXT.local.md
    .exocortex/TODO.md
    .exocortex/LESSONS.md
    .exocortex/PROJECT_MEMORY.md
    .exocortex/OPEN_DECISIONS.md
    .exocortex/subconscious_patterns.md
    .exocortex/.env
    .exocortex/.project-name
    .exocortex/events
    .exocortex/archive
    .exocortex/hub
    .exocortex/local
    .exocortex/planning
    .exocortex/work-items
    .exocortex/control/ACTIVE_WORK.md
    .exocortex/control/BRANCH_POLICY.md
    .exocortex/control/REPO_STATE.md
    .exocortex/control/EXECUTOR_REGISTRY.json
    .exocortex/control/EXTERNAL_SYNC_POLICY.json
    .exocortex/control/INTERRUPTS.md
    .exocortex/control/BACKLOG.md
    .exocortex/control/ROADMAP.md
    .exocortex/control/ARCH_OVERVIEW.md
    .exocortex/control/REPO_ORGANIZATION_REPORT.md
    .exocortex/.hub_enabled
    .exocortex/.hub_disabled
)
# This is the documented direct legacy filename family only. It deliberately
# does not broadly exempt arbitrary backup files from the update code plane.
protected_globs=(".exocortex/SESSION_CONTEXT_BACKUP_*.md")

preflight_surface_paths() {
    local rel cursor link hardlink
    local -a parts
    for rel in "${surface_paths[@]}"; do
        cursor="$PROJECT_ROOT"
        IFS='/' read -r -a parts <<< "$rel"
        for part in "${parts[@]}"; do
            cursor="$cursor/$part"
            [ ! -L "$cursor" ] || fail "target update surface contains a symlink: $rel"
            [ -e "$cursor" ] || break
        done
        if [ "$rel" = ".cursorrules" ] && [ -e "$PROJECT_ROOT/$rel" ] && [ ! -f "$PROJECT_ROOT/$rel" ]; then
            fail "target project-owned Cursor rules must be a regular file: $rel"
        fi
        if [ -d "$PROJECT_ROOT/$rel" ]; then
            link="$(find "$PROJECT_ROOT/$rel" -path "*/.claude/worktrees" -prune -o -type l -print -quit 2>/dev/null)" \
                || fail "target update surface could not be inspected safely: $rel"
            [ -z "$link" ] || fail "target update surface contains a symlink: ${link#"$PROJECT_ROOT/"}"
        fi
        if [ -e "$PROJECT_ROOT/$rel" ]; then
            hardlink="$(find "$PROJECT_ROOT/$rel" -path "*/.claude/worktrees" -prune -o -type f -links +1 -print -quit 2>/dev/null)" \
                || fail "target update surface hard-link state could not be inspected safely: $rel"
            [ -z "$hardlink" ] \
                || fail "target update surface contains an external hard-linked file: ${hardlink#"$PROJECT_ROOT/"}"
        fi
    done
}

# Reject target indirection before inventory, backup, or rehearsal can read it.
preflight_surface_paths

RECONCILIATION_HELPER="$TEMPLATE_ROOT/.exocortex/scripts/prepare_update_reconciliation.py"
PLAN_DIGEST=""
GUARD_OPERATION="apply_template_update"
if [ -n "$RECONCILIATION_PLAN" ]; then
    case "$RECONCILIATION_PLAN" in /*) ;; *) fail "--reconciliation-plan must be absolute" ;; esac
    [ -f "$RECONCILIATION_HELPER" ] || fail "template is missing the reconciliation validator"
    [ -f "$RECONCILIATION_PLAN" ] && [ ! -L "$RECONCILIATION_PLAN" ] \
        || fail "reconciliation plan must be a regular non-symlink file"
    PLAN_DIGEST="$(PYTHONDONTWRITEBYTECODE=1 python3 "$RECONCILIATION_HELPER" validate \
        --target "$PROJECT_ROOT" --template "$TEMPLATE_ROOT" \
        --candidate-digest "$CANDIDATE_DIGEST" --plan "$RECONCILIATION_PLAN" \
        --emit plan-digest)" || fail "reconciliation plan failed closed before backup or rehearsal"
    [[ "$PLAN_DIGEST" =~ ^[0-9a-f]{64}$ ]] || fail "reconciliation validator did not return a plan digest"
    GUARD_OPERATION="apply_template_reconciliation"
fi

BACKUP_NORMALIZED="$(python3 - "$BACKUP_INPUT" <<'PY'
import os, sys
from pathlib import Path

raw = Path(os.path.abspath(sys.argv[1]))
cursor = Path(raw.anchor)
for part in raw.parts[1:]:
    candidate = cursor / part
    if candidate.is_symlink():
        try:
            candidate = candidate.resolve(strict=True)
        except OSError as exc:
            raise SystemExit(f'backup path contains an invalid symlink ancestor: {candidate}') from exc
    if candidate.exists() and not candidate.is_dir():
        raise SystemExit(f'backup path ancestor is not a directory: {candidate}')
    cursor = candidate
print(cursor)
PY
)"

[ "$BACKUP_NORMALIZED" != "/" ] || fail "refusing filesystem root as backup directory"
HOME_CANONICAL=""
if [ -d "${HOME:-}" ]; then HOME_CANONICAL="$(cd "$HOME" && pwd -P)"; fi
[ -z "$HOME_CANONICAL" ] || [ "$BACKUP_NORMALIZED" != "$HOME_CANONICAL" ] || fail "refusing user home as backup directory"
case "$BACKUP_NORMALIZED/" in "$PROJECT_ROOT/"*|"$TEMPLATE_ROOT/"*) fail "backup directory must be outside target and template" ;; esac
if [ -n "$ARCHIVE_TEST_FAULT" ]; then
    TEST_TEMP_ROOT="$(cd "${TMPDIR:-/tmp}" && pwd -P)"
    case "$BACKUP_NORMALIZED" in
        "$TEST_TEMP_ROOT"/exo-test-archive-fault.*) ;;
        *) fail "archive fault injection requires a dedicated temporary backup fixture" ;;
    esac
    [ -d "$BACKUP_NORMALIZED" ] \
        || fail "archive fault injection backup fixture must already exist"
    [ -z "$(find "$BACKUP_NORMALIZED" -mindepth 1 -print -quit)" ] \
        || fail "archive fault injection backup fixture must be empty"
fi

GUARD=""
GUARD_DIGEST=""
if [ "$APPLY" = true ]; then
    for value in "$CAPABILITY" "$WORK_ITEM_ID" "$WORK_ITEM_REVISION" "$REQUEST_ID" "$SURFACE_ID" "$EXECUTOR_ID" "$ADAPTER_VERSION"; do
        [ -n "$value" ] || fail "--apply requires complete guarded-executor identity and capability arguments"
    done
    GUARD="$TEMPLATE_ROOT/.exocortex/scripts/authority_guard.py"
    GUARD_DIGEST="$(python3 "$GUARD" guard-digest)"
    if [ -n "$RECONCILIATION_PLAN" ]; then
        PYTHONDONTWRITEBYTECODE=1 python3 "$RECONCILIATION_HELPER" validate \
            --target "$PROJECT_ROOT" --template "$TEMPLATE_ROOT" \
            --candidate-digest "$CANDIDATE_DIGEST" --plan "$RECONCILIATION_PLAN" \
            --expected-work-item-id "$WORK_ITEM_ID" \
            --expected-work-item-revision "$WORK_ITEM_REVISION" \
            --emit plan-digest | grep -Fqx "$PLAN_DIGEST" \
            || fail "reconciliation plan does not match the exact work-item authority"
    fi
    pre_guard_args=(
        check --project-root "$PROJECT_ROOT" --capability "$CAPABILITY"
        --operation "$GUARD_OPERATION" --work-item-id "$WORK_ITEM_ID"
        --work-item-revision "$WORK_ITEM_REVISION" --request-id "$REQUEST_ID"
        --surface-id "$SURFACE_ID" --executor-id "$EXECUTOR_ID"
        --adapter-version "$ADAPTER_VERSION" --guard-digest "$GUARD_DIGEST"
        --role writer --target-sha "$CANDIDATE_DIGEST"
    )
    if [ -n "$RECONCILIATION_PLAN" ]; then
        pre_guard_args+=(--payload-digest "$PLAN_DIGEST" --require-exact-path-set)
        while IFS= read -r rel; do pre_guard_args+=(--target-path "$rel"); done < <(
            PYTHONDONTWRITEBYTECODE=1 python3 "$RECONCILIATION_HELPER" validate \
                --target "$PROJECT_ROOT" --template "$TEMPLATE_ROOT" \
                --candidate-digest "$CANDIDATE_DIGEST" --plan "$RECONCILIATION_PLAN" \
                --expected-work-item-id "$WORK_ITEM_ID" \
                --expected-work-item-revision "$WORK_ITEM_REVISION" \
                --emit effect-paths
        )
    fi
    # Deny an invalid/revoked apply before backup creation or target rehearsal.
    python3 "$GUARD" "${pre_guard_args[@]}" >/dev/null
fi

inventory_digest() {
    local root="$1" mode="$2" skip="${3:-}"
    python3 - "$root" "$mode" "$skip" <<'PY'
import hashlib, os, stat, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
mode = sys.argv[2]
surface = ['.exocortex','.agents','.cursor','.claude','.github','.windsurf','AI_START_HERE.md','AGENTS.md','CLAUDE.md','.cursorrules','.windsurfrules','.rules','.gitignore']
protected = [
    '.exocortex/SESSION_CONTEXT.md','.exocortex/SESSION_CONTEXT.md.backup','.exocortex/SESSION_CONTEXT.local.md',
    '.exocortex/TODO.md','.exocortex/LESSONS.md','.exocortex/PROJECT_MEMORY.md',
    '.exocortex/OPEN_DECISIONS.md','.exocortex/subconscious_patterns.md',
    '.exocortex/.env','.exocortex/.project-name','.exocortex/events',
    '.exocortex/archive','.exocortex/hub','.exocortex/local','.exocortex/planning',
    '.exocortex/work-items','.exocortex/control/ACTIVE_WORK.md',
    '.exocortex/control/BRANCH_POLICY.md','.exocortex/control/REPO_STATE.md',
    '.exocortex/control/EXECUTOR_REGISTRY.json',
    '.exocortex/control/EXTERNAL_SYNC_POLICY.json',
    '.exocortex/control/INTERRUPTS.md','.exocortex/control/BACKLOG.md',
    '.exocortex/control/ROADMAP.md','.exocortex/control/ARCH_OVERVIEW.md',
    '.exocortex/control/REPO_ORGANIZATION_REPORT.md',
    '.exocortex/.hub_enabled','.exocortex/.hub_disabled',
]
legacy_backup_prefix = '.exocortex/SESSION_CONTEXT_BACKUP_'
selected = surface if mode in ('surface', 'code_plane') else protected if mode == 'protected' else None
if selected is None:
    raise SystemExit('invalid inventory mode')
def legacy_session_context_backup(relative):
    return (
        relative.startswith(legacy_backup_prefix)
        and relative.endswith('.md')
        and '/' not in relative[len(legacy_backup_prefix):]
    )
if mode == 'protected':
    legacy_root = root / '.exocortex'
    if legacy_root.is_dir() and not legacy_root.is_symlink():
        selected = selected + sorted(
            path.relative_to(root).as_posix()
            for path in legacy_root.iterdir()
            if legacy_session_context_backup(path.relative_to(root).as_posix())
        )
skip_argument = sys.argv[3] if len(sys.argv) > 3 else ''
skip = (
    [entry for entry in skip_argument.splitlines() if entry]
    if mode == 'protected'
    else []
)
def runtime_state(relative):
    # Editor session worktrees are runtime state, never update surface —
    # matched at any depth so archive excludes and digests stay symmetric.
    parts = relative.split('/')
    return any(
        parts[index] == '.claude' and parts[index + 1] == 'worktrees'
        for index in range(len(parts) - 1)
    )
def scaffold_directory(relative):
    # Installer-created protocol scaffolding directories carry no user data;
    # protected comparisons track the runtime records (files) inside instead.
    return mode == 'protected' and relative.startswith('.exocortex/local/')
def excluded(relative):
    if runtime_state(relative):
        return True
    return mode in ('surface', 'code_plane') and (
        legacy_session_context_backup(relative)
        or any(relative == item or relative.startswith(item + '/') for item in protected)
    )
def directory_record(path, relative):
    value = os.lstat(path)
    return f'dir:{stat.S_IMODE(value.st_mode):04o}'
def file_record(path):
    value = os.lstat(path)
    return (
        f'file:{stat.S_IMODE(value.st_mode):04o}:{value.st_nlink}:'
        + hashlib.sha256(path.read_bytes()).hexdigest()
    )
def symlink_record(path):
    value = os.lstat(path)
    return (
        f'symlink:{stat.S_IMODE(value.st_mode):04o}:{value.st_nlink}:'
        + os.readlink(path)
    )
records = {}
for rel in selected:
    if excluded(rel):
        continue
    base = root / rel
    if base.is_symlink():
        records[rel] = symlink_record(base)
    elif base.is_file():
        records[rel] = file_record(base)
    elif base.is_dir():
        records[rel] = directory_record(base, rel)
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames.sort()
            filenames.sort()
            here = Path(dirpath)
            for name in list(dirnames):
                path = here / name
                child = path.relative_to(root).as_posix()
                if excluded(child):
                    continue
                if path.is_symlink():
                    records[child] = symlink_record(path)
                elif not scaffold_directory(child):
                    records[child] = directory_record(path, child)
            dirnames[:] = [
                name
                for name in dirnames
                if not (here / name).is_symlink()
                and not excluded((here / name).relative_to(root).as_posix())
            ]
            for name in filenames:
                path = here / name
                child = path.relative_to(root).as_posix()
                if excluded(child):
                    continue
                if path.is_symlink():
                    records[child] = symlink_record(path)
                elif path.is_file():
                    records[child] = file_record(path)
    else:
        records[rel] = 'absent'
for rel in skip:
    if rel in selected:
        # Approved installer-created bootstrap: compare as if still absent.
        records = {
            key: value
            for key, value in records.items()
            if not (key == rel or key.startswith(rel + '/'))
        }
        records[rel] = 'absent'
digest = hashlib.sha256()
for rel, value in sorted(records.items()):
    digest.update(rel.encode('utf-8') + b'\0' + value.encode('utf-8') + b'\0')
print(digest.hexdigest())
PY
}

BASE_SURFACE_DIGEST="$(inventory_digest "$PROJECT_ROOT" surface)"
BASE_CODE_PLANE_DIGEST="$(inventory_digest "$PROJECT_ROOT" code_plane)"
BASE_PROTECTED_DIGEST="$(inventory_digest "$PROJECT_ROOT" protected)"

mkdir -p "$BACKUP_NORMALIZED"
BACKUP_DIR="$(cd "$BACKUP_NORMALIZED" && pwd -P)"
[ "$BACKUP_DIR" != "/" ] || fail "refusing filesystem root as backup directory"
[ "$BACKUP_DIR" != "${HOME:-/__no_home__}" ] || fail "refusing user home as backup directory"
case "$BACKUP_DIR/" in "$PROJECT_ROOT/"*|"$TEMPLATE_ROOT/"*) fail "backup directory must be outside target and template" ;; esac
PYTHONDONTWRITEBYTECODE=1 python3 - "$BACKUP_DIR" <<'PY' \
    || fail "backup directory permissions or ancestry are unsafe"
import os
from pathlib import Path
import stat
import sys

path = Path(sys.argv[1]).resolve(strict=True)
current = path
while True:
    value = os.lstat(current)
    if not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode):
        raise SystemExit("backup path must contain only real directories")
    mode = stat.S_IMODE(value.st_mode)
    if current == path:
        if value.st_uid != os.geteuid() or mode & 0o022:
            raise SystemExit("backup directory must be owner-controlled and not group/world writable")
    elif mode & 0o022 and not mode & stat.S_ISVTX:
        raise SystemExit("writable backup ancestor must have the sticky bit")
    if current == current.parent:
        break
    current = current.parent
PY

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/exocortex-safe-update.XXXXXX")"
REHEARSAL="$WORK_DIR/rehearsal"
FAKE_HOME="$WORK_DIR/fake-home"
CHANGES="$WORK_DIR/changed-paths.txt"
PROTECTED_DIFF="$WORK_DIR/protected-diff.txt"
PLANNED_EFFECTS="$WORK_DIR/planned-effect-paths.txt"
BACKUP_VERIFY="$WORK_DIR/backup-verify"
REHEARSAL_INSTALL_LOG="$WORK_DIR/rehearsal-install.log"
RECONCILED_INSTALL_LOG="$WORK_DIR/reconciled-install.log"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$REHEARSAL" "$FAKE_HOME" "$BACKUP_VERIFY"
if [ -n "$RECONCILIATION_PLAN" ]; then
    PYTHONDONTWRITEBYTECODE=1 python3 "$RECONCILIATION_HELPER" validate \
        --target "$PROJECT_ROOT" --template "$TEMPLATE_ROOT" \
        --candidate-digest "$CANDIDATE_DIGEST" --plan "$RECONCILIATION_PLAN" \
        --emit effect-paths > "$PLANNED_EFFECTS" \
        || fail "reconciliation plan changed after initial validation"
fi

for rel in "${surface_paths[@]}"; do
    if [ -e "$PROJECT_ROOT/$rel" ]; then
        mkdir -p "$REHEARSAL/$(dirname "$rel")"
        cp -pR "$PROJECT_ROOT/$rel" "$REHEARSAL/$(dirname "$rel")/"
    fi
done
# Editor session worktrees are runtime state, never update surface; drop them
# from the rehearsal so they cannot skew evidence or block on their contents.
rm -rf "$REHEARSAL/.claude/worktrees"

# Close the preflight-to-archive window before any target byte is read into
# rollback evidence.
preflight_surface_paths
backup_umask="$(umask)"
umask 077
BACKUP_PREFIX="$(basename "$PROJECT_ROOT")-exocortex-before-update-$(date -u +%Y%m%d-%H%M%S)"
BACKUP_PARTIAL="$(mktemp "$BACKUP_DIR/.$BACKUP_PREFIX.tar.gz.partial.XXXXXX")" \
    || fail "could not reserve a unique rollback archive"
umask "$backup_umask"
BACKUP_SUFFIX="${BACKUP_PARTIAL##*.partial.}"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_PREFIX.tar.gz.$BACKUP_SUFFIX"
[ -f "$BACKUP_PARTIAL" ] && [ ! -L "$BACKUP_PARTIAL" ] \
    || fail "rollback archive reservation is not a regular file"
IFS=: read -r BACKUP_DEV BACKUP_INO < <(
    python3 -c 'import os,sys; value=os.lstat(sys.argv[1]); print(f"{value.st_dev}:{value.st_ino}")' "$BACKUP_PARTIAL"
)
if [ "$ARCHIVE_TEST_FAULT" = "substitute" ]; then
    PYTHONDONTWRITEBYTECODE=1 python3 - "$BACKUP_PARTIAL" <<'PY' \
        || { rm -f -- "$BACKUP_PARTIAL"; fail "test-only rollback archive substitution failed"; }
import os
from pathlib import Path
import stat
import sys

path = Path(sys.argv[1])
replacement = path.with_name(path.name + ".test-substitute")
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
fd = os.open(replacement, flags, 0o600)
try:
    os.fchmod(fd, 0o600)
    value = os.fstat(fd)
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise OSError("test replacement is not a single-link regular file")
    payload = b"EXOCORTEX_TEST_ARCHIVE_SUBSTITUTION_CANARY\n"
    if os.write(fd, payload) != len(payload):
        raise OSError("short test replacement write")
    os.fsync(fd)
finally:
    os.close(fd)
os.replace(replacement, path)
directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
try:
    os.fsync(directory_fd)
finally:
    os.close(directory_fd)
PY
fi
backup_items=()
for rel in "${surface_paths[@]}"; do [ -e "$PROJECT_ROOT/$rel" ] && backup_items+=("$rel"); done
[ "${#backup_items[@]}" -gt 0 ] || fail "nothing to back up"
backup_excludes=()
for rel in "${protected_paths[@]}" "${protected_globs[@]}"; do backup_excludes+=("--exclude=$rel"); done
# Editor session worktrees are runtime state: excluded from the rollback
# archive exactly as they are excluded from every inventory digest, so the
# archive reconstruction comparison stays exact.
backup_excludes+=("--exclude=.claude/worktrees")
if (cd "$PROJECT_ROOT" && COPYFILE_DISABLE=1 tar "${backup_excludes[@]}" -czf - "${backup_items[@]}") \
    | PYTHONDONTWRITEBYTECODE=1 python3 -c '
import os
import stat
import sys

path, expected_dev, expected_ino, fault = (
    sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
)
flags = os.O_WRONLY
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
fd = os.open(path, flags)
try:
    before = os.fstat(fd)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or before.st_dev != expected_dev
        or before.st_ino != expected_ino
        or stat.S_IMODE(before.st_mode) != 0o600
    ):
        raise SystemExit("rollback archive identity changed before write")
    os.ftruncate(fd, 0)
    while True:
        chunk = sys.stdin.buffer.read(1024 * 1024)
        if not chunk:
            break
        view = memoryview(chunk)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short rollback archive write")
            view = view[written:]
    if fault == "file-fsync":
        raise OSError("injected test-only rollback archive file-fsync failure")
    os.fsync(fd)
finally:
    os.close(fd)
' "$BACKUP_PARTIAL" "$BACKUP_DEV" "$BACKUP_INO" "$ARCHIVE_TEST_FAULT"; then
    :
else
    if [ "$ARCHIVE_TEST_FAULT" = "substitute" ]; then
        if PYTHONDONTWRITEBYTECODE=1 python3 - "$BACKUP_PARTIAL" <<'PY'
import os
import stat
import sys

path = sys.argv[1]
flags = os.O_RDONLY
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
fd = os.open(path, flags)
try:
    value = os.fstat(fd)
    content = os.read(fd, 1024)
    if (
        not stat.S_ISREG(value.st_mode)
        or value.st_nlink != 1
        or content != b"EXOCORTEX_TEST_ARCHIVE_SUBSTITUTION_CANARY\n"
    ):
        raise SystemExit(1)
finally:
    os.close(fd)
PY
        then
            echo "test-only rollback archive substitution canary preserved" >&2
        else
            rm -f -- "$BACKUP_PARTIAL"
            fail "rollback archive substitution canary was altered before rejection"
        fi
    fi
    rm -f -- "$BACKUP_PARTIAL"
    fail "rollback archive creation failed"
fi
BACKUP_DIGEST="$(sha256_file "$BACKUP_PARTIAL")"
if [ "$ARCHIVE_TEST_FAULT" = "corrupt" ]; then
    PYTHONDONTWRITEBYTECODE=1 python3 - "$BACKUP_PARTIAL" "$BACKUP_DEV" "$BACKUP_INO" <<'PY' \
        || { rm -f -- "$BACKUP_PARTIAL"; fail "test-only rollback archive corruption failed"; }
import os
import stat
import sys

path, expected_dev, expected_ino = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
flags = os.O_RDWR
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
fd = os.open(path, flags)
try:
    value = os.fstat(fd)
    if (
        not stat.S_ISREG(value.st_mode)
        or value.st_nlink != 1
        or value.st_dev != expected_dev
        or value.st_ino != expected_ino
        or stat.S_IMODE(value.st_mode) != 0o600
    ):
        raise SystemExit("rollback archive identity changed before test corruption")
    os.lseek(fd, -1, os.SEEK_END)
    byte = os.read(fd, 1)
    if len(byte) != 1:
        raise SystemExit("rollback archive is unexpectedly empty")
    os.lseek(fd, -1, os.SEEK_END)
    os.write(fd, bytes((byte[0] ^ 0xFF,)))
    os.fsync(fd)
finally:
    os.close(fd)
PY
fi
PYTHONDONTWRITEBYTECODE=1 python3 - "$BACKUP_PARTIAL" "$BACKUP_DEV" "$BACKUP_INO" "$BACKUP_DIGEST" <<'PY' \
    || { rm -f -- "$BACKUP_PARTIAL"; fail "rollback archive failed identity, privacy, or integrity verification"; }
import hashlib
import os
from pathlib import PurePosixPath
import stat
import sys
import tarfile

path = sys.argv[1]
expected_dev, expected_ino = int(sys.argv[2]), int(sys.argv[3])
expected_digest = sys.argv[4]
value = os.lstat(path)
if (
    not stat.S_ISREG(value.st_mode)
    or value.st_nlink != 1
    or value.st_dev != expected_dev
    or value.st_ino != expected_ino
    or stat.S_IMODE(value.st_mode) != 0o600
):
    raise SystemExit("rollback archive identity or mode changed")
digest = hashlib.sha256()
with open(path, "rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != expected_digest:
    raise SystemExit("rollback archive digest mismatch")
protected = (
    ".exocortex/SESSION_CONTEXT.md", ".exocortex/SESSION_CONTEXT.md.backup", ".exocortex/SESSION_CONTEXT.local.md",
    ".exocortex/TODO.md", ".exocortex/LESSONS.md", ".exocortex/PROJECT_MEMORY.md",
    ".exocortex/OPEN_DECISIONS.md", ".exocortex/subconscious_patterns.md",
    ".exocortex/.env", ".exocortex/.project-name", ".exocortex/events",
    ".exocortex/archive", ".exocortex/hub", ".exocortex/local",
    ".exocortex/planning", ".exocortex/work-items",
    ".exocortex/control/ACTIVE_WORK.md", ".exocortex/control/BRANCH_POLICY.md",
    ".exocortex/control/REPO_STATE.md", ".exocortex/control/EXECUTOR_REGISTRY.json",
    ".exocortex/control/EXTERNAL_SYNC_POLICY.json",
    ".exocortex/control/INTERRUPTS.md", ".exocortex/control/BACKLOG.md",
    ".exocortex/control/ROADMAP.md", ".exocortex/control/ARCH_OVERVIEW.md",
    ".exocortex/control/REPO_ORGANIZATION_REPORT.md",
    ".exocortex/.hub_enabled", ".exocortex/.hub_disabled",
)
legacy_backup_prefix = ".exocortex/SESSION_CONTEXT_BACKUP_"
def legacy_session_context_backup(name):
    return (
        name.startswith(legacy_backup_prefix)
        and name.endswith(".md")
        and "/" not in name[len(legacy_backup_prefix):]
    )
def runtime_state(name):
    parts = name.split("/")
    return any(
        parts[index] == ".claude" and parts[index + 1] == "worktrees"
        for index in range(len(parts) - 1)
    )
with tarfile.open(path, "r:gz") as archive:
    members = archive.getmembers()
    if not members:
        raise SystemExit("rollback archive is empty")
    for member in members:
        name = member.name[2:] if member.name.startswith("./") else member.name
        relative = PurePosixPath(name)
        if (
            not name
            or name.startswith("/")
            or ".." in relative.parts
            or member.issym()
            or member.islnk()
            or not (member.isfile() or member.isdir())
            or runtime_state(name)
            or legacy_session_context_backup(name)
            or any(name == item or name.startswith(item + "/") for item in protected)
        ):
            raise SystemExit(f"unsafe or protected rollback archive member: {name}")
PY
COPYFILE_DISABLE=1 tar -xzpf "$BACKUP_PARTIAL" -C "$BACKUP_VERIFY" \
    || { rm -f -- "$BACKUP_PARTIAL"; fail "rollback archive could not be reconstructed"; }
[ "$(inventory_digest "$BACKUP_VERIFY" code_plane)" = "$BASE_CODE_PLANE_DIGEST" ] \
    || { rm -f -- "$BACKUP_PARTIAL"; fail "rollback archive does not reconstruct the exact prior code plane"; }
PYTHONDONTWRITEBYTECODE=1 python3 - "$BACKUP_PARTIAL" "$BACKUP_PATH" "$ARCHIVE_TEST_FAULT" <<'PY' \
    || { rm -f -- "$BACKUP_PARTIAL" "$BACKUP_PATH"; fail "rollback archive publication failed"; }
import os
from pathlib import Path
import sys

partial, final, fault = sys.argv[1:4]
os.link(partial, final, follow_symlinks=False)
os.unlink(partial)
directory_fd = os.open(Path(final).parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
try:
    if fault == "directory-fsync":
        raise OSError("injected test-only rollback archive directory-fsync failure")
    os.fsync(directory_fd)
finally:
    os.close(directory_fd)
PY

verify_backup_archive() {
    [ -f "$BACKUP_PATH" ] && [ ! -L "$BACKUP_PATH" ] \
        && [ "$(sha256_file "$BACKUP_PATH")" = "$BACKUP_DIGEST" ] \
        && python3 - "$BACKUP_PATH" "$BACKUP_DEV" "$BACKUP_INO" <<'PY'
import os
import stat
import sys
value = os.lstat(sys.argv[1])
raise SystemExit(
    0 if (
        stat.S_ISREG(value.st_mode)
        and value.st_nlink == 1
        and value.st_dev == int(sys.argv[2])
        and value.st_ino == int(sys.argv[3])
        and stat.S_IMODE(value.st_mode) == 0o600
    ) else 1
)
PY
}
verify_backup_archive || fail "rollback archive changed after durable publication"

run_installer_logged() {
    local destination="$1" log_file="$2" status
    if (cd "$destination" && HOME="$FAKE_HOME" EXOCORTEX_TEST_INSTALL_FAULT_AFTER_COPIES=0 \
        EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_ROOT" EXOCORTEX_CANDIDATE_DIGEST="$CANDIDATE_DIGEST" \
        bash "$TEMPLATE_ROOT/install.sh" "$(basename "$PROJECT_ROOT")") > "$log_file" 2>&1; then
        cat "$log_file"
    else
        status=$?
        cat "$log_file" >&2
        return "$status"
    fi
}

command_reconciliation_required() {
    LC_ALL=C grep -Eq \
        '^EXOCORTEX_(COMMAND_AUTHORITY_COLLISION|STALE_COMMAND_GUIDANCE)_PRESERVED:' \
        "$1"
}

run_installer_logged "$REHEARSAL" "$REHEARSAL_INSTALL_LOG"
COMMAND_RECONCILIATION_REQUIRED=false
if command_reconciliation_required "$REHEARSAL_INSTALL_LOG"; then
    COMMAND_RECONCILIATION_REQUIRED=true
fi

materialize_reconciliation() {
    local destination="$1"
    [ -n "$RECONCILIATION_PLAN" ] || return 0
    PYTHONDONTWRITEBYTECODE=1 python3 - \
        "$RECONCILIATION_HELPER" "$RECONCILIATION_PLAN" "$destination" \
        "$TEMPLATE_ROOT" "$PROJECT_ROOT" "$PLAN_DIGEST" <<'PY'
import importlib.util
import hashlib
import sys
from pathlib import Path

helper, plan_name, destination, template, baseline = map(Path, sys.argv[1:6])
expected_plan_digest = sys.argv[6]
spec = importlib.util.spec_from_file_location("exocortex_update_reconciliation", helper)
if spec is None or spec.loader is None:
    raise SystemExit("reconciliation helper could not be loaded")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
raw_plan = plan_name.read_bytes()
if hashlib.sha256(raw_plan).hexdigest() != expected_plan_digest:
    raise SystemExit("reconciliation plan changed before materialization")
plan = module.parse_plan_bytes(raw_plan)
module.validate_plan(
    plan,
    target=baseline,
    template=template,
    candidate_digest=plan["candidate_digest"],
    require_current_target=False,
)
module.materialize_plan(
    plan,
    destination_root=destination,
    template=template,
    baseline_target=baseline,
)
PY
}

materialize_reconciliation "$REHEARSAL" \
    || fail "reconciliation could not be materialized in the disposable rehearsal"
if [ -n "$RECONCILIATION_PLAN" ]; then
    # Re-run the deterministic installer after exact reconciliation so
    # candidate adoptions are reflected in the install manifest while
    # reviewed unknown objects remain preserved. This pass is part of the
    # rehearsed exact effect and must not add paths outside the plan.
    run_installer_logged "$REHEARSAL" "$RECONCILED_INSTALL_LOG"
    if command_reconciliation_required "$RECONCILED_INSTALL_LOG"; then
        fail "reviewed reconciliation left command authority or stale command-guidance drift"
    fi
    COMMAND_RECONCILIATION_REQUIRED=false
fi
REHEARSAL_CODE_PLANE_DIGEST="$(inventory_digest "$REHEARSAL" code_plane)"

allowed_generated() {
    local rel="$1" path="$2" probe
    if [ -d "$path" ] && [ ! -L "$path" ]; then
        if [ "$rel" = ".exocortex/local" ]; then
            # Installer-created protocol scaffolding: allowed only while it
            # holds no runtime records at all (directories only).
            probe="$(find "$path" ! -type d -print -quit 2>/dev/null)" || return 1
            [ -z "$probe" ]
            return
        fi
        # Any other protected directory qualifies only while completely empty.
        probe="$(find "$path" -mindepth 1 -print -quit 2>/dev/null)" || return 1
        [ -z "$probe" ]
        return
    fi
    [ -f "$path" ] || return 1
    case "$rel" in
        .exocortex/SESSION_CONTEXT.md) grep -Fq '_No active session context yet._' "$path" ;;
        .exocortex/TODO.md) grep -Fq '_No tasks captured yet._' "$path" ;;
        .exocortex/LESSONS.md) grep -Fq '_No lessons captured yet._' "$path" ;;
        .exocortex/PROJECT_MEMORY.md) grep -Fq '_No project-specific memory captured yet._' "$path" ;;
        .exocortex/OPEN_DECISIONS.md) grep -Fq '_No open decisions captured yet._' "$path" ;;
        .exocortex/control/INTERRUPTS.md) grep -Fq '_No interrupts captured yet._' "$path" ;;
        .exocortex/control/BACKLOG.md) grep -Fq '_No backlog items yet._' "$path" ;;
        .exocortex/control/ROADMAP.md) grep -Fq '_No roadmap defined yet._' "$path" ;;
        .exocortex/control/EXECUTOR_REGISTRY.json)
            python3 - "$path" <<'PY'
import json, sys
d=json.load(open(sys.argv[1], encoding='utf-8'))
raise SystemExit(0 if d == {"schema_version":"public-v2","kind":"executor_registry","registry_version":1,"default_role":"read_only","executors":[]} else 1)
PY
            ;;
        .exocortex/control/EXTERNAL_SYNC_POLICY.json)
            python3 - "$path" <<'PY'
import json, sys
d=json.load(open(sys.argv[1], encoding='utf-8'))
raise SystemExit(0 if d == {"schema_version":"public-v2","kind":"external_sync_policy","default":"deny","policy_version":1,"destinations":[]} else 1)
PY
            ;;
        *) return 1 ;;
    esac
}

: > "$PROTECTED_DIFF"
ALLOWED_NEW_PROTECTED=""
for rel in "${protected_paths[@]}"; do
    left="$PROJECT_ROOT/$rel"
    right="$REHEARSAL/$rel"
    if [ -e "$left" ] && [ -e "$right" ]; then
        if [ "$rel" = ".exocortex/local" ] && [ -d "$left" ] && [ ! -L "$left" ] && [ -d "$right" ]; then
            # Runtime records are files and symlinks; installer scaffolding
            # directories are not protected content. Compare records exactly
            # so a legacy target adopting new scaffolding still updates while
            # any real record difference fails closed.
            PYTHONDONTWRITEBYTECODE=1 python3 - "$left" "$right" >> "$PROTECTED_DIFF" 2>&1 <<'PY' \
                || fail "protected runtime records could not be compared"
import hashlib, os, sys
from pathlib import Path

def records(root):
    result = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if not (Path(dirpath) / d).is_symlink())
        for name in sorted(filenames):
            path = Path(dirpath) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[rel] = 'symlink:' + os.readlink(path)
            elif path.is_file():
                result[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            else:
                result[rel] = 'special'
    return result

left, right = records(Path(sys.argv[1])), records(Path(sys.argv[2]))
for rel in sorted(set(left) | set(right)):
    if left.get(rel) != right.get(rel):
        print(f'protected runtime record differs: .exocortex/local/{rel}')
PY
        else
            diff -rq "$left" "$right" >> "$PROTECTED_DIFF" 2>&1 || true
        fi
    elif [ -e "$left" ] || [ -e "$right" ]; then
        existing="$left"; [ -e "$existing" ] || existing="$right"
        if allowed_generated "$rel" "$existing"; then
            # An installer-created default that exists only on the rehearsal
            # side is a bootstrap, not drift; digest comparisons treat it as
            # absent so a legacy target can adopt the current layout.
            [ -e "$left" ] || ALLOWED_NEW_PROTECTED="${ALLOWED_NEW_PROTECTED}${rel}
"
            continue
        fi
        echo "protected path exists on one side only: $rel" >> "$PROTECTED_DIFF"
        if [ "$rel" = ".exocortex/.project-name" ] && [ ! -e "$left" ]; then
            echo "hint: project identity is owner-approved, never inferred; run init-project.sh with the exact project name, then update" >> "$PROTECTED_DIFF"
        fi
    fi
done
[ ! -s "$PROTECTED_DIFF" ] || { sed -n '1,120p' "$PROTECTED_DIFF" >&2; fail "protected data changed in rehearsal"; }
[ "$(inventory_digest "$REHEARSAL" protected "$ALLOWED_NEW_PROTECTED")" = "$BASE_PROTECTED_DIGEST" ] \
    || fail "protected data modes changed in rehearsal"

python3 - "$PROJECT_ROOT" "$REHEARSAL" "$CHANGES" <<'PY'
import hashlib, os, stat, sys
from pathlib import Path

left, right, output = map(Path, sys.argv[1:])
surface = ['.exocortex','.agents','.cursor','.claude','.github','.windsurf','AI_START_HERE.md','AGENTS.md','CLAUDE.md','.cursorrules','.windsurfrules','.rules','.gitignore']
protected = [
    '.exocortex/SESSION_CONTEXT.md','.exocortex/SESSION_CONTEXT.md.backup','.exocortex/SESSION_CONTEXT.local.md',
    '.exocortex/TODO.md','.exocortex/LESSONS.md','.exocortex/PROJECT_MEMORY.md',
    '.exocortex/OPEN_DECISIONS.md','.exocortex/subconscious_patterns.md',
    '.exocortex/.env','.exocortex/.project-name','.exocortex/events',
    '.exocortex/archive','.exocortex/hub','.exocortex/local','.exocortex/planning',
    '.exocortex/work-items','.exocortex/control/ACTIVE_WORK.md',
    '.exocortex/control/BRANCH_POLICY.md','.exocortex/control/REPO_STATE.md',
    '.exocortex/control/EXECUTOR_REGISTRY.json',
    '.exocortex/control/EXTERNAL_SYNC_POLICY.json',
    '.exocortex/control/INTERRUPTS.md','.exocortex/control/BACKLOG.md',
    '.exocortex/control/ROADMAP.md','.exocortex/control/ARCH_OVERVIEW.md',
    '.exocortex/control/REPO_ORGANIZATION_REPORT.md',
    '.exocortex/.hub_enabled','.exocortex/.hub_disabled',
]
legacy_backup_prefix = '.exocortex/SESSION_CONTEXT_BACKUP_'
def protected_path(rel):
    return (
        (rel.startswith(legacy_backup_prefix) and rel.endswith('.md') and '/' not in rel[len(legacy_backup_prefix):])
        or any(rel == item or rel.startswith(item + '/') for item in protected)
    )
def runtime(rel):
    # Editor session worktrees are runtime state at any depth.
    parts = rel.split('/')
    return any(
        parts[index] == '.claude' and parts[index + 1] == 'worktrees'
        for index in range(len(parts) - 1)
    )
def inventory(root):
    result={}
    for rel in surface:
        base=root/rel
        if base.is_file():
            mode_bits=stat.S_IMODE(base.stat().st_mode)
            result[rel]=f'{mode_bits:04o}:'+hashlib.sha256(base.read_bytes()).hexdigest()
        elif base.is_dir():
            for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
                dirnames[:] = sorted(
                    d for d in dirnames
                    if not (Path(dirpath)/d).is_symlink()
                    and not runtime((Path(dirpath)/d).relative_to(root).as_posix())
                )
                for name in sorted(filenames):
                    path=Path(dirpath)/name
                    child=path.relative_to(root).as_posix()
                    if runtime(child) or protected_path(child):
                        continue
                    if path.is_symlink():
                        result[child]='symlink:'+os.readlink(path)
                    elif path.is_file():
                        mode_bits=stat.S_IMODE(path.stat().st_mode)
                        result[child]=f'{mode_bits:04o}:'+hashlib.sha256(path.read_bytes()).hexdigest()
    return result
a,b=inventory(left),inventory(right)
changed=sorted(key for key in set(a)|set(b) if a.get(key)!=b.get(key))
Path(output).write_text(''.join(value+'\n' for value in changed), encoding='utf-8')
PY

if [ -n "$RECONCILIATION_PLAN" ] && ! cmp -s "$CHANGES" "$PLANNED_EFFECTS"; then
    diff -u "$PLANNED_EFFECTS" "$CHANGES" >&2 || true
    fail "rehearsed effect does not match the exact reconciliation plan"
fi

echo "Backup: $BACKUP_PATH"
echo "Protected data check: PASS"
if [ "$TRACKED_PROTECTED_SIDECAR" = true ]; then
    echo "EXOCORTEX_TRACKED_PROTECTED_SIDECAR: .exocortex/SESSION_CONTEXT.md.backup is already tracked by Git; it is preserved, but ignore rules do not untrack it. Handle any Git cleanup separately; never automate it during an update."
fi
if [ "$TRACKED_LEGACY_SESSION_CONTEXT_BACKUP" = true ]; then
    echo "EXOCORTEX_TRACKED_LEGACY_SESSION_CONTEXT_BACKUP: one or more legacy protected session-context backup sidecars are already tracked by Git; they are preserved, but ignore rules do not untrack them. Handle any Git cleanup separately; never automate it during an update."
fi
if [ "$COMMAND_RECONCILIATION_REQUIRED" = true ]; then
    echo "EXOCORTEX_COMMAND_RECONCILIATION_REQUIRED: ordinary live apply is blocked; prepare and rehearse an exact target-specific reconciliation plan"
fi
echo "Rehearsal changed paths SHA-256: $(sha256_file "$CHANGES")"
echo "Rehearsal changed paths: $(wc -l < "$CHANGES" | tr -d ' ')"
cat "$CHANGES"

if [ "$APPLY" != true ]; then
    echo "Dry run complete. Real target unchanged."
    exit 0
fi

[ "$COMMAND_RECONCILIATION_REQUIRED" != true ] \
    || fail "ordinary live apply cannot preserve conflicting command authority or known stale command guidance"

[ -s "$CHANGES" ] || { echo "No update required."; exit 0; }

if [ "${EXOCORTEX_TEST_MODE:-0}" = "1" ] && [ -n "${EXOCORTEX_TEST_APPLY_BARRIER:-}" ]; then
    barrier="$EXOCORTEX_TEST_APPLY_BARRIER"
    case "$barrier" in /*) ;; *) fail "test apply barrier must be absolute" ;; esac
    barrier_parent="$(dirname "$barrier")"
    [ -d "$barrier_parent" ] || fail "test apply barrier parent must exist"
    barrier_parent_real="$(cd "$barrier_parent" && pwd -P)"
    case "$barrier_parent_real/" in "$PROJECT_ROOT/"*|"$TEMPLATE_ROOT/"*) fail "test apply barrier must be outside target and template" ;; esac
    : > "$barrier.ready"
    barrier_wait=0
    while [ ! -e "$barrier.continue" ] && [ "$barrier_wait" -lt 100 ]; do
        sleep 0.05
        barrier_wait=$((barrier_wait + 1))
    done
    [ -e "$barrier.continue" ] || fail "test apply barrier timed out"
fi

preflight_surface_paths
[ "$(inventory_digest "$PROJECT_ROOT" surface)" = "$BASE_SURFACE_DIGEST" ] || fail "live target changed after rehearsal; capability was not consumed"
[ "$(inventory_digest "$PROJECT_ROOT" protected)" = "$BASE_PROTECTED_DIGEST" ] || fail "protected target data changed after rehearsal; capability was not consumed"
if [ -n "$RECONCILIATION_PLAN" ]; then
    PYTHONDONTWRITEBYTECODE=1 python3 "$RECONCILIATION_HELPER" validate \
        --target "$PROJECT_ROOT" --template "$TEMPLATE_ROOT" \
        --candidate-digest "$CANDIDATE_DIGEST" --plan "$RECONCILIATION_PLAN" \
        --expected-work-item-id "$WORK_ITEM_ID" \
        --expected-work-item-revision "$WORK_ITEM_REVISION" \
        --emit plan-digest | grep -Fqx "$PLAN_DIGEST" \
        || fail "reconciliation plan or target changed before capability consumption"
fi

guard_args=(
    check --project-root "$PROJECT_ROOT" --capability "$CAPABILITY"
    --operation "$GUARD_OPERATION" --work-item-id "$WORK_ITEM_ID"
    --work-item-revision "$WORK_ITEM_REVISION" --request-id "$REQUEST_ID"
    --surface-id "$SURFACE_ID" --executor-id "$EXECUTOR_ID"
    --adapter-version "$ADAPTER_VERSION" --guard-digest "$GUARD_DIGEST"
    --role writer --target-sha "$CANDIDATE_DIGEST" --require-exact-path-set
)
if [ -n "$RECONCILIATION_PLAN" ]; then
    guard_args+=(--payload-digest "$PLAN_DIGEST")
fi
while IFS= read -r rel; do guard_args+=(--target-path "$rel"); done < "$CHANGES"
python3 "$GUARD" "${guard_args[@]}" >/dev/null
verify_backup_archive || fail "rollback archive changed before capability consumption"
preflight_surface_paths
[ "$(inventory_digest "$PROJECT_ROOT" surface)" = "$BASE_SURFACE_DIGEST" ] \
    || fail "live target changed immediately before capability consumption"
[ "$(inventory_digest "$PROJECT_ROOT" protected)" = "$BASE_PROTECTED_DIGEST" ] \
    || fail "protected target data changed immediately before capability consumption"
guard_args[0]=consume
python3 "$GUARD" "${guard_args[@]}" >/dev/null

POST_AUTH_PROTECTED_DIGEST="$(inventory_digest "$PROJECT_ROOT" protected)"

(cd "$PROJECT_ROOT" && HOME="$FAKE_HOME" EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_ROOT" EXOCORTEX_CANDIDATE_DIGEST="$CANDIDATE_DIGEST" bash "$TEMPLATE_ROOT/install.sh" "$(basename "$PROJECT_ROOT")")
materialize_reconciliation "$PROJECT_ROOT" \
    || fail "reconciliation failed after capability consumption; restore from the recorded archive with fresh authority"
if [ -n "$RECONCILIATION_PLAN" ]; then
    (cd "$PROJECT_ROOT" && HOME="$FAKE_HOME" EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_ROOT" \
        EXOCORTEX_CANDIDATE_DIGEST="$CANDIDATE_DIGEST" \
        bash "$TEMPLATE_ROOT/install.sh" "$(basename "$PROJECT_ROOT")")
fi

if [ "${EXOCORTEX_TEST_MODE:-0}" = "1" ] && [ -n "${EXOCORTEX_TEST_POST_APPLY_BARRIER:-}" ]; then
    post_barrier="$EXOCORTEX_TEST_POST_APPLY_BARRIER"
    case "$post_barrier" in /*) ;; *) fail "test post-apply barrier must be absolute" ;; esac
    post_barrier_parent="$(dirname "$post_barrier")"
    [ -d "$post_barrier_parent" ] || fail "test post-apply barrier parent must exist"
    post_barrier_parent_real="$(cd "$post_barrier_parent" && pwd -P)"
    case "$post_barrier_parent_real/" in "$PROJECT_ROOT/"*|"$TEMPLATE_ROOT/"*) fail "test post-apply barrier must be outside target and template" ;; esac
    : > "$post_barrier.ready"
    post_barrier_wait=0
    while [ ! -e "$post_barrier.continue" ] && [ "$post_barrier_wait" -lt 100 ]; do
        sleep 0.05
        post_barrier_wait=$((post_barrier_wait + 1))
    done
    [ -e "$post_barrier.continue" ] || fail "test post-apply barrier timed out"
fi

while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    # The apply may only have created the exact installer defaults the
    # rehearsal was allowed to create; anything else is protected-data drift.
    allowed_generated "$rel" "$PROJECT_ROOT/$rel" \
        || fail "installer-created protected default does not match its expected content: $rel"
done <<< "$ALLOWED_NEW_PROTECTED"
[ "$(inventory_digest "$PROJECT_ROOT" protected "$ALLOWED_NEW_PROTECTED")" = "$POST_AUTH_PROTECTED_DIGEST" ] || fail "protected target data changed during apply"
[ "$(inventory_digest "$PROJECT_ROOT" code_plane)" = "$REHEARSAL_CODE_PLANE_DIGEST" ] \
    || fail "applied code plane does not exactly match the disposable rehearsal"

python3 - "$PROJECT_ROOT" "$REHEARSAL" "$CHANGES" "$CAPABILITY" <<'PY'
import hashlib, stat, sys
from pathlib import Path

live, rehearsal, changes = map(Path, sys.argv[1:4])
for rel in Path(changes).read_text(encoding='utf-8').splitlines():
    a, b = live / rel, rehearsal / rel
    if a.is_symlink() or b.is_symlink():
        raise SystemExit(f'applied path type does not match rehearsal: {rel}')
    if a.is_file() and b.is_file():
        if hashlib.sha256(a.read_bytes()).digest() != hashlib.sha256(b.read_bytes()).digest():
            raise SystemExit(f'applied file does not match rehearsal: {rel}')
        if stat.S_IMODE(a.stat().st_mode) != stat.S_IMODE(b.stat().st_mode):
            raise SystemExit(f'applied file mode does not match rehearsal: {rel}')
    elif a.exists() or b.exists():
        raise SystemExit(f'applied path type or presence does not match rehearsal: {rel}')
PY

echo "Update applied under consumed capability: $REQUEST_ID"
echo "Rollback archive: $BACKUP_PATH"
echo "Capability state is excluded from rollback to prevent authority resurrection."
