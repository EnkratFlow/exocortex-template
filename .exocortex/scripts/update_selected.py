#!/usr/bin/env python3
"""Explicit selected-project updates through the existing guarded updater.

Plans and receipts are machine-local. Discovery, selection, preview, authority,
apply and verified delivery are separate; this module never creates authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
import project_state as state
import release_awareness as local
import prepare_update_reconciliation as reconciliation

BASE = '.exocortex/local/update-plans'
SHA = re.compile(r'[0-9a-f]{64}\Z')
ID = re.compile(r'[a-z][a-z0-9-]{0,63}\Z')
AUTH = {'capability', 'work_item_id', 'work_item_revision', 'request_id', 'surface_id', 'executor_id', 'adapter_version'}


class UpdateError(ValueError): pass


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value): raise UpdateError('Invalid plan or target ID')
    return value


def sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value): raise UpdateError('Expected an exact SHA-256 digest')
    return value


def digest(data): return hashlib.sha256(data).hexdigest()


def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def file_bytes(path, limit=16*1024*1024):
    path=local.safe(path)
    if not path.is_file(): raise UpdateError('Required regular file unavailable')
    with path.open('rb') as f: data=f.read(limit+1)
    if len(data)>limit: raise UpdateError('File exceeds inspection bound')
    return data


def machine(): return state.opaque(state.machine_name()+'\n'+str(Path.home()))


def independent(a,b): return a!=b and a not in b.parents and b not in a.parents


def absolute(path):
    p=Path(path).absolute()
    local.safe(p)
    return p


PUBLIC_TEMPLATE_FILES = {'.exocortex/.env.example', '.exocortex/key-registry.json'}


def public_template_digest(path, relative):
    """Allow only unchanged, declared public examples; never return their content.

    A consumer may have put private values in these otherwise public paths.
    Hash them without decoding or logging. Any byte difference blocks the
    coordinator before the updater or backup code can inspect them.
    """
    package = Path(__file__).resolve().parents[2]
    hashes = {}
    for line in file_bytes(package/'SHA256SUMS').decode('utf-8').splitlines():
        fields = line.split('  ', 1)
        if len(fields) == 2 and fields[1] in PUBLIC_TEMPLATE_FILES:
            if fields[1] in hashes:
                raise UpdateError('Duplicate public-template manifest entry')
            hashes[fields[1]] = sha(fields[0])
    expected = hashes.get(relative)
    if expected is None:
        raise UpdateError('Public-template example is not declared')
    # The generic state-path guard intentionally rejects .env names. This exact
    # public example exception still checks every parent and rejects links or
    # Windows reparse points before hashing any bytes.
    local.safe(path.parent)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_size > 1024*1024:
        raise UpdateError('Public-template example requires separate review')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        remaining = 1024*1024 + 1
        while remaining:
            chunk = stream.read(min(65536, remaining))
            if not chunk: break
            remaining -= len(chunk); h.update(chunk)
    if remaining == 0 or h.hexdigest() != expected:
        raise UpdateError('Modified public-template example requires separate review; updater not invoked: '+relative)
    return expected


def managed_snapshot(root):
    """Hash the bounded code plane, including additions; never inspect data plane."""
    manifest=file_bytes(root/'.exocortex/.install-manifest')
    declared={'.exocortex/.install-manifest','.exocortex/.version',*reconciliation.SURFACE_PATHS}
    for row in manifest.decode('utf-8').splitlines():
        if not row.strip() or row.startswith('#'):continue
        fields=row.split()
        if len(fields)!=2: raise UpdateError('Installed manifest is malformed')
        rel=fields[0]
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts or '\\' in rel: raise UpdateError('Unsafe installed manifest')
        declared.add(rel)
    result={};total=0;visited=0
    pending=[root/rel for rel in reconciliation.SURFACE_PATHS]
    while pending:
        p=pending.pop();rel=p.relative_to(root).as_posix()
        if reconciliation.is_protected_path(rel) or reconciliation.is_runtime_state(rel):continue
        name=p.name.casefold()
        if rel in PUBLIC_TEMPLATE_FILES and p.exists():
            if rel not in declared:
                raise UpdateError('Undeclared public-template example; updater not invoked')
            result[rel]={'sha256':public_template_digest(p,rel),'mode':stat.S_IMODE(p.stat().st_mode)}
            continue
        # Only names also excluded by the low-level updater may be skipped.
        # Other credential-shaped files block before that updater can inspect or
        # archive them. An environment example in a consumer is not presumed safe.
        if p.name in ('.env','.envrc') or (p.name.startswith('.env.') and p.name!='.env.example'):continue
        if name.startswith('.env') or name in ('credentials','secrets','key-registry.json','__pycache__') or name.endswith(('.pem','.key','.p12','.pyc')):
            raise UpdateError('Credential-shaped or opaque runtime path requires separate review; updater not invoked: '+rel)
        local.safe(p);visited+=1
        if visited>4000:raise UpdateError('Managed code exceeds inspection bound')
        if not p.exists():continue
        if p.is_dir():
            pending.extend(p.iterdir());continue
        if p.name.casefold() in ('settings.local.json','secrets.json','tokens.json','token.json','credentials.json') or rel not in declared:
            raise UpdateError('Unclassified local code-plane file; review without opening: '+rel)
        raw=file_bytes(p);total+=len(raw)
        if total>64*1024*1024:raise UpdateError('Managed code exceeds inspection bound')
        result[rel]={'sha256':digest(raw),'mode':stat.S_IMODE(p.stat().st_mode)}
    return digest(canonical(result))


def target(root):
    root=absolute(root)
    info=state.repository(root)
    if Path(info['root'])!=root: raise UpdateError('Select an exact repository root')
    version,present=state.local_version(root)
    if not present or version is None: raise UpdateError('Installed Exocortex version unavailable')
    return {'path':str(root),'project_id':info['project_id'],'common_dir':info['common_dir'],
            'binding':state.context_binding(root),'version':version,'managed_sha256':managed_snapshot(root)}


def plan_path(root,pid): return local.safe(Path(root)/BASE/(identifier(pid)+'.json'))


def load(root,pid):
    p=local.load(plan_path(root,pid))
    if (not isinstance(p,dict) or p.get('schema')!=1 or p.get('id')!=pid or p.get('machine')!=machine() or
            not isinstance(p.get('targets'),list) or not 1<=len(p['targets'])<=20):
        raise UpdateError('Plan is invalid or belongs to another machine')
    if type(p.get('revision')) is not int or p['revision']<1:raise UpdateError('Invalid plan revision')
    source=p.get('source')
    if not isinstance(source,dict) or set(source)!={'path','manifest_sha256','release'}:raise UpdateError('Invalid source pin')
    src=absolute(source['path']);sha(source['manifest_sha256']);backup=absolute(p['backup_root'])
    if source['release'] is not None:validate_release(source['release'])
    if not independent(src,backup):raise UpdateError('Overlapping source and backups')
    seen=[]
    for n,row in enumerate(p['targets'],1):
        if not isinstance(row,dict) or row.get('id')!=f'target-{n}' or row.get('selected') is not True:raise UpdateError('Invalid target selection')
        path=absolute(row['path'])
        if not independent(path,src) or not independent(path,backup) or any(not independent(path,x) for x in seen):raise UpdateError('Overlapping targets')
        seen.append(path)
        if row.get('state') not in ('not_attempted','blocked','ready','current','applying','recovery_required','verification_failed','applied','restored'):raise UpdateError('Invalid target state')
        if row.get('initial') is None and row['state']!='blocked':raise UpdateError('Missing target identity')
        if row.get('initial') is not None and row['initial'].get('path')!=str(path):raise UpdateError('Target identity mismatch')
    return p


def view(p): return dict(p,plan_sha256=digest(canonical(p)))


def expect(p,expected):
    if sha(expected)!=digest(canonical(p)): raise UpdateError('Plan changed; review its current revision')


def create(root,pid,template,candidate_digest,backup_root,targets,account_scope,release=None):
    identifier(pid);sha(candidate_digest)
    source=absolute(template);backup=absolute(backup_root)
    if not source.is_dir() or not independent(source,backup): raise UpdateError('Source and backup root must be separate')
    if not isinstance(account_scope,str) or not 1<=len(account_scope.strip())<=100: raise UpdateError('Name the explicit account/selection scope')
    if not 1<=len(targets)<=20: raise UpdateError('Select 1 to 20 exact targets')
    rows=[];seen=set()
    for n,path in enumerate(targets,1):
        p=absolute(path)
        if not independent(p,source) or not independent(p,backup): raise UpdateError('Targets, source and backups must be separate')
        if str(p) in seen or any(not independent(p,Path(x)) for x in seen): raise UpdateError('Duplicate or nested targets')
        seen.add(str(p))
        try: facts=target(p);reason=None
        except (UpdateError,state.Unavailable,local.ReleaseError,OSError,UnicodeError):
            facts=None;reason='Target unavailable, not a Git root, or installed version/manifest unsupported'
        rows.append({'id':f'target-{n}','path':str(p),'selected':True,'initial':facts,'state':'not_attempted' if facts else 'blocked','reason':reason,'receipt':None})
    families={r['initial']['common_dir'] for r in rows if r['initial']}
    for family in families:
        group=[r for r in rows if r['initial'] and r['initial']['common_dir']==family]
        if len(group)>1:
            for r in group:r.update(state='blocked',reason='Select only one working folder per Git family in a plan')
    p={'schema':1,'id':pid,'machine':machine(),'revision':1,'account_scope':account_scope.strip(),
       'source':{'path':str(source),'manifest_sha256':candidate_digest,'release':release},'backup_root':str(backup),'targets':rows}
    if digest(file_bytes(source/'SHA256SUMS'))!=candidate_digest: raise UpdateError('Candidate manifest differs from selected digest')
    if release is not None: validate_release(release)
    with local.lock(plan_path(root,pid).with_suffix('.lock')):
        if plan_path(root,pid).exists(): raise UpdateError('Plan already exists; selection is immutable')
        local.write(plan_path(root,pid),p)
    return view(p)


def validate_release(r):
    if not isinstance(r,dict) or set(r)!={'repository','tag','commit','asset'}: raise UpdateError('Incomplete release pin')
    try:local.repository(r['repository'])
    except local.ReleaseError:raise UpdateError('Invalid release repository') from None
    if not isinstance(r['tag'],str) or not re.fullmatch(r'v?(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})\.(?:0|[1-9][0-9]{0,8})',r['tag']): raise UpdateError('Select an exact stable tag')
    if not isinstance(r['commit'],str) or not re.fullmatch('[0-9a-f]{40}',r['commit']): raise UpdateError('Select the exact release commit')
    asset=absolute(r['asset'])
    if asset.name!='SHA256SUMS': raise UpdateError('Retain the verified SHA256SUMS asset')


def checked(args,cwd=None):
    try:
        p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=45)
        if p.returncode: raise UpdateError('Release verification failed; candidate not executed')
        return p.stdout
    except (OSError,subprocess.SubprocessError): raise UpdateError('Release verification unavailable; candidate not executed') from None


def verify_source(source,apply=False):
    root=absolute(source['path']);manifest=file_bytes(root/'SHA256SUMS');sha(source['manifest_sha256'])
    if digest(manifest)!=source['manifest_sha256']: raise UpdateError('Candidate manifest changed')
    r=source['release']
    if apply and r is None: raise UpdateError('Local candidate preview cannot authorize a live update')
    if r is not None:
        validate_release(r);repo='github.com/'+local.repository(r['repository'])
        # Live revocation/attestation checks immediately precede candidate code.
        checked(['gh','release','verify',r['tag'],'-R',repo])
        checked(['gh','release','verify-asset',r['tag'],r['asset'],'-R',repo])
        if file_bytes(Path(r['asset']))!=manifest: raise UpdateError('Attested asset differs from candidate manifest')
        if state.git(root,'rev-parse','HEAD')!=r['commit'] or state.git(root,'rev-parse',r['tag']+'^{commit}')!=r['commit']:
            raise UpdateError('Candidate is not the exact release commit/tag')
        if state.remote_identity(state.git(root,'remote','get-url','origin'))!=repo:
            raise UpdateError('Candidate repository differs from release identity')
        if checked(['git','-C',str(root),'show',r['commit']+':SHA256SUMS'])!=manifest:
            raise UpdateError('Release commit manifest differs from attested asset')
    # Before any candidate script executes, authenticate its bytes. The updater
    # itself validates the remaining code plane, file modes and protected paths.
    hashes={}
    for line in manifest.decode('utf-8').splitlines():
        m=re.fullmatch(r'([0-9a-f]{64})  ([^/].*)',line)
        if not m or m[2] in hashes: raise UpdateError('Malformed candidate manifest')
        hashes[m[2]]=m[1]
    for rel in ('scripts/safe-update.sh','scripts/windows.ps1'):
        if rel not in hashes or digest(file_bytes(root/rel))!=hashes[rel]: raise UpdateError('Updater entrypoint differs from selected release')
    return root


def receipt(output,backup_root,applied=False,request_id=None):
    lines=output.splitlines()
    def only(prefix):
        rows=[x[len(prefix):] for x in lines if x.startswith(prefix)]
        if len(rows)!=1: raise UpdateError('Updater result is incomplete or ambiguous')
        return rows[0]
    archive=absolute(only('Backup: '));backup=absolute(backup_root)
    if backup not in archive.parents: raise UpdateError('Recovery archive is outside the selected backup root')
    h=hashlib.sha256();total=0
    with local.safe(archive).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            total+=len(block)
            if total>512*1024*1024: raise UpdateError('Recovery archive exceeds inspection bound')
            h.update(block)
    count=int(only('Rehearsal changed paths: '));expected=sha(only('Rehearsal changed paths SHA-256: '))
    if not 0<=count<=10000: raise UpdateError('Invalid effect count')
    start=lines.index('Rehearsal changed paths: '+str(count))+1;paths=lines[start:start+count]
    if len(paths)!=count or paths!=sorted(set(paths)) or digest(''.join(x+'\n' for x in paths).encode())!=expected:
        raise UpdateError('Updater effect list differs from its digest')
    for rel in paths:
        if Path(rel).is_absolute() or '..' in Path(rel).parts: raise UpdateError('Unsafe effect path')
    if 'Protected data check: PASS' not in lines: raise UpdateError('Protected data verification missing')
    if applied:
        if request_id is None or 'Update applied under consumed capability: '+request_id not in lines:
            raise UpdateError('Apply completion not confirmed')
    elif 'Dry run complete. Real target unchanged.' not in lines: raise UpdateError('Preview completion not confirmed')
    return {'archive':str(archive),'archive_sha256':h.hexdigest(),'changed_paths':paths,'changed_paths_sha256':expected,
            'reconciliation_required':any(x.startswith('EXOCORTEX_COMMAND_RECONCILIATION_REQUIRED:') for x in lines)}


def validate_authority(a):
    if not isinstance(a,dict) or set(a)!=AUTH: raise UpdateError('Supply exact existing per-target authority references')
    if type(a['work_item_revision']) is not int or a['work_item_revision']<0: raise UpdateError('Invalid work item revision')
    for k in AUTH-{'work_item_revision','capability'}:
        if not isinstance(a[k],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',a[k]): raise UpdateError('Invalid authority reference')
    cap=a['capability']
    if not isinstance(cap,str) or not re.fullmatch(r'\.exocortex/local/protocol/capabilities/[A-Za-z0-9_.-]+\.json',cap): raise UpdateError('Capability must be an exact project-local reference')


def launch_command(temp,args,windows=False):
    if windows:
        pwsh=shutil.which('pwsh') or shutil.which('powershell.exe')
        if not pwsh:raise UpdateError('PowerShell/Git for Windows launcher unavailable')
        return [pwsh,'-NoProfile','-File',str(temp/'scripts/windows.ps1'),'update',*args]
    return ['bash','--noprofile','--norc',str(temp/'scripts/safe-update.sh'),*args]


def invoke(source,row,backup,authority=None):
    root=Path(source['path']);args=['--template',str(root),'--candidate-digest',source['manifest_sha256'],'--backup-dir',str(backup)]
    if authority:
        validate_authority(authority);args+=['--apply']
        for key,value in sorted(authority.items()):args+=['--'+key.replace('_','-'),str(value)]
    else:args+=['--dry-run']
    with tempfile.TemporaryDirectory(prefix='exocortex-selected-run-') as tmp:
        temp=Path(tmp).resolve();(temp/'home').mkdir();(temp/'tmp').mkdir()
        # Execute private copies of the authenticated bytes, never mutable source
        # entrypoints. The launcher still passes the explicitly pinned source to
        # safe-update, which authenticates and snapshots its remaining code plane.
        manifest=file_bytes(root/'SHA256SUMS')
        if digest(manifest)!=source['manifest_sha256']:raise UpdateError('Candidate manifest changed before launch')
        hashes=dict((line.split('  ',1)[1],line.split('  ',1)[0]) for line in manifest.decode().splitlines())
        (temp/'scripts').mkdir();(temp/'SHA256SUMS').write_bytes(manifest)
        for rel in ('scripts/safe-update.sh','scripts/windows.ps1'):
            data=file_bytes(root/rel)
            if digest(data)!=hashes.get(rel):raise UpdateError('Candidate launcher changed before execution')
            (temp/rel).write_bytes(data)
        # On Windows the wrapper derives the same digest from the staged
        # manifest; trailing explicit source overrides its private directory.
        command=launch_command(temp,args,windows=os.name=='nt')
        env={k:os.environ[k] for k in ('PATH','SystemRoot','WINDIR','COMSPEC','PATHEXT') if k in os.environ}
        env.update(HOME=str(temp/'home'),TMPDIR=str(temp/'tmp'),TMP=str(temp/'tmp'),TEMP=str(temp/'tmp'),LC_ALL='C',LANG='C',PYTHONDONTWRITEBYTECODE='1')
        options={'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP} if os.name=='nt' else {'start_new_session':True}
        with (temp/'output').open('wb') as log:
            p=subprocess.Popen(command,cwd=row['path'],env=env,stdout=log,stderr=subprocess.STDOUT,**options)
            try:p.wait(timeout=240)
            except subprocess.TimeoutExpired:
                if os.name=='nt':subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True,timeout=15)
                else:os.killpg(p.pid,signal.SIGKILL)
                p.wait(timeout=15)
                raise UpdateError('Updater timed out; reconcile target and recovery evidence before retrying')
        output=file_bytes(temp/'output',8*1024*1024).decode('utf-8',errors='replace')
        return p.returncode,output


def family_path(facts,lock_root):
    return absolute(lock_root)/(state.opaque(facts['common_dir'])+'.json')


def execute(root,pid,expected,action,authorities=None,lock_root=None):
    if action not in ('preview','apply'): raise UpdateError('Unsupported plan operation')
    authorities=authorities or {};lock_root=lock_root or local.default_cache().parent/'update-locks'
    with local.lock(plan_path(root,pid).with_suffix('.lock')):
        p=load(root,pid);expect(p,expected)
        known={r['id'] for r in p['targets']}
        if not isinstance(authorities,dict) or set(authorities)-known: raise UpdateError('Authority references include unselected targets')
        for a in authorities.values():validate_authority(a)
        if action=='apply' and not authorities: raise UpdateError('No target-specific authority supplied')
        for row in p['targets']:
            if action=='apply' and row['id'] not in authorities:continue
            if row['state'] in ('blocked','current','applying','recovery_required','verification_failed','applied','restored'):continue
            if action=='apply' and row['state']!='ready':continue
            before=None;backup=Path(p['backup_root'])/pid/row['id'];marker=None
            try:
                before=target(row['path'])
                if before!=row['initial']:raise UpdateError('Target identity, HEAD or installed code changed since selection')
                marker=family_path(before,lock_root)
                with local.lock(marker.with_suffix('.lock')):
                    recovery=local.load(marker)
                    if recovery and not recovery.get('resolved'):raise UpdateError('This Git family requires recovery before another update')
                    verify_source(p['source'],apply=action=='apply')
                    code,output=invoke(p['source'],row,backup)
                    log=plan_path(root,pid).parent/pid/(row['id']+'-preview-'+str(p['revision'])+'.json')
                    local.write(log,{'exit_code':code,'output':output[-200000:]})
                    row['diagnostic_record']=str(log)
                    if code:raise UpdateError('Updater preview blocked; preserve target and inspect its prerequisites/customizations')
                    fresh=receipt(output,backup)
                    row['receipt']=dict(fresh,before=before)
                    if fresh['reconciliation_required']:raise UpdateError('Exact command reconciliation required; ordinary apply is blocked')
                    if action=='preview':row.update(state='ready' if fresh['changed_paths'] else 'current',reason=None)
                    else:
                        old_paths=row.get('approved_effect')
                        if old_paths!=fresh['changed_paths_sha256']:raise UpdateError('Rehearsed effect changed; review a new preview')
                        if target(row['path'])!=before:raise UpdateError('Target changed during preview')
                        # Persistent marker survives process crashes and blocks other plans.
                        local.write(marker,{'plan':pid,'target':row['id'],'before':before,'resolved':False,'archive':fresh['archive'],'archive_sha256':fresh['archive_sha256']})
                        row.update(state='applying',reason='Updater outcome pending');p['revision']+=1;local.write(plan_path(root,pid),p)
                        verify_source(p['source'],apply=True)
                        code,output=invoke(p['source'],row,backup,authorities[row['id']])
                        log=plan_path(root,pid).parent/pid/(row['id']+'-apply-'+str(p['revision'])+'.json')
                        local.write(log,{'exit_code':code,'output':output[-200000:]})
                        row['diagnostic_record']=str(log)
                        if code:raise UpdateError('Apply did not complete; recovery review and fresh authority required')
                        applied=receipt(output,backup,applied=True,request_id=authorities[row['id']]['request_id']);row['receipt'].update(apply=applied)
                        row['state']='verification_failed'
                        verify_source(p['source'],apply=True)
                        code,output=invoke(p['source'],row,backup)
                        verified=receipt(output,backup) if code==0 else None
                        if not verified or verified['changed_paths'] or verified['reconciliation_required']:
                            raise UpdateError('Post-apply zero-change verification failed; preserve recovery evidence')
                        row['receipt']['verification']=verified
                        row.update(state='applied',reason='Guarded apply and zero-change verification passed; not committed or deployed')
                        local.write(marker,{'plan':pid,'target':row['id'],'resolved':True,'outcome':'applied'})
                    row['approved_effect']=fresh['changed_paths_sha256']
            except (UpdateError,local.ReleaseError,state.Unavailable,OSError,ValueError,subprocess.SubprocessError) as exc:
                if row['state']=='applying':row['state']='recovery_required'
                elif row['state']!='verification_failed':row['state']='blocked'
                row['reason']=str(exc) if isinstance(exc,(UpdateError,local.ReleaseError,state.Unavailable)) else 'Inspection or updater failed; preserve records and reconcile'
                if row['state'] in ('recovery_required','verification_failed'): row['reason']+='; recovery review required, no automatic retry'
            p['revision']+=1;local.write(plan_path(root,pid),p)
        return view(p)


def recovery(root,pid,tid):
    p=load(root,pid);row=next((r for r in p['targets'] if r['id']==identifier(tid)),None)
    if row is None:raise UpdateError('Target was not selected')
    return {'target':row,'instruction':'Preserve archives and guard transaction. Inspect actual target and capability consumption. Restore only the verified code plane under separately scoped authority; never restore credentials, memory or consumed capabilities. No retry or automatic extraction is performed.'}


def authority_input(root,path):
    path=absolute(path);directory=absolute(Path(root)/'.exocortex/local/update-authorities')
    if path.parent!=directory or not re.fullmatch(r'authority-[a-z0-9-]+\.json',path.name):
        raise UpdateError('Use a named authority reference file under .exocortex/local/update-authorities')
    return local.load(path)


def confirm_restored(root,pid,tid,expected,evidence,lock_root=None):
    """Record an explicitly authorized recovery after exact prior code is back."""
    if not isinstance(evidence,str) or not 1<=len(evidence.strip())<=4000:raise UpdateError('Recovery evidence is required')
    directory=lock_root or local.default_cache().parent/'update-locks'
    with local.lock(plan_path(root,pid).with_suffix('.lock')):
        p=load(root,pid);expect(p,expected)
        row=next((r for r in p['targets'] if r['id']==identifier(tid)),None)
        if not row or row['state'] not in ('applying','recovery_required','verification_failed'):raise UpdateError('Target has no pending recovery')
        before=row['receipt']['before'];marker=family_path(before,directory)
        with local.lock(marker.with_suffix('.lock')):
            m=local.load(marker)
            if not m or m.get('plan')!=pid or m.get('target')!=tid or m.get('resolved'):raise UpdateError('Recovery marker does not match this target')
            if target(row['path'])!=before:raise UpdateError('Prior target code and Git identity have not been restored exactly')
            local.write(marker,dict(m,resolved=True,outcome='restored',evidence=evidence.strip()))
            row.update(state='restored',reason='Prior managed code restored; new preview and fresh authority required')
            p['revision']+=1;local.write(plan_path(root,pid),p)
        return view(p)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project-root',type=Path,default=Path.cwd())
    sub=parser.add_subparsers(dest='action',required=True)
    c=sub.add_parser('create');c.add_argument('id');c.add_argument('--template',type=Path,required=True);c.add_argument('--digest',required=True);c.add_argument('--backup-root',type=Path,required=True);c.add_argument('--target',action='append',required=True);c.add_argument('--account-scope',required=True)
    c.add_argument('--repository');c.add_argument('--tag');c.add_argument('--commit');c.add_argument('--manifest-asset')
    for name in ('show','preview','apply','recovery','confirm-restored'):
        a=sub.add_parser(name);a.add_argument('id')
        if name in ('preview','apply','confirm-restored'):a.add_argument('--expected',required=True)
        if name=='apply':a.add_argument('--authority-file',type=Path,required=True)
        if name in ('recovery','confirm-restored'):a.add_argument('--target-id',required=True)
        if name=='confirm-restored':a.add_argument('--evidence',required=True)
    args=parser.parse_args(argv)
    try:
        root=args.project_root.resolve()
        if args.action=='create':
            values=[args.repository,args.tag,args.commit,args.manifest_asset]
            if any(values) and not all(values):raise UpdateError('Supply all release identity fields')
            r={'repository':args.repository,'tag':args.tag,'commit':args.commit,'asset':str(absolute(args.manifest_asset))} if all(values) else None
            result=create(root,args.id,args.template,args.digest,args.backup_root,args.target,args.account_scope,r)
        elif args.action=='show':result=view(load(root,args.id))
        elif args.action=='recovery':result=recovery(root,args.id,args.target_id)
        elif args.action=='confirm-restored':result=confirm_restored(root,args.id,args.target_id,args.expected,args.evidence)
        else:
            auth=authority_input(root,args.authority_file) if args.action=='apply' else None
            result=execute(root,args.id,args.expected,args.action,auth)
        print(json.dumps(result,indent=2));return 0
    except (UpdateError,local.ReleaseError,state.Unavailable,OSError,ValueError,KeyError,TypeError):
        print('Selected update blocked; preserve records and inspect the exact plan, source and target.',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
