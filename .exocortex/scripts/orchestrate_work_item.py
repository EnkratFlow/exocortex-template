#!/usr/bin/env python3
"""Provider-neutral work-item orchestration and guarded lifecycle mutations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from authority_guard import (
    ProtocolError,
    atomic_write_json,
    canonical_relative_path,
    check_authority,
    consume_capability,
    current_guard_digest,
    exclusive_lock,
    find_executor,
    isoformat,
    json_digest,
    load_json,
    parse_timestamp,
    reject_duplicate_keys,
    require_digest,
    require_exact_keys,
    require_id,
    resolve_repo_path,
    utc_now,
    validate_capability,
    validate_registry,
)
from model_registry import (
    RegistryError,
    canonical_digest as model_evidence_digest,
    parse_as_of,
    require_fresh as require_fresh_model_evidence,
    source_is_fresh,
    validate_availability,
    validate_catalog as validate_model_catalog,
    validate_source_registry,
)


STATES = [
    "captured",
    "triaged",
    "refined",
    "ready",
    "reserved",
    "developing",
    "developer_verified",
    "independent_review",
    "qa_sit",
    "uat_ready",
    "human_uat",
    "release_ready",
    "awaiting_release",
    "deployment_approved",
    "deployed",
    "hypercare",
    "done",
]

TRANSITIONS: Dict[Tuple[str, str], bool] = {
    ("captured", "triaged"): False,
    ("triaged", "refined"): False,
    ("refined", "ready"): False,
    ("ready", "reserved"): False,
    ("reserved", "developing"): True,
    ("developing", "developer_verified"): True,
    ("developer_verified", "independent_review"): False,
    ("independent_review", "qa_sit"): True,
    ("qa_sit", "uat_ready"): True,
    ("uat_ready", "human_uat"): True,
    ("human_uat", "release_ready"): True,
    ("release_ready", "awaiting_release"): False,
    ("awaiting_release", "deployment_approved"): False,
    ("deployment_approved", "deployed"): True,
    ("deployed", "hypercare"): True,
    ("hypercare", "done"): True,
}

LOCAL_DELIVERY_INTERNAL_TRANSITIONS = {
    ("developing", "developer_verified"),
    ("developer_verified", "independent_review"),
    ("independent_review", "qa_sit"),
    ("qa_sit", "uat_ready"),
    ("uat_ready", "human_uat"),
}

REGISTRY_RELPATH = ".exocortex/control/EXECUTOR_REGISTRY.json"
CAPABILITY_PREFIX = ".exocortex/local/protocol/capabilities/"
WORK_ITEM_PREFIX = ".exocortex/work-items/"
ENVELOPE_PREFIX = ".exocortex/local/protocol/envelopes/"
CAPABILITY_DIR = ".exocortex/local/protocol/capabilities"
LOCAL_PROTOCOL_INBOX_PREFIX = ".exocortex/local/protocol/inbox/"
PUBLICATION_RESERVATION_DIR = ".exocortex/local/protocol/publication-reservations"
PUBLICATION_RECORD_DIR = ".exocortex/local/protocol/publications"
EXACT_SHA_RE = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
GIT_SHA_RE = re.compile(r"^[a-f0-9]{40}$")
WILDCARD_RE = re.compile(r"[*?\[\]]")
MAX_ROUTE_CLOCK_SKEW_SECONDS = 60

PROTECTED_LOCAL_PREFIXES = (
    ".git/",
    ".exocortex/archive/",
    ".exocortex/events/",
    ".exocortex/hub/",
    ".exocortex/local/",
    ".exocortex/planning/",
    ".exocortex/secrets/",
    ".exocortex/work-items/",
)
PROTECTED_LOCAL_ROOTS = {prefix.rstrip("/") for prefix in PROTECTED_LOCAL_PREFIXES}
PROTECTED_LOCAL_FILES = {
    ".exocortex/LESSONS.md",
    ".exocortex/OPEN_DECISIONS.md",
    ".exocortex/PROJECT_MEMORY.md",
    ".exocortex/SESSION_CONTEXT.md",
    ".exocortex/TODO.md",
    REGISTRY_RELPATH,
}

SENSITIVE_INPUT_NAMES = {
    ".env",
    ".envrc",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "key-registry.json",
    "secrets.json",
}
SENSITIVE_INPUT_SUFFIXES = (".jks", ".key", ".keystore", ".p12", ".pem", ".pfx")

LOCAL_RUNTIME_FILES = PROTECTED_LOCAL_FILES | {
    ".exocortex/.hub_disabled",
    ".exocortex/.hub_enabled",
    ".exocortex/.install-manifest",
    ".exocortex/.project-name",
    ".exocortex/SESSION_CONTEXT.local.md",
    ".exocortex/control/ACTIVE_WORK.md",
    ".exocortex/control/ARCH_OVERVIEW.md",
    ".exocortex/control/BACKLOG.md",
    ".exocortex/control/BRANCH_POLICY.md",
    ".exocortex/control/EXTERNAL_SYNC_POLICY.json",
    ".exocortex/control/INTERRUPTS.md",
    ".exocortex/control/REPO_ORGANIZATION_REPORT.md",
    ".exocortex/control/REPO_STATE.md",
    ".exocortex/control/ROADMAP.md",
    ".exocortex/subconscious_patterns.md",
}


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:32]}"


def canonical_digest_lines(values: Sequence[str]) -> str:
    material = "".join(f"{value}\n" for value in values).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def resolve_project_root(value: Path) -> Path:
    candidate = Path(os.fspath(value))
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ProtocolError("project_root_unavailable", "project_root could not be resolved") from exc
    if not resolved.is_dir():
        raise ProtocolError("project_root_unavailable", "project_root must be an existing directory")
    return resolved


def require_absolute_project_root(value: Path) -> Path:
    if not Path(os.fspath(value)).is_absolute():
        raise ProtocolError("absolute_project_root_required", "project_root must be an absolute path")
    return resolve_project_root(value)


def is_sensitive_path(value: str) -> bool:
    parts = [part.casefold() for part in PurePosixPath(value).parts]
    basename = parts[-1]
    return (
        basename in SENSITIVE_INPUT_NAMES
        or basename.startswith(".env.")
        or basename.endswith(SENSITIVE_INPUT_SUFFIXES)
        or any(part in {".aws", ".ssh", "credentials", "secrets"} for part in parts)
    )


def is_local_runtime_path(value: str) -> bool:
    if (
        value in LOCAL_RUNTIME_FILES
        or value in PROTECTED_LOCAL_ROOTS
        or any(value.startswith(prefix) for prefix in PROTECTED_LOCAL_PREFIXES)
    ):
        return True
    name = PurePosixPath(value).name
    return value.startswith(".exocortex/") and (
        name == "SESSION_CONTEXT.md.backup" or name.startswith("SESSION_CONTEXT_BACKUP_")
    )


def git_output(project_root: Path, *arguments: str) -> bytes:
    environment = {
        "PATH": os.defpath,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-c", f"core.hooksPath={os.devnull}", "-C", str(project_root), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        raise ProtocolError("git_state_unavailable", "the exact local Git worktree state could not be verified")
    return result.stdout


def require_string_list(value: Any, field: str, *, nonempty: bool = False) -> List[str]:
    if not isinstance(value, list) or (nonempty and not value):
        raise ProtocolError("invalid_envelope", f"{field} must be a{' non-empty' if nonempty else ''} string array")
    if any(not isinstance(item, str) or not item for item in value):
        raise ProtocolError("invalid_envelope", f"{field} must contain non-empty strings")
    return list(value)


def require_local_delivery_string(
    value: Any,
    field: str,
    *,
    maximum: int,
    allow_newlines: bool = False,
) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ProtocolError(
            "invalid_envelope",
            f"{field} must be a non-empty string no longer than {maximum} characters",
        )
    forbidden = ("\x00", "\r") if allow_newlines else ("\x00", "\r", "\n")
    if any(control in value for control in forbidden):
        raise ProtocolError("invalid_envelope", f"{field} contains forbidden control data")
    return value


def require_local_delivery_string_list(
    value: Any,
    field: str,
    *,
    maximum: int,
) -> List[str]:
    if not isinstance(value, list) or not value:
        raise ProtocolError("invalid_envelope", f"{field} must be a non-empty string array")
    result = [
        require_local_delivery_string(item, f"{field} item", maximum=maximum)
        for item in value
    ]
    if len(result) != len(set(result)):
        raise ProtocolError("invalid_envelope", f"{field} entries must be unique")
    return result


def validate_local_delivery_actor(value: Any, field: str) -> Dict[str, str]:
    if not isinstance(value, dict):
        raise ProtocolError("invalid_envelope", f"{field} must be an object")
    require_exact_keys(value, ["surface_id", "executor_id", "adapter_version"], [], field)
    require_id(value["surface_id"], f"{field} surface_id")
    require_id(value["executor_id"], f"{field} executor_id")
    require_local_delivery_string(
        value["adapter_version"],
        f"{field} adapter_version",
        maximum=100,
    )
    return value


def validate_local_delivery_envelope(
    document: Dict[str, Any],
    *,
    require_active: bool = True,
) -> Dict[str, Any]:
    require_exact_keys(
        document,
        [
            "schema_version",
            "kind",
            "envelope_id",
            "work_item_id",
            "title",
            "type",
            "project_root",
            "branch",
            "base_sha",
            "allowed_paths",
            "outcome",
            "risk",
            "rollback",
            "verification",
            "exclusions",
            "writer",
            "reviewer",
            "approval",
            "lease_expires_at",
        ],
        [],
        "local-delivery envelope",
    )
    if document["schema_version"] != "public-v2" or document["kind"] != "local_delivery_envelope":
        raise ProtocolError("wrong_schema", "local-delivery envelope must use public-v2 local_delivery_envelope")
    require_id(document["envelope_id"], "envelope_id")
    require_id(document["work_item_id"], "work_item_id")
    require_local_delivery_string(document["title"], "title", maximum=240)
    require_local_delivery_string(document["project_root"], "project_root", maximum=2000)
    require_local_delivery_string(document["branch"], "branch", maximum=500)
    require_local_delivery_string(
        document["outcome"],
        "outcome",
        maximum=2000,
        allow_newlines=True,
    )
    require_local_delivery_string(
        document["rollback"],
        "rollback",
        maximum=2000,
        allow_newlines=True,
    )
    if not Path(document["project_root"]).is_absolute():
        raise ProtocolError("absolute_project_root_required", "local-delivery project_root must be an absolute path")
    if document["type"] not in {
        "feature",
        "bug",
        "maintenance",
        "security_privacy",
        "migration",
        "documentation_process",
        "retrospective_improvement",
    }:
        raise ProtocolError("invalid_envelope", "local-delivery type is invalid")
    if document["risk"] not in {"low", "medium", "high", "critical"}:
        raise ProtocolError("invalid_envelope", "local-delivery risk is invalid")
    if not isinstance(document["base_sha"], str) or not GIT_SHA_RE.fullmatch(document["base_sha"]):
        raise ProtocolError("invalid_base", "local-delivery base must be an exact Git commit")
    raw_paths = document["allowed_paths"]
    if (
        not isinstance(raw_paths, list)
        or not raw_paths
        or any(not isinstance(raw_path, str) for raw_path in raw_paths)
    ):
        raise ProtocolError("invalid_allowed_paths", "local-delivery allowed_paths must be a non-empty unique array")
    if len(raw_paths) != len(set(raw_paths)):
        raise ProtocolError("invalid_allowed_paths", "local-delivery allowed_paths must be a non-empty unique array")
    allowed_paths: List[str] = []
    for raw_path in raw_paths:
        if (
            len(raw_path) > 500
            or "\\" in raw_path
            or any(control in raw_path for control in ("\x00", "\r", "\n"))
        ):
            raise ProtocolError("invalid_allowed_paths", "local-delivery paths must use portable forward slashes")
        path = canonical_relative_path(raw_path)
        if WILDCARD_RE.search(path):
            raise ProtocolError("wildcard_path", "local-delivery paths must be exact and cannot contain wildcards")
        if is_sensitive_path(path):
            raise ProtocolError(
                "sensitive_allowed_path",
                "credential-shaped paths cannot be included in a local-delivery source lane",
            )
        if (
            path in PROTECTED_LOCAL_FILES
            or path in PROTECTED_LOCAL_ROOTS
            or any(path.startswith(prefix) for prefix in PROTECTED_LOCAL_PREFIXES)
        ):
            raise ProtocolError("protected_path", "project-local data cannot be included in a source-edit lane")
        allowed_paths.append(path)
    if len(allowed_paths) != len(set(allowed_paths)):
        raise ProtocolError("invalid_allowed_paths", "local-delivery paths must remain unique after normalization")
    allowed_paths.sort()
    document["allowed_paths"] = allowed_paths
    document["verification"] = require_local_delivery_string_list(
        document["verification"],
        "verification",
        maximum=1000,
    )
    document["exclusions"] = require_local_delivery_string_list(
        document["exclusions"],
        "exclusions",
        maximum=1000,
    )
    writer = validate_local_delivery_actor(document["writer"], "writer")
    reviewer = validate_local_delivery_actor(document["reviewer"], "reviewer")
    if (writer["surface_id"], writer["executor_id"]) == (reviewer["surface_id"], reviewer["executor_id"]):
        raise ProtocolError("reviewer_not_independent", "local-delivery reviewer must differ from the writer")
    approval = document["approval"]
    if not isinstance(approval, dict):
        raise ProtocolError("invalid_envelope", "approval must be an object")
    require_exact_keys(approval, ["approved_by", "accepted_at", "expires_at", "summary"], [], "approval")
    require_local_delivery_string(
        approval["approved_by"],
        "approved_by",
        maximum=200,
    )
    require_local_delivery_string(
        approval["summary"],
        "approval summary",
        maximum=2000,
        allow_newlines=True,
    )
    accepted_at = parse_timestamp(approval["accepted_at"], "accepted_at")
    expires_at = parse_timestamp(approval["expires_at"], "expires_at")
    lease_expires_at = parse_timestamp(document["lease_expires_at"], "lease_expires_at")
    now = utc_now()
    if accepted_at >= expires_at:
        raise ProtocolError("invalid_approval_window", "local-delivery approval expiry must follow acceptance")
    if lease_expires_at <= accepted_at or lease_expires_at > expires_at:
        raise ProtocolError("invalid_lease", "writer lease must follow acceptance and be no later than envelope expiry")
    if require_active:
        if accepted_at > now:
            raise ProtocolError("future_approval", "local-delivery approval acceptance is in the future")
        if expires_at <= now:
            raise ProtocolError("expired_envelope", "local-delivery approval has expired")
        if lease_expires_at <= now:
            raise ProtocolError("expired_lease", "local-delivery writer lease has expired")
    return document


def git_worktree_identity(
    project_root: Path,
    *,
    expected_branch: str,
    expected_base: str,
    require_clean: bool,
    expected_head: Optional[str] = None,
) -> str:
    root_output = git_output(project_root, "rev-parse", "--show-toplevel").decode("utf-8").strip()
    if Path(root_output).resolve(strict=True) != project_root:
        raise ProtocolError("wrong_worktree", "project root is not the exact Git worktree root")
    branch = git_output(project_root, "symbolic-ref", "--quiet", "--short", "HEAD").decode("utf-8").strip()
    if branch != expected_branch:
        raise ProtocolError("branch_mismatch", "current branch does not match the approved local-delivery branch")
    head = git_output(project_root, "rev-parse", "HEAD").decode("ascii").strip()
    if head != (expected_head or expected_base):
        raise ProtocolError("base_mismatch", "current HEAD does not match the approved local-delivery state")
    if require_clean:
        require_no_unapproved_ignored_paths(project_root)
        if git_output(project_root, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ProtocolError("dirty_worktree", "local-delivery bootstrap requires a clean isolated worktree")
    git_dir_text = git_output(project_root, "rev-parse", "--git-dir").decode("utf-8").strip()
    git_dir = Path(git_dir_text)
    if not git_dir.is_absolute():
        git_dir = project_root / git_dir
    common_dir_text = git_output(project_root, "rev-parse", "--git-common-dir").decode("utf-8").strip()
    common_dir = Path(common_dir_text)
    if not common_dir.is_absolute():
        common_dir = project_root / common_dir
    return json_digest(
        {
            "project_root": str(project_root),
            "branch": branch,
            # The durable identity stays anchored to the approved base even
            # after the exact publication commit becomes HEAD.
            "base_sha": expected_base,
            "git_dir": str(git_dir.resolve(strict=True)),
            "git_common_dir": str(common_dir.resolve(strict=True)),
        }
    )


def load_local_delivery_binding(
    project_root: Path,
    work_item: Dict[str, Any],
    *,
    require_active: bool,
    published_commit_sha: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    binding = work_item.get("local_delivery")
    if binding is None:
        return None
    envelope_path = resolve_repo_path(project_root, binding["envelope_path"], require_exists=True)
    envelope = validate_local_delivery_envelope(load_json(envelope_path), require_active=require_active)
    if json_digest(envelope) != binding["envelope_digest"]:
        raise ProtocolError("envelope_digest_mismatch", "stored local-delivery envelope changed after bootstrap")
    if envelope["work_item_id"] != work_item["id"]:
        raise ProtocolError("envelope_work_item_mismatch", "local-delivery envelope is bound to another work item")
    if envelope["project_root"] != str(project_root):
        raise ProtocolError("wrong_worktree", "local-delivery envelope belongs to another worktree")
    identity = git_worktree_identity(
        project_root,
        expected_branch=envelope["branch"],
        expected_base=envelope["base_sha"],
        require_clean=False,
        expected_head=published_commit_sha,
    )
    if identity != binding["worktree_identity_digest"]:
        raise ProtocolError("worktree_identity_mismatch", "local-delivery runtime state was copied to another worktree")
    if work_item["designated_base"].get("sha") != envelope["base_sha"]:
        raise ProtocolError("envelope_base_mismatch", "work-item base does not match the accepted local-delivery envelope")
    if work_item["designated_base"].get("ref") != f"refs/heads/{envelope['branch']}":
        raise ProtocolError("envelope_branch_mismatch", "work-item branch does not match the accepted local-delivery envelope")
    if sorted(envelope["allowed_paths"]) != sorted(work_item["lane"]["allowed_paths"]):
        raise ProtocolError("envelope_scope_mismatch", "work-item paths do not match the approved local-delivery envelope")
    expected_criteria = [
        {"id": f"AC-{index:03d}", "text": text}
        for index, text in enumerate(envelope["verification"], start=1)
    ]
    actual_criteria = [
        {"id": item["id"], "text": item["text"]}
        for item in work_item["acceptance_criteria"]
    ]
    if actual_criteria != expected_criteria or any("evidence" not in item for item in work_item["acceptance_criteria"]):
        raise ProtocolError(
            "acceptance_binding_mismatch",
            "local-delivery acceptance criteria no longer match the accepted envelope",
        )
    if work_item["lifecycle"]["state"] in {
        "developing",
        "developer_verified",
        "independent_review",
        "qa_sit",
        "uat_ready",
    }:
        if any(item["status"] in {"failed", "blocked"} for item in work_item["acceptance_criteria"]):
            raise ProtocolError(
                "acceptance_not_satisfied",
                "Human UAT cannot proceed while an acceptance criterion is failed or blocked",
            )
        if any(item["status"] != "pending" or item["evidence"] for item in work_item["acceptance_criteria"]):
            raise ProtocolError(
                "acceptance_state_mismatch",
                "local-delivery acceptance criteria must remain pending and empty through UAT-ready",
            )
    registry_path = resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True)
    registry = validate_registry(load_json(registry_path))
    if json_digest(registry) != binding["registry_digest"]:
        raise ProtocolError("registry_digest_mismatch", "executor registry changed after local-delivery bootstrap")
    reservation = work_item["lane"]["reservation"]
    completion = binding["completion"]
    if completion is None:
        expected_writer = envelope["writer"]
        if (
            reservation["status"] != "active"
            or reservation["writer"] != f"{expected_writer['surface_id']}/{expected_writer['executor_id']}"
            or reservation["surface_id"] != expected_writer["surface_id"]
            or reservation["executor_id"] != expected_writer["executor_id"]
            or reservation["lease_expires_at"] != envelope["lease_expires_at"]
        ):
            raise ProtocolError("reservation_binding_mismatch", "writer reservation no longer matches the accepted envelope")
    elif (
        reservation["status"] != "released"
        or any(reservation[field] is not None for field in ("writer", "surface_id", "executor_id", "lease_expires_at"))
    ):
        raise ProtocolError("completion_reservation_mismatch", "completed local delivery must have a released writer")
    return envelope


def read_safe_regular_bytes(path: Path, field: str, *, max_bytes: int = 1024 * 1024) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(path), flags)
    except FileNotFoundError as exc:
        raise ProtocolError("missing_file", f"{field} is missing") from exc
    except OSError as exc:
        raise ProtocolError("unsafe_file", f"{field} cannot be opened as a non-symlink file") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ProtocolError("unsafe_file", f"{field} must be a regular non-symlink file")
        if metadata.st_nlink != 1:
            raise ProtocolError("unsafe_file", f"{field} must not be hard-linked")
        if metadata.st_size > max_bytes:
            raise ProtocolError("file_too_large", f"{field} exceeds the local protocol size limit")
        chunks: List[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ProtocolError("file_too_large", f"{field} exceeds the local protocol size limit")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def canonical_local_protocol_input(value: Path, field: str) -> str:
    raw = os.fspath(value)
    if not isinstance(raw, str) or not raw or "\\" in raw or Path(raw).is_absolute():
        raise ProtocolError(
            "unsafe_input_path",
            f"{field} must be a project-relative file inside {LOCAL_PROTOCOL_INBOX_PREFIX}",
        )
    relative = canonical_relative_path(raw)
    if not relative.startswith(LOCAL_PROTOCOL_INBOX_PREFIX):
        raise ProtocolError(
            "unsafe_input_path",
            f"{field} must be a project-relative file inside {LOCAL_PROTOCOL_INBOX_PREFIX}",
        )
    if is_sensitive_path(relative):
        raise ProtocolError("sensitive_input_path", f"{field} cannot use a credential-shaped path")
    return relative


def read_local_protocol_input(
    project_root: Path,
    value: Path,
    field: str,
    *,
    max_bytes: int = 1024 * 1024,
) -> bytes:
    """Read only a single-link regular file reached through the ignored local inbox."""
    relative = canonical_local_protocol_input(value, field)
    components = PurePosixPath(relative).parts
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    file_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
        file_flags |= os.O_NOFOLLOW
    directory_descriptors: List[int] = []
    descriptor: Optional[int] = None
    try:
        try:
            current = os.open(str(project_root), directory_flags)
            directory_descriptors.append(current)
            for component in components[:-1]:
                current = os.open(component, directory_flags, dir_fd=current)
                directory_descriptors.append(current)
            descriptor = os.open(components[-1], file_flags, dir_fd=current)
        except FileNotFoundError as exc:
            raise ProtocolError("missing_file", f"{field} is missing") from exc
        except OSError as exc:
            raise ProtocolError("unsafe_file", f"{field} cannot be opened through the local protocol inbox") from exc
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ProtocolError("unsafe_file", f"{field} must be a single-link regular file")
        if metadata.st_size > max_bytes:
            raise ProtocolError("file_too_large", f"{field} exceeds the local protocol size limit")
        chunks: List[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ProtocolError("file_too_large", f"{field} exceeds the local protocol size limit")
        return b"".join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)


def load_local_protocol_json(project_root: Path, value: Path, field: str) -> Dict[str, Any]:
    raw = read_local_protocol_input(project_root, value, field)
    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid_json", f"{field} is not valid UTF-8 JSON") from exc
    if not isinstance(document, dict):
        raise ProtocolError("invalid_json", f"{field} must contain a JSON object")
    return document


def load_safe_json(path: Path, field: str) -> Dict[str, Any]:
    raw = read_safe_regular_bytes(path, field)
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid_json", f"{field} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ProtocolError("invalid_json", f"{field} must contain a JSON object")
    return value


def exclusive_write_bytes(path: Path, content: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(path), flags, mode)
    except FileExistsError as exc:
        raise ProtocolError("target_exists", "guarded first-write target already exists") from exc
    except OSError as exc:
        raise ProtocolError("unsafe_target", "guarded first-write target cannot be created safely") from exc
    try:
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)
    directory_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def exclusive_write_json(path: Path, value: Dict[str, Any]) -> None:
    content = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    exclusive_write_bytes(path, content)


def bootstrap_transaction_path(project_root: Path, request_id: str) -> Path:
    return resolve_repo_path(
        project_root,
        f".exocortex/local/protocol/transactions/bootstrap-{require_id(request_id, 'request_id')}.json",
    )


def validate_local_delivery_source_paths(project_root: Path, envelope: Dict[str, Any]) -> None:
    for relative in envelope["allowed_paths"]:
        candidate = resolve_repo_path(project_root, relative)
        if candidate.is_symlink():
            raise ProtocolError("unsafe_allowed_path", "local-delivery source paths cannot be symlinks")
        if candidate.exists():
            metadata = candidate.lstat()
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise ProtocolError("unsafe_allowed_path", "local-delivery source paths must be ordinary single-link files")


def proposed_local_delivery_registry(envelope: Dict[str, Any], guard_digest: str) -> Dict[str, Any]:
    registered_at = envelope["approval"]["accepted_at"]
    expires_at = envelope["approval"]["expires_at"]
    return validate_registry(
        {
            "schema_version": "public-v2",
            "kind": "executor_registry",
            "registry_version": 1,
            "default_role": "read_only",
            "executors": [
                {
                    **envelope["writer"],
                    "guard_digest": guard_digest,
                    "roles": ["read_only", "writer"],
                    "status": "active",
                    "registered_at": registered_at,
                    "expires_at": expires_at,
                    "revoked_at": None,
                },
                {
                    **envelope["reviewer"],
                    "guard_digest": guard_digest,
                    "roles": ["read_only"],
                    "status": "active",
                    "registered_at": registered_at,
                    "expires_at": expires_at,
                    "revoked_at": None,
                },
            ],
        }
    )


def require_local_delivery_registry_actors(
    registry: Dict[str, Any],
    envelope: Dict[str, Any],
    guard_digest: str,
    *,
    now: Any,
) -> None:
    for actor, role in ((envelope["writer"], "writer"), (envelope["reviewer"], "read_only")):
        entry = find_executor(
            registry,
            surface_id=actor["surface_id"],
            executor_id=actor["executor_id"],
            adapter_version=actor["adapter_version"],
            guard_digest=guard_digest,
            role=role,
            now=now,
        )
        if role == "read_only" and set(entry["roles"]) != {"read_only"}:
            raise ProtocolError("reviewer_role_denied", "local-delivery reviewer must remain exclusively read-only")


def build_local_delivery_bootstrap(
    *,
    envelope: Dict[str, Any],
    request_id: str,
    identity_digest: str,
    registry: Dict[str, Any],
    registry_preexisting: bool,
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], Dict[str, Any], str, str]:
    envelope_relpath = f"{ENVELOPE_PREFIX}{envelope['envelope_id']}.json"
    work_item_relpath = f"{WORK_ITEM_PREFIX}{envelope['work_item_id']}.json"
    envelope_digest = json_digest(envelope)
    registry_digest = json_digest(registry)
    result_id = stable_id("local-delivery", envelope["envelope_id"], request_id)
    writer = envelope["writer"]
    work_item = {
        "schema_version": "public-v2",
        "kind": "delivery_work_item",
        "id": envelope["work_item_id"],
        "title": envelope["title"],
        "type": envelope["type"],
        "revision": 0,
        "lifecycle": {"state": "developing", "attempt": 0, "blocked": None},
        "designated_base": {
            "sha": envelope["base_sha"],
            "ref": f"refs/heads/{envelope['branch']}",
            "source": "approved_work_item",
        },
        "lane": {
            "allowed_paths": list(envelope["allowed_paths"]),
            "reservation": {
                "status": "active",
                "writer": f"{writer['surface_id']}/{writer['executor_id']}",
                "surface_id": writer["surface_id"],
                "executor_id": writer["executor_id"],
                "lease_expires_at": envelope["lease_expires_at"],
                "version": 1,
            },
        },
        "acceptance_criteria": [
            {"id": f"AC-{index:03d}", "text": text, "status": "pending", "evidence": []}
            for index, text in enumerate(envelope["verification"], start=1)
        ],
        "transitions": [],
        "checkpoints": [],
        "handoffs": [],
        "idempotency": [
            {
                "request_id": request_id,
                "operation": "bootstrap_local_delivery",
                "result_id": result_id,
                "accepted_at": envelope["approval"]["accepted_at"],
            }
        ],
        "local_delivery": {
            "envelope_path": envelope_relpath,
            "envelope_digest": envelope_digest,
            "registry_digest": registry_digest,
            "worktree_identity_digest": identity_digest,
            "seal": None,
            "completion": None,
        },
    }
    validate_work_item(copy.deepcopy(work_item))
    documents = {envelope_relpath: envelope, work_item_relpath: work_item}
    journal = {
        "schema_version": "public-v2",
        "kind": "local_delivery_bootstrap_transaction",
        "request_id": request_id,
        "result_id": result_id,
        "envelope_digest": envelope_digest,
        "registry_digest": registry_digest,
        "registry_preexisting": registry_preexisting,
        "registry_document": registry,
        "documents": documents,
        "status": "intent",
        "created_at": envelope["approval"]["accepted_at"],
    }
    return work_item, documents, journal, work_item_relpath, result_id


def bootstrap_local_delivery(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = require_absolute_project_root(args.project_root)
    request_id = require_id(args.request_id, "request_id")
    envelope = validate_local_delivery_envelope(
        load_local_protocol_json(project_root, args.envelope_source, "envelope source"),
        require_active=False,
    )
    if envelope["project_root"] != str(project_root):
        raise ProtocolError("wrong_worktree", "envelope project_root does not match the requested worktree")
    journal_path = bootstrap_transaction_path(project_root, request_id)
    registry_path = resolve_repo_path(project_root, REGISTRY_RELPATH)
    lock_path = resolve_repo_path(project_root, ".exocortex/local/protocol/locks/local-delivery-bootstrap.lock")
    guard_digest = current_guard_digest()
    envelope_digest = json_digest(envelope)

    with exclusive_lock(lock_path):
        if journal_path.exists() or journal_path.is_symlink():
            identity_digest = git_worktree_identity(
                project_root,
                expected_branch=envelope["branch"],
                expected_base=envelope["base_sha"],
                require_clean=False,
            )
            validate_local_delivery_source_paths(project_root, envelope)
            existing_journal = load_safe_json(journal_path, "bootstrap transaction")
            require_exact_keys(
                existing_journal,
                [
                    "schema_version", "kind", "request_id", "result_id", "envelope_digest",
                    "registry_digest", "registry_preexisting", "registry_document", "documents",
                    "status", "created_at",
                ],
                ["finalized_at"],
                "bootstrap transaction",
            )
            if (
                existing_journal["schema_version"] != "public-v2"
                or existing_journal["kind"] != "local_delivery_bootstrap_transaction"
                or existing_journal["request_id"] != request_id
                or existing_journal["envelope_digest"] != envelope_digest
                or not isinstance(existing_journal["registry_preexisting"], bool)
                or existing_journal["status"] not in {"intent", "finalized"}
                or existing_journal["created_at"] != envelope["approval"]["accepted_at"]
            ):
                raise ProtocolError("transaction_conflict", "existing bootstrap transaction does not match this envelope")
            if existing_journal["status"] == "finalized":
                parse_timestamp(existing_journal.get("finalized_at"), "finalized_at")
            elif "finalized_at" in existing_journal:
                raise ProtocolError("transaction_conflict", "bootstrap intent cannot contain finalized evidence")
            registry = validate_registry(copy.deepcopy(existing_journal["registry_document"]))
            if json_digest(registry) != existing_journal["registry_digest"]:
                raise ProtocolError("transaction_digest_mismatch", "bootstrap registry digest is invalid")
            require_local_delivery_registry_actors(
                registry,
                envelope,
                guard_digest,
                now=parse_timestamp(existing_journal["created_at"], "created_at"),
            )
            _, documents, expected_journal, work_item_relpath, result_id = build_local_delivery_bootstrap(
                envelope=envelope,
                request_id=request_id,
                identity_digest=identity_digest,
                registry=registry,
                registry_preexisting=existing_journal["registry_preexisting"],
            )
            for field in (
                "result_id", "envelope_digest", "registry_digest", "registry_preexisting",
                "registry_document", "documents", "created_at",
            ):
                if existing_journal[field] != expected_journal[field]:
                    raise ProtocolError("transaction_conflict", "existing bootstrap transaction semantics differ from the envelope")
            finalized = existing_journal["status"] == "finalized"
            if registry_path.exists() or registry_path.is_symlink():
                if json_digest(validate_registry(load_safe_json(registry_path, "executor registry"))) != existing_journal["registry_digest"]:
                    raise ProtocolError("registry_digest_mismatch", "executor registry changed during bootstrap recovery")
            elif existing_journal["registry_preexisting"] or finalized:
                raise ProtocolError("bootstrap_state_missing", "finalized or pre-existing bootstrap registry is missing")
            else:
                exclusive_write_json(registry_path, registry)
            envelope_relpath = f"{ENVELOPE_PREFIX}{envelope['envelope_id']}.json"
            envelope_path = resolve_repo_path(project_root, envelope_relpath)
            expected_envelope = documents[envelope_relpath]
            if envelope_path.exists() or envelope_path.is_symlink():
                if json_digest(load_safe_json(envelope_path, "bootstrap envelope")) != json_digest(expected_envelope):
                    raise ProtocolError("bootstrap_state_conflict", "stored bootstrap envelope differs from the accepted envelope")
            elif finalized:
                raise ProtocolError("bootstrap_state_missing", "finalized bootstrap envelope is missing")
            else:
                exclusive_write_json(envelope_path, expected_envelope)

            work_item_path = resolve_repo_path(project_root, work_item_relpath)
            if work_item_path.exists() or work_item_path.is_symlink():
                current_work_item = validate_work_item(load_safe_json(work_item_path, "bootstrap work item"))
                replay = find_replay(current_work_item, request_id, "bootstrap_local_delivery")
                if replay is None or replay["result_id"] != result_id:
                    raise ProtocolError(
                        "bootstrap_state_conflict",
                        "current work item does not retain the accepted bootstrap idempotency record",
                    )
                load_local_delivery_binding(project_root, current_work_item, require_active=False)
                replay_state = current_work_item["lifecycle"]["state"]
            elif finalized:
                raise ProtocolError("bootstrap_state_missing", "finalized bootstrap work item is missing")
            else:
                exclusive_write_json(work_item_path, documents[work_item_relpath])
                replay_state = "developing"
            if not finalized:
                finalize_transaction(journal_path, existing_journal)
            return {
                "ok": True,
                "replay": True,
                "request_id": request_id,
                "result_id": result_id,
                "work_item": work_item_relpath,
                "state": replay_state,
            }

        # A new authority-bearing bootstrap must be active at the locked write boundary.
        identity_digest = git_worktree_identity(
            project_root,
            expected_branch=envelope["branch"],
            expected_base=envelope["base_sha"],
            require_clean=True,
        )
        validate_local_delivery_source_paths(project_root, envelope)
        validate_local_delivery_envelope(copy.deepcopy(envelope), require_active=True)
        if registry_path.is_symlink():
            raise ProtocolError("unsafe_registry", "executor registry cannot be a symlink")
        registry_preexisting = registry_path.exists()
        if registry_preexisting:
            registry = validate_registry(load_safe_json(registry_path, "executor registry"))
            require_local_delivery_registry_actors(registry, envelope, guard_digest, now=utc_now())
        else:
            registry = proposed_local_delivery_registry(envelope, guard_digest)
        work_item, documents, journal, work_item_relpath, result_id = build_local_delivery_bootstrap(
            envelope=envelope,
            request_id=request_id,
            identity_digest=identity_digest,
            registry=registry,
            registry_preexisting=registry_preexisting,
        )
        envelope_path = resolve_repo_path(project_root, f"{ENVELOPE_PREFIX}{envelope['envelope_id']}.json")
        work_item_path = resolve_repo_path(project_root, work_item_relpath)
        if any(path.exists() or path.is_symlink() for path in (envelope_path, work_item_path)):
            raise ProtocolError("bootstrap_state_exists", "local-delivery bootstrap outputs already exist")
        validate_local_delivery_envelope(copy.deepcopy(envelope), require_active=True)
        if git_worktree_identity(
            project_root,
            expected_branch=envelope["branch"],
            expected_base=envelope["base_sha"],
            require_clean=True,
        ) != identity_digest:
            raise ProtocolError("worktree_identity_mismatch", "worktree identity changed before bootstrap")
        validate_local_delivery_source_paths(project_root, envelope)
        if registry_preexisting:
            current_registry = validate_registry(load_safe_json(registry_path, "executor registry"))
            if json_digest(current_registry) != json_digest(registry):
                raise ProtocolError("registry_digest_mismatch", "executor registry changed before bootstrap")
            require_local_delivery_registry_actors(current_registry, envelope, guard_digest, now=utc_now())
        elif registry_path.exists() or registry_path.is_symlink():
            raise ProtocolError("bootstrap_state_exists", "executor registry appeared before bootstrap")
        validate_local_delivery_envelope(copy.deepcopy(envelope), require_active=True)
        require_local_delivery_registry_actors(registry, envelope, guard_digest, now=utc_now())
        atomic_write_json(journal_path, journal)
        maybe_fault("after_bootstrap_intent")
        exclusive_write_json(envelope_path, envelope)
        maybe_fault("after_bootstrap_envelope")
        if not registry_preexisting:
            exclusive_write_json(registry_path, registry)
        maybe_fault("after_bootstrap_registry")
        exclusive_write_json(work_item_path, work_item)
        maybe_fault("after_bootstrap_work_item")
        finalize_transaction(journal_path, journal)
    return {
        "ok": True,
        "replay": False,
        "request_id": request_id,
        "result_id": result_id,
        "work_item": work_item_relpath,
        "state": "developing",
    }


def decode_git_paths(raw: bytes, field: str) -> List[str]:
    values = [value for value in raw.split(b"\0") if value]
    try:
        return [canonical_relative_path(value.decode("utf-8")) for value in values]
    except UnicodeDecodeError as exc:
        raise ProtocolError("invalid_path_encoding", f"{field} must use valid UTF-8 paths") from exc


def require_no_unapproved_ignored_paths(project_root: Path) -> None:
    ignored = decode_git_paths(
        git_output(
            project_root,
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--directory",
            "--no-empty-directory",
            "-z",
            "--",
        ),
        "ignored Git changes",
    )
    # Git may collapse an ignored directory even when only a known runtime file
    # inside it is ignored (for example, the executor registry). Expand only
    # summaries that are not themselves an approved local/sensitive path. This
    # remains metadata-only: no ignored file is ever opened or fingerprinted.
    if any(not is_local_runtime_path(path) and not is_sensitive_path(path) for path in ignored):
        ignored = decode_git_paths(
            git_output(
                project_root,
                "ls-files",
                "--others",
                "--ignored",
                "--exclude-standard",
                "-z",
                "--",
            ),
            "ignored Git changes",
        )
    if any(not is_local_runtime_path(path) and not is_sensitive_path(path) for path in ignored):
        raise ProtocolError(
            "ignored_path_outside_scope",
            "ignored files outside protected Exocortex data and credential-shaped paths require explicit review",
        )


def current_changed_paths(project_root: Path) -> List[str]:
    require_no_unapproved_ignored_paths(project_root)
    if git_output(project_root, "diff", "--cached", "--name-only", "-z", "--"):
        raise ProtocolError("staged_changes", "local delivery never authorizes Git staging")
    tracked = git_output(project_root, "diff", "--name-only", "--no-renames", "-z", "HEAD", "--")
    untracked = git_output(project_root, "ls-files", "--others", "--exclude-standard", "-z", "--")
    paths = sorted(set(decode_git_paths(tracked + untracked, "changed Git paths")))
    if not paths:
        raise ProtocolError("no_local_changes", "there are no source changes to seal")
    return paths


def source_file_fingerprint(path: Path) -> Optional[Dict[str, str]]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(str(path), flags)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ProtocolError("unsafe_changed_path", "changed source path cannot be opened without following links") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ProtocolError("unsafe_changed_path", "changed source paths must be ordinary single-link files or deletions")
        digest = hashlib.sha256()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        git_mode = "100755" if metadata.st_mode & stat.S_IXUSR else "100644"
        return {"sha256": digest.hexdigest(), "mode": git_mode}
    finally:
        os.close(descriptor)


def candidate_change_evidence(project_root: Path, base_sha: str, paths: Sequence[str]) -> Dict[str, Any]:
    records: List[Dict[str, Any]] = []
    for relative in paths:
        path = resolve_repo_path(project_root, relative)
        before_mode_raw = git_output(project_root, "ls-tree", "-z", base_sha, "--", relative)
        before = None
        if before_mode_raw:
            entries = [entry for entry in before_mode_raw.split(b"\0") if entry]
            if len(entries) != 1 or b"\t" not in entries[0]:
                raise ProtocolError("git_state_unavailable", "base-tree evidence is ambiguous")
            metadata, tree_path = entries[0].split(b"\t", 1)
            try:
                tree_relative = tree_path.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ProtocolError("invalid_path_encoding", "base-tree path must be valid UTF-8") from exc
            metadata_parts = metadata.decode("ascii").split()
            if tree_relative != relative or len(metadata_parts) != 3 or metadata_parts[1] != "blob":
                raise ProtocolError("git_state_unavailable", "base-tree evidence does not identify the exact source file")
            before_bytes = git_output(project_root, "show", f"{base_sha}:{relative}")
            before = {
                "sha256": hashlib.sha256(before_bytes).hexdigest(),
                "mode": metadata_parts[0],
            }
        after = source_file_fingerprint(path)
        records.append({"path": relative, "before": before, "after": after})
    return {
        "changed_paths": list(paths),
        "path_set_digest": canonical_digest_lines(list(paths)),
        "candidate_digest": json_digest(records),
    }


def require_current_seal(
    project_root: Path,
    work_item: Dict[str, Any],
    *,
    ignored_paths: Sequence[str] = (),
) -> Dict[str, Any]:
    binding = work_item.get("local_delivery")
    if binding is None or binding["seal"] is None:
        raise ProtocolError("missing_edit_seal", "local delivery must be sealed before leaving development")
    seal = binding["seal"]
    ignored = {canonical_relative_path(path) for path in ignored_paths}
    completion = binding.get("completion")
    if completion is not None:
        ignored.add(completion["event_path"])
    paths = [path for path in current_changed_paths(project_root) if path not in ignored]
    if not paths:
        raise ProtocolError("sealed_candidate_changed", "sealed source changes are no longer present")
    evidence = candidate_change_evidence(project_root, work_item["designated_base"]["sha"], paths)
    expected = {
        "changed_paths": seal["changed_paths"],
        "path_set_digest": seal["path_set_digest"],
        "candidate_digest": seal["candidate_digest"],
    }
    if evidence != expected:
        raise ProtocolError("sealed_candidate_changed", "source changes no longer match the accepted local-delivery seal")
    return evidence


def committed_tree_fingerprint(
    project_root: Path,
    revision: str,
    relative: str,
) -> Optional[Dict[str, str]]:
    raw = git_output(project_root, "ls-tree", "-z", revision, "--", relative)
    entries = [entry for entry in raw.split(b"\0") if entry]
    if not entries:
        return None
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ProtocolError("published_seal_mismatch", "published tree entry is ambiguous")
    metadata, encoded_path = entries[0].split(b"\t", 1)
    try:
        actual_path = encoded_path.decode("utf-8")
        mode, object_type, object_id = metadata.decode("ascii").split()
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError("published_seal_mismatch", "published tree entry is invalid") from exc
    if actual_path != relative or object_type != "blob" or mode not in {"100644", "100755"}:
        raise ProtocolError("published_seal_mismatch", "published tree entry is not an approved ordinary file")
    content = git_output(project_root, "cat-file", "blob", object_id)
    return {"sha256": hashlib.sha256(content).hexdigest(), "mode": mode}


def require_committed_seal(
    project_root: Path,
    work_item: Dict[str, Any],
    commit_sha: str,
) -> Dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(commit_sha):
        raise ProtocolError("published_seal_mismatch", "published candidate must be one exact Git commit")
    seal = work_item.get("local_delivery", {}).get("seal")
    if seal is None:
        raise ProtocolError("missing_edit_seal", "published candidate lacks its local-delivery seal")
    base_sha = work_item["designated_base"]["sha"]
    parents = git_output(project_root, "rev-list", "--parents", "-n", "1", commit_sha).decode("ascii").split()
    if parents != [commit_sha, base_sha]:
        raise ProtocolError("published_seal_mismatch", "published commit is not one direct child of the approved base")
    paths = sorted(
        canonical_relative_path(value.decode("utf-8"))
        for value in git_output(
            project_root,
            "diff",
            "--name-only",
            "--no-renames",
            "-z",
            base_sha,
            commit_sha,
            "--",
        ).split(b"\0")
        if value
    )
    records = [
        {
            "path": path,
            "before": committed_tree_fingerprint(project_root, base_sha, path),
            "after": committed_tree_fingerprint(project_root, commit_sha, path),
        }
        for path in paths
    ]
    evidence = {
        "changed_paths": paths,
        "path_set_digest": canonical_digest_lines(paths),
        "candidate_digest": json_digest(records),
    }
    if evidence != {
        "changed_paths": seal["changed_paths"],
        "path_set_digest": seal["path_set_digest"],
        "candidate_digest": seal["candidate_digest"],
    }:
        raise ProtocolError("published_seal_mismatch", "published commit differs from the accepted local-delivery seal")
    if git_output(project_root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ProtocolError("published_checkout_dirty", "published candidate checkout must be exactly clean")
    return evidence


def internal_capability_relpath(work_item_id: str, operation: str, request_id: str) -> str:
    capability_id = stable_id("cap", work_item_id, operation, request_id)
    return f"{CAPABILITY_DIR}/{capability_id}.json"


def active_capability_digest(capability: Dict[str, Any]) -> str:
    normalized = copy.deepcopy(capability)
    normalized["status"] = {
        "state": "active",
        "revoked_at": None,
        "consumed_at": None,
        "consumed_by_request_id": None,
    }
    return json_digest(normalized)


def materialize_internal_capability(
    *,
    project_root: Path,
    work_item: Dict[str, Any],
    envelope: Dict[str, Any],
    operation: str,
    request_id: str,
    allowed_paths: Sequence[str],
    payload_digest: Optional[str] = None,
) -> str:
    writer = envelope["writer"]
    registry_path = resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True)
    registry = validate_registry(load_json(registry_path))
    guard_digest = current_guard_digest()
    find_executor(
        registry,
        surface_id=writer["surface_id"],
        executor_id=writer["executor_id"],
        adapter_version=writer["adapter_version"],
        guard_digest=guard_digest,
        role="writer",
        now=utc_now(),
    )
    capability_relpath = internal_capability_relpath(work_item["id"], operation, request_id)
    capability_path = resolve_repo_path(project_root, capability_relpath)
    scope: Dict[str, Any] = {
        "allowed_paths": list(allowed_paths),
        "target_sha": work_item["designated_base"]["sha"],
    }
    if payload_digest is not None:
        scope["payload_digest"] = require_digest(payload_digest, "payload_digest")
    capability = {
        "schema_version": "public-v2",
        "kind": "approval_capability",
        "capability_id": Path(capability_relpath).stem,
        "work_item_id": work_item["id"],
        "work_item_revision": work_item["revision"],
        "operation": operation,
        "scope": scope,
        "executor": {
            **writer,
            "guard_digest": guard_digest,
            "registry_version": registry["registry_version"],
        },
        "approval": {
            "approved_by": envelope["approval"]["approved_by"],
            "accepted_at": envelope["approval"]["accepted_at"],
            "expires_at": envelope["approval"]["expires_at"],
            "one_time": True,
            "summary": f"Internal {operation} capability derived from the exact accepted local-delivery envelope.",
        },
        "status": {
            "state": "active",
            "revoked_at": None,
            "consumed_at": None,
            "consumed_by_request_id": None,
        },
    }
    if capability_path.exists():
        existing = load_json(capability_path)
        for field in ("schema_version", "kind", "capability_id", "work_item_id", "work_item_revision", "operation", "scope", "executor", "approval"):
            if existing.get(field) != capability[field]:
                raise ProtocolError("capability_conflict", "existing internal capability does not match the accepted envelope")
        return capability_relpath
    atomic_write_json(capability_path, capability)
    return capability_relpath


def mutation_for_seal(
    request_id: str,
    evidence: Dict[str, Any],
) -> Callable[[Dict[str, Any], str], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any], accepted_at: str) -> Tuple[Dict[str, Any], str]:
        if document["lifecycle"]["state"] != "developing":
            raise ProtocolError("wrong_state", "local edits can be sealed only while developing")
        if document["local_delivery"]["seal"] is not None:
            raise ProtocolError("already_sealed", "local edits are already sealed")
        document["local_delivery"]["seal"] = {
            "request_id": request_id,
            "sealed_at": accepted_at,
            **evidence,
        }
        result_id = stable_id("edit-seal", document["id"], request_id, evidence["candidate_digest"])
        add_idempotency(document, request_id, "seal_local_edit", result_id, accepted_at=accepted_at)
        return document, result_id

    return mutate


def seal_local_edit(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = require_absolute_project_root(args.project_root)
    work_item_relpath = canonical_relative_path(args.work_item)
    if not work_item_relpath.startswith(WORK_ITEM_PREFIX):
        raise ProtocolError("invalid_work_item_path", "mutable work items must use project-local runtime storage")
    work_item_path = resolve_repo_path(project_root, work_item_relpath, require_exists=True)
    work_item = validate_work_item(load_json(work_item_path))
    envelope = load_local_delivery_binding(project_root, work_item, require_active=False)
    if envelope is None:
        raise ProtocolError("missing_local_delivery", "work item was not created by guarded local-delivery bootstrap")
    writer = envelope["writer"]
    if (
        args.surface_id != writer["surface_id"]
        or args.executor_id != writer["executor_id"]
        or args.adapter_version != writer["adapter_version"]
    ):
        raise ProtocolError("writer_mismatch", "current executor is not the envelope-bound writer")
    paths = current_changed_paths(project_root)
    outside = sorted(set(paths) - set(work_item["lane"]["allowed_paths"]))
    if outside:
        raise ProtocolError("path_not_allowed", "one or more changed source paths are outside the accepted local-delivery scope")
    evidence = candidate_change_evidence(project_root, work_item["designated_base"]["sha"], paths)
    replay = find_replay(work_item, args.request_id, "seal_local_edit")
    if replay is not None:
        if work_item["local_delivery"]["seal"] is None:
            raise ProtocolError("transaction_inconsistent", "seal idempotency exists without a sealed candidate")
        require_current_seal(project_root, work_item)
        journal_path = transaction_path(project_root, args.request_id)
        if journal_path.exists():
            journal = load_safe_json(journal_path, "seal transaction")
            if journal.get("status") != "finalized":
                finalize_transaction(journal_path, journal)
        return {
            "ok": True,
            "replay": True,
            "request_id": args.request_id,
            "result_id": replay["result_id"],
            "revision": work_item["revision"],
            "state": work_item["lifecycle"]["state"],
        }
    envelope = load_local_delivery_binding(project_root, work_item, require_active=True)
    capability_relpath = materialize_internal_capability(
        project_root=project_root,
        work_item=work_item,
        envelope=envelope,
        operation="seal_local_edit",
        request_id=args.request_id,
        allowed_paths=[work_item_relpath],
        payload_digest=evidence["candidate_digest"],
    )
    return guarded_mutation(
        project_root=project_root,
        work_item_relpath=work_item_relpath,
        capability_relpath=capability_relpath,
        registry_relpath=REGISTRY_RELPATH,
        request_id=args.request_id,
        operation="seal_local_edit",
        surface_id=args.surface_id,
        executor_id=args.executor_id,
        adapter_version=args.adapter_version,
        guard_digest=current_guard_digest(),
        payload_digest=evidence["candidate_digest"],
        mutate=mutation_for_seal(args.request_id, evidence),
    )


def completion_event_relpath(work_item: Dict[str, Any], envelope: Dict[str, Any]) -> str:
    event_id = stable_id("local-delivery-event", envelope["envelope_id"], work_item["id"])
    return f".exocortex/events/{event_id}.md"


def completion_transaction_path(project_root: Path, request_id: str) -> Path:
    return resolve_repo_path(
        project_root,
        f".exocortex/local/protocol/transactions/completion-{require_id(request_id, 'request_id')}.json",
    )


def completion_event_content(
    *,
    work_item: Dict[str, Any],
    request_id: str,
    completed_at: str,
    body: bytes,
    body_digest: str,
) -> bytes:
    try:
        body_text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProtocolError("invalid_event_body", "completion body must be UTF-8 text") from exc
    if "\x00" in body_text:
        raise ProtocolError("invalid_event_body", "completion body cannot contain NUL characters")
    seal = work_item["local_delivery"]["seal"]
    header = (
        "<!-- Local Delivery Completion -->\n"
        "schema_version: public-v2\n"
        f"work_item_id: {work_item['id']}\n"
        f"request_id: {request_id}\n"
        f"completed_at: {completed_at}\n"
        f"base_sha: {work_item['designated_base']['sha']}\n"
        f"candidate_digest: {seal['candidate_digest']}\n"
        f"body_sha256: {body_digest}\n"
        "\n---\n\n"
    )
    return header.encode("utf-8") + body


def require_transition_provenance(
    project_root: Path,
    current: Dict[str, Any],
    envelope: Dict[str, Any],
    transition: Dict[str, Any],
    transition_index: int,
) -> Tuple[str, str]:
    is_human_uat = transition["to"] == "human_uat"
    capability_mismatch_code = "human_uat_capability_mismatch" if is_human_uat else "transition_capability_mismatch"
    intent_mismatch_code = "human_uat_intent_mismatch" if is_human_uat else "transition_intent_mismatch"
    transaction_mismatch_code = "human_uat_transaction_mismatch" if is_human_uat else "transition_transaction_mismatch"
    label = "Human UAT" if is_human_uat else f"{transition['from']} to {transition['to']}"
    work_item_relpath = f"{WORK_ITEM_PREFIX}{current['id']}.json"
    capability_relpath = transition["capability_path"]
    capability_path = resolve_repo_path(project_root, capability_relpath, require_exists=True)
    capability = load_safe_json(capability_path, f"{label} capability")
    capability_scope = capability.get("scope")
    if (
        capability.get("capability_id") != transition["capability_id"]
        or active_capability_digest(capability) != transition["capability_digest"]
        or not isinstance(capability_scope, dict)
        or set(capability_scope) != {"allowed_paths", "target_sha", "payload_digest"}
        or capability_scope.get("allowed_paths") != [work_item_relpath]
        or capability_scope.get("target_sha") != current["designated_base"]["sha"]
        or capability.get("executor", {}).get("surface_id") != envelope["writer"]["surface_id"]
        or capability.get("executor", {}).get("executor_id") != envelope["writer"]["executor_id"]
        or capability.get("executor", {}).get("adapter_version") != envelope["writer"]["adapter_version"]
        or capability.get("approval", {}).get("approved_by") != envelope["approval"]["approved_by"]
        or capability.get("approval", {}).get("accepted_at") != envelope["approval"]["accepted_at"]
        or capability.get("approval", {}).get("expires_at") != envelope["approval"]["expires_at"]
        or capability.get("approval", {}).get("one_time") is not True
    ):
        raise ProtocolError(
            capability_mismatch_code,
            f"{label} capability no longer matches its recorded transition provenance",
        )
    intent_digest = transition_record_intent_digest(transition)
    if transition["intent_digest"] != intent_digest or capability_scope.get("payload_digest") != intent_digest:
        raise ProtocolError(
            intent_mismatch_code,
            f"{label} transition no longer matches its consumed capability payload",
        )
    registry_path = resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True)
    consumed_at = parse_timestamp(capability.get("status", {}).get("consumed_at"), f"{label} consumed_at")
    if consumed_at > utc_now():
        raise ProtocolError("invalid_recovery_timestamp", f"{label} capability consumption cannot be in the future")
    executor = capability.get("executor", {})
    check_authority(
        capability_path=capability_path,
        registry_path=registry_path,
        operation="transition_work_item",
        work_item_id=current["id"],
        work_item_revision=capability.get("work_item_revision"),
        request_id=transition["request_id"],
        surface_id=executor.get("surface_id"),
        executor_id=executor.get("executor_id"),
        adapter_version=executor.get("adapter_version"),
        guard_digest=current_guard_digest(),
        role="writer",
        target_path=work_item_relpath,
        target_sha=current["designated_base"]["sha"],
        payload_digest=intent_digest,
        require_exact_paths=True,
        now=consumed_at,
        allow_consumed_by_request_id=True,
    )

    journal_path = transaction_path(project_root, transition["request_id"])
    journal = load_safe_json(journal_path, f"{label} transaction")
    require_exact_keys(
        journal,
        [
            "schema_version",
            "kind",
            "request_id",
            "operation",
            "capability_id",
            "work_item_relpath",
            "before_digest",
            "after_digest",
            "after_document",
            "result_id",
            "payload_digest",
            "status",
            "created_at",
            "finalized_at",
        ],
        [],
        f"{label} transaction",
    )
    if (
        journal["schema_version"] != "public-v2"
        or journal["kind"] != "guarded_transaction"
        or journal["request_id"] != transition["request_id"]
        or journal["operation"] != "transition_work_item"
        or journal["capability_id"] != transition["capability_id"]
        or journal["work_item_relpath"] != work_item_relpath
        or journal["result_id"] != transition["id"]
        or journal["payload_digest"] != intent_digest
        or journal["status"] != "finalized"
        or journal["created_at"] != transition["accepted_at"]
    ):
        raise ProtocolError(
            transaction_mismatch_code,
            f"{label} transaction does not match the recorded transition",
        )
    bounded_consumed_at = bounded_recovery_consumed_at(journal, capability)
    finalized_at = parse_timestamp(journal["finalized_at"], f"{label} finalized_at")
    if finalized_at < bounded_consumed_at or finalized_at > utc_now():
        raise ProtocolError("invalid_recovery_timestamp", f"{label} transaction finalization time is invalid")
    if json_digest(journal["after_document"]) != journal["after_digest"]:
        raise ProtocolError("transaction_digest_mismatch", f"{label} transaction after-state digest is invalid")
    after_document = validate_work_item(journal["after_document"])
    expected_transition_prefix = current["transitions"][: transition_index + 1]
    prefix_ids = {item["id"] for item in expected_transition_prefix}
    expected_checkpoints = [
        item for item in current["checkpoints"] if item.get("transition_id") in prefix_ids
    ]
    transition_idempotency_index = next(
        (
            index
            for index, item in enumerate(current["idempotency"])
            if item.get("request_id") == transition["request_id"]
            and item.get("operation") == "transition_work_item"
            and item.get("result_id") == transition["id"]
        ),
        None,
    )
    if (
        after_document["revision"] != capability["work_item_revision"] + 1
        or after_document["lifecycle"]["state"] != transition["to"]
        or after_document["transitions"] != expected_transition_prefix
        or after_document["checkpoints"] != expected_checkpoints
        or transition_idempotency_index is None
        or after_document["idempotency"] != current["idempotency"][: transition_idempotency_index + 1]
        or after_document["designated_base"] != current["designated_base"]
        or after_document["lane"] != current["lane"]
        or after_document.get("local_delivery") != current.get("local_delivery")
    ):
        raise ProtocolError(
            transaction_mismatch_code,
            f"current transition history is not the state produced by the guarded {label} transaction",
        )
    if is_human_uat:
        if after_document["acceptance_criteria"] != current["acceptance_criteria"]:
            raise ProtocolError(
                transaction_mismatch_code,
                "current Human UAT acceptance state is not the state produced by its guarded transaction",
            )
    elif (
        [
            {"id": item["id"], "text": item["text"]}
            for item in after_document["acceptance_criteria"]
        ]
        != [
            {"id": item["id"], "text": item["text"]}
            for item in current["acceptance_criteria"]
        ]
        or any(
            item["status"] != "pending" or item.get("evidence")
            for item in after_document["acceptance_criteria"]
        )
    ):
        raise ProtocolError(
            transaction_mismatch_code,
            f"{label} transaction does not retain the pending pre-UAT acceptance state",
        )

    reconstructed_before = copy.deepcopy(after_document)
    reconstructed_before["revision"] -= 1
    reconstructed_before["lifecycle"]["state"] = transition["from"]
    if reconstructed_before["transitions"].pop() != transition:
        raise ProtocolError(transaction_mismatch_code, f"{label} transition tail is inconsistent")
    if transition["checkpoint_eligible"]:
        if (
            not reconstructed_before["checkpoints"]
            or reconstructed_before["checkpoints"][-1].get("transition_id") != transition["id"]
        ):
            raise ProtocolError(transaction_mismatch_code, f"{label} checkpoint provenance is inconsistent")
        reconstructed_before["checkpoints"].pop()
    if (
        not reconstructed_before["idempotency"]
        or reconstructed_before["idempotency"][-1].get("request_id") != transition["request_id"]
        or reconstructed_before["idempotency"][-1].get("operation") != "transition_work_item"
        or reconstructed_before["idempotency"][-1].get("result_id") != transition["id"]
    ):
        raise ProtocolError(transaction_mismatch_code, f"{label} idempotency provenance is inconsistent")
    reconstructed_before["idempotency"].pop()
    if is_human_uat:
        for criterion in reconstructed_before["acceptance_criteria"]:
            criterion["status"] = "pending"
            criterion["evidence"] = []
    reconstructed_before = validate_work_item(reconstructed_before)
    if json_digest(reconstructed_before) != journal["before_digest"]:
        raise ProtocolError(
            transaction_mismatch_code,
            f"{label} transaction before-state does not match its exact guarded mutation",
        )
    return journal["before_digest"], journal["after_digest"]


def require_seal_transaction_anchor(
    project_root: Path,
    current: Dict[str, Any],
    envelope: Dict[str, Any],
) -> str:
    seal = current["local_delivery"]["seal"]
    work_item_relpath = f"{WORK_ITEM_PREFIX}{current['id']}.json"
    journal_path = transaction_path(project_root, seal["request_id"])
    journal = load_safe_json(journal_path, "seal transaction")
    require_exact_keys(
        journal,
        [
            "schema_version",
            "kind",
            "request_id",
            "operation",
            "capability_id",
            "work_item_relpath",
            "before_digest",
            "after_digest",
            "after_document",
            "result_id",
            "payload_digest",
            "status",
            "created_at",
            "finalized_at",
        ],
        [],
        "seal transaction",
    )
    seal_idempotency = next(
        (
            item
            for item in current["idempotency"]
            if item.get("request_id") == seal["request_id"]
            and item.get("operation") == "seal_local_edit"
        ),
        None,
    )
    if (
        journal["schema_version"] != "public-v2"
        or journal["kind"] != "guarded_transaction"
        or journal["request_id"] != seal["request_id"]
        or journal["operation"] != "seal_local_edit"
        or journal["work_item_relpath"] != work_item_relpath
        or journal["payload_digest"] != seal["candidate_digest"]
        or journal["status"] != "finalized"
        or journal["created_at"] != seal["sealed_at"]
        or seal_idempotency is None
        or journal["result_id"] != seal_idempotency.get("result_id")
    ):
        raise ProtocolError("seal_transaction_mismatch", "sealed candidate lacks its exact finalized guarded transaction")
    if json_digest(journal["after_document"]) != journal["after_digest"]:
        raise ProtocolError("transaction_digest_mismatch", "seal transaction after-state digest is invalid")
    after_document = validate_work_item(journal["after_document"])
    if (
        after_document["lifecycle"]["state"] != "developing"
        or after_document["local_delivery"]["seal"] != seal
        or after_document["local_delivery"]["completion"] is not None
        or after_document["transitions"]
        or after_document["designated_base"] != current["designated_base"]
        or after_document["lane"] != current["lane"]
    ):
        raise ProtocolError("seal_transaction_mismatch", "seal transaction is not the anchor for the current delivery chain")

    capability_relpath = f"{CAPABILITY_DIR}/{journal['capability_id']}.json"
    capability_path = resolve_repo_path(project_root, capability_relpath, require_exists=True)
    capability = load_safe_json(capability_path, "seal capability")
    if (
        capability.get("capability_id") != journal["capability_id"]
        or capability.get("operation") != "seal_local_edit"
        or capability.get("scope") != {
            "allowed_paths": [work_item_relpath],
            "target_sha": current["designated_base"]["sha"],
            "payload_digest": seal["candidate_digest"],
        }
        or capability.get("executor", {}).get("surface_id") != envelope["writer"]["surface_id"]
        or capability.get("executor", {}).get("executor_id") != envelope["writer"]["executor_id"]
        or capability.get("executor", {}).get("adapter_version") != envelope["writer"]["adapter_version"]
        or capability.get("approval", {}).get("approved_by") != envelope["approval"]["approved_by"]
        or capability.get("approval", {}).get("accepted_at") != envelope["approval"]["accepted_at"]
        or capability.get("approval", {}).get("expires_at") != envelope["approval"]["expires_at"]
        or capability.get("approval", {}).get("one_time") is not True
    ):
        raise ProtocolError("seal_capability_mismatch", "seal capability no longer matches the accepted local-delivery envelope")
    consumed_at = bounded_recovery_consumed_at(journal, capability)
    registry_path = resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True)
    executor = capability.get("executor", {})
    check_authority(
        capability_path=capability_path,
        registry_path=registry_path,
        operation="seal_local_edit",
        work_item_id=current["id"],
        work_item_revision=capability.get("work_item_revision"),
        request_id=seal["request_id"],
        surface_id=executor.get("surface_id"),
        executor_id=executor.get("executor_id"),
        adapter_version=executor.get("adapter_version"),
        guard_digest=current_guard_digest(),
        role="writer",
        target_path=work_item_relpath,
        target_sha=current["designated_base"]["sha"],
        payload_digest=seal["candidate_digest"],
        require_exact_paths=True,
        now=consumed_at,
        allow_consumed_by_request_id=True,
    )
    finalized_at = parse_timestamp(journal["finalized_at"], "seal finalized_at")
    if finalized_at < consumed_at or finalized_at > utc_now():
        raise ProtocolError("invalid_recovery_timestamp", "seal transaction finalization time is invalid")

    reconstructed_before = copy.deepcopy(after_document)
    reconstructed_before["revision"] -= 1
    reconstructed_before["local_delivery"]["seal"] = None
    if (
        not reconstructed_before["idempotency"]
        or reconstructed_before["idempotency"][-1] != seal_idempotency
    ):
        raise ProtocolError("seal_transaction_mismatch", "seal idempotency provenance is inconsistent")
    reconstructed_before["idempotency"].pop()
    reconstructed_before = validate_work_item(reconstructed_before)
    if json_digest(reconstructed_before) != journal["before_digest"]:
        raise ProtocolError("seal_transaction_mismatch", "seal transaction before-state is not the exact bootstrap state")
    return journal["after_digest"]


def require_completion_gate_chain(
    project_root: Path,
    current: Dict[str, Any],
    envelope: Dict[str, Any],
) -> None:
    if current["lifecycle"]["state"] != "human_uat":
        raise ProtocolError("human_uat_required", "local delivery can close only after recorded human UAT")
    required_pairs = [
        ("developing", "developer_verified"),
        ("developer_verified", "independent_review"),
        ("independent_review", "qa_sit"),
        ("qa_sit", "uat_ready"),
        ("uat_ready", "human_uat"),
    ]
    transitions = current["transitions"]
    if len(transitions) < len(required_pairs):
        raise ProtocolError("human_uat_attestation_missing", "local-delivery verification and Human UAT transition chain is incomplete")
    chain = transitions[-len(required_pairs):]
    if [(item["from"], item["to"]) for item in chain] != required_pairs:
        raise ProtocolError("human_uat_attestation_missing", "local-delivery transition tail is not the required review and UAT chain")
    if any(not item["evidence"] for item in chain):
        raise ProtocolError("gate_evidence_missing", "every local-delivery verification and UAT gate requires concrete evidence")
    if not current["acceptance_criteria"] or any(
        item["status"] != "passed" or not item.get("evidence")
        for item in current["acceptance_criteria"]
    ):
        raise ProtocolError(
            "acceptance_incomplete",
            "local delivery can close only after Human UAT records every acceptance criterion as passed",
        )
    review = chain[1]
    reviewer = envelope["reviewer"]
    if (
        review.get("reviewer_surface_id") != reviewer["surface_id"]
        or review.get("reviewer_executor_id") != reviewer["executor_id"]
    ):
        raise ProtocolError("reviewer_mismatch", "independent review is not bound to the envelope reviewer")
    human_uat = chain[-1]
    if human_uat.get("human_uat_attestor") != envelope["approval"]["approved_by"]:
        raise ProtocolError(
            "human_uat_attestation_missing",
            "Human UAT transition must identify the envelope-bound approving authority",
        )
    required_acceptance_evidence = {
        f"human-uat-transition:{human_uat['id']}",
        *human_uat["evidence"],
    }
    if any(
        not required_acceptance_evidence.issubset(set(item["evidence"]))
        for item in current["acceptance_criteria"]
    ):
        raise ProtocolError(
            "acceptance_evidence_mismatch",
            "acceptance criteria are not bound to the exact Human UAT transition evidence",
        )
    chain_start = len(transitions) - len(required_pairs)
    previous_digest = require_seal_transaction_anchor(project_root, current, envelope)
    for offset, transition in enumerate(chain):
        before_digest, after_digest = require_transition_provenance(
            project_root,
            current,
            envelope,
            transition,
            chain_start + offset,
        )
        if before_digest != previous_digest:
            raise ProtocolError(
                "transition_chain_mismatch",
                "local-delivery transition transactions do not form one seal-anchored digest chain",
            )
        previous_digest = after_digest
    first_capability_path = resolve_repo_path(project_root, chain[0]["capability_path"], require_exists=True)
    first_capability = load_safe_json(first_capability_path, "first verification capability")
    if first_capability.get("work_item_revision") != 1:
        raise ProtocolError(
            "transition_chain_mismatch",
            "the first local-delivery verification transition is not anchored to sealed revision 1",
        )
    if previous_digest != json_digest(current):
        raise ProtocolError(
            "transition_chain_mismatch",
            "the Human UAT transaction is not the exact current pre-completion state",
        )
    checkpoint_transition_ids = {
        item.get("transition_id")
        for item in current["checkpoints"]
        if isinstance(item, dict)
    }
    for transition in chain:
        if transition["checkpoint_eligible"] and transition["id"] not in checkpoint_transition_ids:
            raise ProtocolError("checkpoint_missing", "completion gate transition lacks its guarded checkpoint")


def build_completion_document(
    *,
    project_root: Path,
    current: Dict[str, Any],
    envelope: Dict[str, Any],
    request_id: str,
    completed_at: str,
    event_path: str,
    body_digest: str,
    event_digest: str,
    capability_id: str,
    capability_digest: str,
) -> Tuple[Dict[str, Any], str]:
    require_completion_gate_chain(project_root, current, envelope)
    if current["local_delivery"]["completion"] is not None:
        raise ProtocolError("already_completed", "local delivery already has a completion record")
    reservation = current["lane"]["reservation"]
    writer = envelope["writer"]
    if (
        reservation["status"] != "active"
        or reservation["surface_id"] != writer["surface_id"]
        or reservation["executor_id"] != writer["executor_id"]
    ):
        raise ProtocolError("writer_mismatch", "only the active envelope-bound writer can close local delivery")
    after = copy.deepcopy(current)
    seal = after["local_delivery"]["seal"]
    result_id = stable_id("local-delivery-completion", current["id"], request_id, event_digest)
    handoff_id = stable_id("local-delivery-handoff", current["id"], request_id, event_digest)
    after["local_delivery"]["completion"] = {
        "request_id": request_id,
        "completed_at": completed_at,
        "local_state": "complete",
        "event_path": event_path,
        "body_digest": body_digest,
        "event_digest": event_digest,
    }
    after["lane"]["reservation"] = {
        "status": "released",
        "writer": None,
        "surface_id": None,
        "executor_id": None,
        "lease_expires_at": None,
        "version": reservation["version"] + 1,
    }
    after["handoffs"].append(
        {
            "id": handoff_id,
            "request_id": request_id,
            "created_at": completed_at,
            "base_sha": after["designated_base"]["sha"],
            "candidate_sha": seal["candidate_digest"],
            "state": after["lifecycle"]["state"],
            "writer_status": "released",
            "capability_id": capability_id,
            "capability_digest": capability_digest,
            "registry_digest": after["local_delivery"]["registry_digest"],
            "evidence_hashes": sorted(
                {
                    seal["path_set_digest"],
                    seal["candidate_digest"],
                    body_digest,
                    event_digest,
                }
            ),
            "closed_gates": [
                "publication_not_authorized",
                "integration_rollout_not_authorized",
                "production_egress_not_authorized",
            ],
            "first_verification": envelope["verification"][0],
            "local_only": True,
        }
    )
    after["idempotency"].append(
        {
            "request_id": request_id,
            "operation": "complete_local_delivery",
            "result_id": result_id,
            "accepted_at": completed_at,
        }
    )
    after["revision"] = current["revision"] + 1
    return validate_work_item(after), result_id


def write_or_verify_completion_event(
    path: Path,
    content: bytes,
    expected_digest: str,
    *,
    allow_existing: bool,
) -> None:
    if path.exists() or path.is_symlink():
        if not allow_existing:
            raise ProtocolError("completion_event_exists", "deterministic completion event path already exists")
        existing = read_safe_regular_bytes(path, "completion event")
        if hashlib.sha256(existing).hexdigest() != expected_digest or existing != content:
            raise ProtocolError("completion_event_conflict", "existing completion event is not byte-identical to the transaction")
        return
    exclusive_write_bytes(path, content)


def completion_state_for_release_gate(
    project_root: Path,
    current: Dict[str, Any],
    release_request_id: Optional[str],
) -> Dict[str, Any]:
    if current["lifecycle"]["state"] == "human_uat":
        return current
    if release_request_id is None or current["lifecycle"]["state"] != "release_ready":
        raise ProtocolError(
            "completion_state_mismatch",
            "local completion provenance must bind the current Human UAT state",
        )
    replay = find_replay(current, release_request_id, "transition_work_item")
    transition = next(
        (
            item
            for item in current["transitions"]
            if item.get("id") == (replay or {}).get("result_id")
            and item.get("request_id") == release_request_id
            and item.get("from") == "human_uat"
            and item.get("to") == "release_ready"
        ),
        None,
    )
    if replay is None or transition is None or not current["transitions"] or current["transitions"][-1] != transition:
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready replay lacks its exact Human UAT completion prefix",
        )
    work_item_relpath = f"{WORK_ITEM_PREFIX}{current['id']}.json"
    intent_digest = transition_record_intent_digest(transition)
    expected_capability_path = f"{CAPABILITY_DIR}/{transition['capability_id']}.json"
    if (
        transition.get("capability_path") != expected_capability_path
        or transition.get("intent_digest") != intent_digest
    ):
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready transition does not bind its exact capability path and intent",
        )
    capability_path = resolve_repo_path(
        project_root,
        expected_capability_path,
        require_exists=True,
    )
    capability = validate_capability(
        load_safe_json(capability_path, "release-ready capability")
    )
    if (
        capability["capability_id"] != transition["capability_id"]
        or active_capability_digest(capability) != transition["capability_digest"]
        or capability["operation"] != "transition_work_item"
        or capability["work_item_id"] != current["id"]
        or capability["scope"] != {
            "allowed_paths": [work_item_relpath],
            "target_sha": current["designated_base"]["sha"],
            "payload_digest": intent_digest,
        }
        or capability["status"]["state"] != "consumed"
        or capability["status"]["revoked_at"] is not None
        or capability["status"]["consumed_by_request_id"] != release_request_id
    ):
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready capability does not match its recorded transition provenance",
        )
    journal = load_safe_json(transaction_path(project_root, release_request_id), "release-ready transaction")
    require_exact_keys(
        journal,
        [
            "schema_version",
            "kind",
            "request_id",
            "operation",
            "capability_id",
            "work_item_relpath",
            "before_digest",
            "after_digest",
            "after_document",
            "result_id",
            "payload_digest",
            "status",
            "created_at",
            "finalized_at",
        ],
        [],
        "release-ready transaction",
    )
    if (
        journal["schema_version"] != "public-v2"
        or journal["kind"] != "guarded_transaction"
        or journal["request_id"] != release_request_id
        or journal["operation"] != "transition_work_item"
        or journal["work_item_relpath"] != work_item_relpath
        or journal["result_id"] != transition["id"]
        or journal["capability_id"] != transition["capability_id"]
        or journal["payload_digest"] != intent_digest
        or journal["status"] != "finalized"
        or journal["created_at"] != transition["accepted_at"]
    ):
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready replay transaction does not bind its exact completion prefix",
        )
    require_digest(journal["before_digest"], "release-ready before_digest")
    require_digest(journal["after_digest"], "release-ready after_digest")
    after_document = validate_work_item(copy.deepcopy(journal["after_document"]))
    if (
        json_digest(after_document) != journal["after_digest"]
        or after_document != current
        or json_digest(current) != journal["after_digest"]
    ):
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready replay after-state is not the exact current work item",
        )
    before = copy.deepcopy(after_document)
    before["revision"] -= 1
    before["lifecycle"]["state"] = "human_uat"
    before["transitions"].pop()
    if (
        not before["checkpoints"]
        or before["checkpoints"][-1].get("transition_id") != transition["id"]
    ):
        raise ProtocolError("completion_state_mismatch", "release-ready checkpoint prefix is inconsistent")
    before["checkpoints"].pop()
    if (
        not before["idempotency"]
        or before["idempotency"][-1].get("request_id") != release_request_id
        or before["idempotency"][-1].get("operation") != "transition_work_item"
        or before["idempotency"][-1].get("result_id") != transition["id"]
    ):
        raise ProtocolError("completion_state_mismatch", "release-ready idempotency prefix is inconsistent")
    before["idempotency"].pop()
    before = validate_work_item(before)
    if json_digest(before) != journal["before_digest"]:
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready transaction does not preserve its exact Human UAT completion prefix",
        )
    if capability["work_item_revision"] != before["revision"]:
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready capability is bound to the wrong work-item revision",
        )
    created_at = parse_timestamp(journal["created_at"], "release-ready created_at")
    approval_accepted_at = parse_timestamp(
        capability["approval"]["accepted_at"],
        "release-ready approval accepted_at",
    )
    if approval_accepted_at > created_at:
        raise ProtocolError(
            "invalid_recovery_timestamp",
            "release-ready transaction predates its approval capability",
        )
    consumed_at = bounded_recovery_consumed_at(journal, capability)
    finalized_at = parse_timestamp(journal["finalized_at"], "release-ready finalized_at")
    if finalized_at < consumed_at or finalized_at > utc_now():
        raise ProtocolError(
            "invalid_recovery_timestamp",
            "release-ready transaction finalization time is invalid",
        )
    executor = capability["executor"]
    check_authority(
        capability_path=capability_path,
        registry_path=resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True),
        operation="transition_work_item",
        work_item_id=current["id"],
        work_item_revision=before["revision"],
        request_id=release_request_id,
        surface_id=executor["surface_id"],
        executor_id=executor["executor_id"],
        adapter_version=executor["adapter_version"],
        guard_digest=current_guard_digest(),
        role="writer",
        target_path=work_item_relpath,
        target_sha=current["designated_base"]["sha"],
        payload_digest=intent_digest,
        require_exact_paths=True,
        now=consumed_at,
        allow_consumed_by_request_id=True,
    )
    if validate_capability(
        load_safe_json(capability_path, "release-ready capability")
    ) != capability:
        raise ProtocolError(
            "completion_state_mismatch",
            "release-ready capability changed during provenance validation",
        )
    return before


def require_local_completion_provenance(
    project_root: Path,
    current: Dict[str, Any],
    envelope: Dict[str, Any],
    *,
    release_request_id: Optional[str] = None,
    allow_intent_recovery: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    completion_state = completion_state_for_release_gate(project_root, current, release_request_id)
    completion = completion_state["local_delivery"]["completion"]
    if completion is None:
        raise ProtocolError(
            "local_delivery_incomplete",
            "complete-local-delivery must finish local closeout before the separate release-ready gate",
        )
    request_id = completion["request_id"]
    work_item_relpath = f"{WORK_ITEM_PREFIX}{completion_state['id']}.json"
    expected_event_path = completion_event_relpath(completion_state, envelope)
    expected_capability_path = internal_capability_relpath(
        completion_state["id"],
        "complete_local_delivery",
        request_id,
    )
    journal = load_safe_json(
        completion_transaction_path(project_root, request_id),
        "completion provenance transaction",
    )
    require_exact_keys(
        journal,
        [
            "schema_version",
            "kind",
            "request_id",
            "operation",
            "work_item_relpath",
            "capability_relpath",
            "capability_id",
            "capability_digest",
            "body_digest",
            "event_path",
            "event_digest",
            "event_text",
            "before_digest",
            "before_document",
            "after_digest",
            "after_document",
            "result_id",
            "status",
            "created_at",
        ],
        ["finalized_at"],
        "completion provenance transaction",
    )
    journal_status = journal["status"]
    if (
        journal["schema_version"] != "public-v2"
        or journal["kind"] != "local_delivery_completion_transaction"
        or journal["request_id"] != request_id
        or journal["operation"] != "complete_local_delivery"
        or journal["work_item_relpath"] != work_item_relpath
        or journal["capability_relpath"] != expected_capability_path
        or journal["body_digest"] != completion["body_digest"]
        or journal["event_path"] != completion["event_path"]
        or journal["event_path"] != expected_event_path
        or journal["event_digest"] != completion["event_digest"]
        or journal["created_at"] != completion["completed_at"]
        or journal_status not in ({"intent", "finalized"} if allow_intent_recovery else {"finalized"})
        or (journal_status == "intent" and "finalized_at" in journal)
        or (journal_status == "finalized" and "finalized_at" not in journal)
    ):
        raise ProtocolError(
            "completion_provenance_mismatch",
            "local completion does not match its exact finalized transaction",
        )
    require_digest(journal["before_digest"], "completion before_digest")
    require_digest(journal["after_digest"], "completion after_digest")
    before_document = validate_work_item(copy.deepcopy(journal["before_document"]))
    after_document = validate_work_item(copy.deepcopy(journal["after_document"]))
    if (
        json_digest(before_document) != journal["before_digest"]
        or json_digest(after_document) != journal["after_digest"]
        or after_document != completion_state
        or journal["after_digest"] != json_digest(completion_state)
    ):
        raise ProtocolError(
            "completion_provenance_mismatch",
            "completion transaction document digests do not bind the exact Human UAT closeout state",
        )

    capability_path = resolve_repo_path(
        project_root,
        expected_capability_path,
        require_exists=True,
    )
    capability = load_safe_json(capability_path, "completion provenance capability")
    if (
        capability.get("capability_id") != journal["capability_id"]
        or active_capability_digest(capability) != journal["capability_digest"]
        or capability.get("operation") != "complete_local_delivery"
        or capability.get("work_item_id") != completion_state["id"]
        or capability.get("work_item_revision") != before_document["revision"]
        or capability.get("scope") != {
            "allowed_paths": [work_item_relpath, expected_event_path],
            "target_sha": before_document["designated_base"]["sha"],
            "payload_digest": completion["event_digest"],
        }
        or capability.get("executor", {}).get("surface_id") != envelope["writer"]["surface_id"]
        or capability.get("executor", {}).get("executor_id") != envelope["writer"]["executor_id"]
        or capability.get("executor", {}).get("adapter_version") != envelope["writer"]["adapter_version"]
        or capability.get("approval", {}).get("approved_by") != envelope["approval"]["approved_by"]
        or capability.get("approval", {}).get("accepted_at") != envelope["approval"]["accepted_at"]
        or capability.get("approval", {}).get("expires_at") != envelope["approval"]["expires_at"]
        or capability.get("approval", {}).get("one_time") is not True
        or capability.get("status", {}).get("state") != "consumed"
        or capability.get("status", {}).get("consumed_by_request_id") != request_id
    ):
        raise ProtocolError(
            "completion_capability_mismatch",
            "local completion capability no longer matches its accepted envelope and closeout intent",
        )
    consumed_at = bounded_recovery_consumed_at(journal, capability)
    executor = capability["executor"]
    check_authority(
        capability_path=capability_path,
        registry_path=resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True),
        operation="complete_local_delivery",
        work_item_id=before_document["id"],
        work_item_revision=before_document["revision"],
        request_id=request_id,
        surface_id=executor["surface_id"],
        executor_id=executor["executor_id"],
        adapter_version=executor["adapter_version"],
        guard_digest=current_guard_digest(),
        role="writer",
        target_paths=[work_item_relpath, expected_event_path],
        target_sha=before_document["designated_base"]["sha"],
        payload_digest=completion["event_digest"],
        require_exact_paths=True,
        now=consumed_at,
        allow_consumed_by_request_id=True,
    )
    if journal_status == "finalized":
        finalized_at = parse_timestamp(journal["finalized_at"], "completion finalized_at")
        if finalized_at < consumed_at or finalized_at > utc_now():
            raise ProtocolError("invalid_recovery_timestamp", "completion transaction finalization time is invalid")

    try:
        event_text = journal["event_text"].encode("utf-8")
    except (AttributeError, UnicodeEncodeError) as exc:
        raise ProtocolError("completion_event_conflict", "completion transaction event text is invalid") from exc
    event_path = resolve_repo_path(project_root, expected_event_path, require_exists=True)
    event_bytes = read_safe_regular_bytes(event_path, "completion provenance event")
    separator = b"\n---\n\n"
    _, found_separator, event_body = event_bytes.partition(separator)
    if (
        not found_separator
        or event_bytes != event_text
        or hashlib.sha256(event_bytes).hexdigest() != completion["event_digest"]
        or hashlib.sha256(event_body).hexdigest() != completion["body_digest"]
        or event_bytes
        != completion_event_content(
            work_item=before_document,
            request_id=request_id,
            completed_at=completion["completed_at"],
            body=event_body,
            body_digest=completion["body_digest"],
        )
    ):
        raise ProtocolError(
            "completion_event_conflict",
            "completion event bytes do not match the finalized body and event binding",
        )

    expected_after, expected_result = build_completion_document(
        project_root=project_root,
        current=before_document,
        envelope=envelope,
        request_id=request_id,
        completed_at=completion["completed_at"],
        event_path=expected_event_path,
        body_digest=completion["body_digest"],
        event_digest=completion["event_digest"],
        capability_id=journal["capability_id"],
        capability_digest=journal["capability_digest"],
    )
    completion_idempotency = [
        item
        for item in completion_state["idempotency"]
        if item.get("request_id") == request_id
        and item.get("operation") == "complete_local_delivery"
    ]
    expected_handoff_id = stable_id(
        "local-delivery-handoff",
        completion_state["id"],
        request_id,
        completion["event_digest"],
    )
    if (
        expected_after != completion_state
        or expected_result != journal["result_id"]
        or len(completion_idempotency) != 1
        or completion_idempotency[0].get("result_id") != journal["result_id"]
        or completion_idempotency[0].get("accepted_at") != completion["completed_at"]
        or len(completion_state["handoffs"]) != 1
        or completion_state["handoffs"][0].get("id") != expected_handoff_id
        or completion_state["lane"]["reservation"].get("status") != "released"
        or any(
            completion_state["lane"]["reservation"].get(field) is not None
            for field in ("writer", "surface_id", "executor_id", "lease_expires_at")
        )
    ):
        raise ProtocolError(
            "completion_provenance_mismatch",
            "local completion lacks its exact idempotency, handoff, reservation, or after-state semantics",
        )
    return completion_state, journal


def complete_local_delivery(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = require_absolute_project_root(args.project_root)
    request_id = require_id(args.request_id, "request_id")
    work_item_relpath = canonical_relative_path(args.work_item)
    if not work_item_relpath.startswith(WORK_ITEM_PREFIX):
        raise ProtocolError("invalid_work_item_path", "mutable work items must use project-local runtime storage")
    body = read_local_protocol_input(
        project_root,
        args.body_file,
        "completion body",
        max_bytes=64 * 1024,
    )
    body_digest = hashlib.sha256(body).hexdigest()
    work_item_path = resolve_repo_path(project_root, work_item_relpath, require_exists=True)
    registry_path = resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True)
    journal_path = completion_transaction_path(project_root, request_id)
    lock_path = resolve_repo_path(project_root, f".exocortex/local/protocol/locks/{work_item_path.name}.lock")

    with exclusive_lock(lock_path):
        current = validate_work_item(load_json(work_item_path))
        envelope = load_local_delivery_binding(project_root, current, require_active=False)
        if envelope is None:
            raise ProtocolError("missing_local_delivery", "work item was not created by guarded local-delivery bootstrap")
        event_relpath = completion_event_relpath(current, envelope)
        require_current_seal(project_root, current, ignored_paths=[event_relpath])
        completion = current["local_delivery"]["completion"]
        replay = find_replay(current, request_id, "complete_local_delivery")
        if completion is not None:
            if replay is None or completion["request_id"] != request_id:
                raise ProtocolError("already_completed", "local delivery was completed by another request")
            if completion["body_digest"] != body_digest:
                raise ProtocolError("idempotency_conflict", "completion replay body differs from the accepted request")
            _, replay_journal = require_local_completion_provenance(
                project_root,
                current,
                envelope,
                allow_intent_recovery=True,
            )
            event_path = resolve_repo_path(project_root, completion["event_path"], require_exists=True)
            event_bytes = read_safe_regular_bytes(event_path, "completion event")
            expected_event = completion_event_content(
                work_item=current,
                request_id=request_id,
                completed_at=completion["completed_at"],
                body=body,
                body_digest=body_digest,
            )
            if (
                event_bytes != expected_event
                or hashlib.sha256(event_bytes).hexdigest() != completion["event_digest"]
            ):
                raise ProtocolError("completion_event_conflict", "recorded completion event digest no longer matches")
            if replay_journal["status"] == "intent":
                finalize_transaction(journal_path, replay_journal)
            return {
                "ok": True,
                "replay": True,
                "request_id": request_id,
                "result_id": replay["result_id"],
                "event_path": completion["event_path"],
                "revision": current["revision"],
                "state": current["lifecycle"]["state"],
                "writer_status": current["lane"]["reservation"]["status"],
            }

        event_path = resolve_repo_path(project_root, event_relpath)
        capability_relpath = internal_capability_relpath(current["id"], "complete_local_delivery", request_id)
        capability_path = resolve_repo_path(project_root, capability_relpath)
        authority_kwargs: Dict[str, Any]

        started_new = not journal_path.exists()
        if started_new:
            active_envelope = load_local_delivery_binding(project_root, current, require_active=True)
            writer = active_envelope["writer"]
            if (
                args.surface_id != writer["surface_id"]
                or args.executor_id != writer["executor_id"]
                or args.adapter_version != writer["adapter_version"]
            ):
                raise ProtocolError("writer_mismatch", "current executor is not the envelope-bound writer")
            require_completion_gate_chain(project_root, current, active_envelope)
            if event_path.exists() or event_path.is_symlink():
                raise ProtocolError("completion_event_exists", "deterministic completion event path already exists")
            completed_at = isoformat(utc_now())
            event_content = completion_event_content(
                work_item=current,
                request_id=request_id,
                completed_at=completed_at,
                body=body,
                body_digest=body_digest,
            )
            event_digest = hashlib.sha256(event_content).hexdigest()
            prepare = {
                "schema_version": "public-v2",
                "kind": "local_delivery_completion_prepare",
                "request_id": request_id,
                "operation": "complete_local_delivery",
                "work_item_relpath": work_item_relpath,
                "body_digest": body_digest,
                "event_path": event_relpath,
                "event_digest": event_digest,
                "event_text": event_content.decode("utf-8"),
                "before_digest": json_digest(current),
                "status": "prepared",
                "created_at": completed_at,
            }
            exclusive_write_json(journal_path, prepare)
            maybe_fault("after_completion_prepare")

        prepared = load_safe_json(journal_path, "completion transaction")
        if prepared.get("kind") == "local_delivery_completion_prepare":
            require_exact_keys(
                prepared,
                [
                    "schema_version",
                    "kind",
                    "request_id",
                    "operation",
                    "work_item_relpath",
                    "body_digest",
                    "event_path",
                    "event_digest",
                    "event_text",
                    "before_digest",
                    "status",
                    "created_at",
                ],
                [],
                "completion preparation",
            )
            if (
                prepared["schema_version"] != "public-v2"
                or prepared["request_id"] != request_id
                or prepared["operation"] != "complete_local_delivery"
                or prepared["work_item_relpath"] != work_item_relpath
                or prepared["body_digest"] != body_digest
                or prepared["event_path"] != event_relpath
                or prepared["status"] != "prepared"
                or prepared["before_digest"] != json_digest(current)
            ):
                raise ProtocolError("transaction_conflict", "completion preparation does not match this exact request")
            try:
                event_content = prepared["event_text"].encode("utf-8")
            except (AttributeError, UnicodeEncodeError) as exc:
                raise ProtocolError("transaction_conflict", "completion preparation event text is invalid") from exc
            expected_event_content = completion_event_content(
                work_item=current,
                request_id=request_id,
                completed_at=prepared["created_at"],
                body=body,
                body_digest=body_digest,
            )
            event_digest = hashlib.sha256(event_content).hexdigest()
            if (
                event_content != expected_event_content
                or event_digest != prepared["event_digest"]
            ):
                raise ProtocolError("transaction_digest_mismatch", "completion preparation event is not bound to the request")
            active_envelope = load_local_delivery_binding(project_root, current, require_active=True)
            writer = active_envelope["writer"]
            if (
                args.surface_id != writer["surface_id"]
                or args.executor_id != writer["executor_id"]
                or args.adapter_version != writer["adapter_version"]
            ):
                raise ProtocolError("writer_mismatch", "current executor is not the envelope-bound writer")
            require_completion_gate_chain(project_root, current, active_envelope)
            require_current_seal(project_root, current, ignored_paths=[event_relpath])
            if event_path.exists() or event_path.is_symlink():
                raise ProtocolError("completion_event_exists", "deterministic completion event path already exists")
            capability_relpath = materialize_internal_capability(
                project_root=project_root,
                work_item=current,
                envelope=active_envelope,
                operation="complete_local_delivery",
                request_id=request_id,
                allowed_paths=[work_item_relpath, event_relpath],
                payload_digest=event_digest,
            )
            capability_path = resolve_repo_path(project_root, capability_relpath, require_exists=True)
            capability = load_json(capability_path)
            capability_digest = json_digest(capability)
            after_document, result_id = build_completion_document(
                project_root=project_root,
                current=current,
                envelope=active_envelope,
                request_id=request_id,
                completed_at=prepared["created_at"],
                event_path=event_relpath,
                body_digest=body_digest,
                event_digest=event_digest,
                capability_id=capability["capability_id"],
                capability_digest=capability_digest,
            )
            journal = {
                "schema_version": "public-v2",
                "kind": "local_delivery_completion_transaction",
                "request_id": request_id,
                "operation": "complete_local_delivery",
                "work_item_relpath": work_item_relpath,
                "capability_relpath": capability_relpath,
                "capability_id": capability["capability_id"],
                "capability_digest": capability_digest,
                "body_digest": body_digest,
                "event_path": event_relpath,
                "event_digest": event_digest,
                "event_text": event_content.decode("utf-8"),
                "before_digest": json_digest(current),
                "before_document": current,
                "after_digest": json_digest(after_document),
                "after_document": after_document,
                "result_id": result_id,
                "status": "intent",
                "created_at": prepared["created_at"],
            }
            atomic_write_json(journal_path, journal)
            maybe_fault("after_completion_intent")

        if journal_path.exists():
            journal = load_safe_json(journal_path, "completion transaction")
            require_exact_keys(
                journal,
                [
                    "schema_version",
                    "kind",
                    "request_id",
                    "operation",
                    "work_item_relpath",
                    "capability_relpath",
                    "capability_id",
                    "capability_digest",
                    "body_digest",
                    "event_path",
                    "event_digest",
                    "event_text",
                    "before_digest",
                    "before_document",
                    "after_digest",
                    "after_document",
                    "result_id",
                    "status",
                    "created_at",
                ],
                ["finalized_at"],
                "completion transaction",
            )
            if (
                journal["schema_version"] != "public-v2"
                or journal["kind"] != "local_delivery_completion_transaction"
                or journal["request_id"] != request_id
                or journal["operation"] != "complete_local_delivery"
                or journal["work_item_relpath"] != work_item_relpath
                or journal["capability_relpath"] != capability_relpath
                or journal["body_digest"] != body_digest
                or journal["event_path"] != event_relpath
                or journal["status"] != "intent"
            ):
                raise ProtocolError("transaction_conflict", "existing completion transaction does not match this request")
            try:
                event_content = journal["event_text"].encode("utf-8")
            except (AttributeError, UnicodeEncodeError) as exc:
                raise ProtocolError("transaction_conflict", "completion transaction event text is invalid") from exc
            event_digest = hashlib.sha256(event_content).hexdigest()
            if event_digest != journal["event_digest"]:
                raise ProtocolError("transaction_digest_mismatch", "completion event digest is invalid")
            before_document = validate_work_item(journal["before_document"])
            after_document = validate_work_item(journal["after_document"])
            if json_digest(before_document) != journal["before_digest"] or json_digest(after_document) != journal["after_digest"]:
                raise ProtocolError("transaction_digest_mismatch", "completion transaction document digest is invalid")
            capability = load_json(capability_path)
            if (
                capability.get("capability_id") != journal["capability_id"]
                or active_capability_digest(capability) != journal["capability_digest"]
            ):
                raise ProtocolError("transaction_capability_conflict", "completion capability no longer matches its accepted intent")
            expected_after, expected_result = build_completion_document(
                project_root=project_root,
                current=before_document,
                envelope=envelope,
                request_id=request_id,
                completed_at=journal["created_at"],
                event_path=event_relpath,
                body_digest=body_digest,
                event_digest=event_digest,
                capability_id=journal["capability_id"],
                capability_digest=journal["capability_digest"],
            )
            if json_digest(expected_after) != journal["after_digest"] or expected_result != journal["result_id"]:
                raise ProtocolError("transaction_semantics_mismatch", "completion transaction after-state is not the authorized closeout")
            current_digest = json_digest(current)
            if current_digest not in {journal["before_digest"], journal["after_digest"]}:
                raise ProtocolError("transaction_state_conflict", "work item changed outside the incomplete completion transaction")
            authority_kwargs = {
                "operation": "complete_local_delivery",
                "work_item_id": before_document["id"],
                "work_item_revision": before_document["revision"],
                "surface_id": args.surface_id,
                "executor_id": args.executor_id,
                "adapter_version": args.adapter_version,
                "guard_digest": current_guard_digest(),
                "role": "writer",
                "target_paths": [work_item_relpath, event_relpath],
                "target_sha": before_document["designated_base"]["sha"],
                "payload_digest": event_digest,
                "require_exact_paths": True,
            }
            status = capability.get("status", {})
            if status.get("state") == "consumed" and status.get("consumed_by_request_id") == request_id:
                check_authority(
                    capability_path=capability_path,
                    registry_path=registry_path,
                    request_id=request_id,
                    now=bounded_recovery_consumed_at(journal, capability),
                    allow_consumed_by_request_id=True,
                    **authority_kwargs,
                )
            else:
                load_local_delivery_binding(project_root, current, require_active=True)
                consume_capability(
                    capability_path=capability_path,
                    registry_path=registry_path,
                    request_id=request_id,
                    check_kwargs=authority_kwargs,
                )
            require_current_seal(project_root, current, ignored_paths=[event_relpath])
            write_or_verify_completion_event(event_path, event_content, event_digest, allow_existing=True)
            maybe_fault("after_completion_event")
            if current_digest == journal["before_digest"]:
                require_current_seal(project_root, current, ignored_paths=[event_relpath])
                atomic_write_json(work_item_path, after_document)
                maybe_fault("after_completion_state")
            finalize_transaction(journal_path, journal)
            return {
                "ok": True,
                "replay": False,
                "recovered": not started_new,
                "request_id": request_id,
                "result_id": journal["result_id"],
                "event_path": event_relpath,
                "revision": after_document["revision"],
                "state": after_document["lifecycle"]["state"],
                "writer_status": "released",
            }

def validate_work_item(document: Dict[str, Any]) -> Dict[str, Any]:
    require_exact_keys(
        document,
        [
            "schema_version",
            "kind",
            "id",
            "revision",
            "lifecycle",
            "designated_base",
            "lane",
            "acceptance_criteria",
            "transitions",
            "checkpoints",
            "handoffs",
            "idempotency",
        ],
        ["title", "type", "retrospectives", "local_delivery"],
        "work item",
    )
    if document["schema_version"] != "public-v2" or document["kind"] != "delivery_work_item":
        raise ProtocolError("wrong_schema", "work item must use public-v2 delivery_work_item")
    require_id(document["id"], "work item id")
    if not isinstance(document["revision"], int) or document["revision"] < 0:
        raise ProtocolError("invalid_revision", "work item revision must be non-negative")
    lifecycle = document["lifecycle"]
    if not isinstance(lifecycle, dict):
        raise ProtocolError("invalid_lifecycle", "lifecycle must be an object")
    require_exact_keys(lifecycle, ["state", "attempt", "blocked"], [], "lifecycle")
    if lifecycle["state"] not in STATES:
        raise ProtocolError("invalid_state", "work item lifecycle state is invalid")
    if not isinstance(lifecycle["attempt"], int) or lifecycle["attempt"] < 0:
        raise ProtocolError("invalid_attempt", "lifecycle attempt must be non-negative")
    if lifecycle["blocked"] is not None:
        if not isinstance(lifecycle["blocked"], dict):
            raise ProtocolError("invalid_blocked", "blocked must be null or an object")
        require_exact_keys(lifecycle["blocked"], ["reason", "since"], [], "blocked")
        parse_timestamp(lifecycle["blocked"]["since"], "blocked since")

    base = document["designated_base"]
    if not isinstance(base, dict):
        raise ProtocolError("invalid_base", "designated_base must be an object")
    require_exact_keys(base, ["sha", "source"], ["ref"], "designated_base")
    if not isinstance(base["sha"], str) or not EXACT_SHA_RE.fullmatch(base["sha"]):
        raise ProtocolError("invalid_base", "designated base must be an exact Git or SHA-256 digest")

    lane = document["lane"]
    if not isinstance(lane, dict):
        raise ProtocolError("invalid_lane", "lane must be an object")
    require_exact_keys(lane, ["allowed_paths", "reservation"], [], "lane")
    if not isinstance(lane["allowed_paths"], list) or len(lane["allowed_paths"]) != len(set(lane["allowed_paths"])):
        raise ProtocolError("invalid_allowed_paths", "lane allowed_paths must be a unique array")
    lane["allowed_paths"] = [canonical_relative_path(value) for value in lane["allowed_paths"]]
    reservation = lane["reservation"]
    if not isinstance(reservation, dict):
        raise ProtocolError("invalid_reservation", "reservation must be an object")
    require_exact_keys(
        reservation,
        ["status", "writer", "surface_id", "executor_id", "lease_expires_at", "version"],
        [],
        "reservation",
    )
    if reservation["status"] not in {"none", "active", "released", "expired"}:
        raise ProtocolError("invalid_reservation", "reservation status is invalid")
    if not isinstance(reservation["version"], int) or reservation["version"] < 0:
        raise ProtocolError("invalid_reservation", "reservation version must be non-negative")
    if reservation["lease_expires_at"] is not None:
        parse_timestamp(reservation["lease_expires_at"], "lease_expires_at")

    for field in ("acceptance_criteria", "transitions", "checkpoints", "handoffs", "idempotency"):
        if not isinstance(document[field], list):
            raise ProtocolError("invalid_array", f"{field} must be an array")
    acceptance_ids = set()
    for criterion in document["acceptance_criteria"]:
        if not isinstance(criterion, dict):
            raise ProtocolError("invalid_acceptance_criterion", "acceptance criteria must contain objects")
        require_exact_keys(criterion, ["id", "text", "status"], ["evidence"], "acceptance criterion")
        criterion_id = require_id(criterion["id"], "acceptance criterion id")
        if criterion_id in acceptance_ids:
            raise ProtocolError("duplicate_acceptance_criterion", "acceptance criterion IDs must be unique")
        acceptance_ids.add(criterion_id)
        if not isinstance(criterion["text"], str) or not criterion["text"]:
            raise ProtocolError("invalid_acceptance_criterion", "acceptance criterion text must be non-empty")
        if criterion["status"] not in {"pending", "passed", "failed", "blocked"}:
            raise ProtocolError("invalid_acceptance_criterion", "acceptance criterion status is invalid")
        evidence = criterion.get("evidence", [])
        if (
            not isinstance(evidence, list)
            or len(evidence) != len(set(evidence))
            or any(not isinstance(value, str) or not value for value in evidence)
        ):
            raise ProtocolError(
                "invalid_acceptance_criterion",
                "acceptance criterion evidence must contain unique non-empty strings",
            )
        if criterion["status"] != "pending" and not evidence:
            raise ProtocolError(
                "acceptance_evidence_missing",
                "non-pending acceptance criteria require concrete evidence",
            )
    local_delivery = document.get("local_delivery")
    if local_delivery is not None:
        if not isinstance(local_delivery, dict):
            raise ProtocolError("invalid_local_delivery", "local_delivery must be an object")
        require_exact_keys(
            local_delivery,
            ["envelope_path", "envelope_digest", "registry_digest", "worktree_identity_digest", "seal", "completion"],
            [],
            "local_delivery",
        )
        envelope_path = canonical_relative_path(local_delivery["envelope_path"])
        if not envelope_path.startswith(ENVELOPE_PREFIX):
            raise ProtocolError("invalid_envelope_path", "local-delivery envelopes must use protected local protocol storage")
        local_delivery["envelope_path"] = envelope_path
        require_digest(local_delivery["envelope_digest"], "envelope_digest")
        require_digest(local_delivery["registry_digest"], "registry_digest")
        require_digest(local_delivery["worktree_identity_digest"], "worktree_identity_digest")
        if local_delivery["seal"] is not None:
            seal = local_delivery["seal"]
            if not isinstance(seal, dict):
                raise ProtocolError("invalid_edit_seal", "local-delivery seal must be null or an object")
            require_exact_keys(
                seal,
                ["request_id", "sealed_at", "changed_paths", "path_set_digest", "candidate_digest"],
                [],
                "local-delivery seal",
            )
            require_id(seal["request_id"], "seal request_id")
            parse_timestamp(seal["sealed_at"], "sealed_at")
            if (
                not isinstance(seal["changed_paths"], list)
                or not seal["changed_paths"]
                or len(seal["changed_paths"]) != len(set(seal["changed_paths"]))
            ):
                raise ProtocolError("invalid_edit_seal", "sealed changed_paths must be a non-empty unique array")
            seal["changed_paths"] = [canonical_relative_path(value) for value in seal["changed_paths"]]
            if seal["changed_paths"] != sorted(seal["changed_paths"]):
                raise ProtocolError("invalid_edit_seal", "sealed changed_paths must use canonical sorted order")
            if not set(seal["changed_paths"]).issubset(set(lane["allowed_paths"])):
                raise ProtocolError("invalid_edit_seal", "sealed changed_paths exceed the accepted lane")
            require_digest(seal["path_set_digest"], "path_set_digest")
            require_digest(seal["candidate_digest"], "candidate_digest")
            if seal["path_set_digest"] != canonical_digest_lines(seal["changed_paths"]):
                raise ProtocolError("invalid_edit_seal", "sealed path-set digest does not match changed_paths")
        if local_delivery["completion"] is not None:
            completion = local_delivery["completion"]
            if not isinstance(completion, dict):
                raise ProtocolError("invalid_completion", "local-delivery completion must be null or an object")
            require_exact_keys(
                completion,
                ["request_id", "completed_at", "local_state", "event_path", "body_digest", "event_digest"],
                [],
                "local-delivery completion",
            )
            require_id(completion["request_id"], "completion request_id")
            parse_timestamp(completion["completed_at"], "completed_at")
            if completion["local_state"] != "complete":
                raise ProtocolError("invalid_completion", "local-delivery completion state must be complete")
            event_path = canonical_relative_path(completion["event_path"])
            if not event_path.startswith(".exocortex/events/"):
                raise ProtocolError("invalid_completion", "completion event must remain project-local")
            completion["event_path"] = event_path
            require_digest(completion["body_digest"], "body_digest")
            require_digest(completion["event_digest"], "event_digest")
            if STATES.index(lifecycle["state"]) < STATES.index("human_uat") or reservation["status"] != "released":
                raise ProtocolError(
                    "invalid_completion",
                    "local completion begins at human_uat and requires a released writer; later gates remain separate",
                )
        elif STATES.index(lifecycle["state"]) > STATES.index("human_uat"):
            raise ProtocolError(
                "local_delivery_incomplete",
                "local delivery must be completed before advancing beyond Human UAT",
            )
    transition_by_id: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    for index, transition in enumerate(document["transitions"]):
        if not isinstance(transition, dict):
            raise ProtocolError("invalid_transition_record", "transitions must contain objects")
        require_exact_keys(
            transition,
            [
                "id",
                "request_id",
                "operation",
                "from",
                "to",
                "accepted_at",
                "capability_id",
                "checkpoint_eligible",
                "evidence",
            ],
            [
                "reviewer_surface_id",
                "reviewer_executor_id",
                "review_evidence_hash",
                "review_transition_id",
                "human_uat_attestor",
                "capability_path",
                "capability_digest",
                "intent_digest",
            ],
            "transition",
        )
        transition_id = require_id(transition["id"], "transition id")
        if transition_id in transition_by_id:
            raise ProtocolError("duplicate_transition", "work item contains a duplicate transition ID")
        transition_by_id[transition_id] = (index, transition)
        require_id(transition["request_id"], "transition request_id")
        require_id(transition["capability_id"], "transition capability_id")
        if not isinstance(transition["operation"], str) or not transition["operation"]:
            raise ProtocolError("invalid_transition_record", "transition operation must be non-empty")
        if transition["from"] not in STATES or transition["to"] not in STATES:
            raise ProtocolError("invalid_transition_record", "transition states are invalid")
        transition_pair = (transition["from"], transition["to"])
        if transition_pair not in TRANSITIONS:
            raise ProtocolError("invalid_transition_record", "transition state pair is not allowed")
        parse_timestamp(transition["accepted_at"], "transition accepted_at")
        if not isinstance(transition["checkpoint_eligible"], bool):
            raise ProtocolError("invalid_transition_record", "checkpoint_eligible must be boolean")
        if transition["checkpoint_eligible"] is not TRANSITIONS[transition_pair]:
            raise ProtocolError("invalid_transition_record", "checkpoint eligibility does not match the transition")
        if not isinstance(transition["evidence"], list) or any(
            not isinstance(value, str) or not value for value in transition["evidence"]
        ):
            raise ProtocolError("invalid_transition_record", "transition evidence must contain non-empty strings")
        reviewer_fields = ("reviewer_surface_id", "reviewer_executor_id", "review_evidence_hash")
        if transition["to"] == "independent_review":
            if transition["from"] != "developer_verified" or any(field not in transition for field in reviewer_fields):
                raise ProtocolError("missing_review_attestation", "independent review transition lacks reviewer attestation")
            require_id(transition["reviewer_surface_id"], "reviewer_surface_id")
            require_id(transition["reviewer_executor_id"], "reviewer_executor_id")
            if not isinstance(transition["review_evidence_hash"], str) or not SHA256_RE.fullmatch(
                transition["review_evidence_hash"]
            ):
                raise ProtocolError("invalid_review_evidence", "review evidence must be a SHA-256 digest")
        elif any(field in transition for field in reviewer_fields):
            raise ProtocolError("unexpected_review_attestation", "reviewer attestation belongs only on independent review")
        if transition["to"] == "qa_sit":
            if "review_transition_id" not in transition:
                raise ProtocolError("missing_review_reference", "QA/SIT transition must reference independent review")
            require_id(transition["review_transition_id"], "review_transition_id")
        elif "review_transition_id" in transition:
            raise ProtocolError("unexpected_review_reference", "review transition reference belongs only on QA/SIT")
        if transition["to"] == "human_uat":
            if local_delivery is not None and "human_uat_attestor" in transition:
                if not isinstance(transition["human_uat_attestor"], str) or not transition["human_uat_attestor"]:
                    raise ProtocolError("invalid_human_uat_attestor", "Human UAT attestor must be a non-empty string")
            elif local_delivery is not None:
                raise ProtocolError("missing_human_uat_attestation", "local delivery requires an explicit Human UAT attestor")
            elif "human_uat_attestor" in transition:
                raise ProtocolError(
                    "unexpected_human_uat_attestor",
                    "Human UAT attestation belongs only to local delivery",
                )
        elif "human_uat_attestor" in transition:
            raise ProtocolError("unexpected_human_uat_attestor", "Human UAT attestor belongs only on the Human UAT transition")
        provenance_fields = ("capability_path", "capability_digest", "intent_digest")
        if local_delivery is not None:
            if any(field not in transition for field in provenance_fields):
                raise ProtocolError(
                    "missing_transition_provenance",
                    "local-delivery transitions require capability and intent provenance",
                )
            capability_path = canonical_relative_path(transition["capability_path"])
            expected_capability_path = f"{CAPABILITY_DIR}/{transition['capability_id']}.json"
            if capability_path != expected_capability_path:
                raise ProtocolError(
                    "invalid_transition_provenance",
                    "local-delivery transition capability path must match its capability ID",
                )
            transition["capability_path"] = capability_path
            require_digest(transition["capability_digest"], "transition capability_digest")
            require_digest(transition["intent_digest"], "transition intent_digest")
            if transition["intent_digest"] != transition_record_intent_digest(transition):
                raise ProtocolError(
                    "transition_intent_mismatch",
                    "local-delivery transition record no longer matches its capability-bound intent",
                )
        elif any(field in transition for field in provenance_fields):
            raise ProtocolError(
                "unexpected_transition_provenance",
                "legacy transitions cannot claim local-delivery provenance",
            )
    for index, transition in enumerate(document["transitions"]):
        if transition["to"] != "qa_sit":
            continue
        referenced = transition_by_id.get(transition["review_transition_id"])
        if referenced is None or referenced[0] >= index:
            raise ProtocolError("invalid_review_reference", "QA/SIT review reference must identify a prior transition")
        review = referenced[1]
        if review["from"] != "developer_verified" or review["to"] != "independent_review":
            raise ProtocolError("invalid_review_reference", "QA/SIT review reference is not an independent review transition")
    for handoff in document["handoffs"]:
        if not isinstance(handoff, dict):
            raise ProtocolError("invalid_handoff", "handoffs must contain objects")
        require_exact_keys(
            handoff,
            [
                "id",
                "request_id",
                "created_at",
                "base_sha",
                "candidate_sha",
                "state",
                "writer_status",
                "capability_id",
                "capability_digest",
                "registry_digest",
                "evidence_hashes",
                "closed_gates",
                "first_verification",
                "local_only",
            ],
            [],
            "handoff",
        )
        require_id(handoff["id"], "handoff id")
        require_id(handoff["request_id"], "handoff request_id")
        parse_timestamp(handoff["created_at"], "handoff created_at")
        for field in ("base_sha", "candidate_sha"):
            if not isinstance(handoff[field], str) or not EXACT_SHA_RE.fullmatch(handoff[field]):
                raise ProtocolError("invalid_handoff_sha", f"handoff {field} must be an exact digest")
        for field in ("capability_digest", "registry_digest"):
            if not isinstance(handoff[field], str) or not SHA256_RE.fullmatch(handoff[field]):
                raise ProtocolError("invalid_handoff_digest", f"handoff {field} must be a SHA-256 digest")
        require_id(handoff["capability_id"], "handoff capability_id")
        if not isinstance(handoff["evidence_hashes"], list) or not handoff["evidence_hashes"]:
            raise ProtocolError("missing_handoff_evidence", "handoff requires at least one evidence hash")
        if any(not isinstance(value, str) or not SHA256_RE.fullmatch(value) for value in handoff["evidence_hashes"]):
            raise ProtocolError("invalid_handoff_evidence", "handoff evidence hashes must be SHA-256 digests")
        if not isinstance(handoff["closed_gates"], list) or any(
            not isinstance(value, str) or not value for value in handoff["closed_gates"]
        ):
            raise ProtocolError("invalid_handoff_gates", "handoff closed_gates must contain non-empty strings")
        if not isinstance(handoff["first_verification"], str) or not handoff["first_verification"]:
            raise ProtocolError("invalid_handoff_verification", "handoff requires a first verification step")
        if handoff["local_only"] is not True:
            raise ProtocolError("external_handoff", "protocol handoffs are local-only by default")
    if "retrospectives" in document and not isinstance(document["retrospectives"], list):
        raise ProtocolError("invalid_retrospectives", "retrospectives must be an array")
    request_ids = [item.get("request_id") for item in document["idempotency"] if isinstance(item, dict)]
    if len(request_ids) != len(set(request_ids)):
        raise ProtocolError("duplicate_idempotency", "work item contains duplicate idempotency request IDs")
    return document


def find_replay(document: Dict[str, Any], request_id: str, operation: str) -> Optional[Dict[str, Any]]:
    for item in document["idempotency"]:
        if item.get("request_id") == request_id:
            if item.get("operation") != operation:
                raise ProtocolError("idempotency_conflict", "request ID was already used for another operation")
            return item
    return None


def add_idempotency(
    document: Dict[str, Any],
    request_id: str,
    operation: str,
    result_id: str,
    *,
    accepted_at: Optional[str] = None,
) -> None:
    document["idempotency"].append(
        {
            "request_id": request_id,
            "operation": operation,
            "result_id": result_id,
            "accepted_at": accepted_at or isoformat(utc_now()),
        }
    )


def maybe_fault(point: str) -> None:
    if os.environ.get("EXOCORTEX_TEST_MODE") == "1" and os.environ.get("EXOCORTEX_FAULT_POINT") == point:
        raise ProtocolError("injected_fault", f"fault injected at {point}")


def transaction_path(project_root: Path, request_id: str) -> Path:
    return resolve_repo_path(
        project_root,
        f".exocortex/local/protocol/transactions/{request_id}.json",
    )


def publication_reservation_path(project_root: Path, work_item_id: str) -> Path:
    require_id(work_item_id, "work item id")
    return resolve_repo_path(
        project_root,
        f"{PUBLICATION_RESERVATION_DIR}/{work_item_id}.json",
    )


def _require_exact_retirement_release(
    project_root: Path,
    work_item_relpath: str,
    reservation_path: Path,
    reservation: Dict[str, Any],
) -> None:
    """Accept a pre-release source only when its prior publication retired exactly."""

    publication_id = require_id(reservation["publication_id"], "publication id")
    record_path = resolve_repo_path(
        project_root,
        f"{PUBLICATION_RECORD_DIR}/{publication_id}.json",
        require_exists=True,
    )
    record = load_safe_json(record_path, "retired publication record")
    retirement = record.get("retirement")
    writer_reservation = record.get("reservation")
    idempotency = record.get("idempotency")
    reservation_relpath = reservation_path.relative_to(project_root).as_posix()
    if (
        record.get("schema_version") != "public-v2"
        or record.get("kind") != "publication_record"
        or record.get("id") != publication_id
        or record.get("state") != "retired"
        or record.get("source_work_item") != work_item_relpath
        or record.get("source_work_item_id") != reservation["work_item_id"]
        or record.get("source_work_item_revision") != reservation["source_revision"]
        or record.get("envelope_digest") != reservation["envelope_digest"]
        or record.get("source_reservation_path") != reservation_relpath
        or writer_reservation
        != {"status": "released", "lease_expires_at": reservation["lease_expires_at"]}
        or not isinstance(retirement, dict)
        or retirement.get("retired_at") != reservation["released_at"]
        or not isinstance(retirement.get("prior_revision"), int)
        or record.get("revision") != retirement.get("prior_revision") + 1
        or not isinstance(idempotency, list)
    ):
        raise ProtocolError(
            "publication_reservation_invalid",
            "released publication reservation lacks exact retirement evidence",
        )
    request_id = require_id(retirement.get("request_id"), "retirement request id")
    intent_digest = retirement.get("intent_digest")
    require_digest(intent_digest, "retirement intent digest")
    expected_result = stable_id(
        "publication-retirement", publication_id, request_id, intent_digest
    )
    matches = [
        item
        for item in idempotency
        if isinstance(item, dict)
        and item.get("request_id") == request_id
        and item.get("operation") == "retire_publication"
        and item.get("result_id") == expected_result
    ]
    if len(matches) != 1:
        raise ProtocolError(
            "publication_reservation_invalid",
            "released publication reservation lacks exact retirement idempotency evidence",
        )


def require_publication_lane_available(
    project_root: Path,
    work_item_relpath: str,
    work_item: Dict[str, Any],
    *,
    publication_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Deny parallel protocol mutation while a publication owns the source."""

    path = publication_reservation_path(project_root, work_item["id"])
    if not path.exists() and not path.is_symlink():
        return None
    reservation = load_json(path)
    require_exact_keys(
        reservation,
        [
            "schema_version", "kind", "publication_id", "work_item_id", "work_item_path",
            "source_revision", "source_digest", "envelope_digest", "status",
            "lease_expires_at", "created_at", "released_at",
        ],
        [],
        "publication reservation",
    )
    if reservation["schema_version"] != "public-v2" or reservation["kind"] != "publication_reservation":
        raise ProtocolError("publication_reservation_invalid", "publication reservation has the wrong schema")
    require_id(reservation["publication_id"], "publication id")
    if (
        reservation["work_item_id"] != work_item["id"]
        or canonical_relative_path(reservation["work_item_path"]) != work_item_relpath
        or not isinstance(reservation["source_revision"], int)
        or reservation["source_revision"] < 0
    ):
        raise ProtocolError("publication_reservation_invalid", "publication reservation source binding is invalid")
    require_digest(reservation["source_digest"], "publication source digest")
    require_digest(reservation["envelope_digest"], "publication envelope digest")
    parse_timestamp(reservation["lease_expires_at"], "publication reservation lease")
    parse_timestamp(reservation["created_at"], "publication reservation created_at")
    if reservation["status"] == "active":
        if reservation["released_at"] is not None:
            raise ProtocolError("publication_reservation_invalid", "active publication reservation cannot be released")
        if publication_id != reservation["publication_id"]:
            raise ProtocolError("publication_in_progress", "an active publication owns this work item")
        source_matches = (
            reservation["source_revision"] == work_item["revision"]
            and reservation["source_digest"] == json_digest(work_item)
        )
        transition_recovery = (
            work_item["lifecycle"]["state"] == "awaiting_release"
            and work_item["revision"] == reservation["source_revision"] + 1
        )
        if not source_matches and not transition_recovery:
            raise ProtocolError("publication_source_changed", "publication source changed while reserved")
        return reservation
    if reservation["status"] != "released" or reservation["released_at"] is None:
        raise ProtocolError("publication_reservation_invalid", "publication reservation state is invalid")
    parse_timestamp(reservation["released_at"], "publication reservation released_at")
    if STATES.index(work_item["lifecycle"]["state"]) < STATES.index("awaiting_release"):
        _require_exact_retirement_release(
            project_root,
            work_item_relpath,
            path,
            reservation,
        )
    return reservation


