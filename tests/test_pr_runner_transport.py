import io
from pathlib import Path
import sys
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools/update-dashboard"))
from pr_runner import Blocked
from pr_runner_transport import GitHubTransport, NoRedirect


class TransportTests(unittest.TestCase):
    def test_fixed_host_auth_header_and_bound(self):
        class Opener:
            def open(self, req, timeout):
                self.req, self.timeout = req, timeout
                return io.BytesIO(b'{"id":123}')
        opener = Opener()
        transport = GitHubTransport(lambda: "fictional-token", opener)
        self.assertEqual(transport("GET", "/repositories/123"), {"id":123})
        self.assertEqual(opener.req.full_url, "https://api.github.com/repositories/123")
        self.assertEqual(opener.timeout, 20)
        self.assertEqual(opener.req.get_header("Authorization"), "Bearer fictional-token")

    def test_merge_arbitrary_url_and_ref_update_are_unavailable(self):
        transport = GitHubTransport(lambda: self.fail("credentials must not be requested"))
        for method, path in (("PUT", "/repos/example/project/pulls/1/merge"),
                             ("PATCH", "/repos/example/project/git/refs/heads/main"),
                             ("POST", "https://example.invalid/collect"),
                             ("GET", "/repos/../project/git/commits/"+"a"*40)):
            with self.assertRaises(Blocked):
                transport(method, path)

    def test_redirect_and_provider_diagnostics_never_escape(self):
        with self.assertRaises(Blocked):
            NoRedirect().redirect_request(None,None,302,"",{},"https://example.invalid")
        class Opener:
            def open(self, req, timeout):
                raise HTTPError(req.full_url, 403, "sensitive diagnostic", {}, io.BytesIO(b"sensitive-body"))
        with self.assertRaisesRegex(Blocked, "^provider_request_failed$"):
            GitHubTransport(lambda: "fictional-token", Opener())("GET", "/repositories/123")

    def test_response_size_limit(self):
        class Opener:
            def open(self, req, timeout):
                return io.BytesIO(b"x"*(8*1024*1024+1))
        with self.assertRaises(Blocked):
            GitHubTransport(lambda: "fictional-token", Opener())("GET", "/repositories/123")

    def test_only_job_branch_404_can_mean_absent(self):
        class Opener:
            def open(self, req, timeout):
                raise HTTPError(req.full_url,404,"not found",{},io.BytesIO())
        transport = GitHubTransport(lambda: "fictional-token", Opener())
        self.assertIsNone(transport("GET", "/repos/example/project/git/ref/heads/codex%2Fexocortex-update-"+"a"*64))
        with self.assertRaises(Blocked):
            transport("GET", "/repositories/123")


if __name__ == "__main__":
    unittest.main()
