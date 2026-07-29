#!/bin/bash
set -u
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=helpers.sh
source "$TEST_DIR/helpers.sh"

tree_digest() {
    python3 - "$1" <<'PY'
import hashlib, os, stat, sys
from pathlib import Path
root=Path(sys.argv[1])
h=hashlib.sha256()
for base, dirs, files in os.walk(root):
    dirs[:]=sorted(d for d in dirs if d != '.git')
    for name in sorted(files):
        p=Path(base)/name
        rel=p.relative_to(root).as_posix()
        mode=stat.S_IMODE(p.stat().st_mode)
        h.update(rel.encode()+b'\0'+str(mode).encode()+b'\0'+hashlib.sha256(p.read_bytes()).digest())
print(h.hexdigest())
PY
}

code_plane_digest() {
    python3 - "$1" <<'PY'
import hashlib, os, stat, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
surface = (
    '.exocortex', '.agents', '.cursor', '.claude', '.github', '.windsurf',
    'AI_START_HERE.md', 'AGENTS.md', 'CLAUDE.md', '.windsurfrules', '.rules', '.gitignore',
)
protected = (
    '.exocortex/SESSION_CONTEXT.md', '.exocortex/SESSION_CONTEXT.local.md',
    '.exocortex/TODO.md', '.exocortex/LESSONS.md', '.exocortex/PROJECT_MEMORY.md',
    '.exocortex/OPEN_DECISIONS.md', '.exocortex/subconscious_patterns.md',
    '.exocortex/.env', '.exocortex/.project-name', '.exocortex/events',
    '.exocortex/archive', '.exocortex/hub', '.exocortex/local', '.exocortex/planning',
    '.exocortex/work-items', '.exocortex/control/ACTIVE_WORK.md',
    '.exocortex/control/BRANCH_POLICY.md', '.exocortex/control/REPO_STATE.md',
    '.exocortex/control/EXECUTOR_REGISTRY.json',
    '.exocortex/control/EXTERNAL_SYNC_POLICY.json',
    '.exocortex/control/INTERRUPTS.md', '.exocortex/control/BACKLOG.md',
    '.exocortex/control/ROADMAP.md', '.exocortex/control/ARCH_OVERVIEW.md',
    '.exocortex/control/REPO_ORGANIZATION_REPORT.md',
    '.exocortex/.hub_enabled', '.exocortex/.hub_disabled',
)
def excluded(relative):
    return any(relative == item or relative.startswith(item + '/') for item in protected)
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
for relative in surface:
    if excluded(relative):
        continue
    base = root / relative
    if base.is_symlink():
        records[relative] = symlink_record(base)
    elif base.is_file():
        records[relative] = file_record(base)
    elif base.is_dir():
        records[relative] = directory_record(base, relative)
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            here = Path(dirpath)
            dirnames[:] = sorted(
                name for name in dirnames
                if not excluded((here / name).relative_to(root).as_posix())
            )
            for name in list(dirnames):
                path = here / name
                child = path.relative_to(root).as_posix()
                if path.is_symlink():
                    records[child] = symlink_record(path)
                else:
                    records[child] = directory_record(path, child)
            dirnames[:] = [name for name in dirnames if not (here / name).is_symlink()]
            for name in sorted(filenames):
                path = here / name
                child = path.relative_to(root).as_posix()
                if excluded(child):
                    continue
                if path.is_symlink():
                    records[child] = symlink_record(path)
                elif path.is_file():
                    records[child] = file_record(path)
    else:
        records[relative] = 'absent'
digest = hashlib.sha256()
for relative, value in sorted(records.items()):
    digest.update(relative.encode() + b'\0' + value.encode() + b'\0')
print(digest.hexdigest())
PY
}

protected_plane_digest() {
    python3 - "$1" <<'PY'
import hashlib, os, stat, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
protected = (
    '.exocortex/SESSION_CONTEXT.md', '.exocortex/SESSION_CONTEXT.local.md',
    '.exocortex/TODO.md', '.exocortex/LESSONS.md', '.exocortex/PROJECT_MEMORY.md',
    '.exocortex/OPEN_DECISIONS.md', '.exocortex/subconscious_patterns.md',
    '.exocortex/.env', '.exocortex/.project-name', '.exocortex/events',
    '.exocortex/archive', '.exocortex/hub', '.exocortex/local', '.exocortex/planning',
    '.exocortex/work-items', '.exocortex/control/ACTIVE_WORK.md',
    '.exocortex/control/BRANCH_POLICY.md', '.exocortex/control/REPO_STATE.md',
    '.exocortex/control/EXECUTOR_REGISTRY.json',
    '.exocortex/control/EXTERNAL_SYNC_POLICY.json',
    '.exocortex/control/INTERRUPTS.md', '.exocortex/control/BACKLOG.md',
    '.exocortex/control/ROADMAP.md', '.exocortex/control/ARCH_OVERVIEW.md',
    '.exocortex/control/REPO_ORGANIZATION_REPORT.md',
    '.exocortex/.hub_enabled', '.exocortex/.hub_disabled',
)
def record(path):
    value = os.lstat(path)
    if stat.S_ISLNK(value.st_mode):
        return f'symlink:{stat.S_IMODE(value.st_mode):04o}:{value.st_nlink}:' + os.readlink(path)
    if stat.S_ISREG(value.st_mode):
        return (
            f'file:{stat.S_IMODE(value.st_mode):04o}:{value.st_nlink}:'
            + hashlib.sha256(path.read_bytes()).hexdigest()
        )
    if stat.S_ISDIR(value.st_mode):
        return f'dir:{stat.S_IMODE(value.st_mode):04o}'
    return f'other:{stat.S_IFMT(value.st_mode):o}:{stat.S_IMODE(value.st_mode):04o}:{value.st_nlink}'
records = {}
for relative in protected:
    base = root / relative
    try:
        os.lstat(base)
    except FileNotFoundError:
        records[relative] = 'absent'
        continue
    records[relative] = record(base)
    if not base.is_dir() or base.is_symlink():
        continue
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        here = Path(dirpath)
        dirnames.sort()
        filenames.sort()
        for name in list(dirnames):
            path = here / name
            child = path.relative_to(root).as_posix()
            records[child] = record(path)
        dirnames[:] = [
            name for name in dirnames
            if not (here / name).is_symlink()
        ]
        for name in filenames:
            path = here / name
            child = path.relative_to(root).as_posix()
            records[child] = record(path)
digest = hashlib.sha256()
for relative, value in sorted(records.items()):
    digest.update(relative.encode() + b'\0' + value.encode() + b'\0')
print(digest.hexdigest())
PY
}

privacy_scan() {
    local root="$1" mode="$2" fingerprint_file="$3"
    PYTHONDONTWRITEBYTECODE=1 python3 - "$root" "$mode" "$fingerprint_file" <<'PY'
import re, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
mode = sys.argv[2]
fingerprint_path = Path(sys.argv[3]).resolve(strict=True)
try:
    fingerprint_path.relative_to(root)
except ValueError:
    pass
else:
    raise SystemExit(2)
fingerprint = fingerprint_path.read_bytes().strip()
if not fingerprint:
    raise SystemExit(2)
private_tokens = [
    b'/' + b'Us' + b'ers/',
    b'guy' + b'robo',
    b'M' + b'UL-',
    b'EXO-' + b'PHASE-B',
]

def unsafe(data: bytes) -> bool:
    return fingerprint in data or any(token in data for token in private_tokens)

paths = []
if mode == 'checksums':
    sums = root / 'SHA256SUMS'
    if not sums.is_file():
        raise SystemExit(2)
    seen = set()
    for line in sums.read_text(encoding='utf-8').splitlines():
        if not re.fullmatch(r'[0-9a-f]{64}  [^/].*', line):
            raise SystemExit(2)
        rel = line[66:]
        if rel in seen:
            raise SystemExit(2)
        seen.add(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise SystemExit(2)
        try:
            path.resolve(strict=True).relative_to(root)
        except ValueError:
            raise SystemExit(2)
        paths.append(path)
elif mode == 'tree':
    for path in root.rglob('*'):
        if not path.is_file() or path.is_symlink() or '.git' in path.parts:
            continue
        if any(part == '.env' for part in path.relative_to(root).parts):
            continue
        paths.append(path)
else:
    raise SystemExit(2)

for path in paths:
    data = path.read_bytes()
    if unsafe(data):
        raise SystemExit(1)
raise SystemExit(0)
PY
}

expect_install_denial() {
    local label="$1" source="$2"
    local target fake
    local -a run_install_args
    target="$(new_target)"
    fake="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
    if [ "$#" -ge 3 ]; then
        run_install_args=("$target" "$source" "$fake" "$3")
    else
        run_install_args=("$target" "$source" "$fake")
    fi
    if run_install "${run_install_args[@]}" >/dev/null 2>&1; then
        bad "$label"
    elif [ -e "$target/.exocortex" ]; then
        bad "$label wrote target before denial"
    else
        ok "$label"
    fi
    rm -rf "$target" "$fake"
}

echo "Exocortex deterministic installer/update suite"

privacy_fingerprint="${EXOCORTEX_PRIVATE_FINGERPRINT_FILE:-}"
privacy_fingerprint_owned=false
if [ -z "$privacy_fingerprint" ]; then
    privacy_fingerprint="$(mktemp "${TMPDIR:-/tmp}/exo-private-fingerprint.XXXXXX")"
    privacy_fingerprint_owned=true
    prior_umask="$(umask)"
    umask 077
    printf 'private-fixture-%s-%s\n' "$$" "$(date -u +%s)" > "$privacy_fingerprint"
    umask "$prior_umask"
fi
[ -s "$privacy_fingerprint" ] || { echo "private fingerprint input is required" >&2; exit 2; }

if privacy_scan "$TEMPLATE_DIR" checksums "$privacy_fingerprint"; then
    ok "candidate checksum inventory contains no private fingerprint"
else
    bad "candidate checksum inventory contains no private fingerprint"
fi

if PYTHONDONTWRITEBYTECODE=1 python3 "$TEMPLATE_DIR/.exocortex/scripts/generate_command_adapters.py" --check >/dev/null; then
    ok "canonical 24-command registry generates exactly 72 current adapters"
else
    bad "canonical 24-command registry generates exactly 72 current adapters"
fi

expect_install_denial "missing candidate digest fails before target mutation" "$TEMPLATE_DIR" ""
expect_install_denial "malformed candidate digest fails before target mutation" "$TEMPLATE_DIR" "not-a-digest"

source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
approved_before="$(hash_file "$TEMPLATE_DIR/SHA256SUMS")"
printf '\nchanged candidate\n' >> "$source_copy/AI_START_HERE.md"
changed_hash="$(hash_file "$source_copy/AI_START_HERE.md")"
awk -v h="$changed_hash" 'BEGIN{OFS="  "} $2=="AI_START_HERE.md"{$1=h} {print $1,$2}' "$source_copy/SHA256SUMS" > "$source_copy/SHA256SUMS.tmp"
mv "$source_copy/SHA256SUMS.tmp" "$source_copy/SHA256SUMS"
expect_install_denial "altered source with self-consistent sums fails approved candidate digest" "$source_copy" "$approved_before"
rm -rf "$source_copy"

source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
python3 - "$source_copy/.exocortex/model-routing-catalog.json" <<'PY'
import json, sys
from pathlib import Path
path=Path(sys.argv[1])
value=json.loads(path.read_text(encoding='utf-8'))
value['source_registry_digest']='0'*64
path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY
changed_hash="$(hash_file "$source_copy/.exocortex/model-routing-catalog.json")"
awk -v h="$changed_hash" 'BEGIN{OFS="  "} $2==".exocortex/model-routing-catalog.json"{$1=h} {print $1,$2}' "$source_copy/SHA256SUMS" > "$source_copy/SHA256SUMS.tmp"
mv "$source_copy/SHA256SUMS.tmp" "$source_copy/SHA256SUMS"
expect_install_denial \
    "digest-mismatched model catalog fails before target mutation" \
    "$source_copy" \
    "$(hash_file "$source_copy/SHA256SUMS")"
rm -rf "$source_copy"

for symlink_case in exocortex cursor-hooks final-file; do
    target="$(new_target)"
    fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
    outside="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-outside.XXXXXX")"
    printf 'outside canary\n' > "$outside/canary.txt"
    outside_before="$(tree_digest "$outside")"
    case "$symlink_case" in
        exocortex) ln -s "$outside" "$target/.exocortex" ;;
        cursor-hooks) mkdir -p "$target/.cursor"; ln -s "$outside" "$target/.cursor/hooks" ;;
        final-file) ln -s "$outside/canary.txt" "$target/AI_START_HERE.md" ;;
    esac
    if run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null 2>&1; then
        bad "installer denies $symlink_case symlink escape"
    elif [ "$(tree_digest "$outside")" != "$outside_before" ]; then
        bad "installer preserves outside tree for $symlink_case symlink escape"
    elif [ "$symlink_case" != "exocortex" ] && [ -e "$target/.exocortex" ]; then
        bad "installer preflights $symlink_case before target mutation"
    else
        ok "installer denies $symlink_case symlink escape before mutation"
    fi
    rm -rf "$target" "$fake_home" "$outside"
