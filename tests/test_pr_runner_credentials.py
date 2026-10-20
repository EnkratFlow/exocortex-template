"""Fictional provider responses; real disposable RSA signing, no live keys."""
import base64
import copy
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools/update-dashboard"))
from pr_runner import Blocked
from pr_runner_credentials import InstallationCredentials, PERMISSIONS, PrivateKeySigner

NOW = 1800000000


class Response(io.BytesIO):
    def __init__(self, payload, status):
        super().__init__(json.dumps(payload).encode())
        self.status = status


class Provider:
    def __init__(self):
        self.calls = []
        self.installation = {"id": 123, "app_id": 456, "account": {"id": 789},
                             "repository_selection": "selected", "permissions": PERMISSIONS,
                             "suspended_at": None}
        self.repositories = {"total_count": 1, "repositories": [
            {"id": 321, "full_name": "Example/Pilot", "private": True}]}
        self.minted_permissions = None
        self.expires = NOW+3600
        self.fail_delete = False

    def open(self, req, timeout):
        self.calls.append(req)
        assert timeout == 20
        if req.method == "DELETE":
            if self.fail_delete:
                raise HTTPError(req.full_url, 503, "fictional failure", {}, io.BytesIO())
            return Response(None, 204)
        if req.full_url.endswith("/access_tokens"):
            body = json.loads(req.data)
            permissions = self.minted_permissions or body["permissions"]
            return Response({"token": "fictional-audit" if len(body["permissions"]) == 1 else "fictional-write",
                             "permissions": permissions,
                             "expires_at": datetime.fromtimestamp(self.expires, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, 201)
        if req.full_url.endswith("/repositories?per_page=2"):
            return Response(self.repositories, 200)
        return Response(self.installation, 200)


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.provider = Provider()
        self.now = NOW
        self.broker = InstallationCredentials(lambda: "fictional-jwt", app_id="456",
            installation_id="123", account_id="789", repository_id="321",
            repository="Example/Pilot", opener=self.provider, clock=lambda: self.now)

    def test_exact_scope_metadata_audit_cache_and_revoke(self):
        self.assertEqual(self.broker(), "fictional-write")
        calls = self.provider.calls
        self.assertEqual(len(calls), 6)
        self.assertEqual(json.loads(calls[1].data), {"permissions": {"metadata": "read"}})
        self.assertEqual(calls[3].method, "DELETE")
        self.assertEqual(calls[3].get_header("Authorization"), "Bearer fictional-audit")
        self.assertEqual(json.loads(calls[4].data),
                         {"permissions": PERMISSIONS, "repository_ids": [321]})
        self.assertTrue(all(c.full_url.startswith("https://api.github.com/") for c in calls))
        self.broker()
        self.assertEqual(len(calls), 6)
        self.broker.revoke()
        self.assertIsNone(self.broker._token)
        self.assertEqual(calls[-1].get_header("Authorization"), "Bearer fictional-write")

    def test_installation_binding_and_permission_drift_block_before_mint(self):
        for field, value in (("id", 999), ("app_id", 999), ("account", {"id": 999}),
                             ("account", None), ("repository_selection", "all"),
                             ("permissions", dict(PERMISSIONS, workflows="write")),
                             ("suspended_at", "2027-01-01T00:00:00Z")):
            with self.subTest(field=field):
                original = self.provider.installation
                self.provider.installation = dict(original, **{field: value})
                with self.assertRaisesRegex(Blocked, "installation_grant_mismatch"):
                    self.broker()
                self.assertFalse(any(r.method == "POST" for r in self.provider.calls))
                self.provider.installation = original
                self.provider.calls.clear()

    def test_extra_or_wrong_repository_never_receives_write_token(self):
        original = copy.deepcopy(self.provider.repositories)
        variants = [{"total_count": 2, "repositories": original["repositories"]*2},
                    {"total_count": 1, "repositories": [dict(original["repositories"][0], id=999)]},
                    {"total_count": 1, "repositories": [dict(original["repositories"][0], full_name="Example/Other")]},
                    {"total_count": 1, "repositories": [dict(original["repositories"][0], private=False)]},
                    [], {}]
        for value in variants:
            with self.subTest(value=value):
                self.provider.repositories = value
                with self.assertRaises(Blocked):
                    self.broker()
                posts = [r for r in self.provider.calls if r.method == "POST"]
                self.assertEqual(len(posts), 1)
                self.assertEqual(self.provider.calls[-1].method, "DELETE")
                self.assertIsNone(self.broker._token)
                self.provider.calls.clear()

    def test_expiry_and_unexpected_token_permissions_are_revoked(self):
        for expires in (NOW-1, NOW+30, NOW+7200):
            self.provider.expires = expires
            with self.assertRaisesRegex(Blocked, "invalid_installation_token"):
                self.broker()
            self.assertEqual(self.provider.calls[-1].method, "DELETE")
        self.provider.expires = NOW+3600
        self.provider.minted_permissions = dict(PERMISSIONS, workflows="write")
        with self.assertRaisesRegex(Blocked, "invalid_installation_token"):
            self.broker()
        self.assertEqual(self.provider.calls[-1].method, "DELETE")

    def test_expiring_token_rechecks_live_installation(self):
        self.broker()
        self.now += 3550
        self.provider.installation["repository_selection"] = "all"
        with self.assertRaisesRegex(Blocked, "installation_grant_mismatch"):
            self.broker()
        self.assertIsNone(self.broker._token)

    def test_failed_revocation_is_retained_but_not_reused_or_replaced(self):
        self.broker()
        self.provider.calls.clear()
        self.provider.fail_delete = True
        with self.assertRaises(Blocked):
            self.broker.revoke()
        self.assertIsNone(self.broker._token)
        self.assertEqual(self.broker._pending_revoke, {"fictional-write": NOW+3600})
        with self.assertRaises(Blocked):
            self.broker()
        self.assertEqual([r.method for r in self.provider.calls], ["DELETE", "DELETE"])
        self.provider.fail_delete = False
        self.broker.revoke()
        self.assertEqual(self.broker._pending_revoke, {})
        self.assertIsNone(self.broker._token)

    def test_refresh_revokes_old_token_before_any_new_mint(self):
        self.broker()
        self.provider.calls.clear()
        self.now += 3550
        self.provider.expires = self.now+3600
        self.broker()
        self.assertEqual(self.provider.calls[0].method, "DELETE")
        self.assertEqual(self.provider.calls[0].get_header("Authorization"), "Bearer fictional-write")
        self.assertEqual(self.provider.calls[1].method, "GET")

    def test_failed_audit_revocation_blocks_write_token_minting(self):
        self.provider.fail_delete = True
        with self.assertRaises(Blocked):
            self.broker()
        self.assertEqual(self.broker._pending_revoke, {"fictional-audit": NOW+3600})
        before = len(self.provider.calls)
        with self.assertRaises(Blocked):
            self.broker()
        self.assertEqual([r.method for r in self.provider.calls[before:]], ["DELETE"])
        self.assertEqual(len([r for r in self.provider.calls if r.method == "POST"]), 1)

    def test_provider_diagnostics_are_not_exposed(self):
        class Failed:
            def open(self, req, timeout):
                raise HTTPError(req.full_url, 403, "fictional-sensitive-detail", {}, io.BytesIO(b"fictional-secret"))
        self.broker.opener = Failed()
        with self.assertRaisesRegex(Blocked, "^credential_provider_failed$"):
            self.broker()

    def test_binding_validation_precedes_credentials(self):
        for field, value in (("app_id", "../456"), ("repository_id", "0"),
                             ("repository", "Example/../Other")):
            args = dict(app_id="456", installation_id="123", account_id="789",
                        repository_id="321", repository="Example/Pilot")
            args[field] = value
            with self.assertRaises(Blocked):
                InstallationCredentials(lambda: self.fail("must not sign"), **args)


@unittest.skipUnless(os.name == "posix" and Path("/usr/bin/openssl").exists(), "POSIX OpenSSL signer")
class SignerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name).resolve()
        cls.root.chmod(0o700)
        cls.key = cls.root/"fixture.pem"
        subprocess.run(["/usr/bin/openssl", "genrsa", "-out", str(cls.key), "2048"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        cls.key.chmod(0o600)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_real_rs256_signature_and_bounded_claims(self):
        jwt = PrivateKeySigner(self.key, "456", clock=lambda: NOW)()
        head, claims, signature = jwt.split(".")
        def decode(value):
            return base64.urlsafe_b64decode(value+"="*(-len(value) % 4))
        self.assertEqual(json.loads(decode(head)), {"alg": "RS256", "typ": "JWT"})
        self.assertEqual(json.loads(decode(claims)), {"iat": NOW-60, "exp": NOW+540, "iss": "456"})
        public = self.root/"public.pem"
        subprocess.run(["/usr/bin/openssl", "rsa", "-in", str(self.key), "-pubout", "-out", str(public)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        sig = self.root/"signature.bin"
        sig.write_bytes(decode(signature))
        checked = subprocess.run(["/usr/bin/openssl", "dgst", "-sha256", "-verify", str(public),
                                  "-signature", str(sig)], input=(head+"."+claims).encode(),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(checked.returncode, 0)

    def test_unsafe_mode_symlink_and_hardlink_rejected(self):
        self.key.chmod(0o644)
        try:
            with self.assertRaisesRegex(Blocked, "unsafe_app_key"):
                PrivateKeySigner(self.key, "456")()
        finally:
            self.key.chmod(0o600)
        link = self.root/"link.pem"
        link.symlink_to(self.key)
        try:
            with self.assertRaisesRegex(Blocked, "unsafe_app_key"):
                PrivateKeySigner(link, "456")()
        finally:
            link.unlink()
        os.link(self.key, link)
        try:
            with self.assertRaisesRegex(Blocked, "unsafe_app_key"):
                PrivateKeySigner(self.key, "456")()
        finally:
            link.unlink()


if __name__ == "__main__":
    unittest.main()