def finalize_transaction(path: Path, journal: Dict[str, Any]) -> None:
    finalized = copy.deepcopy(journal)
    finalized["status"] = "finalized"
    finalized["finalized_at"] = isoformat(utc_now())
    atomic_write_json(path, finalized)


def bounded_recovery_consumed_at(journal: Dict[str, Any], capability: Dict[str, Any]) -> Any:
    created_at = parse_timestamp(journal.get("created_at"), "transaction created_at")
    consumed_at = parse_timestamp(capability.get("status", {}).get("consumed_at"), "consumed_at")
    if consumed_at < created_at or consumed_at > utc_now():
        raise ProtocolError(
            "invalid_recovery_timestamp",
            "capability consumption time must fall between transaction creation and the current time",
        )
    return consumed_at


def guarded_mutation(
    *,
    project_root: Path,
    work_item_relpath: str,
    capability_relpath: str,
    registry_relpath: str,
    request_id: str,
    operation: str,
    surface_id: str,
    executor_id: str,
    adapter_version: str,
    guard_digest: str,
    payload_digest: Optional[str] = None,
    require_sealed: bool = False,
    separate_business_gate: bool = False,
    publication_id: Optional[str] = None,
    publication_commit_sha: Optional[str] = None,
    mutate: Callable[[Dict[str, Any], str], Tuple[Dict[str, Any], str]],
) -> Dict[str, Any]:
    require_id(request_id, "request_id")
    work_item_path = resolve_repo_path(project_root, work_item_relpath, require_exists=True)
    capability_path = resolve_repo_path(project_root, capability_relpath, require_exists=True)
    registry_path = resolve_repo_path(project_root, registry_relpath, require_exists=True)
    journal_path = transaction_path(project_root, request_id)
    lock_path = resolve_repo_path(project_root, f".exocortex/local/protocol/locks/{work_item_path.name}.lock")

    with exclusive_lock(lock_path):
        current = validate_work_item(load_json(work_item_path))
        if separate_business_gate and operation != "transition_work_item":
            raise ProtocolError("invalid_business_gate", "separate business-gate handling applies only to lifecycle transitions")
        if publication_commit_sha is not None and publication_id is None:
            raise ProtocolError("invalid_publication_transition", "published commit verification requires a publication reservation")
        require_publication_lane_available(
            project_root,
            work_item_relpath,
            current,
            publication_id=publication_id,
        )
        envelope = load_local_delivery_binding(
            project_root,
            current,
            require_active=False,
            published_commit_sha=publication_commit_sha,
        )
        if envelope is not None and current["local_delivery"]["seal"] is not None:
            if publication_commit_sha is None:
                require_current_seal(project_root, current)
            else:
                require_committed_seal(project_root, current, publication_commit_sha)
        replay = find_replay(current, request_id, operation)
        if replay is not None:
            if journal_path.exists():
                journal = load_json(journal_path)
                if journal.get("status") != "finalized":
                    finalize_transaction(journal_path, journal)
            return {
                "ok": True,
                "replay": True,
                "request_id": request_id,
                "result_id": replay["result_id"],
                "revision": current["revision"],
                "state": current["lifecycle"]["state"],
            }

        capability_before = load_json(capability_path)
        consumed_recovery = (
            journal_path.exists()
            and capability_before.get("status", {}).get("state") == "consumed"
            and capability_before.get("status", {}).get("consumed_by_request_id") == request_id
        )
        if envelope is not None and not consumed_recovery and not separate_business_gate:
            envelope = load_local_delivery_binding(project_root, current, require_active=True)
        if envelope is not None and not separate_business_gate:
            writer = envelope["writer"]
            if (
                surface_id != writer["surface_id"]
                or executor_id != writer["executor_id"]
                or adapter_version != writer["adapter_version"]
            ):
                raise ProtocolError("writer_mismatch", "current executor is not the envelope-bound writer")
            if operation in {"release_writer", "create_handoff"}:
                raise ProtocolError(
                    "local_delivery_closeout_required",
                    "sealed local delivery must use complete-local-delivery for event, handoff, and writer release",
                )
            if require_sealed or current["local_delivery"]["seal"] is not None:
                if publication_commit_sha is None:
                    require_current_seal(project_root, current)
                else:
                    require_committed_seal(project_root, current, publication_commit_sha)

        authority_kwargs = {
            "operation": operation,
            "work_item_id": current["id"],
            "work_item_revision": current["revision"],
            "surface_id": surface_id,
            "executor_id": executor_id,
            "adapter_version": adapter_version,
            "guard_digest": guard_digest,
            "role": "writer",
            "target_path": work_item_relpath,
            "target_sha": current["designated_base"]["sha"],
            "payload_digest": payload_digest,
            "require_exact_paths": True,
        }
        if journal_path.exists():
            journal = load_json(journal_path)
            require_exact_keys(
                journal,
                [
                    "schema_version",
                    "kind",
                    "request_id",
                    "operation",
                    "capability_id",
                    "work_item_relpath",
                    "before_digest",
                    "after_digest",
                    "after_document",
                    "result_id",
                    "payload_digest",
                    "status",
                    "created_at",
                ],
                ["finalized_at"],
                "transaction journal",
            )
            if journal["request_id"] != request_id or journal["operation"] != operation:
                raise ProtocolError("transaction_conflict", "existing transaction does not match this request")
            if journal["work_item_relpath"] != work_item_relpath:
                raise ProtocolError("transaction_conflict", "transaction belongs to another work-item path")
            if journal["payload_digest"] != payload_digest:
                raise ProtocolError("transaction_conflict", "transaction payload binding differs from the requested effect")
            if journal["status"] == "finalized":
                raise ProtocolError("transaction_inconsistent", "finalized transaction lacks idempotency state")
            journal_created_at = parse_timestamp(journal["created_at"], "transaction created_at")
            if journal_created_at > utc_now():
                raise ProtocolError("invalid_recovery_timestamp", "transaction creation time cannot be in the future")
            if json_digest(journal["after_document"]) != journal["after_digest"]:
                raise ProtocolError("transaction_digest_mismatch", "transaction after-state digest is invalid")
            after_document = validate_work_item(journal["after_document"])
            matching_idempotency = [
                item
                for item in after_document["idempotency"]
                if item.get("request_id") == request_id
                and item.get("operation") == operation
                and item.get("result_id") == journal["result_id"]
            ]
            if len(matching_idempotency) != 1:
                raise ProtocolError("transaction_semantics_mismatch", "transaction after-state lacks exact idempotency evidence")
            current_digest = json_digest(current)
            if current_digest == journal["before_digest"]:
                expected_after, expected_result = mutate(copy.deepcopy(current), journal["created_at"])
                expected_after["revision"] = current["revision"] + 1
                expected_after = validate_work_item(expected_after)
                if (
                    expected_result != journal["result_id"]
                    or json_digest(expected_after) != journal["after_digest"]
                ):
                    raise ProtocolError(
                        "transaction_semantics_mismatch",
                        "transaction after-state does not match the capability-bound mutation intent",
                    )
            capability = load_json(capability_path)
            if capability.get("capability_id") != journal["capability_id"]:
                raise ProtocolError("transaction_capability_conflict", "transaction capability does not match the current capability file")
            if parse_timestamp(capability["approval"]["accepted_at"], "accepted_at") > journal_created_at:
                raise ProtocolError("invalid_recovery_timestamp", "transaction predates its approval capability")
            if consumed_recovery:
                consumed_at = bounded_recovery_consumed_at(journal, capability)
                check_authority(
                    capability_path=capability_path,
                    registry_path=registry_path,
                    request_id=request_id,
                    now=consumed_at,
                    allow_consumed_by_request_id=True,
                    **authority_kwargs,
                )
            else:
                consume_capability(
                    capability_path=capability_path,
                    registry_path=registry_path,
                    request_id=request_id,
                    check_kwargs=authority_kwargs,
                )
            maybe_fault("after_capability_consumed")
            if current_digest == journal["before_digest"]:
                if after_document["revision"] != current["revision"] + 1:
                    raise ProtocolError("transaction_semantics_mismatch", "transaction revision increment is invalid")
                if operation == "seal_local_edit":
                    require_current_seal(project_root, after_document)
                elif envelope is not None and (require_sealed or current["local_delivery"]["seal"] is not None):
                    if publication_commit_sha is None:
                        require_current_seal(project_root, current)
                    else:
                        require_committed_seal(project_root, current, publication_commit_sha)
                atomic_write_json(work_item_path, after_document)
                finalize_transaction(journal_path, journal)
                return {
                    "ok": True,
                    "recovered": True,
                    "request_id": request_id,
                    "result_id": journal["result_id"],
                    "revision": after_document["revision"],
                    "state": after_document["lifecycle"]["state"],
                }
            if current_digest == journal["after_digest"]:
                finalize_transaction(journal_path, journal)
                return {
                    "ok": True,
                    "recovered": True,
                    "request_id": request_id,
                    "result_id": journal["result_id"],
                    "revision": current["revision"],
                    "state": current["lifecycle"]["state"],
                }
            raise ProtocolError("transaction_state_conflict", "work item changed outside the incomplete transaction")

        capability = check_authority(
            capability_path=capability_path,
            registry_path=registry_path,
            request_id=request_id,
            **authority_kwargs,
        )
        mutation_accepted_at = isoformat(utc_now())
        after_document, result_id = mutate(copy.deepcopy(current), mutation_accepted_at)
        after_document["revision"] = current["revision"] + 1
        after_document = validate_work_item(after_document)
        journal = {
            "schema_version": "public-v2",
            "kind": "guarded_transaction",
            "request_id": request_id,
            "operation": operation,
            "capability_id": capability["capability_id"],
            "work_item_relpath": work_item_relpath,
            "before_digest": json_digest(current),
            "after_digest": json_digest(after_document),
            "after_document": after_document,
            "result_id": result_id,
            "payload_digest": payload_digest,
            "status": "intent",
            "created_at": mutation_accepted_at,
        }
        atomic_write_json(journal_path, journal)
        maybe_fault("after_intent")
        consume_capability(
            capability_path=capability_path,
            registry_path=registry_path,
            request_id=request_id,
            check_kwargs=authority_kwargs,
        )
        maybe_fault("after_capability_consumed")
        if operation == "seal_local_edit":
            require_current_seal(project_root, after_document)
        elif envelope is not None and (require_sealed or current["local_delivery"]["seal"] is not None):
            if publication_commit_sha is None:
                require_current_seal(project_root, current)
            else:
                require_committed_seal(project_root, current, publication_commit_sha)
        latest = validate_work_item(load_json(work_item_path))
        if json_digest(latest) != journal["before_digest"]:
            raise ProtocolError("work_item_changed", "work item changed before the guarded atomic replacement")
        atomic_write_json(work_item_path, after_document)
        maybe_fault("after_state_replaced")
        finalize_transaction(journal_path, journal)
        return {
            "ok": True,
            "replay": False,
            "request_id": request_id,
            "result_id": result_id,
            "revision": after_document["revision"],
            "state": after_document["lifecycle"]["state"],
        }


