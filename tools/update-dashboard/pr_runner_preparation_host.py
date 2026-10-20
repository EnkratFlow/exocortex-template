"""Attended preparation queue host. Execution is preview-only and network-free.

The operator supplies a private fixed configuration and existing signed policy.
No writer App key, publication grant, capability creation or daemon is provided.
"""
import argparse
import json
from pathlib import Path
import sys
import time

from pr_runner import Blocked, validate_job
from pr_runner_authority import RepositoryAuthority, private_json
from pr_runner_controller import PreparationController
from pr_runner_isolation import DockerPreview, directory, observe_repository, updater
from pr_runner_pilot_worker import SiteClient, signing_bytes
from pr_runner_preparation_worker import PreparationWorker


def host_controller(config, job, authority):
    expected={'image','source','checkout','backup_root','controller','account_scope',
              'repository','repository_id','base_branch','base_sha'}
    if not isinstance(config,dict) or set(config)!=expected:
        raise Blocked('invalid_preparation_host')
    if (any(config[k]!=job[k] for k in ('repository','repository_id','base_branch','base_sha'))
            or config['account_scope']!=job['account']):
        raise Blocked('preparation_host_binding_changed')
    root=directory(config['controller'])
    invoke=DockerPreview(config['image'],config['source'],config['checkout'],config['backup_root'])
    if any(not updater.independent(root,p) for p in (Path(config['source']['path']),invoke.checkout,invoke.backup)):
        raise Blocked('overlapping_preparation_host')
    def observe(current):
        if current!=job:raise Blocked('preparation_host_binding_changed')
        observe_repository(config)
        return {k:config[k] for k in ('repository_id','repository','base_branch','base_sha')}
    return PreparationController(root,config['source'],invoke.checkout,invoke.backup,
                                 authority,observe,preview_invoker=invoke)


def read_service_access():
    # Same attended hidden-stdin contract as the existing pilot worker.
    import termios
    saved=None
    if sys.stdin.isatty():
        saved=termios.tcgetattr(sys.stdin.fileno());hidden=list(saved)
        hidden[3]&=~termios.ECHO
        termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,hidden)
    try:
        print('Ready for service access on stdin (input is hidden).',flush=True)
        incoming=sys.stdin.readline(16385)
    finally:
        if saved:termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,saved)
    if len(incoming)>16384:raise Blocked('invalid_service_access')
    value=json.loads(incoming)
    if not isinstance(value,dict) or set(value)!={'service_token'}:raise Blocked('invalid_service_access')
    return value['service_token']


def main():
    parser=argparse.ArgumentParser(description='Attended isolated preparation preview; no apply or publication.')
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--duration',type=int,default=900)
    args=parser.parse_args()
    if not 1<=args.duration<=14400:raise Blocked('invalid_session_duration')
    config=private_json(args.config)
    expected={'host','job','authority_directory','control_key','worker_key','origin','github_id'}
    if not isinstance(config,dict) or set(config)!=expected:raise Blocked('invalid_preparation_host')
    job=private_json(config['job']);validate_job(job,int(time.time()))
    authority=RepositoryAuthority(config['authority_directory'],signing_bytes(config['control_key']))
    controller=host_controller(config['host'],job,authority)
    # Fail before accepting service access if private policy/source/provider drifted.
    controller._validate(job)
    site=SiteClient(config['origin'],read_service_access(),config['worker_key'],lane='preparation')
    worker=PreparationWorker(controller,job,config['github_id'],site)
    # Exclusive host lease across processes, even when hosted claims differ.
    with updater.local.lock(controller.root/'preparation-session.lock'):
        print('Preparation host active; dry runs only.',flush=True)
        result=worker.run(args.duration)
    print('Preparation host stopped: '+result,flush=True)


if __name__=='__main__':
    try:main()
    except Exception:
        print('Preparation host stopped safely; no update authorized.',flush=True)
        raise SystemExit(1)
