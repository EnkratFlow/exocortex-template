"""Network-free disposable preview execution; provider authority stays on the host.

Trusted callers pin one local image ID, published source and disposable checkout.
This adapter is preview-only. It does not provision credentials, grant authority,
start Docker, pull images or accept any browser-selected path/command.
"""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid

from pr_runner_prepare import updater


class IsolationError(updater.UpdateError):
    pass


def directory(value):
    path = Path(value)
    if (not path.is_absolute() or path.resolve() != path or not path.is_dir()
            or any(c in str(path) for c in ',\n\r\x00') or path == Path('/')
            or path == Path.home()):
        raise IsolationError('unsafe_isolation_path')
    return path


class DockerPreview:
    def __init__(self, image, source, checkout, backup_root, docker='docker', timeout=240):
        if not isinstance(image,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',image):
            raise IsolationError('immutable_image_required')
        if type(timeout) is not int or not 1 <= timeout <= 240:
            raise IsolationError('invalid_isolation_timeout')
        self.image, self.source = image, copy.deepcopy(source)
        self.checkout, self.backup = directory(checkout), directory(backup_root)
        src = directory(source['path'])
        if any(not updater.independent(a,b) for a,b in ((src,self.checkout),(src,self.backup),(self.checkout,self.backup))):
            raise IsolationError('overlapping_isolation_paths')
        # A shared-worktree .git file would expose a host Git family outside the
        # mount. The host must provision a standalone disposable clone.
        if not (self.checkout/'.git').is_dir() or (self.checkout/'.git').is_symlink():
            raise IsolationError('standalone_checkout_required')
        self.docker, self.timeout = docker, timeout
        self.last_evidence = None
        self.endpoint = None
        self.docker_config = None
        self.launcher = None
        self.owner = None

    def _environment(self):
        # No ambient Docker host/context, plugin configuration or proxy injection.
        return {k:os.environ[k] for k in ('PATH','HOME','TMPDIR') if k in os.environ}

    def _command(self, args):
        return ([self.docker] + (['--config',str(self.docker_config)] if self.docker_config else [])
                + (['--host',self.endpoint] if self.endpoint else []) + args)

    def _control(self, args):
        try:
            result = subprocess.run(self._command(args),env=self._environment(),capture_output=True,timeout=30)
            if result.returncode or len(result.stdout)>1024*1024:
                raise IsolationError('container_control_failed')
            return result.stdout.decode('utf-8')
        except (OSError,UnicodeError,subprocess.SubprocessError):
            raise IsolationError('container_control_failed') from None

    def _create_args(self, backup):
        args = ['create','--pull=never','--network=none','--read-only',
                '--cap-drop=ALL','--security-opt=no-new-privileges',
                '--user',f'{os.getuid()}:{os.getgid()}', '--cpus=1',
                '--memory=512m','--memory-swap=512m','--pids-limit=128',
                '--log-driver=none','--restart=no','--init',
                '--tmpfs','/tmp:rw,nosuid,nodev,size=268435456,mode=1777',
                '--workdir',str(self.checkout),'--entrypoint','/bin/bash']
        if self.owner:
            args += ['--name',self.owner,'--label','exocortex.preview.owner='+self.owner]
        mounts=[(Path(self.source['path']),True),(self.checkout,True),(backup,False)]
        if self.launcher:mounts.append((self.launcher,True))
        for source, readonly in mounts:
            args += ['--mount',f'type=bind,source={source},target={source}'+(',readonly' if readonly else '')]
        for value in ('HOME=/tmp','TMPDIR=/tmp','LC_ALL=C','LANG=C','PYTHONDONTWRITEBYTECODE=1',
                      'PATH=/usr/local/bin:/usr/bin:/bin','GIT_CONFIG_NOSYSTEM=1','GIT_CONFIG_GLOBAL=/dev/null',
                      'HTTP_PROXY=','HTTPS_PROXY=','ALL_PROXY=','NO_PROXY=','FTP_PROXY=','ftp_proxy=',
                      'http_proxy=','https_proxy=','all_proxy=','no_proxy='):
            args += ['--env',value]
        return args+[self.image,'--noprofile','--norc',str((self.launcher or Path(self.source['path']))/'scripts/safe-update.sh'),
                     '--template',self.source['path'],'--candidate-digest',self.source['manifest_sha256'],
                     '--backup-dir',str(backup),'--dry-run']

    def _inspect(self, cid, backup):
        try:
            data=json.loads(self._control(['inspect',cid]))
            if not isinstance(data,list) or len(data)!=1:raise ValueError()
            info=data[0];host=info['HostConfig'];config=info['Config']
            mounts={(m['Source'],m['Destination'],m['RW'],m['Type']) for m in info['Mounts'] if m['Type']!='tmpfs'}
            expected={(self.source['path'],self.source['path'],False,'bind'),
                      (str(self.checkout),str(self.checkout),False,'bind'),(str(backup),str(backup),True,'bind')}
            if self.launcher:expected.add((str(self.launcher),str(self.launcher),False,'bind'))
            if (info['Id']!=cid or info['Image']!=self.image or config['User']!=f'{os.getuid()}:{os.getgid()}'
                or host['NetworkMode']!='none' or not host['ReadonlyRootfs'] or host['Privileged']
                or set(host['CapDrop'])!={'ALL'} or host.get('CapAdd')
                or set(host['SecurityOpt']) not in ({'no-new-privileges'},{'no-new-privileges=true'})
                or host['Memory']!=536870912 or host['MemorySwap']!=536870912
                or host['NanoCpus']!=1000000000 or host['PidsLimit']!=128
                or host['LogConfig']['Type']!='none' or host['RestartPolicy']['Name']!='no'
                or mounts!=expected or len([m for m in info['Mounts'] if m['Type']!='tmpfs'])!=len(expected)):
                raise ValueError()
            return {'image':self.image,'network':'none','root_read_only':True,
                    'checkout_read_only':True,'source_read_only':True,'nonroot':True,
                    'memory_bytes':host['Memory'],'cpus':1,'pids_limit':128}
        except (KeyError,TypeError,ValueError):
            raise IsolationError('container_boundary_mismatch') from None

    def __call__(self, source, row, backup, authority=None):
        if authority is not None:
            raise IsolationError('isolated_preview_only')
        if source!=self.source or Path(row['path'])!=self.checkout or os.getuid()==0:
            raise IsolationError('isolation_binding_changed')
        directory(self.checkout);directory(self.source['path']);directory(self.backup)
        backup=Path(backup)
        if not backup.is_absolute() or backup.resolve()!=backup or self.backup not in backup.parents:
            raise IsolationError('unsafe_backup_path')
        backup.mkdir(mode=0o700,parents=True,exist_ok=True);directory(backup)
        # Provider checks execute in the trusted host, never in the container.
        # A raw call cannot bypass the controller's published-source requirement.
        updater.verify_source(self.source,apply=True)
        # Discover only the selected local context; execution uses a new empty
        # config and an explicit endpoint, including start and cleanup.
        self.endpoint=None;self.docker_config=None
        endpoint=self._control(['context','inspect','--format','{{.Endpoints.docker.Host}}']).strip()
        if not re.fullmatch(r'unix:///[^\s\x00]+',endpoint):
            raise IsolationError('local_docker_engine_required')
        self.endpoint=endpoint
        with tempfile.TemporaryDirectory(prefix='exocortex-isolated-preview-') as tmp:
            self.docker_config=Path(tmp)/'docker';self.docker_config.mkdir()
            self.launcher=Path(tmp).resolve()/'launcher';self.launcher.mkdir()
            (self.launcher/'scripts').mkdir()
            manifest=updater.file_bytes(Path(source['path'])/'SHA256SUMS')
            if updater.digest(manifest)!=source['manifest_sha256']:
                raise IsolationError('launcher_manifest_changed')
            hashes=dict((line.split('  ',1)[1],line.split('  ',1)[0]) for line in manifest.decode().splitlines())
            (self.launcher/'SHA256SUMS').write_bytes(manifest)
            for rel in ('scripts/safe-update.sh','scripts/windows.ps1'):
                data=updater.file_bytes(Path(source['path'])/rel)
                if updater.digest(data)!=hashes.get(rel):raise IsolationError('launcher_changed')
                (self.launcher/rel).write_bytes(data)
            try:return self._run(backup)
            finally:self.launcher=None;self.docker_config=None;self.owner=None

    def _run(self, backup):
        self.owner='exocortex-preview-'+uuid.uuid4().hex
        cid=None
        try:
            cid=self._control(self._create_args(backup)).strip()
            if not re.fullmatch('[0-9a-f]{64}',cid):
                cid=None
                raise IsolationError('container_identity_unavailable')
            evidence=self._inspect(cid,backup)
            with tempfile.TemporaryFile() as output:
                try:
                    process=subprocess.Popen(self._command(['start','--attach',cid]),env=self._environment(),stdout=output,stderr=subprocess.STDOUT)
                except OSError:raise IsolationError('container_start_failed') from None
                deadline=time.monotonic()+self.timeout
                try:
                    while process.poll() is None:
                        if time.monotonic()>=deadline or os.fstat(output.fileno()).st_size>8*1024*1024:
                            raise IsolationError('container_execution_bound')
                        time.sleep(0.1)
                    if os.fstat(output.fileno()).st_size>8*1024*1024:raise IsolationError('container_output_bound')
                    output.seek(0);text=output.read().decode('utf-8',errors='replace')
                    self.last_evidence=dict(evidence,exit_code=process.returncode)
                    return process.returncode,text
                finally:
                    if process.poll() is None:
                        process.kill();process.wait(timeout=10)
        finally:
            if cid:
                # Cleanup failure is a failure, even after a successful preview.
                self._control(['rm','--force',cid])
            else:
                # Creation may have succeeded even when the client lost its
                # response. Find only this unpredictable name AND ownership label.
                owned=self._control(['ps','-aq','--no-trunc','--filter','name=^/'+self.owner+'$',
                                     '--filter','label=exocortex.preview.owner='+self.owner]).strip()
                if owned:
                    if not re.fullmatch('[0-9a-f]{64}',owned):raise IsolationError('ambiguous_container_cleanup')
                    self._control(['rm','--force',owned])


def observe_repository(config):
    """Two fixed read-only GitHub requests using the host's existing gh session."""
    from urllib.parse import quote
    repository=config['repository']
    if (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository)
            or not isinstance(config['base_branch'],str) or not config['base_branch']
            or len(config['base_branch'])>128):
        raise IsolationError('invalid_repository_binding')
    def read(path):
        try:
            p=subprocess.run(['gh','api','--method','GET',path],capture_output=True,timeout=30)
            if p.returncode or len(p.stdout)>1024*1024:raise ValueError()
            return json.loads(p.stdout)
        except (OSError,ValueError,subprocess.SubprocessError):
            raise IsolationError('repository_observation_failed') from None
    info=read('repos/'+repository)
    ref=read('repos/'+repository+'/git/ref/heads/'+quote(config['base_branch'],safe=''))
    if (str(info.get('id'))!=config['repository_id'] or info.get('full_name')!=repository
            or info.get('default_branch')!=config['base_branch'] or info.get('archived') is not False
            or ref.get('object',{}).get('type')!='commit'
            or ref['object'].get('sha')!=config['base_sha']):
        raise IsolationError('repository_binding_changed')


