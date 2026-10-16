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
        result = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', '-C', str(ROOT), *arguments], capture_output=True,
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



KNOWLEDGE_MAX_BYTES = 4 * 1024 * 1024
KNOWLEDGE_RECENT = 15


def knowledge_evidence(coverage: dict) -> dict:
    """Bounded historical summary, never authority or a reason to stop /work."""
    import refresh_rollups as memory
    import knowledge_map
    result = {'present': False, 'status': 'absent', 'counts': None,
              'recent_entities': [], 'recent_concepts': [],
              'knowledge_view_changed': ('knowledge_view_changed' in coverage.get('reasons', [])
                                         if coverage.get('status') in ('fresh', 'stale') else None)}
    try:
        md = memory.safe_path(ROOT, memory.KNOWLEDGE_MD)
        path = memory.safe_path(ROOT, memory.KNOWLEDGE_JSONL)
        result['present'] = md.exists() or path.exists()
        if not result['present']:
            result['counts'] = {'entities': 0, 'relationships': 0, 'concepts': 0}
            return result
        raw = memory.decode(memory.read_bytes(path, KNOWLEDGE_MAX_BYTES))
        lines = raw.splitlines()
        if not lines or len(lines) > knowledge_map.MAX_TOTAL + 1:
            raise ValueError('knowledge bound')
        header = json.loads(lines[0])
        if (not isinstance(header, dict) or header.get('generator') != knowledge_map.GENERATOR
                or header.get('type') != 'header' or header.get('schema') != knowledge_map.SCHEMA):
            raise ValueError('knowledge header')
        counts = {'entities': 0, 'relationships': 0, 'concepts': 0}
        recent = {'entity': [], 'concept': []}
        for line in lines[1:]:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError('knowledge record')
            kind = record.get('type')
            if kind == 'unparsed':
                continue
            if kind not in ('entity', 'relationship', 'concept'):
                raise ValueError('knowledge kind')
            counts[{'entity': 'entities', 'relationship': 'relationships', 'concept': 'concepts'}[kind]] += 1
            if kind == 'relationship':
                continue
            sources = record.get('sources', [])
            notes = record.get('notes', [])
            if not isinstance(sources, list) or not isinstance(notes, list):
                raise ValueError('knowledge provenance')
            def timestamp(source):
                value = source.get('timestamp')
                if value is None:
                    return ''
                if not isinstance(value, str) or len(value) > 64:
                    raise ValueError('knowledge timestamp')
                stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if stamp.tzinfo is None:
                    raise ValueError('knowledge timestamp')
                return stamp.astimezone(timezone.utc).isoformat()
            if any(not isinstance(x, dict) for x in sources + notes):
                raise ValueError('knowledge provenance')
            updated = max((timestamp(x) for x in sources), default='')
            latest = max(notes, key=timestamp, default={})
            def bounded(value, limit):
                if not isinstance(value, str):
                    raise ValueError('knowledge text')
                return ' '.join(value.split())[:limit]
            row = {'name': bounded(record.get('name'), knowledge_map.MAX_NAME),
                   'text': bounded(latest.get('text', ''), knowledge_map.MAX_TEXT),
                   'updated_at': updated or None}
            if kind == 'entity':
                row['entity_type'] = bounded(record.get('entity_type', ''), knowledge_map.MAX_TYPE)
            recent[kind].append(row)
        for kind, key in (('entity', 'recent_entities'), ('concept', 'recent_concepts')):
            result[key] = sorted(recent[kind], key=lambda r: (r['updated_at'] or '', r['name']),
                                 reverse=True)[:KNOWLEDGE_RECENT]
        result.update(status='available', counts=counts)
    except (OSError, ValueError, TypeError, RecursionError):
        # Do not echo untrusted map contents or invalidate otherwise useful work evidence.
        result.update(status='unavailable', counts=None, recent_entities=[], recent_concepts=[])
    return result


def work() -> dict:
    import refresh_rollups as memory
    import project_state
    with project_state.inspection_budget():
        return work_evidence()


def work_evidence() -> dict:
    import refresh_rollups as memory
    import project_state
    import brief_work
    import release_awareness
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
    try:
        coverage = memory.check_events(ROOT, events, today)
    except (OSError, ValueError, RecursionError):
        coverage = {'status': 'error', 'reasons': ['coverage_unavailable'], 'semantic_review': 'not_performed'}
        knowledge = knowledge_evidence(coverage)
        if knowledge['status'] != 'unavailable':
            raise  # Preserve existing failures unrelated to optional knowledge.
    else:
        knowledge = knowledge_evidence(coverage)
    return dict(status(), coverage=coverage, knowledge=knowledge,
                location=project_state.current_report(ROOT), task_brief=brief_work.context(ROOT),
                release_awareness=release_awareness.status(ROOT),
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
