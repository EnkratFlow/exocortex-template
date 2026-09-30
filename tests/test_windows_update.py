"""Native Windows install and guarded update, through the PowerShell launcher."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.exocortex/scripts'))
import authority_guard as guard
import orchestrate_work_item as orchestrator
import prepare_update_reconciliation as reconciliation


def run(args, cwd):
    result = subprocess.run([str(a) for a in args], cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(f'{args[0]} failed ({result.returncode})\n{result.stdout}\n{result.stderr}')
    return result.stdout


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2) + '\n').encode())


@unittest.skipUnless(os.name == 'nt', 'native Windows integration')
class WindowsUpdateTests(unittest.TestCase):
    def test_windows_filename_aliases_are_rejected_before_open(self):
        for name in ('credentials.', '.env ', 'value.json:stream', 'NUL.json', 'COM1', 'folder./value.json'):
            with self.subTest(name=name), self.assertRaises(guard.ProtocolError):
                orchestrator.canonical_local_protocol_input(Path('.exocortex/local/protocol/inbox')/name, 'fixture')

    def test_reconciliation_candidate_modes_and_copy(self):
        digest = hashlib.sha256((ROOT/'SHA256SUMS').read_bytes()).hexdigest()
        checksums = reconciliation.checksum_map(ROOT, digest)
        modes = reconciliation.candidate_mode_map(ROOT, checksums)
        self.assertEqual(modes['install.sh'], '0755')
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)/'copied.sh'
            reconciliation.atomic_copy(ROOT/'install.sh', destination, '0755', checksums['install.sh'])
            self.assertEqual(destination.read_bytes(), (ROOT/'install.sh').read_bytes())

    def test_protocol_input_binary_and_junction_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inbox = root / '.exocortex/local/protocol/inbox'
            inbox.mkdir(parents=True)
            content = b'first\r\n\x1alast'
            (inbox/'binary.json').write_bytes(content)
            relative = '.exocortex/local/protocol/inbox/binary.json'
            self.assertEqual(orchestrator.read_local_protocol_input(root, Path(relative), 'fixture'), content)
            os.link(inbox/'binary.json', inbox/'hardlink.json')
            with self.assertRaises(guard.ProtocolError):
                orchestrator.read_local_protocol_input(root, Path(relative), 'fixture')
            (inbox/'hardlink.json').unlink()
            outside = root/'outside'; outside.mkdir()
            (outside/'value.json').write_bytes(b'{}')
            junction = inbox/'junction'
            run(['cmd.exe','/c','mklink','/J',junction,outside],root)
            try:
                with self.assertRaises(guard.ProtocolError):
                    orchestrator.read_local_protocol_input(root, Path('.exocortex/local/protocol/inbox/junction/value.json'), 'fixture')
            finally:
                junction.rmdir()

    def test_install_bootstrap_update_and_memory(self):
        with tempfile.TemporaryDirectory(prefix='Exocortex Windows ') as temporary:
            base = Path(temporary)
            primary = base / 'primary'
            target = base / 'work tree'
            primary.mkdir()
            run(['git', 'init', '-q', primary], base)
            run(['git', 'config', 'user.name', 'Windows fixture'], primary)
            run(['git', 'config', 'user.email', 'fixture@example.invalid'], primary)
            run(['git', 'config', 'core.autocrlf', 'false'], primary)
            (primary / 'README.md').write_bytes(b'# Fictional project\n')
            run(['git', 'add', 'README.md'], primary)
            run(['git', 'commit', '-qm', 'fixture'], primary)
            run(['git', 'worktree', 'add', '-b', 'fixture-update', target], primary)
            launcher = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ROOT / 'scripts/windows.ps1']
            print('INSTALL', flush=True)
            run(launcher + ['install', 'fictional-project'], target)
            handwritten = target / '.exocortex/PROJECT_MEMORY.md'
            handwritten.write_bytes(b'# Handwritten memory\nKeep these local notes.\n')
            event = target / '.exocortex/events/2026-01-01_00-00-00_fixture.md'
            event.parent.mkdir(exist_ok=True)
            event.write_bytes(b'# Earlier work\nPreserve this event.\n')
            preserved = {p: p.read_bytes() for p in (handwritten, event)}
            # Model a previous installed version using its exact managed-file receipt.
            script = target / '.exocortex/scripts/read_memory_stack.sh'
            script.write_bytes(b'#!/bin/bash\necho old-fixture\n')
            manifest = target / '.exocortex/.install-manifest'
            text = manifest.read_text()
            lines = []
            for line in text.splitlines():
                if line.startswith('.exocortex/scripts/read_memory_stack.sh '):
                    line = '.exocortex/scripts/read_memory_stack.sh ' + hashlib.sha256(script.read_bytes()).hexdigest()
                lines.append(line)
            manifest.write_bytes(('\n'.join(lines)+'\n').encode())
            run(['git', 'add', '.'], target)
            run(['git', 'commit', '-qm', 'installed fixture baseline'], target)
            print('DRY RUN', flush=True)
            dry = run(launcher + ['update', '--backup-dir', str(base / 'backups'), '--dry-run'], target)
            print(dry, flush=True)
            lines = dry.splitlines()
            start = next(i for i,l in enumerate(lines) if l.startswith('Rehearsal changed paths:')) + 1
            paths = []
            for line in lines[start:]:
                if line.startswith('Dry run complete.'):
                    break
                if line.strip(): paths.append(line.strip())
            self.assertTrue(paths)
            actor = {'surface_id':'windows-codex','executor_id':'fixture-writer','adapter_version':'fixture-v1'}
            envelope = {
                'schema_version':'public-v2','kind':'local_delivery_envelope',
                'envelope_id':'windows-update','work_item_id':'windows-update',
                'title':'Windows update fixture','type':'maintenance','project_root':str(target.resolve()),
                'branch':'fixture-update','base_sha':run(['git','rev-parse','HEAD'],target).strip(),
                'allowed_paths':paths,'outcome':'Update fictional Windows project.','risk':'low',
                'rollback':'Restore fixture backup.','verification':['Memory preserved and no update changes remain.'],
                'exclusions':['No external systems.'],'writer':actor,
                'reviewer':{'surface_id':'windows-review','executor_id':'fixture-review','adapter_version':'fixture-v1'},
                'approval':{'approved_by':'fixture-owner','accepted_at':'2026-01-01T00:00:00Z','expires_at':'2099-01-01T00:00:00Z','summary':'Fictional Windows test.'},
                'lease_expires_at':'2099-01-01T00:00:00Z'
            }
            inbox = '.exocortex/local/protocol/inbox/windows.json'
            write(target / inbox, envelope)
            print('BOOTSTRAP', flush=True)
            run([sys.executable,ROOT/'.exocortex/scripts/orchestrate_work_item.py','bootstrap-local-delivery',
                 '--project-root',target,'--envelope-source',inbox,'--request-id','windows-bootstrap'], target)
            registry=json.loads((target/'.exocortex/control/EXECUTOR_REGISTRY.json').read_text())
            digest=hashlib.sha256((ROOT/'SHA256SUMS').read_bytes()).hexdigest()
            cap={
                'schema_version':'public-v2','kind':'approval_capability','capability_id':'windows-apply',
                'work_item_id':'windows-update','work_item_revision':0,'operation':'apply_template_update',
                'scope':{'allowed_paths':paths,'target_sha':digest},
                'executor':dict(actor,guard_digest=guard.current_guard_digest(),registry_version=registry['registry_version']),
                'approval':dict(envelope['approval'],one_time=True),
                'status':{'state':'active','revoked_at':None,'consumed_at':None,'consumed_by_request_id':None}
            }
            capability='.exocortex/local/protocol/capabilities/windows-apply.json'
            write(target/capability,cap)
            print('APPLY', flush=True)
            run(launcher+['update','--backup-dir',str(base/'backups'),'--apply','--capability',capability,
                '--work-item-id','windows-update','--work-item-revision','0','--request-id','windows-apply',
                '--surface-id',actor['surface_id'],'--executor-id',actor['executor_id'],'--adapter-version',actor['adapter_version']],target)
            for path,content in preserved.items(): self.assertEqual(path.read_bytes(),content)
            after=run(launcher+['update','--backup-dir',str(base/'backups'),'--dry-run'],target)
            self.assertIn('Rehearsal changed paths: 0', after)
            print('SAVE AND REFRESH', flush=True)
            body=base/'event.md'; body.write_bytes(b'# Windows update test\n\nMemory retained.\n')
            run([sys.executable,target/'.exocortex/scripts/record_event.py','--body-file',body],target)
            result=run([sys.executable,target/'.exocortex/scripts/refresh_rollups.py','--check','--json'],target)
            self.assertEqual(json.loads(result)['status'],'fresh')
            self.assertIn(b'Keep these local notes.',handwritten.read_bytes())

if __name__ == '__main__':
    unittest.main()
