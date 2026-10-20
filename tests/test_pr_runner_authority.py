"""Private authority records are real files; release network I/O is mocked."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools/update-dashboard"))
import pr_runner as runner
import pr_runner_authority as authority
from test_pr_runner import sample, NOW, GRANT_KEY


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.root.chmod(0o700)
        self.policy_root = self.root/"policy"/"456"
        self.policy_path = self.policy_root/".exocortex/local/update-policy.json"
        self.policy_path.parent.mkdir(parents=True)
        self.policy_path.write_text('{"mode":"standard","protected_paths":[]}\n')
        self.source = self.root/"release"
        self.source.mkdir()
        (self.source/"FILEMODES").write_text("0644  fictional\n")
        self.payload = sample()
        self.job = self.payload["job"]
        self.job["policy"]["sha256"] = hashlib.sha256(self.policy_path.read_bytes()).hexdigest()
        self.job["release"]["modes_sha256"] = hashlib.sha256((self.source/"FILEMODES").read_bytes()).hexdigest()
        self.record = {key:self.job[key] for key in
                       ("account","installation","grant_epoch","repository_id","repository")}
        self.record.update(enabled=True, expires_at=NOW+600, policy_revision=1,
                           policy_directory=str(self.policy_root),
                           source={"path":str(self.source),"manifest_sha256":"f"*64,
                                   "release":{"repository":"example/template","tag":"v4.0.0",
                                              "commit":"e"*40,"asset":str(self.source/"SHA256SUMS")}})
        self.path = self.root/"456.json"
        self.write()
        self.check = authority.RepositoryAuthority(self.root, GRANT_KEY, lambda:NOW)

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.path.write_text(json.dumps(runner.sign("runner-control", self.record, GRANT_KEY)))
        self.path.chmod(0o600)

    def invoke(self):
        with patch.object(authority.updater, "verify_source", return_value=self.source) as verify:
            result = self.check(self.job, self.payload["artifact"])
            verify.assert_called_once_with(self.record["source"], apply=True)
            return result

    def test_explicit_bound_policy_and_release_accepted(self):
        self.assertTrue(self.invoke())

    def test_object_checks_reread_policy_without_repeating_attestation(self):
        with patch.object(authority.updater, "verify_source", return_value=self.source) as verify:
            self.assertTrue(self.check(self.job, self.payload["artifact"]))
            for _ in range(100):
                self.assertTrue(self.check.recheck(self.job, self.payload["artifact"]))
            self.assertEqual(verify.call_count, 1)
            self.record["enabled"] = False
            self.write()
            with self.assertRaisesRegex(runner.Blocked, "grant_revoked"):
                self.check.recheck(self.job, self.payload["artifact"])
            self.assertEqual(verify.call_count, 1)

    def test_object_check_requires_prior_attestation_of_exact_record(self):
        with self.assertRaisesRegex(runner.Blocked, "live_authority_rejected"):
            self.check.recheck(self.job, self.payload["artifact"])
        self.assertTrue(self.invoke())
        self.record["source"]["manifest_sha256"] = "9"*64
        self.write()
        with self.assertRaisesRegex(runner.Blocked, "live_authority_rejected"):
            self.check.recheck(self.job, self.payload["artifact"])

    def test_revocation_and_epoch_change_are_reread(self):
        self.assertTrue(self.invoke())
        for field,value in (("enabled",False),("grant_epoch","5"),("installation","789"),
                            ("account","another-owner"),("expires_at",NOW)):
            with self.subTest(field=field):
                saved = copy.deepcopy(self.record)
                self.record[field] = value
                self.write()
                with self.assertRaises(runner.Blocked):
                    self.invoke()
                self.record = saved

    def test_missing_policy_never_inherits_standard_default(self):
        self.policy_path.unlink()
        with self.assertRaisesRegex(runner.Blocked, "policy_changed"):
            self.invoke()

    def test_changed_policy_or_revision_blocks(self):
        self.policy_path.write_text('{"mode":"excluded","protected_paths":[]}\n')
        with self.assertRaisesRegex(runner.Blocked, "policy_changed"):
            self.invoke()
        self.policy_path.write_text('{"mode":"standard","protected_paths":[]}\n')
        self.record["policy_revision"] = 2
        self.write()
        with self.assertRaisesRegex(runner.Blocked, "policy_changed"):
            self.invoke()

    def test_protected_paths_block_even_with_matching_digest(self):
        self.policy_path.write_text('{"mode":"standard","protected_paths":["AGENTS.md"]}\n')
        self.job["policy"]["sha256"] = hashlib.sha256(self.policy_path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(runner.Blocked, "policy_changed"):
            self.invoke()

    def test_release_mismatch_and_unpublished_source_block(self):
        self.job["release"]["commit"] = "9"*40
        with self.assertRaisesRegex(runner.Blocked, "release_revoked"):
            self.invoke()
        with patch.object(authority.updater, "verify_source",
                          side_effect=ValueError("private provider diagnostic")):
            with self.assertRaisesRegex(runner.Blocked, "^live_authority_rejected$"):
                self.check(self.job, self.payload["artifact"])

    def test_foreign_policy_directory_is_rejected(self):
        self.record["policy_directory"] = str(self.root.parent)
        self.write()
        with self.assertRaisesRegex(runner.Blocked, "unsafe_authority_store"):
            self.invoke()

    def test_tampering_unsafe_modes_and_links_fail_closed(self):
        value = json.loads(self.path.read_text())
        value["payload"]["enabled"] = False
        self.path.write_text(json.dumps(value))
        with self.assertRaisesRegex(runner.Blocked, "invalid_signature"):
            self.invoke()
        self.write()
        self.path.chmod(0o644)
        with self.assertRaisesRegex(runner.Blocked, "unsafe_authority_store"):
            self.invoke()
        self.path.unlink()
        self.path.symlink_to(self.policy_path)
        with self.assertRaisesRegex(runner.Blocked, "unsafe_authority_store"):
            self.invoke()


if __name__ == "__main__":
    unittest.main()