def orient(project_root: Path, work_item_relpath: str) -> Dict[str, Any]:
    path = resolve_repo_path(project_root, work_item_relpath, require_exists=True)
    raw = load_json(path)
    if raw.get("schema_version") == "1.0-planning" and raw.get("kind") == "delivery_work_item":
        for field in ("id", "revision", "lifecycle", "lane", "acceptance_criteria", "transitions", "checkpoints", "handoffs"):
            if field not in raw:
                raise ProtocolError("missing_field", f"planning work item is missing {field}")
        lifecycle = raw["lifecycle"]
        lane = raw["lane"]
        if not isinstance(lifecycle, dict) or lifecycle.get("state") not in STATES:
            raise ProtocolError("invalid_state", "planning work item lifecycle state is invalid")
        if not isinstance(lane, dict) or not isinstance(lane.get("base_sha"), str) or not EXACT_SHA_RE.fullmatch(lane["base_sha"]):
            raise ProtocolError("invalid_base", "planning work item lane lacks an exact base SHA")
        reservation = lane.get("reservation")
        if not isinstance(reservation, dict):
            raise ProtocolError("invalid_reservation", "planning work item reservation is invalid")
        return {
            "ok": True,
            "read_only": True,
            "compatibility_view": "planning-v1",
            "mutation_supported": False,
            "work_item_id": raw["id"],
            "revision": raw["revision"],
            "state": lifecycle["state"],
            "attempt": lifecycle.get("attempt", 0),
            "blocked": lifecycle.get("blocked") is not None,
            "designated_base": {"sha": lane["base_sha"], "source": "planning_lane"},
            "reservation": reservation,
            "acceptance": {
                "total": len(raw["acceptance_criteria"]),
                "passed": sum(1 for item in raw["acceptance_criteria"] if isinstance(item, dict) and item.get("status") == "passed"),
            },
            "transition_count": len(raw["transitions"]),
            "checkpoint_count": len(raw["checkpoints"]),
            "handoff_count": len(raw["handoffs"]),
        }
    document = validate_work_item(raw)
    reservation = document["lane"]["reservation"]
    return {
        "ok": True,
        "read_only": True,
        "work_item_id": document["id"],
        "revision": document["revision"],
        "state": document["lifecycle"]["state"],
        "attempt": document["lifecycle"]["attempt"],
        "blocked": document["lifecycle"]["blocked"] is not None,
        "designated_base": document["designated_base"],
        "reservation": reservation,
        "acceptance": {
            "total": len(document["acceptance_criteria"]),
            "passed": sum(1 for item in document["acceptance_criteria"] if item.get("status") == "passed"),
        },
        "transition_count": len(document["transitions"]),
        "checkpoint_count": len(document["checkpoints"]),
        "handoff_count": len(document["handoffs"]),
    }


