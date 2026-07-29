#!/usr/bin/env python3
"""Provider-neutral work-item orchestration and guarded lifecycle mutations."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
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
    isoformat,
    json_digest,
    load_json,
    parse_timestamp,
    require_exact_keys,
    require_id,
    resolve_repo_path,
    utc_now,
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

REGISTRY_RELPATH = ".exocortex/control/EXECUTOR_REGISTRY.json"
CAPABILITY_PREFIX = ".exocortex/local/protocol/capabilities/"
WORK_ITEM_PREFIX = ".exocortex/work-items/"
EXACT_SHA_RE = re.compile(r"^(?:[a-f0-9]{40}|[a-f0-9]{64})$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
MAX_ROUTE_CLOCK_SKEW_SECONDS = 60


def stable_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:32]}"


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
        ["title", "type", "retrospectives"],
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


def add_idempotency(document: Dict[str, Any], request_id: str, operation: str, result_id: str) -> None:
    document["idempotency"].append(
        {
            "request_id": request_id,
            "operation": operation,
            "result_id": result_id,
            "accepted_at": isoformat(utc_now()),
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


def finalize_transaction(path: Path, journal: Dict[str, Any]) -> None:
    finalized = copy.deepcopy(journal)
    finalized["status"] = "finalized"
    finalized["finalized_at"] = isoformat(utc_now())
    atomic_write_json(path, finalized)


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
    mutate: Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str]],
) -> Dict[str, Any]:
    require_id(request_id, "request_id")
    work_item_path = resolve_repo_path(project_root, work_item_relpath, require_exists=True)
    capability_path = resolve_repo_path(project_root, capability_relpath, require_exists=True)
    registry_path = resolve_repo_path(project_root, registry_relpath, require_exists=True)
    journal_path = transaction_path(project_root, request_id)
    lock_path = resolve_repo_path(project_root, f".exocortex/local/protocol/locks/{work_item_path.name}.lock")

    with exclusive_lock(lock_path):
        current = validate_work_item(load_json(work_item_path))
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
                    "status",
                    "created_at",
                ],
                ["finalized_at"],
                "transaction journal",
            )
            if journal["request_id"] != request_id or journal["operation"] != operation:
                raise ProtocolError("transaction_conflict", "existing transaction does not match this request")
            if journal["status"] == "finalized":
                raise ProtocolError("transaction_inconsistent", "finalized transaction lacks idempotency state")
            capability = load_json(capability_path)
            if capability.get("capability_id") != journal["capability_id"]:
                raise ProtocolError("transaction_capability_conflict", "transaction capability does not match the current capability file")
            consume_capability(
                capability_path=capability_path,
                registry_path=registry_path,
                request_id=request_id,
                check_kwargs=authority_kwargs,
            )
            maybe_fault("after_capability_consumed")
            current_digest = json_digest(current)
            if current_digest == journal["before_digest"]:
                after_document = validate_work_item(journal["after_document"])
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
        after_document, result_id = mutate(copy.deepcopy(current))
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
            "status": "intent",
            "created_at": isoformat(utc_now()),
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


def mutation_for_reserve(args: argparse.Namespace) -> Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        if document["lifecycle"]["state"] in {"captured", "triaged", "refined", "done"}:
            raise ProtocolError("wrong_state", "writer reservation is not available in this lifecycle state")
        reservation = document["lane"]["reservation"]
        if reservation["status"] == "active":
            if parse_timestamp(reservation["lease_expires_at"], "lease_expires_at") > utc_now():
                raise ProtocolError("writer_conflict", "another writer reservation is active")
            document["lifecycle"]["attempt"] += 1
        expires = parse_timestamp(args.lease_expires_at, "lease_expires_at")
        if expires <= utc_now():
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
        add_idempotency(document, args.request_id, "reserve_writer", result_id)
        return document, result_id

    return mutate


def mutation_for_transition(args: argparse.Namespace) -> Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        current = document["lifecycle"]["state"]
        key = (current, args.to_state)
        if key not in TRANSITIONS:
            raise ProtocolError("invalid_transition", f"transition {current} -> {args.to_state} is not allowed")
        if args.from_state is not None and args.from_state != current:
            raise ProtocolError("stale_state", "declared from-state is stale")
        reservation = document["lane"]["reservation"]
        if args.to_state in {"developing", "developer_verified", "independent_review", "qa_sit", "uat_ready"}:
            if reservation["status"] != "active":
                raise ProtocolError("missing_writer", "this transition requires an active writer reservation")
            if reservation["surface_id"] != args.surface_id or reservation["executor_id"] != args.executor_id:
                raise ProtocolError("writer_mismatch", "current executor does not own the writer reservation")
            if parse_timestamp(reservation["lease_expires_at"], "lease_expires_at") <= utc_now():
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
        checkpoint_eligible = TRANSITIONS[key]
        transition_id = stable_id("transition", document["id"], args.request_id, current, args.to_state)
        document["transitions"].append(
            {
                "id": transition_id,
                "request_id": args.request_id,
                "operation": args.transition_name,
                "from": current,
                "to": args.to_state,
                "accepted_at": isoformat(utc_now()),
                "capability_id": args.capability_id_hint,
                "checkpoint_eligible": checkpoint_eligible,
                "evidence": list(args.evidence),
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
                        "created_at": isoformat(utc_now()),
                        "local_only": True,
                    }
                )
        add_idempotency(document, args.request_id, "transition_work_item", transition_id)
        return document, transition_id

    return mutate


def mutation_for_release(args: argparse.Namespace) -> Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
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
        add_idempotency(document, args.request_id, "release_writer", result_id)
        return document, result_id

    return mutate


def mutation_for_handoff(args: argparse.Namespace) -> Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        handoff_id = stable_id("handoff", document["id"], args.request_id)
        if not isinstance(args.candidate_sha, str) or not EXACT_SHA_RE.fullmatch(args.candidate_sha):
            raise ProtocolError("invalid_candidate_sha", "candidate SHA must be an exact Git or SHA-256 digest")
        if not args.evidence_hash or any(not SHA256_RE.fullmatch(value) for value in args.evidence_hash):
            raise ProtocolError("invalid_handoff_evidence", "handoff requires SHA-256 evidence hashes")
        document["handoffs"].append(
            {
                "id": handoff_id,
                "request_id": args.request_id,
                "created_at": isoformat(utc_now()),
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
        add_idempotency(document, args.request_id, "create_handoff", handoff_id)
        return document, handoff_id

    return mutate


def mutation_for_retrospective(args: argparse.Namespace) -> Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str]]:
    def mutate(document: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
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
        add_idempotency(document, args.request_id, "record_retrospective", retrospective_id)
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


def add_mutation_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--work-item", required=True)
    parser.add_argument("--capability", required=True, help="project-relative path under .exocortex/local/protocol/capabilities/")
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

    reserve = commands.add_parser("reserve")
    add_mutation_args(reserve)
    reserve.add_argument("--writer", required=True)
    reserve.add_argument("--lease-expires-at", required=True)

    transition = commands.add_parser("transition")
    add_mutation_args(transition)
    transition.add_argument("--from-state")
    transition.add_argument("--to-state", choices=STATES, required=True)
    transition.add_argument("--transition-name", required=True)
    transition.add_argument("--evidence", action="append", default=[])
    transition.add_argument("--reviewer-surface-id")
    transition.add_argument("--reviewer-executor-id")
    transition.add_argument("--review-evidence-hash")
    transition.add_argument("--review-transition-id")

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


def run_mutation(args: argparse.Namespace) -> Dict[str, Any]:
    project_root = args.project_root.resolve(strict=True)
    if not args.capability.startswith(CAPABILITY_PREFIX):
        raise ProtocolError("invalid_capability_path", "capability must be project-local protocol state")
    if args.registry != REGISTRY_RELPATH:
        raise ProtocolError("invalid_registry_path", "executor registry path is fixed by the public contract")
    if not args.work_item.startswith(WORK_ITEM_PREFIX):
        raise ProtocolError("invalid_work_item_path", "mutable work items must use the project-local runtime work-item directory")
    capability_path = resolve_repo_path(project_root, args.capability, require_exists=True)
    registry_path = resolve_repo_path(project_root, args.registry, require_exists=True)
    capability_document = load_json(capability_path)
    if args.command in {"transition", "handoff"}:
        args.capability_id_hint = require_id(capability_document.get("capability_id"), "capability_id")
    if args.command == "handoff":
        args.capability_digest_hint = json_digest(capability_document)
        args.registry_digest_hint = json_digest(load_json(registry_path))
    if args.command == "retrospective":
        args.proposal = resolve_repo_path(project_root, args.proposal, require_exists=True)
    if args.command == "transition":
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
        return guarded_mutation(operation="transition_work_item", mutate=mutation_for_transition(args), **common)
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
            result = orient(args.project_root.resolve(strict=True), args.work_item)
        elif args.command == "route":
            root = args.project_root.resolve(strict=True)
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
        else:
            result = run_mutation(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except ProtocolError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
