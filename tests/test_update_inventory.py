"""Focused read-only inventory tests; fictional repositories and disposable Git."""
import base64
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('inventory', ROOT/'.exocortex/scripts/update_inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_numeric_versions(self):
        self.assertEqual(inventory.status('3.3.9', '3.3.11'), 'Update available')
        self.assertEqual(inventory.status('3.3.11', '3.3.11'), 'Current')
        self.assertEqual(inventory.status('3.4.0', '3.3.11'), 'Ahead of release')
        self.assertEqual(inventory.status('3.3.11', None), 'Unavailable')
        self.assertEqual(inventory.status(None, '3.3.11'), 'Needs attention')
        self.assertIsNone(inventory.version('v3.3.12-beta'))

    def test_remote_identity_redacts_credentials(self):
        for remote in ('https://github.com/example/project.git', 'ssh://github.com/example/project.git'):
            self.assertEqual(inventory.github_name(remote), 'example/project')
        self.assertEqual(inventory.state.remote_identity('https://fictional-user:fictional-password@git.example.invalid/example/project.git'),
                         'git.example.invalid/example/project')
        self.assertIsNone(inventory.github_name('https://github.com.other.invalid/example/project'))

    def test_remote_absent_unknown_and_current_are_distinct(self):
        repo = dict(full_name='example/project', id=1, default_branch='feature/test', archived=False)
        calls = []
        def api(endpoint):
            calls.append(endpoint)
            if '/contents?' in endpoint:
                return [dict(name='.exocortex', type='dir')]
            if '/contents/.exocortex?' in endpoint:
                return [dict(name='.version', type='file', size=7)]
            return dict(type='file', encoding='base64', size=7,
                        content=base64.b64encode(b'3.3.11\n').decode())
        result = inventory.remote_record(repo, '3.3.11', 'example/template', api)
        self.assertEqual(result['status'], 'Current')
        self.assertTrue(all('ref=feature%2Ftest' in p for p in calls))
        self.assertFalse(result['selected'])
        self.assertEqual(inventory.remote_record(repo, '3.3.11', 'example/template', lambda _: [])['status'], 'Not installed')
        def denied(_):
            raise inventory.Unavailable('denied')
        self.assertEqual(inventory.remote_record(repo, '3.3.11', 'example/template', denied)['status'], 'Unavailable')
        def missing_marker(p):
            return [dict(name='.exocortex', type='dir')] if '/contents?' in p else []
        self.assertEqual(inventory.remote_record(repo, '3.3.11', 'example/template', missing_marker)['status'], 'Needs attention')

    def test_symlink_marker_is_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'.exocortex').mkdir()
            target = root/'fixture.txt'
            target.write_text('3.3.11')
            try:
                (root/'.exocortex/.version').symlink_to(target)
            except OSError:
                self.skipTest('symlinks unavailable')
            self.assertEqual(inventory.local_version(root), (None, True))

    def test_unreadable_directory_is_not_absent_and_scan_continues(self):
        with patch.object(Path, 'lstat', side_effect=PermissionError):
            self.assertEqual(inventory.local_version(Path('unreadable')), (None, True))
            paths, warnings = inventory.discover(['unreadable'], 3)
            self.assertEqual(paths, [])
            self.assertEqual(len(warnings), 1)

    def test_git_monitor_disabled_and_error_details_not_exposed(self):
        response = subprocess.CompletedProcess([], 0, stdout='main\n', stderr='')
        with patch.object(subprocess, 'run', return_value=response) as call:
            self.assertEqual(inventory.run(['git', 'status', '--porcelain']), 'main\n')
            self.assertIn('core.fsmonitor=false', call.call_args.args[0])
            self.assertEqual(call.call_args.kwargs['env']['GIT_OPTIONAL_LOCKS'], '0')
        with patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'private-error-detail')):
            with self.assertRaises(inventory.Unavailable) as caught:
                inventory.run(['git', 'status'])
            self.assertNotIn('private-error-detail', str(caught.exception))

    def test_parent_memory_folder_does_not_hide_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'.exocortex').mkdir()
            child = root/'project'
            (child/'.git').mkdir(parents=True)
            paths, _ = inventory.discover([root], 3)
            self.assertEqual(set(paths), {root, child})

    def test_worktrees_grouped_and_source_files_unchanged(self):
        with tempfile.TemporaryDirectory(prefix='Inventory spaces ') as tmp:
            base = Path(tmp)
            repo, lane = base/'project', base/'project-review'
            repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], text=True, stderr=subprocess.DEVNULL)
            git('init', '-q')
            (repo/'.exocortex').mkdir()
            (repo/'.exocortex/.version').write_text('3.3.10\n')
            (repo/'.exocortex/PROJECT_MEMORY.md').write_text('Handwritten fixture memory\n')
            git('add', '.exocortex/.version', '.exocortex/PROJECT_MEMORY.md')
            git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
            git('remote', 'add', 'origin', 'https://github.com/example/project.git')
            git('worktree', 'add', '-qb', 'fixture-review', str(lane))
            memory = repo/'.exocortex/PROJECT_MEMORY.md'
            memory.write_text('Uncommitted handwritten fixture memory\n')
            ignored = base/'node_modules'/'ignored'
            (ignored/'.exocortex').mkdir(parents=True)
            non_git = base/'old project'
            (non_git/'.exocortex').mkdir(parents=True)
            (non_git/'.exocortex/.version').write_text('3.1.0')
            before = memory.read_bytes()
            index_before = (repo/'.git/index').read_bytes()
            paths, warnings = inventory.discover([base], 3)
            self.assertEqual(set(paths), {repo, lane, non_git})
            records = [inventory.local_record(p, '3.3.11', 'example/template') for p in paths]
            groups = inventory.group_records([], records)
            shared = next(g for g in groups if g['repository'] == 'example/project')
            self.assertEqual(len(shared['local']), 2)
            self.assertEqual(next(x for x in records if x['path'] == str(repo))['status'], 'Needs attention')
            self.assertEqual(next(x for x in records if x['path'] == str(lane))['status'], 'Update available')
            self.assertEqual(next(x for x in records if x['path'] == str(non_git))['status'], 'Needs attention')
            self.assertEqual(memory.read_bytes(), before)
            self.assertEqual((repo/'.git/index').read_bytes(), index_before)
            self.assertEqual(warnings, [])

    def test_compact_display_counts_projects_not_folders(self):
        report = {'latest_version': '3.3.11', 'warnings': [], 'repositories': [
            {'repository': 'example/project', 'github': None, 'local': [
                {'path': 'fixture-folder-one', 'branch': 'main', 'version': '3.3.10', 'status': 'Update available'},
                {'path': 'fixture-folder-two', 'branch': 'task', 'version': '3.3.9', 'status': 'Needs attention'}]}]}
        compact = inventory.markdown(report)
        self.assertIn('Projects: 1; working folders: 2', compact)
        self.assertIn('3.3.10', compact)
        self.assertNotIn('fixture-folder-one', compact)
        self.assertIn('fixture-folder-one', inventory.markdown(report, details=True))

    def test_parent_scan_includes_nested_claude_and_external_codex_worktrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            selected = base/'selected'
            repo = selected/'project'
            repo.mkdir(parents=True)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), '-c', 'core.hooksPath='+str(base/'no-hooks'),
                    '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args], text=True, stderr=subprocess.DEVNULL)
            git('init', '-q', '-b', 'main')
            git('commit', '--allow-empty', '-qm', 'Fixture')
            claude = repo/'.claude/worktrees/fixture-task'
            claude.parent.mkdir(parents=True)
            codex = base/'.codex/worktrees/fixture-task'
            codex.parent.mkdir(parents=True)
            git('worktree', 'add', '-qb', 'claude/fixture-task', str(claude))
            git('worktree', 'add', '-qb', 'codex/fixture-task', str(codex))
            paths, warnings = inventory.discover([selected], 1)
            self.assertEqual(set(paths), {repo, claude, codex})
            self.assertEqual(warnings, [])
            records = [inventory.local_record(p, None, 'example/template') for p in paths]
            groups = inventory.group_records([], records)
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0]['local']), 3)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(inventory.main(['--root', str(selected), '--depth', '1', '--format', 'json']), 0)
            scope = json.loads(output.getvalue())['scope']
            self.assertEqual(scope['other_machines'], 'not inspected')
            self.assertIn('outside selected roots', scope['linked_worktrees'])

    def test_github_failure_keeps_local_results_and_marks_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'.exocortex').mkdir()
            (root/'.exocortex/.version').write_text('3.3.10')
            output = io.StringIO()
            with patch.object(inventory, 'api', side_effect=inventory.Unavailable('offline')), redirect_stdout(output):
                result = inventory.main(['--github', '--root', str(root), '--format', 'json'])
            report = json.loads(output.getvalue())
            self.assertEqual(result, 0)
            self.assertIsNone(report['latest_version'])
            self.assertEqual(len(report['warnings']), 2)
            self.assertEqual(len(report['repositories']), 1)

    def test_paginated_repo_discovery_deduplicates_and_filters(self):
        repo = dict(full_name='example/project', id=1, default_branch='main', owner=dict(login='example'))
        other = dict(full_name='other/project', id=2, default_branch='main', owner=dict(login='other'))
        def api(endpoint, paginate=False):
            if endpoint.endswith('/releases/latest'):
                return dict(tag_name='v3.3.11', draft=False, prerelease=False)
            return [[repo], [repo, other]]
        output = io.StringIO()
        with patch.object(inventory, 'api', side_effect=api), patch.object(inventory, 'remote_record') as read, redirect_stdout(output):
            read.side_effect = lambda r, *_: dict(repository=r['full_name'], version=None)
            inventory.main(['--github', '--owner', 'example', '--format', 'json'])
        self.assertEqual(read.call_count, 1)
        self.assertEqual(len(json.loads(output.getvalue())['repositories']), 1)


if __name__ == '__main__':
    unittest.main()
