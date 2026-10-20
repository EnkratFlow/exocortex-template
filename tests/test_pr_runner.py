"""Offline publication/restart tests: fictional accounts, no credentials/network."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools/update-dashboard"))
import pr_runner as r
from pr_runner_github import GitHubBackend

REQUEST_KEY = b"fictional-request-signing-key-only" * 2
GRANT_KEY = b"fictional-publish-signing-key-only" * 2
BASE, COMMIT = "a"*40, "b"*40
NOW = 1800000000


def sample():
    artifact = {"base_sha": BASE, "changes": [
        {"path": ".exocortex/scripts/example.py", "before_sha": "c"*40,
         "mode": "100644", "content": base64.b64encode(b"# fictional update\n").decode()}
    ], "verification": {"guarded_apply_receipt_sha256": "d"*64,
                         "protected_data_passed": True, "post_apply_remaining_paths": []}}
    job = {"version": r.VERSION, "account": "owner-1", "installation": "123",
           "grant_epoch": "4", "repository_id": "456", "repository": "example/project",
           "base_branch": "main", "base_sha": BASE,
           "release": {"repository": "example/template", "tag": "v4.0.0", "commit": "e"*40,
                       "manifest_sha256": "f"*64, "modes_sha256": "1"*64},
           "policy": {"revision": 1, "sha256": "2"*64, "declaration": "explicit", "treatment": "standard"},
           "plan_sha256": "3"*64, "artifact_sha256": r.digest(artifact),
           "created_at": NOW, "expires_at": NOW+300}
    return {"job": job, "artifact": artifact}


class FakeBackend:
    def __init__(self):
        self.remote = None
        self.pr = None
        self.calls = []
        self.reject = None
        self.fail = None
        self.clock_hook = None

    def validate(self, job, artifact):
        if self.clock_hook:
            self.clock_hook()
        if self.reject:
            raise r.Blocked(self.reject)

    def observe(self, job):
        self.calls.append("observe")

    def commit(self, job, artifact, before_write):
        before_write()
        self.calls.append("objects")
        return COMMIT

    def branch(self, job, branch):
        return self.remote

    def create_branch(self, job, branch, commit):
        self.calls.append("branch")
        if self.fail == "branch_before":
            raise TimeoutError("private provider diagnostic must never escape")
        self.remote = commit
        if self.fail == "branch_after":
            raise TimeoutError("private provider diagnostic must never escape")

    def find_pr(self, job, branch, commit, marker):
        return self.pr

    def create_pr(self, job, branch, marker):
        self.calls.append("pr")
        if self.fail == "pr_before":
            raise TimeoutError("private provider diagnostic")
        self.pr = {"url":"https://github.com/example/project/pull/1", "base_sha":BASE}
        if self.fail == "pr_after":
            raise TimeoutError("private provider diagnostic")


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.backend = FakeBackend()
        self.now = NOW
        self.runner = self.open_runner()
        self.payload = sample()

    def tearDown(self):
        self.runner.close()
        self.temp.cleanup()

    def open_runner(self):
        return r.Runner(self.temp.name, REQUEST_KEY, GRANT_KEY, self.backend, lambda: self.now)

    def submit(self):
        return self.runner.submit(r.sign("prepared-update", self.payload, REQUEST_KEY), "owner-1")

    def grant(self, jid):
        return r.sign("publish-update-pr", {"account": "owner-1", "job_id": jid,
                        "artifact_sha256": self.payload["job"]["artifact_sha256"],
                        "expires_at": NOW+300}, GRANT_KEY)

    def run_job(self, jid):
        return self.runner.run(jid, "owner-1", self.grant(jid))

    def restart(self):
        self.runner.close()
        self.runner = self.open_runner()

    def test_repeat_and_restart_create_one_branch_and_one_pr(self):
        jid = self.submit()
        self.assertEqual(self.submit(), jid)
        self.assertEqual(self.run_job(jid)["state"], "complete")
        self.restart()
        self.assertEqual(self.run_job(jid)["state"], "complete")
        self.assertEqual(self.backend.calls, ["objects", "branch", "pr"])

    def test_timeout_after_branch_acceptance_reconciles_without_second_branch(self):
        jid = self.submit()
        self.backend.fail = "branch_after"
        first = self.run_job(jid)
        self.assertEqual(first["state"], "branch_pending")
        self.assertEqual(first["error"], "provider_or_runner_unavailable")
        self.restart()
        self.backend.fail = None
        self.assertEqual(self.run_job(jid)["state"], "complete")
        self.assertEqual(self.backend.calls.count("branch"), 1)

    def test_timeout_after_pr_acceptance_reconciles_without_second_pr(self):
        jid = self.submit()
        self.backend.fail = "pr_after"
        self.assertEqual(self.run_job(jid)["state"], "pr_pending")
        self.restart()
        self.backend.fail = None
        self.assertEqual(self.run_job(jid)["state"], "complete")
        self.assertEqual(self.backend.calls.count("pr"), 1)

    def test_unknown_absent_branch_does_not_blindly_retry(self):
        jid = self.submit()
        self.backend.fail = "branch_before"
        self.run_job(jid)
        self.restart()
        self.backend.fail = None
        result = self.run_job(jid)
        self.assertEqual(result["error"], "uncertain_branch_requires_reconciliation")
        self.assertEqual(self.backend.calls.count("branch"), 1)

    def test_unknown_absent_pr_does_not_blindly_retry(self):
        jid = self.submit()
        self.backend.fail = "pr_before"
        self.run_job(jid)
        self.restart()
        self.backend.fail = None
        self.assertEqual(self.run_job(jid)["error"], "uncertain_pr_requires_reconciliation")
        self.assertEqual(self.backend.calls.count("pr"), 1)

    def test_pending_pr_is_observed_after_expiry_and_policy_drift(self):
        jid = self.submit()
        self.backend.fail = "pr_after"
        self.run_job(jid)
        self.restart()
        self.now = NOW+301
        self.backend.reject = "policy_changed"
        self.assertEqual(self.run_job(jid)["state"], "complete")
        self.assertEqual(self.backend.calls.count("pr"), 1)
        self.assertIn("observe", self.backend.calls)

    def test_pending_branch_settles_after_expiry_without_creating_pr(self):
        jid = self.submit()
        self.backend.fail = "branch_after"
        self.run_job(jid)
        self.now = NOW+301
        self.assertEqual(self.run_job(jid)["state"], "branch_ready")
        self.assertNotIn("pr", self.backend.calls)

    def test_base_advance_during_pr_creation_records_review_not_success(self):
        jid = self.submit()
        old = self.backend.create_pr
        def changed(*args):
            old(*args)
            self.backend.pr["base_sha"] = "9"*40
        self.backend.create_pr = changed
        result = self.run_job(jid)
        self.assertEqual(result["state"], "published_needs_review")
        self.assertEqual(result["pr"], "https://github.com/example/project/pull/1")

    def test_foreign_branch_is_never_overwritten(self):
        jid = self.submit()
        self.backend.remote = "9"*40
        self.assertEqual(self.run_job(jid)["error"], "foreign_or_changed_branch")
        self.assertNotIn("branch", self.backend.calls)
        self.assertNotIn("pr", self.backend.calls)

    def test_base_or_policy_or_grant_change_blocks_all_writes(self):
        jid = self.submit()
        for reason in ("base_changed", "policy_changed", "grant_revoked", "release_revoked"):
            self.backend.reject = reason
            self.assertEqual(self.run_job(jid)["error"], reason)
        self.assertEqual(self.backend.calls, [])

    def test_drift_after_branch_does_not_create_pr(self):
        jid = self.submit()
        old = self.backend.create_branch
        def change(*args):
            old(*args)
            self.backend.reject = "base_changed"
        self.backend.create_branch = change
        self.assertEqual(self.run_job(jid)["error"], "base_changed")
        self.assertNotIn("pr", self.backend.calls)

    def test_expiry_during_provider_check_blocks_write(self):
        jid = self.submit()
        self.backend.clock_hook = lambda: setattr(self, "now", NOW+301)
        self.assertEqual(self.run_job(jid)["error"], "expired_request")
        self.assertEqual(self.backend.calls, [])

    def test_other_account_cannot_observe_or_run(self):
        jid = self.submit()
        with self.assertRaises(r.Blocked):
            self.runner.status(jid, "owner-2")
        with self.assertRaises(r.Blocked):
            self.runner.run(jid, "owner-2", self.grant(jid))
        self.assertEqual(self.backend.calls, [])

    def test_preview_or_wrong_signature_cannot_authorize_publication(self):
        jid = self.submit()
        for packet in (r.sign("preview", {}, REQUEST_KEY),
                       r.sign("publish-update-pr", {}, REQUEST_KEY)):
            with self.assertRaises(r.Blocked):
                self.runner.run(jid, "owner-1", packet)
        self.assertEqual(self.backend.calls, [])

    def test_artifact_tampering_rejected(self):
        self.payload["artifact"]["changes"][0]["content"] = "dGFtcGVy"
        with self.assertRaisesRegex(r.Blocked, "artifact_binding"):
            self.submit()

    def test_stored_packet_and_state_tampering_rejected(self):
        jid = self.submit()
        packet = r.sign("prepared-update", self.payload, REQUEST_KEY)
        packet["payload"]["job"]["repository"] = "example/other"
        self.runner.db.execute("UPDATE jobs SET packet=? WHERE id=?", (json.dumps(packet), jid))
        self.runner.db.commit()
        with self.assertRaisesRegex(r.Blocked, "invalid_signature"):
            self.run_job(jid)
        self.runner.db.execute("UPDATE jobs SET state='objects_ready',commit_sha=? WHERE id=?", ("9"*40, jid))
        self.runner.db.commit()
        with self.assertRaisesRegex(r.Blocked, "job_state_integrity_failed"):
            self.run_job(jid)
        self.assertEqual(self.backend.calls, [])

    def test_valid_other_packet_cannot_replace_job_binding(self):
        jid = self.submit()
        other = copy.deepcopy(self.payload)
        other["job"]["repository"] = "example/other"
        self.runner.db.execute("UPDATE jobs SET packet=? WHERE id=?",
                               (json.dumps(r.sign("prepared-update", other, REQUEST_KEY)), jid))
        self.runner.db.commit()
        with self.assertRaisesRegex(r.Blocked, "stored_job_binding_mismatch"):
            self.run_job(jid)

    def test_expiry_after_pending_persistence_is_known_no_effect(self):
        for stage in ("branch_pending", "pr_pending"):
            with self.subTest(stage=stage):
                self.payload = sample()
                self.payload["job"]["grant_epoch"] = stage
                self.now = NOW
                self.backend.remote, self.backend.pr = None, None
                self.backend.calls.clear()
                jid = self.submit()
                original = self.runner._write
                def expire(job_id, state, **kwargs):
                    original(job_id, state, **kwargs)
                    if state == stage:
                        self.now = NOW+301
                self.runner._write = expire
                result = self.run_job(jid)
                self.runner._write = original
                self.assertEqual(result["state"], "objects_ready" if stage=="branch_pending" else "branch_ready")
                self.assertNotIn("branch" if stage=="branch_pending" else "pr", self.backend.calls)

    def test_provider_blocked_message_is_not_exposed(self):
        jid = self.submit()
        self.backend.reject = "sensitive-provider-canary"
        self.assertEqual(self.run_job(jid)["error"], "provider_or_runner_unavailable")
        self.assertNotIn("sensitive-provider-canary", json.dumps(self.runner.status(jid, "owner-1")))

    def test_dot_segments_and_oversized_repository_tag_rejected(self):
        for name in ("../repo", "owner/..", "./repo", "a"*101+"/repo"):
            self.payload = sample()
            self.payload["job"]["repository"] = name
            with self.assertRaises(r.Blocked):
                self.submit()
        self.payload = sample()
        self.payload["job"]["release"]["tag"] = "v"+"1"*100+".0.0"
        with self.assertRaises(r.Blocked):
            self.submit()
        self.assertEqual(self.backend.calls, [])

    def test_missing_or_restrictive_policy_blocks(self):
        for declaration, mode in (("missing", "standard"), ("explicit", "review_only"), ("explicit", "excluded")):
            self.payload["job"]["policy"].update(declaration=declaration, treatment=mode)
            with self.assertRaisesRegex(r.Blocked, "policy_requires_review"):
                self.submit()

    def test_protected_workflow_app_and_credential_paths_blocked(self):
        for path in (".gitignore", ".exocortex/PROJECT_MEMORY.md", ".exocortex/events/a.md",
                     ".exocortex/control/EXECUTOR_REGISTRY.json", ".exocortex/.env",
                     ".github/workflows/deploy.yml", "firebase.json", "src/main.py",
                     ".exocortex/scripts/../../secret", ".exocortex/knowledge/KNOWLEDGE.md",
                     ".exocortex/SESSION_CONTEXT_BACKUP_old.md",
                     ".claude/skills/x/.claude/worktrees/y"):
            self.payload = sample()
            self.payload["artifact"]["changes"][0]["path"] = path
            self.payload["job"]["artifact_sha256"] = r.digest(self.payload["artifact"])
            with self.assertRaises(r.Blocked, msg=path):
                self.submit()

    def test_unknown_verification_or_symlink_mode_blocked(self):
        self.payload["artifact"]["changes"][0]["mode"] = "120000"
        self.payload["job"]["artifact_sha256"] = r.digest(self.payload["artifact"])
        with self.assertRaises(r.Blocked):
            self.submit()

    def test_changed_policy_changes_job_identity(self):
        old = self.submit()
        self.payload["job"]["policy"]["revision"] += 1
        self.assertNotEqual(self.submit(), old)

    def test_second_process_lock_blocks_duplicate_work(self):
        jid = self.submit()
        with self.runner._lock(jid):
            with self.assertRaisesRegex(r.Blocked, "job_busy"):
                self.run_job(jid)


class GitHubBackendTests(unittest.TestCase):
    def test_many_blobs_reuse_tree_but_recheck_policy_for_every_object(self):
        payload = sample()
        artifact, job = payload["artifact"], payload["job"]
        original = artifact["changes"][0]
        artifact["changes"] = [dict(original, path=f".exocortex/scripts/fixture_{i:03}.py") for i in range(50)]
        job["artifact_sha256"] = r.digest(artifact)
        calls = []
        class Authority:
            full = 0
            cheap = 0
            revoked = False
            def __call__(self, *_):
                self.full += 1
                return True
            def recheck(self, *_):
                self.cheap += 1
                if self.revoked:
                    raise r.Blocked("grant_revoked")
                return True
        authority = Authority()
        def request(method, path, body=None):
            calls.append((method, path))
            if method == "POST":
                return {"sha":"d"*40}
            if path.startswith("/repositories/"):
                return {"id":456, "full_name":"example/project", "default_branch":"main", "archived":False}
            if "/git/ref/" in path:
                return {"object":{"sha":BASE}}
            if "/git/commits/" in path:
                return {"tree":{"sha":"e"*40}}
            return {"truncated":False, "tree":[
                {"path":row["path"], "sha":row["before_sha"], "type":"blob", "mode":"100644"}
                for row in artifact["changes"]]}
        backend = GitHubBackend(request, authority)
        with self.assertRaisesRegex(r.Blocked, "live_authority_rejected"):
            backend.validate_objects(job, artifact)
        backend.validate(job, artifact)
        backend.commit(job, artifact, lambda:backend.validate_objects(job, artifact))
        self.assertEqual(authority.full, 1)
        self.assertEqual(authority.cheap, 52)
        self.assertEqual(sum(method == "GET" and "/git/trees/" in path for method,path in calls), 1)
        # Publication is a separate full check, and revocation still prevents
        # any further immutable object writes.
        backend.validate(job, artifact)
        self.assertEqual(authority.full, 2)
        authority.revoked = True
        before = len(calls)
        with self.assertRaisesRegex(r.Blocked, "grant_revoked"):
            backend.commit(job, artifact, lambda:backend.validate_objects(job, artifact))
        self.assertEqual(len(calls), before)

    def test_live_validation_rejects_identity_head_tree_and_blob_mismatches(self):
        payload = sample()
        defaults = [
            {"id":456, "full_name":"example/project", "default_branch":"main", "archived":False},
            {"object":{"sha":BASE}}, {"tree":{"sha":"d"*40}},
            {"truncated":False, "tree":[{"path":".exocortex/scripts/example.py",
                                         "sha":"c"*40, "type":"blob", "mode":"100644"}]},
        ]
        variants = [(0, "id", 789), (0, "full_name", "example/other"),
                    (0, "default_branch", "other"), (0, "archived", True),
                    (1, "object", {"sha":"9"*40}), (3, "truncated", True)]
        for index, key, value in variants:
            replies = copy.deepcopy(defaults)
            replies[index][key] = value
            backend = GitHubBackend(lambda *_: replies.pop(0), lambda *_: True)
            with self.assertRaises(r.Blocked):
                backend.validate(payload["job"], payload["artifact"])
        for mutation in ("duplicate", "sha", "mode", "type"):
            replies = copy.deepcopy(defaults)
            row = replies[3]["tree"][0]
            if mutation == "duplicate":
                replies[3]["tree"].append(copy.deepcopy(row))
            else:
                row[mutation] = {"sha":"9"*40, "mode":"120000", "type":"tree"}[mutation]
            backend = GitHubBackend(lambda *_: replies.pop(0), lambda *_: True)
            with self.assertRaises(r.Blocked):
                backend.validate(payload["job"], payload["artifact"])
        replies = copy.deepcopy(defaults)
        GitHubBackend(lambda *_: replies.pop(0), lambda *_: True).validate(payload["job"], payload["artifact"])

    def test_commit_preserves_base_tree_and_uses_fixed_metadata(self):
        payload, calls = sample(), []
        def request(method, path, body=None):
            calls.append((method, path, body))
            return {"sha": "d"*40}
        backend = GitHubBackend(request, lambda *_: True)
        backend.trees[BASE] = "c"*40
        checks = []
        backend.commit(payload["job"], payload["artifact"], lambda: checks.append(True))
        tree = next(body for _, path, body in calls if path.endswith("/git/trees"))
        commit = next(body for _, path, body in calls if path.endswith("/git/commits"))
        self.assertEqual(tree["base_tree"], "c"*40)
        self.assertEqual(commit["parents"], [BASE])
        self.assertEqual(commit["author"], commit["committer"])
        self.assertIn("Agent: codex", commit["message"])
        self.assertEqual(len(checks), 3)
        self.assertFalse(any("/merges" in path or method in ("PATCH", "DELETE") for method, path, _ in calls))

    def test_closed_matching_pr_is_reused_foreign_pr_is_rejected(self):
        job = sample()["job"]
        branch = "codex/fictional"
        row = {"state": "closed", "html_url": "https://github.com/example/project/pull/1",
               "head": {"ref": branch, "sha": COMMIT, "repo": {"id": 456}},
               "base": {"ref": "main", "repo": {"id": 456}, "sha": BASE}, "body": "fixture marker"}
        backend = GitHubBackend(lambda *_: [row], lambda *_: True)
        self.assertEqual(backend.find_pr(job, branch, COMMIT, "fixture marker"),
                         {"url":row["html_url"], "base_sha":BASE})
        row["head"]["repo"]["id"] = 987
        with self.assertRaisesRegex(r.Blocked, "foreign_or_changed_pr"):
            backend.find_pr(job, branch, COMMIT, "fixture marker")


if __name__ == "__main__":
    unittest.main()