done

fault_target="$(new_target)"
fault_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
fault_outside="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-outside.XXXXXX")"
printf 'INSTALL_FAULT_OUTSIDE_CANARY\n' > "$fault_outside/canary.txt"
fault_outside_before="$(tree_digest "$fault_outside")"
if (cd "$fault_target" && \
    HOME="$fault_home" \
    EXOCORTEX_TEST_MODE=1 \
    EXOCORTEX_TEST_INSTALL_FAULT_AFTER_COPIES=3 \
    EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_DIR" \
    EXOCORTEX_CANDIDATE_DIGEST="$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    bash "$TEMPLATE_DIR/install.sh" test-project) >/dev/null 2>&1; then
    bad "fresh-install test fault fails after a bounded partial copy"
elif [ -z "$(find "$fault_target/.exocortex" -type f -print -quit 2>/dev/null)" ] \
    || [ -e "$fault_target/AI_START_HERE.md" ] \
    || [ -n "$(find "$fault_home" -mindepth 1 -print -quit)" ] \
    || [ "$(tree_digest "$fault_outside")" != "$fault_outside_before" ]; then
    bad "fresh-install test fault contains partial changes inside the disposable fixture"
else
    quarantined_target="${fault_target}.quarantined"
    mv "$fault_target" "$quarantined_target"
    clean_recreated_target="$(new_target)"
    if run_install "$clean_recreated_target" "$TEMPLATE_DIR" "$fault_home" >/dev/null \
        && [ -f "$clean_recreated_target/AI_START_HERE.md" ] \
        && [ -f "$clean_recreated_target/.exocortex/.install-manifest" ]; then
        ok "fresh-install test fault is quarantined and a clean baseline installs successfully"
    else
        bad "fresh-install test fault is quarantined and a clean baseline installs successfully"
    fi
    rm -rf "$quarantined_target" "$clean_recreated_target"
fi
rm -rf "$fault_target" "$fault_home" "$fault_outside"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
install_umask_before="$(umask)"
umask 077
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
umask "$install_umask_before"
assert_file "canonical entry installed" "$target/AI_START_HERE.md"
assert_file "Codex adapter installed" "$target/AGENTS.md"
assert_file "executor registry generated" "$target/.exocortex/control/EXECUTOR_REGISTRY.json"
assert_file "deny policy generated" "$target/.exocortex/control/EXTERNAL_SYNC_POLICY.json"
assert_dir "protocol state generated" "$target/.exocortex/local/protocol"
assert_contains "registry defaults read-only" "$target/.exocortex/control/EXECUTOR_REGISTRY.json" '"default_role": "read_only"'
assert_contains "policy defaults deny" "$target/.exocortex/control/EXTERNAL_SYNC_POLICY.json" '"default": "deny"'
assert_not_contains "registry absent from manifest" "$target/.exocortex/.install-manifest" 'EXECUTOR_REGISTRY.json'
assert_not_contains "policy absent from manifest" "$target/.exocortex/.install-manifest" 'EXTERNAL_SYNC_POLICY.json'
assert_file "official model source registry installed" "$target/.exocortex/model-source-registry.json"
assert_file "advisory model routing catalog installed" "$target/.exocortex/model-routing-catalog.json"
if [ "$(find "$target/.agents/skills" -type f -name SKILL.md | wc -l | tr -d ' ')" = "24" ] \
    && [ "$(find "$target/.claude/skills" -type f -name SKILL.md | wc -l | tr -d ' ')" = "24" ] \
    && [ "$(find "$target/.cursor/skills" -type f -name SKILL.md -exec grep -lF 'GENERATED BY .exocortex/scripts/generate_command_adapters.py' {} + | wc -l | tr -d ' ')" = "24" ] \
    && PYTHONDONTWRITEBYTECODE=1 python3 "$target/.exocortex/scripts/generate_command_adapters.py" --check >/dev/null; then
    ok "fresh install contains exact validated provider-adapter parity"
else
    bad "fresh install contains exact validated provider-adapter parity"
fi
if [ ! -e "$target/.cursor/commands/save.md" ] \
    && [ -f "$target/.cursor/skills/onboard/SKILL.md" ] \
    && [ ! -e "$target/.github/skills/onboard/SKILL.md" ] \
    && [ ! -e "$target/.windsurfrules" ] \
    && [ ! -e "$target/.windsurf" ]; then
    ok "fresh install has dedicated Cursor commands and no retired Windsurf surface"
else
    bad "fresh install has dedicated Cursor commands and no retired Windsurf surface"
fi
[ -z "$(find "$fake_home" -mindepth 1 -print -quit)" ] && ok "fake HOME untouched" || bad "fake HOME untouched"

mkdir -p "$target/.exocortex/local/model-routing"
printf 'FICTIONAL_LOCAL_AVAILABILITY\n' > "$target/.exocortex/local/model-routing/canary.txt"
local_model_routing_before="$(hash_file "$target/.exocortex/local/model-routing/canary.txt")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
if [ "$(hash_file "$target/.exocortex/local/model-routing/canary.txt")" = "$local_model_routing_before" ] \
    && ! grep -Fq '.exocortex/local/model-routing' "$target/.exocortex/.install-manifest"; then
    ok "installer preserves and never manifests local model-routing evidence"
else
    bad "installer preserves and never manifests local model-routing evidence"
fi
if python3 - "$TEMPLATE_DIR" "$target" <<'PY'
import stat
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
for relative_root, suffixes in (
    (Path(".exocortex/scripts"), {".sh", ".py"}),
    (Path(".cursor/hooks"), {".sh"}),
):
    for source_path in (source / relative_root).rglob("*"):
        if not source_path.is_file() or source_path.suffix not in suffixes:
            continue
        relative = source_path.relative_to(source)
        target_path = target / relative
        if not target_path.is_file():
            raise SystemExit(f"missing installed mode fixture: {relative}")
        source_mode = stat.S_IMODE(source_path.stat().st_mode)
        target_mode = stat.S_IMODE(target_path.stat().st_mode)
        if source_mode != target_mode:
            raise SystemExit(f"installed mode drift: {relative}")
PY
then
    ok "installer preserves reviewed helper executable modes"
else
    bad "installer preserves reviewed helper executable modes"
fi

tar_target="$(new_target)"
tar_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
tar_umask_before="$(umask)"
umask 077
(cd "$tar_target" && \
    HOME="$tar_home" \
    EXOCORTEX_FORCE_TAR_STAGE=1 \
    EXOCORTEX_LOCAL_SOURCE="$TEMPLATE_DIR" \
    EXOCORTEX_CANDIDATE_DIGEST="$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    bash "$TEMPLATE_DIR/install.sh" test-project >/dev/null)
umask "$tar_umask_before"
if python3 - "$TEMPLATE_DIR" "$tar_target" <<'PY'
import stat
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
for relative_root, suffixes in (
    (Path(".exocortex/scripts"), {".sh", ".py"}),
    (Path(".cursor/hooks"), {".sh"}),
):
    for source_path in (source / relative_root).rglob("*"):
        if not source_path.is_file() or source_path.suffix not in suffixes:
            continue
        target_path = target / source_path.relative_to(source)
        if not target_path.is_file():
            raise SystemExit(1)
        if stat.S_IMODE(source_path.stat().st_mode) != stat.S_IMODE(target_path.stat().st_mode):
            raise SystemExit(1)
PY
then
    ok "tar staging preserves checksum-bound modes under restrictive umask"
else
    bad "tar staging preserves checksum-bound modes under restrictive umask"
fi
rm -rf "$tar_target" "$tar_home"

chmod 700 "$target/.exocortex/scripts/archive_events.sh"
first="$(tree_digest "$target")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
second="$(tree_digest "$target")"
[ "$first" = "$second" ] \
    && ok "install is idempotent, including a byte-identical local mode override" \
    || bad "install is idempotent, including a byte-identical local mode override"
initializer_before="$(tree_digest "$target")"
(cd "$target" && bash "$TEMPLATE_DIR/init-project.sh" test-project >/dev/null)
initializer_after="$(tree_digest "$target")"
[ "$initializer_before" = "$initializer_after" ] \
    && ok "standalone initializer preserves every existing byte and file mode" \
    || bad "standalone initializer preserves every existing byte and file mode"
rm -rf "$target" "$fake_home"

initializer_target="$(new_target)"
initializer_outside="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-init-outside.XXXXXX")"
rm -rf "$initializer_target/.exocortex"
ln -s "$initializer_outside" "$initializer_target/.exocortex"
if (cd "$initializer_target" && bash "$TEMPLATE_DIR/init-project.sh" test-project) >/dev/null 2>&1 \
    || [ -e "$initializer_outside/.project-name" ]; then
    bad "standalone initializer rejects a symlinked .exocortex directory"
