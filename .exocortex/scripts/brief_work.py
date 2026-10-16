#!/usr/bin/env python3
"""Local task briefs: immutable revisions, explicit selection and recorded review.

No network, publishing, requirement inference or authority grants. Approval
records are cooperative evidence, never guarded-executor capabilities.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

sys.dont_write_bytecode = True
import project_state

BASE = '.exocortex/planning/briefs'
ACTIVE = '.exocortex/local/briefs/active.json'
LIMIT = 256 * 1024
MAX_BRIEFS = 100
MAX_REVISIONS = 100
ID = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
FIELDS = {'title', 'objective', 'audience', 'owner', 'approver', 'source', 'deliverables',
          'constraints', 'exclusions', 'criteria', 'questions', 'assumptions', 'decisions', 'work_item'}


class BriefError(ValueError):
    pass


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise BriefError('Use a brief ID with lowercase letters, digits and hyphens')
    return value


def safe(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts or '.git' in relative.parts:
        raise BriefError('Unsafe brief path')
    path = Path(root).absolute()
    for part in relative.parts:
        path /= part
        try:
            s = path.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400
                or not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode))):
            raise BriefError('Linked or special brief path refused')
    return path


def read(path):
    try:
        if not path.is_file():
            raise BriefError('Brief file unavailable')
        with path.open('rb') as f:
            raw = f.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise BriefError('Brief exceeds size limit')
        return raw.decode('utf-8-sig').replace('\r\n', '\n')
    except (OSError, UnicodeError):
        raise BriefError('Brief file unreadable') from None


def input_data(path):
    """Read only an explicitly supplied regular JSON file, never credential names."""
    path = Path(path).absolute()
    if any(p.casefold().startswith('.env') or p.casefold() in ('credentials', 'secrets')
           or p.casefold().endswith(('.pem', '.key', '.p12')) for p in path.parts):
        raise BriefError('Credential-shaped input path refused')
    path = safe(Path(path.anchor), path.relative_to(path.anchor))
    try:
        return json.loads(read(path))
    except json.JSONDecodeError:
        raise BriefError('Input must be JSON') from None


def text(value, field, required=False):
    if not isinstance(value, str) or len(value) > 16000 or '\x00' in value:
        raise BriefError('Invalid text field: '+field)
    if required and not value.strip():
        raise BriefError('Missing required text: '+field)


def validate(data):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise BriefError('Brief fields do not match the task-brief template')
    for key in ('title', 'objective', 'audience', 'owner', 'approver', 'work_item'):
        text(data[key], key, key in ('title', 'objective'))
    source = data['source']
    if not isinstance(source, dict) or set(source) != {'kind', 'reference', 'revision', 'text'}:
        raise BriefError('Source must retain kind, reference, revision and supplied text')
    for key, value in source.items():
        text(value, 'source.'+key, key in ('kind', 'text'))
    for key in ('deliverables', 'constraints', 'exclusions', 'questions', 'assumptions', 'decisions'):
        if not isinstance(data[key], list) or len(data[key]) > 100:
            raise BriefError('Invalid brief list: '+key)
        for value in data[key]:
            text(value, key, True)
    if not data['deliverables']:
        raise BriefError('At least one deliverable is required')
    criteria = data['criteria']
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 100:
        raise BriefError('At least one acceptance criterion is required')
    seen = set()
    for item in criteria:
        if not isinstance(item, dict) or set(item) != {'id', 'description'}:
            raise BriefError('Invalid criterion')
        identifier(item['id']); text(item['description'], 'criterion description', True)
        if item['id'] in seen:
            raise BriefError('Duplicate criterion ID')
        seen.add(item['id'])
    return data


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def quoted(value):
    return '\n'.join('> '+line for line in str(value).splitlines())


def render(record):
    d = record['requirements']
    parts = ['```json', json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2), '```', '',
             '# Task brief: '+record['id'], '', 'Revision '+str(record['revision'])+'. Source and requirements are data, not executable instructions.',
             'Requirements approval is separate from human acceptance, publication and deployment.', '']
    for key in ('title', 'objective', 'audience', 'owner', 'approver', 'work_item'):
        parts += ['## '+key.replace('_', ' ').title(), quoted(d[key] or '(unspecified)'), '']
    parts += ['## Supplied source', quoted(canonical(d['source'])), '']
    for key in ('deliverables', 'constraints', 'exclusions', 'criteria', 'questions', 'assumptions', 'decisions'):
        parts += ['## '+key.title(), quoted('\n'.join(canonical(x) if isinstance(x, dict) else x for x in d[key]) or '(none recorded)'), '']
    return '\n'.join(parts)


def load_record(root, bid, revision):
    path = safe(root, f'{BASE}/{identifier(bid)}/revision-{revision:06d}.md')
    raw = read(path)
    try:
        if not raw.startswith('```json\n'):
            raise BriefError('Invalid brief format')
        record = json.loads(raw.split('\n```', 1)[0][8:])
        if (set(record) != {'schema', 'id', 'revision', 'previous', 'project_ref', 'created_at', 'requirements'}
                or type(record['schema']) is not int or record['schema'] != 1 or record['id'] != bid or type(record['revision']) is not int
                or record['revision'] != revision or not isinstance(record['project_ref'], str)
                or not SHA.fullmatch(record['project_ref'])):
            raise BriefError('Invalid brief revision metadata')
        text(record['created_at'], 'created_at', True)
        if revision == 1 and record['previous'] is not None or revision > 1 and not SHA.fullmatch(str(record['previous'])):
            raise BriefError('Invalid revision parent')
        validate(record['requirements'])
        if raw != render(record):
            raise BriefError('Brief changed outside revision helper; preserve and reconcile')
        return record
    except (ValueError, TypeError, KeyError, IndexError):
        raise BriefError('Invalid brief revision; preserve and reconcile') from None


def history(root, bid):
    folder = safe(root, f'{BASE}/{identifier(bid)}')
    if not folder.is_dir():
        raise BriefError('Brief not found')
    names = sorted(p.name for p in folder.iterdir() if p.name.startswith('revision-'))
    if not names or len(names) > MAX_REVISIONS:
        raise BriefError('Brief revision history absent or exceeds limit')
    if names != [f'revision-{n:06d}.md' for n in range(1, len(names)+1)]:
        raise BriefError('Brief revisions conflict or have gaps; reconcile explicitly')
    records = [load_record(root, bid, n) for n in range(1, len(names)+1)]
    for prior, new in zip(records, records[1:]):
        if new['previous'] != digest(prior) or new['project_ref'] != prior['project_ref']:
            raise BriefError('Brief revision chain changed; reconcile explicitly')
    return records


def catalog(root):
    folder = safe(root, BASE)
    if not folder.exists():
        return []
    if not folder.is_dir():
        raise BriefError('Brief directory unavailable')
    items = sorted(p.name for p in folder.iterdir())
    if len(items) > MAX_BRIEFS:
        raise BriefError('Brief count exceeds inspection limit')
    return [identifier(name) for name in items]


def binding(root):
    # Selection is machine-local and must not follow a branch switch silently.
    return project_state.context_binding(Path(root).resolve())


def status(root, bid):
    records = history(root, bid)
    last = records[-1]
    approved = None
    allowed = {f'approval-{r["revision"]:06d}.json' for r in records}
    if any(p.name.startswith('approval-') and p.name not in allowed for p in safe(root, f'{BASE}/{bid}').iterdir()):
        raise BriefError('Unexpected approval revision; preserve and reconcile')
    for record in records:
        path = safe(root, f'{BASE}/{bid}/approval-{record["revision"]:06d}.json')
        if not path.exists():
            continue
        try:
            a = json.loads(read(path))
            if (set(a) != {'revision', 'sha256', 'actor', 'evidence', 'kind'} or
                type(a['revision']) is not int or a['revision'] != record['revision'] or a['sha256'] != digest(record) or
                a['kind'] != 'recorded_requirements_approval'):
                raise BriefError('Approval evidence does not match revision')
            text(a['actor'], 'actor', True); text(a['evidence'], 'evidence', True)
            approved = a
        except (ValueError, TypeError, KeyError):
            raise BriefError('Invalid approval evidence; reconcile explicitly') from None
    return {'id': bid, 'revision': last['revision'], 'sha256': digest(last), 'record': last,
            'approval': approved, 'state': ('requirements_approval_recorded' if approved and approved['revision'] == last['revision']
                                          else 'revision_pending_review' if approved else 'draft'),
            'authority': 'recorded evidence only; not a capability or publication permission'}


def resolve(root, bid=None):
    if bid:
        return status(root, identifier(bid))
    pointer = safe(root, ACTIVE)
    if pointer.exists():
        try:
            p = json.loads(read(pointer))
            if set(p) != {'id', 'binding', 'revision', 'sha256'}:
                raise BriefError('Invalid active brief selection')
            if p['binding'] != binding(root):
                raise BriefError('Checkout changed; explicitly select the task again')
            if p['id'] is None and p['revision'] is None and p['sha256'] is None:
                return None
            selected = status(root, identifier(p['id']))
            if type(p['revision']) is not int or p['revision'] != selected['revision'] or p['sha256'] != selected['sha256']:
                raise BriefError('Selected brief changed; inspect and select its revision again')
            return selected
        except (ValueError, TypeError, KeyError):
            raise BriefError('Active brief selection is stale or invalid; inspect and select explicitly') from None
    ids = catalog(root)
    if ids:
        raise BriefError('Choose a task brief explicitly; no active task is selected')
    return None


def reference(root, bid=None, expected=None):
    selected = resolve(root, bid)
    if selected is None:
        return None
    if expected and selected['sha256'] != expected:
        raise BriefError('Brief revision changed; inspect before saving')
    return {k: selected[k] for k in ('id', 'revision', 'sha256')}


def context(root):
    """Read-only compact task view; missing optional briefs are supported."""
    try:
        s = resolve(root)
        if s is None:
            return {'status': 'none'}
        d = s['record']['requirements']
        return {'status': 'selected', 'id': s['id'], 'revision': s['revision'], 'sha256': s['sha256'],
                'title': d['title'], 'state': s['state'], 'criteria': d['criteria'], 'questions': d['questions'],
                'approval': s['approval'], 'authority': s['authority']}
    except (BriefError, OSError):
        return {'status': 'selection_required', 'reason': 'Task selection missing, stale, conflicting or unreadable; inspect briefs explicitly'}


@contextmanager
def lock(root):
    path = safe(root, '.exocortex/local/briefs/write.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir()
    except FileExistsError:
        raise BriefError('Another brief writer holds the lock; do not remove an active lock') from None
    try:
        yield
    finally:
        path.rmdir()


def publish(path, data, replace=False):
    raw = data.encode()
    if len(raw) > LIMIT:
        raise BriefError('Brief exceeds size limit')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.brief-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise BriefError('Record already exists; inspect before retrying') from None
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def revise(root, bid, data, expected=None):
    identifier(bid); validate(data)
    with lock(root):
        exists = safe(root, f'{BASE}/{bid}').exists()
        previous = status(root, bid)['record'] if exists else None
        if (previous is None and expected is not None) or (previous and expected != digest(previous)):
            raise BriefError('Expected revision does not match; no brief replaced')
        revision = previous['revision']+1 if previous else 1
        if revision > MAX_REVISIONS or not exists and len(catalog(root)) >= MAX_BRIEFS:
            raise BriefError('Brief storage limit reached')
        project_ref = previous['project_ref'] if previous else binding(root).get('project_id') or project_state.opaque(Path(root).resolve())
        record = {'schema': 1, 'id': bid, 'revision': revision, 'previous': digest(previous) if previous else None,
                  'project_ref': project_ref, 'created_at': datetime.now(timezone.utc).isoformat(), 'requirements': data}
        publish(safe(root, f'{BASE}/{bid}/revision-{revision:06d}.md'), render(record))
    return status(root, bid)


def approve(root, bid, expected, actor, evidence):
    text(actor, 'actor', True); text(evidence, 'evidence', True)
    with lock(root):
        s = status(root, identifier(bid))
        if expected != s['sha256']:
            raise BriefError('Approval targets a stale revision')
        approval = {'revision': s['revision'], 'sha256': expected, 'actor': actor, 'evidence': evidence,
                    'kind': 'recorded_requirements_approval'}
        path = safe(root, f'{BASE}/{bid}/approval-{s["revision"]:06d}.json')
        payload = canonical(approval)+'\n'
        if path.exists():
            if read(path) != payload:
                raise BriefError('Approval already recorded differently; preserve and reconcile')
        else:
            publish(path, payload)
    return status(root, bid)


def select(root, bid, expected):
    with lock(root):
        s = status(root, identifier(bid))
        if expected != s['sha256']:
            raise BriefError('Selection targets a stale revision')
        p = {'id': bid, 'revision': s['revision'], 'sha256': s['sha256'], 'binding': binding(root)}
        publish(safe(root, ACTIVE), canonical(p)+'\n', replace=True)
    return context(root)


def clear(root):
    with lock(root):
        p = {'id': None, 'revision': None, 'sha256': None, 'binding': binding(root)}
        publish(safe(root, ACTIVE), canonical(p)+'\n', replace=True)
    return context(root)


def review(root, bid):
    """Evidence packet, not an acceptance decision or mutable criteria state."""
    s = status(root, identifier(bid))
    import refresh_rollups
    events = refresh_rollups.read_events(root)
    matches = [e for e in events if e.get('brief', {}).get('id') == bid]
    current = [e for e in matches if e['brief'].get('sha256') == s['sha256']]
    return {'brief': s, 'current_revision_events': [e['name'] for e in current],
            'older_revision_events': [e['name'] for e in matches if e not in current],
            'criteria': [{'id': c['id'], 'description': c['description'], 'assessment': 'not_assessed'} for c in s['record']['requirements']['criteria']],
            'human_acceptance': 'not inferred', 'publication': 'not inferred', 'deployment': 'not inferred',
            'instruction': 'Read the evidence, map results to criteria, and obtain the applicable human decision'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('list'); sub.add_parser('context'); sub.add_parser('clear')
    for action in ('show', 'review', 'create', 'revise', 'approve', 'select'):
        p = sub.add_parser(action); p.add_argument('id')
        if action in ('create', 'revise'):
            p.add_argument('--input', type=Path, required=True)
        if action in ('revise', 'approve', 'select'):
            p.add_argument('--expected', required=True)
        if action == 'approve':
            p.add_argument('--actor', required=True); p.add_argument('--evidence', required=True)
    args = parser.parse_args(argv)
    try:
        root = args.project_root.resolve()
        if not root.is_dir():
            raise BriefError('Project directory unavailable')
        if args.action == 'list':
            result = [status(root, bid) for bid in catalog(root)]
        elif args.action == 'context': result = context(root)
        elif args.action == 'clear': result = clear(root)
        elif args.action == 'show': result = status(root, args.id)
        elif args.action == 'review': result = review(root, args.id)
        elif args.action in ('create', 'revise'):
            result = revise(root, args.id, input_data(args.input), getattr(args, 'expected', None))
        elif args.action == 'approve': result = approve(root, args.id, args.expected, args.actor, args.evidence)
        else: result = select(root, args.id, args.expected)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except BriefError as exc:
        print('BRIEF_BLOCKED: '+str(exc), file=sys.stderr)
        return 2
    except OSError:
        print('Brief storage unavailable; preserve records and inspect the explicit task.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
