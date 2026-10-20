"""Private controller authority, reread before each publication write.

The administrator installs signed control records and explicit policy files.
There is no enrollment, policy-write, credential-discovery, or browser endpoint.
Hosted activation must connect revocation to these records before accepting jobs.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import time

from pr_runner import Blocked, exact, verify, digest
from pr_runner_prepare import updater


def private_json(path, limit=65536):
    """Read an owner-private, regular, non-linked record without following links."""
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise Blocked("unsafe_authority_store")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        meta = os.fstat(fd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or
                meta.st_mode & 0o077 or meta.st_uid != os.getuid() or meta.st_size > limit):
            raise Blocked("unsafe_authority_store")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit+1)
        if len(raw) > limit:
            raise Blocked("authority_record_too_large")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise Blocked("invalid_authority_record")
                result[key] = value
            return result
        return json.loads(raw, object_pairs_hook=unique)
    finally:
        os.close(fd)


class RepositoryAuthority:
    """One private control directory, with a signed record per immutable repo ID.

    Only fixed, administrator-provisioned records select source/policy paths.
    A prepared job cannot select a filesystem path or provide its own policy.
    The credential broker must mint an installation token for precisely the
    installation/repository in this record; this class does not mint tokens.
    """
    def __init__(self, directory, control_key, clock=time.time):
        self.root = Path(directory)
        if (not self.root.is_absolute() or self.root.resolve() != self.root or
                not self.root.is_dir() or self.root.stat().st_mode & 0o077 or
                self.root.stat().st_uid != os.getuid()):
            raise Blocked("unsafe_authority_store")
        self.key, self.clock = control_key, clock
        self.validated = set()

    def _record(self, job):
        # job identity is already validated by Runner. Still reject unsafe IDs
        # before constructing a path when this callback is called independently.
        from pr_runner import token
        token(job["repository_id"], r"[1-9][0-9]{0,19}", "invalid_identity")
        try:
            record = verify(private_json(self.root/(job["repository_id"]+".json")),
                            "runner-control", self.key)
            exact(record, ("account", "installation", "grant_epoch", "repository_id",
                           "repository", "enabled", "expires_at", "policy_revision",
                           "policy_directory", "source"))
            if (record["enabled"] is not True or type(record["expires_at"]) is not int or
                    self.clock() >= record["expires_at"] or
                    any(record[key] != job[key] for key in
                        ("account", "installation", "grant_epoch", "repository_id", "repository"))):
                raise Blocked("grant_revoked")
            # The controller holds the policy; target repository files cannot
            # relax it. Restrictive/missing declarations always block this lane.
            policy_root = Path(record["policy_directory"])
            if (not policy_root.is_absolute() or policy_root.resolve() != policy_root or
                    self.root not in policy_root.parents):
                raise Blocked("unsafe_authority_store")
            policy = updater.policy.read(policy_root)
            if (policy["present"] is not True or policy["mode"] != "standard" or
                    policy["protected_paths"] or
                    type(record["policy_revision"]) is not int or
                    record["policy_revision"] != job["policy"]["revision"] or
                    policy["sha256"] != job["policy"]["sha256"] or
                    job["policy"]["declaration"] != "explicit" or
                    job["policy"]["treatment"] != "standard"):
                raise Blocked("policy_changed")
            return record
        except Blocked:
            raise
        except Exception:
            raise Blocked("live_authority_rejected") from None

    def recheck(self, job, artifact):
        """Cheap revocation/policy check for immutable Git object creation only."""
        record = self._record(job)
        if digest({"record": record, "job": job}) not in self.validated:
            raise Blocked("live_authority_rejected")
        return True

    def __call__(self, job, artifact):
        try:
            record = self._record(job)
            # Full attestation at initial validation and immediately before
            # branch/PR effects; never repeat it once per immutable Git blob.
            source = updater.verify_source(record["source"], apply=True)
            release = record["source"]["release"]
            expected = {"repository": release["repository"], "tag": release["tag"],
                        "commit": release["commit"],
                        "manifest_sha256": record["source"]["manifest_sha256"],
                        "modes_sha256": hashlib.sha256(updater.file_bytes(source/"FILEMODES")).hexdigest()}
            if expected != job["release"]:
                raise Blocked("release_revoked")
            self.validated.add(digest({"record": record, "job": job}))
            return True
        except Blocked:
            raise
        except Exception:
            # A missing record, malformed policy or provider error never
            # includes private filesystem paths, policy prose or diagnostics.
            raise Blocked("live_authority_rejected") from None
