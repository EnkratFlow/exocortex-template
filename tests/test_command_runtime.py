"""Focused real-process daily-command tests; Windows runs PS5.1 and PS7 in CI."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.exocortex/scripts'
sys.path.insert(0, str(SCRIPTS))
import command_runtime as runtime
import refresh_rollups as memory


class Commands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='exo runtime ')
        self.root = Path(self.temp.name) / 'project space café'
        self.scripts = self.root / '.exocortex/scripts'
        self.scripts.mkdir(parents=True)
        for name in ('command_runtime.py', 'run_exocortex.ps1', 'run_exocortex.sh', 'refresh_rollups.py',
                     'record_event.py', 'onboard_evidence.py', 'get_shortterm_memory.py',
                     'get_longterm_memory.py', 'get_subconscious_memory.py', 'drill_memory.py', 'check_keys.py'):
            shutil.copy2(SCRIPTS / name, self.scripts / name)
        (self.root / '.exocortex/events').mkdir()
        (self.root / '.exocortex/PROJECT_MEMORY.md').write_text('Unique handwritten fact\n', encoding='utf-8')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
        self.env.pop('EXOCORTEX_PYTHON', None)
        self.env.pop('EXOCORTEX_SESSION_PYTHON', None)
        self.addCleanup(self.temp.cleanup)

    def run_command(self, *args, env=None):
        return subprocess.run([sys.executable, '-B', str(self.scripts / 'command_runtime.py'), *args],
                              cwd=self.temp.name, env=env or self.env, capture_output=True,
                              text=True, encoding='utf-8', timeout=20)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.root.rglob('*') if p.is_file() and '.git' not in p.parts}

    def test_read_commands_repeat_without_writes_or_shell_tools(self):
        before = self.snapshot()
        for command in ('brief', 'scrum', 'work', 'onboard', 'history', 'shortterm', 'longterm', 'subconscious'):
            for _ in range(2):
                started = time.monotonic()
                result = self.run_command(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertLess(time.monotonic() - started, 10, command)
        self.assertEqual(before, self.snapshot())

    def test_missing_git_is_explicit_not_false_clean(self):
        result = self.run_command('work', env=dict(self.env, PATH=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['git']['status'], 'unavailable')

    def test_save_preserves_unicode_and_handwritten_memory(self):
        body = Path(self.temp.name) / 'save café.txt'
        body.write_text('# Résumé\nA quoted "fact" and café.\n', encoding='utf-8-sig')
        result = self.run_command('save', '--body-file', str(body))
        self.assertEqual(result.returncode, 0, result.stderr)
        events = list((self.root / '.exocortex/events').glob('*.md'))
        self.assertEqual(len(events), 1)
        self.assertIn('A quoted "fact" and café.', events[0].read_text(encoding='utf-8'))
        self.assertEqual((self.root / '.exocortex/PROJECT_MEMORY.md').read_text(), 'Unique handwritten fact\n')
        self.assertEqual(self.run_command('refresh', '--check', '--json').returncode, 0)

    def test_save_refresh_failure_is_not_replayed_or_hidden(self):
        body = Path(self.temp.name) / 'save.txt'
        body.write_text('Saved once.\n')
        # Malformed managed block makes refresh fail after the event is recorded.
        (self.root / memory.CONTEXT).write_text(memory.START + '\n' + memory.START + '\n')
        result = self.run_command('save', '--body-file', str(body))
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn('do not save this event again', result.stderr)
        self.assertEqual(len(list((self.root / '.exocortex/events').glob('*.md'))), 1)

    def test_save_without_git_preserves_narrative_and_reports_gap(self):
        body = Path(self.temp.name) / 'save.txt'
        body.write_text('Do not lose this narrative.\n')
        result = self.run_command('save', '--body-file', str(body), env=dict(self.env, PATH=''))
        self.assertEqual(result.returncode, 0, result.stderr)
        event = next((self.root / '.exocortex/events').glob('*.md')).read_text(encoding='utf-8')
        self.assertIn('Do not lose this narrative.', event)
        self.assertIn('Git missing or timed out', event)

    def test_work_reads_events_once_and_detects_later_edit(self):
        event = self.root / '.exocortex/events/2026-01-01_00-00-00_fixture.md'
        event.write_text('# Evidence\nOriginal\n')
        memory.apply(self.root)
        original = memory.read_events
        with patch.object(runtime, 'ROOT', self.root), patch.object(memory, 'read_events', wraps=original) as reader:
            self.assertEqual(runtime.work()['coverage']['status'], 'fresh')
            self.assertEqual(reader.call_count, 1)
            event.write_text('# Evidence\nChanged\n')
            self.assertEqual(runtime.work()['coverage']['status'], 'stale')
            self.assertEqual(reader.call_count, 2)

    def test_history_treats_shell_text_as_literal(self):
        text = '$(touch unwanted); "literal"'
        (self.root / '.exocortex/events/2026-01-01_00-00-00_fixture.md').write_text('# Evidence\n' + text)
        result = self.run_command('history', '--keyword', text)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(json.loads(result.stdout)['events']), 1)
        self.assertFalse((self.root / 'unwanted').exists())

    def test_drill_does_not_wait_for_stdin(self):
        result = self.run_command('drill', 'literal topic')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_steps_have_both_platforms(self):
        for path in (ROOT / '.exocortex/commands').glob('*.json'):
            for step in json.loads(path.read_text(encoding='utf-8'))['steps']:
                if step['type'] == 'shell':
                    self.assertIn('run_exocortex.sh ', step['command'], path.name)
                    self.assertIn('run_exocortex.ps1 ', step['windows_command'], path.name)

    @unittest.skipIf(os.name == 'nt', 'POSIX launcher')
    def test_posix_exit_code_and_explicit_missing_runtime(self):
        launcher = ['bash', str(self.scripts / 'run_exocortex.sh')]
        result = subprocess.run(launcher + ['check-keys'], env=dict(self.env, EXOCORTEX_PYTHON=sys.executable), capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'No key was read', result.stdout)
        result = subprocess.run(launcher + ['brief'], env=dict(self.env, EXOCORTEX_PYTHON='/missing/python'), capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn(b'EXOCORTEX_PYTHON_UNAVAILABLE', result.stderr)


@unittest.skipUnless(os.name == 'nt', 'Native Windows required')
class Windows(Commands):
    def ps(self, text, env=None):
        script = Path(self.temp.name) / 'invoke.ps1'
        script.write_text(text, encoding='utf-8-sig')
        return subprocess.run([os.environ.get('EXOCORTEX_TEST_POWERSHELL', 'powershell.exe'),
                               '-NoProfile', '-NonInteractive', '-File', str(script)],
                              env=env or self.env, capture_output=True, text=True, encoding='utf-8',
                              errors='replace', timeout=30)

    @staticmethod
    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    def test_native_arguments_and_exit_code(self):
        (self.scripts / 'probe_arguments.py').write_text('import json,sys\nprint(json.dumps(sys.argv[1:],ensure_ascii=True))\nsys.exit(7)\n')
        arguments = ['', 'space value', 'café', 'a"b', 'ends\\', '"\\"', '$(not executed)']
        text = '$env:EXOCORTEX_PYTHON = ' + self.quote(sys.executable) + '\n& ' + self.quote(self.scripts / 'run_exocortex.ps1') + ' script probe_arguments.py ' + ' '.join(map(self.quote, arguments)) + '\nexit $LASTEXITCODE\n'
        result = self.ps(text)
        self.assertEqual(result.returncode, 7, result.stderr)
        self.assertEqual(json.loads(result.stdout), arguments)

    def test_native_discovery_repeat_no_bash_gh_or_git(self):
        # PATH has Python and Windows only, not Git for Windows/Bash/gh.
        env = dict(self.env, PATH=str(Path(sys.executable).parent) + ';' + os.environ['SystemRoot'] + '\\System32')
        launcher = self.quote(self.scripts / 'run_exocortex.ps1')
        shell = shutil.which(os.environ.get('EXOCORTEX_TEST_POWERSHELL', 'powershell.exe'))
        env['EXOCORTEX_TEST_POWERSHELL'] = shell
        # ps() gets the shell from process env, so use an absolute configured runner below.
        with patch.dict(os.environ, EXOCORTEX_TEST_POWERSHELL=shell):
            result = self.ps('& ' + launcher + ' brief\nif ($LASTEXITCODE) { exit $LASTEXITCODE }\n' +
                             '$first = $env:EXOCORTEX_SESSION_PYTHON\n& ' + launcher + ' work\n' +
                             'if ($LASTEXITCODE) { exit $LASTEXITCODE }\n' +
                             'if (!$first -or $first -ne $env:EXOCORTEX_SESSION_PYTHON) { exit 9 }\n', env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('project_root', result.stdout)
        self.assertIn('café', result.stdout)
        self.assertNotIn('__pycache__', str(self.snapshot()))

    def test_native_explicit_missing_python_stops(self):
        result = self.ps('& ' + self.quote(self.scripts / 'run_exocortex.ps1') + ' brief\nexit $LASTEXITCODE\n',
                         dict(self.env, EXOCORTEX_PYTHON='C:\\missing\\python.exe'))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('EXOCORTEX_PYTHON_UNAVAILABLE', result.stderr)

    def test_native_unicode_interpreter_path(self):
        import venv
        folder = Path(self.temp.name) / 'runtime café space'
        venv.EnvBuilder(with_pip=False).create(folder)
        python = folder / 'Scripts/python.exe'
        result = self.ps('& ' + self.quote(self.scripts / 'run_exocortex.ps1') + ' brief\nexit $LASTEXITCODE\n',
                         dict(self.env, EXOCORTEX_PYTHON=str(python)))
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
