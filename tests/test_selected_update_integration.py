"""One disposable real guarded apply; only public-release lookup is substituted."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.exocortex/scripts'))
sys.path.insert(0,str(ROOT/'tests'))
import update_selected as update
import authority_guard as guard
import test_installer_security as fixture


def run(args,root):
    p=subprocess.run([str(x) for x in args],cwd=root,capture_output=True,text=True,timeout=120)
    if p.returncode:raise AssertionError(p.stdout+p.stderr)
    return p.stdout.strip()


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value)+'\n')


class IntegrationTests(unittest.TestCase):
    def test_guarded_update_preserves_memory_and_verifies_installation(self):
        with tempfile.TemporaryDirectory(prefix='selected integration ',ignore_cleanup_errors=True) as tmp:
            base=Path(tmp).resolve();source=base/'source';source.mkdir()
            for row in (ROOT/'SHA256SUMS').read_text().splitlines()+['  SHA256SUMS']:
                name=row.split('  ',1)[1];dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(ROOT/name,dest)
            target=fixture.new_target(base,'target')
            result=fixture.install(source,target)
            self.assertEqual(result.returncode,0,result.stderr)
            run(['git','config','user.name','Fixture'],target)
            run(['git','config','user.email','fixture@example.invalid'],target)
            run(['git','config','core.autocrlf','false'],target)
            run(['git','symbolic-ref','HEAD','refs/heads/fixture-update'],target)
            memory=target/'.exocortex/PROJECT_MEMORY.md';memory.write_bytes(b'# Fictional handwritten memory\nRetain this.\n')
            script=target/'.exocortex/scripts/read_memory_stack.sh';script.write_bytes(b'#!/bin/bash\necho old-fixture\n')
            manifest=target/'.exocortex/.install-manifest'
            rows=[('.exocortex/scripts/read_memory_stack.sh '+hashlib.sha256(script.read_bytes()).hexdigest()) if x.startswith('.exocortex/scripts/read_memory_stack.sh ') else x for x in manifest.read_text().splitlines()]
            manifest.write_bytes(('\n'.join(rows)+'\n').encode())
            run(['git','add','.'],target);run(['git','commit','-qm','Fictional installed baseline'],target)
            controller=base/'controller';controller.mkdir();locks=base/'locks'
            update.target(target)
            sha=hashlib.sha256((source/'SHA256SUMS').read_bytes()).hexdigest()
            plan=update.create(controller,'fixture',source,sha,base/'backups',[target],'fictional')
            self.assertEqual(plan['targets'][0]['state'],'not_attempted',plan)
            plan=update.execute(controller,'fixture',plan['plan_sha256'],'preview',lock_root=locks)
            self.assertEqual(plan['targets'][0]['state'],'ready',plan)
            paths=plan['targets'][0]['receipt']['changed_paths']
            actor={'surface_id':'fixture-surface','executor_id':'fixture-writer','adapter_version':'fixture-v1'}
            approval={'approved_by':'fixture-owner','accepted_at':'2026-01-01T00:00:00Z','expires_at':'2099-01-01T00:00:00Z','summary':'Fictional update test.'}
            envelope={'schema_version':'public-v2','kind':'local_delivery_envelope','envelope_id':'fixture-update',
                      'work_item_id':'fixture-update','title':'Fictional selected update','type':'maintenance',
                      'project_root':str(target),'branch':'fixture-update','base_sha':run(['git','rev-parse','HEAD'],target),
                      'allowed_paths':paths,'outcome':'Update fictional project','risk':'low','rollback':'Retain and review archive',
                      'verification':['Memory preserved; zero changes remain'],'exclusions':['No real projects or accounts'],
                      'writer':actor,'reviewer':{'surface_id':'fixture-review','executor_id':'fixture-reviewer','adapter_version':'fixture-v1'},
                      'approval':approval,'lease_expires_at':'2099-01-01T00:00:00Z'}
            inbox='.exocortex/local/protocol/inbox/fixture-update.json';write(target/inbox,envelope)
            run([sys.executable,source/'.exocortex/scripts/orchestrate_work_item.py','bootstrap-local-delivery',
                 '--project-root',target,'--envelope-source',inbox,'--request-id','fixture-bootstrap'],target)
            registry=json.loads((target/'.exocortex/control/EXECUTOR_REGISTRY.json').read_text())
            capability='.exocortex/local/protocol/capabilities/fixture-apply.json'
            cap={'schema_version':'public-v2','kind':'approval_capability','capability_id':'fixture-apply',
                 'work_item_id':'fixture-update','work_item_revision':0,'operation':'apply_template_update',
                 'scope':{'allowed_paths':paths,'target_sha':sha},
                 'executor':dict(actor,guard_digest=guard.current_guard_digest(),registry_version=registry['registry_version']),
                 'approval':dict(approval,one_time=True),
                 'status':{'state':'active','revoked_at':None,'consumed_at':None,'consumed_by_request_id':None}}
            write(target/capability,cap)
            authority=dict(actor,capability=capability,work_item_id='fixture-update',work_item_revision=0,request_id='fixture-apply')
            # This candidate is deliberately unpublished. Source bytes, real
            # launcher, guard, capability consumption and post-check still run.
            with patch.object(update,'verify_source',return_value=source):
                plan=update.execute(controller,'fixture',plan['plan_sha256'],'apply',{'target-1':authority},locks)
            self.assertEqual(plan['targets'][0]['state'],'applied',plan)
            self.assertEqual(memory.read_bytes(),b'# Fictional handwritten memory\nRetain this.\n')
            self.assertEqual(script.read_bytes(),(source/'.exocortex/scripts/read_memory_stack.sh').read_bytes())
            self.assertEqual(plan['targets'][0]['receipt']['verification']['changed_paths'],[])
            self.assertEqual(json.loads((target/capability).read_text())['status']['state'],'consumed')


if __name__=='__main__':unittest.main()
