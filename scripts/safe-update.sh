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

fail() { echo "ERROR: $*" >&2; exit 1; }

usage() {
    echo "Usage: safe-update.sh --template ABSOLUTE_PATH --candidate-digest SHA256 --backup-dir ABSOLUTE_PATH [--dry-run]" >&2
    echo "       safe-update.sh --template PATH --candidate-digest SHA256 --backup-dir PATH --apply --capability RELPATH --work-item-id ID --work-item-revision N --request-id ID --surface-id ID --executor-id ID --adapter-version VERSION" >&2
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

PROJECT_ROOT="$(pwd -P)"
TEMPLATE_ROOT="$(cd "$TEMPLATE_SOURCE" && pwd -P)"
[ -d "$PROJECT_ROOT/.exocortex" ] || fail "run from an existing Exocortex project"
[ "$PROJECT_ROOT" != "/" ] || fail "refusing filesystem root"
[ "$PROJECT_ROOT" != "${HOME:-/__no_home__}" ] || fail "refusing user home"
[ "$PROJECT_ROOT" != "$TEMPLATE_ROOT" ] || fail "template and target must differ"
case "$TEMPLATE_ROOT/" in "$PROJECT_ROOT/"*) fail "template must not be inside the target" ;; esac
case "$PROJECT_ROOT/" in "$TEMPLATE_ROOT/"*) fail "target must not be inside the template" ;; esac
[ -f "$TEMPLATE_ROOT/SHA256SUMS" ] || fail "template is missing SHA256SUMS"
ACTUAL_CANDIDATE_DIGEST="$(shasum -a 256 "$TEMPLATE_ROOT/SHA256SUMS" 2>/dev/null | awk '{print $1}')"
[ "$ACTUAL_CANDIDATE_DIGEST" = "$CANDIDATE_DIGEST" ] || fail "template does not match the separately approved candidate digest"

