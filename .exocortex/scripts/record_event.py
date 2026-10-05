#!/usr/bin/env python3
"""Publish one complete local event, then refresh the generated context.

Exit 3 means the event was saved but its refresh failed: repair the refresh,
never repeat the save. This helper grants no lifecycle or external authority.
"""
from __future__ import annotations

import argparse
import json
import uuid
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
import refresh_rollups as memory
import project_state
import brief_work
GIT_DEADLINE = 0.0


def git(root: Path, *args: str) -> str:
    remaining = GIT_DEADLINE - time.monotonic()
    if remaining <= 0:
        return "(unavailable: Git inspection time limit)"
    try:
        result = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false", "-C", str(root), *args], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=min(3, remaining),
                                env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0"))
    except (OSError, subprocess.TimeoutExpired):
        return "(unavailable: Git missing or timed out)"
    return result.stdout.strip() if result.returncode == 0 else "(unavailable)"


@project_state.bounded
def record(root: Path, body: str, *, brief_id=None, brief_sha=None, save_id=None, unscoped=False) -> Path:
    global GIT_DEADLINE
    GIT_DEADLINE = time.monotonic() + 10
    if not body.strip():
        raise memory.MemoryError("event body is empty")
    if unscoped and (brief_id or brief_sha):
        raise brief_work.BriefError('An unscoped save cannot name a brief')
    if bool(brief_id) != bool(brief_sha):
        raise brief_work.BriefError('An explicit brief save requires its exact SHA')
    event_id = str(uuid.UUID(save_id)) if save_id else str(uuid.uuid4())
    stable_path = memory.safe_path(root, f'.exocortex/events/event-{event_id}.md') if save_id else None

    def replay(expected_request=None):
        raw = memory.decode(memory.read_bytes(stable_path))
        header = raw.split('\n---', 1)[0]
        hashes = [line for line in header.splitlines() if line.startswith('event_sha256: ')]
        if len(hashes) != 1 or memory.digest(raw.replace(hashes[0]+'\n', '', 1).encode()) != hashes[0][14:]:
            raise memory.MemoryError('Saved event changed; preserve it and reconcile before retrying')
        stored_task = memory.brief_scope(raw) or None
        if (unscoped and stored_task or brief_id and
                (not stored_task or stored_task['id'] != brief_id or stored_task['sha256'] != brief_sha)):
            raise memory.MemoryError('Save ID belongs to a different task revision')
        requested = memory.digest(json.dumps({'body': body.rstrip(), 'brief': stored_task}, sort_keys=True).encode())
        if (expected_request and expected_request != requested or
                f'\nrequest_sha256: {requested}\n' not in header+'\n'):
            raise memory.MemoryError('Save ID already belongs to different content; inspect the original event')
        return stable_path

    # Retry the original immutable request before consulting the current task.
    # A changed checkout or later brief revision cannot erase a successful save.
    if stable_path and stable_path.exists():
        return replay()
    checkout_binding = project_state.context_binding(root)
    def selected_pointer():
        path = brief_work.safe(root, brief_work.ACTIVE)
        return brief_work.read(path) if path.exists() else None
    selection_before = selected_pointer() if not brief_id and not unscoped else None
    task = None if unscoped else brief_work.reference(root, brief_id, brief_sha)
    if task and not save_id:
        raise brief_work.BriefError('Brief saves require a stable save ID for retry safety')
    request_sha = memory.digest(json.dumps({'body': body.rstrip(), 'brief': task}, sort_keys=True).encode())
    folder = memory.safe_path(root, ".exocortex/events")
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    machine = {"Darwin": "macos", "Linux": "linux", "Windows": "windows"}.get(platform.system(), "unknown")
    editor = "cursor" if os.environ.get("CURSOR_TRACE_ID") or os.environ.get("CURSOR_SESSION") else "unknown"
    scope = project_state.portable_snapshot(root)
    branch = scope.get('branch') or '(detached or unknown)'
    content = (f"<!-- Event Metadata -->\ntimestamp: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
               f"editor: {editor}\nbranch: {branch}\nevent_id: {event_id}\n"
               f"work_scope: {json.dumps(scope, sort_keys=True)}\n"
               f"request_sha256: {request_sha}\n"
               + (f"brief_scope: {json.dumps(task, sort_keys=True)}\n" if task else '') + "\n---\n\n"
               f"{body.rstrip()}\n\nHistory saved locally. This event is not yet committed or pushed. "
               f"Merged and deployed status require separate evidence.\n\n## Git State\n\n**Last Commits:**\n{git(root, 'log', '--format=%H', '-5')}\n\n"
               f"**Branch:** {branch}\n\n**Uncommitted Changes:**\n```\n{git(root, 'status', '--short')}\n```\n\n"
               f"**Diff Stats:**\n```\n{git(root, 'diff', '--no-ext-diff', '--no-textconv', '--stat')}\n```\n")
    final_binding = project_state.context_binding(root)
    if any(before is not None and final_binding.get(key) is not None and
           before != final_binding[key] for key, before in checkout_binding.items()):
        raise brief_work.BriefError('Checkout changed during save; reconcile before retrying')
    if task:
        # Recheck the immutable task and pointer without treating unavailable Git
        # observations as proof that the selected task changed.
        if brief_work.reference(root, task['id'], task['sha256']) != task:
            raise brief_work.BriefError('Brief changed during save; retry after reconciliation')
        if not brief_id and selected_pointer() != selection_before:
            raise brief_work.BriefError('Selected task changed during save; reconcile before retrying')
    if final_binding != checkout_binding or any(value is None for value in final_binding.values()):
        content += '\nCheckout verification incomplete: Git inspection unavailable; narrative preserved. Recheck checkout identity before relying on its scope.\n'
    content = content.replace('<!-- Event Metadata -->\n', '<!-- Event Metadata -->\nevent_sha256: '+memory.digest(content.encode())+'\n', 1)
    if len(content.encode()) > memory.MAX_FILE:
        raise memory.MemoryError('Complete event exceeds the read limit; shorten the narrative before saving')
    descriptor, temporary = tempfile.mkstemp(prefix=".event-", dir=folder)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content.encode())
            handle.flush()
            os.fsync(handle.fileno())
        if stable_path:
            try:
                os.link(temporary, stable_path)
                return stable_path
            except FileExistsError:
                return replay(request_sha)
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
    parser.add_argument('--brief')
    parser.add_argument('--brief-sha')
    parser.add_argument('--save-id', help='Stable UUID for a logical save; reuse on retry')
    parser.add_argument('--unscoped', action='store_true', help='Explicitly save without task association')
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
        path = record(root, body, brief_id=args.brief, brief_sha=args.brief_sha, save_id=args.save_id, unscoped=args.unscoped)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
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
