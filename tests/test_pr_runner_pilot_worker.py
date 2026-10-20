import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
from pr_runner import Blocked
from pr_runner_pilot_worker import SiteClient, binding
from pr_runner_transport import GitHubTransport

class Response(io.BytesIO):
    status=200

class PilotWorkerTests(unittest.TestCase):
    def test_site_origin_cannot_redirect_credentials_to_arbitrary_paths(self):
        for origin in ('http://example.invalid','https://user@example.invalid','https://example.invalid/extra','https://example.invalid?query','https://example.invalid:443'):
            with self.assertRaises(Blocked): SiteClient(origin,'fictional-service-token','unused')

    def test_fixed_paths_signed_body_and_separate_service_access(self):
        class Opener:
            def open(self,request,timeout):
                self.request=request
                self.timeout=timeout
                return Response(b'{"job":null}')
        opener=Opener();client=SiteClient('https://uat.example.invalid','fictional-service-token','unused',opener)
        with patch('pr_runner_pilot_worker.request_signature',return_value='fictional-signature') as signer:
            self.assertEqual(client('poll',{}),{'job':None})
            self.assertEqual(opener.request.full_url,'https://uat.example.invalid/api/update-worker/poll')
            self.assertEqual(opener.request.get_header('Oai-sites-authorization'),'Bearer fictional-service-token')
            self.assertIsNone(opener.request.get_header('Oai-authenticated-user-id'))
            self.assertIn(b'POST\nhttps://uat.example.invalid\n/api/update-worker/poll\n',signer.call_args.args[1])
            self.assertEqual(opener.timeout,30)
            with self.assertRaises(Blocked):client('https://evil.invalid',{})

    def test_preparation_lane_has_separate_signed_fixed_path(self):
        class Opener:
            def open(self,request,timeout):
                self.request=request
                return Response(b'{"job":null}')
        opener=Opener()
        client=SiteClient('https://uat.example.invalid','fixture','unused',opener,lane='preparation')
        with patch('pr_runner_pilot_worker.request_signature',return_value='fixture') as signer:
            self.assertEqual(client('poll',{}),{'job':None})
            self.assertEqual(opener.request.full_url,'https://uat.example.invalid/api/preparation-worker/poll')
            self.assertIn(b'/api/preparation-worker/poll\n',signer.call_args.args[1])
        with self.assertRaises(Blocked):
            SiteClient('https://uat.example.invalid','fixture','unused',lane='../other')

    def test_errors_and_large_response_never_expose_diagnostics(self):
        class Opener:
            def open(self,request,timeout):
                raise HTTPError(request.full_url,403,'fictional-sensitive-diagnostic',{},io.BytesIO(b'fictional-secret'))
        with patch('pr_runner_pilot_worker.request_signature',return_value='fixture'):
            with self.assertRaisesRegex(Blocked,'^site_unavailable$'):
                SiteClient('https://uat.example.invalid','fixture','unused',Opener())('poll',{})
            class Large:
                def open(self,*args,**kwargs):return Response(b'x'*65537)
            with self.assertRaisesRegex(Blocked,'^site_unavailable$'):
                SiteClient('https://uat.example.invalid','fixture','unused',Large())('poll',{})

    def test_single_pr_read_allowed_but_merge_and_other_methods_still_denied(self):
        class Opener:
            def open(self,*args,**kwargs):return Response(b'{"draft":true}')
        transport=GitHubTransport(lambda:'fixture',Opener())
        self.assertEqual(transport('GET','/repos/example/pilot/pulls/1'),{'draft':True})
        for method,path in [('POST','/repos/example/pilot/pulls/1'),('PUT','/repos/example/pilot/pulls/1/merge'),('GET','/repos/example/pilot/pulls/0')]:
            with self.assertRaises(Blocked):transport(method,path)

