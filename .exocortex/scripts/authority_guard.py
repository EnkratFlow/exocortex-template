#!/usr/bin/env python3
"""Fail-closed approval and guarded-executor validation.

This module deliberately uses only the Python standard library.  It validates
protocol-managed capabilities and can consume a one-time capability under an
exclusive file lock.  It never reads payload content, credentials, or .env
files and it never performs network activity.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple


PUBLIC_VERSION = "public-v2"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
GIT_OR_DIGEST_RE = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")


class ProtocolError(RuntimeError):
    """A safe, user-displayable protocol denial."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def isoformat(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: Any, field: str) -> dt.datetime:
    if not isinstance(value, str) or not value:
        raise ProtocolError("invalid_timestamp", f"{field} must be a non-empty RFC3339 timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProtocolError("invalid_timestamp", f"{field} is not a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ProtocolError("invalid_timestamp", f"{field} must include a timezone")
    return parsed.astimezone(dt.timezone.utc)


def reject_duplicate_keys(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate_json_key", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=reject_duplicate_keys)
    except FileNotFoundError as exc:
        raise ProtocolError("missing_file", f"required protocol file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolError("invalid_json", f"invalid JSON in {path.name}") from exc
    if not isinstance(value, dict):
        raise ProtocolError("invalid_document", f"{path.name} must contain one JSON object")
    return value


def require_exact_keys(value: Dict[str, Any], required: Iterable[str], optional: Iterable[str], label: str) -> None:
    required_set = set(required)
    allowed = required_set | set(optional)
    missing = sorted(required_set - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ProtocolError("missing_field", f"{label} is missing required fields: {', '.join(missing)}")
    if unknown:
        raise ProtocolError("unknown_field", f"{label} contains unknown fields: {', '.join(unknown)}")


def require_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ProtocolError("invalid_id", f"{field} is not a valid protocol identifier")
    return value


def require_digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise ProtocolError("invalid_digest", f"{field} must be a lowercase SHA-256 digest")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def json_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        raise ProtocolError("unreadable_file", f"cannot safely open file: {path}") from exc
    try:
        with os.fdopen(fd, "rb", closefd=False) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    finally:
        os.close(fd)
    return digest.hexdigest()


def current_guard_digest() -> str:
    """Digest the executing authority guard, never an arbitrary caller path."""
    return sha256_file(Path(__file__).resolve(strict=True))


def canonical_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ProtocolError("invalid_path", "target path must be a non-empty relative path")
    candidate = Path(value)
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise ProtocolError("invalid_path", "absolute and parent-traversal paths are forbidden")
    normalized = candidate.as_posix()
    if normalized in ("", "."):
        raise ProtocolError("invalid_path", "target path must identify a repository-relative path")
    return normalized


def resolve_repo_path(root: Path, relative: str, *, require_exists: bool = False) -> Path:
    rel = canonical_relative_path(relative)
    root_real = root.resolve(strict=True)
    candidate = root_real / rel
    cursor = root_real
    for part in Path(rel).parts[:-1]:
        cursor = cursor / part
        if cursor.exists():
            if cursor.is_symlink():
                raise ProtocolError("symlink_parent", "symlink parents are not allowed for guarded paths")
            try:
                cursor.resolve(strict=True).relative_to(root_real)
            except ValueError as exc:
                raise ProtocolError("path_escape", "target path escapes the approved project root") from exc
    if candidate.exists() and candidate.is_symlink():
        raise ProtocolError("symlink_target", "symlink targets are not allowed for guarded mutations")
    if require_exists and not candidate.exists():
        raise ProtocolError("missing_target", f"target does not exist: {rel}")
    return candidate


def validate_registry(document: Dict[str, Any]) -> Dict[str, Any]:
    require_exact_keys(
        document,
        ["schema_version", "kind", "registry_version", "default_role", "executors"],
        [],
        "executor registry",
    )
    if document["schema_version"] != PUBLIC_VERSION or document["kind"] != "executor_registry":
        raise ProtocolError("wrong_schema", "executor registry must use public-v2 executor_registry")
    if document["default_role"] != "read_only":
        raise ProtocolError("unsafe_default", "executor registry default role must be read_only")
    if not isinstance(document["registry_version"], int) or document["registry_version"] < 1:
        raise ProtocolError("invalid_registry_version", "registry_version must be a positive integer")
    executors = document["executors"]
    if not isinstance(executors, list):
        raise ProtocolError("invalid_registry", "executors must be an array")
    seen: Set[Tuple[str, str]] = set()
    for entry in executors:
        if not isinstance(entry, dict):
            raise ProtocolError("invalid_executor", "executor entry must be an object")
        require_exact_keys(
            entry,
            [
                "surface_id",
                "executor_id",
                "adapter_version",
                "guard_digest",
                "roles",
                "status",
                "registered_at",
                "expires_at",
                "revoked_at",
            ],
            [],
            "executor entry",
        )
        surface_id = require_id(entry["surface_id"], "surface_id")
        executor_id = require_id(entry["executor_id"], "executor_id")
        key = (surface_id, executor_id)
        if key in seen:
            raise ProtocolError("duplicate_executor", "executor registry contains a duplicate surface/executor pair")
        seen.add(key)
        if not isinstance(entry["adapter_version"], str) or not entry["adapter_version"]:
            raise ProtocolError("invalid_adapter", "adapter_version must be non-empty")
        require_digest(entry["guard_digest"], "guard_digest")
        roles = entry["roles"]
        if not isinstance(roles, list) or len(roles) != len(set(roles)) or any(role not in {"read_only", "writer", "egress"} for role in roles):
            raise ProtocolError("invalid_roles", "executor roles are invalid")
        if entry["status"] not in {"active", "expired", "revoked"}:
            raise ProtocolError("invalid_executor_status", "executor status is invalid")
        parse_timestamp(entry["registered_at"], "registered_at")
        parse_timestamp(entry["expires_at"], "expires_at")
        if entry["revoked_at"] is not None:
            parse_timestamp(entry["revoked_at"], "revoked_at")
    return document


def validate_capability(document: Dict[str, Any]) -> Dict[str, Any]:
    require_exact_keys(
        document,
        [
            "schema_version",
            "kind",
            "capability_id",
            "work_item_id",
            "work_item_revision",
            "operation",
            "scope",
            "executor",
            "approval",
            "status",
        ],
        [],
        "approval capability",
    )
    if document["schema_version"] != PUBLIC_VERSION or document["kind"] != "approval_capability":
        raise ProtocolError("wrong_schema", "capability must use public-v2 approval_capability")
    require_id(document["capability_id"], "capability_id")
    require_id(document["work_item_id"], "work_item_id")
    if not isinstance(document["work_item_revision"], int) or document["work_item_revision"] < 0:
        raise ProtocolError("invalid_revision", "work_item_revision must be a non-negative integer")
    if not isinstance(document["operation"], str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,99}", document["operation"]):
        raise ProtocolError("invalid_operation", "operation must be lower snake_case")

    scope = document["scope"]
    if not isinstance(scope, dict):
        raise ProtocolError("invalid_scope", "scope must be an object")
    require_exact_keys(
        scope,
        ["allowed_paths"],
        ["target_sha", "destination_id", "method", "payload_descriptor_id", "payload_digest"],
        "capability scope",
    )
    paths = scope["allowed_paths"]
    if not isinstance(paths, list) or len(paths) != len(set(paths)):
        raise ProtocolError("invalid_scope_paths", "allowed_paths must be a unique array")
    scope["allowed_paths"] = [canonical_relative_path(value) for value in paths]
    if scope.get("target_sha") is not None and (
        not isinstance(scope["target_sha"], str) or not GIT_OR_DIGEST_RE.fullmatch(scope["target_sha"])
    ):
        raise ProtocolError("invalid_target_sha", "target_sha must be a Git or SHA-256 digest")
    if scope.get("payload_digest") is not None:
        require_digest(scope["payload_digest"], "payload_digest")
    for field in ("destination_id", "method", "payload_descriptor_id"):
        if scope.get(field) is not None and (not isinstance(scope[field], str) or not scope[field]):
            raise ProtocolError("invalid_scope_field", f"{field} must be null or a non-empty string")

    executor = document["executor"]
    if not isinstance(executor, dict):
        raise ProtocolError("invalid_executor", "capability executor must be an object")
    require_exact_keys(
        executor,
        ["surface_id", "executor_id", "adapter_version", "guard_digest", "registry_version"],
        [],
        "capability executor",
    )
    require_id(executor["surface_id"], "surface_id")
    require_id(executor["executor_id"], "executor_id")
    if not isinstance(executor["adapter_version"], str) or not executor["adapter_version"]:
        raise ProtocolError("invalid_adapter", "adapter_version must be non-empty")
    require_digest(executor["guard_digest"], "guard_digest")
    if not isinstance(executor["registry_version"], int) or executor["registry_version"] < 1:
        raise ProtocolError("invalid_registry_version", "registry_version must be positive")

    approval = document["approval"]
    if not isinstance(approval, dict):
        raise ProtocolError("invalid_approval", "approval must be an object")
    require_exact_keys(
        approval,
        ["approved_by", "accepted_at", "expires_at", "one_time"],
        ["summary"],
        "approval",
    )
    if not isinstance(approval["approved_by"], str) or not approval["approved_by"]:
        raise ProtocolError("invalid_approver", "approved_by must be non-empty")
    parse_timestamp(approval["accepted_at"], "accepted_at")
    parse_timestamp(approval["expires_at"], "expires_at")
    if approval["one_time"] is not True:
        raise ProtocolError("reusable_capability", "all mutation and egress capabilities must be one-time")

    status = document["status"]
    if not isinstance(status, dict):
        raise ProtocolError("invalid_status", "capability status must be an object")
    require_exact_keys(
        status,
        ["state", "revoked_at", "consumed_at", "consumed_by_request_id"],
        [],
        "capability status",
    )
    if status["state"] not in {"active", "consumed", "revoked"}:
        raise ProtocolError("invalid_status", "capability status state is invalid")
    if status["revoked_at"] is not None:
        parse_timestamp(status["revoked_at"], "revoked_at")
    if status["consumed_at"] is not None:
        parse_timestamp(status["consumed_at"], "consumed_at")
    if status["consumed_by_request_id"] is not None:
        require_id(status["consumed_by_request_id"], "consumed_by_request_id")
    return document


def find_executor(
    registry: Dict[str, Any],
    *,
    surface_id: str,
    executor_id: str,
    adapter_version: str,
    guard_digest: str,
    role: str,
    now: dt.datetime,
) -> Dict[str, Any]:
    matches = [
        item
        for item in registry["executors"]
        if item["surface_id"] == surface_id and item["executor_id"] == executor_id
    ]
    if not matches:
        raise ProtocolError("unregistered_executor", "surface/executor is not registered; role remains read_only")
    entry = matches[0]
    if entry["status"] != "active" or entry["revoked_at"] is not None:
        raise ProtocolError("inactive_executor", "executor registration is expired or revoked")
    if parse_timestamp(entry["expires_at"], "expires_at") <= now:
        raise ProtocolError("expired_executor", "executor registration has expired")
    if entry["adapter_version"] != adapter_version:
        raise ProtocolError("adapter_mismatch", "adapter version does not match the registry")
    if entry["guard_digest"] != guard_digest:
        raise ProtocolError("guard_digest_mismatch", "guard executable digest does not match the registry")
    if role not in entry["roles"]:
        raise ProtocolError("role_denied", f"executor is not registered for role: {role}")
    return entry


def check_authority(
    *,
    capability_path: Path,
    registry_path: Path,
    operation: str,
    work_item_id: str,
    work_item_revision: int,
    request_id: str,
    surface_id: str,
    executor_id: str,
    adapter_version: str,
    guard_digest: str,
    role: str,
    now: Optional[dt.datetime] = None,
    target_path: Optional[str] = None,
    target_paths: Optional[Sequence[str]] = None,
    target_sha: Optional[str] = None,
    destination_id: Optional[str] = None,
    method: Optional[str] = None,
    payload_descriptor_id: Optional[str] = None,
    payload_digest: Optional[str] = None,
    allow_consumed_by_request_id: bool = False,
    require_exact_paths: bool = False,
) -> Dict[str, Any]:
    current = now or utc_now()
    require_id(request_id, "request_id")
    require_id(surface_id, "surface_id")
    require_id(executor_id, "executor_id")
    require_digest(guard_digest, "guard_digest")
    executing_guard_digest = current_guard_digest()
    if guard_digest != executing_guard_digest:
        raise ProtocolError("guard_digest_mismatch", "claimed guard digest does not match the executing authority guard")
    if role not in {"writer", "egress"}:
        raise ProtocolError("invalid_role", "authority checks support writer or egress roles only")

    registry = validate_registry(load_json(registry_path))
    capability = validate_capability(load_json(capability_path))

    find_executor(
        registry,
        surface_id=surface_id,
        executor_id=executor_id,
        adapter_version=adapter_version,
        guard_digest=guard_digest,
        role=role,
        now=current,
    )

    executor = capability["executor"]
    expected_executor = {
        "surface_id": surface_id,
        "executor_id": executor_id,
        "adapter_version": adapter_version,
        "guard_digest": guard_digest,
        "registry_version": registry["registry_version"],
    }
    if executor != expected_executor:
        raise ProtocolError("cross_surface_replay", "capability executor binding does not match current registry identity")
    if capability["operation"] != operation:
        raise ProtocolError("operation_mismatch", "capability does not authorize this operation")
    if capability["work_item_id"] != work_item_id or capability["work_item_revision"] != work_item_revision:
        raise ProtocolError("work_item_mismatch", "capability work item or revision is stale or mismatched")
    status = capability["status"]
    consumed_replay = (
        allow_consumed_by_request_id
        and status["state"] == "consumed"
        and status["revoked_at"] is None
        and status["consumed_at"] is not None
        and status["consumed_by_request_id"] == request_id
    )
    if status["state"] == "revoked" or status["revoked_at"] is not None:
        raise ProtocolError("inactive_capability", "capability is revoked")
    if status["state"] != "active" and not consumed_replay:
        raise ProtocolError("consumed_capability", "capability has already been consumed")
    if not consumed_replay and (status["consumed_at"] is not None or status["consumed_by_request_id"] is not None):
        raise ProtocolError("consumed_capability", "capability has already been consumed")
    accepted_at = parse_timestamp(capability["approval"]["accepted_at"], "accepted_at")
    expires_at = parse_timestamp(capability["approval"]["expires_at"], "expires_at")
    if accepted_at > current:
        raise ProtocolError("future_approval", "approval acceptance time is in the future")
    if expires_at <= current:
        raise ProtocolError("expired_capability", "capability has expired")

    scope = capability["scope"]
    requested_paths: List[str] = []
    if target_path is not None:
        requested_paths.append(canonical_relative_path(target_path))
    if target_paths is not None:
        if not isinstance(target_paths, (list, tuple)) or not target_paths:
            raise ProtocolError("invalid_target_paths", "target_paths must be a non-empty sequence")
        requested_paths.extend(canonical_relative_path(value) for value in target_paths)
    if len(requested_paths) != len(set(requested_paths)):
        raise ProtocolError("duplicate_target_path", "requested target paths must be unique")
    missing_paths = sorted(set(requested_paths) - set(scope["allowed_paths"]))
    if missing_paths:
        raise ProtocolError("path_not_allowed", "one or more target paths are outside the exact capability scope")
    if require_exact_paths and set(requested_paths) != set(scope["allowed_paths"]):
        raise ProtocolError("path_set_mismatch", "requested target paths must exactly match the capability scope")
    expected_fields = {
        "target_sha": target_sha,
        "destination_id": destination_id,
        "method": method,
        "payload_descriptor_id": payload_descriptor_id,
        "payload_digest": payload_digest,
    }
    for field, supplied in expected_fields.items():
        if supplied is not None and scope.get(field) != supplied:
            raise ProtocolError("scope_mismatch", f"capability {field} does not match the requested effect")
    return capability


@contextlib.contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def atomic_write_json(path: Path, value: Dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8"))
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def consume_capability(
    *,
    capability_path: Path,
    registry_path: Path,
    request_id: str,
    check_kwargs: Dict[str, Any],
    now: Optional[dt.datetime] = None,
) -> Dict[str, Any]:
    current = now or utc_now()
    lock_path = capability_path.with_suffix(capability_path.suffix + ".lock")
    with exclusive_lock(lock_path):
        capability = check_authority(
            capability_path=capability_path,
            registry_path=registry_path,
            request_id=request_id,
            now=current,
            allow_consumed_by_request_id=True,
            **check_kwargs,
        )
        if capability["status"]["state"] == "consumed":
            return capability
        capability["status"] = {
            "state": "consumed",
            "revoked_at": None,
            "consumed_at": isoformat(current),
            "consumed_by_request_id": request_id,
        }
        atomic_write_json(capability_path, capability)
        return capability


def safe_result(ok: bool, *, code: str, message: str, capability: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {"ok": ok, "code": code, "message": message}
    if capability is not None:
        result.update(
            {
                "capability_id": capability["capability_id"],
                "work_item_id": capability["work_item_id"],
                "work_item_revision": capability["work_item_revision"],
                "operation": capability["operation"],
            }
        )
    return result


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--capability", required=True, help="project-relative path under .exocortex/local/protocol/capabilities/")
    parser.add_argument("--registry", default=".exocortex/control/EXECUTOR_REGISTRY.json")
    parser.add_argument("--operation", required=True)
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--work-item-revision", type=int, required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--surface-id", required=True)
    parser.add_argument("--executor-id", required=True)
    parser.add_argument("--adapter-version", required=True)
    parser.add_argument("--guard-digest", required=True)
    parser.add_argument("--role", choices=["writer", "egress"], required=True)
    parser.add_argument("--target-path", action="append", dest="target_paths")
    parser.add_argument("--target-sha")
    parser.add_argument("--destination-id")
    parser.add_argument("--method")
    parser.add_argument("--payload-descriptor-id")
    parser.add_argument("--payload-digest")
    parser.add_argument("--require-exact-path-set", action="store_true")


def kwargs_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "operation": args.operation,
        "work_item_id": args.work_item_id,
        "work_item_revision": args.work_item_revision,
        "surface_id": args.surface_id,
        "executor_id": args.executor_id,
        "adapter_version": args.adapter_version,
        "guard_digest": args.guard_digest,
        "role": args.role,
        "target_paths": args.target_paths,
        "target_sha": args.target_sha,
        "destination_id": args.destination_id,
        "method": args.method,
        "payload_descriptor_id": args.payload_descriptor_id,
        "payload_digest": args.payload_digest,
        "require_exact_paths": args.require_exact_path_set,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("guard-digest", help="print only this authority guard's SHA-256 digest")

    check = subparsers.add_parser("check")
    add_common_arguments(check)
    check.add_argument("--allow-consumed-by-request-id", action="store_true")
    consume = subparsers.add_parser("consume")
    add_common_arguments(consume)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "guard-digest":
            print(current_guard_digest())
            return 0
        project_root = args.project_root.resolve(strict=True)
        capability_relpath = canonical_relative_path(args.capability)
        if not capability_relpath.startswith(".exocortex/local/protocol/capabilities/"):
            raise ProtocolError("invalid_capability_path", "capability must be project-local protocol state")
        if canonical_relative_path(args.registry) != ".exocortex/control/EXECUTOR_REGISTRY.json":
            raise ProtocolError("invalid_registry_path", "executor registry path is fixed by the public contract")
        capability_path = resolve_repo_path(project_root, capability_relpath, require_exists=True)
        registry_path = resolve_repo_path(project_root, args.registry, require_exists=True)
        check_kwargs = kwargs_from_args(args)
        if args.command == "check":
            capability = check_authority(
                capability_path=capability_path,
                registry_path=registry_path,
                request_id=args.request_id,
                allow_consumed_by_request_id=args.allow_consumed_by_request_id,
                **check_kwargs,
            )
        else:
            capability = consume_capability(
                capability_path=capability_path,
                registry_path=registry_path,
                request_id=args.request_id,
                check_kwargs=check_kwargs,
            )
        print(json.dumps(safe_result(True, code="authorized", message="exact capability accepted", capability=capability), sort_keys=True))
        return 0
    except ProtocolError as exc:
        print(json.dumps(safe_result(False, code=exc.code, message=exc.message), sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
