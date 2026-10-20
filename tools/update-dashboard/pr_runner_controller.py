"""Trusted local preparation orchestration; never a browser execution endpoint.

The host provisions a disposable checkout and a published source separately.
This controller connects the existing selected updater to the PR artifact
freezer. It does not create authority, clone with write credentials, publish,
merge, execute target scripts, or accept browser-selected filesystem paths.
"""
from pathlib import Path
import hashlib
import time

from pr_runner import Blocked, digest, validate_job, verify
from pr_runner_prepare import updater, prepare


class PreparationController:
    def __init__(self, root, source, checkout, backup, authority, observe, clock=time.time):
        """Paths/callbacks come from trusted host provisioning, not request JSON.

        authority(job, artifact) is the existing RepositoryAuthority callback.
        observe(job) must make a current read-only provider check and return
        exactly the immutable repository ID/name/default branch/base SHA.
        """
        self.root, self.checkout, self.backup = map(Path, (root, checkout, backup))
        self.source, self.authority, self.observe = source, authority, observe
        self.clock = clock
        for path in (self.root, self.checkout, self.backup):
            if not path.is_absolute() or path.resolve() != path:
                raise Blocked('unsafe_preparation_path')
        if any(not updater.independent(a,b) for a,b in ((self.root,self.checkout),(self.root,self.backup),(self.checkout,self.backup))):
            raise Blocked('unsafe_preparation_path')

    def _validate(self, job):
        validate_job(job, self.clock())
        self.authority(job, None)
        source = updater.verify_source(self.source, apply=True)
        release = self.source['release']
        expected = dict(repository=release['repository'], tag=release['tag'], commit=release['commit'],
                        manifest_sha256=self.source['manifest_sha256'],
                        modes_sha256=hashlib.sha256(updater.file_bytes(source/'FILEMODES')).hexdigest())
        if job['release'] != expected:
            raise Blocked('release_binding_mismatch')
        expected_remote = {key:job[key] for key in ('repository_id','repository','base_branch','base_sha')}
        if self.observe(job) != expected_remote:
            raise Blocked('repository_changed')
        current = updater.target(self.checkout, updater.candidate_hashes(self.source))
        if current['binding'].get('head') != job['base_sha']:
            raise Blocked('checkout_binding_mismatch')
        remote = updater.state.git(self.checkout, 'remote', 'get-url', 'origin')
        if updater.state.remote_identity(remote) != 'github.com/'+job['repository'].lower():
            raise Blocked('repository_binding_mismatch')
        if current['customization']['requires_review']:
            raise Blocked('customization_review_required')
        validate_job(job, self.clock())
        return current

    def preview(self, plan_id, job):
        """Persist one immutable selection and run the trusted updater dry run.

        A retry of the same ID reuses its plan; a different binding is rejected.
        Rehearsal/apply cannot start from this result without exact authority.
        """
        current = self._validate(job)
        path = updater.plan_path(self.root, plan_id)
        if not path.exists():
            updater.create(self.root, plan_id, self.source['path'], self.source['manifest_sha256'],
                           self.backup, [self.checkout], job['account'], self.source['release'])
        plan = updater.load(self.root, plan_id)
        self._bind(plan, job)
        row = plan['targets'][0]
        if row['initial'] != current:
            raise Blocked('preparation_changed')
        if row['state'] == 'not_attempted':
            updater.execute(self.root, plan_id, digest(plan), 'preview')
        plan = updater.load(self.root, plan_id)
        self._validate(job)
        return self.summary(plan)

    def _bind(self, plan, job):
        if (plan['account_scope'] != job['account'] or plan['source'] != self.source or
                Path(plan['backup_root']) != self.backup or len(plan['targets']) != 1 or
                Path(plan['targets'][0]['path']) != self.checkout or
                plan['targets'][0]['initial']['binding']['head'] != job['base_sha']):
            raise Blocked('plan_binding_mismatch')

    @staticmethod
    def summary(plan):
        row = plan['targets'][0]
        return {'plan_id':plan['id'], 'plan_sha256':digest(plan), 'target_id':row['id'],
                'state':row['state'], 'changed_paths':(row.get('receipt') or {}).get('changed_paths', []),
                'requires_review':row['state'] not in ('ready','current','applied'),
                'published':False}

    def rehearse(self, plan_id, expected, job, authorities, key):
        """Apply only existing target-specific guarded authority, then freeze.

        No capabilities, policies, publication grants or keys are created here.
        The caller must durably retain the returned signed packet before asking
        the publisher to act. A failure leaves coordinator recovery evidence.
        """
        self._validate(job)
        plan = updater.load(self.root, plan_id)
        self._bind(plan, job)
        updater.expect(plan, expected)
        row = plan['targets'][0]
        if row['state'] != 'ready':
            raise Blocked('reviewed_preview_required')
        if not isinstance(authorities,dict) or set(authorities) != {row['id']}:
            raise Blocked('exact_target_authority_required')
        # The selected updater itself validates and consumes the exact apply
        # authority. This wrapper never substitutes a signed preview for it.
        updater.execute(self.root, plan_id, expected, 'apply', authorities)
        plan = updater.load(self.root, plan_id)
        self._bind(plan, job)
        if plan['targets'][0]['state'] != 'applied':
            raise Blocked('rehearsal_not_verified')
        return self.freeze(plan_id, digest(plan), job, key)

    def freeze(self, plan_id, expected, job, key):
        """Recover artifact creation after a verified rehearsal without reapplying."""
        self._validate(job)
        plan = updater.load(self.root, plan_id)
        self._bind(plan, job)
        updater.expect(plan, expected)
        row = plan['targets'][0]
        if row['state'] != 'applied':
            raise Blocked('verified_rehearsal_required')
        bound = dict(job, plan_sha256=digest(plan))
        packet = prepare(self.root, plan_id, row['id'], bound, key, self.clock())
        payload = verify(packet, 'prepared-update', key)
        self._validate(payload['job'])
        return packet
