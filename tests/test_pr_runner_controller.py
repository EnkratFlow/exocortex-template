"""Offline controller sequencing with mocked coordinator/provider boundaries."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
import pr_runner_controller as c
import pr_runner as r
from test_pr_runner import sample, NOW

class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name).resolve();self.job=sample()['job']
        self.source={'path':str(root/'source'),'manifest_sha256':self.job['release']['manifest_sha256'],
                     'release':{'repository':'example/template','tag':'v4.0.0','commit':'e'*40,'asset':str(root/'SHA256SUMS')}}
        self.current={'version':'1.0.0','binding':{'head':self.job['base_sha']},'customization':{'requires_review':False}}
        self.plan={'id':'test','account_scope':'owner-1','source':self.source,'backup_root':str(root/'backup'),
                   'targets':[{'id':'target-1','path':str(root/'checkout'),'initial':self.current,'state':'not_attempted','receipt':None}]}
        self.authority=Mock(return_value=True)
        self.observe=Mock(return_value={k:self.job[k] for k in ('repository_id','repository','base_branch','base_sha')})
        self.now=NOW;self.controller=c.PreparationController(root/'controller',self.source,root/'checkout',root/'backup',self.authority,self.observe,clock=lambda:self.now)
        self.job['release']['modes_sha256']=c.hashlib.sha256(b'modes').hexdigest()
        self.path=root/'plan';self.created=0;self.actions=[]
        def create(*a):self.created+=1;self.path.touch()
        def execute(*args):
            self.actions.append(args[3]);row=self.plan['targets'][0]
            row.update(state='ready' if args[3]=='preview' else 'applied',receipt={'changed_paths':['.exocortex/scripts/example.py']})
        mocks={'verify_source':lambda *a,**k:root/'source','file_bytes':lambda *a:b'modes',
               'candidate_hashes':lambda *a:{},'target':lambda *a:copy.deepcopy(self.current),'plan_path':lambda *a:self.path,
               'load':lambda *a:copy.deepcopy(self.plan),'create':create,'execute':execute}
        for name,fn in mocks.items():
            p=patch.object(c.updater,name,side_effect=fn);p.start();self.addCleanup(p.stop)
        p=patch.object(c.updater.state,'git',return_value='https://github.com/example/project.git');p.start();self.addCleanup(p.stop)
        p=patch.object(c,'prepare',side_effect=lambda root,pid,tid,job,key,now:r.sign('prepared-update',{'job':job,'artifact':{}},key));self.freeze=p.start();self.addCleanup(p.stop)
    def test_preview_retries_reuse_plan_without_second_execution(self):
        first=self.controller.preview('test',self.job);second=self.controller.preview('test',self.job)
        self.assertEqual(first,second);self.assertEqual(self.created,1);self.assertEqual(self.actions,['preview']);self.freeze.assert_not_called()
    def test_rehearsal_passes_exact_authority_then_freezes_verified_plan(self):
        preview=self.controller.preview('test',self.job)
        result=self.controller.rehearse('test',preview['plan_sha256'],self.job,{'target-1':{'fixture':'authority'}},b'k'*32)
        self.assertEqual(result['kind'],'prepared-update');self.assertEqual(self.actions,['preview','apply'])
        self.assertEqual(self.freeze.call_args.args[3]['plan_sha256'],r.digest(self.plan))
    def test_missing_extra_authority_or_changed_plan_never_apply(self):
        preview=self.controller.preview('test',self.job)
        for authority in ({},{'target-2':{}},{'target-1':{},'target-2':{}}):
            with self.assertRaises(r.Blocked):self.controller.rehearse('test',preview['plan_sha256'],self.job,authority,b'k'*32)
        with self.assertRaises(c.updater.UpdateError):self.controller.rehearse('test','0'*64,self.job,{'target-1':{}},b'k'*32)
        self.assertEqual(self.actions,['preview']);self.freeze.assert_not_called()
    def test_provider_drift_or_policy_revocation_stops_before_plan_creation(self):
        self.observe.return_value['base_sha']='9'*40
        with self.assertRaisesRegex(r.Blocked,'repository_changed'):self.controller.preview('test',self.job)
        self.assertEqual(self.created,0)
        self.authority.side_effect=r.Blocked('grant_revoked')
        with self.assertRaisesRegex(r.Blocked,'grant_revoked'):self.controller.preview('test',self.job)
        self.assertEqual(self.actions,[])
    def test_customizations_or_wrong_checkout_block(self):
        self.current['customization']['requires_review']=True
        with self.assertRaisesRegex(r.Blocked,'customization_review'):self.controller.preview('test',self.job)
        self.current['customization']['requires_review']=False;self.current['binding']['head']='9'*40
        with self.assertRaisesRegex(r.Blocked,'checkout_binding'):self.controller.preview('test',self.job)
        self.assertEqual(self.actions,[])
    def test_plan_from_another_account_or_source_cannot_be_reused(self):
        self.path.touch();self.plan['account_scope']='other'
        with self.assertRaisesRegex(r.Blocked,'plan_binding'):self.controller.preview('test',self.job)
        self.assertEqual(self.actions,[])
    def test_unpublished_release_and_failed_attestation_never_execute(self):
        with patch.object(c.updater,'verify_source',side_effect=c.updater.UpdateError('unpublished')):
            with self.assertRaises(c.updater.UpdateError):self.controller.preview('test',self.job)
        self.assertEqual(self.created,0)
    def test_failed_apply_preserves_coordinator_state_without_signing(self):
        preview=self.controller.preview('test',self.job)
        def failed(*a):self.plan['targets'][0]['state']='recovery_required'
        with patch.object(c.updater,'execute',side_effect=failed):
            with self.assertRaisesRegex(r.Blocked,'rehearsal_not_verified'):
                self.controller.rehearse('test',preview['plan_sha256'],self.job,{'target-1':{}},b'k'*32)
        self.assertEqual(self.plan['targets'][0]['state'],'recovery_required');self.freeze.assert_not_called()
    def test_expiry_during_preview_is_not_returned_as_ready(self):
        def expire(*a):self.now=NOW+1000
        with patch.object(c.updater,'execute',side_effect=expire):
            with self.assertRaises(r.Blocked):self.controller.preview('test',self.job)
        self.freeze.assert_not_called()
    def test_expiry_during_freeze_never_returns_packet(self):
        preview=self.controller.preview('test',self.job)
        def expire(root,pid,tid,job,key,now):
            self.now=NOW+1000
            return r.sign('prepared-update',{'job':job,'artifact':{}},key)
        self.freeze.side_effect=expire
        with self.assertRaises(r.Blocked):
            self.controller.rehearse('test',preview['plan_sha256'],self.job,{'target-1':{}},b'k'*32)
        self.assertEqual(self.plan['targets'][0]['state'],'applied')
    def test_expiry_during_final_provider_revalidation_never_returns_packet(self):
        preview=self.controller.preview('test',self.job)
        count=0
        def observed(job):
            nonlocal count
            count+=1
            if count==3:self.now=NOW+1000
            return {k:job[k] for k in ('repository_id','repository','base_branch','base_sha')}
        self.observe.side_effect=observed
        with self.assertRaises(r.Blocked):
            self.controller.rehearse('test',preview['plan_sha256'],self.job,{'target-1':{}},b'k'*32)
        self.assertEqual(self.plan['targets'][0]['state'],'applied')
    def test_freeze_retry_never_repeats_apply(self):
        preview=self.controller.preview('test',self.job)
        self.controller.rehearse('test',preview['plan_sha256'],self.job,{'target-1':{}},b'k'*32)
        result=self.controller.freeze('test',r.digest(self.plan),self.job,b'k'*32)
        self.assertEqual(result['kind'],'prepared-update');self.assertEqual(self.actions,['preview','apply'])
    def test_path_alias_or_overlap_rejected(self):
        root=Path(self.tmp.name).resolve()
        with self.assertRaisesRegex(r.Blocked,'unsafe_preparation_path'):
            c.PreparationController(root,self.source,root/'checkout',root/'backup',self.authority,self.observe)

    def test_false_authority_callback_fails_closed(self):
        self.authority.return_value=False
        with self.assertRaisesRegex(r.Blocked,'live_authority_rejected'):self.controller.preview('test',self.job)
        self.assertEqual(self.actions,[])

    def test_rehearsal_checks_expiry_between_dryrun_and_apply(self):
        preview=self.controller.preview('test',self.job)
        invoke=Mock(return_value=(0,''));self.controller.rehearsal_invoker=invoke
        def execute(*args,**kw):
            kw['rehearsal_invoker'](self.source,self.plan['targets'][0],Path(self.plan['backup_root']))
            self.now=NOW+1000
            kw['rehearsal_invoker'](self.source,self.plan['targets'][0],Path(self.plan['backup_root']),{})
        with patch.object(c.updater,'execute',side_effect=execute):
            with self.assertRaisesRegex(r.Blocked,'expired_request'):
                self.controller.rehearse('test',preview['plan_sha256'],self.job,{'target-1':{}},b'k'*32)
        invoke.assert_called_once();self.freeze.assert_not_called()

    def test_freeze_uses_rehearsal_readonly_when_no_preview_adapter(self):
        self.plan['targets'][0]['state']='applied'
        invoke=Mock(return_value=(0,''));self.controller.rehearsal_invoker=invoke
        def prepare(root,pid,tid,job,key,now,**kw):
            kw['preview_invoker'](self.source,self.plan['targets'][0],Path(self.plan['backup_root']))
            return r.sign('prepared-update',{'job':job,'artifact':{}},key)
        self.freeze.side_effect=prepare
        self.controller.freeze('test',r.digest(self.plan),self.job,b'k'*32)
        self.assertEqual(len(invoke.call_args.args),3)

if __name__=='__main__':unittest.main()
