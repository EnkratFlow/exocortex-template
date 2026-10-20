"""Exact hosted review, separate signed authority and report retry boundaries."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
import pr_runner_rehearsal_worker as w
import pr_runner as r
from test_pr_runner import sample,NOW

class ReviewWorkerTests(unittest.TestCase):
    def setUp(self):
        self.now=NOW;self.preview=sample()['job'];self.key=b'fictional-review-key'*2;self.prepkey=b'fictional-preparation-key'*2
        self.pid='b'*64
        self.plan={'id':'prep-'+self.pid[:32],'targets':[{'id':'target-1','state':'ready','initial':{'version':'1.0.0'},'receipt':{'changed_paths':['.exocortex/scripts/fixture.py']}}]}
        self.result=w.preparation_result(w.PreparationController.summary(self.plan),self.preview)
        self.job=dict(self.preview,plan_sha256=r.digest(self.plan))
        self.host={'controller':'/fictional-controller'};self.authority=Mock(return_value=True)
        self.review=r.sign('rehearsal-review',dict(job=self.job,host_sha256=r.digest(self.host),plan_id=self.plan['id'],plan_sha256=r.digest(self.plan),target_id='target-1',authorities_sha256=r.digest({}),hosted_review={'preparation_id':self.pid,'result_sha256':r.digest(self.result)}),self.key)
        self.claim={'id':'c'*64,'lease':'fixture','preparation_id':self.pid,'result_sha256':r.digest(self.result),'configuration':w.configuration(self.preview,7),'expires_at':self.preview['expires_at']}
        self.calls=[];self.allow=True;self.fail=False
        def site(op,body):
            self.calls.append((op,body))
            if op=='poll':return {'job':copy.deepcopy(self.claim)}
            if op=='check':return {'allowed':self.allow}
            if self.fail:raise r.Blocked('site_unavailable')
            return {'saved':True}
        self.site=site
        self.execute=Mock(side_effect=lambda *a,**kw:r.sign('prepared-update',sample(),self.prepkey))
        for target,kwargs in [('execute_reviewed',{'new':self.execute}),('updater.load',{'side_effect':lambda *a:copy.deepcopy(self.plan)})]:
            p=patch('pr_runner_rehearsal_worker.'+target,**kwargs);p.start();self.addCleanup(p.stop)
        self.worker=self.make()
    def make(self):return w.RehearsalWorker(self.host,self.preview,self.review,{},self.authority,self.key,self.prepkey,7,self.site,clock=lambda:self.now)
    def test_exact_review_executes_and_only_reports_digest(self):
        self.assertEqual(self.worker.once(),'verified');self.execute.assert_called_once()
        self.assertEqual(set(self.calls[-1][1]['result']),{'state','artifact_sha256','changed_files','error'})
        gate=self.execute.call_args.kwargs['request_gate'];gate();self.allow=False
        with self.assertRaises(r.Blocked):gate()
    def test_wrong_owner_plan_release_and_extra_host_path_fail(self):
        for key,value in [('preparation_id','d'*64),('result_sha256','d'*64),('configuration',{})]:
            old=self.claim[key];self.claim[key]=value
            with self.assertRaises(r.Blocked):self.worker.once()
            self.claim[key]=old
        self.claim['checkout']='/tmp/foreign'
        with self.assertRaises(r.Blocked):self.worker.once()
        self.execute.assert_not_called()
    def test_signed_review_required_and_original_job_cannot_change(self):
        self.review['signature']='0'*64
        with self.assertRaises(r.Blocked):self.make()
        self.review=r.sign('rehearsal-review',{**self.worker.approved,'job':dict(self.job,account='other')},self.key)
        with self.assertRaises(r.Blocked):self.make()
    def test_changed_plan_or_visible_details_never_execute(self):
        self.plan['targets'][0]['receipt']['changed_paths']=['.exocortex/scripts/other.py']
        with self.assertRaises(r.Blocked):self.worker.once()
        self.execute.assert_not_called()
    def test_cancelled_and_expired_request_never_execute(self):
        self.allow=False
        with self.assertRaises(r.Blocked):self.worker.once()
        self.allow=True;self.now=self.claim['expires_at']
        with self.assertRaises(r.Blocked):self.worker.once()
        self.execute.assert_not_called()
    def test_lost_response_retries_result_never_apply(self):
        self.fail=True
        with self.assertRaises(r.Blocked):self.worker.once()
        self.fail=False;self.allow=False
        self.assertEqual(self.worker.once(),'verified');self.execute.assert_called_once()
    def test_uncertain_execution_reports_recovery_not_safe_failure(self):
        self.execute.side_effect=OSError('private diagnostics')
        self.assertEqual(self.worker.once(),'recovery_required');self.assertNotIn('private diagnostics',str(self.calls))
    def test_restart_cannot_reapply_changed_plan(self):
        self.worker.once();self.plan['targets'][0]['state']='applied'
        with self.assertRaises(r.Blocked):self.make().once()
        self.execute.assert_called_once()
    def test_provider_delay_past_expiry_stops(self):
        original=self.site
        def slow(op,body):
            value=original(op,body)
            if op=='check':self.now=self.claim['expires_at']
            return value
        self.worker.site=slow
        with self.assertRaises(r.Blocked):self.worker.once()
        self.execute.assert_not_called()
    def test_unprovisioned_review_cannot_accept_hosted_request(self):
        payload=copy.deepcopy(self.worker.approved);del payload['hosted_review'];self.review=r.sign('rehearsal-review',payload,self.key)
        with self.assertRaises(r.Blocked):self.make()

if __name__=='__main__':unittest.main()
