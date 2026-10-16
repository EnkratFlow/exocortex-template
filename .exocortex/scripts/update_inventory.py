#!/usr/bin/env python3
"""Read-only GitHub/local Exocortex inventory. No fetch, checkout, save or apply."""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import importlib.util
import sys
import os
from pathlib import Path
import re
import stat
import subprocess
from urllib.parse import quote


DEFAULT_TEMPLATE = 'EnkratFlow/exocortex-template'
SKIP = {'.git', '.exocortex', 'node_modules', 'vendor', '.venv', 'venv',
        'build', 'dist', '.next', '__pycache__', '.cache'}
REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')


sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location('exocortex_project_state', Path(__file__).with_name('project_state.py'))
state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(state)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_policy

Unavailable = state.Unavailable
run = state.run
ordinary = state.ordinary
local_version = state.local_version


def api(endpoint, paginate=False):
    args = ['gh', 'api', '--hostname', 'github.com', endpoint]
    if paginate:
        args += ['--paginate', '--slurp']
    try:
        return json.loads(run(args))
    except (ValueError, TypeError):
        raise Unavailable('Invalid GitHub response') from None


def version(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value.removeprefix('v') if re.fullmatch(r'v?\d+\.\d+\.\d+', value) else None


def status(installed, latest, present=True):
    if not present:
        return 'Not installed'
    if installed is None:
        return 'Needs attention'
    if latest is None:
        return 'Unavailable'
    a, b = (tuple(map(int, v.split('.'))) for v in (installed, latest))
    return 'Current' if a == b else ('Update available' if a < b else 'Ahead of release')


def github_name(remote):
    identity = state.remote_identity(remote)
    return identity[len('github.com/'):] if identity and identity.startswith('github.com/') else None


def discover(roots, depth):
    found, warnings = set(), []
    def walk(path, remaining, top=False):
        try:
            if not ordinary(path) or not path.is_dir():
                warnings.append('Skipped unavailable, linked or redirected folder: ' + str(path))
                return
            if (path / '.git').exists() or (path / '.exocortex').exists():
                found.add(path)
                if (path / '.git').exists() and not top:
                    return
            if remaining == 0:
                return
            children = sorted(path.iterdir())
        except OSError:
            warnings.append('Cannot list folder: ' + str(path))
            return
        for child in children:
            try:
                if child.name not in SKIP and ordinary(child) and child.is_dir():
                    walk(child, remaining - 1)
            except OSError:
                warnings.append('Cannot inspect folder: ' + str(child))
    for root in roots:
        walk(Path(os.path.abspath(root)), depth, top=True)
    # A parent-folder scan stops at repositories. Expand their Git registries
    # so nested provider worktrees and linked folders outside the scan roots
    # are still included, without traversing arbitrary hidden directories.
    visited, known = set(), {p.resolve() for p in found}
    for path in sorted(found):
        if not (path/'.git').exists():
            continue
        try:
            info = state.repository(path)
            if info['common_dir'] in visited:
                continue
            visited.add(info['common_dir'])
            linked = state.linked_worktree_paths(path)
            if len(linked) > state.MAX_WORKTREES:
                warnings.append('Git worktree registry truncated; some working folders were not inspected')
            for checkout in linked[:state.MAX_WORKTREES]:
                if checkout.resolve() in known:
                    continue
                try:
                    if not ordinary(checkout) or state.repository(checkout)['common_dir'] != info['common_dir']:
                        raise Unavailable('Registered checkout unavailable')
                    found.add(checkout)
                    known.add(checkout.resolve())
                except (Unavailable, OSError):
                    warnings.append('A registered working folder could not be inspected: '+str(checkout))
        except (Unavailable, OSError):
            warnings.append('Git worktree registry unavailable for: '+str(path))
    return sorted(found), warnings


def local_record(path, latest, template):
    installed, present = local_version(path)
    result = {'path': str(path), 'version': installed, 'status': status(installed, latest, present),
              'branch': None, 'dirty': None, 'repository': None, 'common_dir': None,
              'machine': state.machine_name()}
    try:
        item = state.checkout(path)
        result.update(item)
        result['path'] = str(path)
        # Keep the original inventory display identity for GitHub compatibility.
        identity = item['repository']
        result['repository'] = identity.removeprefix('github.com/') if identity else None
        result['status'] = status(item['version'], latest, item['installed'])
        if item['dirty']:
            result.update(status='Needs attention', reason='Uncommitted work; version comparison is informational')
    except (Unavailable, OSError, UnicodeError):
        result.update(status='Needs attention', reason='Git state unavailable or folder is not a Git repository')
    try:
        rules=update_policy.read(Path(path).resolve())
        result['update_policy']=rules
        if rules['mode']!='standard' or rules['protected_paths']:
            result.update(status='Needs attention',reason='Update policy requires separate review; not eligible for batch update')
    except (update_policy.PolicyError,OSError,ValueError):
        result.update(status='Needs attention',reason='Update policy unavailable or unsafe; separate review required',update_policy={'mode':'unavailable'})
    return result


def remote_record(repo, latest, template, get=api):
    name, branch = repo['full_name'], repo.get('default_branch')
    result = {'repository': name, 'id': repo['id'], 'branch': branch,
              'archived': bool(repo.get('archived')), 'fork': bool(repo.get('fork')),
              'version': None, 'status': 'Unavailable', 'selected': False}
    if not REPO.fullmatch(name) or not branch:
        result['reason'] = 'Repository identity or default branch unavailable'
        return result
    ref = '?ref=' + quote(branch, safe='')
    try:
        # Listing only metadata distinguishes absence from an inaccessible repo;
        # never read arbitrary project files or memories.
        entries = get('repos/' + name + '/contents' + ref)
        if not isinstance(entries, list):
            raise Unavailable('Default branch listing unavailable')
        is_template = name.lower() == template.lower()
        exo = next((e for e in entries if e.get('name') == '.exocortex'), None)
        if not is_template and exo is None:
            result['status'] = 'Not installed'
            return result
        if not is_template and exo.get('type') != 'dir':
            result.update(status='Needs attention', reason='Exocortex directory is not a regular directory')
            return result
        marker = 'VERSION' if is_template else '.exocortex/.version'
        if not is_template:
            contents = get('repos/' + name + '/contents/.exocortex' + ref)
            entry = next((e for e in contents if e.get('name') == '.version'), None)
        else:
            entry = next((e for e in entries if e.get('name') == 'VERSION'), None)
        if entry is None or entry.get('type') != 'file' or entry.get('size', 129) > 128:
            result.update(status='Needs attention', reason='Missing or invalid version marker')
            return result
        content = get('repos/' + name + '/contents/' + marker + ref)
        if content.get('type') != 'file' or content.get('encoding') != 'base64' or content.get('size', 129) > 128:
            raise Unavailable('Version marker unavailable')
        installed = version(base64.b64decode(content['content']).decode('utf-8'))
        result.update(version=installed, status=status(installed, latest))
    except (Unavailable, ValueError, KeyError, TypeError, AttributeError):
        result.update(status='Unavailable', reason='Could not read default-branch version; check access or retry')
    return result


def group_records(remotes, locals_):
    return state.group_projects(remotes, locals_)


def markdown(report, details=False):
    def cell(value):
        return str(value if value is not None else 'Unknown').replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
    lines = ['# Exocortex update inventory', '',
             f"Projects: {len(report['repositories'])}; working folders: {sum(len(g['local']) for g in report['repositories'])}.",
             'Machine: '+cell(report.get('scope', {}).get('machine'))+'. Other machines are not inspected.',
             'Local scope: selected roots plus their Git registered worktrees, regardless of assistant or folder name.',
             'Published version: ' + (report['latest_version'] or 'Unavailable'), '',
             'Read-only comparison. Update available does not mean approved or ready to apply.', '',
             '| Project | GitHub version | Local versions | Working folders | Needs attention |', '| --- | --- | --- | --- | --- |']
    for group in report['repositories']:
        remote = group['github']
        label = group['repository'] + (' (archived)' if remote and remote.get('archived') else '')
        attention = sum(x['status'] == 'Needs attention' for x in group['local'])
        remote_text = (str(remote.get('version') or 'Unknown')+' — '+remote.get('status', 'Unknown')) if remote else 'Not observed'
        local_versions = ', '.join(sorted({x['version'] or 'Unknown' for x in group['local']})) or 'Not inspected'
        lines.append('| ' + ' | '.join(map(cell, [label, remote_text, local_versions, len(group['local']), attention])) + ' |')
    if details:
        for group in report['repositories']:
            lines += ['', '## '+cell(group['repository']), '',
                      '| Machine | Working folder | Branch | Installed | Status |', '| --- | --- | --- | --- | --- |']
            for local in group['local']:
                lines.append('| ' + ' | '.join(map(cell, [local.get('machine'), local['path'], local['branch'] or 'Unknown', local['version'], local['status']])) + ' |')
    else:
        lines += ['', 'Use --details to expand working folders. JSON always includes checkout details.']
    if report['warnings']:
        lines += ['', '## Notices', ''] + ['- '+cell(w) for w in report['warnings']]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--github', action='store_true', help='Read repositories accessible to the current GitHub CLI account')
    parser.add_argument('--owner', action='append', default=[], help='Limit GitHub discovery to this owner (repeatable)')
    parser.add_argument('--root', action='append', default=[], help='Explicit local repository or parent folder (repeatable)')
    parser.add_argument('--depth', type=int, default=3, choices=range(0, 9))
    parser.add_argument('--template', default=DEFAULT_TEMPLATE)
    parser.add_argument('--latest-version', help='Offline comparison value; not authenticated release evidence')
    parser.add_argument('--details', action='store_true', help='Expand working folders beneath each project')
    parser.add_argument('--format', choices=('json', 'markdown'), default='markdown')
    args = parser.parse_args(argv)
    if not args.github and not args.root:
        parser.error('choose --github and/or an explicit --root')
    if not REPO.fullmatch(args.template):
        parser.error('template must be OWNER/REPO')
    if args.latest_version and not version(args.latest_version):
        parser.error('latest-version must be a stable X.Y.Z version')
    latest, warnings, remotes = version(args.latest_version), [], []
    if args.latest_version:
        warnings.append('Comparison version supplied by caller; release authenticity not verified')
    if args.github:
        if not latest:
            try:
                release = api('repos/' + args.template + '/releases/latest')
                latest = version(release.get('tag_name'))
                if release.get('draft') or release.get('prerelease') or latest is None:
                    raise Unavailable('No stable published release available')
            except (Unavailable, AttributeError):
                latest = None
                warnings.append('Published version unavailable; working offline or GitHub access failed')
        try:
            pages = api('user/repos?per_page=100&affiliation=owner,collaborator,organization_member&sort=full_name', paginate=True)
            repos = {r['id']: r for page in pages for r in page}
            owners = {o.lower() for o in args.owner}
            selected = [r for r in repos.values() if not owners or r['owner']['login'].lower() in owners]
            with ThreadPoolExecutor(max_workers=4) as pool:
                remotes = list(pool.map(lambda r: remote_record(r, latest, args.template), selected))
        except (Unavailable, TypeError, KeyError):
            warnings.append('GitHub repository inventory unavailable; local results remain usable')
    paths, local_warnings = discover(args.root, args.depth)
    warnings += local_warnings
    local = [local_record(p, latest, args.template) for p in paths]
    report = {'schema_version': 1, 'read_only': True,
              'observed_at': datetime.now(timezone.utc).isoformat(),
              'scope': {'github': args.github, 'owners': args.owner, 'machine': state.machine_name(),
                        'linked_worktrees': 'included via Git registry, including outside selected roots',
                        'other_machines': 'not inspected',
                        'local_roots': [os.path.abspath(p) for p in args.root], 'depth': args.depth},
              'latest_version': latest,
              'repositories': group_records(remotes, local), 'warnings': warnings}
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.format == 'json' else markdown(report, args.details))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
