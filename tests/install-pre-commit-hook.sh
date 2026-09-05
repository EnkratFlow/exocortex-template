#!/bin/bash
# Install the Exocortex pre-commit hook or run its shared staged checks.
#
#   bash tests/install-pre-commit-hook.sh
#   bash tests/install-pre-commit-hook.sh --run-staged-checks
#
# This is developer convenience, not publication evidence or authority. The
# guarded publisher never executes this candidate-owned runner and never
# installs or modifies a shared Git hook. Child checks receive a fixed,
# allowlisted environment with ambient tokens and user configuration omitted;
# this reduces accidental disclosure but is not an OS or network sandbox.

set -eu

SAFE_PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"
ENV_BIN="/usr/bin/env"
[ -x "$ENV_BIN" ] || {
    echo "A fixed /usr/bin/env is required for sterile staged checks." >&2
    exit 1
}

find_host_command() {
    local name="$1" candidate
    for candidate in \
        "/usr/bin/$name" "/bin/$name" "/usr/sbin/$name" "/sbin/$name" \
        "/usr/local/bin/$name" "/opt/homebrew/bin/$name"
    do
        if [ -x "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

HOST_BASH="$(find_host_command bash)" || {
    echo "bash is required for staged checks." >&2
    exit 1
}
HOST_GIT="$(find_host_command git)" || {
    echo "git is required for staged checks." >&2
    exit 1
}
HOST_PYTHON="$(find_host_command python3)" || {
    echo "python3 is required for staged checks." >&2
    exit 1
}

run_fixed() {
    "$ENV_BIN" -i \
        PATH="$SAFE_PATH" \
        HOME=/nonexistent \
        XDG_CONFIG_HOME=/nonexistent \
        TMPDIR=/tmp \
        LC_ALL=C LANG=C TZ=UTC \
        GIT_CONFIG_NOSYSTEM=1 \
        GIT_CONFIG_GLOBAL=/dev/null \
        GIT_TERMINAL_PROMPT=0 \
        PYTHONDONTWRITEBYTECODE=1 \
        PYTHONNOUSERSITE=1 \
        PYTHONSAFEPATH=1 \
        "$@"
}

SAFE_ENV_ROOT=""
HOOK_TEMP=""
cleanup() {
    if [ -n "$HOOK_TEMP" ]; then
        run_fixed rm -f -- "$HOOK_TEMP" >/dev/null 2>&1 || true
    fi
    case "$SAFE_ENV_ROOT" in
        /tmp/exocortex-hook-env.*)
            run_fixed rm -rf -- "$SAFE_ENV_ROOT" >/dev/null 2>&1 || true
            ;;
    esac
}
trap cleanup EXIT

SAFE_ENV_ROOT="$(run_fixed mktemp -d /tmp/exocortex-hook-env.XXXXXX)" || {
    echo "A private environment for staged checks could not be created." >&2
    exit 1
}
SAFE_HOME="$SAFE_ENV_ROOT/home"
SAFE_TMP="$SAFE_ENV_ROOT/tmp"
run_fixed mkdir -p "$SAFE_HOME" "$SAFE_TMP"
run_fixed chmod 0700 "$SAFE_ENV_ROOT" "$SAFE_HOME" "$SAFE_TMP"

run_clean() {
    "$ENV_BIN" -i \
        PATH="$SAFE_PATH" \
        HOME="$SAFE_HOME" \
        XDG_CONFIG_HOME="$SAFE_HOME/xdg" \
        TMPDIR="$SAFE_TMP" \
        LC_ALL=C LANG=C TZ=UTC \
        GIT_CONFIG_NOSYSTEM=1 \
        GIT_CONFIG_GLOBAL=/dev/null \
        GIT_TERMINAL_PROMPT=0 \
        PYTHONDONTWRITEBYTECODE=1 \
        PYTHONNOUSERSITE=1 \
        PYTHONSAFEPATH=1 \
        "$@"
}

run_git() {
    run_clean "$HOST_GIT" \
        -c core.fsmonitor=false \
        -c core.hooksPath=/dev/null \
        -c credential.helper= \
        -c core.askPass= \
        "$@"
}

REPO_ROOT="$(run_git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "Not inside a Git repository. Run from the exocortex-template root." >&2
    exit 1
}
INDEX_FILE=""
INDEX_ROOT=""