def mutation_for_reserve(args: argparse.Namespace) -> Callable[[Dict[str, Any], str], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any], accepted_at: str) -> Tuple[Dict[str, Any], str]:
        if document["lifecycle"]["state"] in {"captured", "triaged", "refined", "done"}:
            raise ProtocolError("wrong_state", "writer reservation is not available in this lifecycle state")
        reservation = document["lane"]["reservation"]
        if reservation["status"] == "active":
            if parse_timestamp(reservation["lease_expires_at"], "lease_expires_at") > parse_timestamp(accepted_at, "accepted_at"):
                raise ProtocolError("writer_conflict", "another writer reservation is active")
            document["lifecycle"]["attempt"] += 1
        expires = parse_timestamp(args.lease_expires_at, "lease_expires_at")
        if expires <= parse_timestamp(accepted_at, "accepted_at"):
            raise ProtocolError("expired_lease", "writer lease must expire in the future")
        result_id = stable_id("reservation", document["id"], args.request_id)
        document["lane"]["reservation"] = {
            "status": "active",
            "writer": args.writer,
            "surface_id": args.surface_id,
            "executor_id": args.executor_id,
            "lease_expires_at": args.lease_expires_at,
            "version": reservation["version"] + 1,
        }
        if document["lifecycle"]["state"] == "ready":
            document["lifecycle"]["state"] = "reserved"
        add_idempotency(document, args.request_id, "reserve_writer", result_id, accepted_at=accepted_at)
        return document, result_id

    return mutate


