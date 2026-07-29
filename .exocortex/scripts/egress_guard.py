#!/usr/bin/env python3
"""Two-stage immutable-payload egress guard.

Stage creates a local content-addressed payload descriptor under a separately
authorized local operation.  Send checks capability/policy/descriptor metadata
before payload access, verifies the exact bytes, consumes authority, then and
only then resolves a credential and initializes transport.  No automatic retry
is performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Sequence, Tuple
import urllib.error
import urllib.parse
import urllib.request

from authority_guard import (
    ProtocolError,
    atomic_write_json,
    check_authority,
    consume_capability,
    current_guard_digest,
    exclusive_lock,
    isoformat,
    json_digest,
    load_json,
    require_digest,
    require_exact_keys,
    require_id,
    resolve_repo_path,
    utc_now,
)


DESCRIPTOR_VERSION = "public-v2"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
REGISTRY_RELPATH = ".exocortex/control/EXECUTOR_REGISTRY.json"
POLICY_RELPATH = ".exocortex/control/EXTERNAL_SYNC_POLICY.json"
CAPABILITY_PREFIX = ".exocortex/local/protocol/capabilities/"
DESCRIPTOR_PREFIX = ".exocortex/local/protocol/descriptors/"
AUDIT_RELPATH = ".exocortex/local/protocol/audit/egress.jsonl"
TRANSACTION_PREFIX = ".exocortex/local/protocol/transactions/"
AUDIT_GENESIS = "0" * 64


def resolve_identity_paths(project_root: Path, capability: str, registry: str) -> Tuple[Path, Path]:
    if not capability.startswith(CAPABILITY_PREFIX):
        raise ProtocolError("invalid_capability_path", "capability must be project-local protocol state")
    if registry != REGISTRY_RELPATH:
        raise ProtocolError("invalid_registry_path", "executor registry path is fixed by the public contract")
    return (
        resolve_repo_path(project_root, capability, require_exists=True),
        resolve_repo_path(project_root, registry, require_exists=True),
    )


def validate_audit_records(path: Path) -> Tuple[int, str, Dict[str, Dict[str, Any]]]:
    sequence = 0
    previous_hash = AUDIT_GENESIS
    event_ids: Dict[str, Dict[str, Any]] = {}
    if not path.exists():
        return sequence, previous_hash, event_ids
    with path.open("r", encoding="utf-8") as existing:
        for line in existing:
            try:
                record = json.loads(line, object_pairs_hook=lambda pairs: _unique_pairs(pairs))
            except (json.JSONDecodeError, ProtocolError) as exc:
                raise ProtocolError("invalid_audit", "egress audit contains invalid JSON") from exc
            if not isinstance(record, dict):
                raise ProtocolError("invalid_audit", "egress audit record must be an object")
            claimed_hash = record.get("record_hash")
            require_digest(claimed_hash, "audit record_hash")
            body = dict(record)
            body.pop("record_hash")
            if body.get("sequence") != sequence + 1 or body.get("previous_hash") != previous_hash:
                raise ProtocolError("invalid_audit_chain", "egress audit sequence or previous hash is invalid")
            if json_digest(body) != claimed_hash:
                raise ProtocolError("invalid_audit_chain", "egress audit record hash is invalid")
            sequence += 1
            previous_hash = claimed_hash
            event_id = body.get("event_id")
            if event_id is not None:
                if not isinstance(event_id, str) or not event_id or event_id in event_ids:
                    raise ProtocolError("invalid_audit", "egress audit event IDs must be unique non-empty strings")
                event_ids[event_id] = record
    return sequence, previous_hash, event_ids


def _unique_pairs(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProtocolError("duplicate_json_key", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def append_audit(path: Path, event: str, *, event_id: Optional[str] = None, **safe_fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(path.with_suffix(path.suffix + ".lock")):
        sequence, previous_hash, event_ids = validate_audit_records(path)
        if event_id is not None and event_id in event_ids:
            return
        record = {
            "event": event,
            "timestamp": isoformat(utc_now()),
            "sequence": sequence + 1,
            "previous_hash": previous_hash,
            **safe_fields,
        }
        if event_id is not None:
            record["event_id"] = event_id
        record["record_hash"] = json_digest(record)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def validate_descriptor(document: Dict[str, Any]) -> Dict[str, Any]:
    require_exact_keys(
        document,
        [
            "schema_version",
            "kind",
            "descriptor_id",
            "payload_digest",
            "byte_size",
            "media_type",
            "payload_class",
            "object_relpath",
            "created_at",
            "immutable",
        ],
        [],
        "payload descriptor",
    )
    if document["schema_version"] != DESCRIPTOR_VERSION or document["kind"] != "immutable_payload_descriptor":
        raise ProtocolError("wrong_descriptor_schema", "payload descriptor must use public-v2")
    require_id(document["descriptor_id"], "descriptor_id")
    require_digest(document["payload_digest"], "payload_digest")
    if not isinstance(document["byte_size"], int) or document["byte_size"] < 0:
        raise ProtocolError("invalid_payload_size", "descriptor byte_size must be non-negative")
    for field in ("media_type", "payload_class", "object_relpath", "created_at"):
        if not isinstance(document[field], str) or not document[field]:
            raise ProtocolError("invalid_descriptor", f"descriptor {field} must be non-empty")
    if document["immutable"] is not True:
        raise ProtocolError("mutable_payload", "descriptor must mark the payload immutable")
    identity = {
        "payload_digest": document["payload_digest"],
        "byte_size": document["byte_size"],
        "media_type": document["media_type"],
        "payload_class": document["payload_class"],
        "object_relpath": document["object_relpath"],
    }
    expected = "descriptor-" + json_digest(identity)
    if document["descriptor_id"] != expected:
        raise ProtocolError("descriptor_id_mismatch", "descriptor identity does not match its metadata")
    return document


def validate_policy(document: Dict[str, Any]) -> Dict[str, Any]:
    require_exact_keys(
        document,
        ["schema_version", "kind", "default", "policy_version", "destinations"],
        [],
        "external sync policy",
    )
    if document["schema_version"] != "public-v2" or document["kind"] != "external_sync_policy":
        raise ProtocolError("wrong_policy_schema", "external sync policy must use public-v2")
    if document["default"] != "deny":
        raise ProtocolError("unsafe_policy_default", "external sync policy default must be deny")
    if not isinstance(document["policy_version"], int) or document["policy_version"] < 1:
        raise ProtocolError("invalid_policy_version", "policy_version must be positive")
    if not isinstance(document["destinations"], list):
        raise ProtocolError("invalid_policy", "destinations must be an array")
    seen = set()
    for item in document["destinations"]:
        if not isinstance(item, dict):
            raise ProtocolError("invalid_destination", "destination entry must be an object")
        require_exact_keys(
            item,
            ["destination_id", "transport", "methods", "endpoint", "credential_env", "status", "max_payload_bytes"],
            [],
            "destination entry",
        )
        destination_id = require_id(item["destination_id"], "destination_id")
        if destination_id in seen:
            raise ProtocolError("duplicate_destination", "destination policy contains a duplicate ID")
        seen.add(destination_id)
        if item["transport"] not in {"https_json", "local_copy", "fake"}:
            raise ProtocolError("invalid_transport", "destination transport is invalid")
        if not isinstance(item["methods"], list) or not item["methods"] or len(item["methods"]) != len(set(item["methods"])):
            raise ProtocolError("invalid_methods", "destination methods must be a unique non-empty array")
        if any(method not in {"POST", "PUT", "COPY"} for method in item["methods"]):
            raise ProtocolError("invalid_methods", "destination policy contains an unsupported method")
        if not isinstance(item["endpoint"], str) or not item["endpoint"]:
            raise ProtocolError("invalid_endpoint", "destination endpoint must be non-empty")
        if item["transport"] == "https_json":
            endpoint = urllib.parse.urlsplit(item["endpoint"])
            if endpoint.scheme != "https" or not endpoint.hostname or endpoint.username is not None or endpoint.password is not None:
                raise ProtocolError(
                    "invalid_endpoint_scheme",
                    "https_json destination endpoint must be a credential-free https:// URL",
                )
        if item["credential_env"] is not None and (
            not isinstance(item["credential_env"], str) or not item["credential_env"].replace("_", "A").isalnum()
        ):
            raise ProtocolError("invalid_credential_label", "credential_env must be null or an environment variable name")
        if item["status"] not in {"active", "disabled"}:
            raise ProtocolError("invalid_destination_status", "destination status is invalid")
        if (
            not isinstance(item["max_payload_bytes"], int)
            or isinstance(item["max_payload_bytes"], bool)
            or item["max_payload_bytes"] < 0
            or item["max_payload_bytes"] > DEFAULT_MAX_BYTES
        ):
            raise ProtocolError("invalid_payload_limit", "max_payload_bytes must be within the fixed global limit")
    return document


def find_destination(policy: Dict[str, Any], destination_id: str, method: str) -> Dict[str, Any]:
    matches = [item for item in policy["destinations"] if item["destination_id"] == destination_id]
    if not matches:
        raise ProtocolError("destination_denied", "destination is not present in the deny-by-default policy")
    destination = matches[0]
    if destination["status"] != "active" or method not in destination["methods"]:
        raise ProtocolError("destination_denied", "destination or method is disabled")
    return destination


def stream_hash(path: Path, *, max_bytes: int) -> Tuple[bytes, str, int]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        raise ProtocolError("payload_open_failed", "immutable payload could not be opened safely") from exc
    digest = hashlib.sha256()
    data = bytearray()
    size = 0
    try:
        with os.fdopen(fd, "rb", closefd=False) as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise ProtocolError("payload_too_large", "payload exceeds destination policy limit")
                digest.update(chunk)
                data.extend(chunk)
    finally:
        os.close(fd)
    return bytes(data), digest.hexdigest(), size


def build_descriptor(payload_digest: str, byte_size: int, media_type: str, payload_class: str) -> Tuple[Dict[str, Any], str]:
    require_digest(payload_digest, "payload_digest")
    if not isinstance(byte_size, int) or isinstance(byte_size, bool) or byte_size < 0 or byte_size > DEFAULT_MAX_BYTES:
        raise ProtocolError("invalid_payload_size", "payload size must be within the fixed global limit")
    if not media_type or not payload_class:
        raise ProtocolError("invalid_descriptor", "media type and payload class must be non-empty")
    object_relpath = f".exocortex/local/protocol/payloads/sha256-{payload_digest}.payload"
    identity = {
        "payload_digest": payload_digest,
        "byte_size": byte_size,
        "media_type": media_type,
        "payload_class": payload_class,
        "object_relpath": object_relpath,
    }
    descriptor_id = "descriptor-" + json_digest(identity)
    descriptor = {
        "schema_version": DESCRIPTOR_VERSION,
        "kind": "immutable_payload_descriptor",
        "descriptor_id": descriptor_id,
        **identity,
        "created_at": isoformat(utc_now()),
        "immutable": True,
    }
    return descriptor, f".exocortex/local/protocol/descriptors/{descriptor_id}.json"


def inspect_payload(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = args.project_root.resolve(strict=True)
    capability_path, registry_path = resolve_identity_paths(project_root, args.capability, args.registry)
    payload_path = resolve_repo_path(project_root, args.payload, require_exists=True)
    consume_capability(
        capability_path=capability_path,
        registry_path=registry_path,
        request_id=args.request_id,
        check_kwargs={
            "operation": "inspect_egress_payload",
            "work_item_id": args.work_item_id,
            "work_item_revision": args.work_item_revision,
            "surface_id": args.surface_id,
            "executor_id": args.executor_id,
            "adapter_version": args.adapter_version,
            "guard_digest": current_guard_digest(),
            "role": "writer",
            "target_paths": [args.payload],
            "require_exact_paths": True,
        },
    )
    _, payload_digest, payload_size = stream_hash(payload_path, max_bytes=DEFAULT_MAX_BYTES)
    descriptor, descriptor_relpath = build_descriptor(payload_digest, payload_size, args.media_type, args.payload_class)
    return {
        "ok": True,
        "read_only": True,
        "payload_path": args.payload,
        "payload_digest": payload_digest,
        "byte_size": payload_size,
        "descriptor_id": descriptor["descriptor_id"],
        "descriptor_path": descriptor_relpath,
        "object_path": descriptor["object_relpath"],
    }


def create_json_exclusive(path: Path, value: Dict[str, Any], mode: int = 0o400) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(path), flags, mode)
    except FileExistsError:
        existing = validate_descriptor(load_json(path))
        stable_fields = (
            "schema_version",
            "kind",
            "descriptor_id",
            "payload_digest",
            "byte_size",
            "media_type",
            "payload_class",
            "object_relpath",
            "immutable",
        )
        if any(existing[field] != value[field] for field in stable_fields):
            raise ProtocolError("immutable_collision", "existing immutable descriptor differs")
        return existing
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.chmod(path, mode)
    return value


def stage_transaction_relpath(request_id: str) -> str:
    require_id(request_id, "request_id")
    return f"{TRANSACTION_PREFIX}egress-stage-{request_id}.json"


def stage_fault(point: str) -> None:
    if (
        os.environ.get("EXOCORTEX_TEST_MODE") == "1"
        and os.environ.get("EXOCORTEX_EGRESS_STAGE_FAULT") == point
    ):
        raise ProtocolError("injected_stage_fault", f"injected egress stage fault: {point}")


def validate_stage_transaction(document: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    require_exact_keys(
        document,
        [
            "schema_version",
            "kind",
            "request_id",
            "capability_id",
            "payload_digest",
            "byte_size",
            "payload_path",
            "object_relpath",
            "descriptor_relpath",
            "status",
            "updated_at",
        ],
        [],
        "egress stage transaction",
    )
    if document["schema_version"] != DESCRIPTOR_VERSION or document["kind"] != "egress_stage_transaction":
        raise ProtocolError("invalid_stage_transaction", "egress stage transaction uses the wrong schema")
    if document["status"] not in {"authorized", "object_written", "descriptor_written", "complete"}:
        raise ProtocolError("invalid_stage_transaction", "egress stage transaction status is invalid")
    for field, value in expected.items():
        if document.get(field) != value:
            raise ProtocolError("stage_transaction_mismatch", "existing egress stage transaction differs")
    return document


def write_stage_transaction(path: Path, document: Dict[str, Any], status: str) -> Dict[str, Any]:
    status_rank = {"authorized": 0, "object_written": 1, "descriptor_written": 2, "complete": 3}
    if status_rank[status] < status_rank[document["status"]]:
        raise ProtocolError("stage_status_regression", "egress stage transaction status cannot move backwards")
    if status == document["status"]:
        return document
    updated = dict(document)
    updated["status"] = status
    updated["updated_at"] = isoformat(utc_now())
    atomic_write_json(path, updated)
    return updated


def _stage_payload_serialized(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = args.project_root.resolve(strict=True)
    capability_path, registry_path = resolve_identity_paths(project_root, args.capability, args.registry)
    payload_path = resolve_repo_path(project_root, args.payload, require_exists=True)
    audit_path = resolve_repo_path(project_root, AUDIT_RELPATH)
    descriptor, descriptor_relpath = build_descriptor(
        args.expected_payload_digest,
        args.expected_byte_size,
        args.media_type,
        args.payload_class,
    )
    descriptor_path = resolve_repo_path(project_root, descriptor_relpath)
    object_relpath = descriptor["object_relpath"]
    object_path = resolve_repo_path(project_root, object_relpath)
    transaction_relpath = stage_transaction_relpath(args.request_id)
    transaction_path = resolve_repo_path(project_root, transaction_relpath)

    guard_kwargs = {
        "operation": "prepare_egress_payload",
        "work_item_id": args.work_item_id,
        "work_item_revision": args.work_item_revision,
        "surface_id": args.surface_id,
        "executor_id": args.executor_id,
        "adapter_version": args.adapter_version,
        "guard_digest": current_guard_digest(),
        "role": "writer",
        "target_paths": [args.payload, object_relpath, descriptor_relpath, transaction_relpath, AUDIT_RELPATH],
        "target_sha": args.expected_payload_digest,
        "payload_digest": args.expected_payload_digest,
        "require_exact_paths": True,
    }
    check_authority(
        capability_path=capability_path,
        registry_path=registry_path,
        request_id=args.request_id,
        allow_consumed_by_request_id=True,
        **guard_kwargs,
    )

    payload_bytes, actual_digest, actual_size = stream_hash(payload_path, max_bytes=DEFAULT_MAX_BYTES)
    if actual_digest != args.expected_payload_digest or actual_size != args.expected_byte_size:
        consume_capability(
            capability_path=capability_path,
            registry_path=registry_path,
            request_id=args.request_id,
            check_kwargs=guard_kwargs,
        )
        append_audit(
            audit_path,
            "authorization_denied",
            event_id=f"{args.request_id}:stage:digest-mismatch",
            code="payload_digest_mismatch",
        )
        raise ProtocolError("payload_digest_mismatch", "payload no longer matches the approved digest and size")

    capability = consume_capability(
        capability_path=capability_path,
        registry_path=registry_path,
        request_id=args.request_id,
        check_kwargs=guard_kwargs,
    )
    stage_fault("after_consumption")

    transaction_identity = {
        "request_id": args.request_id,
        "capability_id": capability["capability_id"],
        "payload_digest": actual_digest,
        "byte_size": actual_size,
        "payload_path": args.payload,
        "object_relpath": object_relpath,
        "descriptor_relpath": descriptor_relpath,
    }
    if transaction_path.exists():
        transaction = validate_stage_transaction(load_json(transaction_path), transaction_identity)
    else:
        transaction = {
            "schema_version": DESCRIPTOR_VERSION,
            "kind": "egress_stage_transaction",
            **transaction_identity,
            "status": "authorized",
            "updated_at": isoformat(utc_now()),
        }
        atomic_write_json(transaction_path, transaction)
    stage_fault("after_journal")

    status_rank = {"authorized": 0, "object_written": 1, "descriptor_written": 2, "complete": 3}
    if status_rank[transaction["status"]] < status_rank["object_written"]:
        object_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(str(object_path), flags, 0o400)
        except FileExistsError:
            _, existing_digest, existing_size = stream_hash(object_path, max_bytes=DEFAULT_MAX_BYTES)
            if (existing_digest, existing_size) != (actual_digest, actual_size):
                raise ProtocolError("object_collision", "existing immutable payload object differs")
        else:
            with os.fdopen(fd, "wb") as target:
                target.write(payload_bytes)
                target.flush()
                os.fsync(target.fileno())
            os.chmod(object_path, 0o400)
        transaction = write_stage_transaction(transaction_path, transaction, "object_written")
    else:
        if not object_path.is_file():
            raise ProtocolError("missing_stage_object", "egress stage journal references a missing immutable object")
        _, existing_digest, existing_size = stream_hash(object_path, max_bytes=DEFAULT_MAX_BYTES)
        if (existing_digest, existing_size) != (actual_digest, actual_size):
            raise ProtocolError("object_collision", "existing immutable payload object differs")
    stage_fault("after_object")

    if status_rank[transaction["status"]] < status_rank["descriptor_written"]:
        descriptor = create_json_exclusive(descriptor_path, descriptor)
        transaction = write_stage_transaction(transaction_path, transaction, "descriptor_written")
    else:
        if not descriptor_path.is_file():
            raise ProtocolError("missing_stage_descriptor", "egress stage journal references a missing descriptor")
        descriptor = create_json_exclusive(descriptor_path, descriptor)
    stage_fault("after_descriptor")
    append_audit(
        audit_path,
        "payload_staged",
        event_id=f"{args.request_id}:stage:complete",
        descriptor_id=descriptor["descriptor_id"],
        payload_digest=actual_digest,
        byte_size=actual_size,
    )
    stage_fault("after_audit")
    if transaction["status"] != "complete":
        write_stage_transaction(transaction_path, transaction, "complete")
    return {**descriptor, "descriptor_path": descriptor_relpath}


def stage_payload(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = args.project_root.resolve(strict=True)
    transaction_relpath = stage_transaction_relpath(args.request_id)
    transaction_path = resolve_repo_path(project_root, transaction_relpath)
    lock_path = resolve_repo_path(project_root, f"{transaction_relpath}.stage.lock")
    with exclusive_lock(lock_path):
        return _stage_payload_serialized(args)


def send_payload(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = args.project_root.resolve(strict=True)
    audit_path = resolve_repo_path(project_root, AUDIT_RELPATH)
    capability_path, registry_path = resolve_identity_paths(project_root, args.capability, args.registry)
    if not args.descriptor.startswith(DESCRIPTOR_PREFIX):
        raise ProtocolError("invalid_descriptor_path", "descriptor must be project-local immutable protocol state")
    if args.policy != POLICY_RELPATH:
        raise ProtocolError("invalid_policy_path", "external sync policy path is fixed by the public contract")
    descriptor_path = resolve_repo_path(project_root, args.descriptor, require_exists=True)
    policy_path = resolve_repo_path(project_root, args.policy, require_exists=True)
    try:
        descriptor = validate_descriptor(load_json(descriptor_path))
        policy = validate_policy(load_json(policy_path))
        policy_digest = json_digest(policy)
        destination = find_destination(policy, args.destination_id, args.method)
        if descriptor["byte_size"] > destination["max_payload_bytes"]:
            raise ProtocolError("payload_too_large", "descriptor exceeds destination policy limit")
        transport = destination["transport"]
        if transport == "fake":
            if os.environ.get("EXOCORTEX_TEST_MODE") != "1":
                raise ProtocolError("fake_transport_disabled", "fake transport is available only in explicit test mode")
            if args.fake_output is None:
                raise ProtocolError("missing_fake_output", "fake transport requires --fake-output")
            resolve_repo_path(project_root, args.fake_output)
        elif transport == "local_copy":
            if args.allow_external_copy is not True:
                raise ProtocolError("external_copy_disabled", "local copy requires explicit --allow-external-copy")
        elif args.allow_network is not True:
            raise ProtocolError("network_disabled", "HTTPS transport requires explicit --allow-network")
        target_paths = [args.descriptor, AUDIT_RELPATH]
        if destination["transport"] == "fake" and args.fake_output is not None:
            target_paths.append(args.fake_output)
        guard_kwargs = {
            "operation": "external_sync",
            "work_item_id": args.work_item_id,
            "work_item_revision": args.work_item_revision,
            "surface_id": args.surface_id,
            "executor_id": args.executor_id,
            "adapter_version": args.adapter_version,
            "guard_digest": current_guard_digest(),
            "role": "egress",
            "target_paths": target_paths,
            "target_sha": policy_digest,
            "destination_id": args.destination_id,
            "method": args.method,
            "payload_descriptor_id": descriptor["descriptor_id"],
            "payload_digest": descriptor["payload_digest"],
            "require_exact_paths": True,
        }
        check_authority(
            capability_path=capability_path,
            registry_path=registry_path,
            request_id=args.request_id,
            **guard_kwargs,
        )
    except ProtocolError as exc:
        append_audit(audit_path, "authorization_denied", event_id=f"{args.request_id}:metadata:{exc.code}", code=exc.code)
        raise

    append_audit(audit_path, "descriptor_resolved", event_id=f"{args.request_id}:descriptor", descriptor_id=descriptor["descriptor_id"])
    append_audit(
        audit_path,
        "authorization_metadata_checked",
        event_id=f"{args.request_id}:metadata",
        capability_id=load_json(capability_path)["capability_id"],
    )

    payload_path = resolve_repo_path(project_root, descriptor["object_relpath"], require_exists=True)
    append_audit(audit_path, "payload_open_attempt_after_authorization", event_id=f"{args.request_id}:payload-open", descriptor_id=descriptor["descriptor_id"])
    payload_bytes, payload_digest, payload_size = stream_hash(
        payload_path,
        max_bytes=destination.get("max_payload_bytes", DEFAULT_MAX_BYTES),
    )
    if payload_digest != descriptor["payload_digest"] or payload_size != descriptor["byte_size"]:
        append_audit(audit_path, "authorization_denied", event_id=f"{args.request_id}:payload-digest-mismatch", code="payload_digest_mismatch")
        raise ProtocolError("payload_digest_mismatch", "immutable payload does not match its approved descriptor")
    append_audit(
        audit_path,
        "payload_digest_verified",
        event_id=f"{args.request_id}:payload-digest",
        payload_digest=payload_digest,
        byte_size=payload_size,
    )

    current_policy = validate_policy(load_json(policy_path))
    if json_digest(current_policy) != policy_digest:
        append_audit(audit_path, "authorization_denied", event_id=f"{args.request_id}:policy-changed", code="policy_changed")
        raise ProtocolError("policy_changed", "destination policy changed before transport")
    find_destination(current_policy, args.destination_id, args.method)
    check_authority(
        capability_path=capability_path,
        registry_path=registry_path,
        request_id=args.request_id,
        **guard_kwargs,
    )

    credential: Optional[str] = None
    credential_env = destination["credential_env"]
    if credential_env:
        credential = os.environ.get(credential_env)
        if not credential:
            append_audit(audit_path, "authorization_denied", event_id=f"{args.request_id}:credential-unavailable", code="credential_unavailable")
            raise ProtocolError("credential_unavailable", "authorized destination credential is unavailable")
    append_audit(
        audit_path,
        "credential_lookup_after_digest",
        event_id=f"{args.request_id}:credential",
        credential_present=bool(credential_env),
    )

    if (
        os.environ.get("EXOCORTEX_TEST_MODE") == "1"
        and os.environ.get("EXOCORTEX_TEST_REVOKE_AFTER_CREDENTIAL") == "1"
    ):
        revoked = load_json(capability_path)
        revoked["status"] = {
            "state": "revoked",
            "revoked_at": isoformat(utc_now()),
            "consumed_at": None,
            "consumed_by_request_id": None,
        }
        atomic_write_json(capability_path, revoked)
        append_audit(
            audit_path,
            "test_revocation_after_credential",
            event_id=f"{args.request_id}:test-revocation",
        )

    if (
        os.environ.get("EXOCORTEX_TEST_MODE") == "1"
        and os.environ.get("EXOCORTEX_TEST_CHANGE_POLICY_AFTER_CREDENTIAL") == "1"
    ):
        changed_policy = load_json(policy_path)
        for item in changed_policy["destinations"]:
            if item["destination_id"] == args.destination_id:
                item["status"] = "disabled"
        atomic_write_json(policy_path, changed_policy)
        append_audit(
            audit_path,
            "test_policy_change_after_credential",
            event_id=f"{args.request_id}:test-policy-change",
        )

    final_policy = validate_policy(load_json(policy_path))
    if json_digest(final_policy) != policy_digest:
        append_audit(
            audit_path,
            "authorization_denied",
            event_id=f"{args.request_id}:policy-changed-after-credential",
            code="policy_changed",
        )
        raise ProtocolError("policy_changed", "destination policy changed after credential lookup")
    final_destination = find_destination(final_policy, args.destination_id, args.method)
    if final_destination != destination:
        raise ProtocolError("policy_changed", "destination policy entry changed after credential lookup")

    consume_capability(
        capability_path=capability_path,
        registry_path=registry_path,
        request_id=args.request_id,
        check_kwargs=guard_kwargs,
    )

    append_audit(
        audit_path,
        "transport_initialized_after_credential",
        event_id=f"{args.request_id}:transport-init",
        transport=transport,
        destination_id=args.destination_id,
    )
    if transport == "fake":
        fake_path = resolve_repo_path(project_root, args.fake_output)
        atomic_write_json(
            fake_path,
            {
                "destination_id": args.destination_id,
                "method": args.method,
                "descriptor_id": descriptor["descriptor_id"],
                "payload_digest": payload_digest,
                "byte_size": payload_size,
            },
        )
        status = "fake_delivered"
    elif transport == "local_copy":
        destination_dir = Path(destination["endpoint"]).expanduser()
        destination_dir.mkdir(parents=True, exist_ok=True)
        target = destination_dir / f"{descriptor['descriptor_id']}.payload"
        with target.open("xb") as handle:
            handle.write(payload_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        status = "copied"
    else:
        headers = {"Content-Type": descriptor["media_type"]}
        if credential is not None:
            headers["Authorization"] = f"Bearer {credential}"
        request = urllib.request.Request(
            destination["endpoint"],
            data=payload_bytes,
            headers=headers,
            method=args.method,
        )
        try:
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                response.read(1)
                status = f"http_{response.status}"
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise ProtocolError("transport_failed", "authorized transport failed; automatic retry is disabled") from exc
    append_audit(
        audit_path,
        "transport_attempted",
        event_id=f"{args.request_id}:transport-attempt",
        destination_id=args.destination_id,
        status=status,
    )
    return {
        "ok": True,
        "status": status,
        "destination_id": args.destination_id,
        "descriptor_id": descriptor["descriptor_id"],
        "payload_digest": payload_digest,
    }


def verify_audit(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = args.project_root.resolve(strict=True)
    audit_path = resolve_repo_path(project_root, AUDIT_RELPATH, require_exists=True)
    sequence, final_hash, event_ids = validate_audit_records(audit_path)
    return {
        "ok": True,
        "record_count": sequence,
        "final_record_hash": final_hash,
        "unique_event_ids": len(event_ids),
    }


def add_identity_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--capability", required=True, help="project-relative capability path")
    parser.add_argument("--registry", default=REGISTRY_RELPATH, help="fixed project-local executor-registry path")
    parser.add_argument("--work-item-id", required=True)
    parser.add_argument("--work-item-revision", type=int, required=True)
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--surface-id", required=True)
    parser.add_argument("--executor-id", required=True)
    parser.add_argument("--adapter-version", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser("inspect", help="authorized local immutable-payload proposal")
    add_identity_arguments(inspect)
    inspect.add_argument("--payload", required=True, help="project-relative source payload")
    inspect.add_argument("--payload-class", required=True)
    inspect.add_argument("--media-type", default="application/octet-stream")

    stage = commands.add_parser("stage")
    add_identity_arguments(stage)
    stage.add_argument("--payload", required=True, help="project-relative source payload")
    stage.add_argument("--payload-class", required=True)
    stage.add_argument("--media-type", default="application/octet-stream")
    stage.add_argument("--expected-payload-digest", required=True)
    stage.add_argument("--expected-byte-size", type=int, required=True)

    send = commands.add_parser("send")
    add_identity_arguments(send)
    send.add_argument("--descriptor", required=True, help="project-relative immutable descriptor path")
    send.add_argument("--policy", default=POLICY_RELPATH, help="fixed project-local destination-policy path")
    send.add_argument("--destination-id", required=True)
    send.add_argument("--method", choices=["POST", "PUT", "COPY"], required=True)
    send.add_argument("--fake-output")
    send.add_argument("--allow-network", action="store_true")
    send.add_argument("--allow-external-copy", action="store_true")
    send.add_argument("--timeout", type=int, default=30)

    verify = commands.add_parser("verify-audit", help="verify the fixed project-local egress audit chain")
    verify.add_argument("--project-root", type=Path, required=True)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_payload(args)
        elif args.command == "stage":
            result = stage_payload(args)
        elif args.command == "verify-audit":
            result = verify_audit(args)
        else:
            result = send_payload(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except ProtocolError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