run_index_git() {
    [ -n "$INDEX_FILE" ] || {
        echo "The staged index snapshot is unavailable." >&2
        return 1
    }
    run_clean "$ENV_BIN" \
        GIT_INDEX_FILE="$INDEX_FILE" \
        GIT_NO_REPLACE_OBJECTS=1 \
        "$HOST_GIT" \
        -c core.fsmonitor=false \
        -c core.hooksPath=/dev/null \
        -c credential.helper= \
        -c core.askPass= \
        -C "$REPO_ROOT" \
        "$@"
}

freeze_index() {
    local source_index="$1" destination_index="$2"
    run_clean "$HOST_PYTHON" -I - "$source_index" "$destination_index" <<'PY'
import os
import stat
import sys
from pathlib import Path

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
nofollow = getattr(os, "O_NOFOLLOW", 0)
if not nofollow:
    raise SystemExit("secure index snapshotting is unavailable")

source_fd = None
destination_fd = None
try:
    before = os.stat(source, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 64 * 1024 * 1024:
        raise OSError
    source_fd = os.open(source, os.O_RDONLY | nofollow)
    opened = os.fstat(source_fd)
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    ):
        raise OSError
    destination_fd = os.open(
        destination,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
        0o600,
    )
    copied = 0
    while True:
        chunk = os.read(source_fd, 1024 * 1024)
        if not chunk:
            break
        copied += len(chunk)
        if copied > 64 * 1024 * 1024:
            raise OSError
        view = memoryview(chunk)
        while view:
            written = os.write(destination_fd, view)
            if written <= 0:
                raise OSError
            view = view[written:]
    os.fsync(destination_fd)
    after_fd = os.fstat(source_fd)
    after_path = os.stat(source, follow_symlinks=False)
    stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
    if copied != before.st_size or any(
        (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns) != stable
        for value in (after_fd, after_path)
    ):
        raise OSError
except OSError as exc:
    raise SystemExit("Git index could not be frozen safely") from exc
finally:
    if destination_fd is not None:
        os.close(destination_fd)
    if source_fd is not None:
        os.close(source_fd)
PY
}

materialize_index() {
    run_clean "$HOST_PYTHON" -I - \
        "$REPO_ROOT" "$INDEX_ROOT" "$HOST_GIT" "$INDEX_FILE" <<'PY'
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1]).resolve(strict=True)
destination = Path(sys.argv[2]).resolve(strict=True)
git_bin = sys.argv[3]
index_file = Path(sys.argv[4]).resolve(strict=True)
max_listing_bytes = 8 * 1024 * 1024
max_source_file_bytes = 64 * 1024 * 1024
max_entries = 10000
approved_credential_blobs = {
    ".exocortex/.env.example": {
        "mode": "100644",
        "sha1": "11dc64a1a9e6fab6608e1c7360f884d888279ad8",
    },
    ".exocortex/key-registry.json": {
        "mode": "100644",
        "sha1": "22d5d4ecf108933f28016d95fdcdb74cc6ee4df9",
    },
}
nofollow = getattr(os, "O_NOFOLLOW", 0)
if not nofollow:
    raise SystemExit("secure staged-tree materialization is unavailable")

environment = os.environ.copy()
environment.update(
    {
        "GIT_INDEX_FILE": str(index_file),
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
    }
)
git = [
    git_bin,
    "-c", "core.fsmonitor=false",
    "-c", "core.hooksPath=/dev/null",
    "-c", "credential.helper=",
    "-c", "core.askPass=",
    "-C", str(root),
]