def mutation_for_transition(args: argparse.Namespace) -> Callable[[Dict[str, Any], str], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any], accepted_at: str) -> Tuple[Dict[str, Any], str]:
        current = document["lifecycle"]["state"]
        key = (current, args.to_state)
        is_local_delivery = document.get("local_delivery") is not None
        if key not in TRANSITIONS:
            raise ProtocolError("invalid_transition", f"transition {current} -> {args.to_state} is not allowed")
        if args.from_state is not None and args.from_state != current:
            raise ProtocolError("stale_state", "declared from-state is stale")
        if (
            is_local_delivery
            and key == ("human_uat", "release_ready")
            and document["local_delivery"]["completion"] is None
        ):
            raise ProtocolError(
                "local_delivery_incomplete",
                "complete-local-delivery must finish local closeout before the separate release-ready gate",
            )
        if is_local_delivery and args.to_state != "developing" and not args.evidence:
            raise ProtocolError("gate_evidence_missing", "local-delivery lifecycle gates require concrete evidence")
        reservation = document["lane"]["reservation"]
        if args.to_state in {"developing", "developer_verified", "independent_review", "qa_sit", "uat_ready"}:
            if reservation["status"] != "active":
                raise ProtocolError("missing_writer", "this transition requires an active writer reservation")
            if reservation["surface_id"] != args.surface_id or reservation["executor_id"] != args.executor_id:
                raise ProtocolError("writer_mismatch", "current executor does not own the writer reservation")
            if parse_timestamp(reservation["lease_expires_at"], "lease_expires_at") <= parse_timestamp(accepted_at, "accepted_at"):
                raise ProtocolError("expired_lease", "writer reservation has expired")
        transition_review_fields: Dict[str, str] = {}
        if args.to_state == "independent_review":
            transition_review_fields = {
                "reviewer_surface_id": args.reviewer_surface_id,
                "reviewer_executor_id": args.reviewer_executor_id,
                "review_evidence_hash": args.review_evidence_hash,
            }
        elif args.to_state == "qa_sit":
            referenced = next(
                (item for item in document["transitions"] if item.get("id") == args.review_transition_id),
                None,
            )
            if referenced is None or referenced.get("from") != "developer_verified" or referenced.get("to") != "independent_review":
                raise ProtocolError("invalid_review_reference", "QA/SIT must reference the accepted independent review transition")
            transition_review_fields = {"review_transition_id": args.review_transition_id}
        if is_local_delivery and args.to_state == "human_uat" and args.human_uat_attestor is not None:
            transition_review_fields["human_uat_attestor"] = args.human_uat_attestor
        transition_provenance: Dict[str, str] = {}
        if is_local_delivery:
            transition_provenance = {
                "capability_path": args.capability_relpath_hint,
                "capability_digest": args.capability_digest_hint,
                "intent_digest": args.transition_intent_digest_hint,
            }
        checkpoint_eligible = TRANSITIONS[key]
        transition_id = stable_id("transition", document["id"], args.request_id, current, args.to_state)
        if is_local_delivery and args.to_state == "human_uat":
            if any(item["status"] in {"failed", "blocked"} for item in document["acceptance_criteria"]):
                raise ProtocolError(
                    "acceptance_not_satisfied",
                    "Human UAT cannot be recorded while an acceptance criterion is failed or blocked",
                )
            if any(
                item["status"] != "pending" or item.get("evidence")
                for item in document["acceptance_criteria"]
            ):
                raise ProtocolError(
                    "acceptance_state_mismatch",
                    "local-delivery criteria must remain pending until the exact Human UAT transition",
                )
            human_uat_evidence = [f"human-uat-transition:{transition_id}", *args.evidence]
            for criterion in document["acceptance_criteria"]:
                if criterion["status"] == "pending":
                    criterion["status"] = "passed"
                criterion_evidence = criterion.setdefault("evidence", [])
                for evidence in human_uat_evidence:
                    if evidence not in criterion_evidence:
                        criterion_evidence.append(evidence)
        document["transitions"].append(
            {
                "id": transition_id,
                "request_id": args.request_id,
                "operation": args.transition_name,
                "from": current,
                "to": args.to_state,
                "accepted_at": accepted_at,
                "capability_id": args.capability_id_hint,
                "checkpoint_eligible": checkpoint_eligible,
                "evidence": list(args.evidence),
                **transition_provenance,
                **transition_review_fields,
            }
        )
        document["lifecycle"]["state"] = args.to_state
        if checkpoint_eligible:
            checkpoint_id = stable_id("checkpoint", document["id"], args.request_id, args.to_state)
            if not any(item.get("id") == checkpoint_id for item in document["checkpoints"]):
                document["checkpoints"].append(
                    {
                        "id": checkpoint_id,
                        "transition_id": transition_id,
                        "request_id": args.request_id,
                        "state": args.to_state,
                        "created_at": accepted_at,
                        "local_only": True,
                    }
                )
        add_idempotency(document, args.request_id, "transition_work_item", transition_id, accepted_at=accepted_at)
        return document, transition_id

    return mutate


