"""Freeze a publication artifact from a successful *existing* guarded update.

Runs in the trusted preparation process, without a repository write token.
Imports the coordinator from this trusted application tree, never the target.
Does not create capabilities, change a policy, or turn a preview into an apply.
"""
from pathlib import Path
import base64
import hashlib
import os
import stat
import subprocess
import sys

from pr_runner import Blocked, allowed_path, canonical, digest, sign, validate_job, validate_artifact

TRUSTED_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TRUSTED_ROOT/".exocortex/scripts"))
import update_selected as updater


def git_blob(root, commit, path):
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    args = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath="+os.devnull,
            "-C", str(root), "ls-tree", "-z", commit, "--", path]
    result = subprocess.run(args, env=env, capture_output=True, timeout=20)
    if result.returncode:
        raise Blocked("source_tree_unavailable")
    if not result.stdout:
        return None
    entries = result.stdout.rstrip(b"\0").split(b"\0")
    if len(entries) != 1:
        raise Blocked("ambiguous_source_path")
    meta, name = entries[0].split(b"\t", 1)
    mode, kind, sha = meta.decode().split()
    if name.decode() != path or kind != "blob" or mode not in ("100644", "100755"):
        raise Blocked("unsupported_source_path")
    return sha


def prepare(controller, plan_id, target_id, job, key, now):
    """Return a signed prepared-update packet; caller stores it privately.

    `job` is the controller's authenticated selection/policy record with an
    artifact digest placeholder, not arbitrary browser JSON. Publication still
    requires its separate exact artifact-bound grant and live revalidation.
    """
    plan = updater.load(Path(controller), plan_id)
    row = next((row for row in plan["targets"] if row["id"] == target_id), None)
    if not row or row["state"] != "applied":
        raise Blocked("guarded_apply_required")
    receipt = row.get("receipt", {})
    verification = receipt.get("verification", {})
    applied = receipt.get("apply", {})
    if (verification.get("changed_paths") != [] or verification.get("reconciliation_required") is not False or
            applied.get("reconciliation_required") is not False or
            applied.get("changed_paths") != receipt.get("changed_paths")):
        raise Blocked("verified_apply_required")
    # This performs actual GitHub release/asset attestation checks. No test
    # flag or unsigned "published": true boolean can replace it in production.
    source = updater.verify_source(plan["source"], apply=True)
    release = plan["source"]["release"]
    expected_release = {"repository": release["repository"], "tag": release["tag"],
                        "commit": release["commit"], "manifest_sha256": plan["source"]["manifest_sha256"],
                        "modes_sha256": hashlib.sha256(updater.file_bytes(source/"FILEMODES")).hexdigest()}
    if job["release"] != expected_release:
        raise Blocked("release_binding_mismatch")
    root = Path(row["path"])
    current = updater.target(root, updater.candidate_hashes(plan["source"]))
    if (current["binding"] != row["initial"]["binding"] or
            current["binding"].get("head") != job["base_sha"]):
        raise Blocked("checkout_changed_after_apply")
    if current["customization"]["requires_review"]:
        raise Blocked("policy_or_customization_changed")
    if updater.state.remote_identity(updater.state.git(root, "remote", "get-url", "origin")) != "github.com/"+job["repository"]:
        raise Blocked("repository_binding_mismatch")
    if job["plan_sha256"] != digest(plan):
        raise Blocked("plan_binding_mismatch")
    # Recheck the actual post-apply zero-change state, not just a stored claim.
    code, output = updater.invoke(plan["source"], row, Path(plan["backup_root"])/plan_id/target_id)
    fresh = updater.receipt(output, Path(plan["backup_root"])/plan_id/target_id) if code == 0 else None
    if not fresh or fresh["changed_paths"] or fresh["reconciliation_required"]:
        raise Blocked("post_apply_recheck_failed")
    changes = []
    for path in receipt["changed_paths"]:
        if not allowed_path(path):
            raise Blocked("protected_or_unsupported_publication_path")
        destination = updater.local.safe(root/path)
        before = git_blob(root, job["base_sha"], path)
        if destination.exists():
            mode = stat.S_IMODE(destination.stat().st_mode)
            if mode not in (0o644, 0o755):
                raise Blocked("unsupported_file_mode")
            data = updater.file_bytes(destination, 2*1024*1024)
            changes.append({"path": path, "before_sha": before, "mode": format(mode | 0o100000, "o"),
                            "content": base64.b64encode(data).decode()})
        else:
            changes.append({"path": path, "before_sha": before, "mode": None, "content": None})
    if updater.target(root, updater.candidate_hashes(plan["source"])) != current:
        raise Blocked("target_changed_during_freeze")
    artifact = {"base_sha": job["base_sha"], "changes": changes,
                "verification": {"guarded_apply_receipt_sha256": digest(applied),
                                 "protected_data_passed": True, "post_apply_remaining_paths": []}}
    bound_job = dict(job, artifact_sha256=digest(artifact))
    validate_job(bound_job, now)
    validate_artifact(artifact, bound_job)
    return sign("prepared-update", {"job": bound_job, "artifact": artifact}, key)
