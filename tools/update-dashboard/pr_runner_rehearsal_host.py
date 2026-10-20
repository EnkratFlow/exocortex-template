"""One attended, exactly reviewed disposable rehearsal; never a publisher.

All paths and signed review records are operator-provisioned private input.
This module cannot issue review grants or installer capabilities, accept a
browser command, merge a PR, or acquire repository write credentials.
"""
import argparse
import os
from pathlib import Path
import tempfile
import time

from pr_runner import Blocked, canonical, digest, exact, verify, validate_artifact, validate_job, MAX_PACKET
from pr_runner_authority import RepositoryAuthority, private_json
from pr_runner_controller import PreparationController
from pr_runner_isolation import DockerPreview, DockerRehearsal, directory, observe_repository, updater
from pr_runner_pilot_worker import signing_bytes


def save_packet(output, value):
    raw=canonical(value)
    if len(raw)>MAX_PACKET:raise Blocked('prepared_record_too_large')
    fd,name=tempfile.mkstemp(prefix='.rehearsal-',dir=output.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        # Atomically create, never overwrite an existing recovery artifact.
        os.link(name,output)
    finally:
        os.unlink(name)
    directory_fd=os.open(output.parent,os.O_RDONLY)
    try:os.fsync(directory_fd)
    finally:os.close(directory_fd)


def execute_reviewed(config, job, review, authorities, authority, control_key, preparation_key, clock=time.time, request_gate=None):
    """Consume a separately signed review with existing local apply authority.

    A repeat after a durable success returns the exact saved artifact. An
    interrupted run never repeats apply: retain its plan/archive and explicitly
    review recovery. The output belongs to the host, outside every bind mount.
    """
    exact(config,('image','source','checkout','backup_root','controller','output'))
    validate_job(job,clock())
    approved=verify(review,'rehearsal-review',control_key)
    fields=('job','host_sha256','plan_id','plan_sha256','target_id','authorities_sha256')
    exact(approved, fields+(('hosted_review',) if 'hosted_review' in approved else ()))
    if 'hosted_review' in approved and not callable(request_gate):
        raise Blocked('hosted_request_gate_required')
    if (approved['job']!=job or approved['host_sha256']!=digest(config)
            or approved['authorities_sha256']!=digest(authorities)):
        raise Blocked('review_binding_changed')
    if not isinstance(authorities,dict) or set(authorities)!={approved['target_id']}:
        raise Blocked('exact_target_authority_required')
    root=directory(config['controller'])
    output=Path(config['output'])
    if (not output.is_absolute() or output.resolve()!=output or output.parent!=root
            or not output.name.endswith('.json')):
        raise Blocked('unsafe_rehearsal_output')
    paths=[root, directory(config['checkout']), directory(config['backup_root']), directory(config['source']['path'])]
    if any(not updater.independent(a,b) for i,a in enumerate(paths) for b in paths[i+1:]):
        raise Blocked('overlapping_rehearsal_host')

    def observe(current):
        # Plan/artifact digests change after verified apply; all other fields
        # stay pinned to the review's original authenticated job.
        if any(current[k]!=job[k] for k in job if k not in ('plan_sha256','artifact_sha256')):
            raise Blocked('review_binding_changed')
        observe_repository(job)
        return {k:job[k] for k in ('repository_id','repository','base_branch','base_sha')}

    def gate():
        if request_gate is not None:request_gate()
        validate_job(job,clock())
        if authority(job,None) is not True:raise Blocked('live_authority_rejected')
        observe(job)
        if request_gate is not None:request_gate()
        validate_job(job,clock())

    preview=DockerPreview(config['image'],config['source'],paths[1],paths[2],before_start=gate)
    rehearsal=DockerRehearsal(config['image'],config['source'],paths[1],paths[2],
                             authorities[approved['target_id']],before_start=gate)
    controller=PreparationController(root,config['source'],paths[1],paths[2],authority,observe,
                                     clock=clock,preview_invoker=preview,rehearsal_invoker=rehearsal)
    with updater.local.lock(root/'preparation-session.lock'):
        gate()
        controller._validate(job)
        plan=updater.load(root,approved['plan_id'])
        controller._bind(plan,job)
        if plan['targets'][0]['id']!=approved['target_id']:
            raise Blocked('review_binding_changed')
        if output.exists():
            saved=private_json(output,limit=12*1024*1024)
            exact(saved,('review_sha256','packet'))
            packet=verify(saved['packet'],'prepared-update',preparation_key)
            if (saved['review_sha256']!=digest(review) or plan['targets'][0]['state']!='applied'
                    or packet['job']!=dict(job,plan_sha256=digest(plan),artifact_sha256=digest(packet['artifact']))):
                raise Blocked('saved_rehearsal_changed')
            validate_artifact(packet['artifact'],packet['job'])
            gate()
            return saved['packet']
        if plan['targets'][0]['state']!='ready':
            raise Blocked('review_recovery_before_retry')
        updater.expect(plan,approved['plan_sha256'])
        if job['plan_sha256']!=approved['plan_sha256']:
            raise Blocked('review_binding_changed')
        packet=controller.rehearse(approved['plan_id'],approved['plan_sha256'],job,authorities,preparation_key)
        gate()
        save_packet(output,{'review_sha256':digest(review),'packet':packet})
        return packet


def main():
    parser=argparse.ArgumentParser(description='Run one separately reviewed disposable rehearsal; no publication.')
    parser.add_argument('--config',required=True)
    args=parser.parse_args()
    session=private_json(args.config)
    exact(session,('host','job','review','authorities','authority_directory','control_key','preparation_key'))
    control_key=signing_bytes(session['control_key'])
    authority=RepositoryAuthority(session['authority_directory'],control_key)
    packet=execute_reviewed(session['host'],private_json(session['job']),private_json(session['review']),
                            private_json(session['authorities']),authority,control_key,
                            signing_bytes(session['preparation_key']))
    # Never print artifact content, host paths or keys.
    print('Disposable rehearsal verified; '+str(len(packet['payload']['artifact']['changes']))+
          ' template paths prepared. Separate publication review is required.')


if __name__=='__main__':
    try:main()
    except Exception:
        print('Rehearsal stopped; preserve the saved plan and recovery archive. No PR published.')
        raise SystemExit(1)
