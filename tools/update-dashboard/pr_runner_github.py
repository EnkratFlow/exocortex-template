"""Fixed GitHub Git-data API backend; never executes target repository code.

`request(method, path, body=None)` is an installation-scoped transport.
`authority(job, artifact)` must independently authenticate the published release,
current account/App installation/grant epoch, and explicit repository policy.
It must reject missing declarations and any protected-path intersection. A
browser preference or a signed preview is not that authority. Neither dependency
has a default, so this module cannot silently use ambient CLI credentials.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import quote, urlencode
from pr_runner import Blocked, token, SHA, digest


class GitHubBackend:
    def __init__(self, request, authority):
        if not callable(request) or not callable(authority):
            raise Blocked("runner_trust_not_configured")
        self.request, self.authority = request, authority
        self.trees = {}
        self.validated = set()

    def _path(self, job, suffix):
        return "/repos/" + job["repository"] + suffix

    def observe(self, job):
        """Recovery read only: authenticate current read access + immutable repo."""
        repo = self.request("GET", "/repositories/" + job["repository_id"])
        if str(repo.get("id")) != job["repository_id"] or repo.get("full_name") != job["repository"]:
            raise Blocked("repository_identity_changed")

    def validate(self, job, artifact):
        # Controller must check release attestations and policy against its own
        # records, not against fields echoed by the untrusted request.
        if self.authority(job, artifact) is not True:
            raise Blocked("live_authority_rejected")
        repo = self.request("GET", "/repositories/" + job["repository_id"])
        if (str(repo.get("id")) != job["repository_id"] or
                repo.get("full_name") != job["repository"] or
                repo.get("default_branch") != job["base_branch"] or
                repo.get("archived") is not False or repo.get("disabled") is True):
            raise Blocked("repository_identity_changed")
        head = self.request("GET", self._path(job, "/git/ref/heads/" + quote(job["base_branch"], safe="")))
        if head.get("object", {}).get("sha") != job["base_sha"]:
            raise Blocked("base_changed")
        commit = self.request("GET", self._path(job, "/git/commits/" + job["base_sha"]))
        tree_sha = commit.get("tree", {}).get("sha")
        token(tree_sha, SHA.pattern, "invalid_base_tree")
        tree = self.request("GET", self._path(job, "/git/trees/" + tree_sha + "?recursive=1"))
        if tree.get("truncated") is not False or not isinstance(tree.get("tree"), list) or len(tree["tree"]) > 20000:
            raise Blocked("incomplete_source_tree")
        entries = {r.get("path"): r for r in tree["tree"]}
        if len(entries) != len(tree["tree"]):
            raise Blocked("ambiguous_source_tree")
        for change in artifact["changes"]:
            entry = entries.get(change["path"])
            if (entry.get("sha") if entry else None) != change["before_sha"]:
                raise Blocked("source_blob_changed")
            if entry and (entry.get("type") != "blob" or entry.get("mode") not in ("100644", "100755")):
                raise Blocked("unsupported_source_type")
        self.trees[job["base_sha"]] = tree_sha
        self.validated.add(digest({"job": job, "artifact": artifact}))

    def validate_objects(self, job, artifact):
        """Only content-addressed objects: retain cheap current policy checks.

        Full live attestation/tree validation is still mandatory before any
        branch or PR effect. Nothing in this fast path permits a ref mutation.
        """
        if digest({"job": job, "artifact": artifact}) not in self.validated:
            raise Blocked("live_authority_rejected")
        recheck = getattr(self.authority, "recheck", self.authority)
        if recheck(job, artifact) is not True:
            raise Blocked("live_authority_rejected")

    def commit(self, job, artifact, before_write):
        # Git objects are content-addressed; fixed metadata makes object retries
        # deterministic, including after an interrupted response.
        tree_rows = []
        for change in artifact["changes"]:
            if change["content"] is None:
                tree_rows.append({"path": change["path"], "mode": "100644", "type": "blob", "sha": None})
            else:
                before_write()
                blob = self.request("POST", self._path(job, "/git/blobs"),
                                    {"content": change["content"], "encoding": "base64"})
                sha = token(blob.get("sha"), SHA.pattern, "invalid_blob")
                tree_rows.append({"path": change["path"], "mode": change["mode"], "type": "blob", "sha": sha})
        before_write()
        tree = self.request("POST", self._path(job, "/git/trees"),
                            {"base_tree": self.trees[job["base_sha"]], "tree": tree_rows})
        tree_sha = token(tree.get("sha"), SHA.pattern, "invalid_tree")
        date = datetime.fromtimestamp(job["created_at"], timezone.utc).isoformat()
        identity = {"name": "Exocortex Update Manager", "email": "update-manager@example.invalid", "date": date}
        before_write()
        commit = self.request("POST", self._path(job, "/git/commits"),
                              {"message": "Update Exocortex to " + job["release"]["tag"] +
                               "\n\nArtifact: " + job["artifact_sha256"] + "\n\nAgent: codex\n",
                               "tree": tree_sha, "parents": [job["base_sha"]],
                               "author": identity, "committer": identity})
        return token(commit.get("sha"), SHA.pattern, "invalid_commit")

    def branch(self, job, name):
        row = self.request("GET", self._path(job, "/git/ref/heads/" + quote(name, safe="")))
        if row is None:  # Transport may return None ONLY for an authenticated 404.
            return None
        if row.get("ref") != "refs/heads/" + name or row.get("object", {}).get("type") != "commit":
            raise Blocked("invalid_branch_response")
        return token(row["object"].get("sha"), SHA.pattern, "invalid_branch_commit")

    def create_branch(self, job, name, commit):
        # No PATCH/ref update endpoint: existing refs are never overwritten.
        self.request("POST", self._path(job, "/git/refs"), {"ref": "refs/heads/" + name, "sha": commit})

    def find_pr(self, job, branch, commit, marker):
        matches = []
        owner = job["repository"].split("/")[0]
        for page in range(1, 11):
            query = urlencode({"state": "all", "head": owner+":"+branch,
                               "base": job["base_branch"], "per_page": 100, "page": page})
            rows = self.request("GET", self._path(job, "/pulls?"+query))
            if not isinstance(rows, list) or len(rows) > 100:
                raise Blocked("invalid_pr_inventory")
            for row in rows:
                head, base = row.get("head", {}), row.get("base", {})
                if (head.get("ref") != branch or head.get("sha") != commit or
                        str((head.get("repo") or {}).get("id")) != job["repository_id"] or
                        base.get("ref") != job["base_branch"] or
                        str((base.get("repo") or {}).get("id")) != job["repository_id"] or
                        marker not in (row.get("body") or "")):
                    raise Blocked("foreign_or_changed_pr")
                matches.append({"url":row.get("html_url"), "base_sha":base.get("sha")})
            if len(rows) < 100:
                break
        else:
            raise Blocked("pr_inventory_truncated")
        if len(matches) > 1:
            raise Blocked("ambiguous_pr")
        return matches[0] if matches else None

    def create_pr(self, job, branch, marker):
        self.request("POST", self._path(job, "/pulls"),
                     {"title": "Update Exocortex to " + job["release"]["tag"],
                      "head": branch, "base": job["base_branch"], "draft": True,
                      "maintainer_can_modify": False,
                      "body": "Prepared from an exact template release and verified update artifact. "
                              "Review the diff and repository checks before merging. "
                              "This does not deploy the application.\n\n"
                              "Recovery before merge: close this pull request; the default branch is unchanged. "
                              "After merge, use a separately reviewed revert through the project SDLC.\n\n" + marker})
