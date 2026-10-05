"""One disposable installation proves the memory code-plane is distributed."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_installer_security as fixture

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def test_installed_memory_save_and_coverage(self):
        with tempfile.TemporaryDirectory(prefix='memory-install-rehearsal-') as tmp:
            root = Path(tmp).resolve()
            # Rehearse the exact public package, excluding ignored local event
            # and experiment data that must never enter an installer source.
            source = root / 'source'
            source.mkdir()
            paths = [line.split('  ', 1)[1] for line in (ROOT / 'SHA256SUMS').read_text().splitlines()]
            for name in paths + ['SHA256SUMS']:
                self.assertFalse(Path(name).is_absolute() or '..' in Path(name).parts)
                original = ROOT / name
                self.assertFalse(original.is_symlink())
                destination = source / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, destination)
            target = fixture.new_target(root, 'target')
            result = fixture.install(source, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in ['refresh_rollups.py', 'record_event.py', 'curate_memory.py', 'brief_work.py', 'release_awareness.py', 'update_selected.py']:
                self.assertTrue((target / '.exocortex/scripts' / name).is_file(), result.stderr)
            self.assertTrue((target / '.exocortex/prompts/memory-curator.md').is_file())
            release_script = target / '.exocortex/scripts/release_awareness.py'
            result = subprocess.run([sys.executable, str(release_script), 'status'],
                                    capture_output=True, text=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['state'], 'disabled')
            self.assertFalse((target / '.exocortex/local/release-awareness').exists())
            self.assertTrue((target / '.agents/skills/help/SKILL.md').is_file())
            result = subprocess.run(['bash', str(target / '.exocortex/scripts/create_event.sh')],
                                    input='# Fictional install rehearsal\n\n## Outcome\nInstalled candidate.\n',
                                    text=True, capture_output=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([sys.executable, str(target / '.exocortex/scripts/refresh_rollups.py'),
                                     '--check', '--json'], capture_output=True, text=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'fresh')
            # Exercise the installed helper and template, not source-tree imports.
            brief_script = target / '.exocortex/scripts/brief_work.py'
            request_path = target / 'request.json'
            request_path.write_bytes((target / '.exocortex/templates/task-brief.json').read_bytes())
            result = subprocess.run([sys.executable, str(brief_script), 'create', 'example-task',
                                     '--input', str(request_path)], capture_output=True, text=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            task = json.loads(result.stdout)
            result = subprocess.run([sys.executable, str(brief_script), 'select', 'example-task',
                                     '--expected', task['sha256']], capture_output=True, text=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(['bash', str(target / '.exocortex/scripts/create_event.sh'),
                                     '--brief', 'example-task', '--brief-sha', task['sha256'],
                                     '--save-id', '10000000-0000-4000-8000-000000000001'],
                                    input='# Task draft ready for review\n', text=True, capture_output=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            brief_path = target / '.exocortex/planning/briefs/example-task/revision-000001.md'
            original_brief = brief_path.read_bytes()
            context = (target / '.exocortex/SESSION_CONTEXT.md').read_bytes()
            update = fixture.safe_update_dry_run(source, target, root / 'backups')
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertIn('Dry run complete. Real target unchanged.', update.stdout)
            self.assertEqual((target / '.exocortex/SESSION_CONTEXT.md').read_bytes(), context)
            self.assertEqual(brief_path.read_bytes(), original_brief)


if __name__ == '__main__':
    unittest.main()
