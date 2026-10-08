"""Selected-update state machine; fictional local projects, no real accounts."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.exocortex/scripts'))
import update_selected as update


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),'-c','core.hooksPath='+str(root/'.no-hooks'),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',*args],stderr=subprocess.DEVNULL,text=True).strip()


# Integrity fixtures bind explicit UTF-8/LF bytes on every platform.
def write(path,text):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(text.encode('utf-8'))


class SelectedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='selected fixture ');self.base=Path(self.tmp.name).resolve()
        self.control=self.base/'controller';self.control.mkdir();self.source=self.base/'source';self.source.mkdir()
        for n in ('scripts/safe-update.sh','scripts/windows.ps1'):write(self.source/n,'fixture entrypoint\n')
        write(self.source/'SHA256SUMS',''.join(hashlib.sha256((self.source/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ('scripts/safe-update.sh','scripts/windows.ps1')))
        self.digest=hashlib.sha256((self.source/'SHA256SUMS').read_bytes()).hexdigest()
        self.backup=self.base/'backups';self.locks=self.base/'locks';self.first=self.make_target('first');self.calls=[]

    def tearDown(self):self.tmp.cleanup()

    def make_target(self,name):
        p=self.base/name;p.mkdir();git(p,'init','-q','-b','main')
        write(p/'.gitignore','.exocortex/local/\n')
        write(p/'.exocortex/.version','1.0.0\n');write(p/'.exocortex/scripts/example.py','original\n')
        digest=hashlib.sha256((p/'.exocortex/scripts/example.py').read_bytes()).hexdigest()
        write(p/'.exocortex/.install-manifest','.exocortex/scripts/example.py '+digest+'\n')
        git(p,'add','.gitignore','.exocortex/.version','.exocortex/scripts/example.py','.exocortex/.install-manifest');git(p,'commit','-qm','Fixture baseline')
        return p

    def create(self,targets=None,pid='example'):
        return update.create(self.control,pid,self.source,self.digest,self.backup,targets or [self.first],'fictional-personal')

    def fake_run(self,source,row,backup,authority=None):
        self.calls.append((row['id'],bool(authority)))
        archive=backup/('apply.tar.gz' if authority else 'preview.tar.gz');write(archive,'fictional compressed archive')
        paths=['.exocortex/scripts/example.py']
        if getattr(self,'applied',False):paths=[]
        if authority:self.applied=True
        raw=''.join(p+'\n' for p in paths);count=len(paths)
        tail='Update applied under consumed capability: fixture\nRollback archive: '+str(archive)+'\n' if authority else 'Dry run complete. Real target unchanged.\n'
        return 0, f'Backup: {archive}\nProtected data check: PASS\nRehearsal changed paths SHA-256: {hashlib.sha256(raw.encode()).hexdigest()}\nRehearsal changed paths: {count}\n'+raw+tail

    def execute(self,p,action='preview',auth=None):
        return update.execute(self.control,p['id'],p['plan_sha256'],action,auth,self.locks)

    def auth(self):return {'capability':'.exocortex/local/protocol/capabilities/fixture.json','work_item_id':'fixture','work_item_revision':0,'request_id':'fixture','surface_id':'fixture','executor_id':'fixture','adapter_version':'fixture-v1'}

    def test_selection_is_explicit_and_show_is_read_only(self):
        other=self.make_target('unselected');p=self.create()
        self.assertEqual([r['path'] for r in p['targets']],[str(self.first)])
        before=update.plan_path(self.control,'example').read_bytes()
        self.assertEqual(update.view(update.load(self.control,'example')),p)
        self.assertEqual(before,update.plan_path(self.control,'example').read_bytes())
        self.assertTrue(other.is_dir());self.assertEqual(self.calls,[])

    def test_local_preview_does_not_authorize_apply(self):
        p=self.create()
        with patch.object(update,'invoke',side_effect=self.fake_run):
            p=self.execute(p);self.assertEqual(p['targets'][0]['state'],'ready')
            p=self.execute(p,'apply',{'target-1':self.auth()})
        self.assertEqual(p['targets'][0]['state'],'blocked')
        self.assertEqual(self.calls,[('target-1',False)])

    def test_source_change_blocks_before_execution(self):
        p=self.create();write(self.source/'scripts/safe-update.sh','changed')
        with patch.object(update,'invoke',side_effect=AssertionError('must not execute')):p=self.execute(p)
        self.assertEqual(p['targets'][0]['state'],'blocked')

    def test_target_branch_or_managed_content_change_blocks(self):
        p=self.create();write(self.first/'.exocortex/scripts/example.py','changed')
        with patch.object(update,'invoke',side_effect=AssertionError('must not execute')):p=self.execute(p)
        self.assertEqual(p['targets'][0]['state'],'blocked')

    def test_non_git_and_missing_manifest_are_explicitly_blocked(self):
        folder=self.base/'not-git';folder.mkdir();p=self.create([folder])
        self.assertEqual(p['targets'][0]['state'],'blocked')
        self.assertIn('not a Git root',p['targets'][0]['reason'])

    def test_two_worktrees_in_one_plan_require_explicit_choice(self):
        other=self.base/'linked';git(self.first,'worktree','add','-b','other',str(other))
        p=self.create([self.first,other]);self.assertTrue(all(r['state']=='blocked' for r in p['targets']))

    def test_blocked_target_does_not_prevent_independent_preview(self):
        absent=self.base/'missing';p=self.create([absent,self.first])
        with patch.object(update,'invoke',side_effect=self.fake_run):p=self.execute(p)
        self.assertEqual([r['state'] for r in p['targets']],['blocked','ready'])
        self.assertEqual(self.calls,[('target-2',False)])

    def test_stale_plan_and_unselected_authority_rejected(self):
        p=self.create()
        with self.assertRaises(update.UpdateError):update.execute(self.control,'example','0'*64,'preview',lock_root=self.locks)
        with self.assertRaises(update.UpdateError):self.execute(p,'apply',{'unselected':self.auth()})
        self.assertEqual(self.calls,[])

    def test_apply_passes_existing_authority_and_verifies_zero_changes(self):
        p=self.create()
        with patch.object(update,'invoke',side_effect=self.fake_run),patch.object(update,'verify_source',return_value=self.source):
            p=self.execute(p);p=self.execute(p,'apply',{'target-1':self.auth()})
        self.assertEqual(p['targets'][0]['state'],'applied')
        self.assertEqual(self.calls,[('target-1',False),('target-1',False),('target-1',True),('target-1',False)])
        self.assertEqual(p['targets'][0]['receipt']['verification']['changed_paths'],[])

    def test_failure_retains_recovery_and_blocks_other_plan_until_restore(self):
        def failed(s,r,b,a=None):return (1,'apply failed') if a else self.fake_run(s,r,b,a)
        p=self.create()
        with patch.object(update,'invoke',side_effect=failed),patch.object(update,'verify_source',return_value=self.source):
            p=self.execute(p);p=self.execute(p,'apply',{'target-1':self.auth()})
            self.assertEqual(p['targets'][0]['state'],'recovery_required')
            q=self.create(pid='second');q=self.execute(q);self.assertEqual(q['targets'][0]['state'],'blocked')
        packet=update.recovery(self.control,'example','target-1');self.assertTrue(packet['target']['receipt']['archive'])
        # Failed fixture changed no code; exact prior snapshot is the evidence.
        p=update.confirm_restored(self.control,'example','target-1',p['plan_sha256'],'Fixture inspected; exact prior code intact',self.locks)
        self.assertEqual(p['targets'][0]['state'],'restored')

    def test_changed_effect_cannot_apply(self):
        p=self.create()
        with patch.object(update,'invoke',side_effect=self.fake_run),patch.object(update,'verify_source',return_value=self.source):
            p=self.execute(p);self.applied=True;p=self.execute(p,'apply',{'target-1':self.auth()})
        self.assertEqual(p['targets'][0]['state'],'blocked');self.assertFalse(any(applied for _,applied in self.calls))

    def test_receipt_rejects_forged_effect_or_outside_backup(self):
        _,out=self.fake_run({}, {'id':'target-1'},self.backup)
        with self.assertRaises(update.UpdateError):update.receipt(out.replace('Rehearsal changed paths: 1','Rehearsal changed paths: 2'),self.backup)
        with self.assertRaises(update.UpdateError):update.receipt(out,self.base/'other-backups')

    def test_source_identity_fields_cannot_be_partial_or_redirected(self):
        for r in ({}, {'repository':'../repo','tag':'v1.0.0','commit':'a'*40,'asset':str(self.base/'SHA256SUMS')}):
            with self.assertRaises(update.UpdateError):update.validate_release(r)

    def test_cross_machine_plan_cannot_run(self):
        p=self.create()
        with patch.object(update,'machine',return_value='other'):
            with self.assertRaises(update.UpdateError):update.load(self.control,p['id'])

    def test_unclassified_file_is_blocked_without_reading(self):
        for rel in ('.claude/settings.local.json','.exocortex/token.json','.exocortex/scripts/new.py','.exocortex/key-registry.json','.exocortex/.env.example','.exocortex/.ENV','.exocortex/cache.pyc'):
            p=self.first/rel;write(p,'fictional content must not be opened')
            original=update.file_bytes
            def inspected(path,*args):
                self.assertNotEqual(path,p)
                return original(path,*args)
            with patch.object(update,'file_bytes',side_effect=inspected),self.assertRaises(update.UpdateError):update.target(self.first)
            p.unlink()

    def test_credential_shaped_target_blocks_updater(self):
        write(self.first/'.exocortex/key-registry.json','fictional content must not be opened')
        with patch.object(update,'invoke',side_effect=AssertionError('must not invoke')):
            plan=self.create();plan=self.execute(plan)
        self.assertEqual(plan['targets'][0]['state'],'blocked')

    def test_declared_public_examples_allow_preview_but_modified_example_blocks(self):
        content = b'Fictional public example without private values\n'
        checksum = hashlib.sha256(content).hexdigest()
        public_manifest = ''.join(checksum+'  '+rel+'\n' for rel in sorted(update.PUBLIC_TEMPLATE_FILES)).encode()
        installed = self.first/'.exocortex/.install-manifest'
        for rel in update.PUBLIC_TEMPLATE_FILES:
            write(self.first/rel, content.decode())
        write(installed,installed.read_text()+''.join(rel+' '+checksum+'\n' for rel in sorted(update.PUBLIC_TEMPLATE_FILES)))
        original = update.file_bytes
        def read_manifest(path, *args):
            if path == ROOT/'SHA256SUMS': return public_manifest
            return original(path, *args)
        with patch.object(update, 'file_bytes', side_effect=read_manifest), patch.object(update, 'invoke', side_effect=self.fake_run):
            plan = self.execute(self.create())
            self.assertEqual(plan['targets'][0]['state'], 'ready', plan['targets'][0])
            self.assertEqual(self.calls, [('target-1', False)])
            write(self.first/'.exocortex/key-registry.json', 'Changed fictional example\n')
            with self.assertRaisesRegex(update.UpdateError, 'Modified public-template example'):
                update.target(self.first)
            blocked = self.create(pid='modified-example')
            self.assertEqual(blocked['targets'][0]['state'], 'blocked')
            self.assertNotIn('Changed fictional example', json.dumps(blocked))
            self.assertEqual(self.calls, [('target-1', False)])

    def test_opaque_runtime_directory_blocks_without_opening(self):
        write(self.first/'.exocortex/__pycache__/fixture.pyc','opaque fictional bytes')
        with patch.object(update,'invoke',side_effect=AssertionError('must not invoke')):
            plan=self.create();plan=self.execute(plan)
        self.assertEqual(plan['targets'][0]['state'],'blocked')

    def test_authority_input_rejects_arbitrary_json_without_opening(self):
        with patch.object(update.local,'load',side_effect=AssertionError('must not open')):
            for name in ('secrets.json','tokens.json','other.json'):
                with self.assertRaises(update.UpdateError):update.authority_input(self.control,self.base/name)

    def test_windows_falls_back_to_standard_powershell(self):
        with patch.object(update.shutil,'which',side_effect=lambda name:'powershell.exe' if name=='powershell.exe' else None):
            command=update.launch_command(self.base,['--dry-run'],windows=True)
        self.assertEqual(command[0],'powershell.exe');self.assertIn('-NoProfile',command)
        self.assertNotIn('-ExecutionPolicy',command);self.assertNotIn('Bypass',command)

    def test_changed_launcher_after_verification_never_executes(self):
        p=self.create();update.verify_source(p['source'])
        write(self.source/'scripts/safe-update.sh','changed after verification')
        with patch.object(update.subprocess,'Popen',side_effect=AssertionError('must not execute')),self.assertRaises(update.UpdateError):
            update.invoke(p['source'],p['targets'][0],self.backup)

    def test_launcher_environment_preserves_discovery_without_credentials(self):
        p=self.create()
        allowed={'PATH':'/fixture/bin','SystemRoot':'C:/Windows',
                 'WINDIR':'C:/Windows','COMSPEC':'C:/Windows/cmd.exe','PATHEXT':'.EXE',
                 'EXOCORTEX_PYTHON':'C:/Runtime/python.exe',
                 'EXOCORTEX_BASH':'C:/PortableGit/bin/bash.exe',
                 'ProgramFiles':'C:/Program Files','ProgramFiles(x86)':'C:/Program Files (x86)',
                 'ProgramW6432':'C:/Program Files','LOCALAPPDATA':'C:/Profiles/fixture/AppData/Local',
                 'USERPROFILE':'C:/Profiles/fixture'}
        excluded={'OPENAI_API_KEY':'fictional','GITHUB_TOKEN':'fictional',
                  'GIT_CONFIG_GLOBAL':'/fixture/gitconfig','BASH_ENV':'/fixture/startup',
                  'PYTHONPATH':'/fixture/imports','EXOCORTEX_LOCAL_SOURCE':'/fixture/other',
                  'HOME':'/fixture/home','TMP':'/fixture/tmp'}
        captured={}
        def launch(command,**kwargs):
            captured.update(kwargs['env'])
            process=unittest.mock.Mock(returncode=0)
            return process
        # Exercise the environment handoff with a mocked process; discovery is
        # independently tested and must not depend on the fictional PATH.
        with patch.dict(update.os.environ,{**allowed,**excluded},clear=True), patch.object(update,'launch_command',return_value=['fictional-launcher']), patch.object(update.subprocess,'Popen',side_effect=launch):
            code,output=update.invoke(p['source'],p['targets'][0],self.backup)
        self.assertEqual(code,0)
        for key,value in allowed.items():self.assertEqual(captured[key],value)
        for key in set(excluded)-{'HOME','TMP'}:self.assertNotIn(key,captured)
        self.assertNotEqual(captured['HOME'],excluded['HOME'])
        self.assertNotEqual(captured['TMP'],excluded['TMP'])
        self.assertEqual(captured['PYTHONDONTWRITEBYTECODE'],'1')

    def set_policy(self,root,mode='standard',paths=None):
        write(root/update.policy.POLICY,json.dumps({'mode':mode,'protected_paths':paths or []}))

    def candidate_file(self,text):
        rel='.exocortex/scripts/example.py';write(self.source/rel,text)
        manifest=self.source/'SHA256SUMS'
        rows=[r for r in manifest.read_text().splitlines() if not r.endswith('  '+rel)]
        rows.append(hashlib.sha256(text.encode()).hexdigest()+'  '+rel)
        write(manifest,'\n'.join(rows)+'\n')
        self.digest=hashlib.sha256(manifest.read_bytes()).hexdigest()

    def test_three_way_customization_classification(self):
        cases=[('original\n','original\n',None,False),
               ('custom\n','original\n','local-only',True),
               ('original\n','upstream\n','upstream-only',False),
               ('upstream\n','upstream\n','converged',False),
               ('custom\n','upstream\n','conflict',True),
               (None,'upstream\n','deleted',True)]
        for number,(current,incoming,kind,blocked) in enumerate(cases):
            with self.subTest(kind=kind):
                path=self.first/'.exocortex/scripts/example.py'
                if current is None:path.unlink()
                else:write(path,current)
                self.candidate_file(incoming)
                p=self.create(pid='case-'+str(number));row=p['targets'][0]
                report=row['initial']['customization']
                self.assertEqual(report['requires_review'],blocked)
                files=[x for x in report['files'] if x['path']=='.exocortex/scripts/example.py']
                self.assertEqual(files[0]['classification'] if files else None,kind)
                self.assertEqual(row['state']=='blocked',blocked)

    def test_policy_modes_and_declared_external_paths_block_without_reading(self):
        for number,(mode,paths) in enumerate([('excluded',[]),('review_only',[]),('standard',['firebase.json','docs/SDLC.md'])]):
            self.set_policy(self.first,mode,paths)
            external=self.first/'firebase.json';write(external,'private deployment details')
            original=update.file_bytes
            def checked(path,*args):
                self.assertNotEqual(path,external)
                return original(path,*args)
            with patch.object(update,'file_bytes',side_effect=checked),patch.object(update,'invoke',side_effect=AssertionError('must not invoke')):
                p=self.create(pid='policy-'+str(number));p=self.execute(p)
            self.assertEqual(p['targets'][0]['state'],'blocked')
            self.assertEqual(p['targets'][0]['initial']['customization']['policy']['mode'],mode)

    def test_firebase_presence_alone_is_not_customization(self):
        write(self.first/'firebase.json','fictional unrelated project configuration')
        p=self.create()
        self.assertFalse(p['targets'][0]['initial']['customization']['requires_review'])

    def test_policy_change_after_preview_blocks_apply(self):
        p=self.create()
        with patch.object(update,'invoke',side_effect=self.fake_run):p=self.execute(p)
        self.set_policy(self.first,'excluded')
        with patch.object(update,'invoke',side_effect=AssertionError('must not invoke')):
            p=self.execute(p,'apply',{'target-1':self.auth()})
        self.assertEqual(p['targets'][0]['state'],'blocked')
        self.assertIn('changed since selection',p['targets'][0]['reason'])

    def test_policy_removal_or_edit_after_selection_blocks_preview(self):
        for number,remove in enumerate((True,False)):
            self.set_policy(self.first)
            p=self.create(pid='drift-'+str(number))
            path=self.first/update.policy.POLICY
            if remove:path.unlink()
            else:write(path,json.dumps({'mode':'standard','protected_paths':[],'reason':'changed'}))
            with patch.object(update,'invoke',side_effect=AssertionError('must not invoke')):p=self.execute(p)
            self.assertEqual(p['targets'][0]['state'],'blocked')

    def test_policy_change_during_source_verification_blocks_invocation(self):
        p=self.create()
        def verify(*args,**kwargs):self.set_policy(self.first,'excluded')
        with patch.object(update,'verify_source',side_effect=verify),patch.object(update,'invoke',side_effect=AssertionError('must not invoke')):
            p=self.execute(p)
        self.assertEqual(p['targets'][0]['state'],'blocked')

    def test_mixed_customized_batch_allows_only_normal_target(self):
        other=self.make_target('normal');self.candidate_file('upstream\n')
        write(self.first/'.exocortex/scripts/example.py','custom\n')
        p=self.create([self.first,other])
        with patch.object(update,'invoke',side_effect=self.fake_run):p=self.execute(p)
        self.assertEqual([x['state'] for x in p['targets']],['blocked','ready'])
        self.assertEqual(self.calls,[('target-2',False)])

    def test_deeply_nested_policy_blocks_only_its_target(self):
        other=self.make_target('normal')
        write(self.first/update.policy.POLICY,'['*1100+'0'+']'*1100)
        p=self.create([self.first,other])
        with patch.object(update,'invoke',side_effect=self.fake_run):p=self.execute(p)
        self.assertEqual([row['state'] for row in p['targets']],['blocked','ready'])
        self.assertEqual(self.calls,[('target-2',False)])

    def test_malformed_and_linked_policy_fail_closed(self):
        path=self.first/update.policy.POLICY
        for number,text in enumerate(['{}','{"mode":"standard","protected_paths":["../escape"]}',
            '{"mode":"standard","protected_paths":[".env"]}',
            '{"mode":"standard","protected_paths":[".exocortex/PROJECT_MEMORY.md"]}',
            '{"mode":"standard","mode":"excluded","protected_paths":[]}']):
            write(path,text);p=self.create(pid='invalid-'+str(number))
            self.assertEqual(p['targets'][0]['state'],'blocked')
        path.unlink();other=self.base/'policy.json';write(other,'{}');path.symlink_to(other)
        p=self.create(pid='linked');self.assertEqual(p['targets'][0]['state'],'blocked')
        path.unlink();update.os.link(other,path)
        p=self.create(pid='hardlinked');self.assertEqual(p['targets'][0]['state'],'blocked')

    def test_project_gitignore_and_template_ci_are_not_installed_file_conflicts(self):
        report=update.policy.compare({}, {'.gitignore':{'sha256':'a'*64}},
            {'.gitignore':'b'*64,'.github/workflows/test.yml':'c'*64},
            {'mode':'standard','protected_paths':[]})
        self.assertEqual(report['files'],[])
        self.assertFalse(report['requires_review'])

    def test_unknown_baseline_is_structured_and_requires_review(self):
        report=update.policy.compare({}, {'.exocortex/scripts/example.py':{'sha256':'a'*64}},
            {'.exocortex/scripts/example.py':'b'*64}, {'mode':'standard','protected_paths':[]})
        self.assertEqual(report['files'][0]['classification'],'unknownbaseline')
        self.assertTrue(report['requires_review'])

    def test_zero_change_preview_is_current_not_applied(self):
        p=self.create();self.applied=True
        with patch.object(update,'invoke',side_effect=self.fake_run):p=self.execute(p)
        self.assertEqual(p['targets'][0]['state'],'current')

    def test_malformed_selection_fails_before_execution(self):
        p=self.create();saved=update.load(self.control,'example');saved['targets'][0]['selected']=False
        update.local.write(update.plan_path(self.control,'example'),saved)
        with patch.object(update,'invoke',side_effect=AssertionError('must not execute')),self.assertRaises(update.UpdateError):
            self.execute(p)

    def test_source_release_failure_never_executes(self):
        p=self.create();saved=update.load(self.control,'example')
        saved['source']['release']={'repository':'example/template','tag':'v1.0.0','commit':'a'*40,'asset':str(self.base/'SHA256SUMS')}
        update.local.write(update.plan_path(self.control,'example'),saved)
        with patch.object(update,'checked',side_effect=update.UpdateError('Release verification failed')),patch.object(update,'invoke',side_effect=AssertionError('must not execute')):
            p=self.execute(update.view(saved))
        self.assertEqual(p['targets'][0]['state'],'blocked')


if __name__=='__main__':unittest.main()
