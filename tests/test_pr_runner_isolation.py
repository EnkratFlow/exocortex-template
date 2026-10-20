import copy
import json
import hashlib
import subprocess
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/update-dashboard'))
from pr_runner_isolation import DockerPreview, DockerRehearsal, IsolationError, updater, observe_repository, preview_config

@unittest.skipUnless(os.name=='posix','Docker host adapter requires POSIX host')
class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        for name in ('source','checkout','backups'):(self.root/name).mkdir()
        (self.root/'checkout/.git').mkdir()
        (self.root/'source/scripts').mkdir()
        manifest=''
        for rel in ('scripts/safe-update.sh','scripts/windows.ps1'):
            data=b'fictional launcher';(self.root/'source'/rel).write_bytes(data)
            manifest+=hashlib.sha256(data).hexdigest()+'  '+rel+'\n'
        (self.root/'source/SHA256SUMS').write_text(manifest)
        self.source={'path':str(self.root/'source'),'manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest(),'release':None}
        self.image='sha256:'+'b'*64
        self.adapter=DockerPreview(self.image,self.source,self.root/'checkout',self.root/'backups')
        self.backup=self.root/'backups/plan/target';self.cid='c'*64;self.calls=[]
        p=patch('pr_runner_isolation.os.getuid',return_value=1000);p.start();self.addCleanup(p.stop)
        p=patch.object(updater,'verify_source',return_value=self.root/'source');self.verify=p.start();self.addCleanup(p.stop)
    def info(self):
        info={'Id':self.cid,'Image':self.image,'Config':{'User':f'1000:{os.getgid()}'},
          'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,'CapDrop':['ALL'],
           'CapAdd':None,'SecurityOpt':['no-new-privileges=true'],'Memory':536870912,'MemorySwap':536870912,
           'NanoCpus':1000000000,'PidsLimit':128,'LogConfig':{'Type':'none'},'RestartPolicy':{'Name':'no'}},
          'Mounts':[{'Source':str(p),'Destination':str(p),'RW':rw,'Type':'bind'} for p,rw in
           [(self.root/'source',False),(self.root/'checkout',False),(self.backup,True)]]}
        if self.adapter.launcher:
            info['Mounts'].append({'Source':str(self.adapter.launcher),'Destination':str(self.adapter.launcher),'RW':False,'Type':'bind'})
        return info
    def control(self,args):
        self.calls.append(args)
        if args[0]=='context':return 'unix:///var/run/docker.sock\n'
        if args[0]=='create':return self.cid
        if args[0]=='inspect':return json.dumps([self.info()])
        if args[0]=='rm':return self.cid
        self.fail('unexpected controller operation')
    def test_only_pinned_readonly_mounts_and_no_network_or_privilege(self):
        args=self.adapter._create_args(self.backup)
        for option in ('--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--dry-run'):
            self.assertIn(option,args)
        self.assertNotIn('--apply',args);self.assertEqual(args.count('--mount'),3)
        self.assertEqual(args[-1],'--dry-run');self.assertIn(self.image,args)
    def test_mutable_image_shared_checkout_and_overlapping_paths_rejected(self):
        with self.assertRaises(IsolationError):DockerPreview('python:latest',self.source,self.root/'checkout',self.root/'backups')
        with self.assertRaises(IsolationError):DockerPreview(self.image,self.source,self.root/'checkout',self.root)
        (self.root/'checkout/.git').rmdir();(self.root/'checkout/.git').write_text('gitdir: /external')
        with self.assertRaises(IsolationError):DockerPreview(self.image,self.source,self.root/'checkout',self.root/'backups')
    def test_source_target_apply_and_backup_escape_rejected_before_control(self):
        with patch.object(self.adapter,'_control',side_effect=self.fail):
            for source,row,backup,authority in [(self.source,{'path':str(self.root/'checkout')},self.backup,{}),
                 ({**self.source,'manifest_sha256':'d'*64},{'path':str(self.root/'checkout')},self.backup,None),
                 (self.source,{'path':str(self.root/'other')},self.backup,None),
                 (self.source,{'path':str(self.root/'checkout')},self.root/'outside',None)]:
                with self.assertRaises(IsolationError):self.adapter(source,row,backup,authority)
    def test_published_source_required_before_container_created(self):
        self.verify.side_effect=updater.UpdateError('unpublished')
        with patch.object(self.adapter,'_control',side_effect=self.fail):
            with self.assertRaises(updater.UpdateError):self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
        self.verify.assert_called_once_with(self.source,apply=True)
    def test_inspected_boundary_mismatch_stops_before_start_and_cleans_up(self):
        for field,value in [('NetworkMode','host'),('Privileged',True),('ReadonlyRootfs',False),('CapAdd',['SYS_ADMIN']),('Memory',0),('SecurityOpt',['no-new-privileges=false'])]:
            def control(args):
                if args[0]=='inspect':
                    info=self.info();info['HostConfig'][field]=value
                    return json.dumps([info])
                return self.control(args)
            with patch.object(self.adapter,'_control',side_effect=control),patch('pr_runner_isolation.subprocess.Popen') as start:
                with self.assertRaises(IsolationError):self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
                start.assert_not_called();self.assertEqual(self.calls[-1],['rm','--force',self.cid])
    def test_extra_or_writable_target_mount_rejected(self):
        for mutate in (lambda v:v['Mounts'][1].update(RW=True),lambda v:v['Mounts'].append(v['Mounts'][0])):
            info=self.info();mutate(info)
            with patch.object(self.adapter,'_control',return_value=json.dumps([info])):
                with self.assertRaises(IsolationError):self.adapter._inspect(self.cid,self.backup)
    def test_success_cleans_only_owned_container(self):
        process=Mock();process.poll.return_value=0;process.returncode=0
        with patch.object(self.adapter,'_control',side_effect=self.control),patch('pr_runner_isolation.subprocess.Popen',return_value=process):
            self.assertEqual(self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup),(0,''))
        self.assertEqual(self.calls[-1],['rm','--force',self.cid]);self.assertEqual(self.adapter.last_evidence['network'],'none')
    def test_timeout_kills_attachment_and_removes_container(self):
        process=Mock();process.poll.return_value=None
        with patch.object(self.adapter,'_control',side_effect=self.control),patch('pr_runner_isolation.subprocess.Popen',return_value=process),patch('pr_runner_isolation.time.monotonic',side_effect=[0,241]):
            with self.assertRaisesRegex(IsolationError,'execution_bound'):self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
        process.kill.assert_called_once();self.assertEqual(self.calls[-1],['rm','--force',self.cid])
    def test_docker_endpoint_and_configuration_are_pinned(self):
        self.adapter.endpoint='unix:///local.sock';self.adapter.docker_config=self.root/'empty-config'
        with patch.dict(os.environ,{'DOCKER_HOST':'tcp://remote:2375','DOCKER_CONTEXT':'remote','DOCKER_CONFIG':'/ambient','FTP_PROXY':'secret'}),patch('pr_runner_isolation.subprocess.run') as run:
            run.return_value=Mock(returncode=0,stdout=b'ok')
            self.adapter._control(['inspect',self.cid])
            args=run.call_args.args[0];env=run.call_args.kwargs['env']
            self.assertEqual(args[:5],['docker','--config',str(self.root/'empty-config'),'--host','unix:///local.sock'])
            self.assertFalse(any(k.startswith('DOCKER_') or 'PROXY' in k for k in env))
    def test_ambiguous_create_cleans_named_owned_container(self):
        for failure in (IsolationError('timeout'), 'malformed'):
            self.calls=[]
            def control(args):
                self.calls.append(args)
                if args[0]=='context':return 'unix:///local.sock'
                if args[0]=='create':
                    if isinstance(failure,Exception):raise failure
                    return failure
                if args[0]=='ps':return self.cid
                if args[0]=='rm':return self.cid
                self.fail('unexpected call')
            with patch.object(self.adapter,'_control',side_effect=control),patch('pr_runner_isolation.subprocess.Popen') as start:
                with self.assertRaises(IsolationError):self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
                start.assert_not_called()
            create=next(c for c in self.calls if c[0]=='create');name=create[create.index('--name')+1]
            lookup=next(c for c in self.calls if c[0]=='ps')
            self.assertIn('label=exocortex.preview.owner='+name,lookup)
            self.assertEqual(self.calls[-1],['rm','--force',self.cid])
    def test_launcher_mutation_blocks_before_create(self):
        (self.root/'source/scripts/safe-update.sh').write_text('changed')
        with patch.object(self.adapter,'_control',side_effect=self.control),patch('pr_runner_isolation.subprocess.Popen') as start:
            with self.assertRaisesRegex(IsolationError,'launcher_changed'):self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
            start.assert_not_called()
        self.assertFalse(any(c[0]=='create' for c in self.calls))
    def host_config(self):
        controller=self.root/'controller';controller.mkdir(exist_ok=True)
        return {'image':self.image,'source':self.source,'checkout':str(self.root/'checkout'),
                'backup_root':str(self.root/'backups'),'controller':str(controller),'plan_id':'fixture',
                'account_scope':'fixture','repository':'example/disposable','repository_id':'123',
                'base_branch':'main','base_sha':'d'*40}
    def test_provider_observer_checks_immutable_identity_and_base(self):
        config=self.host_config()
        good=[{'id':123,'full_name':'example/disposable','default_branch':'main','archived':False},
              {'object':{'type':'commit','sha':'d'*40}}]
        for change in (None,'identity','base','archived'):
            data=copy.deepcopy(good)
            if change=='identity':data[0]['id']=124
            if change=='base':data[1]['object']['sha']='e'*40
            if change=='archived':data[0]['archived']=True
            with patch('pr_runner_isolation.subprocess.run',side_effect=[Mock(returncode=0,stdout=json.dumps(v).encode()) for v in data]) as run:
                if change:
                    with self.assertRaisesRegex(IsolationError,'binding_changed'):observe_repository(config)
                else:observe_repository(config)
                for call in run.call_args_list:self.assertEqual(call.args[0][:4],['gh','api','--method','GET'])
    def test_host_config_rejects_extra_browser_fields_and_overlapping_controller(self):
        config=self.host_config()
        with self.assertRaisesRegex(IsolationError,'invalid_host_configuration'):preview_config(dict(config,command='anything'))
        config['controller']=config['checkout']
        with self.assertRaisesRegex(IsolationError,'overlapping_controller_path'):preview_config(config)
    def test_provider_drift_stops_before_plan_or_container(self):
        with patch('pr_runner_isolation.observe_repository',side_effect=IsolationError('repository_binding_changed')),patch.object(updater,'create') as create,patch.object(DockerPreview,'__call__') as execute:
            with self.assertRaisesRegex(IsolationError,'binding_changed'):preview_config(self.host_config())
            create.assert_not_called();execute.assert_not_called()
    def test_saved_plan_cannot_rebind_account_or_source(self):
        config=self.host_config();planpath=self.root/'saved.json';planpath.touch()
        plan={'source':self.source,'account_scope':'another-account'}
        with patch('pr_runner_isolation.observe_repository'),patch.object(updater.state,'git',side_effect=['d'*40,'https://github.com/example/disposable.git']),patch.object(updater,'plan_path',return_value=planpath),patch.object(updater,'load',return_value=plan),patch.object(updater,'execute') as execute:
            with self.assertRaisesRegex(IsolationError,'saved_plan_binding_changed'):preview_config(config)
            execute.assert_not_called()
    def test_preview_adapter_cannot_be_supplied_for_apply(self):
        with self.assertRaisesRegex(updater.UpdateError,'cannot authorize apply'):
            updater.execute(self.root,'unused','0'*64,'apply',preview_invoker=self.adapter)

    def authority(self):
        return dict(capability='.exocortex/local/protocol/capabilities/fixture.json',
                    work_item_id='fixture',work_item_revision=0,request_id='fixture',
                    surface_id='fixture',executor_id='fixture',adapter_version='fixture-v1')

    def rehearsal(self):
        return DockerRehearsal(self.image,self.source,self.root/'checkout',self.root/'backups',self.authority())

    def test_rehearsal_dryrun_readonly_and_apply_has_readonly_git(self):
        adapter=self.rehearsal();seen=[]
        def run(backup):
            seen.append((adapter._create_args(backup),adapter._mounts(backup)))
            return 0,''
        with patch.object(adapter,'_control',side_effect=self.control),patch.object(adapter,'_run',side_effect=run):
            adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
            adapter(self.source,{'path':str(self.root/'checkout')},self.backup,self.authority())
            adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
        for n in (0,2):
            self.assertIn('--dry-run',seen[n][0]);self.assertTrue(dict(seen[n][1])[self.root/'checkout'])
        self.assertIn('--apply',seen[1][0]);self.assertFalse(dict(seen[1][1])[self.root/'checkout'])
        self.assertTrue(dict(seen[1][1])[self.root/'checkout/.git'])
        self.assertIn(self.authority()['capability'],seen[1][0])

    def test_rehearsal_rejects_changed_authority_before_container(self):
        adapter=self.rehearsal()
        with patch.object(adapter,'_control',side_effect=self.fail):
            for auth in ({},{**self.authority(),'request_id':'another'}):
                with self.assertRaises(updater.UpdateError):adapter(self.source,{'path':str(self.root/'checkout')},self.backup,auth)

    def test_writable_aliases_fail_without_changing_outside_file(self):
        outside=self.root/'outside';outside.write_text('preserve')
        adapter=self.rehearsal()
        for link in ('hard','symbolic'):
            target=self.root/'checkout/linked'
            if link=='hard':os.link(outside,target)
            else:target.symlink_to(outside)
            with patch.object(adapter,'_control',side_effect=self.fail):
                with self.assertRaisesRegex(IsolationError,'unsafe_rehearsal_tree'):
                    adapter(self.source,{'path':str(self.root/'checkout')},self.backup,self.authority())
            self.assertEqual(outside.read_text(),'preserve');target.unlink()

    def test_preview_backup_alias_rejected(self):
        self.backup.mkdir(parents=True)
        outside=self.root/'outside';outside.write_text('preserve')
        os.link(outside,self.backup/'alias')
        with patch.object(self.adapter,'_control',side_effect=self.fail):
            with self.assertRaisesRegex(IsolationError,'unsafe_rehearsal_tree'):
                self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup)

    def test_git_replacement_after_construction_rejected(self):
        adapter=self.rehearsal()
        (self.root/'checkout/.git').rmdir();(self.root/'checkout/.git').write_text('gitdir: /elsewhere')
        with patch.object(adapter,'_control',side_effect=self.fail):
            with self.assertRaisesRegex(IsolationError,'standalone_checkout_required'):
                adapter(self.source,{'path':str(self.root/'checkout')},self.backup,self.authority())

    def test_expiry_after_container_creation_prevents_start_and_cleans_up(self):
        self.adapter.before_start=Mock(side_effect=IsolationError('expired'))
        with patch.object(self.adapter,'_control',side_effect=self.control),patch('pr_runner_isolation.subprocess.Popen') as start:
            with self.assertRaisesRegex(IsolationError,'expired'):
                self.adapter(self.source,{'path':str(self.root/'checkout')},self.backup)
            start.assert_not_called()
        self.assertEqual(self.calls[-1],['rm','--force',self.cid])

    def test_inspection_rejects_writable_git_in_rehearsal(self):
        adapter=self.rehearsal();adapter._applying=True
        info=self.info()
        info['Mounts']=[{'Source':str(p),'Destination':str(p),'RW':not ro,'Type':'bind'} for p,ro in adapter._mounts(self.backup)]
        with patch.object(adapter,'_control',return_value=json.dumps([info])):
            self.assertFalse(adapter._inspect(self.cid,self.backup)['checkout_read_only'])
        info['Mounts'][-1]['RW']=True
        with patch.object(adapter,'_control',return_value=json.dumps([info])):
            with self.assertRaisesRegex(IsolationError,'boundary_mismatch'):adapter._inspect(self.cid,self.backup)

if __name__=='__main__':unittest.main()