class RecoveryBridgeTests(unittest.TestCase):
    def fixture(self, state='pr_pending'):
        import tempfile, time
        import pr_runner as r
        from test_pr_runner import sample, FakeBackend, COMMIT
        temp=tempfile.TemporaryDirectory();root=Path(temp.name).resolve();root.chmod(0o700)
        prep=b'p'*32;grant=b'g'*32;payload=sample();payload['job']['created_at']=int(time.time());payload['job']['expires_at']=int(time.time())+300
        def save(name,data):
            path=root/name;path.write_bytes(data);path.chmod(0o600);return str(path)
        save('prepared.json',r.canonical(r.sign('prepared-update',payload,prep)))
        config={'runtime':str(root),'preparation_key':save('preparation.key',prep),'publication_key':save('publication.key',grant),'github_id':7}
        backend=FakeBackend();db=r.Runner(root/'jobs',prep,grant,backend)
        jid=db.submit(r.sign('prepared-update',payload,prep),'owner-1')
        approval=r.sign('publish-update-pr',{'account':'owner-1','job_id':jid,'artifact_sha256':payload['job']['artifact_sha256'],'expires_at':payload['job']['expires_at']},grant)
        save('grant.json',r.canonical(approval))
        url='https://github.com/example/project/pull/1'
        db._write(jid,state,commit=COMMIT,pr=url if state!='pr_pending' else None);db.close()
        row={'html_url':url,'draft':True,'state':'open','merged':False,'head':{'sha':COMMIT,'ref':'codex/exocortex-update-'+jid,'repo':{'id':456}},'base':{'sha':payload['job']['base_sha'],'ref':'main','repo':{'id':456}},'body':'<!-- exocortex-update-job:'+jid+' artifact:'+payload['job']['artifact_sha256']+' -->'}
        def transport(method,path,body=None):
            self.assertEqual(method,'GET')
            if path.startswith('/repositories/'):return {'id':456,'full_name':'example/project'}
            if '/git/ref/heads/codex' in path:return {'ref':'refs/heads/codex/exocortex-update-'+jid,'object':{'type':'commit','sha':COMMIT}}
            if path.endswith('/git/ref/heads/main'):return {'object':{'sha':payload['job']['base_sha']}}
            if '/pulls?' in path:return [row]
            if path.endswith('/pulls/1'):return row
            self.fail('unexpected provider operation')
        claim={'id':'f'*64,'lease':'fixture','reconcile_only':True,'configuration':binding(config,payload['job'])}
        return temp,config,claim,row,transport

    def test_cancelled_pending_pr_is_observed_without_authorizing_a_write(self):
        from pr_runner_pilot_worker import process
        temp,config,claim,row,transport=self.fixture()
        try:
            with patch('pr_runner_pilot_worker.RepositoryAuthority'),patch('pr_runner_pilot_worker.GitHubTransport',return_value=transport):
                result=process(config,claim,lambda *a:self.fail('no write gate during read-only reconciliation'),lambda:'fixture')
            self.assertEqual(result['state'],'complete');self.assertEqual(result['pr'],row['html_url'])
        finally:temp.cleanup()

    def test_needs_review_never_downgrades_to_complete(self):
        from pr_runner_pilot_worker import process
        temp,config,claim,row,transport=self.fixture('published_needs_review')
        try:
            with patch('pr_runner_pilot_worker.RepositoryAuthority'),patch('pr_runner_pilot_worker.GitHubTransport',return_value=transport):
                self.assertEqual(process(config,claim,lambda *a:None,lambda:'fixture')['state'],'needs_review')
        finally:temp.cleanup()

    def test_changed_pr_ref_is_rejected(self):
        from pr_runner_pilot_worker import process
        temp,config,claim,row,transport=self.fixture('complete');row['head']['ref']='foreign-branch'
        try:
            with patch('pr_runner_pilot_worker.RepositoryAuthority'),patch('pr_runner_pilot_worker.GitHubTransport',return_value=transport):
                with self.assertRaisesRegex(Blocked,'pilot_result_changed'):process(config,claim,lambda *a:None,lambda:'fixture')
        finally:temp.cleanup()

    def test_service_input_echo_is_disabled_before_readiness(self):
        import os,pty,select,subprocess,tempfile,time
        with tempfile.TemporaryDirectory() as directory:
            config=Path(directory).resolve()/'config.json';config.write_text('{}');config.chmod(0o600)
            master,slave=pty.openpty()
            process=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve().parents[1]/'tools/update-dashboard/pr_runner_pilot_worker.py'),'--config',str(config),'--duration','60'],stdin=slave,stdout=slave,stderr=slave)
            os.close(slave);output=b''
            try:
                deadline=time.monotonic()+5
                while b'Ready for service access' not in output and time.monotonic()<deadline:
                    if select.select([master],[],[],0.1)[0]:
                        chunk=os.read(master,4096)
                        if not chunk:break
                        output+=chunk
                self.assertIn(b'Ready for service access',output)
                os.write(master,b'{"service_token":"fictional-hidden-input"}\n')
                process.wait(timeout=5)
                try:
                    while select.select([master],[],[],0.1)[0]:
                        chunk=os.read(master,4096)
                        if not chunk:break
                        output+=chunk
                except OSError:pass
                self.assertNotIn(b'fictional-hidden-input',output)
            finally:
                if process.poll() is None:process.kill()
                os.close(master)

if __name__=='__main__': unittest.main()
