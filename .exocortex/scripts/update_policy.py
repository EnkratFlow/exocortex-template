"""Private update policy and hash-only customization comparison; no writes."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import prepare_update_reconciliation as surface

POLICY = '.exocortex/local/update-policy.json'


class PolicyError(ValueError): pass


def relative(value):
    if (not isinstance(value, str) or not value or len(value) > 240
            or not re.fullmatch(r'[A-Za-z0-9_. /@+-]+', value)
            or str(PurePosixPath(value)) != value or value.startswith('/')
            or any(part in ('.', '..', '.git') for part in value.split('/'))):
        raise PolicyError('Unsafe policy or manifest path')
    return value


def code_path(value):
    relative(value)
    if value in ('.exocortex/.version','.exocortex/.install-manifest'):return False
    if surface.is_protected_path(value) or surface.is_runtime_state(value):return False
    parts=[part.casefold() for part in value.split('/')]
    if any(part.startswith('.env') or part in ('credentials','secrets','tokens.json','token.json','secrets.json','credentials.json','key-registry.json','settings.local.json','__pycache__') or part.endswith(('.pem','.key','.p12','.pyc')) for part in parts):return False
    return True


def read(root):
    # release_awareness imports update_inventory.version; defer this dependency
    # until module initialization has completed in every canonical import order.
    import release_awareness as local
    path=local.safe(Path(root)/POLICY)
    if not path.exists():return {'present':False,'sha256':None,'mode':'standard','protected_paths':[]}
    if not path.is_file() or path.stat().st_nlink != 1 or path.stat().st_size > 16384:raise PolicyError('Update policy requires a bounded regular file')
    with path.open('rb') as stream:raw=stream.read(16385)
    if len(raw)>16384:raise PolicyError('Update policy exceeds inspection bound')
    try:
        def unique(pairs):
            result={}
            for key,value in pairs:
                if key in result:raise PolicyError('Duplicate update policy field')
                result[key]=value
            return result
        value=json.loads(raw,object_pairs_hook=unique)
        if (not isinstance(value,dict) or not {'mode','protected_paths'} <= set(value)
                or set(value)-{'mode','protected_paths','reason'}
                or value['mode'] not in ('standard','review_only','excluded')
                or not isinstance(value['protected_paths'],list) or len(value['protected_paths'])>100):raise PolicyError('Malformed update policy')
        paths=value['protected_paths']
        if any(not code_path(p) for p in paths) or len(set(paths))!=len(paths):raise PolicyError('Invalid protected paths in update policy')
        if 'reason' in value and (not isinstance(value['reason'],str) or len(value['reason'])>500):raise PolicyError('Invalid update policy reason')
    except (ValueError,TypeError,UnicodeError,RecursionError) as exc:
        raise PolicyError('Malformed or unsafe update policy; separate review required') from exc
    # Reason is private prose, not copied into inventory or plan output.
    return {'present':True,'sha256':hashlib.sha256(raw).hexdigest(),'mode':value['mode'],'protected_paths':sorted(paths)}


def compare(baseline,current,incoming,policy):
    # Match install.sh's copied surfaces. Root .gitignore is project-owned
    # with appended managed blocks; template CI workflows are never installed.
    incoming={path:value for path,value in incoming.items()
              if path in ('AI_START_HERE.md','AGENTS.md','CLAUDE.md','.rules','.github/copilot-instructions.md')
              or path.startswith(('.exocortex/','.agents/','.cursor/','.github/skills/','.claude/skills/'))}
    rows=[]
    for path in sorted(set(baseline)|set(incoming)):
        if not surface.is_surface_path(path) or not code_path(path):continue
        old=baseline.get(path);now=current.get(path,{}).get('sha256');new=incoming.get(path)
        if old==now==new:continue
        if old is None:
            kind='upstream-only' if now is None else ('converged' if now==new else 'unknownbaseline')
        elif now is None:kind='deleted' if new is not None else 'converged'
        elif now==new:kind='converged'
        elif now==old:kind='upstream-only'
        elif new==old:kind='local-only'
        else:kind='conflict'
        rows.append({'path':path,'classification':kind,'baseline_sha256':old,'local_sha256':now,'incoming_sha256':new})
    blocked=policy['mode']!='standard' or bool(policy['protected_paths']) or any(r['classification'] in ('local-only','conflict','deleted','unknownbaseline') for r in rows)
    return {'requires_review':blocked,'policy':policy,'files':rows}
