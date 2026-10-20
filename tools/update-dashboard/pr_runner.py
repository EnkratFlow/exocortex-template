"""Durable, data-only publication of reviewed update artifacts.

No HTTP listener, credential discovery, checkout, shell command, merge or forced
ref update exists here. A trusted controller supplies two independently signed
packets and a backend which revalidates live authority. Preview receipts are not
accepted as publication grants. This library is not wired to the hosted Worker.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import time

VERSION = "update-pr-runner-v1"
MAX_PACKET = 12 * 1024 * 1024
MAX_CONTENT = 8 * 1024 * 1024
SHA = re.compile(r"[0-9a-f]{40}")
DIGEST = re.compile(r"[0-9a-f]{64}")
ROOT_FILES = {"AI_START_HERE.md", "AGENTS.md", "CLAUDE.md", ".rules",
              ".github/copilot-instructions.md"}
PREFIXES = (".exocortex/", ".agents/skills/", ".claude/skills/",
            ".cursor/skills/", ".github/skills/")
PROTECTED = {".exocortex/PROJECT_MEMORY.md", ".exocortex/SESSION_CONTEXT.md",
             ".exocortex/SESSION_CONTEXT.local.md", ".exocortex/SESSION_CONTEXT.md.backup",
             ".exocortex/TODO.md", ".exocortex/LESSONS.md", ".exocortex/OPEN_DECISIONS.md",
             ".exocortex/subconscious_patterns.md", ".exocortex/.project-name",
             ".exocortex/.hub_enabled", ".exocortex/.hub_disabled"}
PRIVATE_DIRS = ("events", "archive", "hub", "local", "planning", "knowledge", "work-items")
PROTECTED_CONTROLS = {"ACTIVE_WORK.md", "BRANCH_POLICY.md", "REPO_STATE.md",
                      "EXECUTOR_REGISTRY.json", "EXTERNAL_SYNC_POLICY.json",
                      "INTERRUPTS.md", "BACKLOG.md", "ROADMAP.md", "ARCH_OVERVIEW.md",
                      "REPO_ORGANIZATION_REPORT.md"}


class Blocked(ValueError):
    """A safe public diagnostic code; never include provider bodies."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def exact(value, fields):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise Blocked("invalid_packet_fields")


def token(value, pattern, code):
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise Blocked(code)
    return value


