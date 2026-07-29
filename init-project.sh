#!/bin/bash
# Minimal project-local initializer. It never reads credentials, rewrites
# memory, installs packages, or changes editor/system state.

set -euo pipefail

PROJECT_NAME="${1:-$(basename "$PWD")}"
command -v python3 >/dev/null 2>&1 \
    || { echo "ERROR: python3 is required for non-following project initialization" >&2; exit 1; }

# Use lstat plus a private same-directory temporary file and no-replace
# publication so neither a symlinked .exocortex directory, a dangling leaf,
# restrictive umask, nor an interrupted write can expose a partial project
# name outside or at the canonical destination.
PYTHONDONTWRITEBYTECODE=1 python3 - "$PROJECT_NAME" "${HOME:-}" <<'PY'
import os
from pathlib import Path
import stat
import sys
import tempfile

project_name = sys.argv[1]
home_input = sys.argv[2]
test_fault = os.environ.get("EXOCORTEX_TEST_INIT_FAULT", "")
if test_fault:
    if os.environ.get("EXOCORTEX_TEST_MODE") != "1":
        raise SystemExit("ERROR: initializer fault injection requires explicit test mode")
    if test_fault not in {"write", "file-fsync", "directory-fsync"}:
        raise SystemExit("ERROR: unknown test-only initializer fault")
root = Path.cwd().resolve(strict=True)
if root == Path(root.anchor):
    raise SystemExit("ERROR: refusing to initialize filesystem root")
if home_input:
    home = Path(home_input)
    if home.is_dir() and root == home.resolve(strict=True):
        raise SystemExit("ERROR: refusing to initialize user home")

exocortex = root / ".exocortex"
try:
    exocortex_stat = os.lstat(exocortex)
except FileNotFoundError as exc:
    raise SystemExit("ERROR: .exocortex directory not found") from exc
if stat.S_ISLNK(exocortex_stat.st_mode) or not stat.S_ISDIR(exocortex_stat.st_mode):
    raise SystemExit("ERROR: .exocortex must be a real project-local directory")
if exocortex.resolve(strict=True) != root / ".exocortex":
    raise SystemExit("ERROR: .exocortex escapes the canonical project root")

target = exocortex / ".project-name"
try:
    target_stat = os.lstat(target)
except FileNotFoundError:
    target_stat = None
if target_stat is not None:
    if (
        stat.S_ISLNK(target_stat.st_mode)
        or not stat.S_ISREG(target_stat.st_mode)
        or target_stat.st_nlink != 1
    ):
        raise SystemExit("ERROR: .project-name must be a single-link regular file")
else:
    fd = None
    temp_path = None
    created_identity = None
    published = False
    try:
        fd, temp_name = tempfile.mkstemp(prefix=".project-name.tmp.", dir=exocortex)
        temp_path = Path(temp_name)
        opened = os.fstat(fd)
        created_identity = (opened.st_dev, opened.st_ino)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise OSError("project-name temporary file is not a single-link regular file")
        os.fchmod(fd, 0o644)
        payload = project_name.encode("utf-8") + b"\n"
        while payload:
            write_payload = payload[:1] if test_fault == "write" else payload
            written = os.write(fd, write_payload)
            if written <= 0:
                raise OSError("short project-name write")
            payload = payload[written:]
            if test_fault == "write":
                raise OSError("injected test-only project-name write failure")
        if test_fault == "file-fsync":
            raise OSError("injected test-only project-name file-fsync failure")
        os.fsync(fd)
        created = os.fstat(fd)
        if (
            not stat.S_ISREG(created.st_mode)
            or created.st_nlink != 1
            or stat.S_IMODE(created.st_mode) != 0o644
            or (created.st_dev, created.st_ino) != created_identity
        ):
            raise OSError("project-name creation failed its safety verification")
        os.close(fd)
        fd = None
        os.link(temp_path, target, follow_symlinks=False)
        published = True
        directory_fd = os.open(exocortex, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            if test_fault == "directory-fsync":
                raise OSError("injected test-only project-name directory-fsync failure")
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        os.unlink(temp_path)
        temp_path = None
        final = os.lstat(target)
        if (
            not stat.S_ISREG(final.st_mode)
            or final.st_nlink != 1
            or stat.S_IMODE(final.st_mode) != 0o644
            or (final.st_dev, final.st_ino) != created_identity
            or target.read_bytes() != project_name.encode("utf-8") + b"\n"
        ):
            raise OSError("published project-name failed its safety verification")
        directory_fd = os.open(exocortex, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        if fd is not None:
            os.close(fd)
        cleanup_changed = False
        if published and created_identity is not None:
            try:
                current = os.lstat(target)
            except FileNotFoundError:
                current = None
            if current is not None and (current.st_dev, current.st_ino) == created_identity:
                os.unlink(target)
                cleanup_changed = True
        if temp_path is not None and created_identity is not None:
            try:
                current = os.lstat(temp_path)
            except FileNotFoundError:
                current = None
            if current is not None and (current.st_dev, current.st_ino) == created_identity:
                os.unlink(temp_path)
                cleanup_changed = True
        if cleanup_changed:
            directory_fd = os.open(exocortex, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        raise
PY

# Installation applies each checksum-bound reviewed file mode. Initialization
# never normalizes or broadens permissions; byte-identical local mode choices
# and intentionally non-executable compatibility helpers remain untouched.

echo "Project-local initialization complete for: $PROJECT_NAME"
echo "Credentials, providers, packages, global editor state, services, and external sync: not accessed."