else
    ok "standalone initializer rejects a symlinked .exocortex directory"
fi
rm -f "$initializer_target/.exocortex"
mkdir -p "$initializer_target/.exocortex"
ln -s "$initializer_outside/dangling-project-name" "$initializer_target/.exocortex/.project-name"
if (cd "$initializer_target" && bash "$TEMPLATE_DIR/init-project.sh" test-project) >/dev/null 2>&1 \
    || [ -e "$initializer_outside/dangling-project-name" ]; then
    bad "standalone initializer rejects a dangling .project-name symlink"
else
    ok "standalone initializer rejects a dangling .project-name symlink"
fi
rm -rf "$initializer_target" "$initializer_outside"

initializer_target="$(new_target)"
mkdir -p "$initializer_target/.exocortex"
initializer_prior_umask="$(umask)"
umask 077
(cd "$initializer_target" && bash "$TEMPLATE_DIR/init-project.sh" test-project >/dev/null)
umask "$initializer_prior_umask"
initializer_first="$(tree_digest "$initializer_target")"
if [ "$(python3 -c 'import os,stat,sys; print(format(stat.S_IMODE(os.lstat(sys.argv[1]).st_mode), "04o"))' "$initializer_target/.exocortex/.project-name")" = "0644" ] \
    && grep -Fxq 'test-project' "$initializer_target/.exocortex/.project-name" \
    && (cd "$initializer_target" && bash "$TEMPLATE_DIR/init-project.sh" test-project >/dev/null) \
    && [ "$(tree_digest "$initializer_target")" = "$initializer_first" ]; then
    ok "standalone initializer creates a durable 0644 project name under restrictive umask"
else
    bad "standalone initializer creates a durable 0644 project name under restrictive umask"
fi
rm -rf "$initializer_target"

initializer_target="$(new_target)"
mkdir -p "$initializer_target/.exocortex"
if (cd "$initializer_target" && EXOCORTEX_TEST_INIT_FAULT=write \
    bash "$TEMPLATE_DIR/init-project.sh" test-project) >/dev/null 2>&1 \
    || [ -e "$initializer_target/.exocortex/.project-name" ] \
    || [ -n "$(find "$initializer_target/.exocortex" -name '.project-name.tmp.*' -print -quit)" ]; then
    bad "standalone initializer rejects fault injection outside explicit test mode"
else
    ok "standalone initializer rejects fault injection outside explicit test mode"
fi
for initializer_fault in write file-fsync directory-fsync; do
    initializer_fault_log="$initializer_target/$initializer_fault.log"
    if (cd "$initializer_target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_INIT_FAULT="$initializer_fault" \
        bash "$TEMPLATE_DIR/init-project.sh" test-project) > "$initializer_fault_log" 2>&1 \
        || ! grep -Fq "injected test-only project-name $initializer_fault failure" "$initializer_fault_log" \
        || [ -e "$initializer_target/.exocortex/.project-name" ] \
        || [ -n "$(find "$initializer_target/.exocortex" -name '.project-name.tmp.*' -print -quit)" ]; then
        bad "standalone initializer cleans up a $initializer_fault publication fault"
    else
        ok "standalone initializer cleans up a $initializer_fault publication fault"
    fi
done
rm -rf "$initializer_target"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
outside_hardlink="$(mktemp "${TMPDIR:-/tmp}/exo-test-hardlink.XXXXXX")"
mkdir -p "$target/.exocortex"
printf 'EXTERNAL_HARDLINK_CANARY\n' > "$outside_hardlink"
chmod 0600 "$outside_hardlink"
ln "$outside_hardlink" "$target/.exocortex/COMMAND_SYSTEM.md"
hardlink_hash_before="$(hash_file "$outside_hardlink")"
if run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null 2>&1 \
    || [ "$(hash_file "$outside_hardlink")" != "$hardlink_hash_before" ] \
    || [ "$(python3 -c 'import os,stat,sys; print(format(stat.S_IMODE(os.stat(sys.argv[1]).st_mode), "04o"))' "$outside_hardlink")" != "0600" ]; then
    bad "installer rejects an external hard-linked target before mutation"
else
    ok "installer rejects an external hard-linked target before mutation"
fi
rm -rf "$target" "$fake_home"
rm -f "$outside_hardlink"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
mkdir -p "$target/.exocortex"
pre_c1_meta="$(mktemp "${TMPDIR:-/tmp}/exo-test-pre-c1-meta.XXXXXX")"
python3 - "$target" "$TEMPLATE_DIR/.exocortex/provider-adapters.json" "$pre_c1_meta" <<'PY'
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1])
matrix = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
meta = Path(sys.argv[3])
custom = '.cursor/commands/work.md'
mode_custom = '.cursor/commands/check-keys.md'
unknown = '.cursor/skills/onboard/SKILL.md'
records = {}
managed = []
for index, item in enumerate(matrix['legacy_retirements']):
    rel = item['path']
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'pre-c1 adapter {index:02d}\n', encoding='utf-8')
    path.chmod(0o644)
    if rel == unknown:
        path.write_text('unknown pre-c1 onboard adapter\n', encoding='utf-8')
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    records[rel] = digest
    if rel == custom:
        path.write_text(path.read_text(encoding='utf-8') + 'user customization\n', encoding='utf-8')
    elif rel == mode_custom:
        path.chmod(0o755)
    else:
        managed.append(rel)
manifest = root / '.exocortex/.install-manifest'
manifest.write_text(
    '# Exocortex install manifest - template code plane only\n'
    + ''.join(f'{rel} {digest}\n' for rel, digest in sorted(records.items())),
    encoding='utf-8',
)
meta.write_text(json.dumps({
    'managed': managed,
    'custom': custom,
    'custom_baseline': records[custom],
    'mode_custom': mode_custom,
    'mode_custom_baseline': records[mode_custom],
    'unknown': unknown,
}) + '\n', encoding='utf-8')
PY
pre_c1_log="$(mktemp "${TMPDIR:-/tmp}/exo-test-pre-c1-migration.XXXXXX")"
if run_install "$target" "$TEMPLATE_DIR" "$fake_home" > "$pre_c1_log" 2>&1 \
    && grep -Fq 'EXOCORTEX_ADAPTER_COLLISION_PRESERVED: .cursor/commands/work.md' "$pre_c1_log" \
    && grep -Fq 'EXOCORTEX_ADAPTER_COLLISION_PRESERVED: .cursor/commands/check-keys.md' "$pre_c1_log" \
    && grep -Fq 'EXOCORTEX_ADAPTER_COLLISION_PRESERVED: .cursor/skills/onboard/SKILL.md' "$pre_c1_log" \
    && python3 - "$target" "$pre_c1_meta" <<'PY'
import json, stat, sys
from pathlib import Path
root = Path(sys.argv[1])
meta = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
if any((root / rel).exists() for rel in meta['managed']):
    raise SystemExit(1)
if 'user customization' not in (root / meta['custom']).read_text(encoding='utf-8'):
    raise SystemExit(1)
if (
    not (root / meta['mode_custom']).is_file()
    or stat.S_IMODE((root / meta['mode_custom']).stat().st_mode) != 0o755
):
    raise SystemExit(1)
if 'unknown pre-c1 onboard adapter' not in (root / meta['unknown']).read_text(encoding='utf-8'):
    raise SystemExit(1)
lines = [
    line for line in (root / '.exocortex/.install-manifest').read_text(encoding='utf-8').splitlines()
    if line and not line.startswith('#')
]
keys = [line.rsplit(' ', 1)[0] for line in lines]
if len(keys) != len(set(keys)):
    raise SystemExit(1)
if f"{meta['custom']} {meta['custom_baseline']}" not in lines:
    raise SystemExit(1)
if f"{meta['mode_custom']} {meta['mode_custom_baseline']}" not in lines:
    raise SystemExit(1)
PY
then
    pre_c1_first="$(tree_digest "$target")"
    run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
    pre_c1_second="$(tree_digest "$target")"
    if [ "$pre_c1_first" = "$pre_c1_second" ]; then
        ok "direct pre-C1 update retires managed paths and preserves byte, mode, and unknown collisions idempotently"
    else
        bad "direct pre-C1 update retires managed paths and preserves byte, mode, and unknown collisions idempotently"
    fi
else
    bad "direct pre-C1 update retires managed paths and preserves byte, mode, and unknown collisions idempotently"
fi
rm -rf "$target" "$fake_home"
rm -f "$pre_c1_meta" "$pre_c1_log"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
c1_meta="$(mktemp "${TMPDIR:-/tmp}/exo-test-c1-meta.XXXXXX")"
python3 - "$target" "$TEMPLATE_DIR/.exocortex/provider-adapters.json" "$c1_meta" <<'PY'
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1])
matrix = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
meta = Path(sys.argv[3])
custom = '.windsurf/workflows/work.md'
unknown = '.windsurfrules'
manifest = root / '.exocortex/.install-manifest'
records = {}
for line in manifest.read_text(encoding='utf-8').splitlines():
    if line and not line.startswith('#'):
        rel, digest = line.rsplit(' ', 1)
        records[rel] = digest
managed = []
for index, rel in enumerate(matrix['windsurf_retirements']):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'c1 windsurf adapter {index:02d}\n', encoding='utf-8')
    path.chmod(0o644)
    if rel == unknown:
        path.write_text('unknown c1 windsurf rules\n', encoding='utf-8')
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    records[rel] = digest
    if rel == custom:
        path.write_text(path.read_text(encoding='utf-8') + 'user customization\n', encoding='utf-8')
    else:
        managed.append(rel)
manifest.write_text(
    '# Exocortex install manifest - template code plane only\n'
    + ''.join(f'{rel} {digest}\n' for rel, digest in sorted(records.items())),
    encoding='utf-8',
)
meta.write_text(json.dumps({
    'managed': managed,
    'custom': custom,
    'custom_baseline': records[custom],
    'unknown': unknown,
}) + '\n', encoding='utf-8')
PY
c1_log="$(mktemp "${TMPDIR:-/tmp}/exo-test-c1-migration.XXXXXX")"
if run_install "$target" "$TEMPLATE_DIR" "$fake_home" > "$c1_log" 2>&1 \
    && grep -Fq 'EXOCORTEX_ADAPTER_COLLISION_PRESERVED: .windsurf/workflows/work.md' "$c1_log" \
    && grep -Fq 'EXOCORTEX_ADAPTER_COLLISION_PRESERVED: .windsurfrules' "$c1_log" \
    && python3 - "$target" "$c1_meta" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
meta = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
if any((root / rel).exists() for rel in meta['managed']):
    raise SystemExit(1)
if 'user customization' not in (root / meta['custom']).read_text(encoding='utf-8'):
    raise SystemExit(1)
