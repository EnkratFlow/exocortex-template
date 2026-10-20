"""Attended bridge for exactly one owner-reviewed disposable update plan.

The browser requests a test; a separate signed local review and already issued
installer authority are also required. No key/capability issuance or publication.
"""
import argparse
from pathlib import Path
import time

from pr_runner import Blocked, digest, exact, verify, validate_job
from pr_runner_authority import RepositoryAuthority, private_json
from pr_runner_controller import PreparationController
from pr_runner_pilot_worker import SiteClient, signing_bytes
from pr_runner_preparation_host import read_service_access
from pr_runner_preparation_worker import configuration, preparation_result
from pr_runner_rehearsal_host import execute_reviewed, updater


class RehearsalWorker:
    def __init__(self, host, preview_job, review, authorities, authority, control_key,
                 preparation_key, github_id, site, clock=time.time):
        self.host,self.preview_job,self.review,self.authorities=host,preview_job,review,authorities
        self.authority,self.control_key,self.preparation_key=authority,control_key,preparation_key
        self.site,self.clock=site,clock
        self.approved=verify(review,'rehearsal-review',control_key)
        self.job=self.approved['job']
        validate_job(preview_job,clock());validate_job(self.job,clock())
        if self.job!=dict(preview_job,plan_sha256=self.approved['plan_sha256']):
            raise Blocked('review_job_changed')
        hosted=self.approved.get('hosted_review')
        exact(hosted,('preparation_id','result_sha256'))
        for value in hosted.values():
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise Blocked('invalid_hosted_review')
        if self.approved['plan_id']!='prep-'+hosted['preparation_id'][:32]:
            raise Blocked('review_plan_changed')
        self.config=configuration(preview_job,github_id)
        self.pending=None

    def gate(self,claim):
        validate_job(self.job,self.clock())
        exact(claim,('id','lease','preparation_id','result_sha256','configuration','expires_at'))
        bound=self.approved['hosted_review']
        if (claim['configuration']!=self.config or any(claim[k]!=bound[k] for k in bound) or
                not isinstance(claim['id'],str) or len(claim['id'])!=64 or
                any(c not in '0123456789abcdef' for c in claim['id']) or
                not isinstance(claim['lease'],str) or not 1<=len(claim['lease'])<=64 or
                type(claim['expires_at']) is not int or not self.clock()<claim['expires_at']<=self.job['expires_at']):
            raise Blocked('review_request_changed')
        if self.site('check',{'id':claim['id'],'lease':claim['lease']}).get('allowed') is not True:
            raise Blocked('review_request_changed')
        validate_job(self.job,self.clock())
        if claim['expires_at']<=self.clock():raise Blocked('review_request_expired')

    def once(self):
        if self.pending:
            claim,result=self.pending
        else:
            claim=self.site('poll',self.approved['hosted_review']).get('job')
            if claim is None:return 'idle'
            self.gate(claim)
            # Recompute the display from the actual still-ready plan. Signed
            # review binds both display digest and exact private plan digest.
            plan=updater.load(Path(self.host['controller']),self.approved['plan_id'])
            if (digest(plan)!=self.approved['plan_sha256'] or
                    digest(preparation_result(PreparationController.summary(plan),self.preview_job))!=claim['result_sha256']):
                raise Blocked('review_plan_changed')
            try:
                packet=execute_reviewed(self.host,self.job,self.review,self.authorities,self.authority,
                    self.control_key,self.preparation_key,self.clock,request_gate=lambda:self.gate(claim))
                payload=verify(packet,'prepared-update',self.preparation_key)
                result=dict(state='verified',artifact_sha256=digest(payload['artifact']),
                            changed_files=len(payload['artifact']['changes']),error=None)
            except Exception:
                # After starting, failures may have effects. Never report a
                # harmless cancellation, retry apply, or expose diagnostic data.
                result=dict(state='recovery_required',artifact_sha256=None,changed_files=0,error='review_required')
            self.pending=(claim,result)
        try:
            response=self.site('result',{'id':claim['id'],'lease':claim['lease'],'result':result})
        except Blocked as exc:
            if str(exc)=='worker_report_conflict':self.pending=None
            raise
        if response.get('saved') is not True:raise Blocked('review_result_not_saved')
        self.pending=None
        return result['state']

    def run(self,duration,sleep=time.sleep):
        if type(duration) is not int or not 1<=duration<=14400:raise Blocked('invalid_session_duration')
        end=self.clock()+duration
        while self.clock()<end:
            try:
                result=self.once()
                if result!='idle':return result
            except Blocked:
                if self.clock()>=self.job['expires_at']:return 'expired'
            sleep(min(10,max(0,end-self.clock())))
        return 'session_ended'


def main():
    parser=argparse.ArgumentParser(description='Attend one reviewed disposable test; no GitHub publication.')
    parser.add_argument('--config',required=True);parser.add_argument('--duration',type=int,default=900)
    args=parser.parse_args()
    if not 1<=args.duration<=14400:raise Blocked('invalid_session_duration')
    s=private_json(args.config)
    exact(s,('host','preview_job','review','authorities','authority_directory','control_key',
             'preparation_key','github_id','worker_key','origin'))
    key=signing_bytes(s['control_key'])
    worker=RehearsalWorker(s['host'],private_json(s['preview_job']),private_json(s['review']),
        private_json(s['authorities']),RepositoryAuthority(s['authority_directory'],key),key,
        signing_bytes(s['preparation_key']),s['github_id'],
        SiteClient(s['origin'],read_service_access(),s['worker_key'],lane='rehearsal'))
    print('Reviewed test host active; disposable checkout only.',flush=True)
    print('Reviewed test host stopped: '+worker.run(args.duration),flush=True)


if __name__=='__main__':
    try:main()
    except Exception:
        print('Reviewed test stopped. Preserve the saved plan and recovery evidence.',flush=True)
        raise SystemExit(1)
