"""Explicit, single-repository App credentials for the local pilot.

No credential discovery, persistence, logging, browser endpoint or hosted
isolation claim. The trusted caller supplies the key path and exact identities.
"""
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from pr_runner import Blocked, canonical
from pr_runner_transport import NoRedirect

PERMISSIONS = {"contents": "write", "metadata": "read", "pull_requests": "write"}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", value):
        raise Blocked("invalid_credential_binding")
    return value


def credential(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 8192
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", value)):
        raise Blocked("app_credentials_unavailable")
    return value


def encoded(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=")


class PrivateKeySigner:
    """POSIX local pilot only; opens an explicitly provisioned private file.

    OpenSSL reads the already validated descriptor. Private key bytes never
    enter Python, argv, environment, stdout or exception diagnostics.
    """
    def __init__(self, path, app_id, clock=time.time):
        self.path, self.app_id, self.clock = Path(path), identifier(app_id), clock

    def __call__(self):
        fd = None
        try:
            path = self.path
            if (not path.is_absolute() or path.resolve() != path
                    or not path.parent.is_dir()
                    or path.parent.stat().st_uid != os.getuid()
                    or stat.S_IMODE(path.parent.stat().st_mode) != 0o700):
                raise Blocked("unsafe_app_key")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            meta = os.fstat(fd)
            if (not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1
                    or meta.st_uid != os.getuid() or meta.st_mode & 0o077
                    or not 1 <= meta.st_size <= 16384):
                raise Blocked("unsafe_app_key")
            now = int(self.clock())
            message = b".".join((encoded(canonical({"alg": "RS256", "typ": "JWT"})),
                                 encoded(canonical({"iat": now-60, "exp": now+540,
                                                    "iss": self.app_id}))))
            result = subprocess.run(
                ["/usr/bin/openssl", "dgst", "-sha256", "-sign", "/dev/fd/"+str(fd),
                 "-passin", "pass:"],
                input=message, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                pass_fds=(fd,), timeout=10,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C", "OPENSSL_CONF": os.devnull})
            if result.returncode or not 256 <= len(result.stdout) <= 1024:
                raise Blocked("app_signing_failed")
            return (message+b"."+encoded(result.stdout)).decode("ascii")
        except Blocked:
            raise
        except Exception:
            raise Blocked("app_signing_failed") from None
        finally:
            if fd is not None:
                os.close(fd)


class InstallationCredentials:
    """Mint only an explicitly pinned repository's short-lived write token.

    Before minting, a metadata-only token verifies this installation contains
    exactly the pilot repository. That audit token is immediately revoked.
    Write tokens are requested with explicit repository_ids and permissions,
    verified through the provider's repository list, and kept only in memory.
    The caller must also enforce the runner's current signed grant/policy.
    """
    def __init__(self, signer, *, app_id, installation_id, account_id,
                 repository_id, repository, opener=None, clock=time.time):
        self.app_id = identifier(app_id)
        self.installation_id = identifier(installation_id)
        self.account_id = identifier(account_id)
        self.repository_id = identifier(repository_id)
        if (not callable(signer) or not isinstance(repository, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", repository)):
            raise Blocked("invalid_credential_binding")
        self.signer, self.repository, self.clock = signer, repository, clock
        self.opener = opener or build_opener(NoRedirect())
        self._token, self._expires = None, 0
        self._pending_revoke = {}
        self._lock = threading.Lock()

    def _request(self, method, path, token, body=None, status=200):
        allowed = {
            ("GET", "/app/installations/"+self.installation_id),
            ("POST", "/app/installations/"+self.installation_id+"/access_tokens"),
            ("GET", "/installation/repositories?per_page=2"),
            ("DELETE", "/installation/token"),
        }
        if (method, path) not in allowed:
            raise Blocked("unsupported_credential_operation")
        req = Request("https://api.github.com"+path, method=method,
                      data=canonical(body) if body is not None else None,
                      headers={"Authorization": "Bearer "+credential(token),
                               "Accept": "application/vnd.github+json",
                               "Content-Type": "application/json",
                               "X-GitHub-Api-Version": "2022-11-28",
                               "User-Agent": "Exocortex-Update-Manager"})
        try:
            with self.opener.open(req, timeout=20) as response:
                if response.status != status:
                    raise Blocked("credential_provider_failed")
                raw = response.read(1024*1024+1)
                if len(raw) > 1024*1024:
                    raise Blocked("credential_provider_failed")
                return json.loads(raw) if status != 204 else None
        except Blocked:
            raise
        except HTTPError as exc:
            # A rejected credential cannot authorize further API work.
            if method == "DELETE" and exc.code == 401:
                return None
            raise Blocked("credential_provider_failed") from None
        except (URLError, OSError, ValueError):
            raise Blocked("credential_provider_failed") from None

    def _drain_revocations(self):
        # Retain inaccessible tokens across ambiguous DELETE responses. Never
        # mint or return credentials until this pending cleanup is resolved.
        for token, expires in list(self._pending_revoke.items()):
            if expires is None or self.clock() < expires:
                self._request("DELETE", "/installation/token", token, status=204)
            del self._pending_revoke[token]

    def _retire(self, token, expires):
        self._pending_revoke[token] = expires
        self._drain_revocations()

    def _repositories(self, token):
        result = self._request("GET", "/installation/repositories?per_page=2", token)
        rows = result.get("repositories") if isinstance(result, dict) else None
        if (not isinstance(result, dict) or result.get("total_count") != 1 or not isinstance(rows, list) or len(rows) != 1
                or not isinstance(rows[0], dict)
                or str(rows[0].get("id")) != self.repository_id
                or rows[0].get("full_name") != self.repository
                or rows[0].get("private") is not True):
            raise Blocked("installation_repository_mismatch")

    def _mint(self, jwt, permissions, repository_ids=None):
        body = {"permissions": permissions}
        if repository_ids is not None:
            body["repository_ids"] = repository_ids
        result = self._request("POST", "/app/installations/"+self.installation_id+
                               "/access_tokens", jwt, body, status=201)
        if not isinstance(result, dict):
            raise Blocked("invalid_installation_token")
        token = credential(result.get("token"))
        expires = None
        try:
            expires = datetime.strptime(result["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            if (result.get("permissions") != permissions
                    or not self.clock()+60 < expires <= self.clock()+3660):
                raise Blocked("invalid_installation_token")
        except Exception:
            self._retire(token, None)
            raise Blocked("invalid_installation_token") from None
        return token, expires

    def __call__(self):
        with self._lock:
            self._drain_revocations()
            if self._token and self.clock() < self._expires-60:
                return self._token
            old_token, old_expires = self._token, self._expires
            self._token, self._expires = None, 0
            if old_token:
                self._retire(old_token, old_expires)
            jwt = self.signer()
            installation = self._request("GET", "/app/installations/"+self.installation_id, jwt)
            if (not isinstance(installation, dict)
                    or str(installation.get("id")) != self.installation_id
                    or str(installation.get("app_id")) != self.app_id
                    or not isinstance(installation.get("account"), dict)
                    or str(installation["account"].get("id")) != self.account_id
                    or installation.get("repository_selection") != "selected"
                    or installation.get("permissions") != PERMISSIONS
                    or installation.get("suspended_at") is not None):
                raise Blocked("installation_grant_mismatch")
            audit, audit_expires = self._mint(jwt, {"metadata": "read"})
            try:
                self._repositories(audit)
            finally:
                self._retire(audit, audit_expires)
            token, expires = self._mint(jwt, PERMISSIONS, [int(self.repository_id)])
            try:
                self._repositories(token)
            except Exception:
                self._retire(token, expires)
                raise Blocked("installation_repository_mismatch") from None
            self._token, self._expires = token, expires
            return token

    def revoke(self):
        """End a pilot session without leaving its write token active."""
        with self._lock:
            token, expires = self._token, self._expires
            self._token, self._expires = None, 0
            if token:
                self._pending_revoke[token] = expires
            self._drain_revocations()
