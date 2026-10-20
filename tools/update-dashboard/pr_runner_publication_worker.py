"""Publish one tested artifact after a separate owner review and local grant.

All files are host-provisioned. The dashboard supplies only an exact claim;
it cannot issue grants, choose paths, supply artifact contents or run commands.
"""
import argparse
from pathlib import Path
import time

from pr_runner import Blocked, DIGEST, digest, exact, token, verify, validate_job, validate_artifact
from pr_runner_authority import private_json
from pr_runner_credentials import InstallationCredentials, PrivateKeySigner
from pr_runner_pilot_worker import SiteClient, signing_bytes, process
from pr_runner_preparation_host import read_service_access
from pr_runner_preparation_worker import configuration


def handoff(saved, review, preview_job, result, control_key, preparation_key, github_id, now):
    """Validate the private rehearsal wrapper and return a data-only binding.

    No signatures or capabilities are issued. Exact template paths must match
    what the owner reviewed before rehearsal; post-apply digests may evolve.
    """
    exact(saved,('review_sha256','packet'))
    approved=verify(review,'rehearsal-review',control_key)
    exact(approved,('job','host_sha256','plan_id','plan_sha256','target_id','authorities_sha256','hosted_review'))
    hosted=approved['hosted_review'];exact(hosted,('preparation_id','result_sha256'))
    for value in hosted.values():token(value,DIGEST.pattern,'invalid_hosted_review')
    payload=verify(saved['packet'],'prepared-update',preparation_key)
    exact(payload,('job','artifact'))
    job=payload['job'];validate_job(preview_job,now);validate_job(job,now)
    validate_artifact(payload['artifact'],job)
    exact(result,('state','changed_files','plan_sha256','error','details'))
    d=result['details'];exact(d,('repository','base_sha','installed_version','release','changed_paths','protected_data'))
    token(d['installed_version'],r'[0-9]+\.[0-9]+\.[0-9]+','invalid_installed_version')
    if (saved['review_sha256']!=digest(review) or approved['plan_id']!='prep-'+hosted['preparation_id'][:32]
            or approved['job']!=dict(preview_job,plan_sha256=approved['plan_sha256'])
            or job!=dict(approved['job'],plan_sha256=job['plan_sha256'],artifact_sha256=job['artifact_sha256'])
            or result['plan_sha256']!=approved['plan_sha256'] or digest(result)!=hosted['result_sha256']
            or result['state']!='review_ready' or result['error'] is not None
            or type(result['changed_files']) is not int or result['changed_files']!=len(payload['artifact']['changes'])
            or d['changed_paths']!=[r['path'] for r in payload['artifact']['changes']]
            or d['repository']!=job['repository'] or d['base_sha']!=job['base_sha']
            or d['release']!=job['release']['tag'] or d['protected_data']!='passed'):
        raise Blocked('publication_handoff_changed')
    return dict(**hosted,artifact_sha256=job['artifact_sha256'],job_id=digest(job),
                preparation=configuration(preview_job,github_id))


class PublicationWorker:
    def __init__(self,config,site,broker,clock=time.time):
        self.config,self.site,self.broker,self.clock=config,site,broker,clock
        self.pending=None

    def load(self):
        c=self.config
        saved=private_json(c['saved'],12*1024*1024)
        binding=handoff(saved,private_json(c['review']),private_json(c['preview_job']),
            private_json(c['result'],320000),signing_bytes(c['control_key']),
            signing_bytes(c['preparation_key']),c['github_id'],self.clock())
        return saved['packet'],binding

    def once(self):
        # Never mint another credential while cleanup of a previous one is pending.
        self.broker.revoke()
        if self.pending:
            claim,result=self.pending
        else:
            prepared,binding=self.load()
            claim=self.site('poll',binding).get('job')
            if claim is None:return 'idle'
            exact(claim,('id','lease','configuration','expires_at'))
            token(claim['id'],DIGEST.pattern,'invalid_claim')
            token(claim['lease'],r'[A-Za-z0-9-]{1,64}','invalid_claim')
            if (claim['configuration']!=binding or type(claim['expires_at']) is not int
                    or not self.clock()<claim['expires_at']<=binding['preparation']['expires_at']):
                raise Blocked('publication_claim_changed')
            def site(op,body):
                if op=='check':
                    _,current=self.load()
                    if current!=binding or self.clock()>=claim['expires_at']:
                        raise Blocked('publication_claim_changed')
                response=self.site(op,body)
                if op=='check' and self.clock()>=claim['expires_at']:
                    raise Blocked('publication_claim_changed')
                return response
            try:
                result=process(self.config,claim,site,self.broker,prepared=prepared,expected_configuration=binding)
                if result['state']=='blocked':
                    result=dict(state='recovery_required',pr=None,commit=None,error='verification_failed')
            except Exception:
                result=dict(state='recovery_required',pr=None,commit=None,error='verification_failed')
            # Save before cleanup/report: neither failure permits another publish.
            self.pending=(claim,result)
            self.broker.revoke()
        response=self.site('result',{'id':claim['id'],'lease':claim['lease'],'result':result})
        if response.get('saved') is not True:raise Blocked('publication_result_not_saved')
        self.pending=None
        return result['state']

    def run(self,duration,sleep=time.sleep):
        if type(duration) is not int or not 1<=duration<=14400:raise Blocked('invalid_session_duration')
        end=self.clock()+duration
        try:
            while self.clock()<end:
                try:
                    result=self.once()
                    if result!='idle':return result
                except Blocked as exc:
                    if str(exc)=='worker_report_conflict':return 'recovery_required'
                sleep(min(10,max(0,end-self.clock())))
            return 'session_ended'
        finally:
            # Same cleanup guarantee as the original pilot; no token discarded.
            while True:
                try:self.broker.revoke();break
                except Exception:sleep(15)


def main():
    parser=argparse.ArgumentParser(description='Attend one reviewed draft PR; no merge or deployment.')
    parser.add_argument('--config',required=True);parser.add_argument('--duration',type=int,default=900)
    args=parser.parse_args();c=private_json(args.config)
    exact(c,('saved','review','preview_job','result','control_key','preparation_key','publication_key',
             'runtime','github_id','worker_key','origin','app_key','app_id','account_id'))
    # Validate the handoff before enabling the credential broker or polling.
    worker=PublicationWorker(c,None,None);packet,_=worker.load();job=packet['payload']['job']
    worker.broker=InstallationCredentials(PrivateKeySigner(c['app_key'],c['app_id']),
        app_id=c['app_id'],installation_id=job['installation'],account_id=c['account_id'],
        repository_id=job['repository_id'],repository=job['repository'])
    worker.site=SiteClient(c['origin'],read_service_access(),c['worker_key'],lane='publication')
    print('Draft PR host active; one exact reviewed artifact only.',flush=True)
    print('Draft PR host stopped: '+worker.run(args.duration),flush=True)


if __name__=='__main__':
    try:main()
    except Exception:
        print('Publication stopped. Preserve the request and runner recovery state.',flush=True)
        raise SystemExit(1)