def mutation_for_release(args: argparse.Namespace) -> Callable[[Dict[str, Any], str], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any], accepted_at: str) -> Tuple[Dict[str, Any], str]:
        reservation = document["lane"]["reservation"]
        if reservation["status"] != "active":
            raise ProtocolError("no_active_writer", "there is no active writer reservation to release")
        if reservation["surface_id"] != args.surface_id or reservation["executor_id"] != args.executor_id:
            raise ProtocolError("writer_mismatch", "current executor does not own the reservation")
        result_id = stable_id("release", document["id"], args.request_id)
        document["lane"]["reservation"] = {
            "status": "released",
            "writer": None,
            "surface_id": None,
            "executor_id": None,
            "lease_expires_at": None,
            "version": reservation["version"] + 1,
        }
        if document["lifecycle"]["state"] == "reserved":
            document["lifecycle"]["state"] = "ready"
        add_idempotency(document, args.request_id, "release_writer", result_id, accepted_at=accepted_at)
        return document, result_id

    return mutate


def mutation_for_handoff(args: argparse.Namespace) -> Callable[[Dict[str, Any], str], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any], accepted_at: str) -> Tuple[Dict[str, Any], str]:
        handoff_id = stable_id("handoff", document["id"], args.request_id)
        if not isinstance(args.candidate_sha, str) or not EXACT_SHA_RE.fullmatch(args.candidate_sha):
            raise ProtocolError("invalid_candidate_sha", "candidate SHA must be an exact Git or SHA-256 digest")
        if not args.evidence_hash or any(not SHA256_RE.fullmatch(value) for value in args.evidence_hash):
            raise ProtocolError("invalid_handoff_evidence", "handoff requires SHA-256 evidence hashes")
        document["handoffs"].append(
            {
                "id": handoff_id,
                "request_id": args.request_id,
                "created_at": accepted_at,
                "base_sha": document["designated_base"]["sha"],
                "candidate_sha": args.candidate_sha,
                "state": document["lifecycle"]["state"],
                "writer_status": document["lane"]["reservation"]["status"],
                "capability_id": args.capability_id_hint,
                "capability_digest": args.capability_digest_hint,
                "registry_digest": args.registry_digest_hint,
                "evidence_hashes": list(args.evidence_hash),
                "closed_gates": list(args.closed_gate),
                "first_verification": args.first_verification,
                "local_only": True,
            }
        )
        add_idempotency(document, args.request_id, "create_handoff", handoff_id, accepted_at=accepted_at)
        return document, handoff_id

    return mutate