def repository(value):
    token(value, r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", "invalid_repository")
    if any(part in (".", "..") for part in value.split("/")):
        raise Blocked("invalid_repository")
    return value


def sign(kind, payload, key):
    """Trusted controller only. Keys are injected bytes, never loaded or logged."""
    if not isinstance(key, bytes) or len(key) < 32:
        raise Blocked("invalid_signing_configuration")
    body = {"kind": kind, "payload": payload}
    return {**body, "signature": hmac.new(key, canonical(body), hashlib.sha256).hexdigest()}


def verify(packet, kind, key):
    exact(packet, ("kind", "payload", "signature"))
    if len(canonical(packet)) > MAX_PACKET or packet["kind"] != kind:
        raise Blocked("invalid_packet_kind_or_size")
    expected = sign(kind, packet["payload"], key)["signature"]
    if not isinstance(packet["signature"], str) or not hmac.compare_digest(expected, packet["signature"]):
        raise Blocked("invalid_signature")
    return packet["payload"]


def validate_job(job, now):
    exact(job, ("version", "account", "installation", "grant_epoch", "repository_id",
                "repository", "base_branch", "base_sha", "release", "policy",
                "plan_sha256", "artifact_sha256", "created_at", "expires_at"))
    if job["version"] != VERSION:
        raise Blocked("runner_version_mismatch")
    for field in ("account", "grant_epoch"):
        token(job[field], r"[A-Za-z0-9_-]{1,128}", "invalid_identity")
    for field in ("installation", "repository_id"):
        token(job[field], r"[1-9][0-9]{0,19}", "invalid_identity")
    repository(job["repository"])
    token(job["base_branch"], r"[A-Za-z0-9][A-Za-z0-9_./-]{0,199}", "invalid_branch")
    if any(x in job["base_branch"] for x in ("..", "//", "@{")) or job["base_branch"].endswith(("/", ".", ".lock")):
        raise Blocked("invalid_branch")
    token(job["base_sha"], SHA.pattern, "invalid_base")
    for field in ("plan_sha256", "artifact_sha256"):
        token(job[field], DIGEST.pattern, "invalid_digest")
    release = job["release"]
    exact(release, ("repository", "tag", "commit", "manifest_sha256", "modes_sha256"))
    repository(release["repository"])
    token(release["tag"], r"v[0-9]{1,8}\.[0-9]{1,8}\.[0-9]{1,8}", "unpublished_or_invalid_release")
    token(release["commit"], SHA.pattern, "invalid_release")
    for field in ("manifest_sha256", "modes_sha256"):
        token(release[field], DIGEST.pattern, "invalid_release")
    policy = job["policy"]
    exact(policy, ("revision", "sha256", "declaration", "treatment"))
    token(policy["sha256"], DIGEST.pattern, "invalid_policy")
    if type(policy["revision"]) is not int or policy["revision"] < 0:
        raise Blocked("invalid_policy")
    # A missing local policy in a GitHub clone is never an enrollment decision.
    if policy["declaration"] != "explicit" or policy["treatment"] != "standard":
        raise Blocked("policy_requires_review")
    if any(type(job[k]) is not int for k in ("created_at", "expires_at")):
        raise Blocked("invalid_expiry")
    if not job["created_at"] <= now < job["expires_at"] <= job["created_at"] + 3600:
        raise Blocked("expired_request")


def allowed_path(path):
    if (not isinstance(path, str) or len(path) > 240 or
            not re.fullmatch(r"[A-Za-z0-9_. /@+-]+", path) or
            str(PurePosixPath(path)) != path or path.startswith("/") or
            any(p in (".", "..", ".git") for p in path.split("/"))):
        return False
    if path not in ROOT_FILES and not path.startswith(PREFIXES):
        return False
    if path in PROTECTED or any(path == ".exocortex/"+p or path.startswith(".exocortex/"+p+"/") for p in PRIVATE_DIRS):
        return False
    if re.fullmatch(r"\.exocortex/SESSION_CONTEXT_BACKUP_[^/]*\.md", path):
        return False
    if "/.claude/worktrees/" in "/"+path+"/":
        return False
    if path.startswith(".exocortex/control/") and path.rsplit("/", 1)[-1] in PROTECTED_CONTROLS:
        return False
    for part in path.lower().split("/"):
        if (part.startswith(".env") or part in ("credentials", "secrets", "key-registry.json",
                "settings.local.json", "credentials.json", "secrets.json", "tokens.json", "token.json",
                "__pycache__") or part.endswith((".pem", ".key", ".p12", ".pyc"))):
            return False
    return True


def validate_artifact(artifact, job):
    exact(artifact, ("base_sha", "changes", "verification"))
    if artifact["base_sha"] != job["base_sha"] or digest(artifact) != job["artifact_sha256"]:
        raise Blocked("artifact_binding_mismatch")
    verification = artifact["verification"]
    exact(verification, ("guarded_apply_receipt_sha256", "protected_data_passed", "post_apply_remaining_paths"))
    token(verification["guarded_apply_receipt_sha256"], DIGEST.pattern, "missing_apply_receipt")
    if verification["protected_data_passed"] is not True or verification["post_apply_remaining_paths"] != []:
        raise Blocked("unverified_artifact")
    changes = artifact["changes"]
    if not isinstance(changes, list) or not 1 <= len(changes) <= 1000:
        raise Blocked("invalid_change_count")
    paths, total = [], 0
    for row in changes:
        exact(row, ("path", "before_sha", "mode", "content"))
        path = row["path"]
        if not allowed_path(path):
            raise Blocked("protected_or_unsupported_path")
        if row["before_sha"] is not None:
            token(row["before_sha"], SHA.pattern, "invalid_previous_blob")
        if row["content"] is None:
            if row["before_sha"] is None or row["mode"] is not None:
                raise Blocked("invalid_delete")
        else:
            if row["mode"] not in ("100644", "100755") or not isinstance(row["content"], str):
                raise Blocked("invalid_file_mode")
            try:
                content = base64.b64decode(row["content"], validate=True)
            except (ValueError, TypeError):
                raise Blocked("invalid_file_content") from None
            total += len(content)
            if len(content) > 2*1024*1024 or total > MAX_CONTENT:
                raise Blocked("artifact_too_large")
        paths.append(path)
    if paths != sorted(set(paths)):
        raise Blocked("duplicate_or_unsorted_paths")


class Runner:
    """Single-host durable queue. OS lock fences duplicate workers/crash recovery.

    Backend contract:
    - validate(job, artifact): authenticate published release + immutable identity,
      current App grants/epoch, explicit policy digest/revision and default HEAD;
      check each before_sha against the source tree. Fail closed if unavailable.
    - commit(job, artifact, before_write): create ONLY content-addressed blobs/tree/commit,
      fixed metadata, exact base parent. Never a branch mutation.
    - branch/create_branch and find_pr/create_pr: exact dedicated job branch;
      never force/update an existing ref, merge, execute code or deploy.
    The concrete GitHub backend is in pr_runner_github.py.
    """
    def __init__(self, directory, request_key, grant_key, backend, clock=time.time):
        self.root = Path(directory)
        if self.root.is_symlink():
            raise Blocked("unsafe_store")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.root, 0o700)
        for filename in ("jobs.sqlite",):
            if (self.root/filename).is_symlink():
                raise Blocked("unsafe_store")
        self.db = sqlite3.connect(self.root/"jobs.sqlite")
        os.chmod(self.root/"jobs.sqlite", 0o600)
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, account TEXT NOT NULL, packet TEXT NOT NULL,
          state TEXT NOT NULL, commit_sha TEXT, pr TEXT, error TEXT,
          revision INTEGER NOT NULL DEFAULT 0, state_mac TEXT NOT NULL)""")
        self.db.commit()
        self.request_key, self.grant_key = request_key, grant_key
        if hmac.compare_digest(request_key, grant_key):
            raise Blocked("request_and_publication_keys_must_differ")
        self.backend, self.clock = backend, clock

    def close(self):
        self.db.close()

    def submit(self, packet, account):
        payload = verify(packet, "prepared-update", self.request_key)
        exact(payload, ("job", "artifact"))
        job, artifact = payload["job"], payload["artifact"]
        validate_job(job, self.clock())
        validate_artifact(artifact, job)
        if account != job["account"]:
            raise Blocked("account_mismatch")
        jid = digest(job)
        initial = dict(id=jid, account=account, state="prepared", commit_sha=None, pr=None, error=None, revision=0)
        self.db.execute("INSERT OR IGNORE INTO jobs(id,account,packet,state,state_mac) VALUES(?,?,?,?,?)",
                        (jid, account, canonical(packet).decode(), "prepared", self._state_mac(initial)))
        self.db.commit()
        self.status(jid, account)
        return jid

    def _state_mac(self, state):
        return sign("publication-job-state", state, self.grant_key)["signature"]

    def status(self, jid, account):
        token(jid, DIGEST.pattern, "invalid_job_id")
        row = self.db.execute("SELECT state,commit_sha,pr,error,revision,state_mac FROM jobs WHERE id=? AND account=?",
                              (jid, account)).fetchone()
        if not row:
            raise Blocked("job_not_found")
        result = dict(zip(("state", "commit_sha", "pr", "error", "revision"), row[:5]))
        if not isinstance(row[5], str) or not hmac.compare_digest(row[5], self._state_mac(dict(id=jid, account=account, **result))):
            raise Blocked("job_state_integrity_failed")
        return result

    def _write(self, jid, state, commit=None, pr=None, error=None):
        account = self.db.execute("SELECT account FROM jobs WHERE id=?", (jid,)).fetchone()[0]
        current = self.status(jid, account)
        updated = dict(id=jid, account=account, state=state,
                       commit_sha=commit if commit is not None else current["commit_sha"],
                       pr=pr if pr is not None else current["pr"], error=error,
                       revision=current["revision"]+1)
        self.db.execute("""UPDATE jobs SET state=?,commit_sha=?,pr=?,error=?,revision=?,state_mac=?
           WHERE id=? AND revision=?""", (updated["state"], updated["commit_sha"], updated["pr"],
                   error, updated["revision"], self._state_mac(updated), jid, current["revision"]))
        self.db.commit()

    @contextlib.contextmanager
    def _lock(self, jid):
        # Deployment target is POSIX; explicitly fail on unsupported platforms.
        import fcntl
        fd = os.open(self.root/(jid+".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Blocked("job_busy") from None
            yield
        finally:
            os.close(fd)

    def run(self, jid, account, grant):
        self.status(jid, account)
        with self._lock(jid):
            state = self.status(jid, account)
            stored = json.loads(self.db.execute("SELECT packet FROM jobs WHERE id=?", (jid,)).fetchone()[0])
            payload = verify(stored, "prepared-update", self.request_key)
            job, artifact = payload["job"], payload["artifact"]
            if digest(job) != jid or job["account"] != account:
                raise Blocked("stored_job_binding_mismatch")
            validate_artifact(artifact, job)
            if state["state"] in ("complete", "published_needs_review"):
                return state
            permission = verify(grant, "publish-update-pr", self.grant_key)
            exact(permission, ("account", "job_id", "artifact_sha256", "expires_at"))
            if (permission["account"] != account or permission["job_id"] != jid or
                    permission["artifact_sha256"] != job["artifact_sha256"] or
                    type(permission["expires_at"]) is not int):
                raise Blocked("publication_grant_mismatch")
            def check(object_write=False):
                validate_job(job, self.clock())
                if self.clock() >= permission["expires_at"] or permission["expires_at"] > job["expires_at"]:
                    raise Blocked("publication_grant_expired")
                validate_artifact(artifact, job)
                # Object creation cannot move a branch. Reuse its immutable
                # validation, but still check current controller policy/expiry.
                # Branch and PR effects always take the full live path.
                if object_write and hasattr(self.backend, "validate_objects"):
                    self.backend.validate_objects(job, artifact)
                else:
                    self.backend.validate(job, artifact)
                # Validation can wait on a provider. Recheck expiry after it.
                validate_job(job, self.clock())
                if self.clock() >= permission["expires_at"]:
                    raise Blocked("publication_grant_expired")
            branch = "codex/exocortex-update-" + jid
            marker = "<!-- exocortex-update-job:" + jid + " artifact:" + job["artifact_sha256"] + " -->"
            def finish(pr):
                exact(pr, ("url", "base_sha"))
                token(pr["url"], r"https://github\.com/"+re.escape(job["repository"])+r"/pull/[1-9][0-9]*", "invalid_pr_identity")
                token(pr["base_sha"], SHA.pattern, "invalid_pr_identity")
                changed = pr["base_sha"] != job["base_sha"]
                self._write(jid, "published_needs_review" if changed else "complete",
                            pr=pr["url"], error="base_changed_after_pr" if changed else None)
            try:
                # Read-only recovery is allowed after expiry/policy drift. It
                # never grants a new write; current read access is still needed.
                if state["state"] in ("branch_pending", "pr_pending"):
                    self.backend.observe(job)
                    token(state["commit_sha"], SHA.pattern, "invalid_commit")
                    observed = self.backend.branch(job, branch)
                    if observed != state["commit_sha"]:
                        raise Blocked("uncertain_branch_requires_reconciliation" if observed is None else "foreign_or_changed_branch")
                    if state["state"] == "pr_pending":
                        pr = self.backend.find_pr(job, branch, state["commit_sha"], marker)
                        if pr is None:
                            raise Blocked("uncertain_pr_requires_reconciliation")
                        finish(pr)
                        return self.status(jid, account)
                    self._write(jid, "branch_ready")
                    state = self.status(jid, account)
                check()
                if state["state"] in ("prepared", "objects_pending"):
                    self._write(jid, "objects_pending")
                    commit = self.backend.commit(job, artifact, lambda: check(object_write=True))
                    token(commit, SHA.pattern, "invalid_commit")
                    self._write(jid, "objects_ready", commit=commit)
                    state = self.status(jid, account)
                commit = state["commit_sha"]
                token(commit, SHA.pattern, "invalid_commit")
                remote = self.backend.branch(job, branch)
                if remote is not None and remote != commit:
                    raise Blocked("foreign_or_changed_branch")
                if remote is None:
                    if state["state"] != "objects_ready":
                        raise Blocked("uncertain_branch_requires_reconciliation")
                    check()
                    self._write(jid, "branch_pending")
                    try:
                        check()
                    except Exception:
                        self._write(jid, "objects_ready")
                        raise
                    self.backend.create_branch(job, branch, commit)
                    # Observe even after a successful response; do not trust success alone.
                    if self.backend.branch(job, branch) != commit:
                        raise Blocked("branch_not_confirmed")
                if state["state"] not in ("pr_pending",):
                    self._write(jid, "branch_ready")
                check()
                pr = self.backend.find_pr(job, branch, commit, marker)
                if pr is None:
                    if state["state"] == "pr_pending":
                        raise Blocked("uncertain_pr_requires_reconciliation")
                    check()
                    if self.backend.branch(job, branch) != commit:
                        raise Blocked("branch_changed_before_pr")
                    self._write(jid, "pr_pending")
                    try:
                        check()
                    except Exception:
                        self._write(jid, "branch_ready")
                        raise
                    self.backend.create_pr(job, branch, marker)
                    pr = self.backend.find_pr(job, branch, commit, marker)
                    if pr is None:
                        raise Blocked("pr_not_confirmed")
                finish(pr)
            except Exception as exc:
                # Retain pending intent. A restart observes exact remote effects first.
                # Adapters cannot cause provider diagnostics/secrets to be persisted.
                safe_codes = {
                    "expired_request", "publication_grant_expired", "artifact_binding_mismatch",
                    "base_changed", "policy_changed", "grant_revoked", "release_revoked",
                    "live_authority_rejected", "repository_identity_changed", "source_blob_changed",
                    "incomplete_source_tree", "ambiguous_source_tree", "unsupported_source_type",
                    "foreign_or_changed_branch", "uncertain_branch_requires_reconciliation",
                    "branch_not_confirmed", "uncertain_pr_requires_reconciliation",
                    "branch_changed_before_pr", "pr_not_confirmed", "foreign_or_changed_pr",
                    "ambiguous_pr", "pr_inventory_truncated", "invalid_pr_identity",
                    "invalid_commit", "invalid_branch_response", "invalid_branch_commit",
                    "invalid_blob", "invalid_tree", "invalid_base_tree", "invalid_pr_inventory",
                }
                code = str(exc) if isinstance(exc, Blocked) and str(exc) in safe_codes else "provider_or_runner_unavailable"
                current = self.status(jid, account)
                self._write(jid, current["state"], error=code)
            return self.status(jid, account)
