#!/usr/bin/env python3
"""Opt-in public release checks; status is offline and never writes.

No credentials, telemetry, repository discovery, downloads or update apply.
A machine cache is shared only for the same public, anonymous release source.
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
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
import project_state
from update_inventory import version as inventory_version, status as version_status

CONFIG = '.exocortex/local/release-awareness/config.json'
DAY = 86400
LIMIT = 512 * 1024
SCHEMA = 1
REPO = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
ERRORS = {'offline_or_timeout', 'rate_limited', 'release_unavailable', 'invalid_release', 'check_interrupted'}


class ReleaseError(ValueError):
    pass


def version(value):
    # Bound remote/cache version strings before numeric comparison.
    return inventory_version(value) if isinstance(value, str) and len(value) <= 64 else None


def repository(value):
    if not isinstance(value, str) or not REPO.fullmatch(value):
        raise ReleaseError('Choose a public GitHub release repository as OWNER/REPO')
    return value.lower()


def source(repo):
    return {'provider': 'github.com', 'repository': repository(repo), 'scope': 'public-anonymous', 'channel': 'stable'}


def default_cache():
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData/Local')
    elif sys.platform == 'darwin':
        base = Path.home()/'Library/Caches'
    else:
        base = Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')
    if not base.is_absolute():
        raise ReleaseError('Cache location must be absolute')
    return base/'exocortex/releases'


def safe(path):
    path = Path(path).absolute()
    # macOS /var may itself be a system alias; callers resolve the explicit
    # root/cache directory first, but every existing child must be ordinary.
    for p in [path, *path.parents]:
        if p.name.casefold().startswith('.env') or p.name.casefold() in ('credentials', 'secrets') or p.name.casefold().endswith(('.pem', '.key', '.p12')):
            raise ReleaseError('Credential-shaped state path refused')
        try:
            s = p.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400 or not (stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode)):
            raise ReleaseError('Linked or special state path refused')
    return path


def load(path):
    path = safe(path)
    if not path.exists():
        return None
    try:
        with path.open('rb') as f:
            raw = f.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ReleaseError('State exceeds inspection limit')
        return json.loads(raw.decode('utf-8'))
    except (OSError, UnicodeError, ValueError):
        raise ReleaseError('State is unreadable; preserve and reconcile') from None


def write(path, value):
    path = safe(path)
    raw = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    if len(raw) > LIMIT:
        raise ReleaseError('State exceeds write limit')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.release-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(raw); f.flush(); os.fsync(f.fileno())
        safe(path)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


@contextmanager
def lock(path):
    path = safe(path); path.parent.mkdir(parents=True, exist_ok=True)
    try: path.mkdir()
    except FileExistsError:
        raise ReleaseError('Release state is busy; preserve the lock and retry later') from None
    try: yield
    finally: path.rmdir()


def config(root):
    c = load(Path(root)/CONFIG)
    if c is None: return None
    if (not isinstance(c, dict) or set(c) != {'schema', 'enabled', 'source', 'reminder'} or
            type(c['schema']) is not int or c['schema'] != SCHEMA or type(c['enabled']) is not bool or
            not isinstance(c['source'], dict) or c['source'] != source(c['source'].get('repository'))):
        raise ReleaseError('Invalid release configuration; preserve and reconcile')
    r = c['reminder']
    if r is not None and (not isinstance(r, dict) or set(r) != {'version', 'until'} or version(r['version']) is None or version(r['version']) != r['version'] or not stamp(r['until'])):
        raise ReleaseError('Invalid reminder; preserve and reconcile')
    return c


def stamp(n):
    return type(n) is int and 0 <= n <= 253402300799


def now_value(now):
    n = int(time.time()) if now is None else now
    if not stamp(n): raise ReleaseError('Invalid observation time')
    return n


def configure(root, repo=None, enabled=True):
    root = Path(root)
    with lock(root/'.exocortex/local/release-awareness/config.lock'):
        old = config(root)
        if repo is None and old is None:
            if not enabled: return {'enabled': False}
            raise ReleaseError('Choose a release repository explicitly')
        selected = source(repo) if repo else old['source']
        c = {'schema': SCHEMA, 'enabled': enabled, 'source': selected,
             'reminder': old['reminder'] if old and old['source'] == selected else None}
        write(root/CONFIG, c)
    return {'enabled': enabled, 'source': selected, 'network_attempted': False}


def cache_path(cache_dir, selected):
    key = hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()
    return safe(Path(cache_dir)/(key+'.json'))


def cached(cache_dir, selected):
    c = load(cache_path(cache_dir, selected))
    if c is None: return None
    fields = {'schema', 'source', 'attempted_at', 'next_check_at', 'failures', 'error', 'release', 'checked_at'}
    if (not isinstance(c, dict) or set(c) != fields or type(c['schema']) is not int or c['schema'] != SCHEMA or
            c['source'] != selected or not stamp(c['attempted_at']) or not stamp(c['next_check_at']) or
            c['next_check_at'] < c['attempted_at'] + DAY or c['next_check_at'] > c['attempted_at']+7*DAY or
            type(c['failures']) is not int or not 0 <= c['failures'] <= 100 or
            (c['error'] is not None and (not isinstance(c['error'], str) or c['error'] not in ERRORS))):
        raise ReleaseError('Invalid release cache; preserve and reconcile')
    if c['release'] is None:
        if c['checked_at'] is not None or c['error'] is None: raise ReleaseError('Invalid empty release cache')
    else:
        r = c['release']
        if (not isinstance(r, dict) or set(r) != {'version', 'tag', 'published_at', 'notes_url'} or
                version(r['tag']) is None or r['version'] != version(r['tag']) or not stamp(r['published_at']) or
                r['notes_url'] != notes_url(selected, r['tag']) or not stamp(c['checked_at']) or
                c['checked_at'] > c['attempted_at']):
            raise ReleaseError('Invalid cached release')
    return c


def notes_url(selected, tag):
    return 'https://github.com/'+selected['repository']+'/releases/tag/'+tag


def parse_release(data, selected):
    if (not isinstance(data, dict) or data.get('draft') is not False or data.get('prerelease') is not False or
            version(data.get('tag_name')) is None):
        raise ReleaseError('invalid_release')
    try:
        published = datetime.fromisoformat(data['published_at'].replace('Z', '+00:00'))
        if published.tzinfo is None: raise ValueError()
        ts = int(published.timestamp())
        if not stamp(ts): raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise ReleaseError('invalid_release') from None
    tag = data['tag_name'].strip()
    return {'version': version(tag), 'tag': tag, 'published_at': ts, 'notes_url': notes_url(selected, tag)}


# The isolated child bounds DNS, TLS, response headers and slow body reads as
# well as socket timeouts. No inherited credential/proxy integration is used.
WORKER = r'''
import http.client, json, sys
conn = http.client.HTTPSConnection('api.github.com', timeout=5)
try:
    conn.request('GET', '/repos/'+sys.argv[1]+'/releases/latest', headers={
        'Accept': 'application/vnd.github+json', 'User-Agent': 'exocortex-release-check',
        'X-GitHub-Api-Version': '2026-03-10'})
    response = conn.getresponse()
    output = {'status': response.status, 'retry_after': response.getheader('Retry-After'), 'body': None}
    if response.status == 200:
        raw = response.read(524289)
        if len(raw) > 524288: raise ValueError()
        output['body'] = json.loads(raw.decode('utf-8'))
    print(json.dumps(output))
finally:
    conn.close()
'''


def fetch(selected):
    try:
        p = subprocess.run([sys.executable, '-I', '-c', WORKER, repository(selected['repository'])],
                           capture_output=True, timeout=12)
        if p.returncode: raise ReleaseError('offline_or_timeout')
        result = json.loads(p.stdout)
        if result['status'] == 200: return parse_release(result['body'], selected), None, 0
        wait = result.get('retry_after')
        delay = min(7*DAY, int(wait)) if isinstance(wait, str) and re.fullmatch(r'[0-9]{1,9}', wait) else 0
        return None, ('rate_limited' if result['status'] in (403, 429) else 'release_unavailable'), delay
    except ReleaseError as e:
        return None, str(e) if str(e) in ERRORS else 'invalid_release', 0
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, KeyError):
        return None, 'offline_or_timeout', 0


def status(root, cache_dir=None, now=None):
    """Offline, read-only projection; never initializes state or a connection."""
    n = now_value(now)
    try:
        c = config(root)
        if not c or not c['enabled']:
            return {'enabled': False, 'state': 'disabled', 'notice': None, 'network_attempted': False}
        selected = c['source']; stored = cached(cache_dir or default_cache(), selected)
        installed, present = project_state.local_version(Path(root))
        result = {'enabled': True, 'source': selected, 'installed_version': installed, 'state': 'unknown',
                  'checked_at': None, 'next_check_at': None, 'latest_version': None, 'notes_url': None,
                  'cache': 'missing', 'comparison': 'Unavailable', 'notice': 'Release status unknown; run the authorized release check.',
                  'network_attempted': False, 'update_authorized': False}
        if not stored: return result
        result.update(checked_at=stored['checked_at'], next_check_at=stored['next_check_at'], error=stored['error'])
        if n < stored['attempted_at']:
            result.update(cache='clock_error', notice='Clock moved backwards; reconcile local release state.'); return result
        r = stored['release']
        fresh = r is not None and stored['error'] is None and n-stored['checked_at'] < DAY
        result['cache'] = 'fresh' if fresh else 'stale' if r else 'missing'
        if r:
            result.update(latest_version=r['version'], notes_url=r['notes_url'],
                          comparison=version_status(installed, r['version'], present))
        if not fresh:
            result['notice'] = 'Release check unavailable or overdue; last known metadata is not current evidence.'
            return result
        result['state'] = result['comparison'].lower().replace(' ', '_')
        messages = {'update_available': 'Exocortex update available. Review release notes, remind later, or plan an update.',
                    'current': None, 'ahead_of_release': 'Installed version is ahead of the published release.',
                    'needs_attention': 'Installed version is unknown; inspect before considering an update.',
                    'not_installed': 'Exocortex version marker is absent; no update readiness inferred.'}
        result['notice'] = messages.get(result['state'])
        reminder = c['reminder']
        result['reminded_until'] = reminder['until'] if reminder and reminder['version'] == r['version'] and n < reminder['until'] else None
        if result['state'] == 'update_available' and result['reminded_until']:
            result['notice'] = None
        return result
    except (ReleaseError, OSError, project_state.Unavailable):
        return {'enabled': None, 'state': 'unavailable', 'notice': 'Release state cannot be inspected; preserve and reconcile it.', 'network_attempted': False}


def check(root, cache_dir=None, now=None, transport=None):
    c = config(root)
    if not c or not c['enabled']: return status(root, cache_dir, now)
    n = now_value(now); directory = cache_dir or default_cache(); selected = c['source']
    path = cache_path(directory, selected)
    with lock(path.with_suffix('.lock')):
        # Recheck consent after waiting for the per-source writer slot.
        if config(root) != c: raise ReleaseError('Configuration changed; no release check started')
        old = cached(directory, selected)
        if old and n < old['attempted_at']: raise ReleaseError('Clock moved backwards; no release check started')
        if old and n < old['next_check_at']: return status(root, directory, n)
        failures = min(100, (old['failures'] if old else 0)+1)
        entry = {'schema': SCHEMA, 'source': selected, 'attempted_at': n, 'next_check_at': n+DAY,
                 'failures': failures, 'error': 'check_interrupted', 'release': old['release'] if old else None,
                 'checked_at': old['checked_at'] if old else None}
        # Reserve the cadence before contacting the source; a crash cannot cause
        # every session to retry the same failed request.
        write(path, entry)
        release, error, retry = (transport or fetch)(selected)
        if error is None:
            # Apply the same strict shape validation to injected transports.
            if not isinstance(release, dict): raise ReleaseError('Invalid transport result')
            entry.update(release=release, checked_at=n, failures=0, error=None)
        else:
            if error not in ERRORS or type(retry) is not int: raise ReleaseError('Invalid transport result')
            entry.update(error=error, next_check_at=n+min(7*DAY, max(DAY*2**min(failures-1,3), retry)))
        write(path, entry)
    result = status(root, directory, n); result['network_attempted'] = True
    return result


def remind(root, expected_version, hours=24, cache_dir=None, now=None):
    n = now_value(now)
    if type(hours) is not int or not 1 <= hours <= 168: raise ReleaseError('Reminder must be 1 to 168 hours')
    with lock(Path(root)/'.exocortex/local/release-awareness/config.lock'):
        current = status(root, cache_dir, n); c = config(root)
        if current.get('state') != 'update_available' or current.get('latest_version') != expected_version:
            raise ReleaseError('Release notice changed; inspect before reminding later')
        c['reminder'] = {'version': expected_version, 'until': n+hours*3600}
        write(Path(root)/CONFIG, c)
    return status(root, cache_dir, n)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root', type=Path, default=Path.cwd())
    p.add_argument('--cache-dir', type=Path, help='Explicit machine cache; keep the same directory across projects')
    sub = p.add_subparsers(dest='action', required=True)
    for name in ('status', 'check', 'disable'): sub.add_parser(name)
    enable = sub.add_parser('enable'); enable.add_argument('--repository', required=True)
    later = sub.add_parser('remind'); later.add_argument('--version', required=True); later.add_argument('--hours', type=int, default=24)
    args = p.parse_args(argv)
    try:
        root = args.project_root.resolve()
        cache = args.cache_dir.absolute() if args.cache_dir else None
        if not root.is_dir(): raise ReleaseError('Project root unavailable')
        if args.action == 'enable': result = configure(root, args.repository)
        elif args.action == 'disable': result = configure(root, enabled=False)
        elif args.action == 'remind': result = remind(root, args.version, args.hours, cache)
        elif args.action == 'check': result = check(root, cache)
        else: result = status(root, cache)
        print(json.dumps(result, indent=2))
        return 2 if result.get('state') == 'unavailable' else 0
    except (ReleaseError, OSError):
        print('Release awareness unavailable; inspect the explicit source and local state without deleting records.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