def mutation_for_retrospective(args: argparse.Namespace) -> Callable[[Dict[str, Any], str], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any], accepted_at: str) -> Tuple[Dict[str, Any], str]:
        retrospective_id = stable_id("retrospective", document["id"], args.request_id)
        proposal = load_json(args.proposal)
        document.setdefault("retrospectives", []).append(
            {
                "id": retrospective_id,
                "observations": list(args.observation),
                "proposed_work_item": proposal,
                "authority": "proposal_only",
            }
        )
        add_idempotency(document, args.request_id, "record_retrospective", retrospective_id, accepted_at=accepted_at)
        return document, retrospective_id

    return mutate


def route_models(
    task_path: Path,
    sources_path: Path,
    catalog_path: Path,
    availability_path: Path,
    as_of_text: str,
    current_surface_id: str,
    current_surface_version: str,
    current_surface_session_id: str,
) -> Dict[str, Any]:
    """Select only fresh, available, measured, explicitly eligible models."""
    try:
        as_of = parse_as_of(as_of_text)
    except RegistryError as exc:
        raise ProtocolError(exc.code, exc.message) from exc
    route_now = utc_now()
    if abs((as_of - route_now).total_seconds()) > MAX_ROUTE_CLOCK_SKEW_SECONDS:
        raise ProtocolError(
            "routing_timestamp_out_of_bounds",
            "route as_of must be within 60 seconds of the current UTC runtime clock",
        )

    try:
        task = load_json(task_path)
        sources = validate_source_registry(load_json(sources_path))
        catalog = validate_model_catalog(load_json(catalog_path), sources)
        availability = validate_availability(load_json(availability_path))
        require_fresh_model_evidence(sources, as_of, "source registry")
        require_fresh_model_evidence(catalog, as_of, "routing catalog")
        require_fresh_model_evidence(availability, as_of, "availability evidence")
    except RegistryError as exc:
        raise ProtocolError(exc.code, exc.message) from exc

    catalog_digest = model_evidence_digest(catalog)
    if availability["catalog_digest"] != catalog_digest:
        raise ProtocolError("catalog_digest_mismatch", "availability is not bound to the exact routing catalog")
    current_surface = (
        require_id(current_surface_id, "current_surface_id"),
        require_id(current_surface_version, "current_surface_version"),
        require_id(current_surface_session_id, "current_surface_session_id"),
    )
    availability_surface = (
        availability["surface_id"],
        availability["surface_version"],
        availability["surface_session_id"],
    )
    if availability_surface != current_surface:
        raise ProtocolError(
            "availability_surface_mismatch",
            "availability is not bound to the exact current surface, version, and session",
        )
    require_exact_keys(
        task,
        [
            "required_capabilities",
            "risk",
            "evaluation_profile_id",
            "max_cost_per_success_microusd",
            "delegates",
        ],
        [],
        "routing task",
    )
    risk_rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    def validate_requirement(requirement: Dict[str, Any], label: str, *, delegate: bool) -> None:
        required = [
            "required_capabilities",
            "risk",
            "evaluation_profile_id",
            "max_cost_per_success_microusd",
        ]
        if delegate:
            required.insert(0, "id")
        require_exact_keys(
            requirement,
            required,
            [] if delegate else ["delegates"],
            label,
        )
        if delegate:
            require_id(requirement["id"], "delegate id")
        if requirement["risk"] not in risk_rank:
            raise ProtocolError("invalid_risk", f"{label} risk is invalid")
        capabilities = requirement["required_capabilities"]
        if (
            not isinstance(capabilities, list)
            or not capabilities
            or len(capabilities) != len(set(capabilities))
            or any(not isinstance(value, str) or not value for value in capabilities)
        ):
            raise ProtocolError("invalid_capabilities", f"{label} capabilities must be unique non-empty strings")
        require_id(requirement["evaluation_profile_id"], f"{label} evaluation_profile_id")
        ceiling = requirement["max_cost_per_success_microusd"]
        if ceiling is not None and (
            not isinstance(ceiling, int) or isinstance(ceiling, bool) or ceiling < 0
        ):
            raise ProtocolError("invalid_cost_ceiling", f"{label} cost ceiling must be null or a non-negative integer")

    validate_requirement(task, "routing task", delegate=False)
    if not isinstance(task["delegates"], list):
        raise ProtocolError("invalid_delegates", "delegates must be an array")
    delegate_ids: set[str] = set()
    for delegate_task in task["delegates"]:
        if not isinstance(delegate_task, dict):
            raise ProtocolError("invalid_delegate", "delegate entries must be objects")
        validate_requirement(delegate_task, "delegate task", delegate=True)
        if delegate_task["id"] in delegate_ids:
            raise ProtocolError(
                "duplicate_delegate_id",
                f"delegate IDs must be unique: {delegate_task['id']}",
            )
        delegate_ids.add(delegate_task["id"])

    available_ids = set(availability["model_ids"])
    catalog_ids = {model["id"] for model in catalog["models"]}
    source_by_id = {source["id"]: source for source in sources["sources"]}
    if not available_ids.issubset(catalog_ids):
        raise ProtocolError("unknown_available_model", "availability contains a model absent from the catalog")

    def measured_candidate(
        model: Dict[str, Any],
        requirement: Dict[str, Any],
        *,
        require_parent: bool,
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], int]]:
        if model["id"] not in available_ids:
            return None
        if model["routing_status"] != "eligible" or model["lifecycle"] != "active":
            return None
        if any(
            not source_is_fresh(source_by_id[source_id], as_of)
            for source_id in model["source_ids"]
        ):
            return None
        if require_parent and not model["parent_capable"]:
            return None
        if risk_rank[model["max_risk"]] < risk_rank[requirement["risk"]]:
            return None
        if not set(requirement["required_capabilities"]).issubset(set(model["capabilities"])):
            return None
        profiles = [
            profile
            for profile in model["evaluation_profiles"]
            if profile["id"] == requirement["evaluation_profile_id"]
            and profile["status"] == "verified"
            and profile["successes"] > 0
            and parse_timestamp(profile["evaluated_at"], "profile evaluated_at") <= as_of
            and parse_timestamp(profile["expires_at"], "profile expires_at") > as_of
        ]
        if len(profiles) != 1:
            return None
        profile = profiles[0]
        cost_per_success = (
            profile["total_cost_microusd"] + profile["successes"] - 1
        ) // profile["successes"]
        ceiling = requirement["max_cost_per_success_microusd"]
        if ceiling is not None and cost_per_success > ceiling:
            return None
        return model, profile, cost_per_success

    parent_candidates = [
        candidate
        for model in catalog["models"]
        if (candidate := measured_candidate(model, task, require_parent=True)) is not None
    ]
    if not parent_candidates:
        raise ProtocolError(
            "no_capable_parent",
            "no fresh, available, verified, budget-compatible eligible model can own the bounded task",
        )
    parent, parent_profile, parent_cost = min(
        parent_candidates,
        key=lambda item: (item[2], item[0]["id"]),
    )

    routed_delegates = []
    evidence_hashes = {availability["evidence_sha256"], parent_profile["evidence_sha256"]}
    for bounded in task["delegates"]:
        delegate_candidates = [
            candidate
            for model in catalog["models"]
            if (candidate := measured_candidate(model, bounded, require_parent=False)) is not None
        ]
        if delegate_candidates:
            chosen, profile, cost = min(delegate_candidates, key=lambda item: (item[2], item[0]["id"]))
            escalated = chosen["id"] == parent["id"]
        else:
            parent_for_delegate = measured_candidate(parent, bounded, require_parent=False)
            if parent_for_delegate is None:
                raise ProtocolError(
                    "no_capable_delegate",
                    f"no verified model can perform delegate task: {bounded['id']}",
                )
            chosen, profile, cost = parent_for_delegate
            escalated = True
        evidence_hashes.add(profile["evidence_sha256"])
        routed_delegates.append(
            {
                "task_id": bounded["id"],
                "model_id": chosen["id"],
                "profile_id": profile["id"],
                "cost_per_success_microusd": cost,
                "escalated_to_parent": escalated,
            }
        )
    return {
        "ok": True,
        "policy": "fresh_source_backed_cost_per_success_v1",
        "as_of": as_of_text,
        "source_registry_digest": model_evidence_digest(sources),
        "catalog_digest": catalog_digest,
        "availability_digest": model_evidence_digest(availability),
        "surface_id": availability["surface_id"],
        "surface_version": availability["surface_version"],
        "surface_session_id": availability["surface_session_id"],
        "availability_scope": availability["scope"],
        "evidence_sha256s": sorted(evidence_hashes),
        "parent_model_id": parent["id"],
        "parent_profile_id": parent_profile["id"],
        "parent_cost_per_success_microusd": parent_cost,
        "delegates": routed_delegates,
        "normative_model_pin": False,
    }


