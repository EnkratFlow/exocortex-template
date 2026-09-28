#!/usr/bin/env python3
"""Publish one complete local event, then refresh the generated context.

Exit 3 means the event was saved but its refresh failed: repair the refresh,
never repeat the save. This helper grants no lifecycle or external authority.
"""
from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
import refresh_rollups as memory


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                            timeout=20, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0"))
    return result.stdout.strip() if result.returncode == 0 else "(unavailable)"


def record(root: Path, body: str) -> Path:
    if not body.strip():
        raise memory.MemoryError("event body is empty")
    folder = memory.safe_path(root, ".exocortex/events")
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    machine = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(platform.system(), "unknown")
    editor = "cursor" if os.environ.get("CURSOR_TRACE_ID") or os.environ.get("CURSOR_SESSION") else "unknown"
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    content = (f"<!-- Event Metadata -->\ntimestamp: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
               f"machine: {machine}\neditor: {editor}\nproject: {root.name}\nbranch: {branch}\n\n---\n\n"
               f"{body.rstrip()}\n\n## Git State\n\n**Last Commits:**\n{git(root, 'log', '--oneline', '-5')}\n\n"
               f"**Branch:** {branch}\n\n**Uncommitted Changes:**\n```\n{git(root, 'status', '--short')}\n```\n\n"
               f"**Diff Stats:**\n```\n{git(root, 'diff', '--stat')}\n```\n")
    descriptor, temporary = tempfile.mkstemp(prefix=".event-", dir=folder)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content.encode())
            handle.flush()
            os.fsync(handle.fileno())
        base = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_{machine}-{editor}"
        for count in range(10000):
            suffix = f"_{count:02d}" if count else ""
            path = folder / f"{base}{suffix}.md"
            try:
                os.link(temporary, path)
                return path
            except FileExistsError:
                continue
        raise memory.MemoryError("event name collision limit reached")
    finally:
        os.unlink(temporary)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    try:
        if args.body_file:
            name = args.body_file.name.casefold()
            if name.startswith(".env") or name in ("credentials", "secrets") or name.endswith((".pem", ".key", ".p12")):
                raise memory.MemoryError("credential-shaped body path refused")
            path = args.body_file.absolute()
            if path.is_symlink():
                raise memory.MemoryError("symlink body path refused")
            path = path.parent.resolve() / path.name
            memory.safe_path(Path(path.anchor), str(path.relative_to(path.anchor)))
            body = memory.decode(memory.read_bytes(path))
        elif not sys.stdin.isatty():
            raw = sys.stdin.buffer.read(memory.MAX_FILE + 1)
            if len(raw) > memory.MAX_FILE:
                raise memory.MemoryError("event body exceeds the read limit")
            body = memory.decode(raw)
        else:
            raise memory.MemoryError("provide content via stdin or --body-file")
        path = record(root, body)
    except (memory.MemoryError, OSError, subprocess.SubprocessError) as exc:
        print(f"EVENT_NOT_SAVED: {exc}", file=sys.stderr)
        return 1
    code = 0
    try:
        result = memory.apply(root)
        if result["status"] != "fresh":
            raise memory.MemoryError("event coverage changed during refresh")
        print("Event saved; generated context refreshed.")
    except (memory.MemoryError, OSError) as exc:
        print(f"EVENT_SAVED_REFRESH_FAILED: {exc}. Run refresh_rollups.py --apply; do not save this event again.", file=sys.stderr)
        code = 3
    print(path)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
