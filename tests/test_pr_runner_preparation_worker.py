"""Offline bridge tests: only the coordinator preview method is exposed."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
import pr_runner_preparation_worker as w
from test_pr_runner import sample, NOW

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.now=NOW;self.job=sample()['job'];self.calls=[]
        self.controller=Mock();self.controller.preview.return_value={'state':'ready','changed_paths':['fixture'],'plan_sha256':'a'*64}
        self.claim={'id':'b'*64,'lease':'fixture','configuration':w.configuration(self.job,7),'expires_at':self.job['expires_at']}
        self.allow=True;self.fail=False
        def site(op,body):
            self.calls.append((op,body))
            if op=='poll':return {'job':copy.deepcopy(self.claim)}
            if op=='check':return {'allowed':self.allow}
            if self.fail:raise w.Blocked('site_unavailable')
            return {'saved':True}
        self.worker=w.PreparationWorker(self.controller,self.job,7,site,clock=lambda:self.now)
    def test_preview_only_with_exact_plan_and_binding(self):
        self.assertEqual(self.worker.once(),'review_ready')
        self.controller.preview.assert_called_once_with('prep-'+'b'*32,self.job)
        self.controller.rehearse.assert_not_called();self.controller.freeze.assert_not_called()
        result=self.calls[-1][1]['result'];self.assertEqual(result['changed_files'],1);self.assertNotIn('fixture',str(result))
    def test_foreign_job_or_extra_paths_never_reach_controller(self):
        for change in (lambda c:c['configuration'].update(base='c'*40),lambda c:c.update(checkout='/tmp/foreign')):
            claim=copy.deepcopy(self.claim);change(self.claim)
            with self.assertRaises(w.Blocked):self.worker.once()
            self.claim=claim
        self.controller.preview.assert_not_called()
    def test_cancelled_or_expired_claim_never_reaches_controller(self):
        self.allow=False
        with self.assertRaises(w.Blocked):self.worker.once()
        self.allow=True;self.now=self.job['expires_at']+1
        with self.assertRaises(w.Blocked):self.worker.once()
        self.controller.preview.assert_not_called()
    def test_revocation_during_preview_never_reports_success(self):
        def preview(*a):self.allow=False;return {'state':'ready','changed_paths':[],'plan_sha256':'a'*64}
        self.controller.preview.side_effect=preview
        with self.assertRaises(w.Blocked):self.worker.once()
        self.assertFalse(any(op=='result' for op,_ in self.calls))
    def test_lost_result_retries_report_without_repeating_preview(self):
        self.fail=True
        with self.assertRaises(w.Blocked):self.worker.once()
        self.fail=False;self.assertEqual(self.worker.once(),'review_ready')
        self.controller.preview.assert_called_once();self.assertEqual(sum(op=='poll' for op,_ in self.calls),1)
    def test_lost_response_after_server_save_can_repeat_terminal_report(self):
        self.fail=True
        with self.assertRaises(w.Blocked):self.worker.once()
        self.fail=False;self.allow=False
        self.assertEqual(self.worker.once(),'review_ready')
        self.controller.preview.assert_called_once()
    def test_lost_lease_drops_pending_report_for_recovery(self):
        self.fail=True
        with self.assertRaises(w.Blocked):self.worker.once()
        def conflict(*a):raise w.Blocked('worker_report_conflict')
        self.worker.site=conflict
        with self.assertRaises(w.Blocked):self.worker.once()
        self.assertIsNone(self.worker.pending)
    def test_controller_failure_returns_bounded_blocked_result(self):
        self.controller.preview.side_effect=w.updater.UpdateError('internal diagnostic')
        self.assertEqual(self.worker.once(),'blocked')
        self.assertNotIn('internal diagnostic',str(self.calls))
    def test_current_requires_zero_changes(self):
        self.controller.preview.return_value.update(state='current',changed_paths=[])
        self.assertEqual(self.worker.once(),'current')
    def test_session_duration_bounded(self):
        for duration in (0,14401,True):
            with self.assertRaises(w.Blocked):self.worker.run(duration)
    def test_provider_expiry_during_gate_is_rechecked(self):
        original=self.worker.site
        def slow(op,body):
            result=original(op,body)
            if op=='check':self.now=self.job['expires_at']+1
            return result
        self.worker.site=slow
        with self.assertRaises(w.Blocked):self.worker.once()
        self.controller.preview.assert_not_called()

if __name__=='__main__':unittest.main()
