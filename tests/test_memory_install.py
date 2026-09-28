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
            for name in ['refresh_rollups.py', 'record_event.py', 'curate_memory.py', 'memory_gepa.py']:
                self.assertTrue((target / '.exocortex/scripts' / name).is_file(), result.stderr)
            self.assertTrue((target / '.exocortex/prompts/memory-curator.md').is_file())
            for name in ['train.json', 'validation.json', 'holdout.json', 'requirements.txt']:
                self.assertTrue((target / '.exocortex/evals/memory' / name).is_file())
            result = subprocess.run(['bash', str(target / '.exocortex/scripts/create_event.sh')],
                                    input='# Fictional install rehearsal\n\n## Outcome\nInstalled candidate.\n',
                                    text=True, capture_output=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([sys.executable, str(target / '.exocortex/scripts/refresh_rollups.py'),
                                     '--check', '--json'], capture_output=True, text=True, cwd=target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'fresh')
            context = (target / '.exocortex/SESSION_CONTEXT.md').read_bytes()
            update = fixture.safe_update_dry_run(source, target, root / 'backups')
            self.assertEqual(update.returncode, 0, update.stderr)
            self.assertIn('Dry run complete. Real target unchanged.', update.stdout)
            self.assertEqual((target / '.exocortex/SESSION_CONTEXT.md').read_bytes(), context)


if __name__ == '__main__':
    unittest.main()