def git_output(*arguments):
    result = subprocess.run(
        [*git, *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        check=False,
    )
    if result.returncode:
        raise SystemExit("staged Git metadata could not be inspected")
    return result.stdout

def credential_shaped(relative):
    parts = [part.casefold() for part in PurePosixPath(relative).parts]
    basename = parts[-1]
    return (
        basename in {
            ".env", ".envrc", "credentials", "credentials.json",
            "id_dsa", "id_ecdsa", "id_ed25519", "id_rsa",
            "key-registry.json", "secrets.json",
        }
        or basename.startswith(".env.")
        or basename.endswith((".jks", ".key", ".keystore", ".p12", ".pem", ".pfx"))
        or any(part in {".aws", ".ssh", "credentials", "secrets"} for part in parts)
    )

object_format = git_output("rev-parse", "--show-object-format").decode("ascii").strip()
if object_format != "sha1":
    raise SystemExit("credential-blind staged checks currently require a SHA-1 Git object store")

listing = git_output("ls-files", "--stage", "-z")
if not listing or len(listing) > max_listing_bytes:
    raise SystemExit("staged index is empty or exceeds the supported size")

records = []
seen = set()
seen_folded = set()
for encoded in listing.split(b"\0"):
    if not encoded:
        continue
    try:
        metadata, raw_path = encoded.split(b"\t", 1)
        mode, object_id, stage = metadata.decode("ascii").split(" ")
        relative = raw_path.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as exc:
        raise SystemExit("staged index contains malformed metadata") from exc
    path = PurePosixPath(relative)
    folded = relative.casefold()
    if (
        not relative
        or len(raw_path) > 4096
        or path.is_absolute()
        or str(path) != relative
        or "\\" in relative
        or any(ord(character) < 32 or ord(character) == 127 for character in relative)
        or any(character in relative for character in "*?[]")
        or any(part in {"", ".", ".."} or part.casefold() == ".git" for part in path.parts)
        or relative in seen
        or folded in seen_folded
        or stage != "0"
        or mode not in {"100644", "100755"}
        or re.fullmatch(r"[0-9a-f]{40}", object_id) is None
    ):
        raise SystemExit("staged index contains an unsafe, duplicate, conflicted, or unsupported entry")
    seen.add(relative)
    seen_folded.add(folded)
    if credential_shaped(relative):
        approved = approved_credential_blobs.get(relative)
        if approved is None or approved["mode"] != mode or approved[object_format] != object_id:
            raise SystemExit("staged index contains an unapproved credential-shaped entry")
        # Preserve only its authenticated presence and mode. Never request or
        # materialize the credential-adjacent blob bytes.
        records.append((relative, mode, object_id, True))
    else:
        records.append((relative, mode, object_id, False))
    if len(records) > max_entries:
        raise SystemExit("staged index contains too many entries")

batch = subprocess.Popen(
    [*git, "cat-file", "--batch"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=environment,
)
try:
    assert batch.stdin is not None and batch.stdout is not None
    for relative, mode, object_id, credential_adjacent in records:
        target = destination / relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if credential_adjacent:
            descriptor = os.open(
                target,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
                0o600,
            )
            os.close(descriptor)
            os.chmod(target, int(mode[-3:], 8), follow_symlinks=False)
            continue

        batch.stdin.write((object_id + "\n").encode("ascii"))
        batch.stdin.flush()
        header = batch.stdout.readline(256)
        match = re.fullmatch(
            rb"([0-9a-f]{40}) blob ([0-9]+)\n",
            header,
        )
        if match is None or match.group(1).decode("ascii") != object_id:
            raise OSError
        size = int(match.group(2))
        if size > max_source_file_bytes:
            raise OSError
        descriptor = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
            0o600,
        )
        try:
            remaining = size
            while remaining:
                chunk = batch.stdout.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise OSError
                view = memoryview(chunk)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError
                    view = view[written:]
                remaining -= len(chunk)
            if batch.stdout.read(1) != b"\n":
                raise OSError
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.chmod(target, int(mode[-3:], 8), follow_symlinks=False)
    batch.stdin.close()
    if batch.wait() != 0:
        raise OSError
except (OSError, BrokenPipeError) as exc:
    batch.kill()
    batch.wait()
    raise SystemExit("staged blob could not be materialized safely") from exc
finally:
    if batch.stdin is not None and not batch.stdin.closed:
        batch.stdin.close()
    if batch.stdout is not None:
        batch.stdout.close()
    if batch.stderr is not None:
        batch.stderr.close()
PY
}

