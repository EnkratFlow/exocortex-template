#!/usr/bin/env python3
"""Guarded publication of one sealed candidate to one new draft pull request.

The command deliberately exposes no merge, ready-for-review, tag, release,
deployment, promotion, or rollout operation. Runtime envelopes, capabilities,
transactions, and records remain ignored project-local data.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import ssl
import stat
import subprocess
import sys
import tempfile
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

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
from orchestrate_work_item import (
    REGISTRY_RELPATH,
    candidate_change_evidence,
    canonical_digest_lines,
    current_changed_paths,
    exclusive_write_json,
    guarded_mutation,
    is_local_runtime_path,
    is_sensitive_path,
    load_local_delivery_binding,
    load_safe_json,
    mutation_for_transition,
    publication_reservation_path,
    read_local_protocol_input,
    require_publication_lane_available,
    require_local_completion_provenance,
    read_safe_regular_bytes,
    source_file_fingerprint,
    stable_id,
    transition_intent_digest,
    validate_work_item,
)


PUBLIC_VERSION = "public-v2"
ENVELOPE_INBOX_PREFIX = ".exocortex/local/protocol/inbox/"
ENVELOPE_STORE_PREFIX = ".exocortex/local/protocol/envelopes/"
PUBLICATION_PREFIX = ".exocortex/local/protocol/publications/"
CAPABILITY_PREFIX = ".exocortex/local/protocol/capabilities/"
TRANSACTION_PREFIX = ".exocortex/local/protocol/transactions/"
LOCK_PREFIX = ".exocortex/local/protocol/locks/"
SOURCE_WORK_PREFIX = ".exocortex/work-items/"
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
GIT_SHA_RE = re.compile(r"^[a-f0-9]{40}$")
CHECKSUM_LINE_RE = re.compile(r"^([a-f0-9]{64})  ([^\r\n]+)$")
FILEMODE_LINE_RE = re.compile(r"^(0644|0755)  ([^\r\n]+)$")
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REMOTE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
FORBIDDEN_BRANCHES = {"main", "master", "trunk"}
STATES = ("authorized", "committed", "pushed", "draft_pr_verified", "complete", "effect_unknown", "retired")
SOURCE_POST_PUBLICATION_STATES = {
    "awaiting_release", "deployment_approved", "deployed", "hypercare", "done",
}
OPERATIONS = ("commit_publication", "push_publication", "create_draft_pr", "complete_publication")
MAX_ENVELOPE_BYTES = 128 * 1024
MAX_METADATA_BYTES = 64 * 1024
MAX_SOURCE_FILE_BYTES = 64 * 1024 * 1024
MAX_REPOSITORY_IDENTITY_BYTES = 256 * 1024
GITHUB_API_HOST = "api.github.com"
PUBLIC_IDENTITY = {"name": "EnkratFlow Release", "email": "noreply@github.com"}
REQUIRED_EFFECTS = {
    "stage_exact_paths": True,
    "one_local_commit": True,
    "create_only_named_branch_push": True,
    "draft_pr_create": True,
    "merge": False,
    "mark_ready": False,
    "tag": False,
    "release": False,
    "deploy": False,
    "promote": False,
    "downstream_rollout": False,
}
GIT_ENV_DENY = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "GIT_COMMITTER_DATE",
}
SAFE_PROCESS_ENV = (
    "PATH", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL", "LC_CTYPE",
    "SYSTEMROOT", "COMSPEC", "PATHEXT",
)
TRANSPORT_CONFIG_ENV = ("HOME", "XDG_CONFIG_HOME", "APPDATA", "LOCALAPPDATA")
IMPLEMENTATION_ROOT = Path(__file__).resolve(strict=True).parents[2]
TRUSTED_RUNTIME_FILES = (
    ".exocortex/scripts/authority_guard.py",
    ".exocortex/scripts/model_registry.py",
    ".exocortex/scripts/orchestrate_work_item.py",
    ".exocortex/scripts/publish_candidate.py",
    "scripts/check-public-release.py",
)
TRUSTED_TOOL_NAMES = ("python", "git", "gh")
_TRUSTED_TOOLS: Dict[str, Dict[str, Any]] = {}
_TRUSTED_RUNTIME_STATE: Dict[str, Dict[str, Any]] = {}


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _regular_file_digest(path: Path, field: str, *, maximum: int = 512 * 1024 * 1024) -> Tuple[str, os.stat_result]:
    resolved = path.resolve(strict=True)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(resolved, flags)
    except OSError as exc:
        raise ProtocolError("untrusted_runtime", f"{field} is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ProtocolError("untrusted_runtime", f"{field} is not one bounded regular file")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum:
                raise ProtocolError("untrusted_runtime", f"{field} exceeds its size limit")
            digest.update(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
        ):
            raise ProtocolError("untrusted_runtime", f"{field} changed while it was inspected")
        return digest.hexdigest(), after
    finally:
        os.close(descriptor)


def _resolve_runtime_executable(name: str, root: Path) -> Path:
    if name == "python":
        selected = Path(sys.executable)
    else:
        path_value = os.environ.get("PATH", "")
        components = path_value.split(os.pathsep)
        if not components or any(not component or not Path(component).is_absolute() for component in components):
            raise ProtocolError("untrusted_runtime", "PATH must contain only absolute non-empty directories")
        found = shutil.which(name, path=path_value)
        if found is None:
            raise ProtocolError("untrusted_runtime", f"the trusted {name} executable is unavailable")
        selected = Path(found)
    resolved = selected.resolve(strict=True)
    temporary_root = Path(tempfile.gettempdir()).resolve(strict=True)
    if (
        not resolved.is_absolute()
        or _is_within(resolved, root)
        or _is_within(resolved, IMPLEMENTATION_ROOT)
        or _is_within(resolved, temporary_root)
        or not os.access(resolved, os.X_OK)
    ):
        raise ProtocolError("untrusted_runtime", f"the trusted {name} executable has an unsafe location")
    return resolved


def _runtime_closure_digest() -> Tuple[str, str, Dict[str, Dict[str, Any]]]:
    entries: List[Dict[str, str]] = []
    runtime_state: Dict[str, Dict[str, Any]] = {}
    checker_digest = ""
    for relative in TRUSTED_RUNTIME_FILES:
        path = (IMPLEMENTATION_ROOT / relative).resolve(strict=True)
        digest, identity = _regular_file_digest(
            path,
            f"trusted runtime file {relative}",
            maximum=16 * 1024 * 1024,
        )
        entries.append({"path": relative, "sha256": digest})
        runtime_state[relative] = {
            "path": path,
            "sha256": digest,
            "device": identity.st_dev,
            "inode": identity.st_ino,
            "size": identity.st_size,
            "mtime_ns": identity.st_mtime_ns,
        }
        if relative == "scripts/check-public-release.py":
            checker_digest = digest
    return json_digest(entries), checker_digest, runtime_state


def _require_trusted_runtime_root(runtime_root: Path, target_root: Path) -> None:
    runtime = runtime_root.resolve(strict=True)
    target = target_root.resolve(strict=True)
    if runtime == target or _is_within(runtime, target):
        raise ProtocolError(
            "untrusted_runtime_root",
            "publication must run from an independently accepted runtime outside the candidate tree",
        )


def _pin_trusted_runtime(root: Path, binding: Any) -> None:
    if not isinstance(binding, dict):
        raise ProtocolError("invalid_trusted_runtime", "trusted runtime binding must be an object")
    keys = [
        "executor_closure_digest", "public_checker_digest", "python_executable_digest",
        "git_executable_digest", "gh_executable_digest",
    ]
    require_exact_keys(binding, keys, [], "trusted runtime binding")
    for key in keys:
        require_digest(binding[key], f"trusted runtime {key}")
    _require_trusted_runtime_root(IMPLEMENTATION_ROOT, root)
    closure_digest, checker_digest, runtime_state = _runtime_closure_digest()
    observed: Dict[str, str] = {
        "executor_closure_digest": closure_digest,
        "public_checker_digest": checker_digest,
    }
    tool_entries: Dict[str, Dict[str, Any]] = {}
    for name in TRUSTED_TOOL_NAMES:
        path = _resolve_runtime_executable(name, root)
        digest, identity = _regular_file_digest(path, f"trusted {name} executable")
        observed[f"{name}_executable_digest"] = digest
        tool_entries[name] = {
            "path": path,
            "sha256": digest,
            "device": identity.st_dev,
            "inode": identity.st_ino,
            "size": identity.st_size,
            "mtime_ns": identity.st_mtime_ns,
        }
    if observed != binding:
        raise ProtocolError("untrusted_runtime", "runtime or executable digests differ from the approved envelope")
    global _TRUSTED_RUNTIME_STATE, _TRUSTED_TOOLS
    if _TRUSTED_TOOLS and _TRUSTED_TOOLS != tool_entries:
        raise ProtocolError("untrusted_runtime", "trusted runtime executables changed within this process")
    if _TRUSTED_RUNTIME_STATE and _TRUSTED_RUNTIME_STATE != runtime_state:
        raise ProtocolError("untrusted_runtime", "trusted runtime files changed within this process")
    _TRUSTED_TOOLS = tool_entries
    _TRUSTED_RUNTIME_STATE = runtime_state


def _trusted_tool(name: str) -> str:
    entry = _TRUSTED_TOOLS.get(name)
    if entry is None:
        raise ProtocolError("untrusted_runtime", "trusted runtime was not pinned before command execution")
    path = Path(entry["path"])
    digest, identity = _regular_file_digest(path, f"trusted {name} executable")
    if (
        digest != entry["sha256"]
        or identity.st_dev != entry["device"]
        or identity.st_ino != entry["inode"]
        or identity.st_size != entry["size"]
        or identity.st_mtime_ns != entry["mtime_ns"]
    ):
        raise ProtocolError("untrusted_runtime", f"trusted {name} executable changed after approval")
    return str(path)


def _trusted_tool_digest(name: str) -> str:
    """Return a tool digest only after revalidating its pinned executable."""

    _trusted_tool(name)
    entry = _TRUSTED_TOOLS.get(name)
    if entry is None:
        raise ProtocolError("untrusted_runtime", "trusted runtime was not pinned before command execution")
    return str(entry["sha256"])


def _trusted_path() -> str:
    directories = {str(Path(entry["path"]).parent) for entry in _TRUSTED_TOOLS.values()}
    directories.update({"/usr/bin", "/bin"})
    return os.pathsep.join(sorted(directories))


def _trusted_checker_bytes() -> bytes:
    relative = "scripts/check-public-release.py"
    entry = _TRUSTED_RUNTIME_STATE.get(relative)
    if entry is None:
        raise ProtocolError("untrusted_runtime", "trusted runtime was not pinned before checker access")
    path = Path(entry["path"])
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ProtocolError("untrusted_runtime", "trusted public checker is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        expected_identity = (
            entry["device"], entry["inode"], entry["size"], entry["mtime_ns"]
        )
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_size > 16 * 1024 * 1024
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != expected_identity
        ):
            raise ProtocolError("untrusted_runtime", "trusted public checker changed after approval")
        chunks: List[bytes] = []
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > 16 * 1024 * 1024:
                raise ProtocolError("untrusted_runtime", "trusted public checker exceeds its size limit")
            chunks.append(chunk)
            digest.update(chunk)
        after = os.fstat(descriptor)
        try:
            named = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            raise ProtocolError("untrusted_runtime", "trusted public checker pathname changed") from exc
        if (
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != expected_identity
            or (named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns)
            != expected_identity
            or digest.hexdigest() != entry["sha256"]
        ):
            raise ProtocolError("untrusted_runtime", "trusted public checker changed while it was read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _git_common_directory(root: Path) -> Path:
    marker = root / ".git"
    if marker.is_dir() and not marker.is_symlink():
        git_directory = marker.resolve(strict=True)
    elif marker.is_file() and not marker.is_symlink():
        raw = marker.read_text(encoding="utf-8", errors="strict")
        if not raw.startswith("gitdir: ") or "\n" in raw.strip("\n") or "\r" in raw or "\x00" in raw:
            raise ProtocolError("unsafe_git_storage", "linked-worktree Git marker is malformed")
        selected = Path(raw[len("gitdir: "):].strip())
        git_directory = (selected if selected.is_absolute() else root / selected).resolve(strict=True)
    else:
        raise ProtocolError("unsafe_git_storage", "project root lacks one safe Git administrative marker")
    common_marker = git_directory / "commondir"
    if common_marker.exists() or common_marker.is_symlink():
        if common_marker.is_symlink() or not common_marker.is_file():
            raise ProtocolError("unsafe_git_storage", "Git common-directory marker is unsafe")
        raw_common = common_marker.read_text(encoding="utf-8", errors="strict")
        if "\r" in raw_common or "\x00" in raw_common or "\n" in raw_common.strip("\n"):
            raise ProtocolError("unsafe_git_storage", "Git common-directory marker is malformed")
        selected_common = Path(raw_common.strip())
        return (selected_common if selected_common.is_absolute() else git_directory / selected_common).resolve(strict=True)
    return git_directory


def _assert_safe_git_storage(root: Path) -> None:
    common = _git_common_directory(root)
    for name in ("alternates", "http-alternates"):
        path = common / "objects" / "info" / name
        if path.exists() or path.is_symlink():
            raise ProtocolError("unsafe_git_storage", "Git object alternates are forbidden during publication")


def _safe_git_env(*, index: Optional[Path] = None, identity: Optional[Dict[str, str]] = None,
                  timestamp: Optional[str] = None) -> Dict[str, str]:
    # Candidate-owned checks receive a sterile allowlisted environment. In
    # particular, API/token variables, Python injection variables, and user
    # configuration locations are not inherited.
    env = {key: os.environ[key] for key in SAFE_PROCESS_ENV if key in os.environ and key != "PATH"}
    env["PATH"] = _trusted_path()
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG"] = os.devnull
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONSAFEPATH"] = "1"
    if index is not None:
        env["GIT_INDEX_FILE"] = str(index)
    if identity is not None and timestamp is not None:
        env.update(
            {
                "GIT_AUTHOR_NAME": identity["name"],
                "GIT_AUTHOR_EMAIL": identity["email"],
                "GIT_AUTHOR_DATE": timestamp,
                "GIT_COMMITTER_NAME": identity["name"],
                "GIT_COMMITTER_EMAIL": identity["email"],
                "GIT_COMMITTER_DATE": timestamp,
            }
        )
    return env


def _transport_env() -> Dict[str, str]:
    """Allow trusted transport clients to find user auth without token env vars."""

    env = {
        key: os.environ[key]
        for key in (*SAFE_PROCESS_ENV, *TRANSPORT_CONFIG_ENV)
        if key in os.environ and key != "PATH"
    }
    env.update(
        {
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GH_PROMPT_DISABLED": "1",
            "GH_PAGER": "cat",
            "PAGER": "cat",
            "NO_COLOR": "1",
        }
    )
    env["PATH"] = _trusted_path()
    return env


def _run(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Optional[Dict[str, str]] = None,
    input_bytes: Optional[bytes] = None,
    failure_code: str = "command_failed",
) -> bytes:
    if not argv or not Path(argv[0]).is_absolute():
        raise ProtocolError("untrusted_runtime", "publication commands must use one pinned absolute executable")
    try:
        result = subprocess.run(
            list(argv),
            cwd=str(cwd),
            env=env,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ProtocolError(failure_code, "required publication command is unavailable") from exc
    if result.returncode != 0:
        raise ProtocolError(failure_code, "guarded publication command failed without exposing command output")
    return result.stdout


def _git(root: Path, *args: str, index: Optional[Path] = None, input_bytes: Optional[bytes] = None,
         failure_code: str = "git_state_unavailable") -> bytes:
    _assert_safe_git_storage(root)
    return _run(
        [
            _trusted_tool("git"),
            "-c", "core.fsmonitor=false",
            "-c", "commit.gpgSign=false",
            "-c", f"core.hooksPath={os.devnull}",
            "-c", "http.followRedirects=false",
            *args,
        ],
        cwd=root,
        env=_safe_git_env(index=index),
        input_bytes=input_bytes,
        failure_code=failure_code,
    )


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def _decode(value: bytes, field: str) -> str:
    try:
        return value.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ProtocolError("invalid_text", f"{field} is not valid UTF-8") from exc


def _string(value: Any, field: str, *, maximum: int = 2000, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value) or len(value) > maximum:
        raise ProtocolError("invalid_publication_envelope", f"{field} is invalid")
    if "\x00" in value or "\r" in value:
        raise ProtocolError("invalid_publication_envelope", f"{field} contains forbidden control data")
    return value


def _string_list(value: Any, field: str, *, item_maximum: int = 1000) -> List[str]:
    if not isinstance(value, list) or not value:
        raise ProtocolError("invalid_publication_envelope", f"{field} must be a non-empty unique string array")
    if any(
        not isinstance(item, str)
        or not item
        or len(item) > item_maximum
        or any(control in item for control in ("\x00", "\r", "\n"))
        for item in value
    ):
        raise ProtocolError("invalid_publication_envelope", f"{field} contains an invalid string")
    if len(value) != len(set(value)):
        raise ProtocolError("invalid_publication_envelope", f"{field} must be a non-empty unique string array")
    return list(value)


def _validate_branch(root: Path, value: Any, field: str, *, allow_protected: bool = False) -> str:
    branch = _string(value, field, maximum=200)
    forbidden = set(" ~^:?*[\\")
    parts = branch.split("/")
    if (
        branch.startswith("-")
        or branch == "@"
        or branch.endswith(("/", "."))
        or "//" in branch
        or ".." in branch
        or "@{" in branch
        or any(ord(char) < 32 or ord(char) == 127 or char in forbidden for char in branch)
        or any(not part or part.startswith(".") or part.endswith(".lock") for part in parts)
        or (not allow_protected and branch in FORBIDDEN_BRANCHES)
    ):
        raise ProtocolError("unsafe_branch", f"{field} is not a permitted publication branch")
    return branch


def _safe_input_path(root: Path, value: Path, field: str) -> str:
    relative = canonical_relative_path(value.as_posix())
    if not relative.startswith(ENVELOPE_INBOX_PREFIX) or is_sensitive_path(relative):
        raise ProtocolError("unsafe_input_path", f"{field} must be a non-credential file in the private protocol inbox")
    # The actual read uses descriptor-relative traversal with O_NOFOLLOW for
    # every component. Resolving here would leave an ancestor-swap window.
    return relative


def validate_publication_envelope(document: Dict[str, Any], *, root: Path, require_active: bool = True) -> Dict[str, Any]:
    required = [
        "schema_version", "kind", "envelope_id", "source_work_item", "source_work_item_id",
        "source_work_item_revision", "source_work_item_digest", "source_completion_digest",
        "project_root", "base_sha", "source_seal_digest", "candidate_digest", "path_set_digest",
        "allowed_paths", "manifest", "trusted_runtime", "branch", "writer", "approval", "lease_expires_at", "remote",
        "commit", "pull_request", "effects", "outcome", "risk", "rollback", "verification", "exclusions",
    ]
    require_exact_keys(document, required, [], "publication envelope")
    if document["schema_version"] != PUBLIC_VERSION or document["kind"] != "publication_envelope":
        raise ProtocolError("wrong_schema", "publication envelope must use public-v2 publication_envelope")
    require_id(document["envelope_id"], "envelope_id")
    source_work_item = canonical_relative_path(_string(document["source_work_item"], "source work item", maximum=500))
    if not source_work_item.startswith(SOURCE_WORK_PREFIX):
        raise ProtocolError("invalid_source_work_item", "source work item must use project-local runtime storage")
    document["source_work_item"] = source_work_item
    require_id(document["source_work_item_id"], "source_work_item_id")
    if not isinstance(document["source_work_item_revision"], int) or document["source_work_item_revision"] < 0:
        raise ProtocolError("invalid_source_revision", "source work item revision must be non-negative")
    for field in ("source_work_item_digest", "source_completion_digest", "source_seal_digest", "candidate_digest", "path_set_digest"):
        require_digest(document[field], field)
    if not isinstance(document["project_root"], str) or len(document["project_root"]) > 1000 or not Path(document["project_root"]).is_absolute():
        raise ProtocolError("absolute_project_root_required", "publication project_root must be absolute")
    if Path(document["project_root"]).resolve() != root.resolve():
        raise ProtocolError("wrong_project_root", "publication envelope belongs to a different project root")
    _pin_trusted_runtime(root, document["trusted_runtime"])
    if not isinstance(document["base_sha"], str) or not GIT_SHA_RE.fullmatch(document["base_sha"]):
        raise ProtocolError("invalid_base", "publication base must be one exact Git commit")
    raw_paths = document["allowed_paths"]
    if not isinstance(raw_paths, list) or not raw_paths:
        raise ProtocolError("invalid_allowed_paths", "publication paths must be a non-empty unique array")
    if any(not isinstance(raw, str) for raw in raw_paths) or len(raw_paths) != len(set(raw_paths)):
        raise ProtocolError("invalid_allowed_paths", "publication paths must be a non-empty unique array")
    paths: List[str] = []
    for raw in raw_paths:
        if not isinstance(raw, str) or len(raw) > 500 or "\\" in raw or any(char in raw for char in "*?[]\x00\r\n"):
            raise ProtocolError("invalid_allowed_paths", "publication paths must be literal portable paths")
        path = canonical_relative_path(raw)
        if any(part.casefold() == ".git" for part in PurePosixPath(path).parts):
            raise ProtocolError("protected_path", "publication paths cannot address Git administrative data")
        if is_local_runtime_path(path) or is_sensitive_path(path):
            raise ProtocolError("protected_path", "publication paths cannot include protected or credential-shaped data")
        paths.append(path)
    if paths != sorted(paths) or document["path_set_digest"] != canonical_digest_lines(paths):
        raise ProtocolError("path_set_mismatch", "publication paths or path-set digest are not canonical")
    document["allowed_paths"] = paths
    manifest = document["manifest"]
    if not isinstance(manifest, dict):
        raise ProtocolError("invalid_manifest", "manifest binding must be an object")
    require_exact_keys(manifest, ["path", "sha256"], [], "manifest binding")
    if manifest["path"] != "SHA256SUMS":
        raise ProtocolError("invalid_manifest", "publication manifest path must be SHA256SUMS")
    require_digest(manifest["sha256"], "manifest sha256")
    branch = _validate_branch(root, document["branch"], "branch")
    writer = document["writer"]
    if not isinstance(writer, dict):
        raise ProtocolError("invalid_writer", "publication writer must be an object")
    require_exact_keys(writer, ["actor", "surface_id", "executor_id", "adapter_version"], [], "publication writer")
    _string(writer["actor"], "writer actor", maximum=200)
    require_id(writer["surface_id"], "writer surface_id")
    require_id(writer["executor_id"], "writer executor_id")
    _string(writer["adapter_version"], "writer adapter_version", maximum=100)
    approval = document["approval"]
    if not isinstance(approval, dict):
        raise ProtocolError("invalid_approval", "publication approval must be an object")
    require_exact_keys(approval, ["approved_by", "accepted_at", "expires_at", "summary"], [], "publication approval")
    _string(approval["approved_by"], "approved_by", maximum=200)
    _string(approval["summary"], "approval summary", maximum=2000)
    accepted_at = parse_timestamp(approval["accepted_at"], "accepted_at")
    expires_at = parse_timestamp(approval["expires_at"], "expires_at")
    lease_expires = parse_timestamp(document["lease_expires_at"], "lease_expires_at")
    now = utc_now()
    if accepted_at > now or expires_at <= accepted_at or lease_expires <= accepted_at or lease_expires > expires_at:
        raise ProtocolError("invalid_approval_window", "publication approval and lease window are inconsistent")
    if require_active and (expires_at <= now or lease_expires <= now):
        raise ProtocolError("expired_publication", "publication approval or writer lease has expired")
    remote = document["remote"]
    if not isinstance(remote, dict):
        raise ProtocolError("invalid_remote", "remote binding must be an object")
    require_exact_keys(
        remote,
        ["provider", "remote_name", "repository", "repository_id", "base_branch", "base_sha", "head_branch", "force", "required_checks"],
        [],
        "remote binding",
    )
    if remote["provider"] != "github" or remote["force"] is not False:
        raise ProtocolError("invalid_remote", "publication supports only non-force GitHub draft PRs")
    if not isinstance(remote["remote_name"], str) or not REMOTE_RE.fullmatch(remote["remote_name"]):
        raise ProtocolError("invalid_remote", "remote name is invalid")
    if not isinstance(remote["repository"], str) or len(remote["repository"]) > 200 or not REPOSITORY_RE.fullmatch(remote["repository"]):
        raise ProtocolError("invalid_remote", "repository must be one canonical OWNER/REPO identifier")
    if not isinstance(remote["repository_id"], str) or not re.fullmatch(r"[1-9][0-9]{0,39}", remote["repository_id"]):
        raise ProtocolError("invalid_remote", "repository_id must be one canonical GitHub REST database ID")
    base_branch = _validate_branch(root, remote["base_branch"], "remote base branch", allow_protected=True)
    head_branch = _validate_branch(root, remote["head_branch"], "remote head branch")
    if base_branch == head_branch or branch != head_branch or remote["base_sha"] != document["base_sha"]:
        raise ProtocolError("remote_scope_mismatch", "remote base/head scope does not match the candidate")
    remote["required_checks"] = _string_list(remote["required_checks"], "required_checks", item_maximum=200)
    if any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ /-]{0,199}", item) is None for item in remote["required_checks"]):
        raise ProtocolError("invalid_remote", "required check names must use the canonical public character set")
    commit = document["commit"]
    if not isinstance(commit, dict):
        raise ProtocolError("invalid_commit", "commit binding must be an object")
    require_exact_keys(commit, ["subject", "body", "trailers", "identity"], [], "commit binding")
    _string(commit["subject"], "commit subject", maximum=200)
    if "\n" in commit["subject"]:
        raise ProtocolError("invalid_commit", "commit subject must be one line")
    _string(commit["body"], "commit body", maximum=4000, allow_empty=True)
    commit["trailers"] = _string_list(commit["trailers"], "commit trailers", item_maximum=200)
    if "Agent: codex" not in commit["trailers"] or commit["identity"] != PUBLIC_IDENTITY:
        raise ProtocolError("unsafe_commit_identity", "publication requires the fixed public identity and Agent trailer")
    pull_request = document["pull_request"]
    if not isinstance(pull_request, dict):
        raise ProtocolError("invalid_pull_request", "pull request binding must be an object")
    require_exact_keys(pull_request, ["draft", "maintainer_edits", "title", "body"], [], "pull request binding")
    if pull_request["draft"] is not True or pull_request["maintainer_edits"] is not False:
        raise ProtocolError("unsafe_pull_request", "publication permits only a non-maintainer-editable draft PR")
    _string(pull_request["title"], "pull request title", maximum=256)
    if "\n" in pull_request["title"]:
        raise ProtocolError("invalid_pull_request", "pull request title must be one line")
    _string(pull_request["body"], "pull request body", maximum=20000)
    if document["effects"] != REQUIRED_EFFECTS:
        raise ProtocolError("forbidden_effect", "publication effect map must deny every later delivery gate")
    _string(document["outcome"], "outcome")
    if document["risk"] not in {"low", "medium", "high", "critical"}:
        raise ProtocolError("invalid_risk", "publication risk is invalid")
    _string(document["rollback"], "rollback")
    document["verification"] = _string_list(document["verification"], "verification")
    document["exclusions"] = _string_list(document["exclusions"], "exclusions")
    return document


def _commit_message(envelope: Dict[str, Any]) -> bytes:
    commit = envelope["commit"]
    sections = [commit["subject"]]
    if commit["body"]:
        sections.append(commit["body"].strip())
    sections.append("\n".join(commit["trailers"]))
    value = "\n\n".join(sections).rstrip() + "\n"
    if not value.rstrip().endswith("Agent: codex"):
        raise ProtocolError("missing_agent_trailer", "commit message must end with Agent: codex")
    return value.encode("utf-8")


def _pr_body(envelope: Dict[str, Any], request_id: str, commit_sha: str) -> bytes:
    marker_digest = json_digest(
        {"envelope_id": envelope["envelope_id"], "request_id": request_id, "commit_sha": commit_sha}
    )
    body = envelope["pull_request"]["body"].rstrip() + f"\n\n<!-- exocortex-publication:{marker_digest} -->\n"
    return body.encode("utf-8")


def _public_metadata_check(root: Path, envelope: Dict[str, Any], title: str, body: bytes) -> str:
    if len(body) > MAX_METADATA_BYTES:
        raise ProtocolError("public_metadata_too_large", "public metadata exceeds the bounded size")
    with tempfile.TemporaryDirectory(prefix="exo-public-metadata-") as temporary:
        target = Path(temporary)
        public_values = {
            "commit-message.txt": _commit_message(envelope),
            "head-branch.txt": (envelope["remote"]["head_branch"] + "\n").encode("utf-8"),
            "pr-body.md": body,
            "pr-title.txt": (title + "\n").encode("utf-8"),
        }
        for name, content in public_values.items():
            _write_private_file(target / name, content)
        baseline_checker = _trusted_checker_bytes()
        _run_checker_bytes(
            baseline_checker,
            cwd=target,
            arguments=("--root", str(target), "--source-tree"),
        )
    return json_digest(
        {
            "metadata": {
                name: hashlib.sha256(content).hexdigest()
                for name, content in sorted(public_values.items())
            },
            "trusted_checker": hashlib.sha256(baseline_checker).hexdigest(),
        }
    )


def _verify_manifest(root: Path, envelope: Dict[str, Any]) -> None:
    path = resolve_repo_path(root, envelope["manifest"]["path"], require_exists=True)
    content = read_safe_regular_bytes(path, "publication manifest")
    if hashlib.sha256(content).hexdigest() != envelope["manifest"]["sha256"]:
        raise ProtocolError("manifest_changed", "publication manifest no longer matches the approved digest")


def _branch_and_head(root: Path) -> Tuple[str, str]:
    branch = _decode(_git(root, "branch", "--show-current"), "branch")
    head = _decode(_git(root, "rev-parse", "HEAD"), "HEAD")
    if not branch or not GIT_SHA_RE.fullmatch(head):
        raise ProtocolError("detached_or_invalid_head", "publication requires one attached exact branch")
    return branch, head


def _require_no_operation_state(root: Path) -> None:
    for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG", "rebase-merge", "rebase-apply", "sequencer"):
        raw = _decode(_git(root, "rev-parse", "--git-path", name), f"Git {name} path")
        path = Path(raw)
        if not path.is_absolute():
            path = root / path
        if path.exists() or path.is_symlink():
            raise ProtocolError("git_operation_in_progress", "another Git operation is active")


def _verify_source_candidate(root: Path, envelope: Dict[str, Any]) -> Dict[str, Any]:
    work_path = resolve_repo_path(root, envelope["source_work_item"], require_exists=True)
    work = validate_work_item(load_safe_json(work_path, "source work item"))
    if (
        work["id"] != envelope["source_work_item_id"]
        or work["revision"] != envelope["source_work_item_revision"]
        or json_digest(work) != envelope["source_work_item_digest"]
        or work["lifecycle"]["state"] != "release_ready"
    ):
        raise ProtocolError("source_work_item_mismatch", "publication source work item is stale or not release-ready")
    release_transition = work["transitions"][-1] if work["transitions"] else None
    if (
        not isinstance(release_transition, dict)
        or release_transition.get("from") != "human_uat"
        or release_transition.get("to") != "release_ready"
    ):
        raise ProtocolError("source_work_item_mismatch", "publication source lacks the final release-ready transition")
    local_envelope = load_local_delivery_binding(root, work, require_active=False)
    if local_envelope is None:
        raise ProtocolError("source_not_complete", "publication source is not a guarded local-delivery work item")
    require_local_completion_provenance(
        root,
        work,
        local_envelope,
        release_request_id=release_transition.get("request_id"),
    )
    local = work.get("local_delivery")
    if local is None or local["completion"] is None or local["seal"] is None:
        raise ProtocolError("source_not_complete", "publication source lacks completed local delivery and seal evidence")
    if (
        json_digest(local["completion"]) != envelope["source_completion_digest"]
        or json_digest(local["seal"]) != envelope["source_seal_digest"]
        or local["seal"]["candidate_digest"] != envelope["candidate_digest"]
        or local["seal"]["path_set_digest"] != envelope["path_set_digest"]
        or local["seal"]["changed_paths"] != envelope["allowed_paths"]
        or work["designated_base"]["sha"] != envelope["base_sha"]
    ):
        raise ProtocolError("source_seal_mismatch", "publication envelope does not match the completed source seal")
    branch, head = _branch_and_head(root)
    if branch != envelope["branch"] or head != envelope["base_sha"]:
        raise ProtocolError("worktree_identity_mismatch", "publication worktree branch or base changed")
    _require_no_operation_state(root)
    if _git(root, "diff", "--cached", "--name-only", "-z"):
        raise ProtocolError("staged_changes_present", "publication requires an untouched real Git index")
    paths = current_changed_paths(root)
    evidence = candidate_change_evidence(root, envelope["base_sha"], paths)
    expected = {
        "changed_paths": envelope["allowed_paths"],
        "path_set_digest": envelope["path_set_digest"],
        "candidate_digest": envelope["candidate_digest"],
    }
    if evidence != expected:
        raise ProtocolError("candidate_changed", "working candidate no longer matches the approved seal")
    _verify_manifest(root, envelope)
    _git(root, "diff", "--check", failure_code="candidate_diff_invalid")
    # This runs before any candidate blob/tree is written to the shared Git
    # object database. Both the trusted base checker and checksum-bound
    # candidate checker inspect a private public-code snapshot.
    _verify_public_candidate(root, envelope)
    return work


def _verify_executor(root: Path, envelope: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    registry = validate_registry(load_safe_json(resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True), "executor registry"))
    writer = envelope["writer"]
    entry = find_executor(
        registry,
        surface_id=writer["surface_id"],
        executor_id=writer["executor_id"],
        adapter_version=writer["adapter_version"],
        guard_digest=current_guard_digest(),
        role="writer",
        now=utc_now(),
    )
    # A publication envelope spans both local commit mutation and later
    # credentialed GitHub egress. Reject it before reserving the source unless
    # the exact executor is registered for both roles.
    find_executor(
        registry,
        surface_id=writer["surface_id"],
        executor_id=writer["executor_id"],
        adapter_version=writer["adapter_version"],
        guard_digest=current_guard_digest(),
        role="egress",
        now=utc_now(),
    )
    return registry, entry


def _recheck_bootstrap_authority(
    root: Path,
    envelope: Dict[str, Any],
    accepted_work: Dict[str, Any],
) -> None:
    """Recheck live source and authority immediately before bootstrap writes."""

    current_work = validate_work_item(
        load_safe_json(
            resolve_repo_path(root, envelope["source_work_item"], require_exists=True),
            "source work item",
        )
    )
    if current_work != accepted_work:
        raise ProtocolError(
            "publication_source_changed",
            "publication source changed before bootstrap state creation",
        )
    refreshed = validate_publication_envelope(
        copy.deepcopy(envelope),
        root=root,
        require_active=True,
    )
    if refreshed != envelope:
        raise ProtocolError(
            "publication_envelope_changed",
            "publication envelope changed before bootstrap state creation",
        )
    _verify_executor(root, envelope)


def _record_path(root: Path, publication_id: str) -> Path:
    return resolve_repo_path(root, f"{PUBLICATION_PREFIX}{publication_id}.json")


def _stored_envelope_path(root: Path, envelope_id: str) -> Path:
    return resolve_repo_path(root, f"{ENVELOPE_STORE_PREFIX}{envelope_id}.publication.json")


def _tx_path(root: Path, publication_id: str, operation: str, request_id: str) -> Path:
    require_id(publication_id, "publication id")
    require_id(request_id, "transaction request id")
    if operation not in OPERATIONS and operation not in {"bootstrap", "retire_publication"}:
        raise ProtocolError("invalid_operation", "publication transaction operation is invalid")
    filename_id = stable_id("publication-transaction", publication_id, operation, request_id)
    return resolve_repo_path(
        root,
        f"{TRANSACTION_PREFIX}publication-{filename_id}.json",
    )


def _lock_path(root: Path, publication_id: str) -> Path:
    return resolve_repo_path(root, f"{LOCK_PREFIX}publication-{publication_id}.lock")


def _source_lock_path(root: Path, source_work_item: str) -> Path:
    return resolve_repo_path(root, f"{LOCK_PREFIX}{Path(source_work_item).name}.lock")


def _source_reservation_document(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": PUBLIC_VERSION,
        "kind": "publication_reservation",
        "publication_id": envelope["envelope_id"],
        "work_item_id": envelope["source_work_item_id"],
        "work_item_path": envelope["source_work_item"],
        "source_revision": envelope["source_work_item_revision"],
        "source_digest": envelope["source_work_item_digest"],
        "envelope_digest": json_digest(envelope),
        "status": "active",
        "lease_expires_at": envelope["lease_expires_at"],
        "created_at": envelope["approval"]["accepted_at"],
        "released_at": None,
    }


def _claim_source_reservation(
    root: Path,
    envelope: Dict[str, Any],
    work: Dict[str, Any],
) -> Path:
    """Claim the source lane, replacing only an exactly retired predecessor."""

    path = publication_reservation_path(root, envelope["source_work_item_id"])
    expected = _source_reservation_document(envelope)
    if path.exists() or path.is_symlink():
        existing = load_safe_json(path, "publication source reservation")
        if existing != expected:
            require_publication_lane_available(
                root,
                envelope["source_work_item"],
                work,
                publication_id=envelope["envelope_id"],
            )
            atomic_write_json(path, expected)
    else:
        exclusive_write_json(path, expected)
    return path


def _validate_source_reservation(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Tuple[Path, Dict[str, Any]]:
    path = resolve_repo_path(root, record["source_reservation_path"], require_exists=True)
    value = load_safe_json(path, "publication source reservation")
    require_exact_keys(
        value,
        [
            "schema_version", "kind", "publication_id", "work_item_id", "work_item_path",
            "source_revision", "source_digest", "envelope_digest", "status",
            "lease_expires_at", "created_at", "released_at",
        ],
        [],
        "publication source reservation",
    )
    expected = _source_reservation_document(envelope)
    static_fields = set(expected) - {"status", "released_at"}
    if any(value.get(field) != expected[field] for field in static_fields):
        raise ProtocolError("publication_reservation_mismatch", "source reservation differs from its publication envelope")
    expected_status = "released" if record["state"] in {"complete", "retired"} else "active"
    release_recovery = (
        expected_status == "released"
        and value.get("status") == "active"
        and value.get("released_at") is None
    )
    if value.get("status") != expected_status and not release_recovery:
        raise ProtocolError("publication_reservation_mismatch", "source reservation status differs from publication state")
    if value.get("status") == "active" and value.get("released_at") is not None:
        raise ProtocolError("publication_reservation_mismatch", "active source reservation has release evidence")
    if value.get("status") == "released":
        parse_timestamp(value.get("released_at"), "publication reservation released_at")
    return path, value


def _validate_record(record: Dict[str, Any]) -> Dict[str, Any]:
    require_exact_keys(
        record,
        [
            "schema_version", "kind", "id", "revision", "state", "envelope_path", "envelope_digest",
            "source_work_item", "source_work_item_id", "source_work_item_revision", "base_sha", "branch",
            "candidate_digest", "path_set_digest", "allowed_paths", "manifest_digest", "writer", "reservation",
            "source_reservation_path",
            "commit", "push", "draft_pull_request", "lifecycle_transition", "completion", "unknown_effect", "retirement", "idempotency",
        ],
        [],
        "publication record",
    )
    if record["schema_version"] != PUBLIC_VERSION or record["kind"] != "publication_record":
        raise ProtocolError("wrong_schema", "publication record has the wrong schema")
    require_id(record["id"], "publication id")
    if not isinstance(record["revision"], int) or record["revision"] < 0 or record["state"] not in STATES:
        raise ProtocolError("invalid_publication_state", "publication record revision or state is invalid")
    source_path = canonical_relative_path(record["source_work_item"])
    if not source_path.startswith(SOURCE_WORK_PREFIX):
        raise ProtocolError("invalid_publication_record", "publication source work-item path is invalid")
    record["source_work_item"] = source_path
    require_id(record["source_work_item_id"], "source work item id")
    if not isinstance(record["source_work_item_revision"], int) or record["source_work_item_revision"] < 0:
        raise ProtocolError("invalid_publication_record", "publication source revision is invalid")
    if not isinstance(record["base_sha"], str) or not GIT_SHA_RE.fullmatch(record["base_sha"]):
        raise ProtocolError("invalid_publication_record", "publication base SHA is invalid")
    envelope_path = canonical_relative_path(record["envelope_path"])
    if not envelope_path.startswith(ENVELOPE_STORE_PREFIX):
        raise ProtocolError("invalid_publication_record", "stored publication envelope path is invalid")
    record["envelope_path"] = envelope_path
    if not isinstance(record["branch"], str) or not record["branch"]:
        raise ProtocolError("invalid_publication_record", "publication branch is invalid")
    for field in ("envelope_digest", "candidate_digest", "path_set_digest", "manifest_digest"):
        require_digest(record[field], field)
    source_reservation = canonical_relative_path(record["source_reservation_path"])
    expected_reservation = f".exocortex/local/protocol/publication-reservations/{record['source_work_item_id']}.json"
    if source_reservation != expected_reservation:
        raise ProtocolError("invalid_publication_record", "publication source reservation path is invalid")
    record["source_reservation_path"] = source_reservation
    if (
        not isinstance(record["allowed_paths"], list)
        or not record["allowed_paths"]
        or any(not isinstance(path, str) for path in record["allowed_paths"])
        or len(record["allowed_paths"]) != len(set(record["allowed_paths"]))
        or record["allowed_paths"] != sorted(record["allowed_paths"])
        or canonical_digest_lines(record["allowed_paths"]) != record["path_set_digest"]
    ):
        raise ProtocolError("invalid_publication_record", "publication record path binding is invalid")
    if not isinstance(record["idempotency"], list):
        raise ProtocolError("invalid_publication_record", "publication idempotency must be an array")
    reservation = record["reservation"]
    if not isinstance(reservation, dict):
        raise ProtocolError("invalid_reservation", "publication reservation must be an object")
    require_exact_keys(reservation, ["status", "lease_expires_at"], [], "publication reservation")
    if reservation["status"] not in {"active", "released"}:
        raise ProtocolError("invalid_reservation", "publication reservation state is invalid")
    parse_timestamp(reservation["lease_expires_at"], "publication lease")
    writer = record["writer"]
    if not isinstance(writer, dict):
        raise ProtocolError("invalid_publication_record", "publication writer must be an object")
    require_exact_keys(writer, ["actor", "surface_id", "executor_id", "adapter_version"], [], "publication writer")
    _string(writer["actor"], "publication writer actor", maximum=200)
    require_id(writer["surface_id"], "publication writer surface_id")
    require_id(writer["executor_id"], "publication writer executor_id")
    _string(writer["adapter_version"], "publication writer adapter_version", maximum=100)
    if record["state"] in {"complete", "retired"} and reservation["status"] != "released":
        raise ProtocolError("invalid_reservation", "closed publication must release its writer")
    if record["state"] not in {"complete", "retired", "effect_unknown"} and reservation["status"] != "active":
        raise ProtocolError("invalid_reservation", "active publication must retain its writer")
    if record["state"] == "effect_unknown" and record["unknown_effect"] is None:
        raise ProtocolError("invalid_unknown_effect", "unknown publication effect requires an audit record")
    if record["state"] not in {"effect_unknown", "retired"} and record["unknown_effect"] is not None:
        raise ProtocolError("invalid_unknown_effect", "known publication state cannot retain unknown-effect data")
    if record["state"] == "retired" and record["retirement"] is None:
        raise ProtocolError("invalid_retirement", "retired publication requires immutable retirement evidence")
    if record["state"] != "retired" and record["retirement"] is not None:
        raise ProtocolError("invalid_retirement", "active publication cannot contain retirement evidence")
    expected_presence = {
        "authorized": (False, False, False, False, False),
        "committed": (True, False, False, False, False),
        "pushed": (True, True, False, False, False),
        "draft_pr_verified": (True, True, True, False, False),
        "complete": (True, True, True, True, True),
    }
    if record["state"] in expected_presence:
        observed = tuple(
            record[field] is not None
            for field in ("commit", "push", "draft_pull_request", "lifecycle_transition", "completion")
        )
        if observed != expected_presence[record["state"]]:
            raise ProtocolError("invalid_publication_record", "publication evidence is not monotonic for its state")
    if record["unknown_effect"] is not None:
        if not isinstance(record["unknown_effect"], dict):
            raise ProtocolError("invalid_unknown_effect", "unknown publication effect must be an object")
        require_exact_keys(
            record["unknown_effect"],
            ["request_id", "recorded_at", "operation", "last_confirmed_state", "intent_digest", "reason_code"],
            [],
            "unknown publication effect",
        )
        require_id(record["unknown_effect"]["request_id"], "unknown effect request_id")
        parse_timestamp(record["unknown_effect"]["recorded_at"], "unknown effect recorded_at")
        require_digest(record["unknown_effect"]["intent_digest"], "unknown effect intent_digest")
        if record["unknown_effect"]["operation"] not in {"push_publication", "create_draft_pr"}:
            raise ProtocolError("invalid_unknown_effect", "unknown effect operation is invalid")
        _string(record["unknown_effect"]["reason_code"], "unknown effect reason_code", maximum=200)
        last = record["unknown_effect"].get("last_confirmed_state")
        if last not in {"committed", "pushed"}:
            raise ProtocolError("invalid_unknown_effect", "unknown effect must follow commit or push state")
        prefix = (record["commit"] is not None, record["push"] is not None, record["draft_pull_request"] is not None)
        if prefix != ((True, False, False) if last == "committed" else (True, True, False)):
            raise ProtocolError("invalid_unknown_effect", "unknown effect evidence does not match its last confirmed state")
        if record["lifecycle_transition"] is not None or record["completion"] is not None:
            raise ProtocolError("invalid_unknown_effect", "unknown outward effect cannot contain completion evidence")

    evidence_specs = {
        "commit": [
            "request_id", "recorded_at", "capability_path", "capability_digest", "intent_digest", "base_sha",
            "candidate_digest", "path_set_digest", "tree_sha", "commit_sha", "message_digest",
            "identity_policy_status", "trusted_public_check_digest",
        ],
        "push": [
            "request_id", "recorded_at", "capability_path", "capability_digest", "intent_digest", "repository", "repository_id",
            "remote_name", "base_branch", "base_sha", "head_branch", "commit_sha", "observed_remote_sha",
            "observation_digest",
        ],
        "draft_pull_request": [
            "request_id", "recorded_at", "capability_path", "capability_digest", "intent_digest", "repository", "repository_id",
            "number", "url", "base_branch", "head_branch", "head_sha", "is_draft", "title_digest",
            "body_digest", "observation_digest",
        ],
        "lifecycle_transition": [
            "request_id", "transition_id", "recorded_at", "from_state", "to_state", "source_revision_before",
            "source_revision_after", "capability_path", "capability_digest", "intent_digest", "evidence_digest",
        ],
        "completion": [
            "request_id", "completed_at", "publication_state", "capability_path", "capability_digest",
            "intent_digest", "required_checks_digest", "verification_digest", "closed_gates",
        ],
        "retirement": [
            "request_id", "retired_at", "capability_path", "capability_digest", "intent_digest",
            "prior_state", "prior_revision", "prior_unknown_effect_digest", "reason", "observation_digest",
            "preserved_effects",
        ],
    }
    for field, keys in evidence_specs.items():
        value = record[field]
        if value is None:
            continue
        if not isinstance(value, dict):
            raise ProtocolError("invalid_publication_record", f"{field} evidence must be an object")
        require_exact_keys(value, keys, [], f"publication {field} evidence")
        require_id(value["request_id"], f"{field} request_id")
        time_field = "completed_at" if field == "completion" else ("retired_at" if field == "retirement" else "recorded_at")
        parse_timestamp(value[time_field], f"{field} {time_field}")
        for digest_field in (
            "capability_digest", "intent_digest", "candidate_digest", "path_set_digest", "message_digest",
            "trusted_public_check_digest", "observation_digest", "title_digest", "body_digest",
            "evidence_digest", "required_checks_digest", "verification_digest",
        ):
            if digest_field in value:
                require_digest(value[digest_field], f"{field} {digest_field}")
        if "capability_path" in value:
            capability_path = canonical_relative_path(value["capability_path"])
            if not capability_path.startswith(CAPABILITY_PREFIX):
                raise ProtocolError("invalid_publication_record", f"{field} capability path is invalid")
            value["capability_path"] = capability_path
    commit = record["commit"]
    if commit is not None:
        for field in ("base_sha", "tree_sha", "commit_sha"):
            if not isinstance(commit[field], str) or not GIT_SHA_RE.fullmatch(commit[field]):
                raise ProtocolError("invalid_publication_record", f"commit {field} is invalid")
        if (
            commit["base_sha"] != record["base_sha"]
            or commit["candidate_digest"] != record["candidate_digest"]
            or commit["path_set_digest"] != record["path_set_digest"]
            or commit["identity_policy_status"] != "pass"
        ):
            raise ProtocolError("invalid_publication_record", "commit evidence differs from publication bindings")
    push = record["push"]
    if push is not None:
        if commit is None or push["commit_sha"] != commit["commit_sha"] or push["observed_remote_sha"] != commit["commit_sha"]:
            raise ProtocolError("invalid_publication_record", "push evidence differs from the publication commit")
        if push["base_sha"] != record["base_sha"]:
            raise ProtocolError("invalid_publication_record", "push base differs from publication base")
    draft = record["draft_pull_request"]
    if draft is not None:
        if push is None or draft["head_sha"] != push["commit_sha"] or draft["is_draft"] is not True:
            raise ProtocolError("invalid_publication_record", "draft PR evidence differs from the publication push")
        if not isinstance(draft["number"], int) or draft["number"] <= 0 or not isinstance(draft["url"], str):
            raise ProtocolError("invalid_publication_record", "draft PR identity is invalid")
    lifecycle_transition = record["lifecycle_transition"]
    if lifecycle_transition is not None:
        require_id(lifecycle_transition["transition_id"], "publication transition id")
        if (
            lifecycle_transition["from_state"] != "release_ready"
            or lifecycle_transition["to_state"] != "awaiting_release"
            or lifecycle_transition["source_revision_before"] != record["source_work_item_revision"]
            or lifecycle_transition["source_revision_after"] != record["source_work_item_revision"] + 1
        ):
            raise ProtocolError("invalid_publication_record", "publication lifecycle evidence is invalid")
    completion = record["completion"]
    if completion is not None:
        if completion["publication_state"] != "complete" or lifecycle_transition is None:
            raise ProtocolError("invalid_publication_record", "publication completion lacks lifecycle evidence")
        if completion["closed_gates"] != ["merge", "mark_ready", "tag", "release", "deploy", "promote", "downstream_rollout"]:
            raise ProtocolError("invalid_publication_record", "publication completion closed-gate list is invalid")
    retirement = record["retirement"]
    if retirement is not None:
        if retirement["prior_state"] not in {"authorized", "committed", "pushed", "effect_unknown"}:
            raise ProtocolError("invalid_retirement", "publication cannot retire from this state")
        if not isinstance(retirement["prior_revision"], int) or retirement["prior_revision"] < 0:
            raise ProtocolError("invalid_retirement", "publication retirement prior revision is invalid")
        _string(retirement["reason"], "publication retirement reason", maximum=1000)
        if retirement["prior_unknown_effect_digest"] is not None:
            require_digest(retirement["prior_unknown_effect_digest"], "retirement prior unknown-effect digest")
        if (
            not isinstance(retirement["preserved_effects"], list)
            or any(item not in {"named_branch"} for item in retirement["preserved_effects"])
            or len(retirement["preserved_effects"]) != len(set(retirement["preserved_effects"]))
        ):
            raise ProtocolError("invalid_retirement", "publication retirement preserved effects are invalid")
        prefix = tuple(
            record[field] is not None
            for field in ("commit", "push", "draft_pull_request", "lifecycle_transition", "completion")
        )
        expected_prefixes = {
            "authorized": {(False, False, False, False, False)},
            "committed": {(True, False, False, False, False)},
            "pushed": {(True, True, False, False, False)},
            "effect_unknown": {
                (True, False, False, False, False),
                (True, True, False, False, False),
            },
        }
        if prefix not in expected_prefixes[retirement["prior_state"]]:
            raise ProtocolError("invalid_retirement", "publication retirement evidence prefix is inconsistent")
        if (retirement["prior_state"] == "effect_unknown") != (record["unknown_effect"] is not None):
            raise ProtocolError("invalid_retirement", "retirement unknown-effect evidence is inconsistent")
    seen_request_ids = set()
    observed_operations: List[str] = []
    for item in record["idempotency"]:
        if not isinstance(item, dict):
            raise ProtocolError("invalid_publication_record", "publication idempotency entries must be objects")
        require_exact_keys(item, ["request_id", "operation", "result_id", "accepted_at"], [], "publication idempotency")
        request = require_id(item["request_id"], "idempotency request_id")
        if request in seen_request_ids:
            raise ProtocolError("duplicate_idempotency", "publication request IDs must be unique")
        seen_request_ids.add(request)
        if item["operation"] not in {"bootstrap_publication", *OPERATIONS, "retire_publication"}:
            raise ProtocolError("invalid_publication_record", "publication idempotency operation is invalid")
        require_id(item["result_id"], "idempotency result_id")
        parse_timestamp(item["accepted_at"], "idempotency accepted_at")
        observed_operations.append(item["operation"])
    operation_sequence = ["bootstrap_publication", *OPERATIONS]
    if record["state"] == "retired":
        retirement = record["retirement"]
        if (
            record["revision"] != retirement["prior_revision"] + 1
            or not observed_operations
            or observed_operations[-1] != "retire_publication"
        ):
            raise ProtocolError("invalid_retirement", "publication retirement revision history is inconsistent")
    elif record["state"] == "effect_unknown":
        expected_count = 2 if record["unknown_effect"]["last_confirmed_state"] == "committed" else 3
        if record["revision"] != expected_count or observed_operations != operation_sequence[:expected_count]:
            raise ProtocolError("invalid_publication_record", "unknown-effect revision history is inconsistent")
    else:
        expected_count = {
            "authorized": 1,
            "committed": 2,
            "pushed": 3,
            "draft_pr_verified": 4,
            "complete": 5,
        }[record["state"]]
        if record["revision"] != expected_count - 1 or observed_operations != operation_sequence[:expected_count]:
            raise ProtocolError("invalid_publication_record", "publication revision history is inconsistent")
    evidence_by_operation = {
        "commit_publication": record["commit"],
        "push_publication": record["push"],
        "create_draft_pr": record["draft_pull_request"],
        "complete_publication": record["completion"],
    }
    idempotency_by_operation = {item["operation"]: item for item in record["idempotency"]}
    bootstrap_item = idempotency_by_operation.get("bootstrap_publication")
    if bootstrap_item is None or bootstrap_item["result_id"] != stable_id(
        "publication", record["id"], bootstrap_item["request_id"]
    ):
        raise ProtocolError("invalid_publication_record", "publication bootstrap result identity is invalid")
    if retirement is not None:
        retirement_item = idempotency_by_operation.get("retire_publication")
        expected_retirement_result = stable_id(
            "publication-retirement", record["id"], retirement["request_id"], retirement["intent_digest"]
        )
        if (
            retirement_item is None
            or retirement_item["request_id"] != retirement["request_id"]
            or retirement_item["result_id"] != expected_retirement_result
        ):
            raise ProtocolError("invalid_retirement", "publication retirement lacks exact idempotency evidence")
    for operation, evidence in evidence_by_operation.items():
        if evidence is not None:
            item = idempotency_by_operation.get(operation)
            if item is None or item["request_id"] != evidence["request_id"]:
                raise ProtocolError("invalid_publication_record", "publication evidence lacks matching idempotency provenance")
            if operation == "commit_publication":
                expected_result = stable_id("publication-commit", record["id"], item["request_id"], evidence["commit_sha"])
            elif operation == "push_publication":
                expected_result = stable_id("publication-push", record["id"], item["request_id"], evidence["commit_sha"])
            elif operation == "create_draft_pr":
                expected_result = stable_id(
                    "publication-pr", record["id"], item["request_id"], str(evidence["number"]), evidence["head_sha"]
                )
            else:
                expected_result = stable_id(
                    "publication-complete",
                    record["id"],
                    item["request_id"],
                    record["commit"]["commit_sha"],
                    str(record["draft_pull_request"]["number"]),
                )
            if item["result_id"] != expected_result:
                raise ProtocolError("invalid_publication_record", "publication result identity is invalid")
    return record


def _verify_record_provenance(root: Path, record: Dict[str, Any], envelope: Dict[str, Any]) -> None:
    expected_revisions = {
        "commit_publication": 0,
        "push_publication": 1,
        "create_draft_pr": 2,
        "complete_publication": 3,
    }
    evidence_by_operation = {
        "commit_publication": record["commit"],
        "push_publication": record["push"],
        "create_draft_pr": record["draft_pull_request"],
        "complete_publication": record["completion"],
    }
    replay_by_operation = {item["operation"]: item for item in record["idempotency"]}
    for operation, evidence in evidence_by_operation.items():
        if evidence is None:
            continue
        capability_path = resolve_repo_path(root, evidence["capability_path"], require_exists=True)
        capability = validate_capability(load_safe_json(capability_path, f"{operation} capability"))
        request_id = evidence["request_id"]
        target_sha = envelope["base_sha"] if operation == "commit_publication" else record["commit"]["commit_sha"]
        destination_id: Optional[str] = None
        method = "git_temporary_index_commit"
        if operation == "push_publication":
            destination_id = _remote_destination(envelope)
            method = "git_create_only_branch_push"
        elif operation == "create_draft_pr":
            destination_id = _pull_request_destination(envelope)
            method = "github_create_draft_pr"
        elif operation == "complete_publication":
            destination_id = _pull_request_destination(envelope, record["draft_pull_request"]["number"])
            method = "complete_draft_pr_publication"
        expected_scope: Dict[str, Any] = {
            "allowed_paths": record["allowed_paths"],
            "target_sha": target_sha,
            "payload_digest": evidence["intent_digest"],
            "method": method,
        }
        if destination_id is not None:
            expected_scope["destination_id"] = destination_id
        if (
            capability["capability_id"] != capability_path.stem
            or capability["work_item_id"] != record["id"]
            or capability["work_item_revision"] != expected_revisions[operation]
            or capability["operation"] != operation
            or capability["scope"] != expected_scope
            or capability["executor"]["surface_id"] != record["writer"]["surface_id"]
            or capability["executor"]["executor_id"] != record["writer"]["executor_id"]
            or capability["executor"]["adapter_version"] != record["writer"]["adapter_version"]
            or capability["executor"].get("guard_digest") != current_guard_digest()
            or capability["approval"].get("approved_by") != envelope["approval"]["approved_by"]
            or capability["approval"].get("accepted_at") != envelope["approval"]["accepted_at"]
            or capability["approval"].get("expires_at") != envelope["approval"]["expires_at"]
            or capability["status"].get("state") != "consumed"
            or capability["status"].get("consumed_by_request_id") != request_id
            or json_digest(capability) != evidence["capability_digest"]
        ):
            raise ProtocolError("publication_provenance_mismatch", "publication capability provenance is inconsistent")
        transaction_path = _tx_path(root, record["id"], operation, request_id)
        transaction = _validate_operation_transaction(load_safe_json(transaction_path, f"{operation} transaction"))
        if (
            transaction.get("schema_version") != PUBLIC_VERSION
            or transaction.get("kind") != "publication_transaction"
            or transaction.get("request_id") != request_id
            or transaction.get("operation") != operation
            or transaction.get("publication_id") != record["id"]
            or transaction.get("record_revision") != expected_revisions[operation]
            or transaction.get("intent_digest") != evidence["intent_digest"]
            or transaction.get("capability_digest") != evidence["capability_digest"]
            or transaction.get("status") not in {
                "capability_consumed", "commit_prepared", "index_locked", "ref_updated", "index_replaced", "effect_observed", "finalized"
            }
        ):
            raise ProtocolError("publication_provenance_mismatch", "publication transaction provenance is inconsistent")
        replay = replay_by_operation.get(operation)
        if replay is None:
            raise ProtocolError("publication_provenance_mismatch", "publication evidence lacks its idempotency record")
        if transaction["status"] == "finalized" and transaction.get("result_id") != replay["result_id"]:
            raise ProtocolError("publication_provenance_mismatch", "finalized publication result differs from idempotency")
    if record["unknown_effect"] is not None:
        unknown = record["unknown_effect"]
        operation = unknown["operation"]
        request_id = unknown["request_id"]
        capability_path = _capability_path(root, record["id"], operation, request_id)
        capability = validate_capability(load_safe_json(capability_path, "unknown-effect capability"))
        transaction = _validate_operation_transaction(
            load_safe_json(
                _tx_path(root, record["id"], operation, request_id),
                "unknown-effect transaction",
            )
        )
        expected_revision = 1 if operation == "push_publication" else 2
        expected_destination = (
            _remote_destination(envelope)
            if operation == "push_publication"
            else _pull_request_destination(envelope)
        )
        expected_method = "git_create_only_branch_push" if operation == "push_publication" else "github_create_draft_pr"
        expected_scope = {
            "allowed_paths": record["allowed_paths"],
            "target_sha": record["commit"]["commit_sha"],
            "payload_digest": unknown["intent_digest"],
            "destination_id": expected_destination,
            "method": expected_method,
        }
        capability_digest = json_digest(capability)
        recoverable_unknown_status = transaction.get("status") in {"intent", "capability_consumed", "effect_unknown"}
        reason_matches = (
            transaction.get("status") != "effect_unknown"
            or transaction.get("reason_code") == unknown["reason_code"]
        )
        if (
            capability_path != _capability_path(root, record["id"], operation, request_id)
            or capability["capability_id"] != capability_path.stem
            or capability["work_item_id"] != record["id"]
            or capability["work_item_revision"] != expected_revision
            or capability["operation"] != operation
            or capability["scope"] != expected_scope
            or capability["executor"].get("surface_id") != record["writer"]["surface_id"]
            or capability["executor"].get("executor_id") != record["writer"]["executor_id"]
            or capability["executor"].get("adapter_version") != record["writer"]["adapter_version"]
            or capability["executor"].get("guard_digest") != current_guard_digest()
            or capability["approval"].get("approved_by") != envelope["approval"]["approved_by"]
            or capability["approval"].get("accepted_at") != envelope["approval"]["accepted_at"]
            or capability["approval"].get("expires_at") != envelope["approval"]["expires_at"]
            or capability["status"].get("state") != "consumed"
            or capability["status"].get("consumed_by_request_id") != request_id
            or not recoverable_unknown_status
            or transaction.get("schema_version") != PUBLIC_VERSION
            or transaction.get("kind") != "publication_transaction"
            or transaction.get("request_id") != request_id
            or transaction.get("operation") != operation
            or transaction.get("publication_id") != record["id"]
            or transaction.get("record_revision") != expected_revision
            or transaction.get("intent_digest") != unknown["intent_digest"]
            or transaction.get("capability_digest") != capability_digest
            or not reason_matches
        ):
            raise ProtocolError("publication_provenance_mismatch", "unknown outward effect lacks exact capability and journal evidence")
    lifecycle = record["lifecycle_transition"]
    if lifecycle is not None:
        capability_path = resolve_repo_path(root, lifecycle["capability_path"], require_exists=True)
        capability = validate_capability(load_safe_json(capability_path, "publication lifecycle capability"))
        normalized_capability = copy.deepcopy(capability)
        normalized_capability["status"] = {
            "state": "active",
            "revoked_at": None,
            "consumed_at": None,
            "consumed_by_request_id": None,
        }
        if (
            capability["work_item_id"] != record["source_work_item_id"]
            or capability["work_item_revision"] != record["source_work_item_revision"]
            or capability["operation"] != "transition_work_item"
            or capability["scope"].get("allowed_paths") != [record["source_work_item"]]
            or capability["scope"].get("target_sha") != record["base_sha"]
            or capability["scope"].get("payload_digest") != lifecycle["intent_digest"]
            or capability["status"].get("state") != "consumed"
            or capability["status"].get("consumed_by_request_id") != lifecycle["request_id"]
            or json_digest(normalized_capability) != lifecycle["capability_digest"]
        ):
            raise ProtocolError("publication_provenance_mismatch", "publication lifecycle capability is inconsistent")
        work_item = validate_work_item(
            load_safe_json(resolve_repo_path(root, record["source_work_item"], require_exists=True), "publication source work item")
        )
        matching_transitions = [
            item
            for item in work_item["transitions"]
            if item.get("id") == lifecycle["transition_id"]
        ]
        transition = matching_transitions[0] if len(matching_transitions) == 1 else None
        if (
            work_item["id"] != record["source_work_item_id"]
            or work_item["revision"] < lifecycle["source_revision_after"]
            or work_item["lifecycle"]["state"] not in SOURCE_POST_PUBLICATION_STATES
            or not isinstance(transition, dict)
            or transition.get("id") != lifecycle["transition_id"]
            or transition.get("request_id") != lifecycle["request_id"]
            or transition.get("capability_path") != lifecycle["capability_path"]
            or transition.get("capability_digest") != lifecycle["capability_digest"]
            or transition.get("intent_digest") != lifecycle["intent_digest"]
        ):
            raise ProtocolError("publication_provenance_mismatch", "source lifecycle no longer matches publication completion")
        transition_journal = load_safe_json(
            resolve_repo_path(root, f"{TRANSACTION_PREFIX}{lifecycle['request_id']}.json", require_exists=True),
            "publication lifecycle transaction",
        )
        if (
            transition_journal.get("status") != "finalized"
            or transition_journal.get("operation") != "transition_work_item"
            or transition_journal.get("request_id") != lifecycle["request_id"]
            or transition_journal.get("result_id") != lifecycle["transition_id"]
            or transition_journal.get("payload_digest") != lifecycle["intent_digest"]
        ):
            raise ProtocolError("publication_provenance_mismatch", "publication lifecycle transaction is inconsistent")
    retirement = record.get("retirement")
    if retirement is not None:
        capability_path = resolve_repo_path(root, retirement["capability_path"], require_exists=True)
        capability = validate_capability(load_safe_json(capability_path, "publication retirement capability"))
        target_sha = record["commit"]["commit_sha"] if record.get("commit") is not None else envelope["base_sha"]
        target_paths = sorted(
            [record["source_work_item"], record["source_reservation_path"], _record_path(root, record["id"]).relative_to(root).as_posix()]
        )
        expected_scope = {
            "allowed_paths": target_paths,
            "target_sha": target_sha,
            "destination_id": f"project-local/publication/{record['id']}",
            "method": "retire_local_publication_reservation",
            "payload_digest": retirement["intent_digest"],
        }
        consumed_at = parse_timestamp(capability["status"].get("consumed_at"), "retirement capability consumed_at")
        role = "egress" if retirement["prior_state"] in {"pushed", "effect_unknown"} else "writer"
        if (
            capability_path != _capability_path(root, record["id"], "retire_publication", retirement["request_id"])
            or capability["capability_id"] != capability_path.stem
            or capability["work_item_id"] != record["id"]
            or capability["work_item_revision"] != retirement["prior_revision"]
            or capability["operation"] != "retire_publication"
            or capability["scope"] != expected_scope
            or capability["executor"].get("guard_digest") != current_guard_digest()
            or capability["status"].get("state") != "consumed"
            or capability["status"].get("consumed_by_request_id") != retirement["request_id"]
            or json_digest(capability) != retirement["capability_digest"]
        ):
            raise ProtocolError("publication_provenance_mismatch", "publication retirement capability is inconsistent")
        check_authority(
            capability_path=capability_path,
            registry_path=resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True),
            operation="retire_publication",
            work_item_id=record["id"],
            work_item_revision=retirement["prior_revision"],
            request_id=retirement["request_id"],
            surface_id=capability["executor"]["surface_id"],
            executor_id=capability["executor"]["executor_id"],
            adapter_version=capability["executor"]["adapter_version"],
            guard_digest=current_guard_digest(),
            role=role,
            target_paths=target_paths,
            target_sha=target_sha,
            destination_id=f"project-local/publication/{record['id']}",
            method="retire_local_publication_reservation",
            payload_digest=retirement["intent_digest"],
            allow_consumed_by_request_id=True,
            require_exact_paths=True,
            now=consumed_at,
        )
        transaction = _validate_operation_transaction(
            load_safe_json(
                _tx_path(root, record["id"], "retire_publication", retirement["request_id"]),
                "publication retirement transaction",
            )
        )
        result_id = stable_id(
            "publication-retirement", record["id"], retirement["request_id"], retirement["intent_digest"]
        )
        if (
            transaction.get("schema_version") != PUBLIC_VERSION
            or transaction.get("kind") != "publication_transaction"
            or transaction.get("request_id") != retirement["request_id"]
            or transaction.get("operation") != "retire_publication"
            or transaction.get("publication_id") != record["id"]
            or transaction.get("record_revision") != retirement["prior_revision"]
            or transaction.get("intent_digest") != retirement["intent_digest"]
            or transaction.get("capability_digest") != retirement["capability_digest"]
            or transaction.get("status") not in {"capability_consumed", "finalized"}
            or (transaction.get("status") == "finalized" and transaction.get("result_id") != result_id)
        ):
            raise ProtocolError("publication_provenance_mismatch", "publication retirement transaction is inconsistent")


def _verify_record_evidence_bindings(record: Dict[str, Any], envelope: Dict[str, Any]) -> None:
    commit = record.get("commit")
    if commit is not None:
        expected_message = hashlib.sha256(_commit_message(envelope)).hexdigest()
        if (
            commit.get("base_sha") != envelope["base_sha"]
            or commit.get("candidate_digest") != envelope["candidate_digest"]
            or commit.get("path_set_digest") != envelope["path_set_digest"]
            or commit.get("message_digest") != expected_message
            or commit.get("trusted_public_check_digest") != envelope["trusted_runtime"]["public_checker_digest"]
        ):
            raise ProtocolError("publication_record_mismatch", "commit evidence differs from immutable publication approval")
    push = record.get("push")
    if push is not None:
        remote = envelope["remote"]
        expected_observation = json_digest(
            {
                "repository": remote["repository"],
                "repository_id": remote["repository_id"],
                "base": envelope["base_sha"],
                "head": commit["commit_sha"],
            }
        )
        if (
            commit is None
            or push.get("repository") != remote["repository"]
            or push.get("repository_id") != remote["repository_id"]
            or push.get("remote_name") != remote["remote_name"]
            or push.get("base_branch") != remote["base_branch"]
            or push.get("base_sha") != envelope["base_sha"]
            or push.get("head_branch") != remote["head_branch"]
            or push.get("commit_sha") != commit["commit_sha"]
            or push.get("observed_remote_sha") != commit["commit_sha"]
            or push.get("observation_digest") != expected_observation
        ):
            raise ProtocolError("publication_record_mismatch", "push evidence differs from immutable publication approval")
    draft = record.get("draft_pull_request")
    if draft is not None:
        remote = envelope["remote"]
        expected_body = _pr_body(envelope, draft["request_id"], commit["commit_sha"])
        expected_url = f"https://github.com/{remote['repository']}/pull/{draft['number']}"
        if (
            commit is None
            or push is None
            or draft.get("repository") != remote["repository"]
            or draft.get("repository_id") != remote["repository_id"]
            or draft.get("url") != expected_url
            or draft.get("base_branch") != remote["base_branch"]
            or draft.get("head_branch") != remote["head_branch"]
            or draft.get("head_sha") != commit["commit_sha"]
            or draft.get("is_draft") is not True
            or draft.get("title_digest") != hashlib.sha256(envelope["pull_request"]["title"].encode("utf-8")).hexdigest()
            or draft.get("body_digest") != hashlib.sha256(expected_body).hexdigest()
        ):
            raise ProtocolError("publication_record_mismatch", "draft pull-request evidence differs from immutable approval")
    lifecycle = record.get("lifecycle_transition")
    if lifecycle is not None:
        if commit is None or draft is None:
            raise ProtocolError("publication_record_mismatch", "publication transition lacks commit and draft-PR evidence")
        evidence = [
            f"publication-record:{record['id']}",
            f"commit:{commit['commit_sha']}",
            f"draft-pr:{draft['number']}",
            f"required-checks:{record['completion']['required_checks_digest'] if record.get('completion') else ''}",
        ]
        if record.get("completion") is not None and lifecycle.get("evidence_digest") != json_digest(evidence):
            raise ProtocolError("publication_record_mismatch", "publication transition evidence digest is inconsistent")
    completion = record.get("completion")
    if completion is not None:
        expected_verification = json_digest(
            {
                "base": envelope["base_sha"],
                "head": commit["commit_sha"],
                "pr": draft,
                "checks": completion["required_checks_digest"],
                "transition": lifecycle,
            }
        )
        if completion.get("verification_digest") != expected_verification:
            raise ProtocolError("publication_record_mismatch", "publication completion verification digest is inconsistent")


def _load_publication(root: Path, relative: str, *, require_active: bool = True) -> Tuple[Path, Dict[str, Any], Dict[str, Any]]:
    rel = canonical_relative_path(relative)
    if not rel.startswith(PUBLICATION_PREFIX):
        raise ProtocolError("invalid_publication_path", "publication record must use protected runtime storage")
    path = resolve_repo_path(root, rel, require_exists=True)
    record = _validate_record(load_safe_json(path, "publication record"))
    if path != _record_path(root, record["id"]):
        raise ProtocolError("invalid_publication_path", "publication record path does not match its bound identifier")
    envelope_path = resolve_repo_path(root, record["envelope_path"], require_exists=True)
    envelope = validate_publication_envelope(load_safe_json(envelope_path, "publication envelope"), root=root, require_active=require_active)
    if json_digest(envelope) != record["envelope_digest"]:
        raise ProtocolError("envelope_changed", "stored publication envelope changed")
    expected_record_bindings = {
        "id": envelope["envelope_id"],
        "envelope_path": _stored_envelope_path(root, envelope["envelope_id"]).relative_to(root).as_posix(),
        "source_work_item": envelope["source_work_item"],
        "source_work_item_id": envelope["source_work_item_id"],
        "source_work_item_revision": envelope["source_work_item_revision"],
        "base_sha": envelope["base_sha"],
        "branch": envelope["branch"],
        "candidate_digest": envelope["candidate_digest"],
        "path_set_digest": envelope["path_set_digest"],
        "allowed_paths": envelope["allowed_paths"],
        "manifest_digest": envelope["manifest"]["sha256"],
        "writer": envelope["writer"],
        "source_reservation_path": publication_reservation_path(root, envelope["source_work_item_id"]).relative_to(root).as_posix(),
    }
    if any(record.get(field) != value for field, value in expected_record_bindings.items()):
        raise ProtocolError("publication_record_mismatch", "publication record differs from its immutable envelope bindings")
    _verify_record_evidence_bindings(record, envelope)
    _verify_record_provenance(root, record, envelope)
    _, source_reservation = _validate_source_reservation(root, record, envelope)
    source_work_item = validate_work_item(
        load_safe_json(resolve_repo_path(root, record["source_work_item"], require_exists=True), "publication source work item")
    )
    source_exact = (
        source_work_item["revision"] == record["source_work_item_revision"]
        and json_digest(source_work_item) == envelope["source_work_item_digest"]
        and source_work_item["lifecycle"]["state"] == "release_ready"
    )
    transition_recovery = (
        record["state"] == "draft_pr_verified"
        and source_work_item["revision"] == record["source_work_item_revision"] + 1
        and source_work_item["lifecycle"]["state"] == "awaiting_release"
        and bool(source_work_item["transitions"])
        and source_work_item["transitions"][-1].get("from") == "release_ready"
        and source_work_item["transitions"][-1].get("to") == "awaiting_release"
        and source_work_item["transitions"][-1].get("operation") == "publication_draft_pr_verified"
        and f"publication-record:{record['id']}" in source_work_item["transitions"][-1].get("evidence", [])
    )
    completed_source = (
        record["state"] == "complete"
        and source_work_item["revision"] >= record["source_work_item_revision"] + 1
        and source_work_item["lifecycle"]["state"] in SOURCE_POST_PUBLICATION_STATES
    )
    if not source_exact and not transition_recovery and not completed_source:
        raise ProtocolError("publication_source_changed", "publication source work item changed outside the guarded workflow")
    if require_active:
        if record["reservation"]["status"] != "active" or parse_timestamp(record["reservation"]["lease_expires_at"], "lease") <= utc_now():
            raise ProtocolError("inactive_publication_writer", "publication writer reservation is inactive")
        if source_reservation["status"] != "active":
            raise ProtocolError("inactive_publication_writer", "publication source reservation is inactive")
        _verify_executor(root, envelope)
    return path, record, envelope


def _replay(record: Dict[str, Any], request_id: str, operation: str) -> Optional[Dict[str, Any]]:
    matches = [item for item in record["idempotency"] if item.get("request_id") == request_id]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].get("operation") != operation:
        raise ProtocolError("idempotency_conflict", "request id was already used for a different publication intent")
    return matches[0]


def _load_operation(
    root: Path,
    publication_rel: str,
    operation: str,
    request_id: str,
) -> Tuple[Path, Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]], bool]:
    record_path, record, envelope = _load_publication(root, publication_rel, require_active=False)
    replay = _replay(record, request_id, operation)
    if replay is not None:
        return record_path, record, envelope, replay, False
    transaction_path = _tx_path(root, record["id"], operation, request_id)
    capability_path = _capability_path(root, record["id"], operation, request_id)
    recovering = False
    if transaction_path.exists() or capability_path.exists():
        if not transaction_path.exists() or not capability_path.exists():
            raise ProtocolError("recovery_state_incomplete", "publication recovery lacks transaction or capability state")
        transaction = _validate_operation_transaction(load_safe_json(transaction_path, "publication recovery transaction"))
        capability = load_safe_json(capability_path, "publication recovery capability")
        recovering = (
            transaction.get("request_id") == request_id
            and transaction.get("operation") == operation
            and transaction.get("publication_id") == record["id"]
            and transaction.get("status") != "finalized"
            and capability.get("status", {}).get("state") == "consumed"
            and capability.get("status", {}).get("consumed_by_request_id") == request_id
        )
        if not recovering:
            raise ProtocolError("recovery_state_inconsistent", "publication recovery state is not exact")
    if not recovering:
        record_path, record, envelope = _load_publication(root, publication_rel, require_active=True)
    return record_path, record, envelope, None, recovering


def _append_idempotency(record: Dict[str, Any], request_id: str, operation: str, result_id: str) -> None:
    record["idempotency"].append(
        {"request_id": request_id, "operation": operation, "result_id": result_id, "accepted_at": isoformat(utc_now())}
    )


def bootstrap_publication(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    if not Path(args.project_root).is_absolute():
        raise ProtocolError("absolute_project_root_required", "publication project_root must be absolute")
    source_rel = _safe_input_path(root, args.envelope_source, "publication envelope")
    envelope_bytes = read_local_protocol_input(
        root,
        args.envelope_source,
        "publication envelope",
        max_bytes=MAX_ENVELOPE_BYTES,
    )
    try:
        envelope_raw = json.loads(
            envelope_bytes.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid_json", "publication envelope is not valid UTF-8 JSON") from exc
    if not isinstance(envelope_raw, dict):
        raise ProtocolError("invalid_document", "publication envelope must contain one JSON object")
    envelope = validate_publication_envelope(envelope_raw, root=root, require_active=False)
    request_id = require_id(args.request_id, "request_id")
    publication_id = envelope["envelope_id"]
    record_path = _record_path(root, publication_id)
    stored_path = _stored_envelope_path(root, publication_id)
    transaction_path = _tx_path(root, publication_id, "bootstrap", request_id)
    with exclusive_lock(_lock_path(root, publication_id)), exclusive_lock(
        _source_lock_path(root, envelope["source_work_item"])
    ):
        if record_path.exists():
            loaded_path, record, stored_envelope = _load_publication(
                root,
                record_path.relative_to(root).as_posix(),
                require_active=False,
            )
            replay = _replay(record, request_id, "bootstrap_publication")
            registry = validate_registry(
                load_safe_json(resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True), "executor registry")
            )
            intent_digest = json_digest(
                {"source": source_rel, "envelope": envelope, "registry": json_digest(registry)}
            )
            if (
                loaded_path != record_path
                or replay is None
                or not transaction_path.exists()
                or stored_envelope != envelope
            ):
                raise ProtocolError("bootstrap_conflict", "publication bootstrap state already exists with different intent")
            journal = load_safe_json(transaction_path, "publication bootstrap transaction")
            require_exact_keys(
                journal,
                [
                    "schema_version", "kind", "request_id", "operation", "publication_id",
                    "intent_digest", "result_id", "status", "created_at",
                ],
                ["finalized_at"],
                "publication bootstrap transaction",
            )
            if (
                journal.get("schema_version") != PUBLIC_VERSION
                or journal.get("kind") != "publication_transaction"
                or journal.get("request_id") != request_id
                or journal.get("operation") != "bootstrap_publication"
                or journal.get("publication_id") != publication_id
                or journal.get("intent_digest") != intent_digest
                or journal.get("result_id") != replay["result_id"]
                or journal.get("status") not in {"intent", "finalized"}
            ):
                raise ProtocolError("bootstrap_conflict", "publication bootstrap transaction is inconsistent")
            parse_timestamp(journal["created_at"], "publication bootstrap created_at")
            if journal["status"] == "finalized":
                parse_timestamp(journal.get("finalized_at"), "publication bootstrap finalized_at")
            if journal["status"] != "finalized":
                journal["status"] = "finalized"
                journal["finalized_at"] = isoformat(utc_now())
                atomic_write_json(transaction_path, journal)
            return {"ok": True, "replay": True, "publication": record_path.relative_to(root).as_posix(), "state": record["state"], "revision": record["revision"]}
        envelope = validate_publication_envelope(envelope, root=root, require_active=True)
        work = _verify_source_candidate(root, envelope)
        registry, _ = _verify_executor(root, envelope)
        _public_metadata_check(
            root,
            envelope,
            envelope["pull_request"]["title"],
            envelope["pull_request"]["body"].encode("utf-8"),
        )
        result_id = stable_id("publication", publication_id, request_id)
        record = {
            "schema_version": PUBLIC_VERSION,
            "kind": "publication_record",
            "id": publication_id,
            "revision": 0,
            "state": "authorized",
            "envelope_path": stored_path.relative_to(root).as_posix(),
            "envelope_digest": json_digest(envelope),
            "source_work_item": envelope["source_work_item"],
            "source_work_item_id": work["id"],
            "source_work_item_revision": work["revision"],
            "base_sha": envelope["base_sha"],
            "branch": envelope["branch"],
            "candidate_digest": envelope["candidate_digest"],
            "path_set_digest": envelope["path_set_digest"],
            "allowed_paths": envelope["allowed_paths"],
            "manifest_digest": envelope["manifest"]["sha256"],
            "writer": copy.deepcopy(envelope["writer"]),
            "reservation": {"status": "active", "lease_expires_at": envelope["lease_expires_at"]},
            "source_reservation_path": publication_reservation_path(
                root, envelope["source_work_item_id"]
            ).relative_to(root).as_posix(),
            "commit": None,
            "push": None,
            "draft_pull_request": None,
            "lifecycle_transition": None,
            "completion": None,
            "unknown_effect": None,
            "retirement": None,
            "idempotency": [],
        }
        _append_idempotency(record, request_id, "bootstrap_publication", result_id)
        record = _validate_record(record)
        journal = {
            "schema_version": PUBLIC_VERSION,
            "kind": "publication_transaction",
            "request_id": request_id,
            "operation": "bootstrap_publication",
            "publication_id": publication_id,
            "intent_digest": json_digest({"source": source_rel, "envelope": envelope, "registry": json_digest(registry)}),
            "result_id": result_id,
            "status": "intent",
            "created_at": isoformat(utc_now()),
        }
        _recheck_bootstrap_authority(root, envelope, work)
        if transaction_path.exists() or transaction_path.is_symlink():
            existing = load_safe_json(transaction_path, "publication bootstrap transaction")
            if existing != journal:
                # The timestamp is chosen on first intent creation, so compare
                # the immutable fields and retain that accepted time on retry.
                comparable = {key: existing.get(key) for key in journal if key != "created_at"}
                expected = {key: value for key, value in journal.items() if key != "created_at"}
                if comparable != expected or existing.get("status") != "intent":
                    raise ProtocolError("bootstrap_conflict", "publication bootstrap transaction differs from the current intent")
                parse_timestamp(existing.get("created_at"), "publication bootstrap created_at")
                journal = existing
        else:
            atomic_write_json(transaction_path, journal)
        if stored_path.exists() or stored_path.is_symlink():
            if json_digest(load_safe_json(stored_path, "stored publication envelope")) != json_digest(envelope):
                raise ProtocolError("bootstrap_conflict", "stored publication envelope differs from the current intent")
        else:
            exclusive_write_json(stored_path, envelope)
        _claim_source_reservation(root, envelope, work)
        exclusive_write_json(record_path, record)
        journal["status"] = "finalized"
        journal["finalized_at"] = isoformat(utc_now())
        atomic_write_json(transaction_path, journal)
    return {"ok": True, "replay": False, "publication": record_path.relative_to(root).as_posix(), "state": "authorized", "revision": 0}


def _capability_path(root: Path, publication_id: str, operation: str, request_id: str) -> Path:
    capability_id = stable_id("cap", publication_id, operation, request_id)
    return resolve_repo_path(root, f"{CAPABILITY_PREFIX}{capability_id}.json")


def _consume_operation(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    *,
    operation: str,
    request_id: str,
    target_sha: str,
    payload_digest: str,
    destination_id: Optional[str] = None,
    method: Optional[str] = None,
) -> Tuple[str, str]:
    registry = validate_registry(load_safe_json(resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True), "executor registry"))
    writer = envelope["writer"]
    capability_path = _capability_path(root, record["id"], operation, request_id)
    capability_id = capability_path.stem
    scope: Dict[str, Any] = {
        "allowed_paths": record["allowed_paths"],
        "target_sha": target_sha,
        "payload_digest": payload_digest,
    }
    if destination_id is not None:
        scope["destination_id"] = destination_id
    if method is not None:
        scope["method"] = method
    capability = {
        "schema_version": PUBLIC_VERSION,
        "kind": "approval_capability",
        "capability_id": capability_id,
        "work_item_id": record["id"],
        "work_item_revision": record["revision"],
        "operation": operation,
        "scope": scope,
        "executor": {
            "surface_id": writer["surface_id"],
            "executor_id": writer["executor_id"],
            "adapter_version": writer["adapter_version"],
            "guard_digest": current_guard_digest(),
            "registry_version": registry["registry_version"],
        },
        "approval": {
            "approved_by": envelope["approval"]["approved_by"],
            "accepted_at": envelope["approval"]["accepted_at"],
            "expires_at": envelope["approval"]["expires_at"],
            "one_time": True,
            "summary": f"Internal one-time {operation} capability derived from publication envelope {record['id']}.",
        },
        "status": {"state": "active", "revoked_at": None, "consumed_at": None, "consumed_by_request_id": None},
    }
    if capability_path.exists():
        existing = load_safe_json(capability_path, "publication capability")
        normalized = copy.deepcopy(existing)
        normalized["status"] = capability["status"]
        if normalized != capability:
            raise ProtocolError("capability_conflict", "publication capability differs from the exact derived intent")
    else:
        exclusive_write_json(capability_path, capability)
        existing = capability
    authority_time = None
    if (
        existing.get("status", {}).get("state") == "consumed"
        and existing.get("status", {}).get("consumed_by_request_id") == request_id
    ):
        authority_time = parse_timestamp(existing["status"].get("consumed_at"), "capability consumed_at")
    authority_role = "writer" if operation == "commit_publication" else "egress"
    consumed = consume_capability(
        capability_path=capability_path,
        registry_path=resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True),
        request_id=request_id,
        check_kwargs={
            "operation": operation,
            "work_item_id": record["id"],
            "work_item_revision": record["revision"],
            "surface_id": writer["surface_id"],
            "executor_id": writer["executor_id"],
            "adapter_version": writer["adapter_version"],
            "guard_digest": current_guard_digest(),
            "role": authority_role,
            "target_paths": record["allowed_paths"],
            "target_sha": target_sha,
            "destination_id": destination_id,
            "method": method,
            "payload_digest": payload_digest,
            "require_exact_paths": True,
        },
        now=authority_time,
    )
    return capability_path.relative_to(root).as_posix(), json_digest(consumed)


def _recheck_consumed_operation(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    operation: str,
    request_id: str,
    intent: Dict[str, Any],
) -> None:
    """Revalidate current-clock authority immediately before an effect."""

    validate_publication_envelope(copy.deepcopy(envelope), root=root, require_active=True)
    _verify_executor(root, envelope)
    path = _capability_path(root, record["id"], operation, request_id)
    capability = validate_capability(load_safe_json(path, "publication capability"))
    writer = envelope["writer"]
    role = "writer" if operation == "commit_publication" else "egress"
    revisions = {
        "commit_publication": 0,
        "push_publication": 1,
        "create_draft_pr": 2,
        "complete_publication": 3,
    }
    commit_sha = record.get("commit", {}).get("commit_sha") if isinstance(record.get("commit"), dict) else None
    if operation == "commit_publication":
        target_sha = envelope["base_sha"]
        destination_id = None
        method = "git_temporary_index_commit"
    elif operation == "push_publication":
        target_sha = commit_sha
        destination_id = _remote_destination(envelope)
        method = "git_create_only_branch_push"
    elif operation == "create_draft_pr":
        target_sha = commit_sha
        destination_id = _pull_request_destination(envelope)
        method = "github_create_draft_pr"
    elif operation == "complete_publication":
        target_sha = commit_sha
        draft = record.get("draft_pull_request")
        number = draft.get("number") if isinstance(draft, dict) else None
        destination_id = _pull_request_destination(envelope, number)
        method = "complete_draft_pr_publication"
    else:
        raise ProtocolError("unsupported_operation", "publication authority operation is unsupported")
    if target_sha is None or (operation == "complete_publication" and destination_id.endswith("/None")):
        raise ProtocolError("publication_provenance_mismatch", "publication authority lacks immutable target evidence")
    payload_digest = json_digest(intent)
    transaction = _validate_operation_transaction(
        load_safe_json(_tx_path(root, record["id"], operation, request_id), "publication transaction")
    )
    if (
        transaction.get("record_revision") != revisions[operation]
        or transaction.get("intent_digest") != payload_digest
        or transaction.get("operation") != operation
        or transaction.get("request_id") != request_id
        or transaction.get("publication_id") != record["id"]
    ):
        raise ProtocolError("publication_provenance_mismatch", "publication transaction differs from current immutable intent")
    check_authority(
        capability_path=path,
        registry_path=resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True),
        operation=operation,
        work_item_id=record["id"],
        work_item_revision=revisions[operation],
        request_id=request_id,
        surface_id=writer["surface_id"],
        executor_id=writer["executor_id"],
        adapter_version=writer["adapter_version"],
        guard_digest=current_guard_digest(),
        role=role,
        target_paths=record["allowed_paths"],
        target_sha=target_sha,
        destination_id=destination_id,
        method=method,
        payload_digest=payload_digest,
        allow_consumed_by_request_id=True,
        require_exact_paths=True,
    )


def _begin_transaction(
    root: Path,
    record: Dict[str, Any],
    request_id: str,
    operation: str,
    intent: Dict[str, Any],
) -> Tuple[Path, Dict[str, Any], bool]:
    path = _tx_path(root, record["id"], operation, request_id)
    digest = json_digest(intent)
    expected = {
        "schema_version": PUBLIC_VERSION,
        "kind": "publication_transaction",
        "request_id": request_id,
        "operation": operation,
        "publication_id": record["id"],
        "record_revision": record["revision"],
        "intent_digest": digest,
        "status": "intent",
        "created_at": isoformat(utc_now()),
    }
    if path.exists():
        current = _validate_operation_transaction(load_safe_json(path, "publication transaction"))
        immutable = {key: value for key, value in expected.items() if key not in {"status", "created_at"}}
        if any(current.get(key) != value for key, value in immutable.items()):
            raise ProtocolError("transaction_conflict", "publication transaction is stale or mismatched")
        allowed_statuses = {
            "intent", "capability_consumed", "commit_prepared", "index_locked", "ref_updated", "index_replaced",
            "effect_observed", "blocked_collision", "finalized", "effect_unknown",
        }
        if current.get("status") not in allowed_statuses:
            raise ProtocolError("transaction_conflict", "publication transaction status is invalid")
        created_at = parse_timestamp(current.get("created_at"), "publication transaction created_at")
        if created_at > utc_now():
            raise ProtocolError("transaction_conflict", "publication transaction creation time is in the future")
        return path, current, False
    atomic_write_json(path, expected)
    return path, expected, True


def _validate_operation_transaction(document: Dict[str, Any]) -> Dict[str, Any]:
    statuses = {
        "intent", "capability_consumed", "commit_prepared", "index_locked", "ref_updated",
        "index_replaced", "effect_observed", "blocked_collision", "effect_unknown", "finalized",
    }
    optional = {
        "capability_digest", "commit_sha", "tree_sha", "trusted_check_digest",
        "starting_index_digest", "prepared_index_digest", "index_lock_identity", "reason_code",
        "remote_head_sha", "reconciled_observation", "pr_number", "pr_url", "result_id",
        *(f"{status}_at" for status in statuses if status != "intent"),
    }
    require_exact_keys(
        document,
        [
            "schema_version", "kind", "request_id", "operation", "publication_id",
            "record_revision", "intent_digest", "status", "created_at",
        ],
        sorted(optional),
        "publication transaction",
    )
    if (
        document["schema_version"] != PUBLIC_VERSION
        or document["kind"] != "publication_transaction"
        or document["operation"] not in {*OPERATIONS, "retire_publication"}
        or document["status"] not in statuses
        or not isinstance(document["record_revision"], int)
        or document["record_revision"] < 0
    ):
        raise ProtocolError("transaction_conflict", "publication transaction identity or status is invalid")
    require_id(document["request_id"], "transaction request id")
    require_id(document["publication_id"], "transaction publication id")
    require_digest(document["intent_digest"], "transaction intent digest")
    created_at = parse_timestamp(document["created_at"], "publication transaction created_at")
    if created_at > utc_now():
        raise ProtocolError("transaction_conflict", "publication transaction creation time is in the future")
    for field in ("capability_digest", "trusted_check_digest", "starting_index_digest", "prepared_index_digest"):
        if field in document:
            require_digest(document[field], f"transaction {field}")
    for field in ("commit_sha", "tree_sha", "remote_head_sha"):
        if field in document and (not isinstance(document[field], str) or not GIT_SHA_RE.fullmatch(document[field])):
            raise ProtocolError("transaction_conflict", f"transaction {field} is invalid")
    for field in (f"{status}_at" for status in statuses if status != "intent"):
        if field in document:
            parse_timestamp(document[field], f"transaction {field}")
    if "index_lock_identity" in document:
        identity = document["index_lock_identity"]
        if (
            not isinstance(identity, dict)
            or set(identity) != {"device", "inode", "sha256"}
            or not isinstance(identity["device"], int)
            or not isinstance(identity["inode"], int)
            or not isinstance(identity["sha256"], str)
            or not SHA256_RE.fullmatch(identity["sha256"])
        ):
            raise ProtocolError("transaction_conflict", "transaction index-lock identity is invalid")
    if "reconciled_observation" in document and not isinstance(document["reconciled_observation"], bool):
        raise ProtocolError("transaction_conflict", "transaction reconciliation marker is invalid")
    if "pr_number" in document and (not isinstance(document["pr_number"], int) or document["pr_number"] <= 0):
        raise ProtocolError("transaction_conflict", "transaction pull-request number is invalid")
    if "reason_code" in document:
        _string(document["reason_code"], "transaction reason code", maximum=200)
    return document


def _tx_status(path: Path, journal: Dict[str, Any], status_value: str, **fields: Any) -> Dict[str, Any]:
    updated = copy.deepcopy(journal)
    updated["status"] = status_value
    updated.update(fields)
    updated[f"{status_value}_at"] = isoformat(utc_now())
    updated = _validate_operation_transaction(updated)
    atomic_write_json(path, updated)
    return updated


def _fault(point: str) -> None:
    if os.environ.get("EXOCORTEX_TEST_MODE") == "1" and os.environ.get("EXOCORTEX_FAULT_POINT") == point:
        raise ProtocolError("injected_fault", f"publication fault injected at {point}")


def _assert_actor(args: argparse.Namespace, envelope: Dict[str, Any]) -> None:
    writer = envelope["writer"]
    if (args.surface_id, args.executor_id, args.adapter_version) != (
        writer["surface_id"], writer["executor_id"], writer["adapter_version"]
    ):
        raise ProtocolError("writer_mismatch", "only the envelope-bound publication writer may execute this operation")


def _read_source_bytes(root: Path, relative: str) -> Optional[Tuple[bytes, str]]:
    parts = PurePosixPath(relative).parts
    if not parts:
        raise ProtocolError("unsafe_candidate_path", "candidate path is empty")
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory_flag = getattr(os, "O_DIRECTORY", 0)
    if not nofollow or not directory_flag:
        raise ProtocolError("safe_topology_unsupported", "publication requires descriptor-relative no-follow file access")
    directory_descriptors: List[int] = []
    descriptor: Optional[int] = None
    try:
        current = os.open(str(root), os.O_RDONLY | directory_flag | nofollow)
        directory_descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(part, os.O_RDONLY | directory_flag | nofollow, dir_fd=current)
            directory_descriptors.append(current)
        try:
            descriptor = os.open(parts[-1], os.O_RDONLY | nofollow, dir_fd=current)
        except FileNotFoundError:
            return None
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ProtocolError("unsafe_candidate_path", "candidate source must be an ordinary single-link file")
        if before.st_size > MAX_SOURCE_FILE_BYTES:
            raise ProtocolError("candidate_file_too_large", "candidate source exceeds the publication size limit")
        chunks: List[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_SOURCE_FILE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_SOURCE_FILE_BYTES:
                raise ProtocolError("candidate_file_too_large", "candidate source exceeds the publication size limit")
        after = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, stat.S_IMODE(before.st_mode))
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, stat.S_IMODE(after.st_mode))
        if identity != identity_after:
            raise ProtocolError("candidate_race", "candidate source changed while being read")
        mode = "100755" if before.st_mode & stat.S_IXUSR else "100644"
        return b"".join(chunks), mode
    except FileNotFoundError as exc:
        raise ProtocolError("unsafe_candidate_path", "candidate path ancestor disappeared") from exc
    except OSError as exc:
        raise ProtocolError("unsafe_candidate_path", "candidate path cannot be safely opened") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        for directory_descriptor in reversed(directory_descriptors):
            os.close(directory_descriptor)


def _manifest_digest_map(content: bytes, field: str) -> Dict[str, str]:
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ProtocolError("manifest_invalid", f"{field} is not valid UTF-8") from exc
    values: Dict[str, str] = {}
    ordered: List[str] = []
    for line in lines:
        match = CHECKSUM_LINE_RE.fullmatch(line)
        if match is None:
            raise ProtocolError("manifest_invalid", f"{field} contains a malformed entry")
        digest, raw_path = match.groups()
        if "\\" in raw_path or any(char in raw_path for char in "*?[]"):
            raise ProtocolError("manifest_invalid", f"{field} contains a non-portable path")
        relative = canonical_relative_path(raw_path)
        if (
            relative == "SHA256SUMS"
            or any(part.casefold() == ".git" for part in PurePosixPath(relative).parts)
            or is_local_runtime_path(relative)
            or relative in values
        ):
            raise ProtocolError("manifest_invalid", f"{field} contains a protected, runtime, or duplicate path")
        values[relative] = digest
        ordered.append(relative)
    if not ordered or ordered != sorted(ordered):
        raise ProtocolError("manifest_invalid", f"{field} is empty or not canonically sorted")
    names = set(values)
    for relative in ordered:
        parents = PurePosixPath(relative).parents
        if any(parent.as_posix() in names for parent in parents if parent.as_posix() != "."):
            raise ProtocolError("manifest_invalid", f"{field} contains a file and descendant path collision")
    return values


def _filemode_map(content: bytes, field: str) -> Dict[str, str]:
    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ProtocolError("filemodes_invalid", f"{field} is not valid UTF-8") from exc
    values: Dict[str, str] = {}
    ordered: List[str] = []
    for line in lines:
        match = FILEMODE_LINE_RE.fullmatch(line)
        if match is None:
            raise ProtocolError("filemodes_invalid", f"{field} contains a malformed entry")
        mode, raw_path = match.groups()
        if "\\" in raw_path or any(char in raw_path for char in "*?[]"):
            raise ProtocolError("filemodes_invalid", f"{field} contains a non-portable path")
        relative = canonical_relative_path(raw_path)
        if (
            any(part.casefold() == ".git" for part in PurePosixPath(relative).parts)
            or is_local_runtime_path(relative)
            or relative in values
        ):
            raise ProtocolError("filemodes_invalid", f"{field} contains a protected, runtime, or duplicate path")
        values[relative] = mode
        ordered.append(relative)
    if not ordered or ordered != sorted(ordered):
        raise ProtocolError("filemodes_invalid", f"{field} is empty or not canonically sorted")
    names = set(values)
    for relative in ordered:
        if any(
            parent.as_posix() in names
            for parent in PurePosixPath(relative).parents
            if parent.as_posix() != "."
        ):
            raise ProtocolError("filemodes_invalid", f"{field} contains a file and descendant path collision")
    return values


def _checksum_inventory(root: Path, envelope: Dict[str, Any]) -> Dict[str, Tuple[bytes, str]]:
    manifest = _read_source_bytes(root, "SHA256SUMS")
    if manifest is None:
        raise ProtocolError("manifest_missing", "SHA256SUMS is missing")
    current_digests = _manifest_digest_map(manifest[0], "SHA256SUMS")
    baseline_manifest = _git(
        root,
        "show",
        f"{envelope['base_sha']}:SHA256SUMS",
        failure_code="trusted_manifest_unavailable",
    )
    baseline_digests = _manifest_digest_map(baseline_manifest, "trusted baseline SHA256SUMS")
    allowed_sources: Dict[str, Optional[Tuple[bytes, str]]] = {}
    for relative in envelope["allowed_paths"]:
        if relative == "SHA256SUMS":
            continue
        if is_sensitive_path(relative):
            raise ProtocolError("credential_path_changed", "credential-shaped paths cannot be published")
        allowed_sources[relative] = _read_source_bytes(root, relative)
    expected_manifest_paths = set(baseline_digests)
    for relative, selected in allowed_sources.items():
        if selected is None:
            expected_manifest_paths.discard(relative)
        else:
            expected_manifest_paths.add(relative)
    if set(current_digests) != expected_manifest_paths:
        raise ProtocolError("manifest_inventory_mismatch", "SHA256SUMS differs from the trusted base plus sealed path changes")

    inventory: Dict[str, Tuple[bytes, str]] = {}
    for relative, digest in current_digests.items():
        if is_sensitive_path(relative):
            # Credential-shaped template fixtures are never opened by the
            # publisher. They must remain unchanged and retain the trusted
            # baseline manifest digest; changed paths cannot include them.
            if relative in envelope["allowed_paths"] or baseline_digests.get(relative) != digest:
                raise ProtocolError("credential_path_changed", "credential-shaped template data cannot change during publication")
            continue
        selected = _read_source_bytes(root, relative)
        if selected is None or hashlib.sha256(selected[0]).hexdigest() != digest:
            raise ProtocolError("manifest_mismatch", "a checksum-bound public source file is missing or changed")
        inventory[relative] = selected
    for required in ("FILEMODES", "scripts/check-public-release.py"):
        if required not in inventory:
            raise ProtocolError("manifest_invalid", "SHA256SUMS omits a required publication verifier")
    for relative, selected in allowed_sources.items():
        if selected is not None and relative not in inventory:
            raise ProtocolError("manifest_omission", "a changed public source file is omitted from SHA256SUMS")

    current_modes = _filemode_map(inventory["FILEMODES"][0], "FILEMODES")
    baseline_modes = _filemode_map(
        _git(
            root,
            "show",
            f"{envelope['base_sha']}:FILEMODES",
            failure_code="trusted_filemodes_unavailable",
        ),
        "trusted baseline FILEMODES",
    )
    if set(current_modes) != set(current_digests) | {"SHA256SUMS"}:
        raise ProtocolError("filemodes_inventory_mismatch", "FILEMODES does not exactly cover the public checksum inventory")
    for relative, declared_mode in current_modes.items():
        if is_sensitive_path(relative):
            if baseline_modes.get(relative) != declared_mode:
                raise ProtocolError("credential_path_changed", "credential-shaped template mode cannot change")
            continue
        selected = manifest if relative == "SHA256SUMS" else inventory.get(relative)
        if selected is None:
            raise ProtocolError("filemodes_inventory_mismatch", "FILEMODES names a missing public source file")
        expected_mode = "0755" if selected[1] == "100755" else "0644"
        if declared_mode != expected_mode:
            raise ProtocolError("filemode_mismatch", "a public source file mode differs from FILEMODES")
    return inventory


def _write_private_file(path: Path, content: bytes, mode: int = 0o600) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags, mode)
    except OSError as exc:
        raise ProtocolError("private_file_error", "private publication file could not be created safely") from exc
    try:
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    except OSError as exc:
        raise ProtocolError("private_file_error", "private publication file could not be written safely") from exc
    finally:
        os.close(descriptor)


def _run_checker_bytes(checker: bytes, *, cwd: Path, arguments: Sequence[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="exo-public-checker-") as temporary:
        checker_path = Path(temporary) / "check-public-release.py"
        _write_private_file(checker_path, checker)
        _run(
            [
                _trusted_tool("python"),
                "-I",
                str(checker_path),
                "--git-executable",
                _trusted_tool("git"),
                "--git-executable-sha256",
                _trusted_tool_digest("git"),
                *arguments,
            ],
            cwd=cwd,
            env=_safe_git_env(),
            failure_code="public_boundary_failed",
        )


def _verify_public_candidate(
    root: Path,
    envelope: Dict[str, Any],
) -> Tuple[str, Dict[str, Optional[Tuple[bytes, str]]]]:
    inventory = _checksum_inventory(root, envelope)
    manifest = _read_source_bytes(root, "SHA256SUMS")
    assert manifest is not None
    baseline_checker = _trusted_checker_bytes()
    with tempfile.TemporaryDirectory(prefix="exo-public-candidate-") as temporary:
        snapshot = Path(temporary) / "source"
        snapshot.mkdir(mode=0o700)
        for relative, (content, _mode) in inventory.items():
            _write_private_file(snapshot / relative, content)
        _write_private_file(snapshot / "SHA256SUMS", manifest[0])
        _run_checker_bytes(
            baseline_checker,
            cwd=snapshot,
            arguments=("--root", str(snapshot), "--source-tree"),
        )
        # Never execute candidate-owned code during publication. The candidate
        # checker is checksum-bound data inspected by the independently
        # accepted runtime checker, not an executable authority source.
    # Candidate-owned validation cannot race or rewrite the approved source.
    refreshed = _checksum_inventory(root, envelope)
    refreshed_manifest = _read_source_bytes(root, "SHA256SUMS")
    if {
        path: (hashlib.sha256(value[0]).hexdigest(), value[1]) for path, value in refreshed.items()
    } != {
        path: (hashlib.sha256(value[0]).hexdigest(), value[1]) for path, value in inventory.items()
    } or refreshed_manifest != manifest:
        raise ProtocolError("candidate_race", "public candidate changed during validation")
    approved_sources: Dict[str, Optional[Tuple[bytes, str]]] = {}
    for relative in envelope["allowed_paths"]:
        approved_sources[relative] = manifest if relative == "SHA256SUMS" else inventory.get(relative)
    return hashlib.sha256(baseline_checker).hexdigest(), approved_sources


def _verify_public_commit(root: Path, envelope: Dict[str, Any], commit_sha: str) -> None:
    baseline_checker = _trusted_checker_bytes()
    _assert_safe_git_storage(root)
    _run_checker_bytes(
        baseline_checker,
        cwd=root,
        arguments=(
            "--root",
            str(root),
            "--tree",
            commit_sha,
            "--baseline",
            envelope["base_sha"],
            "--candidate",
            commit_sha,
        ),
    )
    _assert_safe_git_storage(root)


def _tree_fingerprint(root: Path, revision: str, relative: str) -> Optional[Dict[str, str]]:
    raw = _git(root, "ls-tree", "-z", revision, "--", relative)
    entries = [entry for entry in raw.split(b"\0") if entry]
    if not entries:
        return None
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ProtocolError("tree_evidence_invalid", "candidate tree entry is ambiguous")
    metadata, path_bytes = entries[0].split(b"\t", 1)
    try:
        path = path_bytes.decode("utf-8")
        mode, object_type, object_id = metadata.decode("ascii").split()
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError("tree_evidence_invalid", "candidate tree entry is invalid") from exc
    if path != relative or object_type != "blob" or mode not in {"100644", "100755"}:
        raise ProtocolError("tree_evidence_invalid", "candidate tree entry is not an approved ordinary file")
    content = _git(root, "cat-file", "blob", object_id)
    return {"sha256": hashlib.sha256(content).hexdigest(), "mode": mode}


def _tree_change_evidence(root: Path, base_sha: str, candidate: str, paths: Sequence[str]) -> Dict[str, Any]:
    records = [
        {"path": path, "before": _tree_fingerprint(root, base_sha, path), "after": _tree_fingerprint(root, candidate, path)}
        for path in paths
    ]
    return {"changed_paths": list(paths), "path_set_digest": canonical_digest_lines(paths), "candidate_digest": json_digest(records)}


def _approved_snapshot_evidence(
    root: Path,
    envelope: Dict[str, Any],
    approved_sources: Dict[str, Optional[Tuple[bytes, str]]],
) -> Dict[str, Any]:
    records = []
    for relative in envelope["allowed_paths"]:
        if relative not in approved_sources:
            raise ProtocolError("approved_snapshot_incomplete", "approved publication snapshot omits a sealed path")
        selected = approved_sources[relative]
        after = None
        if selected is not None:
            content, mode = selected
            after = {"sha256": hashlib.sha256(content).hexdigest(), "mode": mode}
        records.append(
            {
                "path": relative,
                "before": _tree_fingerprint(root, envelope["base_sha"], relative),
                "after": after,
            }
        )
    return {
        "changed_paths": list(envelope["allowed_paths"]),
        "path_set_digest": canonical_digest_lines(envelope["allowed_paths"]),
        "candidate_digest": json_digest(records),
    }


def _verify_commit(root: Path, envelope: Dict[str, Any], commit_sha: str, message: bytes) -> str:
    parents = _decode(_git(root, "rev-list", "--parents", "-n", "1", commit_sha), "commit parents").split()
    if parents != [commit_sha, envelope["base_sha"]]:
        raise ProtocolError("commit_parent_mismatch", "publication commit must be one direct child of the approved base")
    paths = sorted(
        canonical_relative_path(value.decode("utf-8"))
        for value in _git(root, "diff", "--name-only", "--no-renames", "-z", envelope["base_sha"], commit_sha, "--").split(b"\0")
        if value
    )
    if paths != envelope["allowed_paths"]:
        raise ProtocolError("commit_path_mismatch", "publication commit changed paths differ from the exact seal")
    evidence = _tree_change_evidence(root, envelope["base_sha"], commit_sha, paths)
    if evidence != {
        "changed_paths": envelope["allowed_paths"],
        "path_set_digest": envelope["path_set_digest"],
        "candidate_digest": envelope["candidate_digest"],
    }:
        raise ProtocolError("commit_tree_mismatch", "publication commit tree differs from the sealed candidate")
    raw_commit = _git(root, "cat-file", "commit", commit_sha)
    separator = raw_commit.find(b"\n\n")
    if separator < 0 or raw_commit[separator + 2:] != message:
        raise ProtocolError("commit_message_mismatch", "publication commit message differs from the approved bytes")
    identity_raw = _git(
        root,
        "show",
        "-s",
        "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI",
        commit_sha,
    ).rstrip(b"\n")
    try:
        author_name, author_email, author_at, committer_name, committer_email, committer_at = (
            item.decode("utf-8") for item in identity_raw.split(b"\0")
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise ProtocolError("commit_identity_mismatch", "publication commit identity is malformed") from exc
    approved_at = parse_timestamp(envelope["approval"]["accepted_at"], "publication approval accepted_at")
    if (
        {"name": author_name, "email": author_email} != PUBLIC_IDENTITY
        or {"name": committer_name, "email": committer_email} != PUBLIC_IDENTITY
        or parse_timestamp(author_at, "commit author date") != approved_at
        or parse_timestamp(committer_at, "commit committer date") != approved_at
    ):
        raise ProtocolError("commit_identity_mismatch", "publication commit identity or timestamp differs from approval")
    _verify_public_commit(root, envelope, commit_sha)
    return _decode(_git(root, "show", "-s", "--format=%T", commit_sha), "commit tree")


def _real_index_path(root: Path) -> Path:
    raw = _decode(_git(root, "rev-parse", "--git-path", "index"), "Git index path")
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    parent = path.parent.resolve(strict=True)
    git_dir_raw = _decode(_git(root, "rev-parse", "--absolute-git-dir"), "Git directory")
    git_dir = Path(git_dir_raw).resolve(strict=True)
    if parent != git_dir or path.name != "index":
        raise ProtocolError("unsafe_index", "Git index path is outside the exact worktree Git directory")
    return parent / path.name


def _index_digest(index_path: Path) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(index_path, flags)
    except FileNotFoundError:
        return "absent"
    except OSError as exc:
        raise ProtocolError("unsafe_index", "Git index cannot be safely opened") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ProtocolError("unsafe_index", "Git index must be a single-link regular file")
        digest = hashlib.sha256()
        for chunk in iter(lambda: os.read(descriptor, 1024 * 1024), b""):
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(descriptor)


def _index_identity(index_path: Path) -> Dict[str, Any]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(index_path, flags)
    except OSError as exc:
        raise ProtocolError("unsafe_index", "Git index lock cannot be opened safely") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise ProtocolError("unsafe_index", "Git index lock must be a single-link regular file")
        digest = hashlib.sha256()
        for chunk in iter(lambda: os.read(descriptor, 1024 * 1024), b""):
            digest.update(chunk)
        return {
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "sha256": digest.hexdigest(),
        }
    finally:
        os.close(descriptor)


def _prepare_real_index_lock(
    index_path: Path,
    prepared_index: Path,
    expected_index_digest: str,
    expected_owner: Optional[Dict[str, Any]],
) -> Tuple[Path, Dict[str, Any]]:
    if expected_owner is not None and (
        not isinstance(expected_owner, dict)
        or set(expected_owner) != {"device", "inode", "sha256"}
        or not isinstance(expected_owner.get("device"), int)
        or not isinstance(expected_owner.get("inode"), int)
        or not isinstance(expected_owner.get("sha256"), str)
        or not SHA256_RE.fullmatch(expected_owner["sha256"])
    ):
        raise ProtocolError("index_lock_conflict", "publication Git index lock ownership evidence is invalid")
    if _index_digest(index_path) != expected_index_digest:
        raise ProtocolError("index_changed", "Git index changed before publication commit")
    content = read_safe_regular_bytes(prepared_index, "prepared publication index", max_bytes=64 * 1024 * 1024)
    lock_path = index_path.with_name(index_path.name + ".lock")
    if lock_path.exists() or lock_path.is_symlink():
        observed_owner = _index_identity(lock_path)
        if expected_owner is None or observed_owner != expected_owner:
            raise ProtocolError("index_lock_conflict", "an unrelated Git index lock is active")
        if observed_owner["sha256"] != hashlib.sha256(content).hexdigest():
            raise ProtocolError("index_lock_conflict", "publication Git index lock content changed")
        return lock_path, observed_owner
    if expected_owner is not None:
        raise ProtocolError("index_lock_missing", "owned publication Git index lock disappeared")
    _write_private_file(lock_path, content)
    if _index_digest(index_path) != expected_index_digest:
        raise ProtocolError("index_changed", "Git index changed while publication lock was acquired")
    return lock_path, _index_identity(lock_path)


def _finish_real_index_update(index_path: Path, lock_path: Path, expected_owner: Dict[str, Any]) -> None:
    if lock_path != index_path.with_name(index_path.name + ".lock"):
        raise ProtocolError("unsafe_index", "publication index lock path is invalid")
    if not lock_path.exists() or lock_path.is_symlink():
        raise ProtocolError("index_lock_missing", "prepared publication index lock is missing")
    if _index_identity(lock_path) != expected_owner:
        raise ProtocolError("index_lock_conflict", "publication Git index lock ownership changed")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory = os.open(index_path.parent, directory_flags)
    try:
        observed = os.stat(lock_path.name, dir_fd=directory, follow_symlinks=False)
        if observed.st_dev != expected_owner["device"] or observed.st_ino != expected_owner["inode"]:
            raise ProtocolError("index_lock_conflict", "publication Git index lock changed before replacement")
        os.replace(
            lock_path.name,
            index_path.name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
        )
        os.fsync(directory)
    finally:
        os.close(directory)


def _prepare_commit(
    root: Path,
    envelope: Dict[str, Any],
    approved_sources: Dict[str, Optional[Tuple[bytes, str]]],
    before_object_write: Callable[[], None],
) -> Tuple[Path, str, str, str]:
    if _approved_snapshot_evidence(root, envelope, approved_sources) != {
        "changed_paths": envelope["allowed_paths"],
        "path_set_digest": envelope["path_set_digest"],
        "candidate_digest": envelope["candidate_digest"],
    }:
        raise ProtocolError("approved_snapshot_mismatch", "scanner-approved bytes differ from the sealed candidate")
    index_path = _real_index_path(root)
    starting_index_digest = _index_digest(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".exo-publication-index-", dir=str(index_path.parent))
    os.close(descriptor)
    temp_index = Path(temporary)
    temp_index.unlink()
    try:
        _git(root, "read-tree", envelope["base_sha"], index=temp_index)
        before_object_write()
        for relative in envelope["allowed_paths"]:
            if relative not in approved_sources:
                raise ProtocolError("approved_snapshot_incomplete", "approved publication snapshot omits a sealed path")
            selected = approved_sources[relative]
            if selected is None:
                _git(root, "update-index", "--force-remove", "--", relative, index=temp_index)
                continue
            content, mode = selected
            object_id = _decode(
                _git(root, "hash-object", "-w", "--stdin", input_bytes=content, failure_code="object_write_failed"),
                "candidate blob",
            )
            if not GIT_SHA_RE.fullmatch(object_id):
                raise ProtocolError("object_write_failed", "Git returned an invalid candidate blob id")
            _git(root, "update-index", "--add", "--cacheinfo", f"{mode},{object_id},{relative}", index=temp_index)
        staged = sorted(
            canonical_relative_path(value.decode("utf-8"))
            for value in _git(root, "diff", "--cached", "--name-only", "--no-renames", "-z", envelope["base_sha"], "--", index=temp_index).split(b"\0")
            if value
        )
        if staged != envelope["allowed_paths"]:
            raise ProtocolError("staged_path_mismatch", "temporary index does not contain exactly the sealed paths")
        _git(root, "diff", "--cached", "--check", envelope["base_sha"], "--", index=temp_index, failure_code="staged_diff_invalid")
        tree_sha = _decode(_git(root, "write-tree", index=temp_index), "candidate tree")
        evidence = _tree_change_evidence(root, envelope["base_sha"], tree_sha, staged)
        if evidence != {
            "changed_paths": envelope["allowed_paths"],
            "path_set_digest": envelope["path_set_digest"],
            "candidate_digest": envelope["candidate_digest"],
        }:
            raise ProtocolError("temporary_tree_mismatch", "temporary index tree differs from the sealed candidate")
        # Candidate-owned hooks and test runners are deliberately not executed
        # here. Publication relies on prior sealed test evidence plus the
        # trusted external checker that is rerun immediately before object
        # writes. The candidate never executes its own checker.
        baseline_checker = _trusted_checker_bytes()
        return (
            temp_index,
            tree_sha,
            hashlib.sha256(baseline_checker).hexdigest(),
            starting_index_digest,
        )
    except BaseException:
        if temp_index.exists():
            temp_index.unlink()
        raise


def _materialize_prepared_commit(
    root: Path,
    envelope: Dict[str, Any],
    message: bytes,
    head: str,
    temp_index: Path,
    tree_sha: str,
    prepared_check_digest: str,
    trusted_check_digest: str,
    starting_index_digest: str,
    transaction_path: Path,
    transaction: Dict[str, Any],
    capability_digest: str,
    prior_index_owner: Optional[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any], Path, Optional[Path], Optional[Dict[str, Any]]]:
    """Create deterministic local objects and an owned index lock with cleanup."""

    try:
        if prepared_check_digest != trusted_check_digest:
            raise ProtocolError("trusted_checker_changed", "trusted publication checker changed during commit preparation")
        identity = envelope["commit"]["identity"]
        commit_sha = _decode(
            _run(
                [
                    _trusted_tool("git"),
                    "-c", "commit.gpgSign=false",
                    "-c", f"core.hooksPath={os.devnull}",
                    "-c", "http.followRedirects=false",
                    "commit-tree", tree_sha, "-p", envelope["base_sha"],
                ],
                cwd=root,
                env=_safe_git_env(identity=identity, timestamp=envelope["approval"]["accepted_at"]),
                input_bytes=message,
                failure_code="commit_object_failed",
            ),
            "publication commit",
        )
        if not GIT_SHA_RE.fullmatch(commit_sha):
            raise ProtocolError("commit_object_failed", "Git returned an invalid publication commit id")
        _verify_commit(root, envelope, commit_sha, message)
        if transaction.get("commit_sha") not in {None, commit_sha}:
            raise ProtocolError("commit_recovery_conflict", "recreated commit differs from the transaction")
        prepared_index_digest = _index_digest(temp_index)
        for field, value in (
            ("tree_sha", tree_sha),
            ("trusted_check_digest", trusted_check_digest),
            ("prepared_index_digest", prepared_index_digest),
        ):
            if transaction.get(field) not in {None, value}:
                raise ProtocolError("commit_recovery_conflict", "commit preparation evidence changed during recovery")
        recorded_starting_index_digest = transaction.get("starting_index_digest", starting_index_digest)
        if starting_index_digest not in {recorded_starting_index_digest, prepared_index_digest}:
            raise ProtocolError("commit_recovery_conflict", "real index is outside the recognized publication states")
        transaction = _tx_status(
            transaction_path,
            transaction,
            "commit_prepared",
            capability_digest=capability_digest,
            commit_sha=commit_sha,
            tree_sha=tree_sha,
            trusted_check_digest=trusted_check_digest,
            starting_index_digest=recorded_starting_index_digest,
            prepared_index_digest=prepared_index_digest,
        )
        if head == envelope["base_sha"]:
            _verify_source_candidate(root, envelope)
        index_path = _real_index_path(root)
        current_index_digest = _index_digest(index_path)
        lock_owner: Optional[Dict[str, Any]] = None
        if current_index_digest == prepared_index_digest:
            possible_lock = index_path.with_name(index_path.name + ".lock")
            if possible_lock.exists() or possible_lock.is_symlink():
                raise ProtocolError("index_lock_conflict", "an unrelated Git index lock is active")
            lock_path: Optional[Path] = None
        else:
            if current_index_digest != recorded_starting_index_digest:
                raise ProtocolError("index_changed", "real Git index differs from both recognized recovery states")
            lock_path, lock_owner = _prepare_real_index_lock(
                index_path,
                temp_index,
                recorded_starting_index_digest,
                prior_index_owner,
            )
            transaction = _tx_status(
                transaction_path,
                transaction,
                "index_locked",
                index_lock_identity=lock_owner,
            )
        return commit_sha, transaction, index_path, lock_path, lock_owner
    finally:
        if temp_index.exists():
            temp_index.unlink()


def commit_publication(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    request_id = require_id(args.request_id, "request_id")
    publication_rel = canonical_relative_path(args.publication)
    with exclusive_lock(_lock_path(root, Path(publication_rel).stem)):
        record_path, record, envelope, replay, recovering = _load_operation(
            root, publication_rel, "commit_publication", request_id
        )
        _assert_actor(args, envelope)
        message = _commit_message(envelope)
        if replay is not None:
            if record["commit"] is None:
                raise ProtocolError("replay_state_mismatch", "commit replay lacks committed evidence")
            _verify_commit(root, envelope, record["commit"]["commit_sha"], message)
            transaction_path = _tx_path(root, record["id"], "commit_publication", request_id)
            if not transaction_path.exists():
                raise ProtocolError("transaction_missing", "commit replay lacks its transaction journal")
            transaction = _validate_operation_transaction(load_safe_json(transaction_path, "publication commit transaction"))
            if transaction.get("status") != "finalized":
                _tx_status(
                    transaction_path,
                    transaction,
                    "finalized",
                    result_id=replay["result_id"],
                    commit_sha=record["commit"]["commit_sha"],
                )
            return {"ok": True, "replay": True, "state": record["state"], "revision": record["revision"], "commit_sha": record["commit"]["commit_sha"]}
        if record["state"] != "authorized" or record["commit"] is not None:
            raise ProtocolError("wrong_publication_state", "publication commit requires authorized state")
        message_digest = hashlib.sha256(message).hexdigest()
        intent = {
            "operation": "commit_publication", "record_digest": json_digest(record), "base_sha": envelope["base_sha"],
            "candidate_digest": envelope["candidate_digest"], "path_set_digest": envelope["path_set_digest"],
            "message_digest": message_digest, "identity": PUBLIC_IDENTITY,
        }
        transaction_path, transaction, transaction_created = _begin_transaction(
            root, record, request_id, "commit_publication", intent
        )
        prior_transaction_status = transaction["status"]
        prior_index_owner = (
            transaction.get("index_lock_identity")
            if prior_transaction_status in {"index_locked", "ref_updated"}
            else None
        )
        capability_path, capability_digest = _consume_operation(
            root, record, envelope, operation="commit_publication", request_id=request_id,
            target_sha=envelope["base_sha"], payload_digest=json_digest(intent), method="git_temporary_index_commit",
        )
        if transaction.get("capability_digest") not in {None, capability_digest}:
            raise ProtocolError("transaction_conflict", "commit transaction capability changed")
        if transaction["status"] == "intent":
            transaction = _tx_status(transaction_path, transaction, "capability_consumed", capability_digest=capability_digest)
        _fault("after_commit_capability")
        branch, head = _branch_and_head(root)
        if branch != envelope["branch"]:
            raise ProtocolError("worktree_identity_mismatch", "publication branch changed")
        if head == envelope["base_sha"]:
            _recheck_consumed_operation(root, record, envelope, "commit_publication", request_id, intent)
            _verify_source_candidate(root, envelope)
        elif transaction.get("commit_sha") != head:
            raise ProtocolError("commit_recovery_conflict", "branch moved outside the exact publication transaction")
        else:
            _verify_commit(root, envelope, head, message)
            if _git(root, "diff", "--name-only", "--no-renames", head, "--"):
                raise ProtocolError("commit_recovery_conflict", "working files differ from the exact publication commit")
            if _git(root, "ls-files", "--others", "--exclude-standard", "-z"):
                raise ProtocolError("commit_recovery_conflict", "unexpected untracked files block publication recovery")
            _verify_public_candidate(root, envelope)

        trusted_check_digest, approved_sources = _verify_public_candidate(root, envelope)
        temp_index, tree_sha, prepared_check_digest, starting_index_digest = _prepare_commit(
            root,
            envelope,
            approved_sources,
            (
                lambda: _recheck_consumed_operation(
                    root,
                    record,
                    envelope,
                    "commit_publication",
                    request_id,
                    intent,
                )
                if head == envelope["base_sha"]
                else lambda: None
            ),
        )
        commit_sha, transaction, index_path, lock_path, lock_owner = _materialize_prepared_commit(
            root,
            envelope,
            message,
            head,
            temp_index,
            tree_sha,
            prepared_check_digest,
            trusted_check_digest,
            starting_index_digest,
            transaction_path,
            transaction,
            capability_digest,
            prior_index_owner,
        )
        ref = f"refs/heads/{envelope['branch']}"
        if head == envelope["base_sha"]:
            _recheck_consumed_operation(root, record, envelope, "commit_publication", request_id, intent)
            _git(root, "update-ref", ref, commit_sha, envelope["base_sha"], failure_code="branch_advance_failed")
            transaction = _tx_status(transaction_path, transaction, "ref_updated", commit_sha=commit_sha)
        else:
            current_branch, current_head = _branch_and_head(root)
            if current_branch != envelope["branch"] or current_head != commit_sha:
                raise ProtocolError("commit_recovery_conflict", "publication branch changed during recovery")
        _fault("after_commit_ref")
        if lock_path is not None:
            assert lock_owner is not None
            _finish_real_index_update(index_path, lock_path, lock_owner)
        transaction = _tx_status(transaction_path, transaction, "index_replaced", commit_sha=commit_sha)
        branch, head = _branch_and_head(root)
        if branch != envelope["branch"] or head != commit_sha or _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ProtocolError("commit_checkout_mismatch", "publication commit did not leave the exact clean candidate checkout")
        committed_at = isoformat(utc_now())
        result_id = stable_id("publication-commit", record["id"], request_id, commit_sha)
        record["commit"] = {
            "request_id": request_id, "recorded_at": committed_at, "capability_path": capability_path,
            "capability_digest": capability_digest, "intent_digest": json_digest(intent), "base_sha": envelope["base_sha"],
            "candidate_digest": envelope["candidate_digest"], "path_set_digest": envelope["path_set_digest"],
            "tree_sha": tree_sha, "commit_sha": commit_sha, "message_digest": message_digest,
            "identity_policy_status": "pass", "trusted_public_check_digest": trusted_check_digest,
        }
        record["state"] = "committed"
        record["revision"] += 1
        _append_idempotency(record, request_id, "commit_publication", result_id)
        atomic_write_json(record_path, _validate_record(record))
        _tx_status(transaction_path, transaction, "finalized", result_id=result_id, commit_sha=commit_sha)
    return {"ok": True, "replay": False, "state": "committed", "revision": record["revision"], "commit_sha": commit_sha}


def _remote_destination(envelope: Dict[str, Any]) -> str:
    remote = envelope["remote"]
    return f"github.com/{remote['repository']}@{remote['repository_id']}/refs/heads/{remote['head_branch']}"


def _pull_request_destination(envelope: Dict[str, Any], number: Optional[int] = None) -> str:
    remote = envelope["remote"]
    suffix = "/pull" if number is None else f"/pull/{number}"
    return f"github.com/{remote['repository']}@{remote['repository_id']}{suffix}"


def _canonical_remote_url(envelope: Dict[str, Any]) -> str:
    return f"https://github.com/{envelope['remote']['repository']}.git"


def _require_remote_url(root: Path, envelope: Dict[str, Any]) -> str:
    # Repository-local Git config is deliberately ignored for publication.
    # All remote reads and writes use this envelope-derived canonical URL.
    return _canonical_remote_url(envelope)


def _repository_tls_context() -> ssl.SSLContext:
    """Build TLS trust from compiled system paths, not ambient CA variables."""

    defaults = ssl.get_default_verify_paths()
    cafile = defaults.openssl_cafile
    capath = defaults.openssl_capath
    selected_cafile = cafile if cafile and Path(cafile).is_file() else None
    selected_capath = capath if capath and Path(capath).is_dir() else None
    if selected_cafile is None and selected_capath is None:
        raise ProtocolError("repository_identity_indeterminate", "system TLS trust is unavailable")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    try:
        context.load_verify_locations(cafile=selected_cafile, capath=selected_capath)
    except (OSError, ssl.SSLError) as exc:
        raise ProtocolError("repository_identity_indeterminate", "system TLS trust could not be loaded") from exc
    return context


def _read_repository_identity(repository: str) -> Dict[str, str]:
    """Read one public GitHub REST identity without following redirects."""

    connection = http.client.HTTPSConnection(
        GITHUB_API_HOST,
        timeout=15,
        context=_repository_tls_context(),
    )
    try:
        connection.request(
            "GET",
            f"/repos/{repository}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "EnkratFlow-publication-guard",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response = connection.getresponse()
        if 300 <= response.status < 400 or response.getheader("Location") is not None:
            raise ProtocolError(
                "repository_identity_redirect",
                "GitHub repository identity redirected; a new reviewed envelope is required",
            )
        if response.status != 200:
            raise ProtocolError(
                "repository_identity_indeterminate",
                "GitHub repository identity could not be read without redirecting",
            )
        raw = response.read(MAX_REPOSITORY_IDENTITY_BYTES + 1)
        if len(raw) > MAX_REPOSITORY_IDENTITY_BYTES:
            raise ProtocolError(
                "repository_identity_indeterminate",
                "GitHub repository identity response exceeded its bound",
            )
    except ProtocolError:
        raise
    except (OSError, http.client.HTTPException) as exc:
        raise ProtocolError(
            "repository_identity_indeterminate",
            "GitHub repository identity request failed",
        ) from exc
    finally:
        connection.close()
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("repository_identity_indeterminate", "GitHub repository identity is malformed") from exc
    repository_id = payload.get("id") if isinstance(payload, dict) else None
    name = payload.get("full_name") if isinstance(payload, dict) else None
    if type(repository_id) is not int or repository_id <= 0 or not isinstance(name, str):
        raise ProtocolError("repository_identity_indeterminate", "GitHub repository identity has the wrong shape")
    return {"repository_id": str(repository_id), "nameWithOwner": name}


def _verify_repository_identity(root: Path, envelope: Dict[str, Any]) -> None:
    del root
    remote = envelope["remote"]
    observed = _read_repository_identity(remote["repository"])
    if (
        observed.get("repository_id") != remote["repository_id"]
        or observed.get("nameWithOwner") != remote["repository"]
    ):
        raise ProtocolError("repository_identity_mismatch", "GitHub repository identity differs from the approval")


def _observe_remote(root: Path, envelope: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    _verify_repository_identity(root, envelope)
    remote = envelope["remote"]
    output = _git(
        root, "ls-remote", "--refs", _canonical_remote_url(envelope),
        f"refs/heads/{remote['base_branch']}", f"refs/heads/{remote['head_branch']}",
        failure_code="remote_state_indeterminate",
    )
    values: Dict[str, str] = {}
    for line in output.splitlines():
        parts = line.split(b"\t")
        if len(parts) != 2:
            raise ProtocolError("remote_state_indeterminate", "remote branch observation is malformed")
        sha = parts[0].decode("ascii", errors="ignore")
        ref = parts[1].decode("utf-8", errors="ignore")
        if not GIT_SHA_RE.fullmatch(sha) or ref in values:
            raise ProtocolError("remote_state_indeterminate", "remote branch observation is ambiguous")
        values[ref] = sha
    return values.get(f"refs/heads/{remote['base_branch']}"), values.get(f"refs/heads/{remote['head_branch']}")


def _mark_unknown(record_path: Path, record: Dict[str, Any], request_id: str, operation: str,
                  last_state: str, intent_digest: str, reason_code: str) -> None:
    record["state"] = "effect_unknown"
    record["unknown_effect"] = {
        "request_id": request_id, "recorded_at": isoformat(utc_now()), "operation": operation,
        "last_confirmed_state": last_state, "intent_digest": intent_digest, "reason_code": reason_code,
    }
    record["revision"] += 1
    atomic_write_json(record_path, _validate_record(record))


def _unknown_capability_evidence(
    root: Path,
    record: Dict[str, Any],
    operation: str,
    request_id: str,
) -> Tuple[str, str]:
    unknown = record.get("unknown_effect")
    if (
        record.get("state") != "effect_unknown"
        or not isinstance(unknown, dict)
        or unknown.get("operation") != operation
        or unknown.get("request_id") != request_id
    ):
        raise ProtocolError("unknown_effect_conflict", "only the exact unknown-effect request may reconcile its observation")
    path = _capability_path(root, record["id"], operation, request_id)
    capability = validate_capability(load_safe_json(path, "unknown-effect capability"))
    if (
        capability["status"].get("state") != "consumed"
        or capability["status"].get("consumed_by_request_id") != request_id
        or capability["scope"].get("payload_digest") != unknown["intent_digest"]
    ):
        raise ProtocolError("publication_provenance_mismatch", "unknown effect lacks its exact consumed capability")
    transaction_path = _tx_path(root, record["id"], operation, request_id)
    transaction = _validate_operation_transaction(load_safe_json(transaction_path, "unknown-effect transaction"))
    if transaction.get("status") != "effect_unknown":
        transaction = _tx_status(
            transaction_path,
            transaction,
            "effect_unknown",
            reason_code=unknown["reason_code"],
        )
    elif transaction.get("reason_code") != unknown["reason_code"]:
        raise ProtocolError("publication_provenance_mismatch", "unknown-effect reason differs from its transaction")
    return path.relative_to(root).as_posix(), json_digest(capability)


def _reconcile_unknown_push(
    root: Path,
    record_path: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    request_id: str,
) -> Dict[str, Any]:
    capability_path, capability_digest = _unknown_capability_evidence(
        root, record, "push_publication", request_id
    )
    commit_sha = record["commit"]["commit_sha"]
    base_remote, head_remote = _observe_remote(root, envelope)
    if base_remote != envelope["base_sha"]:
        raise ProtocolError("base_moved", "remote base moved while the push outcome was unknown")
    if head_remote is None:
        raise ProtocolError(
            "effect_absent",
            "the publication branch is absent; this read-only reconciliation will not retry the push",
        )
    if head_remote != commit_sha:
        raise ProtocolError("remote_head_collision", "publication branch exists at a different commit")
    unknown = record["unknown_effect"]
    remote = envelope["remote"]
    result_id = stable_id("publication-push", record["id"], request_id, commit_sha)
    record["push"] = {
        "request_id": request_id,
        "recorded_at": isoformat(utc_now()),
        "intent_digest": unknown["intent_digest"],
        "capability_path": capability_path,
        "capability_digest": capability_digest,
        "repository": remote["repository"],
        "repository_id": remote["repository_id"],
        "remote_name": remote["remote_name"],
        "base_branch": remote["base_branch"],
        "base_sha": base_remote,
        "head_branch": remote["head_branch"],
        "commit_sha": commit_sha,
        "observed_remote_sha": head_remote,
        "observation_digest": json_digest(
            {"repository": remote["repository"], "repository_id": remote["repository_id"], "base": base_remote, "head": head_remote}
        ),
    }
    record["state"] = "pushed"
    record["unknown_effect"] = None
    # _mark_unknown already occupied this milestone revision. Reconciliation
    # fills the exact evidence slot without creating a second outward effect.
    _append_idempotency(record, request_id, "push_publication", result_id)
    atomic_write_json(record_path, _validate_record(record))
    transaction_path = _tx_path(root, record["id"], "push_publication", request_id)
    transaction = _validate_operation_transaction(load_safe_json(transaction_path, "unknown push transaction"))
    _tx_status(
        transaction_path,
        transaction,
        "finalized",
        result_id=result_id,
        remote_head_sha=head_remote,
        reconciled_observation=True,
    )
    return {
        "ok": True,
        "replay": False,
        "reconciled": True,
        "state": "pushed",
        "revision": record["revision"],
        "remote_head_sha": head_remote,
    }


def push_publication(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    request_id = require_id(args.request_id, "request_id")
    publication_rel = canonical_relative_path(args.publication)
    with exclusive_lock(_lock_path(root, Path(publication_rel).stem)):
        record_path, record, envelope, replay, recovering = _load_operation(
            root, publication_rel, "push_publication", request_id
        )
        _assert_actor(args, envelope)
        if record["state"] == "effect_unknown":
            return _reconcile_unknown_push(root, record_path, record, envelope, request_id)
        if replay is not None:
            if record["push"] is None:
                raise ProtocolError("replay_state_mismatch", "push replay lacks exact recorded evidence")
            transaction_path = _tx_path(root, record["id"], "push_publication", request_id)
            transaction = _validate_operation_transaction(load_safe_json(transaction_path, "publication push transaction"))
            if transaction.get("status") != "finalized":
                _tx_status(
                    transaction_path,
                    transaction,
                    "finalized",
                    result_id=replay["result_id"],
                    remote_head_sha=record["push"]["observed_remote_sha"],
                )
            return {
                "ok": True,
                "replay": True,
                "state": record["state"],
                "revision": record["revision"],
                "remote_head_sha": record["push"]["observed_remote_sha"],
            }
        if record["state"] != "committed" or record["commit"] is None:
            raise ProtocolError("wrong_publication_state", "push requires one verified local publication commit")
        branch, head = _branch_and_head(root)
        commit_sha = record["commit"]["commit_sha"]
        if branch != envelope["branch"] or head != commit_sha or _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
            raise ProtocolError("commit_checkout_mismatch", "local publication commit is not the exact clean checkout")
        _verify_commit(root, envelope, commit_sha, _commit_message(envelope))
        remote_url = _require_remote_url(root, envelope)
        intent = {
            "operation": "push_publication", "record_digest": json_digest(record), "commit_sha": commit_sha,
            "destination": _remote_destination(envelope), "method": "git_create_only_branch_push",
        }
        transaction_path, transaction, transaction_created = _begin_transaction(
            root, record, request_id, "push_publication", intent
        )
        capability_path, capability_digest = _consume_operation(
            root, record, envelope, operation="push_publication", request_id=request_id, target_sha=commit_sha,
            payload_digest=json_digest(intent), destination_id=_remote_destination(envelope), method="git_create_only_branch_push",
        )
        if transaction.get("capability_digest") not in {None, capability_digest}:
            raise ProtocolError("transaction_conflict", "push transaction capability changed")
        if transaction["status"] == "intent":
            transaction = _tx_status(transaction_path, transaction, "capability_consumed", capability_digest=capability_digest)
        if transaction.get("status") == "blocked_collision":
            raise ProtocolError("remote_head_collision", "named publication branch already existed before this request")
        base_remote, head_remote = _observe_remote(root, envelope)
        if base_remote != envelope["base_sha"]:
            raise ProtocolError("base_moved", "remote base branch moved after publication approval")
        if head_remote is not None:
            if not transaction_created and head_remote == commit_sha:
                base_after, head_after = base_remote, head_remote
            else:
                transaction = _tx_status(transaction_path, transaction, "blocked_collision", reason_code="remote_head_collision")
                raise ProtocolError("remote_head_collision", "named publication branch already exists")
        else:
            base_after = head_after = None
        remote = envelope["remote"]
        refspec = f"{commit_sha}:refs/heads/{remote['head_branch']}"
        if head_remote is None:
            _recheck_consumed_operation(root, record, envelope, "push_publication", request_id, intent)
            _verify_repository_identity(root, envelope)
            try:
                with tempfile.TemporaryDirectory(prefix="exo-publication-hooks-") as hooks:
                    _run(
                        [
                            _trusted_tool("git"),
                            "-c", "push.default=nothing",
                            "-c", "push.followTags=false",
                            "-c", "http.followRedirects=false",
                            "-c", "credential.helper=",
                            "-c", f"credential.helper=!{shlex.quote(_trusted_tool('gh'))} auth git-credential",
                            "-c", f"core.hooksPath={hooks}",
                            "push",
                            "--porcelain",
                            "--atomic",
                            f"--force-with-lease=refs/heads/{remote['head_branch']}:",
                            "--no-all",
                            "--no-mirror",
                            "--no-tags",
                            "--no-follow-tags",
                            "--no-delete",
                            "--no-prune",
                            "--no-set-upstream",
                            "--no-signed",
                            "--no-push-option",
                            "--no-verify",
                            "--recurse-submodules=no",
                            remote_url,
                            refspec,
                        ],
                        cwd=root,
                        env=_transport_env(),
                        failure_code="push_failed",
                    )
            except ProtocolError:
                try:
                    base_after, head_after = _observe_remote(root, envelope)
                except ProtocolError:
                    _mark_unknown(record_path, record, request_id, "push_publication", "committed", json_digest(intent), "remote_state_indeterminate")
                    _tx_status(transaction_path, transaction, "effect_unknown", reason_code="remote_state_indeterminate")
                    raise ProtocolError("effect_unknown", "push outcome is unknown; no automatic retry is permitted")
                if base_after != envelope["base_sha"] or head_after != commit_sha:
                    _mark_unknown(record_path, record, request_id, "push_publication", "committed", json_digest(intent), "push_unconfirmed")
                    _tx_status(transaction_path, transaction, "effect_unknown", reason_code="push_unconfirmed")
                    raise ProtocolError("effect_unknown", "push outcome is not exactly confirmed; no automatic retry is permitted")
            try:
                base_after, head_after = _observe_remote(root, envelope)
            except ProtocolError:
                _mark_unknown(record_path, record, request_id, "push_publication", "committed", json_digest(intent), "push_postcheck_indeterminate")
                _tx_status(transaction_path, transaction, "effect_unknown", reason_code="push_postcheck_indeterminate")
                raise ProtocolError("effect_unknown", "push postcondition is unknown; no automatic retry is permitted")
        if base_after != envelope["base_sha"] or head_after != commit_sha:
            _mark_unknown(record_path, record, request_id, "push_publication", "committed", json_digest(intent), "push_postcheck_failed")
            _tx_status(transaction_path, transaction, "effect_unknown", reason_code="push_postcheck_failed")
            raise ProtocolError("effect_unknown", "push postcondition is unknown or mismatched")
        result_id = stable_id("publication-push", record["id"], request_id, commit_sha)
        record["push"] = {
            "request_id": request_id, "recorded_at": isoformat(utc_now()), "intent_digest": json_digest(intent),
            "capability_path": capability_path, "capability_digest": capability_digest,
            "repository": remote["repository"], "repository_id": remote["repository_id"],
            "remote_name": remote["remote_name"], "base_branch": remote["base_branch"],
            "base_sha": base_after, "head_branch": remote["head_branch"], "commit_sha": commit_sha,
            "observed_remote_sha": head_after,
            "observation_digest": json_digest(
                {"repository": remote["repository"], "repository_id": remote["repository_id"], "base": base_after, "head": head_after}
            ),
        }
        record["state"] = "pushed"
        record["revision"] += 1
        _append_idempotency(record, request_id, "push_publication", result_id)
        atomic_write_json(record_path, _validate_record(record))
        _tx_status(transaction_path, transaction, "finalized", result_id=result_id, remote_head_sha=head_after)
    return {"ok": True, "replay": False, "state": "pushed", "revision": record["revision"], "remote_head_sha": head_after}


def _gh(root: Path, *args: str, input_bytes: Optional[bytes] = None, failure_code: str = "github_state_indeterminate") -> bytes:
    return _run([_trusted_tool("gh"), *args], cwd=root, env=_transport_env(), input_bytes=input_bytes, failure_code=failure_code)


def _query_prs(root: Path, envelope: Dict[str, Any]) -> List[Dict[str, Any]]:
    _verify_repository_identity(root, envelope)
    remote = envelope["remote"]
    raw = _gh(
        root, "pr", "list", "--repo", f"github.com/{remote['repository']}", "--state", "all", "--head", remote["head_branch"],
        "--base", remote["base_branch"], "--limit", "100", "--json",
        "number,url,state,isDraft,maintainerCanModify,headRefName,headRefOid,baseRefName,title,body,"
        "headRepository,headRepositoryOwner,isCrossRepository",
    )
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("github_state_indeterminate", "GitHub returned malformed PR metadata") from exc
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ProtocolError("github_state_indeterminate", "GitHub PR metadata has the wrong shape")
    return value


def _verified_pr(envelope: Dict[str, Any], commit_sha: str, body: bytes, values: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if len(values) != 1:
        raise ProtocolError("pr_state_mismatch", "exactly one draft PR must exist for the publication branch")
    item = values[0]
    required = {
        "number", "url", "state", "isDraft", "maintainerCanModify", "headRefName", "headRefOid",
        "baseRefName", "title", "body", "headRepository", "headRepositoryOwner", "isCrossRepository",
    }
    if set(item) != required:
        raise ProtocolError("pr_state_mismatch", "PR observation fields are incomplete or unexpected")
    remote = envelope["remote"]
    expected_url_prefix = f"https://github.com/{remote['repository']}/pull/"
    expected_url = f"{expected_url_prefix}{item['number']}" if isinstance(item.get("number"), int) else ""
    expected_body = body.decode("utf-8")
    observed_body = item.get("body")
    body_matches = isinstance(observed_body, str) and observed_body in {expected_body, expected_body[:-1]}
    owner = item.get("headRepositoryOwner")
    repository = item.get("headRepository")
    owner_login = owner.get("login") if isinstance(owner, dict) else None
    repository_name = repository.get("nameWithOwner") if isinstance(repository, dict) else None
    expected_owner = remote["repository"].split("/", 1)[0]
    if (
        not isinstance(item["number"], int)
        or not isinstance(item["url"], str)
        or item["url"] != expected_url
        or item["state"] != "OPEN"
        or item["isDraft"] is not True
        or item["maintainerCanModify"] is not False
        or item["isCrossRepository"] is not False
        or owner_login != expected_owner
        or repository_name != remote["repository"]
        or item["headRefName"] != remote["head_branch"]
        or item["headRefOid"] != commit_sha
        or item["baseRefName"] != remote["base_branch"]
        or item["title"] != envelope["pull_request"]["title"]
        or not body_matches
    ):
        raise ProtocolError("pr_state_mismatch", "draft PR does not match the exact publication envelope")
    return item


def _verified_required_checks(root: Path, envelope: Dict[str, Any], pr_number: int) -> str:
    _verify_repository_identity(root, envelope)
    remote = envelope["remote"]
    raw = _gh(
        root,
        "pr",
        "checks",
        str(pr_number),
        "--repo",
        f"github.com/{remote['repository']}",
        "--required",
        "--json",
        "name,bucket,state,workflow",
        failure_code="required_checks_indeterminate",
    )
    try:
        checks = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("required_checks_indeterminate", "GitHub returned malformed required-check metadata") from exc
    if not isinstance(checks, list) or not checks:
        raise ProtocolError("required_checks_missing", "the required publication checks were not observed")
    expected = set(remote["required_checks"])
    observed: List[str] = []
    for item in checks:
        if not isinstance(item, dict) or set(item) != {"name", "bucket", "state", "workflow"}:
            raise ProtocolError("required_checks_indeterminate", "required-check metadata has the wrong shape")
        name = item.get("name")
        if not isinstance(name, str) or not name or item.get("bucket") != "pass":
            raise ProtocolError("required_checks_not_passed", "one or more required publication checks have not passed")
        observed.append(name)
    if len(observed) != len(set(observed)) or set(observed) != expected:
        raise ProtocolError("required_checks_mismatch", "observed required checks differ from the publication envelope")
    canonical_checks = sorted(
        checks,
        key=lambda item: (item["name"], item["workflow"], item["state"], item["bucket"]),
    )
    return json_digest(canonical_checks)


def _reconcile_unknown_pr(
    root: Path,
    record_path: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    request_id: str,
) -> Dict[str, Any]:
    capability_path, capability_digest = _unknown_capability_evidence(
        root, record, "create_draft_pr", request_id
    )
    commit_sha = record["commit"]["commit_sha"]
    body = _pr_body(envelope, request_id, commit_sha)
    values = _query_prs(root, envelope)
    if not values:
        raise ProtocolError(
            "effect_absent",
            "the draft PR is absent; this read-only reconciliation will not retry creation",
        )
    try:
        item = _verified_pr(envelope, commit_sha, body, values)
    except ProtocolError as exc:
        raise ProtocolError("pr_collision", "observed pull request does not match the unknown publication effect") from exc
    unknown = record["unknown_effect"]
    remote = envelope["remote"]
    result_id = stable_id("publication-pr", record["id"], request_id, str(item["number"]), commit_sha)
    title = envelope["pull_request"]["title"]
    record["draft_pull_request"] = {
        "request_id": request_id,
        "recorded_at": isoformat(utc_now()),
        "intent_digest": unknown["intent_digest"],
        "capability_path": capability_path,
        "capability_digest": capability_digest,
        "repository": remote["repository"],
        "repository_id": remote["repository_id"],
        "number": item["number"],
        "url": item["url"],
        "base_branch": remote["base_branch"],
        "head_branch": remote["head_branch"],
        "head_sha": commit_sha,
        "is_draft": True,
        "title_digest": hashlib.sha256(title.encode("utf-8")).hexdigest(),
        "body_digest": hashlib.sha256(body).hexdigest(),
        "observation_digest": json_digest(
            {
                "repository_id": remote["repository_id"],
                "pull_request": {key: item[key] for key in sorted(item) if key not in {"title", "body"}},
            }
        ),
    }
    record["state"] = "draft_pr_verified"
    record["unknown_effect"] = None
    _append_idempotency(record, request_id, "create_draft_pr", result_id)
    atomic_write_json(record_path, _validate_record(record))
    transaction_path = _tx_path(root, record["id"], "create_draft_pr", request_id)
    transaction = _validate_operation_transaction(load_safe_json(transaction_path, "unknown draft-PR transaction"))
    _tx_status(
        transaction_path,
        transaction,
        "finalized",
        result_id=result_id,
        pr_number=item["number"],
        pr_url=item["url"],
        reconciled_observation=True,
    )
    return {
        "ok": True,
        "replay": False,
        "reconciled": True,
        "state": "draft_pr_verified",
        "revision": record["revision"],
        "pr_number": item["number"],
        "pr_url": item["url"],
    }


def create_draft_pr(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    request_id = require_id(args.request_id, "request_id")
    publication_rel = canonical_relative_path(args.publication)
    with exclusive_lock(_lock_path(root, Path(publication_rel).stem)):
        record_path, record, envelope, replay, recovering = _load_operation(
            root, publication_rel, "create_draft_pr", request_id
        )
        _assert_actor(args, envelope)
        if record["state"] == "effect_unknown":
            return _reconcile_unknown_pr(root, record_path, record, envelope, request_id)
        commit_sha = record.get("commit", {}).get("commit_sha") if isinstance(record.get("commit"), dict) else None
        if not isinstance(commit_sha, str):
            raise ProtocolError("missing_publication_commit", "draft PR requires one verified publication commit")
        body = _pr_body(envelope, request_id, commit_sha)
        title = envelope["pull_request"]["title"]
        metadata_digest = _public_metadata_check(root, envelope, title, body)
        if replay is not None:
            if record["draft_pull_request"] is None:
                raise ProtocolError("replay_state_mismatch", "draft-PR replay lacks exact recorded evidence")
            transaction_path = _tx_path(root, record["id"], "create_draft_pr", request_id)
            transaction = _validate_operation_transaction(load_safe_json(transaction_path, "publication draft-PR transaction"))
            if transaction.get("status") != "finalized":
                _tx_status(
                    transaction_path,
                    transaction,
                    "finalized",
                    result_id=replay["result_id"],
                    pr_number=record["draft_pull_request"]["number"],
                    pr_url=record["draft_pull_request"]["url"],
                )
            return {
                "ok": True,
                "replay": True,
                "state": record["state"],
                "revision": record["revision"],
                "pr_number": record["draft_pull_request"]["number"],
                "pr_url": record["draft_pull_request"]["url"],
            }
        if record["state"] != "pushed" or record["push"] is None:
            raise ProtocolError("wrong_publication_state", "draft PR requires an exactly confirmed branch push")
        _verify_commit(root, envelope, commit_sha, _commit_message(envelope))
        intent = {
            "operation": "create_draft_pr", "record_digest": json_digest(record), "commit_sha": commit_sha,
            "destination": _pull_request_destination(envelope), "method": "github_create_draft_pr",
            "title_digest": hashlib.sha256(title.encode("utf-8")).hexdigest(), "body_digest": hashlib.sha256(body).hexdigest(),
            "metadata_digest": metadata_digest,
        }
        transaction_path, transaction, transaction_created = _begin_transaction(
            root, record, request_id, "create_draft_pr", intent
        )
        capability_path, capability_digest = _consume_operation(
            root, record, envelope, operation="create_draft_pr", request_id=request_id, target_sha=commit_sha,
            payload_digest=json_digest(intent), destination_id=_pull_request_destination(envelope),
            method="github_create_draft_pr",
        )
        if transaction.get("capability_digest") not in {None, capability_digest}:
            raise ProtocolError("transaction_conflict", "draft-PR transaction capability changed")
        if transaction["status"] == "intent":
            transaction = _tx_status(transaction_path, transaction, "capability_consumed", capability_digest=capability_digest)
        if transaction.get("status") == "blocked_collision":
            raise ProtocolError("pr_collision", "a pull request existed before this publication request")
        base_remote, head_remote = _observe_remote(root, envelope)
        if base_remote != envelope["base_sha"] or head_remote != commit_sha:
            raise ProtocolError("published_state_drift", "remote branch changed before draft PR creation")
        existing = _query_prs(root, envelope)
        if existing:
            if transaction_created:
                transaction = _tx_status(transaction_path, transaction, "blocked_collision", reason_code="pr_collision")
                raise ProtocolError("pr_collision", "a pull request already exists for this exact branch")
            try:
                item = _verified_pr(envelope, commit_sha, body, existing)
            except ProtocolError:
                transaction = _tx_status(transaction_path, transaction, "blocked_collision", reason_code="pr_collision")
                raise ProtocolError("pr_collision", "existing pull request does not match this publication request")
        else:
            item = None
        remote = envelope["remote"]
        if item is None:
            _recheck_consumed_operation(root, record, envelope, "create_draft_pr", request_id, intent)
            _verify_repository_identity(root, envelope)
            try:
                _gh(
                    root, "pr", "create", "--repo", f"github.com/{remote['repository']}", "--base", remote["base_branch"],
                    "--head", remote["head_branch"], "--title", title, "--body-file", "-", "--draft",
                    "--no-maintainer-edit", input_bytes=body, failure_code="pr_create_failed",
                )
            except ProtocolError:
                try:
                    item = _verified_pr(envelope, commit_sha, body, _query_prs(root, envelope))
                except ProtocolError:
                    _mark_unknown(record_path, record, request_id, "create_draft_pr", "pushed", json_digest(intent), "pr_state_indeterminate")
                    _tx_status(transaction_path, transaction, "effect_unknown", reason_code="pr_state_indeterminate")
                    raise ProtocolError("effect_unknown", "draft PR outcome is unknown; no automatic retry is permitted")
            try:
                item = _verified_pr(envelope, commit_sha, body, _query_prs(root, envelope))
            except ProtocolError:
                _mark_unknown(record_path, record, request_id, "create_draft_pr", "pushed", json_digest(intent), "pr_postcheck_indeterminate")
                _tx_status(transaction_path, transaction, "effect_unknown", reason_code="pr_postcheck_indeterminate")
                raise ProtocolError("effect_unknown", "draft PR postcondition is unknown; no automatic retry is permitted")
        assert item is not None
        result_id = stable_id("publication-pr", record["id"], request_id, str(item["number"]), commit_sha)
        record["draft_pull_request"] = {
            "request_id": request_id, "recorded_at": isoformat(utc_now()), "intent_digest": json_digest(intent),
            "capability_path": capability_path, "capability_digest": capability_digest,
            "repository": remote["repository"], "repository_id": remote["repository_id"],
            "number": item["number"], "url": item["url"],
            "base_branch": remote["base_branch"], "head_branch": remote["head_branch"], "head_sha": commit_sha,
            "is_draft": True, "title_digest": hashlib.sha256(title.encode("utf-8")).hexdigest(),
            "body_digest": hashlib.sha256(body).hexdigest(),
            "observation_digest": json_digest(
                {
                    "repository_id": remote["repository_id"],
                    "pull_request": {key: item[key] for key in sorted(item) if key not in {"title", "body"}},
                }
            ),
        }
        record["state"] = "draft_pr_verified"
        record["revision"] += 1
        _append_idempotency(record, request_id, "create_draft_pr", result_id)
        atomic_write_json(record_path, _validate_record(record))
        _tx_status(transaction_path, transaction, "finalized", result_id=result_id, pr_number=item["number"], pr_url=item["url"])
    return {"ok": True, "replay": False, "state": "draft_pr_verified", "revision": record["revision"], "pr_number": item["number"], "pr_url": item["url"]}


def _publication_transition_capability(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    transition_request_id: str,
    payload_digest: str,
) -> Tuple[str, str]:
    registry = validate_registry(
        load_safe_json(resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True), "executor registry")
    )
    writer = envelope["writer"]
    capability_id = stable_id(
        "cap",
        envelope["source_work_item_id"],
        "transition_work_item",
        transition_request_id,
    )
    relative = f"{CAPABILITY_PREFIX}{capability_id}.json"
    path = resolve_repo_path(root, relative)
    capability = {
        "schema_version": PUBLIC_VERSION,
        "kind": "approval_capability",
        "capability_id": capability_id,
        "work_item_id": envelope["source_work_item_id"],
        "work_item_revision": envelope["source_work_item_revision"],
        "operation": "transition_work_item",
        "scope": {
            "allowed_paths": [envelope["source_work_item"]],
            "target_sha": envelope["base_sha"],
            "payload_digest": payload_digest,
        },
        "executor": {
            "surface_id": writer["surface_id"],
            "executor_id": writer["executor_id"],
            "adapter_version": writer["adapter_version"],
            "guard_digest": current_guard_digest(),
            "registry_version": registry["registry_version"],
        },
        "approval": {
            "approved_by": envelope["approval"]["approved_by"],
            "accepted_at": envelope["approval"]["accepted_at"],
            "expires_at": envelope["approval"]["expires_at"],
            "one_time": True,
            "summary": "Advance the exact published candidate from release-ready to awaiting-release.",
        },
        "status": {
            "state": "active",
            "revoked_at": None,
            "consumed_at": None,
            "consumed_by_request_id": None,
        },
    }
    if path.exists() or path.is_symlink():
        existing = load_safe_json(path, "publication lifecycle capability")
        normalized = copy.deepcopy(existing)
        normalized["status"] = capability["status"]
        if normalized != capability:
            raise ProtocolError("capability_conflict", "publication lifecycle capability differs from exact intent")
    else:
        exclusive_write_json(path, capability)
    return relative, json_digest(capability)


def _ensure_awaiting_release(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    completion_request_id: str,
    commit_sha: str,
    pr_number: int,
    checks_digest: str,
) -> Dict[str, Any]:
    transition_request_id = stable_id(
        "publication-awaiting-release",
        record["id"],
        completion_request_id,
    )
    evidence = [
        f"publication-record:{record['id']}",
        f"commit:{commit_sha}",
        f"draft-pr:{pr_number}",
        f"required-checks:{checks_digest}",
    ]
    transition_args = argparse.Namespace(
        from_state="release_ready",
        to_state="awaiting_release",
        transition_name="publication_draft_pr_verified",
        evidence=evidence,
        reviewer_surface_id=None,
        reviewer_executor_id=None,
        review_evidence_hash=None,
        review_transition_id=None,
        human_uat_attestor=None,
    )
    intent_digest = transition_intent_digest(transition_args)
    capability_relpath, capability_digest = _publication_transition_capability(
        root,
        record,
        envelope,
        transition_request_id,
        intent_digest,
    )
    transition_args.capability_id_hint = Path(capability_relpath).stem
    transition_args.capability_relpath_hint = capability_relpath
    transition_args.capability_digest_hint = capability_digest
    transition_args.transition_intent_digest_hint = intent_digest
    writer = envelope["writer"]
    result = guarded_mutation(
        project_root=root,
        work_item_relpath=envelope["source_work_item"],
        capability_relpath=capability_relpath,
        registry_relpath=REGISTRY_RELPATH,
        request_id=transition_request_id,
        operation="transition_work_item",
        surface_id=writer["surface_id"],
        executor_id=writer["executor_id"],
        adapter_version=writer["adapter_version"],
        guard_digest=current_guard_digest(),
        payload_digest=intent_digest,
        require_sealed=True,
        separate_business_gate=True,
        publication_id=record["id"],
        publication_commit_sha=commit_sha,
        mutate=mutation_for_transition(transition_args),
    )
    current = validate_work_item(
        load_safe_json(resolve_repo_path(root, envelope["source_work_item"], require_exists=True), "publication source work item")
    )
    transition = current["transitions"][-1] if current["transitions"] else None
    if (
        current["lifecycle"]["state"] != "awaiting_release"
        or current["revision"] != envelope["source_work_item_revision"] + 1
        or not isinstance(transition, dict)
        or transition.get("id") != result["result_id"]
        or transition.get("request_id") != transition_request_id
        or transition.get("from") != "release_ready"
        or transition.get("to") != "awaiting_release"
        or transition.get("intent_digest") != intent_digest
        or transition.get("capability_path") != capability_relpath
        or transition.get("capability_digest") != capability_digest
    ):
        raise ProtocolError("publication_transition_mismatch", "source lifecycle transition is not exact")
    return {
        "request_id": transition_request_id,
        "transition_id": result["result_id"],
        "recorded_at": transition["accepted_at"],
        "from_state": "release_ready",
        "to_state": "awaiting_release",
        "source_revision_before": envelope["source_work_item_revision"],
        "source_revision_after": current["revision"],
        "capability_path": capability_relpath,
        "capability_digest": capability_digest,
        "intent_digest": intent_digest,
        "evidence_digest": json_digest(evidence),
    }


def _recovered_transition_checks_digest(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    completion_request_id: str,
) -> Optional[str]:
    source = validate_work_item(
        load_safe_json(
            resolve_repo_path(root, envelope["source_work_item"], require_exists=True),
            "publication source work item",
        )
    )
    if source["lifecycle"]["state"] == "release_ready" and source["revision"] == envelope["source_work_item_revision"]:
        return None
    transition_request_id = stable_id("publication-awaiting-release", record["id"], completion_request_id)
    transition = source["transitions"][-1] if source["transitions"] else None
    fixed_evidence = {
        f"publication-record:{record['id']}",
        f"commit:{record['commit']['commit_sha']}",
        f"draft-pr:{record['draft_pull_request']['number']}",
    }
    if (
        source["lifecycle"]["state"] != "awaiting_release"
        or source["revision"] != envelope["source_work_item_revision"] + 1
        or not isinstance(transition, dict)
        or transition.get("request_id") != transition_request_id
        or transition.get("from") != "release_ready"
        or transition.get("to") != "awaiting_release"
        or transition.get("operation") != "publication_draft_pr_verified"
        or not isinstance(transition.get("evidence"), list)
    ):
        raise ProtocolError("publication_transition_mismatch", "existing source transition is not exact recovery evidence")
    evidence = transition["evidence"]
    if any(not isinstance(item, str) for item in evidence):
        raise ProtocolError("publication_transition_mismatch", "existing source transition evidence is malformed")
    checks = [item for item in evidence if isinstance(item, str) and item.startswith("required-checks:")]
    if set(evidence) - set(checks) != fixed_evidence or len(evidence) != 4 or len(checks) != 1:
        raise ProtocolError("publication_transition_mismatch", "existing source transition evidence is incomplete or ambiguous")
    checks_digest = checks[0].split(":", 1)[1]
    require_digest(checks_digest, "recovered required-check digest")
    return checks_digest


def complete_publication(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    request_id = require_id(args.request_id, "request_id")
    publication_rel = canonical_relative_path(args.publication)
    with exclusive_lock(_lock_path(root, Path(publication_rel).stem)):
        record_path, record, envelope, replay, recovering = _load_operation(
            root, publication_rel, "complete_publication", request_id
        )
        _assert_actor(args, envelope)
        if replay is not None:
            if record["state"] != "complete" or record["completion"] is None or record["lifecycle_transition"] is None:
                raise ProtocolError("replay_state_mismatch", "publication completion replay lacks exact evidence")
            reservation_path, source_reservation = _validate_source_reservation(root, record, envelope)
            if source_reservation["status"] == "active":
                with exclusive_lock(_source_lock_path(root, envelope["source_work_item"])):
                    source_reservation = load_safe_json(reservation_path, "publication source reservation")
                    if source_reservation.get("status") == "active" and source_reservation.get("released_at") is None:
                        source_reservation["status"] = "released"
                        source_reservation["released_at"] = record["completion"]["completed_at"]
                        atomic_write_json(reservation_path, source_reservation)
            transaction_path = _tx_path(root, record["id"], "complete_publication", request_id)
            if not transaction_path.exists():
                raise ProtocolError("transaction_missing", "publication completion replay lacks its transaction")
            transaction = _validate_operation_transaction(load_safe_json(transaction_path, "publication completion transaction"))
            if transaction.get("status") != "finalized":
                _tx_status(
                    transaction_path,
                    transaction,
                    "finalized",
                    result_id=replay["result_id"],
                    pr_number=record["draft_pull_request"]["number"],
                    pr_url=record["draft_pull_request"]["url"],
                )
            return {"ok": True, "replay": True, "state": record["state"], "revision": record["revision"], "writer_status": record["reservation"]["status"]}
        if record["state"] != "draft_pr_verified" or record["draft_pull_request"] is None or record["commit"] is None:
            raise ProtocolError("wrong_publication_state", "publication completion requires one verified draft PR")
        commit_sha = record["commit"]["commit_sha"]
        pr_request = record["draft_pull_request"]["request_id"]
        body = _pr_body(envelope, pr_request, commit_sha)
        pr_number = record["draft_pull_request"]["number"]
        intent = {
            "operation": "complete_publication", "record_digest": json_digest(record), "commit_sha": commit_sha,
            "expected_remote_base": envelope["base_sha"], "expected_remote_head": commit_sha,
            "pr_number": pr_number, "pr_observation": record["draft_pull_request"]["observation_digest"],
            "required_checks": envelope["remote"]["required_checks"],
        }
        transaction_path, transaction, transaction_created = _begin_transaction(
            root, record, request_id, "complete_publication", intent
        )
        capability_path, capability_digest = _consume_operation(
            root, record, envelope, operation="complete_publication", request_id=request_id, target_sha=commit_sha,
            payload_digest=json_digest(intent), destination_id=_pull_request_destination(envelope, pr_number),
            method="complete_draft_pr_publication",
        )
        if transaction.get("capability_digest") not in {None, capability_digest}:
            raise ProtocolError("transaction_conflict", "publication completion capability changed")
        if transaction["status"] == "intent":
            transaction = _tx_status(transaction_path, transaction, "capability_consumed", capability_digest=capability_digest)
        recovered_checks_digest = _recovered_transition_checks_digest(root, record, envelope, request_id)
        if recovered_checks_digest is None:
            _recheck_consumed_operation(root, record, envelope, "complete_publication", request_id, intent)
            _verify_commit(root, envelope, commit_sha, _commit_message(envelope))
            base_after, head_after = _observe_remote(root, envelope)
            verified = _verified_pr(envelope, commit_sha, body, _query_prs(root, envelope))
            if base_after != envelope["base_sha"] or head_after != commit_sha or verified["number"] != pr_number:
                raise ProtocolError("published_state_drift", "publication state changed during completion")
            checks_digest = _verified_required_checks(root, envelope, pr_number)
            _recheck_consumed_operation(root, record, envelope, "complete_publication", request_id, intent)
        else:
            # The exact source transition is already durable. Converge using
            # its historical consumed authority without new network or local
            # lifecycle effects after the envelope expires.
            base_after = envelope["base_sha"]
            head_after = commit_sha
            checks_digest = recovered_checks_digest
            verified = record["draft_pull_request"]
        lifecycle_transition = _ensure_awaiting_release(
            root,
            record,
            envelope,
            request_id,
            commit_sha,
            pr_number,
            checks_digest,
        )
        _fault("after_publication_transition")
        result_id = stable_id("publication-complete", record["id"], request_id, commit_sha, str(pr_number))
        completed_at = isoformat(utc_now())
        record["lifecycle_transition"] = lifecycle_transition
        record["completion"] = {
            "request_id": request_id, "completed_at": completed_at, "publication_state": "complete",
            "capability_path": capability_path, "capability_digest": capability_digest,
            "intent_digest": json_digest(intent),
            "required_checks_digest": checks_digest,
            "verification_digest": json_digest({"base": base_after, "head": head_after, "pr": record["draft_pull_request"], "checks": checks_digest, "transition": lifecycle_transition}),
            "closed_gates": ["merge", "mark_ready", "tag", "release", "deploy", "promote", "downstream_rollout"],
        }
        record["state"] = "complete"
        record["reservation"]["status"] = "released"
        record["revision"] += 1
        _append_idempotency(record, request_id, "complete_publication", result_id)
        atomic_write_json(record_path, _validate_record(record))
        _fault("after_publication_record")
        reservation_path, source_reservation = _validate_source_reservation(root, record, envelope)
        with exclusive_lock(_source_lock_path(root, envelope["source_work_item"])):
            source_reservation = load_safe_json(reservation_path, "publication source reservation")
            if source_reservation.get("status") == "active" and source_reservation.get("released_at") is None:
                source_reservation["status"] = "released"
                source_reservation["released_at"] = completed_at
                atomic_write_json(reservation_path, source_reservation)
            elif source_reservation.get("status") != "released":
                raise ProtocolError("publication_reservation_mismatch", "source reservation cannot be safely released")
        _tx_status(transaction_path, transaction, "finalized", result_id=result_id, pr_number=pr_number, pr_url=verified["url"])
    return {"ok": True, "replay": False, "state": "complete", "revision": record["revision"], "writer_status": "released", "pr_number": pr_number, "pr_url": verified["url"]}


def _retirement_scope(root: Path, record: Dict[str, Any], envelope: Dict[str, Any], intent_digest: str) -> Dict[str, Any]:
    target_sha = record["commit"]["commit_sha"] if record.get("commit") is not None else envelope["base_sha"]
    return {
        "allowed_paths": sorted(
            [
                record["source_work_item"],
                record["source_reservation_path"],
                _record_path(root, record["id"]).relative_to(root).as_posix(),
            ]
        ),
        "target_sha": target_sha,
        "destination_id": f"project-local/publication/{record['id']}",
        "method": "retire_local_publication_reservation",
        "payload_digest": intent_digest,
    }


def _consume_retirement_capability(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
    args: argparse.Namespace,
    intent_digest: str,
) -> Tuple[str, str, Dict[str, Any]]:
    expected_path = _capability_path(root, record["id"], "retire_publication", args.request_id)
    relative = canonical_relative_path(args.capability)
    path = resolve_repo_path(root, relative, require_exists=True)
    if path != expected_path or not relative.startswith(CAPABILITY_PREFIX):
        raise ProtocolError("invalid_capability_path", "retirement requires its exact deterministic capability path")
    capability = validate_capability(load_safe_json(path, "publication retirement capability"))
    scope = _retirement_scope(root, record, envelope, intent_digest)
    executor = capability["executor"]
    if (
        capability["capability_id"] != path.stem
        or capability["work_item_id"] != record["id"]
        or capability["work_item_revision"] != record["revision"]
        or capability["operation"] != "retire_publication"
        or capability["scope"] != scope
        or executor["surface_id"] != args.surface_id
        or executor["executor_id"] != args.executor_id
        or executor["adapter_version"] != args.adapter_version
        or executor["guard_digest"] != current_guard_digest()
    ):
        raise ProtocolError("retirement_capability_mismatch", "retirement capability differs from the exact local intent")
    role = "egress" if record["state"] in {"pushed", "effect_unknown"} else "writer"
    authority_time = None
    if (
        capability["status"].get("state") == "consumed"
        and capability["status"].get("consumed_by_request_id") == args.request_id
    ):
        authority_time = parse_timestamp(capability["status"].get("consumed_at"), "retirement capability consumed_at")
    consumed = consume_capability(
        capability_path=path,
        registry_path=resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True),
        request_id=args.request_id,
        check_kwargs={
            "operation": "retire_publication",
            "work_item_id": record["id"],
            "work_item_revision": record["revision"],
            "surface_id": args.surface_id,
            "executor_id": args.executor_id,
            "adapter_version": args.adapter_version,
            "guard_digest": current_guard_digest(),
            "role": role,
            "target_paths": scope["allowed_paths"],
            "target_sha": scope["target_sha"],
            "destination_id": scope["destination_id"],
            "method": scope["method"],
            "payload_digest": intent_digest,
            "require_exact_paths": True,
        },
        now=authority_time,
    )
    return relative, json_digest(consumed), consumed


def _retirement_observation(
    root: Path,
    record: Dict[str, Any],
    envelope: Dict[str, Any],
) -> Tuple[str, List[str]]:
    state = record["state"]
    if state in {"authorized", "committed"}:
        return json_digest({"mode": "local_only", "outward_effects": []}), []
    if state not in {"pushed", "effect_unknown"}:
        raise ProtocolError("unsafe_retirement", "this publication state cannot be retired")
    base_remote, head_remote = _observe_remote(root, envelope)
    if base_remote != envelope["base_sha"]:
        raise ProtocolError("unsafe_retirement", "remote base moved; retirement requires manual resolution")
    commit_sha = record["commit"]["commit_sha"]
    if state == "effect_unknown" and record["unknown_effect"]["operation"] == "push_publication":
        if head_remote is not None:
            raise ProtocolError("unsafe_retirement", "unknown push is not absent; reconcile or resolve it before retirement")
        return json_digest({"base": base_remote, "head": None, "pull_requests": []}), []
    if head_remote != commit_sha:
        raise ProtocolError("unsafe_retirement", "published branch is missing or changed; retirement requires manual resolution")
    pull_requests = _query_prs(root, envelope)
    if pull_requests:
        raise ProtocolError("unsafe_retirement", "a pull request exists; reconcile or resolve it before retirement")
    return json_digest({"base": base_remote, "head": head_remote, "pull_requests": []}), ["named_branch"]


def retire_publication(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    request_id = require_id(args.request_id, "request_id")
    reason = _string(args.reason, "retirement reason", maximum=1000)
    publication_rel = canonical_relative_path(args.publication)
    with exclusive_lock(_lock_path(root, Path(publication_rel).stem)):
        record_path, record, envelope = _load_publication(root, publication_rel, require_active=False)
        replay = _replay(record, request_id, "retire_publication")
        if replay is not None:
            if record["state"] != "retired" or record["retirement"] is None:
                raise ProtocolError("replay_state_mismatch", "retirement replay lacks exact evidence")
            with exclusive_lock(_source_lock_path(root, envelope["source_work_item"])):
                reservation_path, reservation = _validate_source_reservation(root, record, envelope)
                if reservation["status"] == "active":
                    reservation["status"] = "released"
                    reservation["released_at"] = record["retirement"]["retired_at"]
                    atomic_write_json(reservation_path, reservation)
            transaction_path = _tx_path(root, record["id"], "retire_publication", request_id)
            transaction = _validate_operation_transaction(load_safe_json(transaction_path, "publication retirement transaction"))
            if transaction.get("status") != "finalized":
                _tx_status(transaction_path, transaction, "finalized", result_id=replay["result_id"])
            return {"ok": True, "replay": True, "state": "retired", "revision": record["revision"], "writer_status": "released"}
        if record["state"] in {"draft_pr_verified", "complete", "retired"}:
            raise ProtocolError("unsafe_retirement", "verified draft-PR or completed publication cannot be retired here")
        prior_state = record["state"]
        prior_revision = record["revision"]
        prior_unknown_digest = json_digest(record["unknown_effect"]) if record["unknown_effect"] is not None else None
        intent = {
            "operation": "retire_publication",
            "record_digest": json_digest(record),
            "prior_state": prior_state,
            "prior_revision": prior_revision,
            "prior_unknown_effect_digest": prior_unknown_digest,
            "reason": reason,
            "policy": "release_local_reservation_without_deleting_or_modifying_remote_effects",
        }
        intent_digest = json_digest(intent)
        retirement_scope = _retirement_scope(root, record, envelope, intent_digest)
        retirement_capability_rel = canonical_relative_path(args.capability)
        retirement_capability_path = resolve_repo_path(
            root, retirement_capability_rel, require_exists=True
        )
        if (
            retirement_capability_path
            != _capability_path(root, record["id"], "retire_publication", request_id)
            or not retirement_capability_rel.startswith(CAPABILITY_PREFIX)
        ):
            raise ProtocolError(
                "invalid_capability_path",
                "retirement requires its exact deterministic capability path",
            )
        # Reject expired or otherwise stale authority before _begin_transaction
        # can create the first local journal write. A second check below closes
        # the window between observation and the final retirement mutations.
        check_authority(
            capability_path=retirement_capability_path,
            registry_path=resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True),
            operation="retire_publication",
            work_item_id=record["id"],
            work_item_revision=prior_revision,
            request_id=request_id,
            surface_id=args.surface_id,
            executor_id=args.executor_id,
            adapter_version=args.adapter_version,
            guard_digest=current_guard_digest(),
            role="egress" if prior_state in {"pushed", "effect_unknown"} else "writer",
            target_paths=retirement_scope["allowed_paths"],
            target_sha=retirement_scope["target_sha"],
            destination_id=retirement_scope["destination_id"],
            method=retirement_scope["method"],
            payload_digest=intent_digest,
            allow_consumed_by_request_id=True,
            require_exact_paths=True,
        )
        transaction_path, transaction, _created = _begin_transaction(
            root, record, request_id, "retire_publication", intent
        )
        capability_path, capability_digest, capability = _consume_retirement_capability(
            root, record, envelope, args, intent_digest
        )
        if transaction.get("capability_digest") not in {None, capability_digest}:
            raise ProtocolError("transaction_conflict", "retirement transaction capability changed")
        if transaction["status"] == "intent":
            transaction = _tx_status(
                transaction_path, transaction, "capability_consumed", capability_digest=capability_digest
            )
        observation_digest, preserved_effects = _retirement_observation(root, record, envelope)
        # Recheck current authority only before the first local mutation. A
        # retry after that point converges through the replay branch above.
        check_authority(
            capability_path=resolve_repo_path(root, capability_path, require_exists=True),
            registry_path=resolve_repo_path(root, REGISTRY_RELPATH, require_exists=True),
            operation="retire_publication",
            work_item_id=record["id"],
            work_item_revision=prior_revision,
            request_id=request_id,
            surface_id=args.surface_id,
            executor_id=args.executor_id,
            adapter_version=args.adapter_version,
            guard_digest=current_guard_digest(),
            role="egress" if prior_state in {"pushed", "effect_unknown"} else "writer",
            target_paths=retirement_scope["allowed_paths"],
            target_sha=retirement_scope["target_sha"],
            destination_id=f"project-local/publication/{record['id']}",
            method="retire_local_publication_reservation",
            payload_digest=intent_digest,
            allow_consumed_by_request_id=True,
            require_exact_paths=True,
        )
        retired_at = isoformat(utc_now())
        record["state"] = "retired"
        record["revision"] = prior_revision + 1
        record["reservation"]["status"] = "released"
        record["retirement"] = {
            "request_id": request_id,
            "retired_at": retired_at,
            "capability_path": capability_path,
            "capability_digest": capability_digest,
            "intent_digest": intent_digest,
            "prior_state": prior_state,
            "prior_revision": prior_revision,
            "prior_unknown_effect_digest": prior_unknown_digest,
            "reason": reason,
            "observation_digest": observation_digest,
            "preserved_effects": preserved_effects,
        }
        result_id = stable_id("publication-retirement", record["id"], request_id, intent_digest)
        _append_idempotency(record, request_id, "retire_publication", result_id)
        atomic_write_json(record_path, _validate_record(record))
        with exclusive_lock(_source_lock_path(root, envelope["source_work_item"])):
            reservation_path, reservation = _validate_source_reservation(root, record, envelope)
            if reservation["status"] == "active":
                reservation["status"] = "released"
                reservation["released_at"] = retired_at
                atomic_write_json(reservation_path, reservation)
        _tx_status(transaction_path, transaction, "finalized", result_id=result_id)
    return {
        "ok": True,
        "replay": False,
        "state": "retired",
        "revision": record["revision"],
        "writer_status": "released",
        "preserved_effects": preserved_effects,
    }


def publication_status(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    _, record, _ = _load_publication(root, canonical_relative_path(args.publication), require_active=False)
    return {
        "ok": True, "read_only": True, "publication_id": record["id"], "revision": record["revision"],
        "state": record["state"], "writer_status": record["reservation"]["status"],
        "commit_sha": None if record["commit"] is None else record["commit"]["commit_sha"],
        "remote_head_sha": None if record["push"] is None else record["push"]["observed_remote_sha"],
        "pr_number": None if record["draft_pull_request"] is None else record["draft_pull_request"]["number"],
        "unknown_effect": None if record["unknown_effect"] is None else record["unknown_effect"]["reason_code"],
        "retirement_reason": None if record["retirement"] is None else record["retirement"]["reason"],
    }


def runtime_facts(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.project_root).resolve(strict=True)
    _require_trusted_runtime_root(IMPLEMENTATION_ROOT, root)
    closure_digest, checker_digest, _runtime_state = _runtime_closure_digest()
    facts = {
        "executor_closure_digest": closure_digest,
        "public_checker_digest": checker_digest,
    }
    for name in TRUSTED_TOOL_NAMES:
        path = _resolve_runtime_executable(name, root)
        facts[f"{name}_executable_digest"] = _regular_file_digest(
            path, f"trusted {name} executable"
        )[0]
    return {"ok": True, "read_only": True, "trusted_runtime": facts}


def _add_actor_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--publication", required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--surface-id", required=True)
    parser.add_argument("--executor-id", required=True)
    parser.add_argument("--adapter-version", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("bootstrap-publication")
    bootstrap.add_argument("--project-root", type=Path, required=True)
    bootstrap.add_argument("--envelope-source", type=Path, required=True)
    bootstrap.add_argument("--request-id", required=True)
    status = commands.add_parser("status")
    status.add_argument("--project-root", type=Path, required=True)
    status.add_argument("--publication", required=True)
    facts = commands.add_parser("runtime-facts")
    facts.add_argument("--project-root", type=Path, required=True)
    for name in ("commit-publication", "push-publication", "create-draft-pr", "complete-publication"):
        _add_actor_arguments(commands.add_parser(name))
    retire = commands.add_parser("retire-publication")
    _add_actor_arguments(retire)
    retire.add_argument("--capability", required=True)
    retire.add_argument("--reason", required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "bootstrap-publication":
            result = bootstrap_publication(args)
        elif args.command == "status":
            result = publication_status(args)
        elif args.command == "runtime-facts":
            result = runtime_facts(args)
        elif args.command == "commit-publication":
            result = commit_publication(args)
        elif args.command == "push-publication":
            result = push_publication(args)
        elif args.command == "create-draft-pr":
            result = create_draft_pr(args)
        elif args.command == "complete-publication":
            result = complete_publication(args)
        elif args.command == "retire-publication":
            result = retire_publication(args)
        else:
            raise ProtocolError("unknown_command", "publication command is not supported")
    except ProtocolError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message}, sort_keys=True))
        return 1
    except Exception:
        print(
            json.dumps(
                {
                    "ok": False,
                    "code": "internal_publication_error",
                    "message": "guarded publication failed without exposing internal paths or data",
                },
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