if 'unknown c1 windsurf rules' not in (root / meta['unknown']).read_text(encoding='utf-8'):
    raise SystemExit(1)
lines = [
    line for line in (root / '.exocortex/.install-manifest').read_text(encoding='utf-8').splitlines()
    if line and not line.startswith('#')
]
keys = [line.rsplit(' ', 1)[0] for line in lines]
if len(keys) != len(set(keys)):
    raise SystemExit(1)
if f"{meta['custom']} {meta['custom_baseline']}" not in lines:
    raise SystemExit(1)
PY
then
    c1_first="$(tree_digest "$target")"
    run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
    c1_second="$(tree_digest "$target")"
    if [ "$c1_first" = "$c1_second" ]; then
        ok "direct C1 update retires managed Windsurf paths and preserves customized and unknown collisions idempotently"
    else
        bad "direct C1 update retires managed Windsurf paths and preserves customized and unknown collisions idempotently"
    fi
else
    bad "direct C1 update retires managed Windsurf paths and preserves customized and unknown collisions idempotently"
fi
rm -rf "$target" "$fake_home"
rm -f "$c1_meta" "$c1_log"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
mkdir -p "$target/.exocortex"/{events,archive,hub,local,planning,work-items,control}
protected=(
  SESSION_CONTEXT.md SESSION_CONTEXT.local.md TODO.md LESSONS.md PROJECT_MEMORY.md
  OPEN_DECISIONS.md subconscious_patterns.md .env .project-name .hub_enabled .hub_disabled
  events/canary.md archive/canary.md hub/canary.md local/canary.md planning/canary.md work-items/canary.md
  control/ACTIVE_WORK.md control/BRANCH_POLICY.md control/REPO_STATE.md
  control/EXECUTOR_REGISTRY.json control/EXTERNAL_SYNC_POLICY.json control/INTERRUPTS.md
  control/BACKLOG.md control/ROADMAP.md control/ARCH_OVERVIEW.md control/REPO_ORGANIZATION_REPORT.md
)
for rel in "${protected[@]}"; do
    mkdir -p "$(dirname "$target/.exocortex/$rel")"
    printf 'PRIVATE_CANARY_%s\n' "$rel" > "$target/.exocortex/$rel"
done
before="$(tree_digest "$target/.exocortex")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
for rel in "${protected[@]}"; do
    grep -Fq "PRIVATE_CANARY_$rel" "$target/.exocortex/$rel" || bad "protected path preserved: $rel"
done
ok "full protected-path canary matrix preserved"
rm -rf "$target" "$fake_home"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
printf '\nUSER_CUSTOMIZATION\n' >> "$target/.exocortex/COMMAND_SYSTEM.md"
custom_hash="$(hash_file "$target/.exocortex/COMMAND_SYSTEM.md")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
[ "$(hash_file "$target/.exocortex/COMMAND_SYSTEM.md")" = "$custom_hash" ] && ok "user-modified code-plane file preserved" || bad "user-modified code-plane file preserved"
rm -rf "$target" "$fake_home"

for case_name in missing malformed mismatch duplicate traversal extra; do
    source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
    cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
    case "$case_name" in
        missing) rm -f "$source_copy/SHA256SUMS" ;;
        malformed) printf 'not-a-checksum\n' >> "$source_copy/SHA256SUMS" ;;
        mismatch) printf '\nchanged\n' >> "$source_copy/AI_START_HERE.md" ;;
        duplicate) sed -n '1p' "$source_copy/SHA256SUMS" >> "$source_copy/SHA256SUMS" ;;
        traversal) printf '%064d  ../escape\n' 0 >> "$source_copy/SHA256SUMS" ;;
        extra) printf 'unlisted\n' > "$source_copy/UNLISTED_CODE_PLANE.txt" ;;
    esac
    expect_install_denial "checksum $case_name fails before target mutation" "$source_copy"
    rm -rf "$source_copy"
done

for tampered_path in \
    .exocortex/scripts/check_keys.sh \
    install.sh \
    scripts/safe-update.sh; do
    source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
    cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
    actual_mode="$(python3 -c 'import os,stat,sys; print(format(stat.S_IMODE(os.stat(sys.argv[1]).st_mode), "04o"))' "$source_copy/$tampered_path")"
    if [ "$actual_mode" = "0644" ]; then
        chmod 755 "$source_copy/$tampered_path"
    else
        chmod 644 "$source_copy/$tampered_path"
    fi
    expect_install_denial \
        "checksum-approved candidate rejects tampered mode for $tampered_path" \
        "$source_copy"
    rm -rf "$source_copy"
done

for mode_case in missing malformed duplicate traversal extra unsorted unsupported; do
    source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
    cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
    case "$mode_case" in
        missing) rm -f "$source_copy/FILEMODES" ;;
        malformed) printf 'not-a-mode-entry\n' >> "$source_copy/FILEMODES" ;;
        duplicate) sed -n '1p' "$source_copy/FILEMODES" >> "$source_copy/FILEMODES" ;;
        traversal) printf '0644  ../escape\n' >> "$source_copy/FILEMODES" ;;
        extra) printf '0644  UNLISTED_MODE_PATH\n' >> "$source_copy/FILEMODES" ;;
        unsorted)
            awk 'NR==1{first=$0;next} NR==2{print;print first;next} {print}' \
                "$source_copy/FILEMODES" > "$source_copy/FILEMODES.tmp"
            mv "$source_copy/FILEMODES.tmp" "$source_copy/FILEMODES"
            ;;
        unsupported) sed '1s/^0[67][45][45]/0777/' "$source_copy/FILEMODES" > "$source_copy/FILEMODES.tmp"; mv "$source_copy/FILEMODES.tmp" "$source_copy/FILEMODES" ;;
    esac
    if [ "$mode_case" != "missing" ]; then
        changed_hash="$(hash_file "$source_copy/FILEMODES")"
        awk -v h="$changed_hash" 'BEGIN{OFS="  "} $2=="FILEMODES"{$1=h} {print $1,$2}' \
            "$source_copy/SHA256SUMS" > "$source_copy/SHA256SUMS.tmp"
        mv "$source_copy/SHA256SUMS.tmp" "$source_copy/SHA256SUMS"
    fi
    expect_install_denial "FILEMODES $mode_case fails before target mutation" "$source_copy"
    rm -rf "$source_copy"
done

source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
outside_source="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source-outside.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
mv "$source_copy/.agents" "$outside_source/agents"
ln -s "$outside_source/agents" "$source_copy/.agents"
expect_install_denial \
    "installer rejects a checksum-valid source with a symlinked path ancestor" \
    "$source_copy"
rm -rf "$source_copy" "$outside_source"

if grep -E '(^|/)(__pycache__/|[^/]+\.py[co]$)' "$TEMPLATE_DIR/SHA256SUMS" >/dev/null; then
    bad "checksum inventory excludes generated bytecode"
else
    ok "checksum inventory excludes generated bytecode"
fi

source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
mkdir -p "$source_copy/.exocortex/scripts/__pycache__"
printf 'ignored generated bytecode\n' > "$source_copy/.exocortex/scripts/__pycache__/ignored.pyc"
target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
if run_install "$target" "$source_copy" "$fake_home" >/dev/null \
    && [ -z "$(find "$target" -type f \( -name '*.pyc' -o -name '*.pyo' \) -print -quit)" ]; then
    ok "installer ignores generated bytecode consistently with checksum CI"
else
    bad "installer ignores generated bytecode consistently with checksum CI"
fi
rm -rf "$source_copy" "$target" "$fake_home"

target="$(new_target)"
outside="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-outside.XXXXXX")"
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
work_temp="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-safe-temp.XXXXXX")"
printf 'outside update canary\n' > "$outside/canary.txt"
outside_before="$(tree_digest "$outside")"
ln -s "$outside" "$target/.exocortex"
if (cd "$target" && TMPDIR="$work_temp" bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$TEMPLATE_DIR" --candidate-digest "$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    --backup-dir "$backup" --dry-run) >/dev/null 2>&1; then
    bad "safe-update rejects target surface symlinks before reading or copying"
elif [ "$(tree_digest "$outside")" != "$outside_before" ] \
    || [ -n "$(find "$backup" -mindepth 1 -print -quit)" ] \
    || [ -n "$(find "$work_temp" -mindepth 1 -print -quit)" ]; then
    bad "safe-update rejects target surface symlinks before reading or copying"
else
    ok "safe-update rejects target surface symlinks before reading or copying"
fi
rm -rf "$target" "$outside" "$backup" "$work_temp"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
outside_hardlink="$(mktemp "${TMPDIR:-/tmp}/exo-test-update-hardlink.XXXXXX")"
cp -p "$target/.exocortex/COMMAND_SYSTEM.md" "$outside_hardlink"
rm -f "$target/.exocortex/COMMAND_SYSTEM.md"
ln "$outside_hardlink" "$target/.exocortex/COMMAND_SYSTEM.md"
outside_hardlink_hash_before="$(hash_file "$outside_hardlink")"
outside_hardlink_mode_before="$(python3 -c 'import os,stat,sys; print(format(stat.S_IMODE(os.stat(sys.argv[1]).st_mode), "04o"))' "$outside_hardlink")"
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
work_temp="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-safe-temp.XXXXXX")"
if (cd "$target" && TMPDIR="$work_temp" bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$TEMPLATE_DIR" --candidate-digest "$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    --backup-dir "$backup" --dry-run) >/dev/null 2>&1 \
    || [ "$(hash_file "$outside_hardlink")" != "$outside_hardlink_hash_before" ] \
    || [ "$(python3 -c 'import os,stat,sys; print(format(stat.S_IMODE(os.stat(sys.argv[1]).st_mode), "04o"))' "$outside_hardlink")" != "$outside_hardlink_mode_before" ] \
    || [ -n "$(find "$backup" -mindepth 1 -print -quit)" ] \
    || [ -n "$(find "$work_temp" -mindepth 1 -print -quit)" ]; then
    bad "safe-update rejects an external hard-linked code-plane file before backup"
else
    ok "safe-update rejects an external hard-linked code-plane file before backup"
fi
rm -rf "$target" "$fake_home" "$backup" "$work_temp"
rm -f "$outside_hardlink"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
work_temp="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-safe-temp.XXXXXX")"
target_before="$(tree_digest "$target")"
if (cd "$target" && TMPDIR="$work_temp" bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$TEMPLATE_DIR" --candidate-digest "$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    --backup-dir "$backup" --apply --capability .exocortex/local/protocol/capabilities/missing.json \
    --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id unauthorized-update \
    --surface-id test-surface --executor-id test-executor --adapter-version test-v1) >/dev/null 2>&1; then
    bad "unauthorized safe-update creates no backup or rehearsal"
