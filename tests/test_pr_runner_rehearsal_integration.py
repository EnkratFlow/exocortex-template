"""Real container/installer/guard/freezer fixture, with provider I/O substituted.

Opt in with an already built immutable EXOCORTEX_REHEARSAL_TEST_IMAGE. No real
account, repository write, published release claim or credential is involved.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/update-dashboard'))
sys.path.insert(0,str(ROOT/'.exocortex/scripts'))
import authority_guard as guard
import pr_runner as runner
import pr_runner_rehearsal_host as host
from pr_runner_isolation import DockerPreview, DockerRehearsal, IsolationError
from pr_runner_prepare import updater
import test_installer_security as fixture
from test_selected_update_integration import run, write


@unittest.skipUnless(os.name=='posix' and os.environ.get('EXOCORTEX_REHEARSAL_TEST_IMAGE'),
                     'Explicit immutable disposable Docker test image required')
class ContainerRehearsalTests(unittest.TestCase):
    def exercise(self, lost_apply_reply=False):
        with tempfile.TemporaryDirectory(prefix='rehearsal-fixture-') as tmp:
            base=Path(tmp).resolve();source=base/'source';source.mkdir()
            for row in (ROOT/'SHA256SUMS').read_text().splitlines()+['  SHA256SUMS']:
                rel=row.split('  ',1)[1];dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/rel,dest)
            target=fixture.new_target(base,'checkout')
            result=fixture.install(source,target)
            self.assertEqual(result.returncode,0,result.stderr)
            run(['git','config','user.name','Fixture'],target)
            run(['git','config','user.email','fixture@example.invalid'],target)
            run(['git','symbolic-ref','HEAD','refs/heads/fixture-update'],target)
            run(['git','remote','add','origin','https://github.com/example/disposable.git'],target)
            memory=target/'.exocortex/PROJECT_MEMORY.md';memory.write_text('# Fictional project memory\nPreserve this.\n')
            knowledge=target/'.exocortex/knowledge/KNOWLEDGE.md';knowledge.parent.mkdir(exist_ok=True)
            knowledge.write_text('# Fictional knowledge\nHistorical evidence only.\n')
            app=target/'application.txt';app.write_text('Fictional app: unchanged\n')
            script=target/'.exocortex/scripts/read_memory_stack.sh';script.write_text('#!/bin/bash\necho old-fixture\n')
            manifest=target/'.exocortex/.install-manifest'
            rows=[('.exocortex/scripts/read_memory_stack.sh '+hashlib.sha256(script.read_bytes()).hexdigest())
                  if x.startswith('.exocortex/scripts/read_memory_stack.sh ') else x for x in manifest.read_text().splitlines()]
            manifest.write_text('\n'.join(rows)+'\n')
            run(['git','add','.'],target);run(['git','commit','-qm','Fictional installed baseline'],target)
            head=run(['git','rev-parse','HEAD'],target)
            preserved={str(p):p.read_bytes() for p in (memory,knowledge,app)}
            root=base/'controller';backup=base/'backups';root.mkdir(mode=0o700);backup.mkdir(mode=0o700)
            sha=hashlib.sha256((source/'SHA256SUMS').read_bytes()).hexdigest()
            release=dict(repository='example/template',tag='v4.0.0',commit='e'*40,asset=str(source/'SHA256SUMS'))
            pin=dict(path=str(source),manifest_sha256=sha,release=release)
            image=os.environ['EXOCORTEX_REHEARSAL_TEST_IMAGE']
            verify_source=updater.verify_source
            # Only provider provenance is substituted for this unpublished test
            # source. Byte verification, all container commands, guard checks,
            # one-time consumption, post-check and artifact freezing remain real.
            def local_source(candidate,apply=False):
                return verify_source(dict(candidate,release=None),apply=False)
            with patch.object(updater,'verify_source',side_effect=local_source), \
                 patch.object(updater.local,'default_cache',return_value=root/'cache.json'), \
                 patch.object(host,'observe_repository',return_value=None):
                updater.create(root,'fixture',source,sha,backup,[target],'fictional',release)
                plan=updater.load(root,'fixture')
                preview=DockerPreview(image,pin,target,backup)
                result=updater.execute(root,'fixture',runner.digest(plan),'preview',preview_invoker=preview)
                self.assertEqual(result['targets'][0]['state'],'ready',result['targets'][0].get('reason'))
                plan=updater.load(root,'fixture');paths=plan['targets'][0]['receipt']['changed_paths']
                actor=dict(surface_id='fixture-surface',executor_id='fixture-writer',adapter_version='fixture-v1')
                approval=dict(approved_by='fixture-owner',accepted_at='2026-01-01T00:00:00Z',expires_at='2099-01-01T00:00:00Z',summary='Fictional container rehearsal.')
                envelope=dict(schema_version='public-v2',kind='local_delivery_envelope',envelope_id='fixture-update',
                    work_item_id='fixture-update',title='Fictional isolated update',type='maintenance',project_root=str(target),
                    branch='fixture-update',base_sha=head,allowed_paths=paths,outcome='Update fictional disposable project',risk='low',
                    rollback='Retain archive; review recovery',verification=['Memory preserved; zero changes remain'],
                    exclusions=['No real projects or accounts'],writer=actor,
                    reviewer=dict(surface_id='fixture-review',executor_id='fixture-reviewer',adapter_version='fixture-v1'),
                    approval=approval,lease_expires_at='2099-01-01T00:00:00Z')
                inbox='.exocortex/local/protocol/inbox/fixture-update.json';write(target/inbox,envelope)
                run([sys.executable,source/'.exocortex/scripts/orchestrate_work_item.py','bootstrap-local-delivery',
                     '--project-root',target,'--envelope-source',inbox,'--request-id','fixture-bootstrap'],target)
                registry=json.loads((target/'.exocortex/control/EXECUTOR_REGISTRY.json').read_text())
                capability='.exocortex/local/protocol/capabilities/fixture-apply.json'
                cap=dict(schema_version='public-v2',kind='approval_capability',capability_id='fixture-apply',
                    work_item_id='fixture-update',work_item_revision=0,operation='apply_template_update',
                    scope=dict(allowed_paths=paths,target_sha=sha),
                    executor=dict(actor,guard_digest=guard.current_guard_digest(),registry_version=registry['registry_version']),
                    approval=dict(approval,one_time=True),
                    status=dict(state='active',revoked_at=None,consumed_at=None,consumed_by_request_id=None))
                write(target/capability,cap)
                auth={'target-1':dict(actor,capability=capability,work_item_id='fixture-update',work_item_revision=0,request_id='fixture-apply')}
                now=int(time.time())
                job=dict(version=runner.VERSION,account='fictional',installation='123',grant_epoch='1',repository_id='456',
                    repository='example/disposable',base_branch='main',base_sha=head,
                    release={k:release[k] for k in ('repository','tag','commit')},
                    policy=dict(revision=1,sha256='2'*64,declaration='explicit',treatment='standard'),
                    plan_sha256=runner.digest(plan),artifact_sha256='0'*64,created_at=now,expires_at=now+1800)
                job['release'].update(manifest_sha256=sha,modes_sha256=hashlib.sha256((source/'FILEMODES').read_bytes()).hexdigest())
                config=dict(image=image,source=pin,checkout=str(target),backup_root=str(backup),controller=str(root),output=str(root/'prepared.json'))
                control=b'fictional-review-key'*2;key=b'fictional-preparation-key'*2
                review=runner.sign('rehearsal-review',dict(job=job,host_sha256=runner.digest(config),plan_id='fixture',
                    plan_sha256=runner.digest(plan),target_id='target-1',authorities_sha256=runner.digest(auth)),control)
                def execute():return host.execute_reviewed(config,job,review,auth,lambda *a:True,control,key)
                if lost_apply_reply:
                    real=DockerRehearsal.__call__
                    def lose_reply(self,src,row,back,authority=None):
                        result=real(self,src,row,back,authority)
                        if authority is not None and result[0]==0:raise IsolationError('fictional_lost_apply_reply')
                        return result
                    with patch.object(DockerRehearsal,'__call__',lose_reply):
                        with self.assertRaisesRegex(runner.Blocked,'rehearsal_not_verified'):execute()
                    failed=updater.load(root,'fixture')['targets'][0]
                    self.assertEqual(failed['state'],'recovery_required',failed.get('reason'))
                    self.assertTrue(Path(failed['receipt']['archive']).is_file())
                    with patch.object(DockerRehearsal,'__call__',side_effect=AssertionError('must not reapply')):
                        with self.assertRaisesRegex(runner.Blocked,'review_recovery'):execute()
                    self.assertFalse(Path(config['output']).exists())
                else:
                    packet=execute();self.assertEqual(packet,execute())
                    payload=runner.verify(packet,'prepared-update',key)
                    runner.validate_artifact(payload['artifact'],payload['job'])
                    self.assertEqual(sorted(x['path'] for x in payload['artifact']['changes']),paths)
                    self.assertEqual(updater.load(root,'fixture')['targets'][0]['state'],'applied')
                self.assertEqual(run(['git','rev-parse','HEAD'],target),head)
                self.assertEqual(script.read_bytes(),(source/'.exocortex/scripts/read_memory_stack.sh').read_bytes())
                for path,data in preserved.items():self.assertEqual(Path(path).read_bytes(),data)
                self.assertEqual(json.loads((target/capability).read_text())['status']['state'],'consumed')

    def test_real_isolated_apply_freeze_and_exact_retry(self):self.exercise()
    def test_lost_apply_reply_retains_recovery_and_never_retries(self):self.exercise(lost_apply_reply=True)


if __name__=='__main__':unittest.main()
