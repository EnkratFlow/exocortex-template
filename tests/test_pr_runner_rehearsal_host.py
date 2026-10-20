"""Signed review/retry boundaries; container and coordinator are mocked here."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
import pr_runner as r
import pr_runner_rehearsal_host as h
from test_pr_runner import sample, NOW


class ReviewedHostTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        for name in ('controller','source','checkout','backup'):(self.root/name).mkdir(mode=0o700)
        (self.root/'checkout/.git').mkdir()
        self.config=dict(image='sha256:'+'a'*64,source={'path':str(self.root/'source')},
                         controller=str(self.root/'controller'),checkout=str(self.root/'checkout'),
                         backup_root=str(self.root/'backup'),output=str(self.root/'controller/prepared.json'))
        self.plan={'id':'fixture','targets':[{'id':'target-1','state':'ready'}]}
        self.job=sample()['job'];self.job['plan_sha256']=r.digest(self.plan)
        self.auth={'target-1':dict(capability='.exocortex/local/protocol/capabilities/fixture.json',
            work_item_id='fixture',work_item_revision=0,request_id='fixture',surface_id='fixture',executor_id='fixture',adapter_version='fixture-v1')}
        self.key=b'fictional-control-key'*2;self.prepkey=b'fictional-preparation-key'*2
        self.review=r.sign('rehearsal-review',dict(job=copy.deepcopy(self.job),host_sha256=r.digest(self.config),
            plan_id='fixture',plan_sha256=r.digest(self.plan),target_id='target-1',authorities_sha256=r.digest(self.auth)),self.key)
        self.authority=Mock(return_value=True);self.controller=Mock()
        def rehearse(*args):
            self.plan['targets'][0]['state']='applied'
            packet=sample();packet['job']=dict(self.job,plan_sha256=r.digest(self.plan),artifact_sha256=r.digest(packet['artifact']))
            return r.sign('prepared-update',packet,self.prepkey)
        self.controller.rehearse.side_effect=rehearse
        for name,value in [('PreparationController',Mock(return_value=self.controller)),('observe_repository',Mock()),
                           ('DockerPreview',Mock()),('DockerRehearsal',Mock())]:
            p=patch.object(h,name,value);p.start();self.addCleanup(p.stop)
        p=patch.object(h.updater,'load',side_effect=lambda *a:copy.deepcopy(self.plan));p.start();self.addCleanup(p.stop)
    def run_review(self):
        return h.execute_reviewed(self.config,self.job,self.review,self.auth,self.authority,self.key,self.prepkey,lambda:NOW)
    def test_exact_review_applies_once_and_replay_returns_identical_packet(self):
        first=self.run_review();second=self.run_review()
        self.assertEqual(first,second);self.controller.rehearse.assert_called_once()
        saved=h.private_json(Path(self.config['output']))
        self.assertEqual(saved['review_sha256'],r.digest(self.review))
        self.assertEqual(Path(self.config['output']).stat().st_mode&0o777,0o600)
    def test_preview_signature_cannot_authorize_rehearsal(self):
        self.review=r.sign('prepared-update',self.review['payload'],self.key)
        with self.assertRaises(r.Blocked):self.run_review()
        self.controller.rehearse.assert_not_called()
    def test_changed_account_base_epoch_policy_source_path_or_authority_stops(self):
        original=copy.deepcopy(self.job)
        for field,value in [('account','other'),('base_sha','9'*40),('grant_epoch','5'),('policy',{**self.job['policy'],'revision':2})]:
            self.job=copy.deepcopy(original);self.job[field]=value
            with self.assertRaises(r.Blocked):self.run_review()
        self.job=original
        self.config['source']['path']=str(self.root/'elsewhere')
        with self.assertRaises(r.Blocked):self.run_review()
        self.config['source']['path']=str(self.root/'source')
        self.auth['target-1']['request_id']='different'
        with self.assertRaises(r.Blocked):self.run_review()
        self.controller.rehearse.assert_not_called()
    def test_interrupted_or_zero_change_plan_never_reapplies(self):
        for state in ('current','applying','applied','verification_failed','recovery_required','blocked'):
            self.plan['targets'][0]['state']=state
            with self.assertRaisesRegex(r.Blocked,'review_recovery'):self.run_review()
        self.controller.rehearse.assert_not_called()
    def test_expired_review_stops_before_rehearsal(self):
        self.job['expires_at']=NOW
        self.review['payload']['job']=copy.deepcopy(self.job)
        self.review=r.sign('rehearsal-review',self.review['payload'],self.key)
        with self.assertRaisesRegex(r.Blocked,'expired'):self.run_review()
        self.controller.rehearse.assert_not_called()
    def test_container_start_gate_rechecks_policy_and_provider(self):
        self.run_review()
        gate=h.DockerRehearsal.call_args.kwargs['before_start']
        self.authority.return_value=False
        with self.assertRaisesRegex(r.Blocked,'authority_rejected'):gate()
        self.authority.return_value=True;h.observe_repository.side_effect=r.Blocked('base_changed')
        with self.assertRaisesRegex(r.Blocked,'base_changed'):gate()
    def test_packet_write_failure_cannot_trigger_repeat_apply(self):
        with patch.object(h,'save_packet',side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):self.run_review()
        with self.assertRaisesRegex(r.Blocked,'review_recovery'):self.run_review()
        self.controller.rehearse.assert_called_once()
    def test_saved_packet_or_plan_tampering_fails_replay(self):
        self.run_review();self.plan['changed']=True
        with self.assertRaisesRegex(r.Blocked,'saved_rehearsal_changed'):self.run_review()
        self.controller.rehearse.assert_called_once()
    def test_revocation_during_saved_result_read_blocks_return(self):
        self.run_review()
        read=h.private_json
        def revoke(*a,**kw):
            value=read(*a,**kw);self.authority.return_value=False;return value
        with patch.object(h,'private_json',side_effect=revoke):
            with self.assertRaisesRegex(r.Blocked,'authority_rejected'):self.run_review()
        self.controller.rehearse.assert_called_once()
    def test_large_artifact_saved_privately_and_never_overwrites(self):
        output=Path(self.config['output'])
        value={'fixture':'x'*(600*1024)};h.save_packet(output,value)
        self.assertEqual(h.private_json(output,limit=r.MAX_PACKET),value)
        with self.assertRaises(FileExistsError):h.save_packet(output,{'changed':True})
        self.assertEqual(h.private_json(output,limit=r.MAX_PACKET),value)


if __name__=='__main__':unittest.main()
