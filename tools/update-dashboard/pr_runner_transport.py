"""Bounded GitHub transport with explicit injected installation-token supplier.

No environment/CLI/keychain credential discovery. No provider response bodies
are returned on failure. The publisher must run separately from preparation.
"""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from pr_runner import Blocked, canonical


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Blocked("provider_redirect_rejected")


class GitHubTransport:
    def __init__(self, installation_token, opener=None):
        if not callable(installation_token):
            raise Blocked("installation_credentials_unavailable")
        self.installation_token = installation_token
        self.opener = opener or build_opener(NoRedirect())

    def __call__(self, method, path, body=None):
        # Only endpoints used by the publisher. No arbitrary URL, ref PATCH,
        # repository settings, workflow dispatch, delete, or merge operation.
        common = r"/repos/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}"
        get = (r"/repositories/[1-9][0-9]{0,19}|" + common +
               r"/(?:git/(?:ref/heads/[A-Za-z0-9_%./-]+|commits/[a-f0-9]{40}|trees/[a-f0-9]{40}\?recursive=1)"
               r"|pulls\?[A-Za-z0-9_%=&+.-]+)")
        post = common + r"/(?:git/(?:blobs|trees|commits|refs)|pulls)"
        if (method not in ("GET", "POST") or
                not re.fullmatch(get if method == "GET" else post, path)):
            raise Blocked("unsupported_provider_operation")
        if method == "GET" and body is not None:
            raise Blocked("invalid_provider_body")
        data = canonical(body) if body is not None else None
        if data is not None and len(data) > 4*1024*1024:
            raise Blocked("provider_request_too_large")
        token = self.installation_token()
        if not isinstance(token, str) or not token or len(token) > 8192 or "\r" in token or "\n" in token:
            raise Blocked("installation_credentials_unavailable")
        req = Request("https://api.github.com"+path, data=data, method=method,
                      headers={"Authorization": "Bearer "+token, "Accept": "application/vnd.github+json",
                               "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28",
                               "User-Agent": "Exocortex-Update-Manager"})
        try:
            with self.opener.open(req, timeout=20) as response:
                raw = response.read(8*1024*1024+1)
                if len(raw) > 8*1024*1024:
                    raise Blocked("provider_response_too_large")
                return json.loads(raw)
        except HTTPError as exc:
            # Missing branch is useful only after the caller has validated
            # current repository access/identity. Other 404s are not absence.
            if exc.code == 404 and method == "GET" and "/git/ref/heads/codex%2Fexocortex-update-" in path:
                return None
            raise Blocked("provider_request_failed") from None
        except (URLError, OSError, ValueError):
            raise Blocked("provider_request_failed") from None