def add_mutation_args(parser: argparse.ArgumentParser, *, capability_required: bool = True) -> None:
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--work-item", required=True)
    parser.add_argument(
        "--capability",
        required=capability_required,
        help="project-relative path under .exocortex/local/protocol/capabilities/",
    )
    parser.add_argument("--registry", default=REGISTRY_RELPATH)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--surface-id", required=True)
    parser.add_argument("--executor-id", required=True)
    parser.add_argument("--adapter-version", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    orient_parser = commands.add_parser("orient")
    orient_parser.add_argument("--project-root", type=Path, required=True)
    orient_parser.add_argument("--work-item", required=True)

    route_parser = commands.add_parser("route")
    route_parser.add_argument("--project-root", type=Path, required=True)
    route_parser.add_argument("--task", required=True, help="project-relative routing task JSON")
    route_parser.add_argument("--sources", default=".exocortex/model-source-registry.json")
    route_parser.add_argument("--catalog", default=".exocortex/model-routing-catalog.json")
    route_parser.add_argument("--availability", required=True, help="project-relative local availability JSON")
    route_parser.add_argument(
        "--as-of",
        required=True,
        help="current UTC routing timestamp; must be within 60 seconds of the runtime clock",
    )
    route_parser.add_argument("--current-surface-id", required=True)
    route_parser.add_argument("--current-surface-version", required=True)
    route_parser.add_argument("--current-surface-session-id", required=True)

    bootstrap = commands.add_parser("bootstrap-local-delivery")
    bootstrap.add_argument("--project-root", type=Path, required=True)
    bootstrap.add_argument("--envelope-source", type=Path, required=True)
    bootstrap.add_argument("--request-id", required=True)

    seal = commands.add_parser("seal-local-edit")
    seal.add_argument("--project-root", type=Path, required=True)
    seal.add_argument("--work-item", required=True)
    seal.add_argument("--request-id", required=True)
    seal.add_argument("--surface-id", required=True)
    seal.add_argument("--executor-id", required=True)
    seal.add_argument("--adapter-version", required=True)

    complete = commands.add_parser("complete-local-delivery")
    complete.add_argument("--project-root", type=Path, required=True)
    complete.add_argument("--work-item", required=True)
    complete.add_argument("--request-id", required=True)
    complete.add_argument("--surface-id", required=True)
    complete.add_argument("--executor-id", required=True)
    complete.add_argument("--adapter-version", required=True)
    complete.add_argument("--body-file", type=Path, required=True)

    reserve = commands.add_parser("reserve")
    add_mutation_args(reserve)
    reserve.add_argument("--writer", required=True)
    reserve.add_argument("--lease-expires-at", required=True)

    transition = commands.add_parser("transition")
    add_mutation_args(transition, capability_required=False)
    transition.add_argument("--from-state")
    transition.add_argument("--to-state", choices=STATES, required=True)
    transition.add_argument("--transition-name", required=True)
    transition.add_argument("--evidence", action="append", default=[])
    transition.add_argument("--reviewer-surface-id")
    transition.add_argument("--reviewer-executor-id")
    transition.add_argument("--review-evidence-hash")
    transition.add_argument("--review-transition-id")
    transition.add_argument("--human-uat-attestor")

    release = commands.add_parser("release")
    add_mutation_args(release)

    handoff = commands.add_parser("handoff")
    add_mutation_args(handoff)
    handoff.add_argument("--candidate-sha", required=True)
    handoff.add_argument("--evidence-hash", action="append", required=True)
    handoff.add_argument("--closed-gate", action="append", default=[])
    handoff.add_argument("--first-verification", required=True)

    retrospective = commands.add_parser("retrospective")
    add_mutation_args(retrospective)
    retrospective.add_argument("--proposal", required=True, help="project-relative proposal JSON")
    retrospective.add_argument("--observation", action="append", default=[])
    return parser


def transition_intent_digest(args: argparse.Namespace) -> str:
    return json_digest(
        {
            "operation": "transition_work_item",
            "from_state": args.from_state,
            "to_state": args.to_state,
            "transition_name": args.transition_name,
            "evidence": list(args.evidence),
            "reviewer_surface_id": args.reviewer_surface_id,
            "reviewer_executor_id": args.reviewer_executor_id,
            "review_evidence_hash": args.review_evidence_hash,
            "review_transition_id": args.review_transition_id,
            "human_uat_attestor": args.human_uat_attestor,
        }
    )


def transition_record_intent_digest(transition: Dict[str, Any]) -> str:
    return json_digest(
        {
            "operation": "transition_work_item",
            "from_state": transition["from"],
            "to_state": transition["to"],
            "transition_name": transition["operation"],
            "evidence": list(transition["evidence"]),
            "reviewer_surface_id": transition.get("reviewer_surface_id"),
            "reviewer_executor_id": transition.get("reviewer_executor_id"),
            "review_evidence_hash": transition.get("review_evidence_hash"),
            "review_transition_id": transition.get("review_transition_id"),
            "human_uat_attestor": transition.get("human_uat_attestor"),
        }
    )


def validate_transition_cli_fields(
    args: argparse.Namespace,
    registry_path: Path,
    *,
    local_delivery: bool,
) -> None:
    review_attestation = (args.reviewer_surface_id, args.reviewer_executor_id, args.review_evidence_hash)
    if args.to_state == "independent_review":
        if any(value is None for value in review_attestation):
            raise ProtocolError("missing_review_attestation", "independent review requires reviewer identity and evidence digest")
        reviewer_surface_id = require_id(args.reviewer_surface_id, "reviewer_surface_id")
        reviewer_executor_id = require_id(args.reviewer_executor_id, "reviewer_executor_id")
        if (reviewer_surface_id, reviewer_executor_id) == (args.surface_id, args.executor_id):
            raise ProtocolError("reviewer_not_independent", "independent reviewer must differ from the active writer")
        if not SHA256_RE.fullmatch(args.review_evidence_hash):
            raise ProtocolError("invalid_review_evidence", "review evidence must be a SHA-256 digest")
        registry = validate_registry(load_json(registry_path))
        matches = [
            item
            for item in registry["executors"]
            if item["surface_id"] == reviewer_surface_id and item["executor_id"] == reviewer_executor_id
        ]
        if not matches:
            raise ProtocolError("unregistered_reviewer", "independent reviewer is not registered")
        reviewer = matches[0]
        if (
            reviewer["status"] != "active"
            or reviewer["revoked_at"] is not None
            or parse_timestamp(reviewer["expires_at"], "reviewer expires_at") <= utc_now()
        ):
            raise ProtocolError("inactive_reviewer", "independent reviewer registration is inactive")
        if set(reviewer["roles"]) != {"read_only"}:
            raise ProtocolError("reviewer_role_denied", "independent reviewer must have an exclusively read-only role")
        if args.review_transition_id is not None:
            raise ProtocolError("unexpected_review_reference", "review reference is supplied only when entering QA/SIT")
    elif args.to_state == "qa_sit":
        if any(value is not None for value in review_attestation):
            raise ProtocolError("unexpected_review_attestation", "reviewer attestation belongs only on independent review")
        if args.review_transition_id is None:
            raise ProtocolError("missing_review_reference", "QA/SIT requires the independent review transition ID")
        require_id(args.review_transition_id, "review_transition_id")
    elif any(value is not None for value in (*review_attestation, args.review_transition_id)):
        raise ProtocolError("unexpected_review_fields", "review fields do not apply to this transition")
    if args.to_state == "human_uat" and local_delivery:
        if not isinstance(args.human_uat_attestor, str) or not args.human_uat_attestor:
            raise ProtocolError("missing_human_uat_attestation", "Human UAT requires an explicit approving authority")
    elif args.human_uat_attestor is not None:
        raise ProtocolError(
            "unexpected_human_uat_attestor",
            "Human UAT attestation belongs only to a local-delivery Human UAT transition",
        )


def preflight_local_transition(
    project_root: Path,
    current: Dict[str, Any],
    args: argparse.Namespace,
) -> None:
    require_current_seal(project_root, current)
    after, _ = mutation_for_transition(args)(copy.deepcopy(current), isoformat(utc_now()))
    after["revision"] = current["revision"] + 1
    validate_work_item(after)


def verify_internal_transition_replay(
    project_root: Path,
    current: Dict[str, Any],
    replay: Dict[str, Any],
    args: argparse.Namespace,
    expected_intent_digest: str,
) -> str:
    request_id = args.request_id
    matches = [
        item
        for item in current["transitions"]
        if item.get("id") == replay["result_id"] and item.get("request_id") == request_id
    ]
    if len(matches) != 1:
        raise ProtocolError("transaction_inconsistent", "transition replay lacks its exact recorded transition")
    transition = matches[0]
    if transition_record_intent_digest(transition) != expected_intent_digest or transition.get("intent_digest") != expected_intent_digest:
        raise ProtocolError("idempotency_conflict", "transition replay intent differs from the accepted request")
    capability_relpath = transition.get("capability_path")
    expected_relpath = internal_capability_relpath(current["id"], "transition_work_item", request_id)
    if capability_relpath != expected_relpath:
        raise ProtocolError("transition_capability_mismatch", "transition replay does not reference its deterministic capability")
    capability_path = resolve_repo_path(project_root, capability_relpath, require_exists=True)
    capability = load_safe_json(capability_path, "transition replay capability")
    if (
        capability.get("capability_id") != transition.get("capability_id")
        or active_capability_digest(capability) != transition.get("capability_digest")
        or capability.get("scope") != {
            "allowed_paths": [f"{WORK_ITEM_PREFIX}{current['id']}.json"],
            "target_sha": current["designated_base"]["sha"],
            "payload_digest": expected_intent_digest,
        }
        or capability.get("status", {}).get("state") != "consumed"
        or capability.get("status", {}).get("consumed_by_request_id") != request_id
    ):
        raise ProtocolError("transition_capability_mismatch", "transition replay capability provenance is invalid")
    journal_path = transaction_path(project_root, request_id)
    journal = load_safe_json(journal_path, "transition replay transaction")
    require_exact_keys(
        journal,
        [
            "schema_version",
            "kind",
            "request_id",
            "operation",
            "capability_id",
            "work_item_relpath",
            "before_digest",
            "after_digest",
            "after_document",
            "result_id",
            "payload_digest",
            "status",
            "created_at",
        ],
        ["finalized_at"],
        "transition replay transaction",
    )
    status = journal["status"]
    if (
        journal.get("schema_version") != "public-v2"
        or journal.get("kind") != "guarded_transaction"
        or journal.get("operation") != "transition_work_item"
        or journal.get("request_id") != request_id
        or journal.get("capability_id") != transition.get("capability_id")
        or journal.get("work_item_relpath") != f"{WORK_ITEM_PREFIX}{current['id']}.json"
        or journal.get("result_id") != transition.get("id")
        or journal.get("payload_digest") != expected_intent_digest
        or journal.get("created_at") != transition.get("accepted_at")
        or status not in {"intent", "finalized"}
        or (status == "intent" and "finalized_at" in journal)
        or (status == "finalized" and "finalized_at" not in journal)
    ):
        raise ProtocolError("transition_transaction_mismatch", "transition replay transaction provenance is invalid")
    require_digest(journal["before_digest"], "transition replay before_digest")
    require_digest(journal["after_digest"], "transition replay after_digest")
    after_document = validate_work_item(copy.deepcopy(journal["after_document"]))
    if json_digest(after_document) != journal["after_digest"]:
        raise ProtocolError("transition_transaction_mismatch", "transition replay after-state digest is invalid")
    if after_document != current or json_digest(current) != journal["after_digest"]:
        raise ProtocolError(
            "transition_transaction_mismatch",
            "transition replay is not the exact current work-item state",
        )

    consumed_at = bounded_recovery_consumed_at(journal, capability)
    executor = capability.get("executor", {})
    check_authority(
        capability_path=capability_path,
        registry_path=resolve_repo_path(project_root, REGISTRY_RELPATH, require_exists=True),
        operation="transition_work_item",
        work_item_id=current["id"],
        work_item_revision=capability.get("work_item_revision"),
        request_id=request_id,
        surface_id=executor.get("surface_id"),
        executor_id=executor.get("executor_id"),
        adapter_version=executor.get("adapter_version"),
        guard_digest=current_guard_digest(),
        role="writer",
        target_path=f"{WORK_ITEM_PREFIX}{current['id']}.json",
        target_sha=current["designated_base"]["sha"],
        payload_digest=expected_intent_digest,
        require_exact_paths=True,
        now=consumed_at,
        allow_consumed_by_request_id=True,
    )
    if status == "finalized":
        finalized_at = parse_timestamp(journal["finalized_at"], "transition replay finalized_at")
        if finalized_at < consumed_at or finalized_at > utc_now():
            raise ProtocolError("invalid_recovery_timestamp", "transition replay finalization time is invalid")
    reconstructed_before = copy.deepcopy(after_document)
    reconstructed_before["revision"] -= 1
    reconstructed_before["lifecycle"]["state"] = transition["from"]
    if not reconstructed_before["transitions"] or reconstructed_before["transitions"].pop() != transition:
        raise ProtocolError("transition_transaction_mismatch", "transition replay tail is inconsistent")
    if transition["checkpoint_eligible"]:
        if (
            not reconstructed_before["checkpoints"]
            or reconstructed_before["checkpoints"][-1].get("transition_id") != transition["id"]
        ):
            raise ProtocolError("transition_transaction_mismatch", "transition replay checkpoint is inconsistent")
        reconstructed_before["checkpoints"].pop()
    if (
        not reconstructed_before["idempotency"]
        or reconstructed_before["idempotency"][-1].get("request_id") != request_id
        or reconstructed_before["idempotency"][-1].get("operation") != "transition_work_item"
        or reconstructed_before["idempotency"][-1].get("result_id") != transition["id"]
    ):
        raise ProtocolError("transition_transaction_mismatch", "transition replay idempotency is inconsistent")
    reconstructed_before["idempotency"].pop()
    if transition["to"] == "human_uat":
        for criterion in reconstructed_before["acceptance_criteria"]:
            criterion["status"] = "pending"
            criterion["evidence"] = []
    reconstructed_before = validate_work_item(reconstructed_before)
    if json_digest(reconstructed_before) != journal["before_digest"]:
        raise ProtocolError("transition_transaction_mismatch", "transition replay before-state is inconsistent")

    args.capability_id_hint = capability["capability_id"]
    args.capability_relpath_hint = capability_relpath
    args.capability_digest_hint = active_capability_digest(capability)
    args.transition_intent_digest_hint = expected_intent_digest
    expected_after, expected_result = mutation_for_transition(args)(
        copy.deepcopy(reconstructed_before),
        journal["created_at"],
    )
    expected_after["revision"] = reconstructed_before["revision"] + 1
    expected_after = validate_work_item(expected_after)
    if expected_result != journal["result_id"] or expected_after != after_document:
        raise ProtocolError("transition_transaction_mismatch", "transition replay mutation semantics are inconsistent")
    return capability_relpath


def run_mutation(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = resolve_project_root(args.project_root)
    if args.registry != REGISTRY_RELPATH:
        raise ProtocolError("invalid_registry_path", "executor registry path is fixed by the public contract")
    if not args.work_item.startswith(WORK_ITEM_PREFIX):
        raise ProtocolError("invalid_work_item_path", "mutable work items must use the project-local runtime work-item directory")
    registry_path = resolve_repo_path(project_root, args.registry, require_exists=True)
    current = validate_work_item(
        load_json(resolve_repo_path(project_root, args.work_item, require_exists=True))
    )
    if current.get("local_delivery") is not None:
        require_absolute_project_root(args.project_root)
    local_transition_digest: Optional[str] = None
    separate_business_gate = False
    if args.command == "transition":
        local_delivery = current.get("local_delivery")
        validate_transition_cli_fields(
            args,
            registry_path,
            local_delivery=local_delivery is not None,
        )
        if local_delivery is not None and args.from_state is None:
            raise ProtocolError("missing_from_state", "local-delivery transition capabilities require an exact from-state")
        internal_transition = (
            local_delivery is not None
            and (args.from_state, args.to_state) in LOCAL_DELIVERY_INTERNAL_TRANSITIONS
        )
        if internal_transition and args.capability is not None:
            raise ProtocolError(
                "caller_capability_forbidden",
                "pre-UAT local-delivery transitions derive their capability internally",
            )
        separate_business_gate = (
            local_delivery is not None
            and (args.from_state, args.to_state) == ("human_uat", "release_ready")
        )
        if (
            local_delivery is not None
            and (args.from_state, args.to_state) == ("human_uat", "release_ready")
            and local_delivery["completion"] is None
        ):
            raise ProtocolError(
                "local_delivery_incomplete",
                "complete-local-delivery must finish local closeout before the separate release-ready gate",
            )
        if local_delivery is not None:
            envelope = load_local_delivery_binding(project_root, current, require_active=False)
            if (args.from_state, args.to_state) == ("human_uat", "release_ready"):
                require_local_completion_provenance(
                    project_root,
                    current,
                    envelope,
                    release_request_id=args.request_id,
                )
            if args.to_state == "human_uat" and args.human_uat_attestor != envelope["approval"]["approved_by"]:
                raise ProtocolError("human_uat_authority_mismatch", "Human UAT authority does not match the accepted envelope")
            local_transition_digest = transition_intent_digest(args)
        if internal_transition:
            replay = find_replay(current, args.request_id, "transition_work_item")
            if replay is not None:
                args.capability = verify_internal_transition_replay(
                    project_root,
                    current,
                    replay,
                    args,
                    local_transition_digest,
                )
            else:
                envelope = load_local_delivery_binding(project_root, current, require_active=True)
                capability_relpath = internal_capability_relpath(
                    current["id"],
                    "transition_work_item",
                    args.request_id,
                )
                args.capability_id_hint = Path(capability_relpath).stem
                args.capability_relpath_hint = capability_relpath
                args.capability_digest_hint = "0" * 64
                args.transition_intent_digest_hint = local_transition_digest
                preflight_local_transition(project_root, current, args)
                args.capability = materialize_internal_capability(
                    project_root=project_root,
                    work_item=current,
                    envelope=envelope,
                    operation="transition_work_item",
                    request_id=args.request_id,
                    allowed_paths=[args.work_item],
                    payload_digest=local_transition_digest,
                )
        elif args.capability is None:
            raise ProtocolError(
                "missing_capability",
                "this transition requires a caller-supplied capability from its separate business gate",
            )

    if args.capability is None or not args.capability.startswith(CAPABILITY_PREFIX):
        raise ProtocolError("invalid_capability_path", "capability must be project-local protocol state")
    capability_path = resolve_repo_path(project_root, args.capability, require_exists=True)
    capability_document = load_json(capability_path)
    if args.command in {"transition", "handoff"}:
        args.capability_id_hint = require_id(capability_document.get("capability_id"), "capability_id")
    if args.command == "transition":
        args.capability_relpath_hint = canonical_relative_path(args.capability)
        args.capability_digest_hint = active_capability_digest(capability_document)
        args.transition_intent_digest_hint = local_transition_digest
        if current.get("local_delivery") is not None:
            expected_capability_path = f"{CAPABILITY_DIR}/{args.capability_id_hint}.json"
            if args.capability_relpath_hint != expected_capability_path:
                raise ProtocolError(
                    "invalid_capability_path",
                    "local-delivery transition capability filename must match its capability ID",
                )
    if args.command == "handoff":
        args.capability_digest_hint = active_capability_digest(capability_document)
        args.registry_digest_hint = json_digest(load_json(registry_path))
    if args.command == "retrospective":
        args.proposal = resolve_repo_path(project_root, args.proposal, require_exists=True)
    common = {
        "project_root": project_root,
        "work_item_relpath": args.work_item,
        "capability_relpath": args.capability,
        "registry_relpath": args.registry,
        "request_id": args.request_id,
        "surface_id": args.surface_id,
        "executor_id": args.executor_id,
        "adapter_version": args.adapter_version,
        "guard_digest": current_guard_digest(),
    }
    if args.command == "reserve":
        return guarded_mutation(operation="reserve_writer", mutate=mutation_for_reserve(args), **common)
    if args.command == "transition":
        return guarded_mutation(
            operation="transition_work_item",
            payload_digest=local_transition_digest,
            require_sealed=args.to_state != "developing",
            separate_business_gate=separate_business_gate,
            mutate=mutation_for_transition(args),
            **common,
        )
    if args.command == "release":
        return guarded_mutation(operation="release_writer", mutate=mutation_for_release(args), **common)
    if args.command == "handoff":
        return guarded_mutation(operation="create_handoff", mutate=mutation_for_handoff(args), **common)
    if args.command == "retrospective":
        return guarded_mutation(operation="record_retrospective", mutate=mutation_for_retrospective(args), **common)
    raise ProtocolError("unknown_command", "unknown mutation command")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "orient":
            result = orient(resolve_project_root(args.project_root), args.work_item)
        elif args.command == "route":
            root = resolve_project_root(args.project_root)
            result = route_models(
                resolve_repo_path(root, args.task, require_exists=True),
                resolve_repo_path(root, args.sources, require_exists=True),
                resolve_repo_path(root, args.catalog, require_exists=True),
                resolve_repo_path(root, args.availability, require_exists=True),
                args.as_of,
                args.current_surface_id,
                args.current_surface_version,
                args.current_surface_session_id,
            )
        elif args.command == "bootstrap-local-delivery":
            result = bootstrap_local_delivery(args)
        elif args.command == "seal-local-edit":
            result = seal_local_edit(args)
        elif args.command == "complete-local-delivery":
            result = complete_local_delivery(args)
        else:
            result = run_mutation(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except ProtocolError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