# Retired Windsurf paths remain update surfaces so rehearsals, authorization,
# backups, changed-path evidence, and rollback all cover their removal.
surface_paths=(.exocortex .agents .cursor .claude .github .windsurf AI_START_HERE.md AGENTS.md CLAUDE.md .windsurfrules .rules .gitignore)
protected_paths=(
    .exocortex/SESSION_CONTEXT.md
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

preflight_surface_paths() {
    local rel cursor link
    local -a parts
    for rel in "${surface_paths[@]}"; do
        cursor="$PROJECT_ROOT"
        IFS='/' read -r -a parts <<< "$rel"
        for part in "${parts[@]}"; do
            cursor="$cursor/$part"
            [ ! -L "$cursor" ] || fail "target update surface contains a symlink: $rel"
            [ -e "$cursor" ] || break
        done
        if [ -d "$PROJECT_ROOT/$rel" ]; then
            link="$(find "$PROJECT_ROOT/$rel" -type l -print -quit 2>/dev/null)" \
                || fail "target update surface could not be inspected safely: $rel"
            [ -z "$link" ] || fail "target update surface contains a symlink: ${link#"$PROJECT_ROOT/"}"
        fi
    done
}

# Reject target indirection before inventory, backup, or rehearsal can read it.
preflight_surface_paths

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

GUARD=""
GUARD_DIGEST=""
if [ "$APPLY" = true ]; then
    for value in "$CAPABILITY" "$WORK_ITEM_ID" "$WORK_ITEM_REVISION" "$REQUEST_ID" "$SURFACE_ID" "$EXECUTOR_ID" "$ADAPTER_VERSION"; do
        [ -n "$value" ] || fail "--apply requires complete guarded-executor identity and capability arguments"
    done
    GUARD="$TEMPLATE_ROOT/.exocortex/scripts/authority_guard.py"
    GUARD_DIGEST="$(python3 "$GUARD" guard-digest)"
    pre_guard_args=(
        check --project-root "$PROJECT_ROOT" --capability "$CAPABILITY"
        --operation apply_template_update --work-item-id "$WORK_ITEM_ID"
        --work-item-revision "$WORK_ITEM_REVISION" --request-id "$REQUEST_ID"
        --surface-id "$SURFACE_ID" --executor-id "$EXECUTOR_ID"
        --adapter-version "$ADAPTER_VERSION" --guard-digest "$GUARD_DIGEST"
        --role writer --target-sha "$CANDIDATE_DIGEST"
    )
    # Deny an invalid/revoked apply before backup creation or target rehearsal.
    python3 "$GUARD" "${pre_guard_args[@]}" >/dev/null
fi

inventory_digest() {
    local root="$1" mode="$2"
    python3 - "$root" "$mode" <<'PY'
import hashlib, os, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
mode = sys.argv[2]
surface = ['.exocortex','.agents','.cursor','.claude','.github','.windsurf','AI_START_HERE.md','AGENTS.md','CLAUDE.md','.windsurfrules','.rules','.gitignore']
protected = [
    '.exocortex/SESSION_CONTEXT.md','.exocortex/SESSION_CONTEXT.local.md',
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
selected = surface if mode == 'surface' else protected if mode == 'protected' else None
if selected is None:
    raise SystemExit('invalid inventory mode')
records = {}
for rel in selected:
    base = root / rel
    if base.is_symlink():
        records[rel] = 'symlink:' + os.readlink(base)
    elif base.is_file():
        records[rel] = 'file:' + hashlib.sha256(base.read_bytes()).hexdigest()
    elif base.is_dir():
        records[rel] = 'dir'
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames.sort()
            filenames.sort()
            here = Path(dirpath)
            for name in list(dirnames):
                path = here / name
                child = path.relative_to(root).as_posix()
                if path.is_symlink():
                    records[child] = 'symlink:' + os.readlink(path)
            dirnames[:] = [name for name in dirnames if not (here / name).is_symlink()]
            for name in filenames:
                path = here / name
                child = path.relative_to(root).as_posix()
                if path.is_symlink():
                    records[child] = 'symlink:' + os.readlink(path)
                elif path.is_file():
                    records[child] = 'file:' + hashlib.sha256(path.read_bytes()).hexdigest()
    else:
        records[rel] = 'absent'
digest = hashlib.sha256()
for rel, value in sorted(records.items()):
    digest.update(rel.encode('utf-8') + b'\0' + value.encode('utf-8') + b'\0')
print(digest.hexdigest())
PY
}

BASE_SURFACE_DIGEST="$(inventory_digest "$PROJECT_ROOT" surface)"
BASE_PROTECTED_DIGEST="$(inventory_digest "$PROJECT_ROOT" protected)"

mkdir -p "$BACKUP_NORMALIZED"
BACKUP_DIR="$(cd "$BACKUP_NORMALIZED" && pwd -P)"
[ "$BACKUP_DIR" != "/" ] || fail "refusing filesystem root as backup directory"
[ "$BACKUP_DIR" != "${HOME:-/__no_home__}" ] || fail "refusing user home as backup directory"
case "$BACKUP_DIR/" in "$PROJECT_ROOT/"*|"$TEMPLATE_ROOT/"*) fail "backup directory must be outside target and template" ;; esac

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/exocortex-safe-update.XXXXXX")"
REHEARSAL="$WORK_DIR/rehearsal"
FAKE_HOME="$WORK_DIR/fake-home"
CHANGES="$WORK_DIR/changed-paths.txt"
PROTECTED_DIFF="$WORK_DIR/protected-diff.txt"
trap 'rm -rf "$WORK_DIR"' EXIT
mkdir -p "$REHEARSAL" "$FAKE_HOME"

for rel in "${surface_paths[@]}"; do
    if [ -e "$PROJECT_ROOT/$rel" ]; then
        mkdir -p "$REHEARSAL/$(dirname "$rel")"
        cp -R "$PROJECT_ROOT/$rel" "$REHEARSAL/$(dirname "$rel")/"
    fi
done

BACKUP_PATH="$BACKUP_DIR/$(basename "$PROJECT_ROOT")-exocortex-before-update-$(date -u +%Y%m%d-%H%M%S).tar.gz"
backup_items=()
for rel in "${surface_paths[@]}"; do [ -e "$PROJECT_ROOT/$rel" ] && backup_items+=("$rel"); done
[ "${#backup_items[@]}" -gt 0 ] || fail "nothing to back up"
(cd "$PROJECT_ROOT" && tar --exclude='.exocortex/local/protocol/capabilities' --exclude='.exocortex/local/protocol/capabilities/*' -czf "$BACKUP_PATH" "${backup_items[@]}")

(cd "$REHEARSAL" && HOME="$FAKE_HOME" EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_ROOT" EXOCORTEX_CANDIDATE_DIGEST="$CANDIDATE_DIGEST" bash "$TEMPLATE_ROOT/install.sh" "$(basename "$PROJECT_ROOT")")

allowed_generated() {
    local rel="$1" path="$2"
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
for rel in "${protected_paths[@]}"; do
    left="$PROJECT_ROOT/$rel"
    right="$REHEARSAL/$rel"
    if [ -e "$left" ] && [ -e "$right" ]; then
        diff -rq "$left" "$right" >> "$PROTECTED_DIFF" 2>&1 || true
    elif [ -e "$left" ] || [ -e "$right" ]; then
        existing="$left"; [ -e "$existing" ] || existing="$right"
        if [ -d "$existing" ] && [ -z "$(find "$existing" -mindepth 1 -print -quit 2>/dev/null)" ]; then
            continue
        fi
        allowed_generated "$rel" "$existing" && continue
        echo "protected path exists on one side only: $rel" >> "$PROTECTED_DIFF"
    fi
done
[ ! -s "$PROTECTED_DIFF" ] || { sed -n '1,120p' "$PROTECTED_DIFF" >&2; fail "protected data changed in rehearsal"; }

python3 - "$PROJECT_ROOT" "$REHEARSAL" "$CHANGES" <<'PY'
import hashlib, os, sys
from pathlib import Path

left, right, output = map(Path, sys.argv[1:])
surface = ['.exocortex','.agents','.cursor','.claude','.github','.windsurf','AI_START_HERE.md','AGENTS.md','CLAUDE.md','.windsurfrules','.rules','.gitignore']
def inventory(root):
    result={}
    for rel in surface:
        base=root/rel
        if base.is_file():
            result[rel]=hashlib.sha256(base.read_bytes()).hexdigest()
        elif base.is_dir():
            for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
                dirnames[:] = sorted(d for d in dirnames if not (Path(dirpath)/d).is_symlink())
                for name in sorted(filenames):
                    path=Path(dirpath)/name
                    if path.is_symlink():
                        result[path.relative_to(root).as_posix()]='symlink:'+os.readlink(path)
                    elif path.is_file():
                        result[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result
a,b=inventory(left),inventory(right)
changed=sorted(key for key in set(a)|set(b) if a.get(key)!=b.get(key))
Path(output).write_text(''.join(value+'\n' for value in changed), encoding='utf-8')
PY

echo "Backup: $BACKUP_PATH"
echo "Protected data check: PASS"
echo "Rehearsal changed paths SHA-256: $(shasum -a 256 "$CHANGES" 2>/dev/null | awk '{print $1}')"
echo "Rehearsal changed paths: $(wc -l < "$CHANGES" | tr -d ' ')"
cat "$CHANGES"

if [ "$APPLY" != true ]; then
    echo "Dry run complete. Real target unchanged."
    exit 0
fi

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

[ "$(inventory_digest "$PROJECT_ROOT" surface)" = "$BASE_SURFACE_DIGEST" ] || fail "live target changed after rehearsal; capability was not consumed"
[ "$(inventory_digest "$PROJECT_ROOT" protected)" = "$BASE_PROTECTED_DIGEST" ] || fail "protected target data changed after rehearsal; capability was not consumed"

guard_args=(
    check --project-root "$PROJECT_ROOT" --capability "$CAPABILITY"
    --operation apply_template_update --work-item-id "$WORK_ITEM_ID"
    --work-item-revision "$WORK_ITEM_REVISION" --request-id "$REQUEST_ID"
    --surface-id "$SURFACE_ID" --executor-id "$EXECUTOR_ID"
    --adapter-version "$ADAPTER_VERSION" --guard-digest "$GUARD_DIGEST"
    --role writer --target-sha "$CANDIDATE_DIGEST" --require-exact-path-set
)
while IFS= read -r rel; do guard_args+=(--target-path "$rel"); done < "$CHANGES"
python3 "$GUARD" "${guard_args[@]}" >/dev/null
guard_args[0]=consume
python3 "$GUARD" "${guard_args[@]}" >/dev/null

POST_AUTH_PROTECTED_DIGEST="$(inventory_digest "$PROJECT_ROOT" protected)"

(cd "$PROJECT_ROOT" && HOME="$FAKE_HOME" EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_ROOT" EXOCORTEX_CANDIDATE_DIGEST="$CANDIDATE_DIGEST" bash "$TEMPLATE_ROOT/install.sh" "$(basename "$PROJECT_ROOT")")

[ "$(inventory_digest "$PROJECT_ROOT" protected)" = "$POST_AUTH_PROTECTED_DIGEST" ] || fail "protected target data changed during apply"

python3 - "$PROJECT_ROOT" "$REHEARSAL" "$CHANGES" "$CAPABILITY" <<'PY'
import hashlib, sys
from pathlib import Path

live, rehearsal, changes = map(Path, sys.argv[1:4])
for rel in Path(changes).read_text(encoding='utf-8').splitlines():
    a, b = live / rel, rehearsal / rel
    if a.is_file() and b.is_file():
        if hashlib.sha256(a.read_bytes()).digest() != hashlib.sha256(b.read_bytes()).digest():
            raise SystemExit(f'applied file does not match rehearsal: {rel}')
    elif a.exists() != b.exists():
        raise SystemExit(f'applied path presence does not match rehearsal: {rel}')
PY

echo "Update applied under consumed capability: $REQUEST_ID"
echo "Rollback archive: $BACKUP_PATH"
echo "Capability state is excluded from rollback to prevent authority resurrection."