prepare_index_snapshot() {
    local source_index
    source_index="$(run_git rev-parse --git-path index 2>/dev/null)" || {
        echo "Git index path could not be resolved." >&2
        return 1
    }
    case "$source_index" in
        /*) ;;
        *) source_index="$REPO_ROOT/$source_index" ;;
    esac
    INDEX_FILE="$SAFE_ENV_ROOT/index"
    INDEX_ROOT="$SAFE_ENV_ROOT/index-tree"
    freeze_index "$source_index" "$INDEX_FILE" || return 1
    run_clean mkdir -m 0700 "$INDEX_ROOT" || return 1
    materialize_index || return 1
}

verify_checksums() {
    local root="$1"
    run_clean "$HOST_PYTHON" -I - "$root" <<'PY'
import hashlib
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1]).resolve(strict=True)
line_re = re.compile(r"^([a-f0-9]{64})  ([^\r\n]+)$")
max_manifest_bytes = 128 * 1024
max_source_file_bytes = 64 * 1024 * 1024
approved_credential_adjacent = {
    ".exocortex/.env.example": "f7b31458dd5095a7fe2d07d093dc7c0e9702d3693faa76af4addad88168601bf",
    ".exocortex/key-registry.json": "b1d352104c6479f87ca9040ab2ae0558c8d82bcc0df452cd7a2bdea2faaea7d7",
}
nofollow = getattr(os, "O_NOFOLLOW", 0)
directory = getattr(os, "O_DIRECTORY", 0)
if not nofollow or not directory:
    raise SystemExit("secure checksum verification is unavailable")

def credential_shaped(relative):
    parts = [part.casefold() for part in PurePosixPath(relative).parts]
    basename = parts[-1]
    return (
        basename in {
            ".env", ".envrc", "credentials", "credentials.json",
            "id_dsa", "id_ecdsa", "id_ed25519", "id_rsa",
            "key-registry.json", "secrets.json",
        }
        or basename.startswith(".env.")
        or basename.endswith((".jks", ".key", ".keystore", ".p12", ".pem", ".pfx"))
        or any(part in {".aws", ".ssh", "credentials", "secrets"} for part in parts)
    )

def read_regular(relative, maximum):
    parts = PurePosixPath(relative).parts
    descriptors = []
    final = None
    try:
        current = os.open(root, os.O_RDONLY | directory | nofollow)
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=current)
            descriptors.append(current)
        before = os.stat(parts[-1], dir_fd=current, follow_symlinks=False)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size > maximum
        ):
            raise OSError
        final = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=current)
        value = os.fstat(final)
        if (
            not stat.S_ISREG(value.st_mode)
            or value.st_nlink != 1
            or value.st_size > maximum
            or (value.st_dev, value.st_ino, value.st_size) !=
               (before.st_dev, before.st_ino, before.st_size)
        ):
            raise OSError
        chunks = []
        total = 0
        while True:
            chunk = os.read(final, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                raise OSError
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError as exc:
        raise SystemExit("checksum inventory contains an unsafe, oversized, or missing file") from exc
    finally:
        if final is not None:
            os.close(final)
        for descriptor in reversed(descriptors):
            os.close(descriptor)

try:
    manifest = read_regular("SHA256SUMS", max_manifest_bytes).decode("utf-8")
except UnicodeDecodeError as exc:
    raise SystemExit("checksum inventory is not valid UTF-8") from exc
paths = []
seen = set()
for line in manifest.splitlines():
    match = line_re.fullmatch(line)
    if match is None:
        raise SystemExit("checksum inventory contains a malformed entry")
    expected, raw = match.groups()
    path = PurePosixPath(raw)
    if (
        not raw
        or "\\" in raw
        or any(char in raw for char in "*?[]")
        or path.is_absolute()
        or ".." in path.parts
        or any(part.casefold() == ".git" for part in path.parts)
        or raw == "SHA256SUMS"
        or raw in seen
    ):
        raise SystemExit("checksum inventory contains an unsafe or duplicate path")
    if credential_shaped(raw):
        # These two public fixtures are intentionally listed by the template.
        # Compare only their fixed approved digests: never open their paths.
        # Every other credential-shaped entry fails before path traversal.
        if approved_credential_adjacent.get(raw) != expected:
            raise SystemExit("checksum inventory contains a credential-shaped path")
    elif hashlib.sha256(read_regular(raw, max_source_file_bytes)).hexdigest() != expected:
        raise SystemExit("checksum inventory does not match the public source")
    seen.add(raw)
    paths.append(raw)
if not paths or paths != sorted(paths):
    raise SystemExit("checksum inventory is empty or unsorted")
PY
}

run_staged_checks() {
    local changed result path docs_only event_only tests_dir
    prepare_index_snapshot || return 1
    tests_dir="$INDEX_ROOT/tests"
    [ -f "$tests_dir/run_tests.sh" ] || {
        echo "The staged tests/run_tests.sh is required; staged checks fail closed." >&2
        return 1
    }
    changed="$(run_index_git diff --cached --name-only --no-ext-diff --no-textconv 2>/dev/null)" || {
        echo "Staged paths could not be inspected" >&2
        return 1
    }
    [ -n "$changed" ] || {
        echo "No staged paths were present" >&2
        return 1
    }

    docs_only=true
    event_only=true
    while IFS= read -r path; do
        case "$path" in
            *.md|SHA256SUMS|FILEMODES|VERSION|LICENSE) ;;
            *) docs_only=false ;;
        esac
        case "$path" in
            *.md|SHA256SUMS|FILEMODES|VERSION|LICENSE|\
            .exocortex/scripts/create_event.sh|\
            .exocortex/scripts/read_memory_stack.sh|\
            .exocortex/scripts/generate_context.sh|\
            .exocortex/scripts/tests/test_event_tooling.sh) ;;
            *) event_only=false ;;
        esac
    done <<EOF
$changed
EOF

    echo ""
    if [ "$docs_only" = true ]; then
        echo "Exocortex: quick documentation and integrity checks..."
        run_clean "$HOST_PYTHON" -I "$INDEX_ROOT/tests/test_documentation_contract.py" "$INDEX_ROOT" \
          && run_clean "$HOST_PYTHON" -I "$INDEX_ROOT/.exocortex/scripts/generate_command_adapters.py" --check \
          && verify_checksums "$INDEX_ROOT" \
          && run_index_git diff --cached --check --no-ext-diff --no-textconv
    elif [ "$event_only" = true ]; then
        echo "Exocortex: focused event/memory checks and quick contracts..."
        run_clean "$HOST_BASH" "$INDEX_ROOT/.exocortex/scripts/tests/test_event_tooling.sh" \
          && run_clean "$HOST_PYTHON" -I "$INDEX_ROOT/tests/test_documentation_contract.py" "$INDEX_ROOT" \
          && run_clean "$HOST_PYTHON" -I "$INDEX_ROOT/.exocortex/scripts/generate_command_adapters.py" --check \
          && verify_checksums "$INDEX_ROOT" \
          && run_index_git diff --cached --check --no-ext-diff --no-textconv
    else
        echo "Exocortex: affected deterministic suite..."
        run_clean "$HOST_BASH" "$tests_dir/run_tests.sh" \
          && run_clean "$HOST_PYTHON" -I "$INDEX_ROOT/.exocortex/scripts/generate_command_adapters.py" --check \
          && verify_checksums "$INDEX_ROOT" \
          && run_index_git diff --cached --check --no-ext-diff --no-textconv
    fi
    result=$?

    if [ "$result" -ne 0 ]; then
        echo "Checks failed; commit blocked." >&2
        return "$result"
    fi
    echo "Right-sized staged checks passed."
}

case "${1:-}" in
    --run-staged-checks)
        [ "$#" -eq 1 ] || {
            echo "--run-staged-checks accepts no additional arguments" >&2
            exit 2
        }
        run_staged_checks
        exit $?
        ;;
    "")
        ;;
    *)
        echo "Unknown argument" >&2
        exit 2
        ;;
esac

HOOK_FILE="$(run_clean "$HOST_GIT" rev-parse --git-path hooks/pre-commit)"
case "$HOOK_FILE" in /*) ;; *) HOOK_FILE="$REPO_ROOT/$HOOK_FILE" ;; esac
GIT_DIR="$(run_git rev-parse --absolute-git-dir)"
GIT_COMMON_DIR="$(run_git rev-parse --git-common-dir)"
case "$GIT_COMMON_DIR" in /*) ;; *) GIT_COMMON_DIR="$REPO_ROOT/$GIT_COMMON_DIR" ;; esac
if [ "$(cd "$GIT_DIR" && pwd -P)" != "$(cd "$GIT_COMMON_DIR" && pwd -P)" ]; then
    echo "Refusing to install a shared hook from a linked worktree." >&2
    exit 1
fi
HOOK_DIR="${HOOK_FILE%/*}"
[ ! -L "$HOOK_DIR" ] || {
    echo "Refusing a symlinked hooks directory." >&2
    exit 1
}
run_clean mkdir -p "$HOOK_DIR"
if [ -e "$HOOK_FILE" ] || [ -L "$HOOK_FILE" ]; then
    echo "Refusing to overwrite an existing pre-commit hook." >&2
    exit 1
fi
HOOK_TEMP="$(run_clean mktemp "$HOOK_DIR/.exocortex-pre-commit.XXXXXX")"

run_clean cat > "$HOOK_TEMP" << 'HOOK'
#!/bin/sh
# Developer-only Exocortex check. It supplies no publication authority or
# attestation and deliberately forwards no ambient token or user-config state.
set -eu
SAFE_PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin"
exec /usr/bin/env -i \
    PATH="$SAFE_PATH" HOME=/nonexistent XDG_CONFIG_HOME=/nonexistent TMPDIR=/tmp \
    LC_ALL=C LANG=C TZ=UTC \
    GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null GIT_TERMINAL_PROMPT=0 \
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 PYTHONSAFEPATH=1 \
    bash -c '
        set -eu
        REPO_ROOT="$(git -c core.fsmonitor=false -c core.hooksPath=/dev/null rev-parse --show-toplevel)"
        exec bash "$REPO_ROOT/tests/install-pre-commit-hook.sh" --run-staged-checks
    '
HOOK

run_clean chmod 0700 "$HOOK_TEMP"
if ! run_clean ln "$HOOK_TEMP" "$HOOK_FILE"; then
    echo "Pre-commit hook appeared concurrently; nothing was overwritten." >&2
    exit 1
fi
run_clean rm -f "$HOOK_TEMP"
HOOK_TEMP=""

echo "Pre-commit hook installed at $HOOK_FILE"
echo "Guarded publication never invokes this candidate-owned hook runner."