def preview_config(config):
    """Run/reuse one host-pinned plan. No apply or hosted identity impersonation."""
    expected={'image','source','checkout','backup_root','controller','plan_id','account_scope',
              'repository','repository_id','base_branch','base_sha'}
    if not isinstance(config,dict) or set(config)!=expected:
        raise IsolationError('invalid_host_configuration')
    if (not isinstance(config['repository_id'],str) or not re.fullmatch('[1-9][0-9]{0,19}',config['repository_id'])
            or not isinstance(config['base_sha'],str) or not re.fullmatch('[0-9a-f]{40}',config['base_sha'])):
        raise IsolationError('invalid_repository_binding')
    controller=directory(config['controller']);source=config['source']
    invoke=DockerPreview(config['image'],source,config['checkout'],config['backup_root'])
    if any(not updater.independent(controller,p) for p in (Path(source['path']),invoke.checkout,invoke.backup)):
        raise IsolationError('overlapping_controller_path')
    observe_repository(config)
    updater.verify_source(source,apply=True)
    if (updater.state.git(invoke.checkout,'rev-parse','HEAD')!=config['base_sha'] or
        updater.state.remote_identity(updater.state.git(invoke.checkout,'remote','get-url','origin'))
            !='github.com/'+config['repository'].lower()):
        raise IsolationError('checkout_binding_changed')
    pid=config['plan_id'];path=updater.plan_path(controller,pid)
    if not path.exists():
        updater.create(controller,pid,source['path'],source['manifest_sha256'],invoke.backup,
                       [invoke.checkout],config['account_scope'],source['release'])
    plan=updater.load(controller,pid)
    if (plan['source']!=source or plan['account_scope']!=config['account_scope']
            or Path(plan['backup_root'])!=invoke.backup or len(plan['targets'])!=1
            or plan['targets'][0]['path']!=str(invoke.checkout)
            or (plan['targets'][0].get('initial') or {}).get('binding',{}).get('head')!=config['base_sha']):
        raise IsolationError('saved_plan_binding_changed')
    from pr_runner import digest
    result=updater.execute(controller,pid,digest(plan),'preview',preview_invoker=invoke,
                           lock_root=controller/'locks')
    observe_repository(config)
    updater.verify_source(source,apply=True)
    row=result['targets'][0]
    if row.get('initial')!=updater.target(invoke.checkout,updater.candidate_hashes(source)):
        raise IsolationError('checkout_changed_during_preview')
    return {'state':row['state'],'plan_sha256':result['plan_sha256'],
            'changed_files':len((row.get('receipt') or {}).get('changed_paths',[])),
            'container':invoke.last_evidence,'provider_writes':False}


def main():
    import argparse
    from pr_runner_authority import private_json
    parser=argparse.ArgumentParser(description='One network-free disposable update preview. No apply or publication.')
    parser.add_argument('--config',required=True,help='Owner-private fixed host configuration; no credentials')
    args=parser.parse_args()
    try:
        result=preview_config(private_json(args.config))
        print(json.dumps(result))
        return 0 if result['state'] in ('ready','current') else 1
    except Exception:
        # Provider errors and filesystem details stay off the public output.
        print(json.dumps({'state':'blocked','error':'isolated_preparation_failed','provider_writes':False}))
        return 1


if __name__=='__main__':
    raise SystemExit(main())
