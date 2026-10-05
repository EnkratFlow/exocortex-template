#!/usr/bin/env python3
"""Shared offline project/checkout facts. Never fetch, save, clean up or deploy.

Paths and observations are machine-local. Portable event metadata uses opaque
project/checkout references and commit identities, never absolute paths.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import time
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
MAX_WORKTREES = 100
MAX_MEMORY_FILES = 1000
MAX_MEMORY_BYTES = 64 * 1024 * 1024


INSPECTION_DEADLINE = ContextVar("inspection_deadline", default=None)


@contextmanager
def inspection_budget(seconds=10):
    previous = INSPECTION_DEADLINE.get()
    token = INSPECTION_DEADLINE.set(min(previous, time.monotonic()+seconds) if previous is not None else time.monotonic()+seconds)
    try:
        yield
    finally:
        INSPECTION_DEADLINE.reset(token)


def bounded(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with inspection_budget():
            return function(*args, **kwargs)
    return wrapped


class Unavailable(Exception):
    pass


def run(args, cwd=None):
    deadline = INSPECTION_DEADLINE.get()
    remaining = deadline - time.monotonic() if deadline is not None else 20
    if remaining <= 0:
        raise Unavailable('Inspection time limit reached')
    if args[0] == 'git':
        args = ['git', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', *args[1:]]
    try:
        result = subprocess.run(args, cwd=cwd, text=True, encoding='utf-8', errors='replace',
                                capture_output=True, timeout=min(3, remaining),
                                env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0',
                                         GH_PROMPT_DISABLED='1', LC_ALL='C'))
    except (OSError, subprocess.TimeoutExpired):
        raise Unavailable('Inspection unavailable or timed out') from None
    if result.returncode:
        # Raw errors and remote URLs may contain credentials.
        raise Unavailable('Inspection unavailable')
    return result.stdout


def git(root, *args):
    return run(['git', '-C', str(root), *args]).rstrip('\n')


def optional(root, *args):
    try:
        return git(root, *args)
    except Unavailable:
        return None


def opaque(value):
    return hashlib.sha256(str(value).encode()).hexdigest()


def machine_name():
    """Local observation only; never include in portable event metadata."""
    try:
        return socket.gethostname()
    except OSError:
        return 'unknown'


def linked_worktree_paths(root):
    """Git is the registry for every provider, independent of folder names."""
    raw = git(root, 'worktree', 'list', '--porcelain', '-z')
    return [Path(part[9:]) for part in raw.split('\0') if part.startswith('worktree ')]


def remote_identity(value):
    """Sanitized host/repository identity; never return URL userinfo or query."""
    if not value or any(ord(c) < 32 for c in value):
        return None
    try:
        if '://' in value:
            parsed = urlsplit(value)
            if parsed.scheme not in ('https', 'http', 'ssh', 'git') or parsed.query or parsed.fragment:
                return None
            host, path = parsed.hostname, parsed.path.lstrip('/')
            port = parsed.port
            if port and port not in (22 if parsed.scheme == 'ssh' else 443 if parsed.scheme == 'https' else 80,):
                host = f'{host}:{port}'
        else:
            match = re.fullmatch(r'(?:[^/@:]+@)?([^/:]+):(.+)', value)
            if not match or len(match[1]) == 1:  # not a local Windows path
                return None
            host, path = match.groups()
        path = path.removesuffix('/').removesuffix('.git')
        if not host or not re.fullmatch(r'[A-Za-z0-9.:-]+', host):
            return None
        if not re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+', path):
            return None
        if any(p in ('.', '..') for p in path.split('/')):
            return None
        # GitHub repository names are case insensitive; other hosts may not be.
        return host.lower() + '/' + (path.lower() if host.lower() == 'github.com' else path)
    except ValueError:
        return None


def ordinary(path):
    try:
        info = path.lstat()
        return not (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400)
    except OSError:
        return False


def safe_file(root, relative, limit=128):
    path = root
    for part in Path(relative).parts:
        path /= part
        if not ordinary(path):
            raise Unavailable('File unavailable or linked')
    if not path.is_file():
        raise Unavailable('Expected a regular file')
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Unavailable('Inspection limit reached')
    return data


def version(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value.removeprefix('v') if re.fullmatch(r'v?\d+\.\d+\.\d+', value) else None


def local_version(root):
    folder = root / '.exocortex'
    try:
        folder.lstat()
    except FileNotFoundError:
        return None, False
    except OSError:
        return None, True
    if not ordinary(folder) or not folder.is_dir():
        return None, True
    try:
        installed = version(safe_file(root, '.exocortex/.version').decode('utf-8'))
        return installed, True
    except (Unavailable, OSError, UnicodeError):
        # Source template has a package marker rather than an installed marker.
        if all((root/p).is_file() for p in ('install.sh', 'scripts/safe-update.sh', '.exocortex/release-baseline.json')):
            try:
                return version(safe_file(root, 'VERSION').decode('utf-8')), True
            except (Unavailable, OSError, UnicodeError):
                pass
        return None, True


def repository(root):
    top = Path(git(root, 'rev-parse', '--show-toplevel')).resolve()
    common = Path(git(top, 'rev-parse', '--git-common-dir'))
    if not common.is_absolute():
        common = top/common
    common = common.resolve()
    remote = remote_identity(optional(top, 'config', '--get', 'remote.origin.url'))
    return {'root': str(top), 'common_dir': str(common), 'repository': remote,
            'project_id': opaque(remote or str(common)),
            'identity_basis': 'origin host/repository' if remote else 'local Git common directory',
            'cross_machine_identity': bool(remote)}


def resolve_trunk(root):
    ref = optional(root, 'symbolic-ref', '--quiet', 'refs/remotes/origin/HEAD')
    choices = [(ref, 'cached origin default branch')] if ref else []
    choices += [('refs/heads/main', 'local main fallback'), ('refs/heads/master', 'local master fallback')]
    for name, basis in choices:
        sha = optional(root, 'rev-parse', '--verify', name+'^{commit}')
        if sha:
            return {'ref': name, 'sha': sha, 'basis': basis, 'fresh_remote': False}
    return {'ref': None, 'sha': None, 'basis': 'unknown', 'fresh_remote': False}


def relation(root, base, head='HEAD'):
    if not base:
        return {'ahead': None, 'behind': None}
    counts = optional(root, 'rev-list', '--left-right', '--count', base+'...'+head)
    try:
        behind, ahead = map(int, counts.split())
        return {'ahead': ahead, 'behind': behind}
    except (AttributeError, ValueError):
        return {'ahead': None, 'behind': None}


def working_counts(root):
    raw = git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    parts = iter(raw.split('\0'))
    counts = {'staged': 0, 'modified': 0, 'untracked': 0, 'conflicted': 0}
    for entry in parts:
        if not entry:
            continue
        xy = entry[:2]
        if xy == '??':
            counts['untracked'] += 1
        elif xy != '!!':
            counts['staged'] += xy[0] != ' '
            counts['modified'] += xy[1] != ' '
            counts['conflicted'] += 'U' in xy or xy in ('AA', 'DD')
        if 'R' in xy or 'C' in xy:
            next(parts, None)
    return counts


def checkout(root, trunk=None):
    root = Path(root).resolve()
    info = repository(root)
    if Path(info['root']) != root:
        raise Unavailable('Expected a checkout root')
    trunk = trunk or resolve_trunk(root)
    branch = optional(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    head = optional(root, 'rev-parse', '--verify', 'HEAD')
    counts = working_counts(root)
    upstream = optional(root, 'rev-parse', '--symbolic-full-name', '@{upstream}')
    remote_ref = upstream if upstream and upstream.startswith('refs/remotes/') else None
    sync = relation(root, remote_ref)
    installed, present = local_version(root)
    marker = '.exocortex/.version' if (root/'.exocortex/.version').exists() else 'VERSION'
    trunk_version = version(optional(root, 'show', trunk['sha']+':'+marker)) if trunk['sha'] else None
    return {**info, 'path': str(root), 'machine': machine_name(), 'checkout_id': opaque(str(root)), 'branch': branch,
            'head': head, 'version': installed, 'installed': present, 'trunk': trunk,
            'trunk_version': trunk_version, 'version_differs_from_trunk':
            installed != trunk_version if installed and trunk_version else None,
            'divergence': relation(root, trunk['sha']), 'working': counts, 'dirty': any(counts.values()),
            'upstream': remote_ref, 'upstream_divergence': sync,
            'pushed': 'unknown; remote not contacted',
            'process_use': 'unknown; no process inspection',
            'deployment': 'unknown; not observed', 'cleanup': 'not assessed'}


@bounded
def context_binding(root):
    """Local receipt identity. No host paths or project names in generated text."""
    try:
        info = repository(root)
        return {'project_id': info['project_id'], 'checkout_id': opaque(info['root']),
                'branch': optional(root, 'symbolic-ref', '--quiet', '--short', 'HEAD'),
                'head': optional(root, 'rev-parse', '--verify', 'HEAD')}
    except Unavailable:
        return {'project_id': None, 'checkout_id': opaque(Path(root).resolve()), 'branch': None, 'head': None}


@bounded
def portable_snapshot(root):
    result = context_binding(root)
    try:
        item = checkout(root)
        result.update(working=item['working'], trunk_sha=item['trunk']['sha'],
                      ahead=item['divergence']['ahead'], behind=item['divergence']['behind'],
                      pushed='unknown; remote not contacted', deployment='unknown; not observed')
    except (Unavailable, OSError):
        result['inspection'] = 'unavailable'
    return result


@bounded
def current_report(root):
    """Daily commands inspect one checkout; /where explicitly expands its family."""
    try:
        item = checkout(root)
        item['current'] = True
        return {'schema': 'project-state/1', 'read_only': True, 'network': False,
                'observed_at': datetime.now(timezone.utc).isoformat(),
                'checkouts': [item], 'warnings': [],
                'verdict': 'Current checkout inspected; other working folders require /where.'}
    except (Unavailable, OSError):
        return {'schema': 'project-state/1', 'read_only': True, 'network': False,
                'checkouts': [], 'warnings': ['Current checkout inspection unavailable'],
                'verdict': 'Checkout unknown; preserve existing work.'}


def memory_inventory(root):
    """Hash only declared portable notes/events; never inspect secrets or caches."""
    names = ['PROJECT_MEMORY.md', 'LESSONS.md', 'OPEN_DECISIONS.md', 'TODO.md',
             'control/ACTIVE_WORK.md', 'control/BACKLOG.md', 'control/INTERRUPTS.md']
    records, issues, total = [], [], 0
    folder = root/'.exocortex/events'
    try:
        if folder.exists():
            if not ordinary(root/'.exocortex') or not ordinary(folder):
                raise Unavailable('Linked memory directory')
            for i, path in enumerate(folder.iterdir()):
                if i >= MAX_MEMORY_FILES:
                    raise Unavailable('Memory file limit reached')
                if path.name.endswith('.md') and path.name != '2000-01-01_00-00-00_example-event.md':
                    names.append('events/'+path.name)
        for name in sorted(names):
            relative = '.exocortex/'+name
            if not (root/relative).exists() and not (root/relative).is_symlink():
                continue
            data = safe_file(root, relative, 4*1024*1024)
            total += len(data)
            if total > MAX_MEMORY_BYTES:
                raise Unavailable('Memory byte limit reached')
            records.append({'name': name, 'sha256': hashlib.sha256(data).hexdigest()})
    except (Unavailable, OSError):
        issues.append('Memory inspection incomplete; preserve this checkout')
    return {'files': records, 'complete': not issues, 'issues': issues}


def collect(root, include_memory=False):
    root = Path(root).resolve()
    info = repository(root)
    root = Path(info['root'])
    trunk = resolve_trunk(root)
    entries = linked_worktree_paths(root)
    records, warnings = [], []
    if len(entries) > MAX_WORKTREES:
        warnings.append('Checkout list truncated; remaining work is uninspected')
    for name in entries[:MAX_WORKTREES]:
        try:
            path = Path(name)
            if not ordinary(path):
                raise Unavailable('Linked or missing checkout')
            item = checkout(path, trunk)
            if item['common_dir'] != info['common_dir']:
                raise Unavailable('Checkout belongs to another Git repository')
            item['current'] = path.resolve() == root
            if include_memory:
                item['memory'] = memory_inventory(path)
            records.append(item)
        except (Unavailable, OSError):
            warnings.append('A registered checkout could not be inspected; it is not safe to retire')
    if include_memory:
        copies, names = {}, {}
        for item in records:
            for record in item['memory']['files']:
                copies.setdefault(record['sha256'], set()).add(item['checkout_id'])
                names.setdefault(record['name'], set()).add(record['sha256'])
        for item in records:
            item['memory']['unique_in_inspected_checkouts'] = [r['name'] for r in item['memory']['files']
                                                              if len(copies[r['sha256']]) == 1]
            item['memory']['identical_content_elsewhere'] = [r['name'] for r in item['memory']['files']
                                                            if len(copies[r['sha256']]) > 1]
            item['memory']['conflicting_names'] = [r['name'] for r in item['memory']['files']
                                                   if len(names[r['name']]) > 1]
            if not item['memory']['complete']:
                warnings.append('Memory inspection incomplete in a checkout; preservation remains unverified')
            item['memory']['retirement'] = 'not authorized; remote preservation and other local data unverified'
    dirty = sum(x['dirty'] for x in records)
    return {'schema': 'project-state/1', 'observed_at': datetime.now(timezone.utc).isoformat(),
            'read_only': True, 'network': False, 'project': info, 'trunk': trunk,
            'scope': {'machine': machine_name(), 'project_root': str(root),
                      'discovery': 'Git registered worktrees on this machine, regardless of provider',
                      'other_clones': 'not inspected', 'other_machines': 'not inspected'},
            'checkouts': records, 'warnings': warnings,
            'verdict': f'Projects: 1; checkouts: {len(entries)}; inspected: {len(records)}; '
                       f'with uncommitted work: {dirty}; process use and live deployment: unknown.'}


def group_projects(remotes, locals_):
    """One project per canonical remote, or Git common directory when offline-only."""
    groups = {}
    for remote in remotes:
        identity = 'github.com/'+remote['repository'].lower()
        groups[opaque(identity)] = {'project_id': opaque(identity), 'repository': remote['repository'],
                                    'github': remote, 'local': []}
    for item in locals_:
        key = item.get('project_id') or opaque(item.get('common_dir') or item['path'])
        group = groups.setdefault(key, {'project_id': key, 'repository': item['repository'] or item['path'],
                                        'github': None, 'local': []})
        group['local'].append(item)
    return sorted(groups.values(), key=lambda x: x['repository'].lower())


def markdown(report):
    def cell(value):
        return str(value if value is not None else 'Unknown').replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
    notes = []
    lines = [report['verdict'], '', 'Observed: '+report['observed_at'],
             'Machine: '+cell(report['scope']['machine'])+'; project root: '+cell(report['scope']['project_root'])+'.',
             'Scope: Git registered worktrees on this machine, including Claude, Codex and other tools. Other clones and machines are not inspected.',
             'Folder and branch names do not establish which assistant created or last used a checkout.',
             'Local observations only. Remote refs are cached; merged and deployed are separate states.', '',
             '| Working folder | Branch / HEAD | Ahead / behind trunk | Staged / modified / untracked | Exocortex |',
             '| --- | --- | --- | --- | --- |']
    for item in report['checkouts']:
        work, diff = item['working'], item['divergence']
        values = [item['path'] + (' (current)' if item['current'] else ''),
                  (item['branch'] or 'detached')+' / '+str(item['head'])[:12],
                  f"{diff['ahead']} / {diff['behind']}",
                  f"{work['staged']} / {work['modified']} / {work['untracked']}", item['version']]
        lines.append('| '+' | '.join(map(cell, values))+' |')
        if item.get('version_differs_from_trunk'):
            notes.append('Template version differs from trunk in '+cell(item['path'])+'.')
        if 'memory' in item:
            notes += [cell(item['path'])+': '+str(len(item['memory']['unique_in_inspected_checkouts']))+
                      ' note/event files unique among inspected checkouts. Preserve before retirement.']
    lines += ['', 'Trunk comparison: '+cell(report['trunk']['ref'])+' ('+report['trunk']['basis']+').', *notes, *report['warnings']]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path.cwd())
    parser.add_argument('--memory', action='store_true', help='Inspect declared portable memory in linked checkouts')
    parser.add_argument('--format', choices=('json', 'markdown'), default='markdown')
    args = parser.parse_args(argv)
    try:
        report = collect(args.project_root, args.memory)
        print(json.dumps(report, indent=2) if args.format == 'json' else markdown(report))
        return 0
    except (Unavailable, OSError):
        print('Project inspection unavailable; no files changed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
