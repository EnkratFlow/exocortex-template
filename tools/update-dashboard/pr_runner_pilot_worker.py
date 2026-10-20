"""Outbound-only, bounded UAT bridge for one pre-provisioned runner job.

The dashboard cannot supply a command, key path or prepared artifact. The host
administrator pins one existing signed job and one origin in a private config.
Sites service access is supplied through stdin and held only in memory; it is
not an end-user identity or publication grant. This is a session worker, not a
permanent daemon or OS isolation boundary.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import time
from urllib.request import Request, build_opener
from urllib.error import HTTPError

import pr_runner as runner
from pr_runner_authority import RepositoryAuthority, private_json
from pr_runner_credentials import InstallationCredentials, PrivateKeySigner
from pr_runner_github import GitHubBackend
from pr_runner_transport import GitHubTransport, NoRedirect


def private_key(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    meta = os.fstat(fd)
    if (not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or
            meta.st_uid != os.getuid() or meta.st_mode & 0o077):
        os.close(fd)
        raise runner.Blocked('unsafe_worker_file')
    return fd


def signing_bytes(path):
    fd = private_key(path)
    try:
        data = os.read(fd, 33)
        if len(data) != 32:
            raise runner.Blocked('unsafe_worker_file')
        return data
    finally:
        os.close(fd)


def request_signature(path, data):
    fd = private_key(path)
    try:
        result = subprocess.run(
            ['/usr/bin/openssl', 'dgst', '-sha256', '-sign', '/dev/fd/'+str(fd), '-passin', 'pass:'],
            input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            pass_fds=(fd,), timeout=10,
            env={'PATH':'/usr/bin:/bin', 'OPENSSL_CONF':os.devnull, 'LC_ALL':'C'})
        if result.returncode or not 256 <= len(result.stdout) <= 1024:
            raise runner.Blocked('worker_signing_failed')
        return base64.urlsafe_b64encode(result.stdout).rstrip(b'=').decode()
    finally:
        os.close(fd)


class SiteClient:
    def __init__(self, origin, service_token, key, opener=None, lane="pilot"):
        from urllib.parse import urlsplit
        url = urlsplit(origin)
        if (url.scheme != 'https' or not url.hostname or url.username or url.password or
                url.port or url.path or url.query or url.fragment):
            raise runner.Blocked('invalid_site_origin')
        if not isinstance(service_token, str) or not 1 <= len(service_token) <= 8192 or any(c.isspace() for c in service_token):
            raise runner.Blocked('invalid_service_access')
        if lane not in ("pilot", "preparation", "rehearsal"):
            raise runner.Blocked("invalid_worker_lane")
        self.prefix = "/api/update-worker/" if lane == "pilot" else "/api/"+lane+"-worker/"
        self.origin, self.token, self.key = origin, service_token, Path(key)
        self.opener = opener or build_opener(NoRedirect())

    def __call__(self, operation, body):
        if operation not in ('poll','check','result'):
            raise runner.Blocked('invalid_worker_operation')
        path=self.prefix+operation
        raw=runner.canonical(body)
        if len(raw)>(320000 if self.prefix=="/api/preparation-worker/" else 4096): raise runner.Blocked('worker_request_bound')
        stamp=str(int(time.time()));nonce=secrets.token_hex(32)
        message='\n'.join(('POST',self.origin,path,stamp,nonce,hashlib.sha256(raw).hexdigest())).encode()
        req=Request(self.origin+path,data=raw,method='POST',headers={
            'Content-Type':'application/json','OAI-Sites-Authorization':'Bearer '+self.token,
            'X-Runner-Time':stamp,'X-Runner-Nonce':nonce,
            'X-Runner-Signature':request_signature(self.key,message)})
        try:
            with self.opener.open(req,timeout=30) as response:
                raw=response.read(65537)
                if response.status!=200 or len(raw)>65536: raise ValueError()
                return json.loads(raw)
        except HTTPError as exc:
            if operation=='result' and exc.code==409:
                raise runner.Blocked('worker_report_conflict') from None
            raise runner.Blocked('site_unavailable') from None
        except Exception:
            # Never echo headers, credential-bearing Request reprs or response bodies.
            raise runner.Blocked('site_unavailable') from None


def binding(config, job):
    return dict(repository_id=job['repository_id'], repository=job['repository'],
                branch=job['base_branch'], base=job['base_sha'], release=job['release']['tag'],
                github_id=config['github_id'], job_id=runner.digest(job), artifact=job['artifact_sha256'])


def process(config, claim, site, broker):
    prepared=private_json(Path(config['runtime'])/'prepared.json',12*1024*1024)
    prep_key=signing_bytes(config['preparation_key']);grant_key=signing_bytes(config['publication_key'])
    payload=runner.verify(prepared,'prepared-update',prep_key);job=payload['job']
    runner.validate_artifact(payload['artifact'],job)
    if claim.get('configuration')!=binding(config,job): raise runner.Blocked('pilot_binding_mismatch')
    jid=runner.digest(job)
    check_body={'id':claim['id'],'lease':claim['lease']}
    def gate():
        if claim.get('reconcile_only') or site('check',check_body).get('allowed') is not True:
            raise runner.Blocked('grant_revoked')
    authority=RepositoryAuthority(Path(config['runtime'])/'authority',grant_key)
    class CurrentAuthority:
        def __call__(self,j,a):
            gate();answer=authority(j,a);gate();return answer
        def recheck(self,j,a):
            gate();return authority.recheck(j,a)
    transport=GitHubTransport(broker)
    backend=GitHubBackend(transport,CurrentAuthority())
    state=runner.Runner(Path(config['runtime'])/'jobs',prep_key,grant_key,backend)
    try:
        state.status(jid,job['account'])
        # A completed job is read-only recovery, even after original grant expiry.
        # Unfinished jobs still require their original unexpired signed authority.
        result=state.run(jid,job['account'],private_json(Path(config['runtime'])/'grant.json'))
        if not result.get('pr'):
            return {'state':'blocked','pr':None,'commit':None,'error':'verification_failed'}
        # Verify the saved result is still this exact draft before displaying it.
        repo=transport('GET','/repositories/'+job['repository_id'])
        base=transport('GET','/repos/'+job['repository']+'/git/ref/heads/'+job['base_branch'])
        number=result['pr'].rsplit('/',1)[1]
        pr=transport('GET','/repos/'+job['repository']+'/pulls/'+number)
        if (str(repo.get('id'))!=job['repository_id'] or repo.get('full_name')!=job['repository'] or
            pr.get('html_url')!=result['pr'] or pr.get('head',{}).get('ref')!='codex/exocortex-update-'+jid or
            pr.get('base',{}).get('ref')!=job['base_branch'] or pr.get('head',{}).get('sha')!=result['commit_sha'] or
            str(pr.get('head',{}).get('repo',{}).get('id'))!=job['repository_id'] or
            str(pr.get('base',{}).get('repo',{}).get('id'))!=job['repository_id']):
            raise runner.Blocked('pilot_result_changed')
        clear=(result['state']=='complete' and base.get('object',{}).get('sha')==job['base_sha'] and pr.get('base',{}).get('sha')==job['base_sha'] and
               pr.get('draft') is True and pr.get('state')=='open' and not pr.get('merged'))
        return {'state':'complete' if clear else 'needs_review','pr':result['pr'],'commit':result['commit_sha'],'error':None}
    finally:
        state.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--duration',type=int,default=7200);args=parser.parse_args()
    if not 60<=args.duration<=14400: raise runner.Blocked('invalid_worker_duration')
    config=private_json(args.config)
    # Disable terminal echo BEFORE announcing readiness or accepting any bytes.
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
        if saved: termios.tcsetattr(sys.stdin.fileno(),termios.TCSANOW,saved)
    if len(incoming)>16384: raise runner.Blocked('invalid_service_access')
    access=json.loads(incoming);site=SiteClient(config['origin'],access['service_token'],config['worker_key'])
    del access,incoming
    payload=runner.verify(private_json(Path(config['runtime'])/'prepared.json',12*1024*1024),
                          'prepared-update',signing_bytes(config['preparation_key']))
    job=payload['job']
    broker=InstallationCredentials(PrivateKeySigner(config['app_key'],config['app_id']),
        app_id=config['app_id'],installation_id=job['installation'],account_id=config['account_id'],
        repository_id=job['repository_id'],repository=job['repository'])
    deadline=time.monotonic()+args.duration
    pending=None
    connected=False
    print('Pilot worker active; outbound polling only.',flush=True)
    try:
        while time.monotonic()<deadline:
            try:
                # Retain the broker and any pending report until revocation has
                # succeeded. A failed cleanup never permits another poll/mint.
                broker.revoke()
                if pending:
                    site('result',pending);pending=None
                    print('Pilot result recorded.',flush=True)
                claim=site('poll',{}).get('job')
                if not connected:
                    print('Pilot service connection verified.',flush=True);connected=True
                if claim:
                    print('Pilot request received.',flush=True)
                    try: result=process(config,claim,site,broker)
                    except Exception: result={'state':'blocked','pr':None,'commit':None,'error':'runner_unavailable'}
                    pending={'id':claim['id'],'lease':claim['lease'],'result':result}
                    broker.revoke()
                    site('result',pending);pending=None
                    print('Pilot result recorded: '+result['state'],flush=True)
            except Exception as exc:
                if isinstance(exc,runner.Blocked) and str(exc)=='worker_report_conflict':
                    pending=None  # Reclaim and reconcile this same immutable job.
                print('Pilot polling or cleanup unavailable; retrying without new writes.',flush=True)
                time.sleep(15)
            time.sleep(5)
    finally:
        # Keep pending credentials inaccessible until provider revocation or
        # verified expiry. Do not discard them merely because the session ends.
        while True:
            try: broker.revoke();break
            except Exception:
                print('Waiting for temporary credential cleanup.',flush=True)
                time.sleep(15)
    print('Pilot session ended; no new jobs will be claimed.',flush=True)


if __name__=='__main__':
    try: main()
    except Exception:
        print('Pilot worker stopped safely.',flush=True);sys.exit(1)
