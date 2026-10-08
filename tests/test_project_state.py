"""Focused project/location and portable-memory regressions in fictional Git repos."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]/'.exocortex/scripts'
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
import project_state as state
import record_event
import refresh_rollups as memory


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), '-c', 'core.hooksPath='+str(root/'.no-hooks'),
                                    '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args],
                                   text=True, stderr=subprocess.DEVNULL).strip()


def tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and not p.is_symlink()}


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='project state ')
        self.base = Path(self.temp.name).resolve()
        self.root = self.base/'project'
        self.root.mkdir()
        git(self.root, 'init', '-q', '-b', 'main')
        (self.root/'.exocortex/events').mkdir(parents=True)
        (self.root/'.exocortex/.version').write_text('3.3.11\n')
        (self.root/'.gitignore').write_text('.exocortex/local/\n.exocortex/SESSION_CONTEXT.md.backup\n')
        (self.root/'.exocortex/PROJECT_MEMORY.md').write_text('Shared handwritten memory.\n')
        git(self.root, 'add', '.exocortex/.version', '.exocortex/PROJECT_MEMORY.md', '.gitignore')
        git(self.root, 'commit', '-qm', 'Initial fixture')

    def tearDown(self):
        self.temp.cleanup()

    def lane(self):
        target = self.base/'task folder'
        git(self.root, 'worktree', 'add', '-qb', 'task', str(target))
        return target

    def test_worktrees_one_project_read_only_including_git_index(self):
        lane = self.lane()
        (lane/'local.txt').write_text('Uncommitted fixture')
        before = tree(self.base)
        report = state.collect(self.root)
        self.assertEqual(len(report['checkouts']), 2)
        self.assertEqual(len({x['project_id'] for x in report['checkouts']}), 1)
        self.assertEqual(sum(x['dirty'] for x in report['checkouts']), 1)
        self.assertEqual(tree(self.base), before)
        self.assertFalse(report['network'])
        self.assertTrue(all(x['pushed'].startswith('unknown') for x in report['checkouts']))
        self.assertIn('unknown', report['verdict'])

    def test_remote_identity_portable_and_forks_separate(self):
        git(self.root, 'remote', 'add', 'origin', 'https://github.com/example/project.git')
        clone = self.base/'clone'
        git(self.root, 'clone', '-q', str(self.root), str(clone))
        git(clone, 'remote', 'set-url', 'origin', 'ssh://github.com/example/project.git')
        self.assertEqual(state.repository(self.root)['project_id'], state.repository(clone)['project_id'])
        git(clone, 'remote', 'set-url', 'origin', 'https://github.com/fork-owner/project.git')
        self.assertNotEqual(state.repository(self.root)['project_id'], state.repository(clone)['project_id'])
        self.assertEqual(state.remote_identity('ssh://git@git.example.invalid/team/project.git'), 'git.example.invalid/team/project')

    def test_claude_and_codex_worktrees_share_project_and_explicit_scope(self):
        codex = self.lane()
        claude = self.root/'.claude/worktrees/fixture-task'
        claude.parent.mkdir(parents=True)
        git(self.root, 'worktree', 'add', '-qb', 'claude/fixture-task', str(claude))
        before = tree(self.base)
        with patch.object(state, 'machine_name', return_value='fixture-machine'):
            report = state.collect(self.root)
            portable = state.portable_snapshot(self.root)
        self.assertEqual({r['path'] for r in report['checkouts']}, {str(p) for p in (self.root, codex, claude)})
        self.assertEqual(len({r['project_id'] for r in report['checkouts']}), 1)
        self.assertEqual(report['scope']['other_machines'], 'not inspected')
        self.assertEqual(report['scope']['machine'], 'fixture-machine')
        self.assertIn('Other clones and machines are not inspected', state.markdown(report))
        self.assertNotIn('fixture-machine', json.dumps(portable))
        self.assertEqual(tree(self.base), before)

    def test_remote_userinfo_is_never_reported(self):
        self.assertEqual(state.remote_identity('https://fictional:do-not-display@git.example.invalid/example/project.git'), 'git.example.invalid/example/project')
        self.assertIsNone(state.remote_identity('https://github.com/example/project?credential=fictional'))
        self.assertIsNone(state.remote_identity('file:///private/local/repository'))
        self.assertIsNone(state.remote_identity('https://host.invalid/../project'))

    def test_dirty_counts_rename_and_untracked(self):
        git(self.root, 'mv', '.exocortex/PROJECT_MEMORY.md', '.exocortex/LESSONS.md')
        (self.root/'scratch.txt').write_text('local')
        result = state.working_counts(self.root)
        self.assertEqual(result['staged'], 1)
        self.assertEqual(result['untracked'], 1)

    def test_detached_checkout_keeps_commit_identity(self):
        lane = self.lane()
        git(lane, 'switch', '--detach')
        result = state.checkout(lane)
        self.assertIsNone(result['branch'])
        self.assertEqual(result['head'], git(lane, 'rev-parse', 'HEAD'))
        self.assertIn('unknown', result['process_use'])

    def test_cached_non_main_default_and_version_drift(self):
        lane = self.lane()
        (self.root/'.exocortex/.version').write_text('3.3.12\n')
        git(self.root, 'add', '.exocortex/.version')
        git(self.root, 'commit', '-qm', 'New template fixture')
        git(self.root, 'update-ref', 'refs/remotes/origin/trunk', 'HEAD')
        git(self.root, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/trunk')
        result = state.checkout(lane)
        self.assertEqual(result['trunk']['ref'], 'refs/remotes/origin/trunk')
        self.assertEqual(result['divergence']['behind'], 1)
        self.assertTrue(result['version_differs_from_trunk'])
        self.assertFalse(result['trunk']['fresh_remote'])

    def test_context_switch_and_commit_invalidate_without_writing(self):
        memory.apply(self.root)
        old_context = (self.root/memory.CONTEXT).read_bytes()
        old_receipt = (self.root/memory.RECEIPT).read_bytes()
        git(self.root, 'switch', '-c', 'unfinished')
        result = memory.check(self.root)
        self.assertIn('checkout_changed', result['reasons'])
        self.assertEqual((self.root/memory.CONTEXT).read_bytes(), old_context)
        self.assertEqual((self.root/memory.RECEIPT).read_bytes(), old_receipt)
        memory.apply(self.root)
        self.assertIn('branch unfinished', (self.root/memory.CONTEXT).read_text())
        self.assertEqual(memory.check(self.root)['status'], 'fresh')
        (self.root/'code.txt').write_text('New commit fixture')
        git(self.root, 'add', 'code.txt')
        git(self.root, 'commit', '-qm', 'Advance head')
        self.assertIn('checkout_changed', memory.check(self.root)['reasons'])

    def test_shared_history_push_clone_and_scoped_unfinished_notes(self):
        git(self.root, 'switch', '-c', 'unfinished')
        body = '# Unfinished task\nImplementation is pending.\n'
        save_id = '00000000-0000-4000-8000-000000000007'
        source = record_event.record(self.root, body, save_id=save_id)
        event = source.read_text()
        self.assertNotIn(str(self.root), event)
        self.assertIn('work_scope:', event)
        self.assertIn('not yet committed or pushed', event)
        git(self.root, 'add', str(source.relative_to(self.root)))
        git(self.root, 'commit', '-qm', 'Share unfinished task narrative')
        remote = self.base/'remote.git'
        git(self.root, 'init', '-q', '--bare', str(remote))
        git(self.root, 'remote', 'add', 'origin', str(remote))
        git(self.root, 'push', '-q', 'origin', 'unfinished')
        clone = self.base/'other computer'
        git(self.root, 'clone', '-q', '-c', 'core.autocrlf=true', '--branch', 'unfinished', str(remote), str(clone))
        cloned_event = clone/source.relative_to(self.root)
        self.assertIn(b'\r\n', cloned_event.read_bytes())
        self.assertEqual(cloned_event.read_text(), source.read_text())
        before = cloned_event.read_bytes()
        self.assertEqual(record_event.record(clone, body, save_id=save_id), cloned_event)
        self.assertEqual(cloned_event.read_bytes(), before)
        git(clone, 'switch', '-c', 'review')
        memory.apply(clone)
        context = (clone/memory.CONTEXT).read_text()
        self.assertIn('Different branch; unfinished work is not assumed present here', context)
        self.assertIn('not proof of merged or deployed changes', context)
        self.assertNotIn(str(clone), context)
        self.assertEqual(memory.check(clone)['status'], 'fresh')
        cloned_event.write_bytes(before.replace(b'Implementation is pending.', b'Implementation is complete.'))
        with self.assertRaisesRegex(ValueError, 'Saved event changed'):
            record_event.record(clone, body, save_id=save_id)

    def test_dirty_save_is_allowed_and_portable_metadata_has_no_paths(self):
        (self.root/'unfinished.txt').write_text('Unfinished fixture')
        event = record_event.record(self.root, '# Save\nStill working.')
        scope = json.loads(next(x[12:] for x in event.read_text().splitlines() if x.startswith('work_scope: ')))
        self.assertGreater(scope['working']['untracked'], 0)
        self.assertNotIn('path', json.dumps(scope))
        self.assertIn('unknown', scope['deployment'])
        memory.apply(self.root)
        self.assertEqual(memory.check(self.root)['status'], 'fresh')

    def test_unique_notes_duplicates_and_conflicts_preserved(self):
        lane = self.lane()
        (lane/'.exocortex/events').mkdir(exist_ok=True)
        (lane/'.exocortex/events/2026-01-01_unique.md').write_text('# Unique event\nOnly here.')
        (lane/'.exocortex/PROJECT_MEMORY.md').write_text('Divergent task notes.')
        before = tree(self.base)
        report = state.collect(self.root, include_memory=True)
        target = next(x for x in report['checkouts'] if x['path'] == str(lane))
        self.assertIn('events/2026-01-01_unique.md', target['memory']['unique_in_inspected_checkouts'])
        self.assertIn('PROJECT_MEMORY.md', target['memory']['unique_in_inspected_checkouts'])
        self.assertIn('PROJECT_MEMORY.md', target['memory']['conflicting_names'])
        self.assertIn('not authorized', target['memory']['retirement'])
        self.assertEqual(tree(self.base), before)

    def test_linked_memory_and_limits_are_unknown_not_safe(self):
        other = self.base/'outside.md'
        other.write_text('Must not be read')
        link = self.root/'.exocortex/events/2026-01-01_link.md'
        try:
            link.symlink_to(other)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with patch.object(state, 'MAX_MEMORY_FILES', 0):
            self.assertFalse(state.memory_inventory(self.root)['complete'])
        self.assertFalse(state.memory_inventory(self.root)['complete'])

    def test_same_branch_other_clone_and_fork_scope(self):
        git(self.root, 'remote', 'add', 'origin', 'https://github.com/example/project.git')
        (self.root/'unfinished.txt').write_text('Not shared with the clone')
        source = record_event.record(self.root, '# Unfinished source work')
        git(self.root, 'add', str(source.relative_to(self.root)))
        git(self.root, 'commit', '-qm', 'Share the note only')
        clone = self.base/'second-clone'
        git(self.root, 'clone', '-q', str(self.root), str(clone))
        git(clone, 'remote', 'set-url', 'origin', 'https://github.com/example/project.git')
        memory.apply(clone)
        context = (clone/memory.CONTEXT).read_text()
        self.assertIn('Different working folder', context)
        self.assertIn('Uncommitted work existed at save', context)
        self.assertIn('Recorded at another commit', context)
        self.assertNotIn('Different project identity', context)
        self.assertFalse((clone/'unfinished.txt').exists())
        git(clone, 'remote', 'set-url', 'origin', 'https://github.com/other-owner/project.git')
        memory.apply(clone)
        self.assertIn('Different project identity', (clone/memory.CONTEXT).read_text())

    def test_onboard_refuses_symlink_sources(self):
        import onboard_evidence
        outside = self.base/'outside.md'
        outside.write_text('External fixture must not be read')
        link = self.root/'.exocortex/events/2026-01-01_link.md'
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with patch.object(Path, 'open', side_effect=AssertionError('must refuse before opening')):
            self.assertIsNone(onboard_evidence.read_text(link))

    def test_onboard_refuses_linked_directories_before_enumeration(self):
        import onboard_evidence
        outside = self.base/'outside'
        outside.mkdir()
        (outside/'2026-01-01_private-name.md').write_text('External fixture')
        events = self.root/'.exocortex/events'
        events.rmdir()
        control = self.root/'.exocortex/control'
        try:
            events.symlink_to(outside, target_is_directory=True)
            control.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        original = Path.iterdir
        def guarded(path):
            if path in (events, control, outside):
                raise AssertionError('Linked directory must not be enumerated')
            return original(path)
        with patch.object(Path, 'iterdir', guarded):
            result = onboard_evidence.collect(self.root)
        self.assertIn('memory_inspection_unavailable', result['readiness']['material_gaps'])
        self.assertNotIn('private-name', json.dumps(result))

    def test_automatic_event_history_does_not_copy_commit_subjects(self):
        git(self.root, 'commit', '--allow-empty', '-qm', 'Fixture source '+str(self.root))
        path = record_event.record(self.root, '# Portable narrative')
        text = path.read_text()
        self.assertNotIn(str(self.root), text)
        self.assertIn(git(self.root, 'rev-parse', 'HEAD'), text)

    def test_onboard_linked_files_mark_evidence_incomplete(self):
        import onboard_evidence
        outside = self.base/'outside.md'
        outside.write_text('External fixture must not be read')
        event = self.root/'.exocortex/events/2026-01-01_link.md'
        todo = self.root/'.exocortex/TODO.md'
        try:
            event.symlink_to(outside)
            todo.symlink_to(outside)
        except OSError:
            self.skipTest('Symlinks unavailable')
        result = onboard_evidence.collect(self.root)
        self.assertIn('events_inspection_unavailable', result['errors'])
        self.assertIn('records_inspection_unavailable', result['errors'])
        self.assertIn('memory_inspection_unavailable', result['readiness']['material_gaps'])
        self.assertNotIn('External fixture', json.dumps(result))

    def test_onboard_enumeration_failures_mark_evidence_incomplete(self):
        import onboard_evidence
        events = self.root/'.exocortex/events'
        control = self.root/'.exocortex/control'
        control.mkdir()
        original = Path.iterdir
        def denied(path):
            if path in (events, control):
                raise PermissionError('Fictional unreadable directory')
            return original(path)
        with patch.object(Path, 'iterdir', denied):
            result = onboard_evidence.collect(self.root)
        self.assertIn('events_inspection_unavailable', result['errors'])
        self.assertIn('records_inspection_unavailable', result['errors'])
        self.assertIn('memory_inspection_unavailable', result['readiness']['material_gaps'])

    def test_command_wiring_and_generic_public_assets(self):
        root = SCRIPTS.parents[1]
        where = json.loads((root/'.exocortex/commands/where.json').read_text())
        self.assertEqual(where['protocol']['default_role'], 'read_only')
        self.assertIn('project_state.py', json.dumps(where))
        # Daily commands use the shared collector, without scanning every worktree.
        self.assertIn('task_brief', (root/'.exocortex/commands/work.json').read_text())
        self.assertIn('project_state.current_report', (SCRIPTS/'onboard_evidence.py').read_text())
        # Public fixtures derive paths at runtime; code never embeds the host checkout.
        self.assertNotIn(str(root), (SCRIPTS/'project_state.py').read_text())


if __name__ == '__main__':
    unittest.main()
