#!/usr/bin/env python3
"""Local command entry point. No runtime discovery, network or implicit writes."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent


def git(*arguments: str) -> dict:
    try:
        result = subprocess.run(['git', '-C', str(ROOT), *arguments], capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=5,
                                env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0'))
        return {'status': 'ok' if result.returncode == 0 else 'unavailable',
                'output': result.stdout.strip() if result.returncode == 0 else ''}
    except (OSError, subprocess.TimeoutExpired):
        return {'status': 'unavailable', 'output': ''}


def note(relative: str) -> str | None:
    import refresh_rollups as memory
    path = memory.safe_path(ROOT, relative)
    return memory.decode(memory.read_bytes(path)) if path.exists() else None


def status() -> dict:
    return {'project_root': str(ROOT), 'git': git('status', '--short', '--branch'),
            'todo': note('.exocortex/TODO.md'),
            'interrupts': note('.exocortex/control/INTERRUPTS.md'),
            'open_decisions': note('.exocortex/OPEN_DECISIONS.md')}


def work() -> dict:
    import refresh_rollups as memory
    events = memory.read_events(ROOT)
    today = datetime.now(timezone.utc).date()
    windows = {'right_now': [], 'shortterm': []}
    for event in events:
        if not event['timestamp']:
            continue
        age = (today - datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).date()).days
        group = 'right_now' if 0 <= age < 7 else 'shortterm' if 7 <= age < 31 else None
        if group:
            windows[group].append({'file': event['name'], 'timestamp': event['timestamp'],
                                   'excerpt': event['body'][:2400], 'truncated': len(event['body']) > 2400})
    nudge = next((line.strip() for event in events for line in event['body'].splitlines()
                  if any(word in line.lower() for word in ('friction', 'recurring', 'context gap'))), '')
    return dict(status(), coverage=memory.check_events(ROOT, events, today),
                right_now=windows['right_now'][:10], shortterm=windows['shortterm'][:15],
                omitted={key: max(0, len(value) - (10 if key == 'right_now' else 15)) for key, value in windows.items()},
                subconscious_nudge=nudge, recent_commits=git('log', '-5', '--oneline'))


def history(arguments: list[str]) -> dict:
    import refresh_rollups as memory
    parser = argparse.ArgumentParser(prog='exocortex history')
    parser.add_argument('--keyword')
    parser.add_argument('--since', type=datetime.fromisoformat)
    parser.add_argument('--until', type=datetime.fromisoformat)
    args = parser.parse_args(arguments)
    events = memory.read_events(ROOT)
    selected = []
    for event in events:
        stamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).date() if event['timestamp'] else None
        if args.keyword and args.keyword.casefold() not in event['body'].casefold():
            continue
        if args.since and (not stamp or stamp < args.since.date()):
            continue
        if args.until and (not stamp or stamp > args.until.date()):
            continue
        selected.append({'file': event['name'], 'timestamp': event['timestamp'], 'title': event['title']})
    return {'events': selected[:50], 'omitted': max(0, len(selected) - 50)}


def main(arguments=None) -> int:
    if sys.version_info < (3, 9):
        print('EXOCORTEX_PYTHON_UNAVAILABLE: Python 3.9+ is required.', file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['onboard', 'work', 'brief', 'scrum', 'history', 'save',
                                               'refresh', 'drill', 'shortterm', 'longterm', 'subconscious',
                                               'check-keys', 'script'])
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(arguments)
    # Helpers must behave the same when the caller's shell is outside the project.
    os.chdir(ROOT)
    if args.operation in ('work', 'brief', 'scrum', 'history'):
        if args.arguments and args.operation != 'history':
            parser.error('unexpected arguments')
        try:
            if args.operation == 'work':
                result = work()
            elif args.operation == 'history':
                result = history(args.arguments)
            elif args.operation == 'scrum':
                import refresh_rollups as memory
                yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
                events = memory.read_events(ROOT)
                result = dict(status(), yesterday_utc=yesterday,
                              events=[{'file': e['name'], 'excerpt': e['body'][:2400]}
                                      for e in events if (e['timestamp'] or '').startswith(yesterday)][:10])
            else:
                result = status()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except (OSError, ValueError) as exc:
            print('EXOCORTEX_READ_FAILED: ' + str(exc), file=sys.stderr)
            return 2
    scripts = {'onboard': 'onboard_evidence.py', 'save': 'record_event.py', 'refresh': 'refresh_rollups.py',
               'drill': 'drill_memory.py', 'shortterm': 'get_shortterm_memory.py',
               'longterm': 'get_longterm_memory.py', 'subconscious': 'get_subconscious_memory.py',
               'check-keys': 'check_keys.py'}
    if args.operation == 'script':
        if not args.arguments:
            parser.error('script requires a project helper filename')
        filename = args.arguments.pop(0)
    else:
        filename = scripts[args.operation]
    if not re.fullmatch(r'[a-z][a-z0-9_]*\.py', filename):
        parser.error('expected a project helper basename, not a path')
    path = SCRIPTS / filename
    if not path.is_file() or path.is_symlink() or path.name == Path(__file__).name:
        parser.error('helper unavailable')
    sys.argv = [str(path), *args.arguments]
    # No subprocess, shell interpolation or status translation; notably preserve save exit 3.
    runpy.run_path(str(path), run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
