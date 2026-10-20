"""Preparation boundary tests; release and updater I/O are explicitly mocked."""
import base64
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools/update-dashboard"))
import pr_runner as r
import pr_runner_prepare as prep


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root/"target"
        self.source = self.root/"source"
        self.source.mkdir()
        (self.source/"FILEMODES").write_text("0644  fixture\n")
        self.path = ".exocortex/scripts/fixture.py"
        destination = self.target/self.path
        destination.parent.mkdir(parents=True)
        destination.write_text("# fictional\n")
        destination.chmod(0o644)
        self.binding = {"head":"a"*40, "branch":"fixture", "project_id":"fictional", "checkout_id":"fictional"}
        self.current = {"binding":self.binding, "customization":{"requires_review":False}}
        applied = {"changed_paths":[self.path], "reconciliation_required":False}
        self.row = {"id":"target-1", "path":str(self.target), "state":"applied",
                    "initial":{"binding":self.binding},
                    "receipt":{"changed_paths":[self.path], "apply":applied,
                               "verification":{"changed_paths":[], "reconciliation_required":False}}}
        self.plan = {"source":{"path":str(self.source), "manifest_sha256":"f"*64,
                               "release":{"repository":"example/template", "tag":"v4.0.0",
                                          "commit":"e"*40, "asset":"fictional"}},
                     "targets":[self.row], "backup_root":str(self.root/"backup")}
        self.job = {"version":r.VERSION, "account":"owner-1", "installation":"123",
                    "grant_epoch":"1", "repository_id":"456", "repository":"example/project",
                    "base_branch":"main", "base_sha":"a"*40,
                    "release":{"repository":"example/template", "tag":"v4.0.0", "commit":"e"*40,
                               "manifest_sha256":"f"*64,
                               "modes_sha256":hashlib.sha256((self.source/"FILEMODES").read_bytes()).hexdigest()},
                    "policy":{"revision":1, "sha256":"2"*64, "declaration":"explicit", "treatment":"standard"},
                    "plan_sha256":r.digest(self.plan), "artifact_sha256":"0"*64,
                    "created_at":1800000000, "expires_at":1800000300}
        self.key = b"fictional-preparation-key"*2

    def tearDown(self):
        self.tmp.cleanup()

    def prepare(self, verify=None, invoke=None, target=None):
        with patch.object(prep.updater, "load", return_value=self.plan), \
             patch.object(prep.updater, "verify_source", side_effect=verify or (lambda *a, **k: self.source)) as release, \
             patch.object(prep.updater, "target", side_effect=target or (lambda *a: self.current)), \
             patch.object(prep.updater, "candidate_hashes", return_value={}), \
             patch.object(prep.updater.state, "git", return_value="https://github.com/example/project"), \
             patch.object(prep.updater, "invoke", side_effect=invoke or (lambda *a: (0, "fixture"))) as updater, \
             patch.object(prep.updater, "receipt", return_value={"changed_paths":[], "reconciliation_required":False}), \
             patch.object(prep, "git_blob", return_value="c"*40):
            result = prep.prepare(self.root, "fixture-plan", "target-1", self.job, self.key, 1800000000)
            release.assert_called_once_with(self.plan["source"], apply=True)
            updater.assert_called_once()
            return result

    def test_verified_result_freezes_exact_effect_only(self):
        (self.target/"unrelated.txt").write_text("not included")
        packet = self.prepare()
        payload = r.verify(packet, "prepared-update", self.key)
        r.validate_artifact(payload["artifact"], payload["job"])
        self.assertEqual([x["path"] for x in payload["artifact"]["changes"]], [self.path])
        self.assertEqual(base64.b64decode(payload["artifact"]["changes"][0]["content"]), b"# fictional\n")

    def test_preview_cannot_become_signed_apply(self):
        self.row["state"] = "ready"
        with self.assertRaisesRegex(r.Blocked, "guarded_apply_required"):
            self.prepare()

    def test_failed_release_authentication_produces_no_packet(self):
        def reject(*a, **k):
            raise prep.updater.UpdateError("No published attested release")
        with self.assertRaises(prep.updater.UpdateError):
            self.prepare(verify=reject)

    def test_changed_checkout_and_plan_are_rejected(self):
        self.current = copy.deepcopy(self.current)
        self.current["binding"]["head"] = "9"*40
        with self.assertRaisesRegex(r.Blocked, "checkout_changed"):
            self.prepare()
        self.current["binding"] = self.binding
        self.job["plan_sha256"] = "8"*64
        with self.assertRaisesRegex(r.Blocked, "plan_binding"):
            self.prepare()

    def test_drift_during_freeze_rejected(self):
        sequence = [self.current, {**self.current, "changed":True}]
        with self.assertRaisesRegex(r.Blocked, "target_changed_during_freeze"):
            self.prepare(target=lambda *a: sequence.pop(0))

    def test_failed_post_apply_recheck_produces_no_packet(self):
        with self.assertRaisesRegex(r.Blocked, "post_apply_recheck_failed"):
            self.prepare(invoke=lambda *a: (1, "failure"))

    def test_project_owned_gitignore_cannot_be_frozen_into_artifact(self):
        # Even if a dry-run says zero remaining changes, owner additions to
        # .gitignore are not included in the coordinator's managed snapshot.
        (self.target/".gitignore").write_text("# unrelated owner rule\nprivate-local/\n")
        self.row["receipt"]["changed_paths"].append(".gitignore")
        self.row["receipt"]["apply"]["changed_paths"].append(".gitignore")
        self.row["receipt"]["changed_paths"].sort()
        self.row["receipt"]["apply"]["changed_paths"].sort()
        self.job["plan_sha256"] = r.digest(self.plan)
        with self.assertRaisesRegex(r.Blocked, "protected_or_unsupported"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