elif [ "$(tree_digest "$target")" != "$target_before" ] \
    || [ -n "$(find "$backup" -mindepth 1 -print -quit)" ] \
    || [ -n "$(find "$work_temp" -mindepth 1 -print -quit)" ]; then
    bad "unauthorized safe-update creates no backup or rehearsal"
else
    ok "unauthorized safe-update creates no backup or rehearsal"
fi

outside="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-outside.XXXXXX")"
printf 'backup path canary\n' > "$outside/canary.txt"
canary_before="$(hash_file "$outside/canary.txt")"
ln -s "$target/.exocortex" "$outside/redirect"
if (cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$TEMPLATE_DIR" --candidate-digest "$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    --backup-dir "$outside/redirect/redirected-backup" --dry-run) >/dev/null 2>&1; then
    bad "safe-update rejects backup ancestor symlink before mutation"
elif [ "$(tree_digest "$target")" != "$target_before" ] \
    || [ "$(hash_file "$outside/canary.txt")" != "$canary_before" ] \
    || [ -e "$target/.exocortex/redirected-backup" ]; then
    bad "safe-update rejects backup ancestor symlink before mutation"
else
    ok "safe-update rejects backup ancestor symlink before mutation"
fi
rm -rf "$target" "$fake_home" "$backup" "$work_temp" "$outside"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
printf 'KEEP_ME\n' > "$target/.exocortex/LESSONS.md"
target_before="$(tree_digest "$target")"
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
(cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" --backup-dir "$backup" --dry-run) >/tmp/exo-safe-update-test.log 2>&1
target_after="$(tree_digest "$target")"
[ "$target_before" = "$target_after" ] && ok "safe-update dry-run leaves target byte-identical" || bad "safe-update dry-run leaves target byte-identical"
grep -Fq 'Protected data check: PASS' /tmp/exo-safe-update-test.log && ok "safe-update proves protected data" || bad "safe-update proves protected data"
restore_archive="$(find "$backup" -type f -name '*.tar.gz.*' -print -quit)"
if [ -n "$restore_archive" ] \
    && [ "$(python3 -c 'import os,stat,sys; print(format(stat.S_IMODE(os.stat(sys.argv[1]).st_mode), "04o"))' "$restore_archive")" = "0600" ] \
    && tar -tzf "$restore_archive" | grep -Fq '.exocortex/COMMAND_SYSTEM.md' \
    && ! tar -tzf "$restore_archive" | grep -Eq '^\\.?/?\\.exocortex/(LESSONS\\.md|local/|events/)'; then
    ok "safe-update creates a private code-plane-only restore archive"
else
    bad "safe-update creates a private code-plane-only restore archive"
fi
rm -rf "$target" "$fake_home" "$backup"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
chmod 755 "$source_copy/.exocortex/scripts/check_keys.sh"
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
target_before="$(tree_digest "$target")"
if (cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$source_copy" \
    --candidate-digest "$(hash_file "$source_copy/SHA256SUMS")" \
    --backup-dir "$backup" --dry-run) >/dev/null 2>&1; then
    bad "safe-update rejects a checksum-approved source-mode change before backup"
elif [ "$(tree_digest "$target")" != "$target_before" ] \
    || [ -n "$(find "$backup" -mindepth 1 -print -quit)" ]; then
    bad "safe-update rejects a checksum-approved source-mode change before backup"
else
    ok "safe-update rejects a checksum-approved source-mode change before backup"
fi
rm -rf "$target" "$fake_home" "$source_copy" "$backup"

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
external_sums="$(mktemp "${TMPDIR:-/tmp}/exo-test-external-sums.XXXXXX")"
cp -p "$source_copy/SHA256SUMS" "$external_sums"
rm -f "$source_copy/SHA256SUMS"
ln -s "$external_sums" "$source_copy/SHA256SUMS"
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
target_before="$(tree_digest "$target")"
if (cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$source_copy" \
    --candidate-digest "$(hash_file "$source_copy/SHA256SUMS")" \
    --backup-dir "$backup" --dry-run) >/dev/null 2>&1; then
    bad "safe-update rejects a symlinked candidate SHA256SUMS before backup"
elif [ "$(tree_digest "$target")" != "$target_before" ] \
    || [ -n "$(find "$backup" -mindepth 1 -print -quit)" ]; then
    bad "safe-update rejects a symlinked candidate SHA256SUMS before backup"
else
    ok "safe-update rejects a symlinked candidate SHA256SUMS before backup"
fi
rm -rf "$target" "$fake_home" "$source_copy" "$backup"
rm -f "$external_sums"
rm -f /tmp/exo-safe-update-test.log

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
fixture_meta="$(mktemp "${TMPDIR:-/tmp}/exo-test-complete-paths-meta.XXXXXX")"
python3 - "$target" "$fixture_meta" <<'PY'
import hashlib, json, sys
from pathlib import Path

root = Path(sys.argv[1])
meta = Path(sys.argv[2])
manifest = root / '.exocortex/.install-manifest'
records = {}
for line in manifest.read_text(encoding='utf-8').splitlines():
    if not line or line.startswith('#'):
        continue
    rel, digest = line.rsplit(' ', 1)
    path = root / rel
    if path.is_file() and not path.is_symlink():
        records[rel] = digest
selected = sorted(records)[:121]
if len(selected) != 121:
    raise SystemExit('fixture requires at least 121 manifest-managed files')
for index, rel in enumerate(selected):
    path = root / rel
    path.write_bytes(path.read_bytes() + f'\nOLD_TEMPLATE_FIXTURE_{index:03d}\n'.encode())
    records[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
manifest.write_text(
    '# Exocortex install manifest - template code plane only\n'
    + ''.join(f'{rel} {digest}\n' for rel, digest in sorted(records.items())),
    encoding='utf-8',
)
meta.write_text(json.dumps({'selected_count': len(selected), 'sentinel': selected[-1]}) + '\n', encoding='utf-8')
PY
target_before="$(tree_digest "$target")"
backup_one="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
backup_two="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
complete_log_one="$(mktemp "${TMPDIR:-/tmp}/exo-test-complete-paths-one.XXXXXX")"
complete_log_two="$(mktemp "${TMPDIR:-/tmp}/exo-test-complete-paths-two.XXXXXX")"
complete_paths_one="$(mktemp "${TMPDIR:-/tmp}/exo-test-complete-paths-list-one.XXXXXX")"
complete_paths_two="$(mktemp "${TMPDIR:-/tmp}/exo-test-complete-paths-list-two.XXXXXX")"
(cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$TEMPLATE_DIR" --candidate-digest "$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    --backup-dir "$backup_one" --dry-run) > "$complete_log_one" 2>&1
(cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$TEMPLATE_DIR" --candidate-digest "$(hash_file "$TEMPLATE_DIR/SHA256SUMS")" \
    --backup-dir "$backup_two" --dry-run) > "$complete_log_two" 2>&1
awk '/^Rehearsal changed paths:/ {capture=1; next} /^Dry run complete/ {capture=0} capture && NF {print}' "$complete_log_one" > "$complete_paths_one"
awk '/^Rehearsal changed paths:/ {capture=1; next} /^Dry run complete/ {capture=0} capture && NF {print}' "$complete_log_two" > "$complete_paths_two"
if python3 - "$complete_log_one" "$complete_paths_one" "$complete_log_two" "$complete_paths_two" "$fixture_meta" <<'PY'
import hashlib, json, re, sys
from pathlib import Path

def evidence(log_name, paths_name):
    log = Path(log_name).read_text(encoding='utf-8')
    count_match = re.search(r'^Rehearsal changed paths: ([0-9]+)$', log, re.MULTILINE)
    digest_match = re.search(r'^Rehearsal changed paths SHA-256: ([0-9a-f]{64})$', log, re.MULTILINE)
    if not count_match or not digest_match:
        raise SystemExit(1)
    raw = Path(paths_name).read_bytes()
    paths = raw.decode('utf-8').splitlines()
    if raw != ''.join(path + '\n' for path in paths).encode('utf-8'):
        raise SystemExit(1)
    if int(count_match.group(1)) != len(paths) or len(paths) <= 120:
        raise SystemExit(1)
    if paths != sorted(set(paths)):
        raise SystemExit(1)
    if hashlib.sha256(raw).hexdigest() != digest_match.group(1):
        raise SystemExit(1)
    return paths, digest_match.group(1)

first_paths, first_digest = evidence(sys.argv[1], sys.argv[2])
second_paths, second_digest = evidence(sys.argv[3], sys.argv[4])
meta = json.loads(Path(sys.argv[5]).read_text(encoding='utf-8'))
if meta['sentinel'] not in first_paths:
    raise SystemExit(1)
if first_paths != second_paths or first_digest != second_digest:
    raise SystemExit(1)
PY
then
    if [ "$(tree_digest "$target")" = "$target_before" ]; then
        ok "safe-update emits complete deterministic sorted path evidence and digest above 120 paths"
    else
        bad "safe-update emits complete deterministic sorted path evidence and digest above 120 paths"
    fi
else
    bad "safe-update emits complete deterministic sorted path evidence and digest above 120 paths"
fi
rm -rf "$target" "$fake_home" "$backup_one" "$backup_two"
rm -f "$fixture_meta" "$complete_log_one" "$complete_log_two" "$complete_paths_one" "$complete_paths_two"

make_old_template_source() {
    local source old_hash
    source="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-old-template.XXXXXX")"
    cp -Rp "$TEMPLATE_DIR/." "$source/"
    printf '\nOLD_TEMPLATE_FIXTURE\n' >> "$source/.exocortex/COMMAND_SYSTEM.md"
    old_hash="$(hash_file "$source/.exocortex/COMMAND_SYSTEM.md")"
    awk -v h="$old_hash" 'BEGIN{OFS="  "} $2==".exocortex/COMMAND_SYSTEM.md"{$1=h} {print $1,$2}' "$source/SHA256SUMS" > "$source/SHA256SUMS.tmp"
    mv "$source/SHA256SUMS.tmp" "$source/SHA256SUMS"
    chmod 0644 "$source/SHA256SUMS"
    printf '%s\n' "$source"
}

old_source="$(make_old_template_source)"
target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$old_source" "$fake_home" >/dev/null
printf 'KEEP_PROTECTED\n' > "$target/.exocortex/TODO.md"
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
apply_probe_log="$(mktemp "${TMPDIR:-/tmp}/exo-test-apply-probe.XXXXXX")"
candidate_digest="$(hash_file "$TEMPLATE_DIR/SHA256SUMS")"
(cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" --backup-dir "$backup" --dry-run) > "$apply_probe_log" 2>&1
changed_paths="$(mktemp "${TMPDIR:-/tmp}/exo-test-changed-paths.XXXXXX")"
awk '/^Rehearsal changed paths:/ {capture=1; next} /^Dry run complete/ {capture=0} capture && NF {print}' "$apply_probe_log" > "$changed_paths"
guard_digest="$(python3 "$TEMPLATE_DIR/.exocortex/scripts/authority_guard.py" guard-digest)"
python3 - "$target" "$guard_digest" "$candidate_digest" "$changed_paths" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
guard=sys.argv[2]
candidate=sys.argv[3]
paths=Path(sys.argv[4]).read_text(encoding='utf-8').splitlines()
registry={
  'schema_version':'public-v2','kind':'executor_registry','registry_version':1,
  'default_role':'read_only','executors':[{
    'surface_id':'test-surface','executor_id':'test-executor','adapter_version':'test-v1',
    'guard_digest':guard,'roles':['read_only','writer'],'status':'active',
    'registered_at':'2026-01-01T00:00:00Z','expires_at':'2099-01-01T00:00:00Z','revoked_at':None,
  }],
}
capability={
  'schema_version':'public-v2','kind':'approval_capability','capability_id':'cap-update-apply',
  'work_item_id':'TEST-UPGRADE-001','work_item_revision':0,'operation':'apply_template_update',
  'scope':{'allowed_paths':paths,'target_sha':candidate},
  'executor':{'surface_id':'test-surface','executor_id':'test-executor','adapter_version':'test-v1','guard_digest':guard,'registry_version':1},
  'approval':{'approved_by':'fixture-human','accepted_at':'2026-01-01T00:00:00Z','expires_at':'2099-01-01T00:00:00Z','one_time':True,'summary':'fictional apply fixture'},
  'status':{'state':'active','revoked_at':None,'consumed_at':None,'consumed_by_request_id':None},
}
for rel,value in (
  ('.exocortex/control/EXECUTOR_REGISTRY.json',registry),
  ('.exocortex/local/protocol/capabilities/update-apply.json',capability),
):
  path=root/rel
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY
apply_log="$(mktemp "${TMPDIR:-/tmp}/exo-test-apply.XXXXXX")"
if (cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
    --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" --backup-dir "$backup" --apply \
    --capability .exocortex/local/protocol/capabilities/update-apply.json \
    --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id apply-update \
    --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$apply_log" 2>&1 \
    && [ "$(hash_file "$target/.exocortex/COMMAND_SYSTEM.md")" = "$(hash_file "$TEMPLATE_DIR/.exocortex/COMMAND_SYSTEM.md")" ] \
    && grep -Fq 'KEEP_PROTECTED' "$target/.exocortex/TODO.md" \
    && grep -Fq '"state": "consumed"' "$target/.exocortex/local/protocol/capabilities/update-apply.json"; then
    ok "guarded safe-update apply matches rehearsal and preserves protected data"
else
    bad "guarded safe-update apply matches rehearsal and preserves protected data"
fi
rm -rf "$old_source" "$target" "$fake_home" "$backup"
rm -f "$apply_probe_log" "$changed_paths" "$apply_log"

old_source="$(make_old_template_source)"
target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$old_source" "$fake_home" >/dev/null
rm -f "$target/.exocortex/AI_BOOTSTRAP.md"
printf 'RESTORE_PROTECTED_CANARY\n' > "$target/.exocortex/PROJECT_MEMORY.md"
backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
barrier_root="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-barrier.XXXXXX")"
race_log="$barrier_root/safe-update.log"
race_probe_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-backup.XXXXXX")"
race_probe_log="$barrier_root/probe.log"
race_changed_paths="$barrier_root/changed-paths.txt"
(cd "$target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
  --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$race_probe_backup" --dry-run) > "$race_probe_log" 2>&1
awk '/^Rehearsal changed paths:/ {capture=1; next} /^Dry run complete/ {capture=0} capture && NF {print}' \
  "$race_probe_log" > "$race_changed_paths"
guard_digest="$(python3 "$TEMPLATE_DIR/.exocortex/scripts/authority_guard.py" guard-digest)"
python3 - "$target" "$guard_digest" "$candidate_digest" "$race_changed_paths" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
guard=sys.argv[2]
candidate=sys.argv[3]
paths=Path(sys.argv[4]).read_text(encoding='utf-8').splitlines()
registry={
  'schema_version':'public-v2','kind':'executor_registry','registry_version':1,
  'default_role':'read_only','executors':[{
    'surface_id':'test-surface','executor_id':'test-executor','adapter_version':'test-v1',
    'guard_digest':guard,'roles':['read_only','writer'],'status':'active',
    'registered_at':'2026-01-01T00:00:00Z','expires_at':'2099-01-01T00:00:00Z','revoked_at':None,
  }],
}
capability={
  'schema_version':'public-v2','kind':'approval_capability','capability_id':'cap-update-race',
  'work_item_id':'TEST-UPGRADE-001','work_item_revision':0,'operation':'apply_template_update',
  'scope':{'allowed_paths':paths,'target_sha':candidate},
  'executor':{'surface_id':'test-surface','executor_id':'test-executor','adapter_version':'test-v1','guard_digest':guard,'registry_version':1},
  'approval':{'approved_by':'fixture-human','accepted_at':'2026-01-01T00:00:00Z','expires_at':'2099-01-01T00:00:00Z','one_time':True,'summary':'fictional race fixture'},
  'status':{'state':'active','revoked_at':None,'consumed_at':None,'consumed_by_request_id':None},
}
for rel,value in (
  ('.exocortex/control/EXECUTOR_REGISTRY.json',registry),
  ('.exocortex/local/protocol/capabilities/update-race.json',capability),
):
  path=root/rel
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')
PY
rollback_baseline="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-rollback-baseline.XXXXXX")"
cp -pR "$target/." "$rollback_baseline/"
rollback_baseline_digest="$(code_plane_digest "$rollback_baseline")"
archive_capability="$target/.exocortex/local/protocol/capabilities/update-race.json"
archive_ungated_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-archive-fault.XXXXXX")"
archive_ungated_log="$barrier_root/archive-ungated.log"
archive_ungated_code_before="$(code_plane_digest "$target")"
archive_ungated_protected_before="$(protected_plane_digest "$target")"
archive_ungated_capability_before="$(hash_file "$archive_capability")"
if (cd "$target" && EXOCORTEX_TEST_ARCHIVE_FAULT=corrupt \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$archive_ungated_backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
  --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id archive-ungated \
  --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$archive_ungated_log" 2>&1 \
  || ! grep -Fq 'archive fault injection is available only in explicit test mode' "$archive_ungated_log" \
  || [ "$(code_plane_digest "$target")" != "$archive_ungated_code_before" ] \
  || [ "$(protected_plane_digest "$target")" != "$archive_ungated_protected_before" ] \
  || [ "$(hash_file "$archive_capability")" != "$archive_ungated_capability_before" ] \
  || [ -n "$(find "$archive_ungated_backup" -mindepth 1 -print -quit)" ]; then
    bad "safe-update rejects archive fault injection outside explicit test mode"
else
    ok "safe-update rejects archive fault injection outside explicit test mode"
fi
rm -rf "$archive_ungated_backup"
archive_invalid_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-archive-fault.XXXXXX")"
archive_invalid_log="$barrier_root/archive-invalid.log"
if (cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_ARCHIVE_FAULT=invalid \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$archive_invalid_backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
  --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id archive-invalid \
  --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$archive_invalid_log" 2>&1 \
  || ! grep -Fq 'unknown test-only archive fault' "$archive_invalid_log" \
  || [ -n "$(find "$archive_invalid_backup" -mindepth 1 -print -quit)" ]; then
    bad "safe-update rejects an unknown archive fault selector"
else
    ok "safe-update rejects an unknown archive fault selector"
fi
rm -rf "$archive_invalid_backup"

archive_dry_run_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-archive-fault.XXXXXX")"
archive_dry_run_log="$barrier_root/archive-dry-run.log"
if (cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_ARCHIVE_FAULT=corrupt \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$archive_dry_run_backup" --dry-run) > "$archive_dry_run_log" 2>&1 \
  || ! grep -Fq 'archive fault injection requires an apply rehearsal' "$archive_dry_run_log" \
  || [ -n "$(find "$archive_dry_run_backup" -mindepth 1 -print -quit)" ]; then
    bad "safe-update rejects archive fault injection during dry-run"
else
    ok "safe-update rejects archive fault injection during dry-run"
fi
rm -rf "$archive_dry_run_backup"

archive_nonfixture_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-not-archive.XXXXXX")"
archive_nonfixture_log="$barrier_root/archive-nonfixture.log"
if (cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_ARCHIVE_FAULT=corrupt \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$archive_nonfixture_backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
  --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id archive-nonfixture \
  --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$archive_nonfixture_log" 2>&1 \
  || ! grep -Fq 'archive fault injection requires a dedicated temporary backup fixture' "$archive_nonfixture_log" \
  || [ -n "$(find "$archive_nonfixture_backup" -mindepth 1 -print -quit)" ]; then
    bad "safe-update confines archive faults to a dedicated temporary fixture"
else
    ok "safe-update confines archive faults to a dedicated temporary fixture"
fi
rm -rf "$archive_nonfixture_backup"

for archive_fault in substitute corrupt file-fsync directory-fsync; do
    case "$archive_fault" in
        substitute)
            archive_fault_detector='rollback archive identity changed before write'
            archive_fault_failure='rollback archive creation failed'
            ;;
        corrupt)
            archive_fault_detector='rollback archive digest mismatch'
            archive_fault_failure='rollback archive failed identity, privacy, or integrity verification'
            ;;
        file-fsync)
            archive_fault_detector='injected test-only rollback archive file-fsync failure'
            archive_fault_failure='rollback archive creation failed'
            ;;
        directory-fsync)
            archive_fault_detector='injected test-only rollback archive directory-fsync failure'
            archive_fault_failure='rollback archive publication failed'
            ;;
    esac
    archive_fault_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-archive-fault.XXXXXX")"
    archive_fault_code_before="$(code_plane_digest "$target")"
    archive_fault_protected_before="$(protected_plane_digest "$target")"
    archive_fault_capability_before="$(hash_file "$archive_capability")"
    archive_fault_log="$barrier_root/archive-$archive_fault.log"
    if (cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_ARCHIVE_FAULT="$archive_fault" \
      bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
      --backup-dir "$archive_fault_backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
      --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id "archive-$archive_fault" \
      --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$archive_fault_log" 2>&1 \
      || ! grep -Fq "$archive_fault_detector" "$archive_fault_log" \
      || ! grep -Fq "$archive_fault_failure" "$archive_fault_log" \
      || { [ "$archive_fault" = "substitute" ] \
          && ! grep -Fq 'test-only rollback archive substitution canary preserved' "$archive_fault_log"; } \
      || grep -Fq 'Backup:' "$archive_fault_log" \
      || grep -Fq 'Update applied' "$archive_fault_log" \
      || [ "$(code_plane_digest "$target")" != "$archive_fault_code_before" ] \
      || [ "$(protected_plane_digest "$target")" != "$archive_fault_protected_before" ] \
      || [ "$(hash_file "$archive_capability")" != "$archive_fault_capability_before" ] \
      || ! grep -Fq '"state": "active"' "$target/.exocortex/local/protocol/capabilities/update-race.json" \
      || [ -n "$(find "$archive_fault_backup" -mindepth 1 -print -quit)" ]; then
        bad "safe-update fails closed on rollback archive $archive_fault fault"
    else
        ok "safe-update fails closed on rollback archive $archive_fault fault"
    fi
    rm -rf "$archive_fault_backup"
done
(cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_APPLY_BARRIER="$barrier_root/gate" \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
  --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id race-update \
  --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$race_log" 2>&1 &
race_pid=$!
race_wait=0
while [ ! -e "$barrier_root/gate.ready" ] && [ "$race_wait" -lt 800 ]; do
    sleep 0.05
    race_wait=$((race_wait + 1))
done
if [ -e "$barrier_root/gate.ready" ]; then
    chmod 0755 "$target/.exocortex/COMMAND_SYSTEM.md"
    : > "$barrier_root/gate.continue"
fi
wait "$race_pid"
race_rc=$?
if [ "$race_rc" -ne 0 ] \
    && grep -Fq 'live target changed after rehearsal' "$race_log" \
    && grep -Fq 'OLD_TEMPLATE_FIXTURE' "$target/.exocortex/COMMAND_SYSTEM.md" \
    && [ -x "$target/.exocortex/COMMAND_SYSTEM.md" ] \
    && grep -Fq '"state": "active"' "$target/.exocortex/local/protocol/capabilities/update-race.json"; then
    ok "safe-update denies a mode-only target race before capability consumption"
else
    bad "safe-update denies a mode-only target race before capability consumption"
fi

chmod 0644 "$target/.exocortex/COMMAND_SYSTEM.md"
hardlink_barrier="$barrier_root/hardlink-gate"
hardlink_log="$barrier_root/hardlink-race.log"
hardlink_outside="$barrier_root/hardlink-outside"
cp -p "$target/.exocortex/COMMAND_SYSTEM.md" "$hardlink_outside"
(cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_APPLY_BARRIER="$hardlink_barrier" \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
  --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id hardlink-race-update \
  --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$hardlink_log" 2>&1 &
hardlink_pid=$!
hardlink_wait=0
while [ ! -e "$hardlink_barrier.ready" ] && [ "$hardlink_wait" -lt 800 ]; do
    sleep 0.05
    hardlink_wait=$((hardlink_wait + 1))
done
if [ -e "$hardlink_barrier.ready" ]; then
    rm -f "$target/.exocortex/COMMAND_SYSTEM.md"
    ln "$hardlink_outside" "$target/.exocortex/COMMAND_SYSTEM.md"
    : > "$hardlink_barrier.continue"
fi
wait "$hardlink_pid"
hardlink_rc=$?
if [ "$hardlink_rc" -ne 0 ] \
    && grep -Fq 'external hard-linked file' "$hardlink_log" \
    && grep -Fq '"state": "active"' "$target/.exocortex/local/protocol/capabilities/update-race.json" \
    && [ "$(python3 -c 'import os,sys; print(os.lstat(sys.argv[1]).st_nlink)' "$hardlink_outside")" = "2" ]; then
    ok "safe-update denies a barrier-time hard-link race before capability consumption"
else
    bad "safe-update denies a barrier-time hard-link race before capability consumption"
fi
rm -f "$target/.exocortex/COMMAND_SYSTEM.md"
cp -p "$hardlink_outside" "$target/.exocortex/COMMAND_SYSTEM.md"

directory_barrier="$barrier_root/directory-mode-gate"
directory_log="$barrier_root/directory-mode-race.log"
directory_mode_before="$(python3 -c 'import os,stat,sys; print(format(stat.S_IMODE(os.lstat(sys.argv[1]).st_mode), "04o"))' "$target/.exocortex")"
if [ "$directory_mode_before" = "0700" ]; then
    directory_mode_raced="0755"
else
    directory_mode_raced="0700"
fi
(cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_APPLY_BARRIER="$directory_barrier" \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
  --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id directory-mode-race-update \
  --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$directory_log" 2>&1 &
directory_pid=$!
directory_wait=0
while [ ! -e "$directory_barrier.ready" ] && [ "$directory_wait" -lt 800 ]; do
    sleep 0.05
    directory_wait=$((directory_wait + 1))
done
if [ -e "$directory_barrier.ready" ]; then
    chmod "$directory_mode_raced" "$target/.exocortex"
    : > "$directory_barrier.continue"
fi
wait "$directory_pid"
directory_rc=$?
if [ "$directory_rc" -ne 0 ] \
    && grep -Fq 'live target changed after rehearsal' "$directory_log" \
    && grep -Fq '"state": "active"' "$target/.exocortex/local/protocol/capabilities/update-race.json"; then
    ok "safe-update denies a directory-mode race before capability consumption"
else
    bad "safe-update denies a directory-mode race before capability consumption"
fi
chmod "$directory_mode_before" "$target/.exocortex"

post_apply_log="$barrier_root/post-apply.log"
(cd "$target" && EXOCORTEX_TEST_MODE=1 EXOCORTEX_TEST_INSTALL_FAULT_AFTER_COPIES=1 \
  bash "$TEMPLATE_DIR/scripts/safe-update.sh" --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
  --backup-dir "$backup" --apply --capability .exocortex/local/protocol/capabilities/update-race.json \
  --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id post-apply-race \
  --surface-id test-surface --executor-id test-executor --adapter-version test-v1) > "$post_apply_log" 2>&1
post_apply_rc=$?
if [ "$post_apply_rc" -ne 0 ] \
    && grep -Fq 'injected test-only install fault after 1 copies' "$post_apply_log" \
    && [ -f "$target/.exocortex/AI_BOOTSTRAP.md" ] \
    && grep -Fq 'OLD_TEMPLATE_FIXTURE' "$target/.exocortex/COMMAND_SYSTEM.md" \
    && grep -Fq '"state": "consumed"' "$target/.exocortex/local/protocol/capabilities/update-race.json" \
    && [ "$(find "$backup" -type f -name '*.tar.gz.*' | wc -l | tr -d ' ')" -ge 2 ] \
    && python3 - "$backup" <<'PY'
import os, stat, sys, tarfile
from pathlib import Path
archives = sorted(Path(sys.argv[1]).glob('*.tar.gz.*'))
if len(archives) < 2 or len({path.name for path in archives}) != len(archives):
    raise SystemExit(1)
for path in archives:
    value = os.lstat(path)
    if stat.S_IMODE(value.st_mode) != 0o600 or value.st_nlink != 1:
        raise SystemExit(1)
    with tarfile.open(path, 'r:gz') as archive:
        archive.getmembers()
PY
then
    ok "safe-update reaches a live post-consumption fault with unique verified private archives"
else
    bad "safe-update reaches a live post-consumption fault with unique verified private archives"
fi

restore_target="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-rollback-restore.XXXXXX")"
restore_stash="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-rollback-stash.XXXXXX")"
post_fault_protected_digest="$(protected_plane_digest "$target")"
cp -pR "$target/." "$restore_target/"
restore_archive="$(awk -F': ' '/^Backup: /{print $2; exit}' "$post_apply_log")"
python3 - "$restore_target" "$restore_stash" <<'PY'
import os
from pathlib import Path
import shutil
import sys

root, stash = map(Path, sys.argv[1:3])
surface = (
    '.exocortex', '.agents', '.cursor', '.claude', '.github', '.windsurf',
    'AI_START_HERE.md', 'AGENTS.md', 'CLAUDE.md', '.windsurfrules', '.rules', '.gitignore',
)
protected = (
    '.exocortex/SESSION_CONTEXT.md', '.exocortex/SESSION_CONTEXT.local.md',
    '.exocortex/TODO.md', '.exocortex/LESSONS.md', '.exocortex/PROJECT_MEMORY.md',
    '.exocortex/OPEN_DECISIONS.md', '.exocortex/subconscious_patterns.md',
    '.exocortex/.env', '.exocortex/.project-name', '.exocortex/events',
    '.exocortex/archive', '.exocortex/hub', '.exocortex/local', '.exocortex/planning',
    '.exocortex/work-items', '.exocortex/control/ACTIVE_WORK.md',
    '.exocortex/control/BRANCH_POLICY.md', '.exocortex/control/REPO_STATE.md',
    '.exocortex/control/EXECUTOR_REGISTRY.json',
    '.exocortex/control/EXTERNAL_SYNC_POLICY.json',
    '.exocortex/control/INTERRUPTS.md', '.exocortex/control/BACKLOG.md',
    '.exocortex/control/ROADMAP.md', '.exocortex/control/ARCH_OVERVIEW.md',
    '.exocortex/control/REPO_ORGANIZATION_REPORT.md',
    '.exocortex/.hub_enabled', '.exocortex/.hub_disabled',
)
for relative in protected:
    source = root / relative
    if not os.path.lexists(source):
        continue
    destination = stash / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, copy_function=shutil.copy2)
    else:
        shutil.copy2(source, destination, follow_symlinks=False)
for relative in surface:
    path = root / relative
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif os.path.lexists(path):
        path.unlink()
PY
if [ -n "$restore_archive" ] \
    && COPYFILE_DISABLE=1 tar -xzpf "$restore_archive" -C "$restore_target" \
    && python3 - "$restore_target" "$restore_stash" <<'PY'
import os
from pathlib import Path
import shutil
import sys

root, stash = map(Path, sys.argv[1:3])
for source in sorted(stash.rglob('*'), key=lambda path: len(path.parts)):
    relative = source.relative_to(stash)
    destination = root / relative
    if source.is_dir():
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copystat(source, destination, follow_symlinks=False)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)
PY
then
    :
else
    false
fi
if [ -n "$restore_archive" ] \
    && [ "$(code_plane_digest "$restore_target")" = "$rollback_baseline_digest" ] \
    && [ "$(protected_plane_digest "$restore_target")" = "$post_fault_protected_digest" ] \
    && [ ! -e "$restore_target/.exocortex/AI_BOOTSTRAP.md" ] \
    && grep -Fq 'RESTORE_PROTECTED_CANARY' "$restore_target/.exocortex/PROJECT_MEMORY.md" \
    && ! tar -tzf "$restore_archive" | grep -Eq '^\\.?/?\\.exocortex/local(/|$)' \
    && grep -Fq '"state": "consumed"' "$restore_target/.exocortex/local/protocol/capabilities/update-race.json"; then
    ok "rollback removes post-fault additions and restores the exact prior code plane in place"
else
    bad "rollback removes post-fault additions and restores the exact prior code plane in place"
fi
replay_code_before="$(code_plane_digest "$restore_target")"
replay_protected_before="$(protected_plane_digest "$restore_target")"
replay_same_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-replay-backup.XXXXXX")"
replay_different_backup="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-replay-backup.XXXXXX")"
if (cd "$restore_target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
      --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
      --backup-dir "$replay_same_backup" --apply \
      --capability .exocortex/local/protocol/capabilities/update-race.json \
      --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id post-apply-race \
      --surface-id test-surface --executor-id test-executor --adapter-version test-v1) >/dev/null 2>&1 \
    || (cd "$restore_target" && bash "$TEMPLATE_DIR/scripts/safe-update.sh" \
      --template "$TEMPLATE_DIR" --candidate-digest "$candidate_digest" \
      --backup-dir "$replay_different_backup" --apply \
      --capability .exocortex/local/protocol/capabilities/update-race.json \
      --work-item-id TEST-UPGRADE-001 --work-item-revision 0 --request-id replay-different-request \
      --surface-id test-surface --executor-id test-executor --adapter-version test-v1) >/dev/null 2>&1 \
    || [ "$(code_plane_digest "$restore_target")" != "$replay_code_before" ] \
    || [ "$(protected_plane_digest "$restore_target")" != "$replay_protected_before" ] \
    || [ -n "$(find "$replay_same_backup" "$replay_different_backup" -mindepth 1 -print -quit)" ]; then
    bad "consumed update capability denies same-request and different-request replay"
else
    ok "consumed update capability denies same-request and different-request replay"
fi
rm -rf "$replay_same_backup" "$replay_different_backup"
rm -rf "$old_source" "$target" "$fake_home" "$backup" "$race_probe_backup" "$barrier_root" "$rollback_baseline" "$restore_target" "$restore_stash"

hook_target="$(new_target)"
hook_before="$(tree_digest "$hook_target")"
hook_output="$(printf '%s\n' '{"description":"Phase 2 complete"}' | (cd "$hook_target" && bash "$TEMPLATE_DIR/.cursor/hooks/auto-save-phase.sh"))"
hook_after="$(tree_digest "$hook_target")"
if [ "$hook_before" = "$hook_after" ] && printf '%s' "$hook_output" | grep -Fq 'Do not save automatically'; then
    ok "legacy-named phase hook is reminder-only"
else
    bad "legacy-named phase hook is reminder-only"
fi
rm -rf "$hook_target"

invalid_evidence_existing="$(mktemp -d "${TMPDIR:-/tmp}/exo-phase-b-evidence.existing.XXXXXX")"
invalid_evidence_cases=(
    "relative-evidence"
    "${TMPDIR:-/tmp}/not-phase-b-evidence"
    "$TEMPLATE_DIR/tests/phase-b/exo-phase-b-evidence.workspace"
    "${HOME:-/__no_home__}/exo-phase-b-evidence.home"
    "$invalid_evidence_existing"
)
for invalid_evidence in "${invalid_evidence_cases[@]}"; do
    if bash "$TEMPLATE_DIR/tests/phase-b/run.sh" "$invalid_evidence" >/dev/null 2>&1; then
        bad "phase-b harness rejects unsafe evidence path"
    else
        ok "phase-b harness rejects unsafe evidence path"
    fi
done
rm -rf "$invalid_evidence_existing"

fake_workspace_tmp="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-fake-workspace.XXXXXX")"
fake_home_tmp="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-fake-home.XXXXXX")"
for caller_tmp in "$fake_workspace_tmp" "$fake_home_tmp"; do
    requested="$caller_tmp/exo-phase-b-evidence.caller-controlled"
    if TMPDIR="$caller_tmp" bash "$TEMPLATE_DIR/tests/phase-b/run.sh" "$requested" >/dev/null 2>&1 \
        || [ -e "$requested" ]; then
        bad "phase-b harness ignores caller-controlled TMPDIR"
    else
        ok "phase-b harness ignores caller-controlled TMPDIR"
    fi
done
rm -rf "$fake_workspace_tmp" "$fake_home_tmp"

batch_root="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-batch.XXXXXX")"
mkdir -p "$batch_root/one/.exocortex"
bash "$TEMPLATE_DIR/scripts/update-all-repos.sh" "$batch_root" --dry-run >/dev/null && ok "batch updater inventory is read-only" || bad "batch updater inventory is read-only"
if bash "$TEMPLATE_DIR/scripts/update-all-repos.sh" "$batch_root" --yes >/dev/null 2>&1; then bad "batch live mutation denied"; else ok "batch live mutation denied"; fi
rm -rf "$batch_root"

if rg -n 'curl|urllib\.request|requests\.|mcp_' "$TEMPLATE_DIR/.exocortex/scripts" \
    --glob '!egress_guard.py' --glob '!**/tests/**' >/dev/null; then
    bad "legacy scripts contain no direct network/provider path"
else
    ok "legacy scripts contain no direct network/provider path"
fi

install_target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$install_target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
if privacy_scan "$install_target" tree "$privacy_fingerprint"; then
    ok "fresh install contains no private Phase B evidence"
else
    bad "fresh install contains no private Phase B evidence"
fi
rm -rf "$install_target" "$fake_home"

source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
cat "$privacy_fingerprint" >> "$source_copy/README.md"
if privacy_scan "$source_copy" checksums "$privacy_fingerprint"; then
    bad "candidate privacy scan rejects injected fingerprint"
else
    ok "candidate privacy scan rejects injected fingerprint"
fi
rm -rf "$source_copy"

install_target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$install_target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
cat "$privacy_fingerprint" >> "$install_target/AI_START_HERE.md"
if privacy_scan "$install_target" tree "$privacy_fingerprint"; then
    bad "installed-output privacy scan rejects injected fingerprint"
else
    ok "installed-output privacy scan rejects injected fingerprint"
fi
rm -rf "$install_target" "$fake_home"

source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -Rp "$TEMPLATE_DIR/." "$source_copy/"
mkdir -p "$source_copy/.exocortex/planning"
cp "$privacy_fingerprint" "$source_copy/.exocortex/planning/private-fixture.txt"
install_target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
if privacy_scan "$source_copy" checksums "$privacy_fingerprint" \
    && run_install "$install_target" "$source_copy" "$fake_home" >/dev/null \
    && [ ! -e "$install_target/.exocortex/planning/private-fixture.txt" ]; then
    ok "protected planning fingerprint is excluded from public install"
else
    bad "protected planning fingerprint is excluded from public install"
fi
rm -rf "$source_copy" "$install_target" "$fake_home"

if [ "$privacy_fingerprint_owned" = true ]; then
    rm -f "$privacy_fingerprint"
fi

if PYTHONDONTWRITEBYTECODE=1 python3 "$TEMPLATE_DIR/tests/test_documentation_contract.py" "$TEMPLATE_DIR"; then
    ok "active installation documentation contract"
else
    bad "active installation documentation contract"
fi

docs_negative_base="$(mktemp -d "${TMPDIR:-/tmp}/exo-doc-contract-base.XXXXXX")"
while IFS='  ' read -r _ rel; do
    [ -n "$rel" ] || continue
    mkdir -p "$docs_negative_base/$(dirname "$rel")"
    cp "$TEMPLATE_DIR/$rel" "$docs_negative_base/$rel"
done < "$TEMPLATE_DIR/SHA256SUMS"
cp "$TEMPLATE_DIR/SHA256SUMS" "$docs_negative_base/SHA256SUMS"

expect_docs_contract_failure() {
    label="$1"
    relative="$2"
    mutation="$3"
    expected="$4"
    docs_negative="$(mktemp -d "${TMPDIR:-/tmp}/exo-doc-contract-negative.XXXXXX")"
    cp -R "$docs_negative_base/." "$docs_negative/"
    printf '\n%b\n' "$mutation" >> "$docs_negative/$relative"
    if PYTHONDONTWRITEBYTECODE=1 python3 \
        "$docs_negative/tests/test_documentation_contract.py" \
        "$docs_negative" >"$docs_negative/result.log" 2>&1; then
        bad "$label"
    elif grep -Fq "$expected" "$docs_negative/result.log"; then
        ok "$label"
    else
        bad "$label"
    fi
    rm -rf "$docs_negative"
}

expect_docs_contract_failure \
    "documentation contract rejects legacy copy guidance" \
    ".exocortex/README.md" \
    'cp templates/* .exocortex/' \
    '.exocortex/README.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects credential-shaped guidance" \
    ".exocortex/README.md" \
    'OPENAI_API_KEY=sk-fixture-only' \
    '.exocortex/README.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects remote pipe guidance" \
    "SECURITY.md" \
    '`curl | bash` is convenient.' \
    'SECURITY.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects stale fixed test count" \
    "CONTRIBUTING.md" \
    'All 8 tests must pass.' \
    'CONTRIBUTING.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects stale dependency baseline" \
    "CONTRIBUTING.md" \
    'Do not add external runtime dependencies beyond git and bash.' \
    'CONTRIBUTING.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects full-suite hook overclaim" \
    "CONTRIBUTING.md" \
    'The hook runs the full test suite.' \
    'CONTRIBUTING.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects save-as-checkpoint guidance" \
    ".exocortex/control/README.md" \
    'Use /save to checkpoint your work state.' \
    '.exocortex/control/README.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects stale relative links" \
    ".exocortex/docs/user-guide.md" \
    'See the root `README.md` and `UPGRADE_MANIFEST.md`.' \
    '.exocortex/docs/user-guide.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects stale command-registry claim" \
    "WHATSNEW.md" \
    'The canonical command JSON files remain unchanged.' \
    'WHATSNEW.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects native Windows support claim" \
    "README.md" \
    'Native Windows is supported.' \
    'README.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects bare-yes authority" \
    ".exocortex/docs/AI_INSTALLATION.md" \
    'A bare yes authorizes installation and push.' \
    '.exocortex/docs/AI_INSTALLATION.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects bundled Git authority" \
    ".exocortex/docs/AI_INSTALLATION.md" \
    'Installation includes commit and push.' \
    '.exocortex/docs/AI_INSTALLATION.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects transaction-exclusion overclaim" \
    ".exocortex/docs/AI_INSTALLATION.md" \
    'Confirm that capability and transaction paths were excluded.' \
    '.exocortex/docs/AI_INSTALLATION.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects automatic handoff write" \
    ".exocortex/docs/AI_INSTALLATION.md" \
    'After install, write a handoff.' \
    '.exocortex/docs/AI_INSTALLATION.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects wrong clean-install gate" \
    ".exocortex/docs/AI_INSTALLATION.md" \
    'Stop and ask for my exact local-install approval.' \
    '.exocortex/docs/AI_INSTALLATION.md: forbidden'
expect_docs_contract_failure \
    "documentation contract rejects broken inline link" \
    "README.md" \
    '[missing inline](docs/does-not-exist.md)' \
    'README.md: broken local link: docs/does-not-exist.md'
expect_docs_contract_failure \
    "documentation contract rejects broken reference link" \
    "README.md" \
    '[missing reference][missing-doc]\n\n[missing-doc]: docs/also-missing.md' \
    'README.md: broken local link: docs/also-missing.md'

rm -rf "$docs_negative_base"

finish_suite
