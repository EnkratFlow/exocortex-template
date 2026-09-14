#!/bin/bash
set -u
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=helpers.sh
source "$TEST_DIR/helpers.sh"

tree_digest() {
    python3 - "$1" <<'PY'
import hashlib, os, sys
from pathlib import Path
root=Path(sys.argv[1])
h=hashlib.sha256()
for base, dirs, files in os.walk(root):
    dirs[:]=sorted(d for d in dirs if d != '.git')
    for name in sorted(files):
        p=Path(base)/name
        rel=p.relative_to(root).as_posix()
        h.update(rel.encode()+b'\0'+hashlib.sha256(p.read_bytes()).digest())
print(h.hexdigest())
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
    umask 077
    printf 'private-fixture-%s-%s\n' "$$" "$(date -u +%s)" > "$privacy_fingerprint"
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
cp -R "$TEMPLATE_DIR/." "$source_copy/"
approved_before="$(hash_file "$TEMPLATE_DIR/SHA256SUMS")"
printf '\nchanged candidate\n' >> "$source_copy/AI_START_HERE.md"
changed_hash="$(hash_file "$source_copy/AI_START_HERE.md")"
awk -v h="$changed_hash" 'BEGIN{OFS="  "} $2=="AI_START_HERE.md"{$1=h} {print $1,$2}' "$source_copy/SHA256SUMS" > "$source_copy/SHA256SUMS.tmp"
mv "$source_copy/SHA256SUMS.tmp" "$source_copy/SHA256SUMS"
expect_install_denial "altered source with self-consistent sums fails approved candidate digest" "$source_copy" "$approved_before"
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

target="$(new_target)"
fake_home="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-home.XXXXXX")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
assert_file "canonical entry installed" "$target/AI_START_HERE.md"
assert_file "Codex adapter installed" "$target/AGENTS.md"
assert_file "executor registry generated" "$target/.exocortex/control/EXECUTOR_REGISTRY.json"
assert_file "deny policy generated" "$target/.exocortex/control/EXTERNAL_SYNC_POLICY.json"
assert_dir "protocol state generated" "$target/.exocortex/local/protocol"
assert_contains "registry defaults read-only" "$target/.exocortex/control/EXECUTOR_REGISTRY.json" '"default_role": "read_only"'
assert_contains "policy defaults deny" "$target/.exocortex/control/EXTERNAL_SYNC_POLICY.json" '"default": "deny"'
assert_not_contains "registry absent from manifest" "$target/.exocortex/.install-manifest" 'EXECUTOR_REGISTRY.json'
assert_not_contains "policy absent from manifest" "$target/.exocortex/.install-manifest" 'EXTERNAL_SYNC_POLICY.json'
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

first="$(tree_digest "$target")"
run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
second="$(tree_digest "$target")"
[ "$first" = "$second" ] && ok "install is idempotent" || bad "install is idempotent"
rm -rf "$target" "$fake_home"

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
unknown = '.cursor/skills/onboard/SKILL.md'
records = {}
managed = []
for index, item in enumerate(matrix['legacy_retirements']):
    rel = item['path']
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'pre-c1 adapter {index:02d}\n', encoding='utf-8')
    if rel == unknown:
        path.write_text('unknown pre-c1 onboard adapter\n', encoding='utf-8')
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    records[rel] = digest
    if rel == custom:
        path.write_text(path.read_text(encoding='utf-8') + 'user customization\n', encoding='utf-8')
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
    'unknown': unknown,
}) + '\n', encoding='utf-8')
PY
pre_c1_log="$(mktemp "${TMPDIR:-/tmp}/exo-test-pre-c1-migration.XXXXXX")"
if run_install "$target" "$TEMPLATE_DIR" "$fake_home" > "$pre_c1_log" 2>&1 \
    && grep -Fq 'EXOCORTEX_ADAPTER_COLLISION_PRESERVED: .cursor/commands/work.md' "$pre_c1_log" \
    && grep -Fq 'EXOCORTEX_ADAPTER_COLLISION_PRESERVED: .cursor/skills/onboard/SKILL.md' "$pre_c1_log" \
    && python3 - "$target" "$pre_c1_meta" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
meta = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
if any((root / rel).exists() for rel in meta['managed']):
    raise SystemExit(1)
if 'user customization' not in (root / meta['custom']).read_text(encoding='utf-8'):
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
PY
then
    pre_c1_first="$(tree_digest "$target")"
    run_install "$target" "$TEMPLATE_DIR" "$fake_home" >/dev/null
    pre_c1_second="$(tree_digest "$target")"
    if [ "$pre_c1_first" = "$pre_c1_second" ]; then
        ok "direct pre-C1 update retires managed paths and preserves customized and unknown collisions idempotently"
    else
        bad "direct pre-C1 update retires managed paths and preserves customized and unknown collisions idempotently"
    fi
else
    bad "direct pre-C1 update retires managed paths and preserves customized and unknown collisions idempotently"
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
    cp -R "$TEMPLATE_DIR/." "$source_copy/"
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

if grep -E '(^|/)(__pycache__/|[^/]+\.py[co]$)' "$TEMPLATE_DIR/SHA256SUMS" >/dev/null; then
    bad "checksum inventory excludes generated bytecode"
else
    ok "checksum inventory excludes generated bytecode"
fi

source_copy="$(mktemp -d "${TMPDIR:-/tmp}/exo-test-source.XXXXXX")"
cp -R "$TEMPLATE_DIR/." "$source_copy/"
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
[ -n "$(find "$backup" -type f -name '*.tar.gz' -print -quit)" ] && ok "safe-update creates explicit restore archive" || bad "safe-update creates explicit restore archive"
rm -rf "$target" "$fake_home" "$backup"
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
    cp -R "$TEMPLATE_DIR/." "$source/"
    printf '\nOLD_TEMPLATE_FIXTURE\n' >> "$source/.exocortex/COMMAND_SYSTEM.md"
    old_hash="$(hash_file "$source/.exocortex/COMMAND_SYSTEM.md")"
    awk -v h="$old_hash" 'BEGIN{OFS="  "} $2==".exocortex/COMMAND_SYSTEM.md"{$1=h} {print $1,$2}' "$source/SHA256SUMS" > "$source/SHA256SUMS.tmp"
    mv "$source/SHA256SUMS.tmp" "$source/SHA256SUMS"
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
    printf 'CONCURRENT_PROTECTED_CHANGE\n' >> "$target/.exocortex/TODO.md"
    : > "$barrier_root/gate.continue"
fi
wait "$race_pid"
race_rc=$?
if [ "$race_rc" -ne 0 ] \
    && grep -Eq 'live target changed after rehearsal|protected target data changed after rehearsal' "$race_log" \
    && grep -Fq 'OLD_TEMPLATE_FIXTURE' "$target/.exocortex/COMMAND_SYSTEM.md" \
    && grep -Fq '"state": "active"' "$target/.exocortex/local/protocol/capabilities/update-race.json"; then
    ok "safe-update denies target race before capability consumption"
else
    bad "safe-update denies target race before capability consumption"
fi
rm -rf "$old_source" "$target" "$fake_home" "$backup" "$race_probe_backup" "$barrier_root"

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
cp -R "$TEMPLATE_DIR/." "$source_copy/"
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
cp -R "$TEMPLATE_DIR/." "$source_copy/"
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
