"""Attended read-only bridge from hosted requests to trusted preparation preview.

A host provisions the controller/checkout and pinned job; claims cannot choose
paths, release inputs, commands, keys or authority. No apply/publish path exists.
Use SiteClient(lane='preparation') with hidden-stdin service access. This module
neither discovers credentials nor provisions an isolated host.
"""
import time
import re
from pr_runner import Blocked, digest, validate_job, allowed_path, canonical
from pr_runner_prepare import updater


def configuration(job, github_id):
    return dict(job_id=digest(job), repository_id=job['repository_id'],
                repository=job['repository'], branch=job['base_branch'],
                base=job['base_sha'], release=job['release'],
                github_id=github_id, expires_at=job['expires_at'])


def preparation_result(summary, job):
    """Bounded, data-only review evidence; no host paths or file contents."""
    changes=summary['changed_paths']
    if (not isinstance(changes,list) or len(changes)>1000 or
            any(not allowed_path(p) for p in changes) or changes!=sorted(set(changes)) or
            not isinstance(summary['plan_sha256'],str) or
            not re.fullmatch('[a-f0-9]{64}',summary['plan_sha256'])):
        raise Blocked('preparation_summary_invalid')
    state=summary['state']
    result=dict(state='current' if state=='current' and not changes else
                'review_ready' if state=='ready' and changes else 'blocked',
                changed_files=len(changes),plan_sha256=summary['plan_sha256'],error=None,details=None)
    if result['state']=='blocked':
        result.update(error='verification_failed',changed_files=0)
    else:
        version=summary.get('installed_version')
        if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+',version) or summary.get('protected_data') is not True:
            raise Blocked('preparation_summary_invalid')
        result['details']=dict(repository=job['repository'],base_sha=job['base_sha'],
            installed_version=version,release=job['release']['tag'],changed_paths=changes,
            protected_data='passed')
    if len(canonical(result))>300000:raise Blocked('preparation_summary_invalid')
    return result


class PreparationWorker:
    """One session, one host-pinned job. Coordinator stores the immutable plan.

    A lost response is retried from the pending result, never by repeating a
    completed preview. After a process restart the same claim ID chooses the
    same coordinator plan. The coordinator remains responsible for its own
    filesystem locking and guarded state; hosting must prevent shared writers.
    """
    def __init__(self, controller, job, github_id, site, clock=time.time):
        self.controller, self.job, self.site, self.clock = controller, job, site, clock
        self.config = configuration(job, github_id)
        self.pending = None

    def _gate(self, claim):
        validate_job(self.job, self.clock())
        if (claim.get('configuration') != self.config or
                set(claim) != {'id','lease','configuration','expires_at'} or
                not isinstance(claim['id'],str) or len(claim['id']) != 64 or
                any(c not in '0123456789abcdef' for c in claim['id']) or
                not isinstance(claim['lease'],str) or not 1 <= len(claim['lease']) <= 64 or
                type(claim['expires_at']) is not int or claim['expires_at'] <= self.clock() or
                claim['expires_at'] > self.job['expires_at']):
            raise Blocked('preparation_request_changed')
        if self.site('check', {'id':claim['id'],'lease':claim['lease']}).get('allowed') is not True:
            raise Blocked('preparation_request_changed')
        validate_job(self.job, self.clock())
        if claim['expires_at'] <= self.clock():
            raise Blocked('preparation_request_expired')

    def once(self):
        """Poll/prepare/report once. Exceptions never include provider diagnostics."""
        if self.pending:
            claim, result = self.pending
        else:
            claim = self.site('poll', {}).get('job')
            if claim is None:
                return 'idle'
            self._gate(claim)
            # Keep IDs within the coordinator's bounded identifier grammar.
            try:
                summary = self.controller.preview('prep-'+claim['id'][:32], self.job)
            except (Blocked, updater.UpdateError):
                summary = {'state':'blocked','changed_paths':[],'plan_sha256':'0'*64}
            self._gate(claim)
            result = preparation_result(summary,self.job)
            self.pending = (claim,result)
        # Reporting the same saved result is harmless after a lost response.
        # The hosted endpoint enforces current lease/access before first save and
        # accepts exact terminal-result retries without requiring a running lease.
        try:
            response = self.site('result', {'id':claim['id'],'lease':claim['lease'],'result':result})
        except Blocked as exc:
            if str(exc) == 'worker_report_conflict':
                self.pending = None
            raise
        if response.get('saved') is not True:
            raise Blocked('preparation_result_not_saved')
        self.pending = None
        return result['state']

    def run(self, duration, sleep=time.sleep):
        """An attended maximum-four-hour session; no daemon or automatic renewal."""
        if type(duration) is not int or not 1 <= duration <= 14400:
            raise Blocked('invalid_session_duration')
        end = self.clock()+duration
        while self.clock()<end:
            try:
                self.once()
            except Blocked:
                # Keep a pending result on transport loss. Never log exceptions,
                # create authority, renew jobs, or initiate another operation.
                if self.clock() >= self.job['expires_at']:
                    return 'expired'
            sleep(min(10,max(0,end-self.clock())))
        return 'session_ended'
