"""Offline exact artifact handoff, no credentials or provider writes."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
import pr_runner_publication_worker as w
import pr_runner as r
from test_pr_runner import sample,NOW

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.now=NOW;self.key=b'c'*32;self.prep=b'p'*32
        self.payload=sample();self.preview=copy.deepcopy(self.payload['job'])
        self.result=dict(state='review_ready',changed_files=1,plan_sha256='3'*64,error=None,details=dict(repository=self.preview['repository'],base_sha=self.preview['base_sha'],installed_version='3.0.0',release=self.preview['release']['tag'],changed_paths=[x['path'] for x in self.payload['artifact']['changes']],protected_data='passed'))
        self.approved=dict(job=self.preview,host_sha256='a'*64,plan_id='prep-'+'b'*32,plan_sha256='3'*64,target_id='target-1',authorities_sha256='c'*64,hosted_review=dict(preparation_id='b'*64,result_sha256=r.digest(self.result)))
        self.review=r.sign('rehearsal-review',self.approved,self.key)
        self.saved=dict(review_sha256=r.digest(self.review),packet=r.sign('prepared-update',self.payload,self.prep))
    def binding(self):return w.handoff(self.saved,self.review,self.preview,self.result,self.key,self.prep,7,self.now)
    def test_exact_handoff_contains_no_contents_host_paths_or_signatures(self):
        b=self.binding();self.assertEqual(b['job_id'],r.digest(self.payload['job']))
        self.assertEqual(b['artifact_sha256'],r.digest(self.payload['artifact']))
        self.assertEqual(set(b),{'preparation_id','result_sha256','job_id','artifact_sha256','preparation'})
    def test_signed_packets_and_review_wrapper_cannot_be_substituted(self):
        for field in ('signature','kind'):
            original=copy.deepcopy(self.saved);self.saved['packet'][field]='wrong'
            with self.assertRaises(r.Blocked):self.binding()
            self.saved=original
        self.saved['review_sha256']='0'*64
        with self.assertRaises(r.Blocked):self.binding()
    def test_signed_unreviewed_file_or_foreign_job_rejected(self):
        for field,value in [('account','foreign'),('base_sha','b'*40),('expires_at',NOW+400)]:
            payload=copy.deepcopy(self.payload);payload['job'][field]=value
            self.saved['packet']=r.sign('prepared-update',payload,self.prep)
            with self.assertRaises(r.Blocked):self.binding()
        payload=copy.deepcopy(self.payload);payload['artifact']['changes'][0]['path']='.exocortex/scripts/other.py';payload['job']['artifact_sha256']=r.digest(payload['artifact'])
        self.saved['packet']=r.sign('prepared-update',payload,self.prep)
        with self.assertRaises(r.Blocked):self.binding()
    def test_expiry_and_display_digest_rejected(self):
        self.now=NOW+300
        with self.assertRaises(r.Blocked):self.binding()
        self.now=NOW;self.result['details']['installed_version']='2.0.0'
        with self.assertRaises(r.Blocked):self.binding()
    def worker(self):
        self.calls=[];self.fail_report=False;self.expire=False
        b=self.binding();self.claim=dict(id='e'*64,lease='fixture',configuration=b,expires_at=NOW+300)
        def site(op,body):
            self.calls.append((op,body))
            if op=='poll':return {'job':copy.deepcopy(self.claim)}
            if op=='check':return {'allowed':True}
            if self.fail_report:raise r.Blocked('site_unavailable')
            return {'saved':True}
        broker=Mock();worker=w.PublicationWorker({},site,broker,clock=lambda:self.now)
        worker.load=Mock(side_effect=lambda:(self.saved['packet'],self.binding()))
        return worker
    def test_claim_mismatch_never_reaches_publisher(self):
        worker=self.worker();self.claim['configuration']['job_id']='f'*64
        with patch.object(w,'process') as publish:
            with self.assertRaises(r.Blocked):worker.once()
            publish.assert_not_called()
    def test_report_loss_retries_only_report_even_after_expiry(self):
        worker=self.worker();result=dict(state='complete',pr='https://github.com/example/project/pull/1',commit='a'*40,error=None)
        with patch.object(w,'process',return_value=result) as publish:
            self.fail_report=True
            with self.assertRaises(r.Blocked):worker.once()
            self.fail_report=False;self.now=NOW+400
            self.assertEqual(worker.once(),'complete');publish.assert_called_once()
        self.assertEqual([op for op,_ in self.calls],['poll','result','result'])
    def test_cleanup_failure_retains_result_without_republishing(self):
        worker=self.worker();worker.broker.revoke.side_effect=[None,r.Blocked('cleanup'),None]
        with patch.object(w,'process',return_value=dict(state='complete')) as publish:
            with self.assertRaises(r.Blocked):worker.once()
            self.assertEqual(worker.once(),'complete');publish.assert_called_once()
    def test_uncertain_publication_reports_recovery(self):
        worker=self.worker()
        with patch.object(w,'process',side_effect=RuntimeError('secret diagnostic')):
            self.assertEqual(worker.once(),'recovery_required')
        self.assertNotIn('secret',str(self.calls))
    def test_blocked_runner_result_is_not_claimed_harmless(self):
        worker=self.worker()
        with patch.object(w,'process',return_value=dict(state='blocked',pr=None,commit=None,error='verification_failed')):
            self.assertEqual(worker.once(),'recovery_required')
    def test_site_response_delay_cannot_extend_claim(self):
        worker=self.worker();original=worker.site
        def slow(op,body):
            response=original(op,body)
            if op=='check':self.now=NOW+300
            return response
        worker.site=slow
        def publish(config,claim,site,broker,**kwargs):
            with self.assertRaises(r.Blocked):site('check',{})
            return dict(state='recovery_required')
        with patch.object(w,'process',side_effect=publish):self.assertEqual(worker.once(),'recovery_required')
    def test_gate_reloads_handoff_and_checks_expiry(self):
        worker=self.worker()
        def publish(config,claim,site,broker,**kwargs):
            self.now=NOW+300
            with self.assertRaises(r.Blocked):site('check',{})
            return dict(state='recovery_required')
        with patch.object(w,'process',side_effect=publish):self.assertEqual(worker.once(),'recovery_required')


class RealPublicationBridgeTests(unittest.TestCase):
    def test_injected_artifact_requires_both_grant_and_live_hosted_permission(self):
        import tempfile,time
        from test_pr_runner import FakeBackend,COMMIT
        from pr_runner_pilot_worker import process
        for mode in ('missing','wrong','denied','allowed'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                root=Path(temp).resolve();root.chmod(0o700)
                prep=b'p'*32;grant=b'g'*32;payload=sample();job=payload['job']
                job.update(created_at=int(time.time()),expires_at=int(time.time())+300)
                packet=r.sign('prepared-update',payload,prep);jid=r.digest(job)
                def save(name,raw):
                    p=root/name;p.write_bytes(raw);p.chmod(0o600);return str(p)
                config={'runtime':str(root),'preparation_key':save('prep.key',prep),'publication_key':save('publish.key',grant),'github_id':7}
                if mode!='missing':
                    permission=dict(account=job['account'],job_id=jid,artifact_sha256=job['artifact_sha256'],expires_at=job['expires_at'])
                    if mode=='wrong':permission['job_id']='0'*64
                    save('grant.json',r.canonical(r.sign('publish-update-pr',permission,grant)))
                class Backend(FakeBackend):
                    def validate(self,j,a):
                        self.authority(j,a)
                backend=Backend()
                def factory(transport,authority):backend.authority=authority;return backend
                def transport(method,path,body=None):
                    self.assertEqual(method,'GET')
                    if path.startswith('/repositories/'):return {'id':456,'full_name':job['repository']}
                    if '/git/ref/heads/main' in path:return {'object':{'sha':job['base_sha']}}
                    if '/pulls/1' in path:return {'html_url':'https://github.com/example/project/pull/1','draft':True,'state':'open','merged':False,'head':{'ref':'codex/exocortex-update-'+jid,'sha':COMMIT,'repo':{'id':456}},'base':{'ref':'main','sha':job['base_sha'],'repo':{'id':456}}}
                    self.fail('Unexpected read')
                expected={'fictional':'exact-host-config'};claim={'id':'e'*64,'lease':'fixture','configuration':expected}
                with patch('pr_runner_pilot_worker.RepositoryAuthority',return_value=lambda *a:True),patch('pr_runner_pilot_worker.GitHubTransport',return_value=transport),patch('pr_runner_pilot_worker.GitHubBackend',side_effect=factory):
                    if mode in ('missing','wrong'):
                        with self.assertRaises(FileNotFoundError if mode=='missing' else r.Blocked):process(config,claim,lambda *a:{'allowed':True},None,prepared=packet,expected_configuration=expected)
                    else:
                        result=process(config,claim,lambda *a:{'allowed':mode!='denied'},None,prepared=packet,expected_configuration=expected)
                        self.assertEqual(result['state'],'complete' if mode=='allowed' else 'blocked')
                self.assertFalse((root/'prepared.json').exists())
                self.assertEqual(backend.calls,['objects','branch','pr'] if mode=='allowed' else [])

    def test_wrong_injected_configuration_cannot_submit(self):
        # Exercise the shared bridge's pin before creating any durable queue.
        import tempfile
        from pr_runner_pilot_worker import process
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();key=b'p'*32
            for name,data in [('prep.key',key),('publish.key',b'g'*32)]:
                p=root/name;p.write_bytes(data);p.chmod(0o600)
            config={'runtime':str(root),'preparation_key':str(root/'prep.key'),'publication_key':str(root/'publish.key')}
            with self.assertRaisesRegex(r.Blocked,'pilot_binding_mismatch'):
                process(config,{'configuration':{}},None,None,prepared=r.sign('prepared-update',sample(),key),expected_configuration={'exact':'pin'})
            self.assertFalse((root/'jobs').exists())

if __name__=='__main__':unittest.main()
