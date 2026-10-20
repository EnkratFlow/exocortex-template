import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
from pr_runner import Blocked
from pr_runner_isolation import DockerPreview
from pr_runner_preparation_host import host_controller,read_service_access

@unittest.skipUnless(os.name=='posix','POSIX attended host')
class HostTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        for name in ('source','checkout','backups','controller'):(self.root/name).mkdir()
        (self.root/'checkout/.git').mkdir()
        self.job=dict(repository='example/disposable',repository_id='123',base_branch='main',base_sha='a'*40,account='fixture')
        self.config=dict(image='sha256:'+'b'*64,source={'path':str(self.root/'source'),'manifest_sha256':'c'*64,'release':None},
            checkout=str(self.root/'checkout'),backup_root=str(self.root/'backups'),controller=str(self.root/'controller'),
            account_scope='fixture',**{k:v for k,v in self.job.items() if k!='account'})
    def test_controller_always_uses_isolated_preview_and_fixed_provider(self):
        authority=Mock();controller=host_controller(self.config,self.job,authority)
        self.assertIs(controller.authority,authority)
        self.assertIsInstance(controller.preview_invoker,DockerPreview)
        with patch('pr_runner_preparation_host.observe_repository') as observe:
            facts=controller.observe(self.job);observe.assert_called_once_with(self.config)
            self.assertEqual(facts['base_sha'],self.job['base_sha'])
            with self.assertRaises(Blocked):controller.observe(dict(self.job,base_sha='d'*40))
    def test_job_rebinding_extra_fields_and_controller_mounts_rejected(self):
        for config in (dict(self.config,repository='other/repo'),dict(self.config,account_scope='other'),dict(self.config,apply=True),dict(self.config,controller=self.config['checkout'])):
            with self.assertRaises(Blocked):host_controller(config,self.job,Mock())
    def test_service_access_stays_off_output(self):
        value='fictional-test-access'
        with patch('sys.stdin',io.StringIO('{"service_token":"'+value+'"}\n')),patch('sys.stdout',io.StringIO()) as output:
            self.assertEqual(read_service_access(),value)
            self.assertNotIn(value,output.getvalue())
    def test_service_input_bound_and_extra_fields(self):
        for raw in ('x'*16385,'{"service_token":"fixture","user":"forged"}'):
            with patch('sys.stdin',io.StringIO(raw)),patch('sys.stdout',io.StringIO()):
                with self.assertRaises(Blocked):read_service_access()
if __name__=='__main__':unittest.main()
