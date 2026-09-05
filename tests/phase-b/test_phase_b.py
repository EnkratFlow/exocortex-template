#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Dict, List, Optional
import unittest


TEMPLATE = Path(__file__).resolve().parents[2]
AUTHORITY = TEMPLATE / ".exocortex/scripts/authority_guard.py"
ORCHESTRATOR = TEMPLATE / ".exocortex/scripts/orchestrate_work_item.py"
MODEL_REGISTRY = TEMPLATE / ".exocortex/scripts/model_registry.py"
RECONCILIATION = TEMPLATE / ".exocortex/scripts/prepare_update_reconciliation.py"
EGRESS = TEMPLATE / ".exocortex/scripts/egress_guard.py"
ADAPTER_GENERATOR = TEMPLATE / ".exocortex/scripts/generate_command_adapters.py"
ADAPTER_MATRIX = TEMPLATE / ".exocortex/provider-adapters.json"
ADAPTER_SCHEMA = TEMPLATE / ".exocortex/schemas/provider-adapter-matrix.schema.json"
ADAPTER_TEST_MATRIX = TEMPLATE / "tests/phase-b/provider-adapter-matrix.json"
REGISTRY_REL = ".exocortex/control/EXECUTOR_REGISTRY.json"
WORK_REL = ".exocortex/work-items/TEST-WORK-001.json"
AUDIT_REL = ".exocortex/local/protocol/audit/egress.jsonl"
BASE_SHA = "a" * 40


def canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def stable_protocol_id(prefix: str, *parts: str) -> str:
    material = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(material).hexdigest()[:32]}"


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def materialize_credential_blind_candidate(source: Path, destination: Path) -> None:
    """Build a public code-plane fixture without reading credential-adjacent files."""

    excluded = {".exocortex/.env.example", ".exocortex/key-registry.json"}
    manifest_paths: list[str] = []
    for line in (source / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"[0-9a-f]{64}  ([^/].*)", line)
        if match is None:
            raise AssertionError("malformed template checksum fixture")
        relative = match.group(1)
        parts = Path(relative).parts
        if relative in manifest_paths or "." in parts or ".." in parts:
            raise AssertionError("unsafe template checksum fixture")
        if relative not in excluded:
            manifest_paths.append(relative)

    destination.mkdir()
    for relative in manifest_paths:
        if relative == "FILEMODES":
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)

    mode_lines: list[str] = []
    for line in (source / "FILEMODES").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(0644|0755)  ([^/].*)", line)
        if match is None:
            raise AssertionError("malformed template mode fixture")
        if match.group(2) not in excluded:
            mode_lines.append(line)
    (destination / "FILEMODES").write_text(
        "".join(f"{line}\n" for line in mode_lines), encoding="utf-8"
    )
    os.chmod(destination / "FILEMODES", 0o644)

    (destination / "SHA256SUMS").write_text(
        "".join(
            f"{file_digest(destination / relative)}  {relative}\n"
            for relative in manifest_paths
        ),
        encoding="utf-8",
    )
    os.chmod(destination / "SHA256SUMS", 0o644)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stage_transaction(request_id: str) -> str:
    return f".exocortex/local/protocol/transactions/egress-stage-{request_id}.json"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(
    command: List[str],
    *,
    env: Optional[Dict[str, str]] = None,
    check: bool = False,
    cwd: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    current = os.environ.copy()
    current["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        current.update(env)
    result = subprocess.run(command, text=True, capture_output=True, env=current, check=False, cwd=cwd)
    if check and result.returncode != 0:
        raise AssertionError(f"command failed ({result.returncode}): {result.stdout}\n{result.stderr}")
    return result


class ProtocolFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="exo-phase-b-")
        self.root = Path(self.temp.name)
        (self.root / ".exocortex/control").mkdir(parents=True)
        (self.root / ".exocortex/work-items").mkdir(parents=True)
        self.guard_digest = file_digest(AUTHORITY)
        self.surface = "test-surface"
        self.executor = "test-executor"
        self.adapter = "test-v1"
        self.registry = {
            "schema_version": "public-v2",
            "kind": "executor_registry",
            "registry_version": 1,
            "default_role": "read_only",
            "executors": [
                {
                    "surface_id": self.surface,
                    "executor_id": self.executor,
                    "adapter_version": self.adapter,
                    "guard_digest": self.guard_digest,
                    "roles": ["read_only", "writer", "egress"],
                    "status": "active",
                    "registered_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2099-01-01T00:00:00Z",
                    "revoked_at": None,
                }
            ],
        }
        write_json(self.root / REGISTRY_REL, self.registry)
        self.work = {
            "schema_version": "public-v2",
            "kind": "delivery_work_item",
            "id": "TEST-WORK-001",
            "revision": 0,
            "title": "Protocol fixture",
            "type": "maintenance",
            "lifecycle": {"state": "ready", "attempt": 0, "blocked": None},
            "designated_base": {"sha": BASE_SHA, "source": "fixture"},
            "lane": {
                "allowed_paths": [WORK_REL],
                "reservation": {
                    "status": "none",
                    "writer": None,
                    "surface_id": None,
                    "executor_id": None,
                    "lease_expires_at": None,
                    "version": 0,
                },
            },
            "acceptance_criteria": [],
            "transitions": [],
            "checkpoints": [],
            "handoffs": [],
            "idempotency": [],
        }
        write_json(self.root / WORK_REL, self.work)

    def close(self) -> None:
        self.temp.cleanup()

    def register_reviewer(self) -> tuple[str, str]:
        surface_id = "review-surface"
        executor_id = "review-executor"
        self.registry["executors"].append(
            {
                "surface_id": surface_id,
                "executor_id": executor_id,
                "adapter_version": "review-v1",
                "guard_digest": self.guard_digest,
                "roles": ["read_only"],
                "status": "active",
                "registered_at": "2026-01-01T00:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "revoked_at": None,
            }
        )
        write_json(self.root / REGISTRY_REL, self.registry)
        return surface_id, executor_id

    def capability(
        self,
        name: str,
        operation: str,
        revision: int,
        paths: List[str],
        **scope: object,
    ) -> str:
        rel = f".exocortex/local/protocol/capabilities/{name}.json"
        document = {
            "schema_version": "public-v2",
            "kind": "approval_capability",
            "capability_id": f"cap-{name}",
            "work_item_id": "TEST-WORK-001",
            "work_item_revision": revision,
            "operation": operation,
            "scope": {"allowed_paths": paths, **scope},
            "executor": {
                "surface_id": self.surface,
                "executor_id": self.executor,
                "adapter_version": self.adapter,
                "guard_digest": self.guard_digest,
                "registry_version": 1,
            },
            "approval": {
                "approved_by": "fixture-human",
                "accepted_at": "2026-01-01T00:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "one_time": True,
                "summary": "fictional deterministic test authority",
            },
            "status": {
                "state": "active",
                "revoked_at": None,
                "consumed_at": None,
                "consumed_by_request_id": None,
            },
        }
        write_json(self.root / rel, document)
        return rel

    def orchestration(
        self,
        command: str,
        capability: str,
        request: str,
        extra: Optional[List[str]] = None,
        *,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        extra = extra or []
        return run(
            [
                "python3", str(ORCHESTRATOR), command,
                "--project-root", str(self.root),
                "--work-item", WORK_REL,
                "--capability", capability,
                "--request-id", request,
                "--surface-id", self.surface,
                "--executor-id", self.executor,
                "--adapter-version", self.adapter,
                *extra,
            ],
            env=env,
        )

    def egress(
        self,
        command: str,
        capability: str,
        request: str,
        extra: Optional[List[str]] = None,
        *,
        env: Optional[Dict[str, str]] = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        extra = extra or []
        return run(
            [
                "python3", str(EGRESS), command,
                "--project-root", str(self.root),
                "--capability", capability,
                "--work-item-id", "TEST-WORK-001",
                "--work-item-revision", "0",
                "--request-id", request,
                "--surface-id", self.surface,
                "--executor-id", self.executor,
                "--adapter-version", self.adapter,
                *extra,
            ],
            env=env,
            check=check,
        )


class AuthorityAndLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = ProtocolFixture()

    def tearDown(self) -> None:
        self.fx.close()

    def prepare_developer_verified(self) -> None:
        work = json.loads((self.fx.root / WORK_REL).read_text())
        work["lifecycle"]["state"] = "developer_verified"
        work["lane"]["reservation"] = {
            "status": "active",
            "writer": "fixture-writer",
            "surface_id": self.fx.surface,
            "executor_id": self.fx.executor,
            "lease_expires_at": "2099-01-01T00:00:00Z",
            "version": 1,
        }
        write_json(self.fx.root / WORK_REL, work)

    def test_guard_digest_and_protocol_paths_fail_closed(self) -> None:
        cap = self.fx.capability("guard", "reserve_writer", 0, [WORK_REL], target_sha=BASE_SHA)
        base = [
            "python3", str(AUTHORITY), "check", "--project-root", str(self.fx.root),
            "--capability", cap, "--operation", "reserve_writer",
            "--work-item-id", "TEST-WORK-001", "--work-item-revision", "0",
            "--request-id", "guard-request", "--surface-id", self.fx.surface,
            "--executor-id", self.fx.executor, "--adapter-version", self.fx.adapter,
            "--role", "writer", "--target-sha", BASE_SHA, "--target-path", WORK_REL,
        ]
        wrong = run([*base, "--guard-digest", "0" * 64])
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("guard_digest_mismatch", wrong.stdout)
        alternate = self.fx.root / "alternate-registry.json"
        write_json(alternate, self.fx.registry)
        escaped = run([*base, "--guard-digest", self.fx.guard_digest, "--registry", "alternate-registry.json"])
        self.assertNotEqual(escaped.returncode, 0)
        self.assertIn("invalid_registry_path", escaped.stdout)

    def test_exact_path_set_rejects_partial_capability_scope(self) -> None:
        extra_rel = ".exocortex/SECOND-PATH.md"
        cap = self.fx.capability("exact-paths", "reserve_writer", 0, [WORK_REL, extra_rel], target_sha=BASE_SHA)
        result = run(
            [
                "python3", str(AUTHORITY), "check", "--project-root", str(self.fx.root),
                "--capability", cap, "--operation", "reserve_writer",
                "--work-item-id", "TEST-WORK-001", "--work-item-revision", "0",
                "--request-id", "exact-paths", "--surface-id", self.fx.surface,
                "--executor-id", self.fx.executor, "--adapter-version", self.fx.adapter,
                "--guard-digest", self.fx.guard_digest, "--role", "writer",
                "--target-sha", BASE_SHA, "--target-path", WORK_REL,
                "--require-exact-path-set",
            ]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("path_set_mismatch", result.stdout)
        self.assertEqual(json.loads((self.fx.root / cap).read_text())["status"]["state"], "active")

    def test_orchestration_rejects_surplus_capability_paths(self) -> None:
        cap = self.fx.capability(
            "orchestration-surplus",
            "reserve_writer",
            0,
            [WORK_REL, ".exocortex/UNRELATED.md"],
            target_sha=BASE_SHA,
        )
        result = self.fx.orchestration(
            "reserve",
            cap,
            "orchestration-surplus",
            ["--writer", "writer", "--lease-expires-at", "2099-01-01T00:00:00Z"],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("path_set_mismatch", result.stdout)
        self.assertEqual(json.loads((self.fx.root / cap).read_text())["status"]["state"], "active")
        self.assertEqual(json.loads((self.fx.root / WORK_REL).read_text())["lifecycle"]["state"], "ready")

    def test_runtime_rejects_historical_transition_pair_drift(self) -> None:
        work = json.loads((self.fx.root / WORK_REL).read_text())
        work["transitions"].append(
            {
                "id": "transition-invalid-pair",
                "request_id": "invalid-pair",
                "operation": "invalid-pair",
                "from": "captured",
                "to": "done",
                "accepted_at": "2026-01-01T00:00:00Z",
                "capability_id": "cap-invalid-pair",
                "checkpoint_eligible": True,
                "evidence": ["fixture"],
            }
        )
        write_json(self.fx.root / WORK_REL, work)
        result = run(
            ["python3", str(ORCHESTRATOR), "orient", "--project-root", str(self.fx.root), "--work-item", WORK_REL]
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid_transition_record", result.stdout)

    def test_32_writer_race_has_one_winner_and_no_checkpoint(self) -> None:
        capabilities = [
            self.fx.capability(f"race-{i}", "reserve_writer", 0, [WORK_REL], target_sha=BASE_SHA)
            for i in range(32)
        ]

        def attempt(i: int) -> int:
            result = self.fx.orchestration(
                "reserve", capabilities[i], f"race-request-{i}",
                ["--writer", f"writer-{i}", "--lease-expires-at", "2099-01-01T00:00:00Z"],
            )
            return result.returncode

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(attempt, range(32)))
        self.assertEqual(results.count(0), 1)
        work = json.loads((self.fx.root / WORK_REL).read_text())
        self.assertEqual(work["lifecycle"]["state"], "reserved")
        self.assertEqual(work["revision"], 1)
        self.assertEqual(work["checkpoints"], [])
        consumed = 0
        for rel in capabilities:
            if json.loads((self.fx.root / rel).read_text())["status"]["state"] == "consumed":
                consumed += 1
        self.assertEqual(consumed, 1)

    def test_fault_recovery_and_idempotent_checkpoint(self) -> None:
        cap = self.fx.capability("reserve", "reserve_writer", 0, [WORK_REL], target_sha=BASE_SHA)
        self.assertEqual(
            self.fx.orchestration("reserve", cap, "reserve-request", ["--writer", "writer", "--lease-expires-at", "2099-01-01T00:00:00Z"]).returncode,
            0,
        )
        trans = self.fx.capability("transition", "transition_work_item", 1, [WORK_REL], target_sha=BASE_SHA)
        args = [
            "python3", str(ORCHESTRATOR), "transition", "--project-root", str(self.fx.root),
            "--work-item", WORK_REL, "--capability", trans, "--request-id", "transition-request",
            "--surface-id", self.fx.surface, "--executor-id", self.fx.executor,
            "--adapter-version", self.fx.adapter, "--to-state", "developing",
            "--transition-name", "start-development", "--evidence", "fixture",
        ]
        fault = run(args, env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_intent"})
        self.assertNotEqual(fault.returncode, 0)
        self.assertEqual(run(args).returncode, 0)
        self.assertEqual(run(args).returncode, 0)
        work = json.loads((self.fx.root / WORK_REL).read_text())
        self.assertEqual(work["lifecycle"]["state"], "developing")
        self.assertEqual(len(work["checkpoints"]), 1)
        self.assertEqual(len(work["transitions"]), 1)

    def test_consumed_recovery_clock_is_bounded(self) -> None:
        reserve = self.fx.capability("clock-reserve", "reserve_writer", 0, [WORK_REL], target_sha=BASE_SHA)
        self.assertEqual(
            self.fx.orchestration(
                "reserve",
                reserve,
                "clock-reserve-request",
                ["--writer", "writer", "--lease-expires-at", "2099-01-01T00:00:00Z"],
            ).returncode,
            0,
        )
        transition = self.fx.capability(
            "clock-transition",
            "transition_work_item",
            1,
            [WORK_REL],
            target_sha=BASE_SHA,
        )
        command = [
            "python3", str(ORCHESTRATOR), "transition", "--project-root", str(self.fx.root),
            "--work-item", WORK_REL, "--capability", transition,
            "--request-id", "clock-transition-request",
            "--surface-id", self.fx.surface, "--executor-id", self.fx.executor,
            "--adapter-version", self.fx.adapter, "--to-state", "developing",
            "--transition-name", "clock-bounded-development", "--evidence", "fixture",
        ]
        fault = run(
            command,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_capability_consumed"},
        )
        self.assertNotEqual(fault.returncode, 0)
        capability_path = self.fx.root / transition
        capability = json.loads(capability_path.read_text(encoding="utf-8"))
        original_consumed_at = capability["status"]["consumed_at"]
        for invalid_time in ("2026-01-01T00:00:00Z", "2099-01-01T00:00:00Z"):
            capability["status"]["consumed_at"] = invalid_time
            write_json(capability_path, capability)
            rejected = run(command)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("invalid_recovery_timestamp", rejected.stdout)
        capability["status"]["consumed_at"] = original_consumed_at
        write_json(capability_path, capability)
        self.assertEqual(run(command).returncode, 0)

    def test_handoff_recovers_after_capability_consumption(self) -> None:
        self.prepare_developer_verified()
        capability = self.fx.capability(
            "handoff-recovery",
            "create_handoff",
            0,
            [WORK_REL],
            target_sha=BASE_SHA,
        )
        arguments = [
            "--candidate-sha", BASE_SHA,
            "--evidence-hash", "e" * 64,
            "--first-verification", "Verify the fictional recovered handoff.",
        ]
        fault = self.fx.orchestration(
            "handoff",
            capability,
            "handoff-recovery-request",
            arguments,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_capability_consumed"},
        )
        self.assertNotEqual(fault.returncode, 0)
        self.assertEqual(
            json.loads((self.fx.root / capability).read_text(encoding="utf-8"))["status"]["state"],
            "consumed",
        )
        recovered = self.fx.orchestration(
            "handoff",
            capability,
            "handoff-recovery-request",
            arguments,
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        replay = self.fx.orchestration(
            "handoff",
            capability,
            "handoff-recovery-request",
            arguments,
        )
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
        work = json.loads((self.fx.root / WORK_REL).read_text(encoding="utf-8"))
        self.assertEqual(len(work["handoffs"]), 1)

    def test_invalid_transition_does_not_consume_or_checkpoint(self) -> None:
        cap = self.fx.capability("invalid", "transition_work_item", 0, [WORK_REL], target_sha=BASE_SHA)
        result = self.fx.orchestration(
            "transition", cap, "invalid-request",
            ["--to-state", "done", "--transition-name", "skip-everything"],
        )
        self.assertNotEqual(result.returncode, 0)
        work = json.loads((self.fx.root / WORK_REL).read_text())
        self.assertEqual(work["revision"], 0)
        self.assertEqual(work["checkpoints"], [])
        self.assertEqual(json.loads((self.fx.root / cap).read_text())["status"]["state"], "active")

    def test_independent_review_cannot_be_skipped(self) -> None:
        self.prepare_developer_verified()
        cap = self.fx.capability("skip-review", "transition_work_item", 0, [WORK_REL], target_sha=BASE_SHA)
        result = self.fx.orchestration(
            "transition", cap, "skip-review-request",
            [
                "--to-state", "qa_sit",
                "--transition-name", "skip-independent-review",
                "--review-transition-id", "transition-not-reachable",
            ],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid_transition", result.stdout)
        current = json.loads((self.fx.root / WORK_REL).read_text())
        self.assertEqual(current["lifecycle"]["state"], "developer_verified")
        self.assertEqual(current["checkpoints"], [])
        self.assertEqual(json.loads((self.fx.root / cap).read_text())["status"]["state"], "active")

    def test_independent_review_rejects_same_writer_and_missing_evidence(self) -> None:
        self.prepare_developer_verified()
        reviewer_surface, reviewer_executor = self.fx.register_reviewer()

        same_writer = self.fx.capability("same-writer-review", "transition_work_item", 0, [WORK_REL], target_sha=BASE_SHA)
        denied_same = self.fx.orchestration(
            "transition",
            same_writer,
            "same-writer-review",
            [
                "--to-state", "independent_review",
                "--transition-name", "independent-review",
                "--reviewer-surface-id", self.fx.surface,
                "--reviewer-executor-id", self.fx.executor,
                "--review-evidence-hash", "b" * 64,
            ],
        )
        self.assertNotEqual(denied_same.returncode, 0)
        self.assertIn("reviewer_not_independent", denied_same.stdout)
        self.assertEqual(json.loads((self.fx.root / same_writer).read_text())["status"]["state"], "active")

        missing_evidence = self.fx.capability("missing-review-evidence", "transition_work_item", 0, [WORK_REL], target_sha=BASE_SHA)
        denied_missing = self.fx.orchestration(
            "transition",
            missing_evidence,
            "missing-review-evidence",
            [
                "--to-state", "independent_review",
                "--transition-name", "independent-review",
                "--reviewer-surface-id", reviewer_surface,
                "--reviewer-executor-id", reviewer_executor,
            ],
        )
        self.assertNotEqual(denied_missing.returncode, 0)
        self.assertIn("missing_review_attestation", denied_missing.stdout)
        self.assertEqual(json.loads((self.fx.root / missing_evidence).read_text())["status"]["state"], "active")
        self.assertEqual(json.loads((self.fx.root / WORK_REL).read_text())["lifecycle"]["state"], "developer_verified")

        self.fx.registry["executors"][-1]["roles"] = ["read_only", "writer"]
        write_json(self.fx.root / REGISTRY_REL, self.fx.registry)
        dual_role = self.fx.capability("dual-role-reviewer", "transition_work_item", 0, [WORK_REL], target_sha=BASE_SHA)
        denied_dual = self.fx.orchestration(
            "transition",
            dual_role,
            "dual-role-reviewer",
            [
                "--to-state", "independent_review",
                "--transition-name", "independent-review",
                "--reviewer-surface-id", reviewer_surface,
                "--reviewer-executor-id", reviewer_executor,
                "--review-evidence-hash", "b" * 64,
            ],
        )
        self.assertNotEqual(denied_dual.returncode, 0)
        self.assertIn("reviewer_role_denied", denied_dual.stdout)
        self.assertEqual(json.loads((self.fx.root / dual_role).read_text())["status"]["state"], "active")

    def test_qa_sit_requires_exact_independent_review_reference(self) -> None:
        self.prepare_developer_verified()
        reviewer_surface, reviewer_executor = self.fx.register_reviewer()
        review_cap = self.fx.capability("review", "transition_work_item", 0, [WORK_REL], target_sha=BASE_SHA)
        accepted = self.fx.orchestration(
            "transition",
            review_cap,
            "review-request",
            [
                "--to-state", "independent_review",
                "--transition-name", "independent-review",
                "--reviewer-surface-id", reviewer_surface,
                "--reviewer-executor-id", reviewer_executor,
                "--review-evidence-hash", "b" * 64,
            ],
        )
        self.assertEqual(accepted.returncode, 0)
        review_transition_id = json.loads((self.fx.root / WORK_REL).read_text())["transitions"][-1]["id"]

        qa_cap = self.fx.capability("qa-review-reference", "transition_work_item", 1, [WORK_REL], target_sha=BASE_SHA)
        missing = self.fx.orchestration(
            "transition", qa_cap, "qa-missing-reference",
            ["--to-state", "qa_sit", "--transition-name", "qa-sit"],
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("missing_review_reference", missing.stdout)
        wrong = self.fx.orchestration(
            "transition", qa_cap, "qa-wrong-reference",
            [
                "--to-state", "qa_sit", "--transition-name", "qa-sit",
                "--review-transition-id", "transition-not-the-review",
            ],
        )
        self.assertNotEqual(wrong.returncode, 0)
        self.assertIn("invalid_review_reference", wrong.stdout)
        self.assertEqual(json.loads((self.fx.root / qa_cap).read_text())["status"]["state"], "active")

        passed = self.fx.orchestration(
            "transition", qa_cap, "qa-correct-reference",
            [
                "--to-state", "qa_sit", "--transition-name", "qa-sit",
                "--review-transition-id", review_transition_id,
            ],
        )
        self.assertEqual(passed.returncode, 0)
        current = json.loads((self.fx.root / WORK_REL).read_text())
        self.assertEqual(current["lifecycle"]["state"], "qa_sit")
        self.assertEqual(current["transitions"][-1]["review_transition_id"], review_transition_id)
        self.assertEqual(json.loads((self.fx.root / qa_cap).read_text())["status"]["state"], "consumed")

    def test_human_uat_preserves_legacy_caller_capability_behavior(self) -> None:
        work_path = self.fx.root / WORK_REL
        work = json.loads(work_path.read_text(encoding="utf-8"))
        work["lifecycle"]["state"] = "uat_ready"
        work["lane"]["reservation"] = {
            "status": "active",
            "writer": "fixture-writer",
            "surface_id": self.fx.surface,
            "executor_id": self.fx.executor,
            "lease_expires_at": "2099-01-01T00:00:00Z",
            "version": 1,
        }
        work["acceptance_criteria"] = [
            {
                "id": "AC-001",
                "text": "Fictional owner-visible result",
                "status": "pending",
                "evidence": [],
            }
        ]
        write_json(work_path, work)

        accepted_cap = self.fx.capability(
            "legacy-human-uat-accepted",
            "transition_work_item",
            0,
            [WORK_REL],
            target_sha=BASE_SHA,
        )
        accepted = self.fx.orchestration(
            "transition",
            accepted_cap,
            "legacy-human-uat-accepted",
            [
                "--from-state", "uat_ready",
                "--to-state", "human_uat",
                "--transition-name", "human-uat",
            ],
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        current = json.loads(work_path.read_text(encoding="utf-8"))
        transition = current["transitions"][-1]
        criterion = current["acceptance_criteria"][0]
        self.assertEqual(transition["evidence"], [])
        self.assertNotIn("human_uat_attestor", transition)
        self.assertEqual(criterion, work["acceptance_criteria"][0])
        self.assertEqual(json.loads((self.fx.root / accepted_cap).read_text())["status"]["state"], "consumed")

    def test_legacy_mutation_accepts_relative_project_root(self) -> None:
        capability = self.fx.capability(
            "legacy-relative-root",
            "reserve_writer",
            0,
            [WORK_REL],
            target_sha=BASE_SHA,
        )
        result = run(
            [
                "python3",
                str(ORCHESTRATOR),
                "reserve",
                "--project-root",
                ".",
                "--work-item",
                WORK_REL,
                "--capability",
                capability,
                "--request-id",
                "legacy-relative-root",
                "--surface-id",
                self.fx.surface,
                "--executor-id",
                self.fx.executor,
                "--adapter-version",
                self.fx.adapter,
                "--writer",
                "fixture-writer",
                "--lease-expires-at",
                "2099-01-01T00:00:00Z",
            ],
            cwd=self.fx.root,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads((self.fx.root / WORK_REL).read_text())["lifecycle"]["state"], "reserved")

    def test_release_and_reacquire_are_independent_of_lifecycle(self) -> None:
        reserve = self.fx.capability("reserve-a", "reserve_writer", 0, [WORK_REL], target_sha=BASE_SHA)
        self.assertEqual(self.fx.orchestration("reserve", reserve, "reserve-a", ["--writer", "a", "--lease-expires-at", "2099-01-01T00:00:00Z"]).returncode, 0)
        transition = self.fx.capability("develop", "transition_work_item", 1, [WORK_REL], target_sha=BASE_SHA)
        self.assertEqual(self.fx.orchestration("transition", transition, "develop", ["--to-state", "developing", "--transition-name", "develop"]).returncode, 0)
        release = self.fx.capability("release", "release_writer", 2, [WORK_REL], target_sha=BASE_SHA)
        self.assertEqual(self.fx.orchestration("release", release, "release").returncode, 0)
        reserve_b = self.fx.capability("reserve-b", "reserve_writer", 3, [WORK_REL], target_sha=BASE_SHA)
        self.assertEqual(self.fx.orchestration("reserve", reserve_b, "reserve-b", ["--writer", "b", "--lease-expires-at", "2099-01-01T00:00:00Z"]).returncode, 0)
        work = json.loads((self.fx.root / WORK_REL).read_text())
        self.assertEqual(work["lifecycle"]["state"], "developing")
        self.assertEqual(work["lane"]["reservation"]["writer"], "b")

    def test_planning_v1_is_orientation_only(self) -> None:
        rel = ".exocortex/planning/work-items/PLAN-001.json"
        write_json(
            self.fx.root / rel,
            {
                "schema_version": "1.0-planning", "kind": "delivery_work_item", "id": "PLAN-001", "revision": 2,
                "lifecycle": {"state": "refined", "attempt": 0, "blocked": None},
                "lane": {"base_sha": BASE_SHA, "reservation": {"status": "none"}},
                "acceptance_criteria": [], "transitions": [], "checkpoints": [], "handoffs": [],
            },
        )
        result = run(["python3", str(ORCHESTRATOR), "orient", "--project-root", str(self.fx.root), "--work-item", rel], check=True)
        output = json.loads(result.stdout)
        self.assertEqual(output["compatibility_view"], "planning-v1")
        self.assertFalse(output["mutation_supported"])


class LocalDeliveryFixture:
    """A disposable, fictional Git worktree for local-delivery protocol tests."""

    def __init__(self, *, branch: str = "local-delivery-test") -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="exo-local-delivery-")
        self.container = Path(self.temp.name)
        self.root = self.container / "repo"
        self.root.mkdir()
        self.branch = branch
        self.writer = {
            "surface_id": "fixture-writer-surface",
            "executor_id": "fixture-writer",
            "adapter_version": "fixture-v1",
        }
        self.reviewer = {
            "surface_id": "fixture-review-surface",
            "executor_id": "fixture-reviewer",
            "adapter_version": "fixture-review-v1",
        }
        (self.root / ".gitignore").write_text(
            ".exocortex/control/EXECUTOR_REGISTRY.json\n"
            ".exocortex/events/\n"
            ".exocortex/local/\n"
            ".exocortex/work-items/\n"
            ".env\n"
            "*.scratch\n",
            encoding="utf-8",
        )
        (self.root / "allowed.txt").write_text("base\n", encoding="utf-8")
        (self.root / ".exocortex").mkdir()
        (self.root / ".exocortex" / ".gitkeep").write_text("", encoding="utf-8")
        run(["git", "init", "--quiet", str(self.root)], check=True)
        run(["git", "-C", str(self.root), "config", "user.email", "fixture@example.invalid"], check=True)
        run(["git", "-C", str(self.root), "config", "user.name", "Exocortex Fixture"], check=True)
        run(
            ["git", "-C", str(self.root), "add", ".gitignore", "allowed.txt", ".exocortex/.gitkeep"],
            check=True,
        )
        run(["git", "-C", str(self.root), "commit", "--quiet", "-m", "fixture base"], check=True)
        run(["git", "-C", str(self.root), "branch", "-M", self.branch], check=True)
        self.base = run(["git", "-C", str(self.root), "rev-parse", "HEAD"], check=True).stdout.strip()

    def close(self) -> None:
        self.temp.cleanup()

    def envelope(self, **overrides: object) -> dict:
        document = {
            "schema_version": "public-v2",
            "kind": "local_delivery_envelope",
            "envelope_id": "LOCAL-DELIVERY-001",
            "work_item_id": "LOCAL-DELIVERY-WORK-001",
            "title": "Fictional local delivery fixture",
            "type": "maintenance",
            "project_root": str(self.root.resolve()),
            "branch": self.branch,
            "base_sha": self.base,
            "allowed_paths": ["allowed.txt"],
            "outcome": "Prove bounded local delivery without publication.",
            "risk": "medium",
            "rollback": "Discard the disposable Git worktree.",
            "verification": ["Focused fictional protocol test."],
            "exclusions": ["No commit, push, network, or live repository."],
            "writer": self.writer,
            "reviewer": self.reviewer,
            "approval": {
                "approved_by": "fixture-owner",
                "accepted_at": "2026-01-01T00:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "summary": "Fictional bounded local delivery authority.",
            },
            "lease_expires_at": "2099-01-01T00:00:00Z",
        }
        document.update(overrides)
        return document

    def write_envelope(self, document: Optional[dict] = None, *, name: str = "envelope.json") -> Path:
        source = self.root / ".exocortex/local/protocol/inbox" / name
        write_json(source, self.envelope() if document is None else document)
        return source

    def write_inbox_text(self, name: str, content: str) -> Path:
        path = self.root / ".exocortex/local/protocol/inbox" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def input_argument(self, path: Path, *, root: Optional[Path] = None) -> str:
        selected_root = (root or self.root).absolute()
        try:
            return path.absolute().relative_to(selected_root).as_posix()
        except ValueError:
            return str(path)

    def install_matching_registry(self) -> dict:
        guard_digest = file_digest(AUTHORITY)
        registry = {
            "schema_version": "public-v2",
            "kind": "executor_registry",
            "registry_version": 1,
            "default_role": "read_only",
            "executors": [
                {
                    **self.writer,
                    "guard_digest": guard_digest,
                    "roles": ["read_only", "writer"],
                    "status": "active",
                    "registered_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2099-01-01T00:00:00Z",
                    "revoked_at": None,
                },
                {
                    **self.reviewer,
                    "guard_digest": guard_digest,
                    "roles": ["read_only"],
                    "status": "active",
                    "registered_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2099-01-01T00:00:00Z",
                    "revoked_at": None,
                },
            ],
        }
        write_json(self.root / REGISTRY_REL, registry)
        return registry

    def bootstrap(
        self,
        source: Path,
        request_id: str = "bootstrap-001",
        *,
        root: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        selected_root = root or self.root
        return run(
            [
                "python3", str(ORCHESTRATOR), "bootstrap-local-delivery",
                "--project-root", str(selected_root),
                "--envelope-source", self.input_argument(source, root=selected_root),
                "--request-id", request_id,
            ],
            env=env,
        )

    def sealed_work_item(self) -> Path:
        path = self.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        if document["lifecycle"]["state"] != "developing":
            raise AssertionError("guarded local-delivery bootstrap must enter developing directly")
        return path

    def seal(self, request_id: str = "seal-001", *, root: Optional[Path] = None) -> subprocess.CompletedProcess:
        selected_root = root or self.root
        return run(
            [
                "python3", str(ORCHESTRATOR), "seal-local-edit",
                "--project-root", str(selected_root),
                "--work-item", ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json",
                "--request-id", request_id,
                "--surface-id", self.writer["surface_id"],
                "--executor-id", self.writer["executor_id"],
                "--adapter-version", self.writer["adapter_version"],
            ]
        )

    def complete(
        self,
        body: Path,
        request_id: str = "complete-001",
        *,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        return run(
            [
                "python3", str(ORCHESTRATOR), "complete-local-delivery",
                "--project-root", str(self.root),
                "--work-item", ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json",
                "--request-id", request_id,
                "--surface-id", self.writer["surface_id"],
                "--executor-id", self.writer["executor_id"],
                "--adapter-version", self.writer["adapter_version"],
                "--body-file", self.input_argument(body),
            ],
            env=env,
        )

    def transition(
        self,
        to_state: str,
        request_id: str,
        *,
        review_transition_id: Optional[str] = None,
        human_uat: bool = False,
        evidence: Optional[List[str]] = None,
        human_uat_attestor: Optional[str] = None,
        caller_capability: bool = False,
        payload_digest_override: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> tuple[str, subprocess.CompletedProcess]:
        work_rel = ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        work = json.loads((self.root / work_rel).read_text(encoding="utf-8"))
        transition_evidence = ["fixture lifecycle evidence"] if evidence is None else list(evidence)
        if human_uat:
            transition_evidence.append("fixture human UAT accepted")
            human_uat_attestor = human_uat_attestor or "fixture-owner"
        reviewer_surface_id = self.reviewer["surface_id"] if to_state == "independent_review" else None
        reviewer_executor_id = self.reviewer["executor_id"] if to_state == "independent_review" else None
        review_evidence_hash = "b" * 64 if to_state == "independent_review" else None
        payload = {
            "operation": "transition_work_item",
            "from_state": work["lifecycle"]["state"],
            "to_state": to_state,
            "transition_name": f"fixture-{to_state}",
            "evidence": transition_evidence,
            "reviewer_surface_id": reviewer_surface_id,
            "reviewer_executor_id": reviewer_executor_id,
            "review_evidence_hash": review_evidence_hash,
            "review_transition_id": review_transition_id,
            "human_uat_attestor": human_uat_attestor,
        }
        internal_pair = (work["lifecycle"]["state"], to_state) in {
            ("developing", "developer_verified"),
            ("developer_verified", "independent_review"),
            ("independent_review", "qa_sit"),
            ("qa_sit", "uat_ready"),
            ("uat_ready", "human_uat"),
        }
        capability_rel = (
            ".exocortex/local/protocol/capabilities/"
            f"{stable_protocol_id('cap', work['id'], 'transition_work_item', request_id)}.json"
        )
        if caller_capability or not internal_pair:
            capability_id = f"fixture-{request_id}"
            capability_rel = f".exocortex/local/protocol/capabilities/{capability_id}.json"
            capability = {
                "schema_version": "public-v2",
                "kind": "approval_capability",
                "capability_id": capability_id,
                "work_item_id": work["id"],
                "work_item_revision": work["revision"],
                "operation": "transition_work_item",
                "scope": {
                    "allowed_paths": [work_rel],
                    "target_sha": self.base,
                    "payload_digest": payload_digest_override or canonical_digest(payload),
                },
                "executor": {
                    **self.writer,
                    "guard_digest": file_digest(AUTHORITY),
                    "registry_version": 1,
                },
                "approval": {
                    "approved_by": "fixture-owner",
                    "accepted_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2099-01-01T00:00:00Z",
                    "one_time": True,
                    "summary": "Fictional transition authority for local-delivery tests.",
                },
                "status": {
                    "state": "active",
                    "revoked_at": None,
                    "consumed_at": None,
                    "consumed_by_request_id": None,
                },
            }
            write_json(self.root / capability_rel, capability)
        command = [
            "python3", str(ORCHESTRATOR), "transition",
            "--project-root", str(self.root),
            "--work-item", work_rel,
            "--request-id", request_id,
            "--surface-id", self.writer["surface_id"],
            "--executor-id", self.writer["executor_id"],
            "--adapter-version", self.writer["adapter_version"],
            "--from-state", work["lifecycle"]["state"],
            "--to-state", to_state,
            "--transition-name", f"fixture-{to_state}",
        ]
        if caller_capability or not internal_pair:
            command.extend(["--capability", capability_rel])
        for item in transition_evidence:
            command.extend(["--evidence", item])
        if to_state == "independent_review":
            command.extend(
                [
                    "--reviewer-surface-id", reviewer_surface_id,
                    "--reviewer-executor-id", reviewer_executor_id,
                    "--review-evidence-hash", review_evidence_hash,
                ]
            )
        if to_state == "qa_sit":
            if review_transition_id is None:
                raise AssertionError("QA/SIT test transition requires the independent-review transition ID")
            command.extend(["--review-transition-id", review_transition_id])
        if human_uat:
            command.extend(["--human-uat-attestor", human_uat_attestor])
        result = run(command, env=env)
        return capability_rel, result

    def prepare_uat_ready(self) -> None:
        for state, request_id in (
            ("developer_verified", "lifecycle-developer-verified"),
            ("independent_review", "lifecycle-independent-review"),
        ):
            _, result = self.transition(state, request_id)
            if result.returncode != 0:
                raise AssertionError(result.stdout + result.stderr)
        work = json.loads((self.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8"))
        review_transition_id = work["transitions"][-1]["id"]
        for state, request_id, reference in (
            ("qa_sit", "lifecycle-qa-sit", review_transition_id),
            ("uat_ready", "lifecycle-uat-ready", None),
        ):
            _, result = self.transition(
                state,
                request_id,
                review_transition_id=reference,
            )
            if result.returncode != 0:
                raise AssertionError(result.stdout + result.stderr)

    def prepare_human_uat(self) -> None:
        self.prepare_uat_ready()
        _, result = self.transition(
            "human_uat",
            "lifecycle-human-uat",
            human_uat=True,
        )
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)


class LocalDeliveryProtocolTests(unittest.TestCase):
    """Focused tests for the bounded bootstrap/seal safety foundation only."""

    def setUp(self) -> None:
        self.fixtures: List[LocalDeliveryFixture] = []

    def tearDown(self) -> None:
        for fixture in reversed(self.fixtures):
            fixture.close()

    def fixture(self, **kwargs: object) -> LocalDeliveryFixture:
        result = LocalDeliveryFixture(**kwargs)
        self.fixtures.append(result)
        return result

    def assert_no_bootstrap_outputs(self, fixture: LocalDeliveryFixture) -> None:
        self.assertFalse((fixture.root / ".exocortex/local/protocol/envelopes/LOCAL-DELIVERY-001.json").exists())
        self.assertFalse((fixture.root / ".exocortex/control/EXECUTOR_REGISTRY.json").exists())
        self.assertFalse((fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").exists())

    def test_bootstrap_binds_exact_clean_identity_and_replays(self) -> None:
        fixture = self.fixture()
        source = fixture.write_envelope()
        first = fixture.bootstrap(source)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertFalse(json.loads(first.stdout)["replay"])
        work = json.loads((fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8"))
        self.assertEqual(work["lifecycle"]["state"], "developing")
        self.assertEqual(work["designated_base"]["sha"], fixture.base)
        self.assertEqual(work["lane"]["allowed_paths"], ["allowed.txt"])
        self.assertEqual(work["lane"]["reservation"]["surface_id"], fixture.writer["surface_id"])
        self.assertEqual(work["local_delivery"]["seal"], None)
        self.assertEqual(work["local_delivery"]["completion"], None)
        registry = json.loads((fixture.root / REGISTRY_REL).read_text(encoding="utf-8"))
        self.assertEqual([item["roles"] for item in registry["executors"]], [["read_only", "writer"], ["read_only"]])
        self.assertEqual(run(["git", "-C", str(fixture.root), "status", "--porcelain"], check=True).stdout, "")
        runtime_paths = [
            fixture.root / ".exocortex/local/protocol/envelopes/LOCAL-DELIVERY-001.json",
            fixture.root / REGISTRY_REL,
            fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json",
        ]
        before_replay = {path: file_digest(path) for path in runtime_paths}
        os.utime(source, (1, 1))

        replay = fixture.bootstrap(source)
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["replay"])
        self.assertEqual({path: file_digest(path) for path in runtime_paths}, before_replay)
        self.assertEqual(len(work["idempotency"]), 1)

        (fixture.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(fixture.seal().returncode, 0)
        _, verified = fixture.transition("developer_verified", "bootstrap-replay-after-verification")
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        advanced_work_digest = file_digest(runtime_paths[2])
        advanced_replay = fixture.bootstrap(source)
        self.assertEqual(advanced_replay.returncode, 0, advanced_replay.stdout + advanced_replay.stderr)
        self.assertTrue(json.loads(advanced_replay.stdout)["replay"])
        self.assertEqual(json.loads(advanced_replay.stdout)["state"], "developer_verified")
        self.assertEqual(file_digest(runtime_paths[2]), advanced_work_digest)

        runtime_paths[0].unlink()
        missing_finalized = fixture.bootstrap(source)
        self.assertNotEqual(missing_finalized.returncode, 0)
        self.assertIn("bootstrap_state_missing", missing_finalized.stdout)
        self.assertFalse(runtime_paths[0].exists())

        recovered = self.fixture()
        recovered_source = recovered.write_envelope()
        bootstrap_fault = recovered.bootstrap(
            recovered_source,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_bootstrap_envelope"},
        )
        self.assertNotEqual(bootstrap_fault.returncode, 0)
        bootstrap_retry = recovered.bootstrap(recovered_source)
        self.assertEqual(bootstrap_retry.returncode, 0, bootstrap_retry.stdout + bootstrap_retry.stderr)
        self.assertTrue(json.loads(bootstrap_retry.stdout)["replay"])
        self.assertEqual(
            len(list((recovered.root / ".exocortex/local/protocol/envelopes").glob("*.json"))),
            1,
        )

    def test_bootstrap_rejects_invalid_or_dirty_envelopes_without_partial_state(self) -> None:
        cases = (
            ("wildcard", lambda fx: fx.envelope(allowed_paths=["*.txt"]), None, "wildcard_path"),
            ("normalized-duplicate", lambda fx: fx.envelope(allowed_paths=["allowed.txt", "./allowed.txt"]), None, "invalid_allowed_paths"),
            ("backslash", lambda fx: fx.envelope(allowed_paths=["folder\\allowed.txt"]), None, "invalid_allowed_paths"),
            ("environment-file", lambda fx: fx.envelope(allowed_paths=["config/.ENV.local"]), None, "sensitive_allowed_path"),
            ("environment-rc", lambda fx: fx.envelope(allowed_paths=["config/.envrc"]), None, "sensitive_allowed_path"),
            ("credential-directory", lambda fx: fx.envelope(allowed_paths=["Credentials/fixture.json"]), None, "sensitive_allowed_path"),
            ("credential-json", lambda fx: fx.envelope(allowed_paths=["config/Credentials.json"]), None, "sensitive_allowed_path"),
            ("secrets-json", lambda fx: fx.envelope(allowed_paths=["config/Secrets.json"]), None, "sensitive_allowed_path"),
            ("private-key-name", lambda fx: fx.envelope(allowed_paths=["keys/id_ed25519"]), None, "sensitive_allowed_path"),
            ("private-key-suffix", lambda fx: fx.envelope(allowed_paths=["keys/fixture.PEM"]), None, "sensitive_allowed_path"),
            ("protected-root", lambda fx: fx.envelope(allowed_paths=[".exocortex/events"]), None, "protected_path"),
            ("wrong-branch", lambda fx: fx.envelope(branch="not-the-current-branch"), None, "branch_mismatch"),
            ("wrong-root", lambda fx: fx.envelope(project_root=str(fx.container)), None, "wrong_worktree"),
            ("noncanonical-root", lambda fx: fx.envelope(project_root=f"{fx.root}/."), None, "wrong_worktree"),
            ("wrong-base", lambda fx: fx.envelope(base_sha="a" * 40), None, "base_mismatch"),
            (
                "expired",
                lambda fx: fx.envelope(approval={
                    "approved_by": "fixture-owner",
                    "accepted_at": "2025-01-01T00:00:00Z",
                    "expires_at": "2025-01-02T00:00:00Z",
                    "summary": "Expired fictional authority.",
                }, lease_expires_at="2025-01-01T12:00:00Z"),
                None,
                "expired_envelope",
            ),
            ("dirty", lambda fx: fx.envelope(), "untracked-dirty.txt", "dirty_worktree"),
        )
        for name, builder, dirty_path, expected in cases:
            with self.subTest(name=name):
                fixture = self.fixture()
                if dirty_path:
                    (fixture.root / dirty_path).write_text("fictional dirt\n", encoding="utf-8")
                result = fixture.bootstrap(fixture.write_envelope(builder(fixture), name=f"{name}.json"))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stdout)
                self.assert_no_bootstrap_outputs(fixture)

        missing = self.fixture()
        missing_result = missing.bootstrap(
            missing.root / ".exocortex/local/protocol/inbox/missing-envelope.json"
        )
        self.assertNotEqual(missing_result.returncode, 0)
        self.assertIn("missing_file", missing_result.stdout)
        self.assert_no_bootstrap_outputs(missing)

        linked = self.fixture()
        target = linked.write_envelope(name="real-envelope.json")
        source_link = linked.root / ".exocortex/local/protocol/inbox/envelope-link.json"
        source_link.symlink_to(target)
        linked_result = linked.bootstrap(source_link)
        self.assertNotEqual(linked_result.returncode, 0)
        self.assertIn("unsafe_file", linked_result.stdout)
        self.assert_no_bootstrap_outputs(linked)

        linked_ancestor = self.fixture()
        outside_inbox = linked_ancestor.container / "fictional-outside-inbox"
        outside_inbox.mkdir()
        ancestor_source = outside_inbox / "envelope.json"
        write_json(ancestor_source, linked_ancestor.envelope())
        inbox_link = linked_ancestor.root / ".exocortex/local/protocol/inbox"
        inbox_link.parent.mkdir(parents=True, exist_ok=True)
        inbox_link.symlink_to(outside_inbox, target_is_directory=True)
        ancestor_result = linked_ancestor.bootstrap(inbox_link / "envelope.json")
        self.assertNotEqual(ancestor_result.returncode, 0)
        self.assertIn("unsafe_file", ancestor_result.stdout)
        self.assert_no_bootstrap_outputs(linked_ancestor)

        hard_linked = self.fixture()
        hard_target = hard_linked.write_envelope(name="hardlink-target.json")
        hard_source = hard_linked.root / ".exocortex/local/protocol/inbox/hardlink-envelope.json"
        os.link(hard_target, hard_source)
        hard_result = hard_linked.bootstrap(hard_source)
        self.assertNotEqual(hard_result.returncode, 0)
        self.assertIn("unsafe_file", hard_result.stdout)
        self.assert_no_bootstrap_outputs(hard_linked)

        outside = self.fixture()
        outside_source = outside.container / "outside-envelope.json"
        write_json(outside_source, outside.envelope())
        outside_result = outside.bootstrap(outside_source)
        self.assertNotEqual(outside_result.returncode, 0)
        self.assertIn("unsafe_input_path", outside_result.stdout)
        self.assert_no_bootstrap_outputs(outside)

        sensitive = self.fixture()
        sensitive_source = sensitive.root / ".exocortex/local/protocol/inbox/.env"
        write_json(sensitive_source, sensitive.envelope())
        sensitive_result = sensitive.bootstrap(sensitive_source)
        self.assertNotEqual(sensitive_result.returncode, 0)
        self.assertIn("sensitive_input_path", sensitive_result.stdout)
        self.assert_no_bootstrap_outputs(sensitive)

        relative_root = self.fixture()
        relative_result = run(
            [
                "python3",
                str(ORCHESTRATOR),
                "bootstrap-local-delivery",
                "--project-root",
                "repo",
                "--envelope-source",
                ".exocortex/local/protocol/inbox/envelope.json",
                "--request-id",
                "relative-root",
            ],
            cwd=relative_root.container,
        )
        self.assertNotEqual(relative_result.returncode, 0)
        self.assertIn("absolute_project_root_required", relative_result.stdout)
        self.assert_no_bootstrap_outputs(relative_root)

        envelope_schema = json.loads(
            (TEMPLATE / ".exocortex/schemas/local-delivery-envelope.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("pattern", envelope_schema["properties"]["project_root"])
        self.assertEqual(
            envelope_schema["properties"]["allowed_paths"]["items"],
            {"$ref": "#/$defs/source_path"},
        )
        sensitive_pattern = envelope_schema["$defs"]["source_path"]["allOf"][1]["not"]["pattern"]
        for relative in (
            "credentials.json",
            "config/secrets.json",
            "keys/private.pem",
            ".ssh/config",
            "config/.envrc",
        ):
            self.assertIsNotNone(re.search(sensitive_pattern, relative), relative)
        self.assertIsNone(re.search(sensitive_pattern, "docs/public-guide.md"))

    def test_safe_json_rejects_duplicate_keys_in_sources_and_replay_state(self) -> None:
        duplicate_source = self.fixture()
        source = duplicate_source.write_envelope()
        text = source.read_text(encoding="utf-8")
        source.write_text(
            text.replace(
                '"kind": "local_delivery_envelope"',
                '"kind": "local_delivery_envelope",\n  "kind": "local_delivery_envelope"',
                1,
            ),
            encoding="utf-8",
        )
        rejected_source = duplicate_source.bootstrap(source)
        self.assertNotEqual(rejected_source.returncode, 0)
        self.assertIn("duplicate_json_key", rejected_source.stdout)
        self.assert_no_bootstrap_outputs(duplicate_source)

        duplicate_replay = self.fixture()
        replay_source = duplicate_replay.write_envelope()
        self.assertEqual(duplicate_replay.bootstrap(replay_source).returncode, 0)
        journal_path = duplicate_replay.root / ".exocortex/local/protocol/transactions/bootstrap-bootstrap-001.json"
        journal_text = journal_path.read_text(encoding="utf-8")
        journal_path.write_text(
            journal_text.replace(
                '"kind": "local_delivery_bootstrap_transaction"',
                '"kind": "local_delivery_bootstrap_transaction",\n  "kind": "local_delivery_bootstrap_transaction"',
                1,
            ),
            encoding="utf-8",
        )
        rejected_replay = duplicate_replay.bootstrap(replay_source)
        self.assertNotEqual(rejected_replay.returncode, 0)
        self.assertIn("duplicate_json_key", rejected_replay.stdout)

    def test_ignored_changes_are_accounted_without_reading_local_runtime_or_credentials(self) -> None:
        outside = self.fixture()
        self.assertEqual(outside.bootstrap(outside.write_envelope()).returncode, 0)
        (outside.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        (outside.root / "unreviewed.scratch").write_text("ignored output\n", encoding="utf-8")
        rejected = outside.seal()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("ignored_path_outside_scope", rejected.stdout)

        protected = self.fixture()
        self.assertEqual(protected.bootstrap(protected.write_envelope()).returncode, 0)
        (protected.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        protected.write_inbox_text("runtime-note.txt", "protected local runtime\n")
        credential_path = protected.root / ".env"
        credential_path.touch()
        accepted = protected.seal()
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)

    def test_bootstrap_reuses_matching_registry_and_allows_a_distinct_work_item(self) -> None:
        fixture = self.fixture()
        expected_registry = fixture.install_matching_registry()
        first = fixture.bootstrap(fixture.write_envelope())
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        second_envelope = fixture.envelope(
            envelope_id="LOCAL-DELIVERY-002",
            work_item_id="LOCAL-DELIVERY-WORK-002",
        )
        second = fixture.bootstrap(
            fixture.write_envelope(second_envelope, name="second-envelope.json"),
            request_id="bootstrap-002",
        )
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(
            json.loads((fixture.root / REGISTRY_REL).read_text(encoding="utf-8")),
            expected_registry,
        )
        self.assertTrue((fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").exists())
        self.assertTrue((fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-002.json").exists())

    def test_seal_accepts_only_the_exact_lane_and_rejects_copied_runtime(self) -> None:
        fixture = self.fixture()
        self.assertEqual(fixture.bootstrap(fixture.write_envelope()).returncode, 0)
        fixture.sealed_work_item()
        (fixture.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        accepted = fixture.seal()
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        work = json.loads((fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8"))
        evidence = work["local_delivery"]["seal"]
        self.assertEqual(evidence["changed_paths"], ["allowed.txt"])
        self.assertEqual(len(evidence["candidate_digest"]), 64)
        self.assertEqual(fixture.seal().returncode, 0)

        outside = self.fixture()
        self.assertEqual(outside.bootstrap(outside.write_envelope()).returncode, 0)
        outside.sealed_work_item()
        (outside.root / "allowed.txt").write_text("permitted\n", encoding="utf-8")
        (outside.root / "outside.txt").write_text("not permitted\n", encoding="utf-8")
        denied = outside.seal()
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("path_not_allowed", denied.stdout)
        denied_work = json.loads((outside.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8"))
        self.assertIsNone(denied_work["local_delivery"]["seal"])

        copied = self.fixture()
        shutil.copytree(fixture.root / ".exocortex", copied.root / ".exocortex", dirs_exist_ok=True)
        copied_result = copied.seal(root=copied.root)
        self.assertNotEqual(copied_result.returncode, 0)
        self.assertTrue(
            "wrong_worktree" in copied_result.stdout or "worktree_identity_mismatch" in copied_result.stdout,
            copied_result.stdout + copied_result.stderr,
        )

    def test_registry_tamper_and_post_seal_source_drift_fail_closed(self) -> None:
        tampered = self.fixture()
        self.assertEqual(tampered.bootstrap(tampered.write_envelope()).returncode, 0)
        tampered.sealed_work_item()
        (tampered.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        registry_path = tampered.root / REGISTRY_REL
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        registry["registry_version"] = 2
        write_json(registry_path, registry)
        rejected_registry = tampered.seal()
        self.assertNotEqual(rejected_registry.returncode, 0)
        self.assertIn("registry_digest_mismatch", rejected_registry.stdout)
        work = json.loads((tampered.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8"))
        self.assertIsNone(work["local_delivery"]["seal"])

        drifted = self.fixture()
        self.assertEqual(drifted.bootstrap(drifted.write_envelope()).returncode, 0)
        drifted.sealed_work_item()
        (drifted.root / "allowed.txt").write_text("sealed source edit\n", encoding="utf-8")
        self.assertEqual(drifted.seal().returncode, 0)
        drifted.prepare_human_uat()
        (drifted.root / "allowed.txt").write_text("changed after seal\n", encoding="utf-8")
        body = drifted.write_inbox_text("completion.md", "Fictional drift denial.\n")
        rejected_drift = drifted.complete(body)
        self.assertNotEqual(rejected_drift.returncode, 0)
        self.assertIn("sealed_candidate_changed", rejected_drift.stdout)
        self.assertFalse((drifted.root / ".exocortex/events").exists())

        criterion_tamper = self.fixture()
        self.assertEqual(criterion_tamper.bootstrap(criterion_tamper.write_envelope()).returncode, 0)
        (criterion_tamper.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(criterion_tamper.seal().returncode, 0)
        criterion_work_path = criterion_tamper.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        criterion_work = json.loads(criterion_work_path.read_text(encoding="utf-8"))
        criterion_work["acceptance_criteria"][0]["text"] = "Substituted criterion"
        write_json(criterion_work_path, criterion_work)
        capability_rel, rejected_criterion = criterion_tamper.transition(
            "developer_verified",
            "reject-substituted-criterion",
        )
        self.assertNotEqual(rejected_criterion.returncode, 0)
        self.assertIn("acceptance_binding_mismatch", rejected_criterion.stdout)
        self.assertFalse((criterion_tamper.root / capability_rel).exists())

    def test_no_post_development_transition_is_allowed_without_a_seal(self) -> None:
        fixture = self.fixture()
        self.assertEqual(fixture.bootstrap(fixture.write_envelope()).returncode, 0)
        fixture.sealed_work_item()
        capability_rel, rejected = fixture.transition(
            "developer_verified",
            "leave-development-without-seal",
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("missing_edit_seal", rejected.stdout)
        self.assertFalse((fixture.root / capability_rel).exists())
        work = json.loads((fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8"))
        self.assertEqual(work["lifecycle"]["state"], "developing")

        missing_evidence = self.fixture()
        self.assertEqual(missing_evidence.bootstrap(missing_evidence.write_envelope()).returncode, 0)
        (missing_evidence.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(missing_evidence.seal().returncode, 0)
        evidence_capability, evidence_result = missing_evidence.transition(
            "developer_verified",
            "missing-gate-evidence",
            evidence=[],
        )
        self.assertNotEqual(evidence_result.returncode, 0)
        self.assertIn("gate_evidence_missing", evidence_result.stdout)
        self.assertFalse((missing_evidence.root / evidence_capability).exists())

        payload_bound = self.fixture()
        self.assertEqual(payload_bound.bootstrap(payload_bound.write_envelope()).returncode, 0)
        (payload_bound.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(payload_bound.seal().returncode, 0)
        payload_capability, payload_result = payload_bound.transition(
            "developer_verified",
            "wrong-transition-payload",
            caller_capability=True,
            payload_digest_override="d" * 64,
        )
        self.assertNotEqual(payload_result.returncode, 0)
        self.assertIn("caller_capability_forbidden", payload_result.stdout)
        self.assertEqual(
            json.loads((payload_bound.root / payload_capability).read_text(encoding="utf-8"))["status"]["state"],
            "active",
        )

        recovery_bound = self.fixture()
        self.assertEqual(recovery_bound.bootstrap(recovery_bound.write_envelope()).returncode, 0)
        (recovery_bound.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(recovery_bound.seal().returncode, 0)
        recovery_capability, faulted_transition = recovery_bound.transition(
            "developer_verified",
            "transition-intent-recovery",
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_intent"},
        )
        self.assertNotEqual(faulted_transition.returncode, 0)
        journal_path = (
            recovery_bound.root
            / ".exocortex/local/protocol/transactions/transition-intent-recovery.json"
        )
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        tampered_transition = journal["after_document"]["transitions"][-1]
        tampered_transition["evidence"] = ["tampered recovery evidence"]
        tampered_transition["intent_digest"] = canonical_digest(
            {
                "operation": "transition_work_item",
                "from_state": tampered_transition["from"],
                "to_state": tampered_transition["to"],
                "transition_name": tampered_transition["operation"],
                "evidence": tampered_transition["evidence"],
                "reviewer_surface_id": tampered_transition.get("reviewer_surface_id"),
                "reviewer_executor_id": tampered_transition.get("reviewer_executor_id"),
                "review_evidence_hash": tampered_transition.get("review_evidence_hash"),
                "review_transition_id": tampered_transition.get("review_transition_id"),
                "human_uat_attestor": tampered_transition.get("human_uat_attestor"),
            }
        )
        journal["after_digest"] = canonical_digest(journal["after_document"])
        write_json(journal_path, journal)
        _, rejected_recovery = recovery_bound.transition(
            "developer_verified",
            "transition-intent-recovery",
        )
        self.assertNotEqual(rejected_recovery.returncode, 0)
        self.assertIn("transaction_semantics_mismatch", rejected_recovery.stdout)
        self.assertEqual(
            json.loads((recovery_bound.root / recovery_capability).read_text(encoding="utf-8"))["status"]["state"],
            "active",
        )

        uat_authority = self.fixture()
        self.assertEqual(uat_authority.bootstrap(uat_authority.write_envelope()).returncode, 0)
        (uat_authority.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(uat_authority.seal().returncode, 0)
        uat_authority.prepare_uat_ready()
        uat_ready_work = json.loads(
            (uat_authority.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8")
        )
        self.assertEqual(uat_ready_work["lifecycle"]["state"], "uat_ready")
        self.assertTrue(all(item["status"] == "pending" for item in uat_ready_work["acceptance_criteria"]))
        self.assertTrue(all(item["evidence"] == [] for item in uat_ready_work["acceptance_criteria"]))
        _, missing_attestor = uat_authority.transition(
            "human_uat",
            "missing-human-uat-attestor",
        )
        self.assertNotEqual(missing_attestor.returncode, 0)
        self.assertIn("missing_human_uat_attestation", missing_attestor.stdout)
        _, wrong_attestor = uat_authority.transition(
            "human_uat",
            "wrong-human-uat-attestor",
            human_uat=True,
            human_uat_attestor="different-fictional-authority",
        )
        self.assertNotEqual(wrong_attestor.returncode, 0)
        self.assertIn("human_uat_authority_mismatch", wrong_attestor.stdout)

        for rejected_status in ("failed", "blocked"):
            with self.subTest(acceptance_status=rejected_status):
                unsatisfied = self.fixture()
                self.assertEqual(unsatisfied.bootstrap(unsatisfied.write_envelope()).returncode, 0)
                (unsatisfied.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
                self.assertEqual(unsatisfied.seal().returncode, 0)
                unsatisfied.prepare_uat_ready()
                unsatisfied_work_path = unsatisfied.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
                unsatisfied_work = json.loads(unsatisfied_work_path.read_text(encoding="utf-8"))
                unsatisfied_work["acceptance_criteria"][0]["status"] = rejected_status
                unsatisfied_work["acceptance_criteria"][0]["evidence"] = [
                    f"fixture criterion is {rejected_status}"
                ]
                write_json(unsatisfied_work_path, unsatisfied_work)
                capability_rel, rejected_acceptance = unsatisfied.transition(
                    "human_uat",
                    f"reject-{rejected_status}-acceptance",
                    human_uat=True,
                )
                self.assertNotEqual(rejected_acceptance.returncode, 0)
                self.assertIn("acceptance_not_satisfied", rejected_acceptance.stdout)
                self.assertFalse((unsatisfied.root / capability_rel).exists())
                unchanged = json.loads(unsatisfied_work_path.read_text(encoding="utf-8"))
                self.assertEqual(unchanged["lifecycle"]["state"], "uat_ready")

        premature_pass = self.fixture()
        self.assertEqual(premature_pass.bootstrap(premature_pass.write_envelope()).returncode, 0)
        (premature_pass.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(premature_pass.seal().returncode, 0)
        premature_pass.prepare_uat_ready()
        premature_work_path = premature_pass.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        premature_work = json.loads(premature_work_path.read_text(encoding="utf-8"))
        premature_work["acceptance_criteria"][0]["status"] = "passed"
        premature_work["acceptance_criteria"][0]["evidence"] = ["forged premature acceptance"]
        write_json(premature_work_path, premature_work)
        capability_rel, rejected_premature = premature_pass.transition(
            "human_uat",
            "reject-premature-passed-acceptance",
            human_uat=True,
        )
        self.assertNotEqual(rejected_premature.returncode, 0)
        self.assertIn("acceptance_state_mismatch", rejected_premature.stdout)
        self.assertFalse((premature_pass.root / capability_rel).exists())

        recovered_uat = self.fixture()
        self.assertEqual(recovered_uat.bootstrap(recovered_uat.write_envelope()).returncode, 0)
        (recovered_uat.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(recovered_uat.seal().returncode, 0)
        recovered_uat.prepare_uat_ready()
        _, faulted_uat = recovered_uat.transition(
            "human_uat",
            "recover-human-uat-acceptance",
            human_uat=True,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_intent"},
        )
        self.assertNotEqual(faulted_uat.returncode, 0)
        _, recovered_uat_result = recovered_uat.transition(
            "human_uat",
            "recover-human-uat-acceptance",
            human_uat=True,
        )
        self.assertEqual(recovered_uat_result.returncode, 0, recovered_uat_result.stdout + recovered_uat_result.stderr)
        recovered_work = json.loads(
            (recovered_uat.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8")
        )
        recovered_transition = recovered_work["transitions"][-1]
        expected_marker = f"human-uat-transition:{recovered_transition['id']}"
        for criterion in recovered_work["acceptance_criteria"]:
            self.assertEqual(criterion["status"], "passed")
            self.assertEqual(criterion["evidence"].count(expected_marker), 1)
            self.assertEqual(criterion["evidence"].count("fixture human UAT accepted"), 1)

    def test_internal_transition_capabilities_replay_exact_intent_and_closeout_precedes_release(self) -> None:
        replayed = self.fixture()
        self.assertEqual(replayed.bootstrap(replayed.write_envelope()).returncode, 0)
        (replayed.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(replayed.seal().returncode, 0)
        capability_rel, accepted = replayed.transition(
            "developer_verified",
            "internal-transition-replay",
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        capability = json.loads((replayed.root / capability_rel).read_text(encoding="utf-8"))
        self.assertEqual(capability["status"]["state"], "consumed")
        replay_command = [
            "python3",
            str(ORCHESTRATOR),
            "transition",
            "--project-root",
            str(replayed.root),
            "--work-item",
            ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json",
            "--request-id",
            "internal-transition-replay",
            "--surface-id",
            replayed.writer["surface_id"],
            "--executor-id",
            replayed.writer["executor_id"],
            "--adapter-version",
            replayed.writer["adapter_version"],
            "--from-state",
            "developing",
            "--to-state",
            "developer_verified",
            "--transition-name",
            "fixture-developer_verified",
            "--evidence",
            "fixture lifecycle evidence",
        ]
        replay = run(replay_command)
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["replay"])

        replayed_work_path = replayed.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        replayed_journal_path = (
            replayed.root
            / ".exocortex/local/protocol/transactions/internal-transition-replay.json"
        )
        work_before_tamper_attempt = replayed_work_path.read_bytes()
        capability_before_tamper_attempt = (replayed.root / capability_rel).read_bytes()
        finalized_journal = json.loads(replayed_journal_path.read_text(encoding="utf-8"))
        finalized_journal["after_document"]["title"] = "Semantically tampered finalized state"
        finalized_journal["after_digest"] = canonical_digest(finalized_journal["after_document"])
        write_json(replayed_journal_path, finalized_journal)
        rejected_finalized_tamper = run(replay_command)
        self.assertNotEqual(rejected_finalized_tamper.returncode, 0)
        self.assertIn("transition_transaction_mismatch", rejected_finalized_tamper.stdout)
        self.assertEqual(replayed_work_path.read_bytes(), work_before_tamper_attempt)
        self.assertEqual(
            (replayed.root / capability_rel).read_bytes(),
            capability_before_tamper_attempt,
        )

        changed_intent = run([*replay_command[:-1], "different replay evidence"])
        self.assertNotEqual(changed_intent.returncode, 0)
        self.assertIn("idempotency_conflict", changed_intent.stdout)

        recovered_after_replace = self.fixture()
        self.assertEqual(
            recovered_after_replace.bootstrap(recovered_after_replace.write_envelope()).returncode,
            0,
        )
        (recovered_after_replace.root / "allowed.txt").write_text(
            "approved source edit\n",
            encoding="utf-8",
        )
        self.assertEqual(recovered_after_replace.seal().returncode, 0)
        recovery_request = "recover-after-state-replaced"
        recovery_command = [
            "python3",
            str(ORCHESTRATOR),
            "transition",
            "--project-root",
            str(recovered_after_replace.root),
            "--work-item",
            ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json",
            "--request-id",
            recovery_request,
            "--surface-id",
            recovered_after_replace.writer["surface_id"],
            "--executor-id",
            recovered_after_replace.writer["executor_id"],
            "--adapter-version",
            recovered_after_replace.writer["adapter_version"],
            "--from-state",
            "developing",
            "--to-state",
            "developer_verified",
            "--transition-name",
            "fixture-developer_verified",
            "--evidence",
            "fixture lifecycle evidence",
        ]
        faulted = run(
            recovery_command,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_state_replaced"},
        )
        self.assertNotEqual(faulted.returncode, 0)
        self.assertIn("injected_fault", faulted.stdout)
        replaced_work = json.loads(
            (
                recovered_after_replace.root
                / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(replaced_work["lifecycle"]["state"], "developer_verified")
        recovery_capability_rel = (
            ".exocortex/local/protocol/capabilities/"
            f"{stable_protocol_id('cap', replaced_work['id'], 'transition_work_item', recovery_request)}.json"
        )
        self.assertEqual(
            json.loads((recovered_after_replace.root / recovery_capability_rel).read_text(encoding="utf-8"))[
                "status"
            ]["state"],
            "consumed",
        )
        recovery_journal = (
            recovered_after_replace.root
            / f".exocortex/local/protocol/transactions/{recovery_request}.json"
        )
        self.assertEqual(json.loads(recovery_journal.read_text(encoding="utf-8"))["status"], "intent")
        recovered = run(recovery_command)
        self.assertEqual(recovered.returncode, 0, recovered.stdout + recovered.stderr)
        self.assertTrue(json.loads(recovered.stdout)["replay"])
        self.assertEqual(json.loads(recovery_journal.read_text(encoding="utf-8"))["status"], "finalized")
        self.assertEqual(
            json.loads(
                (
                    recovered_after_replace.root
                    / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
                ).read_text(encoding="utf-8")
            ),
            replaced_work,
        )

        release = self.fixture()
        self.assertEqual(release.bootstrap(release.write_envelope()).returncode, 0)
        (release.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(release.seal().returncode, 0)
        release.prepare_human_uat()
        premature_capability, premature = release.transition(
            "release_ready",
            "release-before-closeout",
        )
        self.assertNotEqual(premature.returncode, 0)
        self.assertIn("local_delivery_incomplete", premature.stdout)
        self.assertEqual(
            json.loads((release.root / premature_capability).read_text(encoding="utf-8"))["status"]["state"],
            "active",
        )
        body = release.write_inbox_text("completion.md", "Fictional closeout before release readiness.\n")
        completed = release.complete(body)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        release_capability, release_ready = release.transition("release_ready", "release-after-closeout")
        self.assertEqual(release_ready.returncode, 0, release_ready.stdout + release_ready.stderr)
        self.assertEqual(json.loads(release_ready.stdout)["state"], "release_ready")
        release_replay = run(
            [
                "python3",
                str(ORCHESTRATOR),
                "transition",
                "--project-root",
                str(release.root),
                "--work-item",
                ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json",
                "--capability",
                release_capability,
                "--request-id",
                "release-after-closeout",
                "--surface-id",
                release.writer["surface_id"],
                "--executor-id",
                release.writer["executor_id"],
                "--adapter-version",
                release.writer["adapter_version"],
                "--from-state",
                "human_uat",
                "--to-state",
                "release_ready",
                "--transition-name",
                "fixture-release_ready",
                "--evidence",
                "fixture lifecycle evidence",
            ]
        )
        self.assertEqual(release_replay.returncode, 0, release_replay.stdout + release_replay.stderr)
        self.assertTrue(json.loads(release_replay.stdout)["replay"])

    def test_release_ready_rejects_fabricated_completion_provenance(self) -> None:
        fixture = self.fixture()
        self.assertEqual(fixture.bootstrap(fixture.write_envelope()).returncode, 0)
        (fixture.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(fixture.seal().returncode, 0)
        fixture.prepare_human_uat()
        work_path = fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        work = json.loads(work_path.read_text(encoding="utf-8"))
        reservation = work["lane"]["reservation"]
        work["local_delivery"]["completion"] = {
            "request_id": "fabricated-completion",
            "completed_at": "2026-01-02T00:00:00Z",
            "local_state": "complete",
            "event_path": ".exocortex/events/fabricated-completion.md",
            "body_digest": "c" * 64,
            "event_digest": "d" * 64,
        }
        work["lane"]["reservation"] = {
            "status": "released",
            "writer": None,
            "surface_id": None,
            "executor_id": None,
            "lease_expires_at": None,
            "version": reservation["version"] + 1,
        }
        write_json(work_path, work)

        capability_rel, rejected = fixture.transition(
            "release_ready",
            "release-after-fabricated-closeout",
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("missing_file", rejected.stdout)
        self.assertFalse((fixture.root / ".exocortex/events/fabricated-completion.md").exists())
        self.assertFalse(
            any(
                item.get("operation") == "complete_local_delivery"
                for item in json.loads(work_path.read_text(encoding="utf-8"))["idempotency"]
            )
        )
        self.assertEqual(
            json.loads((fixture.root / capability_rel).read_text(encoding="utf-8"))["status"]["state"],
            "active",
        )

    def test_completion_requires_human_uat_and_binds_event_and_body_bytes(self) -> None:
        gated = self.fixture()
        self.assertEqual(gated.bootstrap(gated.write_envelope()).returncode, 0)
        gated.sealed_work_item()
        (gated.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(gated.seal().returncode, 0)
        gated_body = gated.write_inbox_text("completion.md", "Fictional UAT gate denial.\n")
        rejected_gate = gated.complete(gated_body)
        self.assertNotEqual(rejected_gate.returncode, 0)
        self.assertIn("human_uat_required", rejected_gate.stdout)
        self.assertFalse((gated.root / ".exocortex/events").exists())

        outside_body = gated.container / "outside-completion.md"
        outside_body.write_text("Fictional outside-inbox body.\n", encoding="utf-8")
        rejected_outside_body = gated.complete(outside_body)
        self.assertNotEqual(rejected_outside_body.returncode, 0)
        self.assertIn("unsafe_input_path", rejected_outside_body.stdout)
        sensitive_body = gated.write_inbox_text("identity.pem", "Fictional private-key-shaped body.\n")
        rejected_sensitive_body = gated.complete(sensitive_body)
        self.assertNotEqual(rejected_sensitive_body.returncode, 0)
        self.assertIn("sensitive_input_path", rejected_sensitive_body.stdout)
        self.assertFalse((gated.root / ".exocortex/events").exists())

        tampered_acceptance = self.fixture()
        self.assertEqual(tampered_acceptance.bootstrap(tampered_acceptance.write_envelope()).returncode, 0)
        (tampered_acceptance.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(tampered_acceptance.seal().returncode, 0)
        tampered_acceptance.prepare_human_uat()
        tampered_work_path = tampered_acceptance.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        tampered_work = json.loads(tampered_work_path.read_text(encoding="utf-8"))
        tampered_work["acceptance_criteria"][0]["status"] = "pending"
        tampered_work["acceptance_criteria"][0]["evidence"] = []
        write_json(tampered_work_path, tampered_work)
        tampered_body = tampered_acceptance.write_inbox_text(
            "completion.md", "Fictional incomplete acceptance denial.\n"
        )
        rejected_acceptance = tampered_acceptance.complete(tampered_body)
        self.assertNotEqual(rejected_acceptance.returncode, 0)
        self.assertIn("acceptance_incomplete", rejected_acceptance.stdout)
        self.assertFalse((tampered_acceptance.root / ".exocortex/events").exists())

        forged_evidence = self.fixture()
        self.assertEqual(forged_evidence.bootstrap(forged_evidence.write_envelope()).returncode, 0)
        (forged_evidence.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(forged_evidence.seal().returncode, 0)
        forged_evidence.prepare_human_uat()
        forged_work_path = forged_evidence.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        forged_work = json.loads(forged_work_path.read_text(encoding="utf-8"))
        forged_work["acceptance_criteria"][0]["evidence"] = ["forged replacement evidence"]
        write_json(forged_work_path, forged_work)
        forged_body = forged_evidence.write_inbox_text(
            "completion.md", "Fictional forged acceptance-evidence denial.\n"
        )
        rejected_forgery = forged_evidence.complete(forged_body)
        self.assertNotEqual(rejected_forgery.returncode, 0)
        self.assertIn("acceptance_evidence_mismatch", rejected_forgery.stdout)
        self.assertFalse((forged_evidence.root / ".exocortex/events").exists())

        coordinated_tamper = self.fixture()
        self.assertEqual(coordinated_tamper.bootstrap(coordinated_tamper.write_envelope()).returncode, 0)
        (coordinated_tamper.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(coordinated_tamper.seal().returncode, 0)
        coordinated_tamper.prepare_human_uat()
        coordinated_work_path = coordinated_tamper.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        coordinated_work = json.loads(coordinated_work_path.read_text(encoding="utf-8"))
        coordinated_transition = coordinated_work["transitions"][-1]
        coordinated_transition["evidence"] = ["forged replacement UAT evidence"]
        coordinated_transition["intent_digest"] = canonical_digest(
            {
                "operation": "transition_work_item",
                "from_state": coordinated_transition["from"],
                "to_state": coordinated_transition["to"],
                "transition_name": coordinated_transition["operation"],
                "evidence": coordinated_transition["evidence"],
                "reviewer_surface_id": None,
                "reviewer_executor_id": None,
                "review_evidence_hash": None,
                "review_transition_id": None,
                "human_uat_attestor": coordinated_transition["human_uat_attestor"],
            }
        )
        coordinated_marker = f"human-uat-transition:{coordinated_transition['id']}"
        for criterion in coordinated_work["acceptance_criteria"]:
            criterion["evidence"] = [coordinated_marker, "forged replacement UAT evidence"]
        write_json(coordinated_work_path, coordinated_work)
        coordinated_body = coordinated_tamper.write_inbox_text(
            "completion.md", "Fictional coordinated UAT tamper denial.\n"
        )
        rejected_coordinated = coordinated_tamper.complete(coordinated_body)
        self.assertNotEqual(rejected_coordinated.returncode, 0)
        self.assertIn("human_uat_intent_mismatch", rejected_coordinated.stdout)
        self.assertFalse((coordinated_tamper.root / ".exocortex/events").exists())

        synthetic_uat = self.fixture()
        self.assertEqual(synthetic_uat.bootstrap(synthetic_uat.write_envelope()).returncode, 0)
        (synthetic_uat.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(synthetic_uat.seal().returncode, 0)
        synthetic_uat.prepare_uat_ready()
        synthetic_work_path = synthetic_uat.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        synthetic_work = json.loads(synthetic_work_path.read_text(encoding="utf-8"))
        synthetic_transition = {
            "id": "transition-forged-human-uat",
            "request_id": "forged-human-uat",
            "operation": "forged-human-uat",
            "from": "uat_ready",
            "to": "human_uat",
            "accepted_at": "2026-01-02T00:00:00Z",
            "capability_id": "fixture-nonexistent-human-uat",
            "capability_path": ".exocortex/local/protocol/capabilities/fixture-nonexistent-human-uat.json",
            "capability_digest": "e" * 64,
            "checkpoint_eligible": True,
            "evidence": ["forged UAT evidence"],
            "human_uat_attestor": "fixture-owner",
        }
        synthetic_transition["intent_digest"] = canonical_digest(
            {
                "operation": "transition_work_item",
                "from_state": synthetic_transition["from"],
                "to_state": synthetic_transition["to"],
                "transition_name": synthetic_transition["operation"],
                "evidence": synthetic_transition["evidence"],
                "reviewer_surface_id": None,
                "reviewer_executor_id": None,
                "review_evidence_hash": None,
                "review_transition_id": None,
                "human_uat_attestor": synthetic_transition["human_uat_attestor"],
            }
        )
        synthetic_work["transitions"].append(synthetic_transition)
        synthetic_work["checkpoints"].append(
            {
                "id": "checkpoint-forged-human-uat",
                "transition_id": synthetic_transition["id"],
                "request_id": synthetic_transition["request_id"],
                "state": "human_uat",
                "created_at": synthetic_transition["accepted_at"],
                "local_only": True,
            }
        )
        synthetic_work["lifecycle"]["state"] = "human_uat"
        synthetic_marker = f"human-uat-transition:{synthetic_transition['id']}"
        for criterion in synthetic_work["acceptance_criteria"]:
            criterion["status"] = "passed"
            criterion["evidence"] = [synthetic_marker, "forged UAT evidence"]
        write_json(synthetic_work_path, synthetic_work)
        synthetic_body = synthetic_uat.write_inbox_text(
            "completion.md", "Fictional synthetic UAT denial.\n"
        )
        rejected_synthetic = synthetic_uat.complete(synthetic_body)
        self.assertNotEqual(rejected_synthetic.returncode, 0)
        self.assertFalse((synthetic_uat.root / ".exocortex/events").exists())

        missing_transaction = self.fixture()
        self.assertEqual(missing_transaction.bootstrap(missing_transaction.write_envelope()).returncode, 0)
        (missing_transaction.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(missing_transaction.seal().returncode, 0)
        missing_transaction.prepare_human_uat()
        missing_work = json.loads(
            (missing_transaction.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8")
        )
        missing_request = missing_work["transitions"][-1]["request_id"]
        (missing_transaction.root / f".exocortex/local/protocol/transactions/{missing_request}.json").unlink()
        missing_body = missing_transaction.write_inbox_text(
            "completion.md", "Fictional missing Human-UAT transaction denial.\n"
        )
        rejected_missing_transaction = missing_transaction.complete(missing_body)
        self.assertNotEqual(rejected_missing_transaction.returncode, 0)
        self.assertFalse((missing_transaction.root / ".exocortex/events").exists())

        pre_uat_capability = self.fixture()
        self.assertEqual(pre_uat_capability.bootstrap(pre_uat_capability.write_envelope()).returncode, 0)
        (pre_uat_capability.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(pre_uat_capability.seal().returncode, 0)
        pre_uat_capability.prepare_human_uat()
        pre_uat_work = json.loads(
            (pre_uat_capability.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(
                encoding="utf-8"
            )
        )
        developer_transition = pre_uat_work["transitions"][0]
        developer_capability_path = pre_uat_capability.root / developer_transition["capability_path"]
        developer_capability = json.loads(developer_capability_path.read_text(encoding="utf-8"))
        developer_capability["approval"]["summary"] = "Tampered fictional transition capability."
        write_json(developer_capability_path, developer_capability)
        pre_uat_body = pre_uat_capability.write_inbox_text(
            "completion.md", "Fictional pre-UAT capability provenance denial.\n"
        )
        rejected_pre_uat_capability = pre_uat_capability.complete(pre_uat_body)
        self.assertNotEqual(rejected_pre_uat_capability.returncode, 0)
        self.assertIn("transition_capability_mismatch", rejected_pre_uat_capability.stdout)
        self.assertFalse((pre_uat_capability.root / ".exocortex/events").exists())

        pre_uat_transaction = self.fixture()
        self.assertEqual(pre_uat_transaction.bootstrap(pre_uat_transaction.write_envelope()).returncode, 0)
        (pre_uat_transaction.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(pre_uat_transaction.seal().returncode, 0)
        pre_uat_transaction.prepare_human_uat()
        transaction_work = json.loads(
            (pre_uat_transaction.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(
                encoding="utf-8"
            )
        )
        developer_request = transaction_work["transitions"][0]["request_id"]
        (pre_uat_transaction.root / f".exocortex/local/protocol/transactions/{developer_request}.json").unlink()
        transaction_body = pre_uat_transaction.write_inbox_text(
            "completion.md", "Fictional pre-UAT transaction provenance denial.\n"
        )
        rejected_pre_uat_transaction = pre_uat_transaction.complete(transaction_body)
        self.assertNotEqual(rejected_pre_uat_transaction.returncode, 0)
        self.assertFalse((pre_uat_transaction.root / ".exocortex/events").exists())

        completed = self.fixture()
        self.assertEqual(completed.bootstrap(completed.write_envelope()).returncode, 0)
        completed.sealed_work_item()
        (completed.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(completed.seal().returncode, 0)
        completed.prepare_human_uat()
        accepted_work = json.loads(
            (completed.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8")
        )
        accepted_transition = accepted_work["transitions"][-1]
        acceptance_marker = f"human-uat-transition:{accepted_transition['id']}"
        for criterion in accepted_work["acceptance_criteria"]:
            self.assertEqual(criterion["status"], "passed")
            self.assertIn(acceptance_marker, criterion["evidence"])
            self.assertIn("fixture lifecycle evidence", criterion["evidence"])
            self.assertIn("fixture human UAT accepted", criterion["evidence"])
        original_body = b"Fictional byte-bound completion.\n"
        body = completed.write_inbox_text("completion.md", original_body.decode("utf-8"))
        accepted = completed.complete(body)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        event = next((completed.root / ".exocortex/events").glob("*.md"))
        event_bytes = event.read_bytes()
        self.assertIn(hashlib.sha256(original_body).hexdigest().encode("ascii"), event_bytes)
        body.write_bytes(b"Different body on the same request.\n")
        body_conflict = completed.complete(body)
        self.assertNotEqual(body_conflict.returncode, 0)
        self.assertIn("idempotency_conflict", body_conflict.stdout)
        body.write_bytes(original_body)
        event.write_bytes(event_bytes + b"tampered\n")
        event_conflict = completed.complete(body)
        self.assertNotEqual(event_conflict.returncode, 0)
        self.assertIn("completion_event_conflict", event_conflict.stdout)

    def test_completion_is_single_event_and_recovers_after_event_write(self) -> None:
        fixture = self.fixture()
        self.assertEqual(fixture.bootstrap(fixture.write_envelope()).returncode, 0)
        fixture.sealed_work_item()
        (fixture.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(fixture.seal().returncode, 0)
        fixture.prepare_human_uat()
        body = fixture.write_inbox_text("completion.md", "Fictional local delivery completion record.\n")
        completed = fixture.complete(body)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        replay = fixture.complete(body)
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
        events = sorted((fixture.root / ".exocortex/events").glob("*.md"))
        self.assertEqual(len(events), 1)
        work = json.loads((fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(work["local_delivery"]["completion"])
        self.assertEqual(work["local_delivery"]["completion"]["local_state"], "complete")
        self.assertEqual(work["lifecycle"]["state"], "human_uat")
        self.assertEqual(work["lane"]["reservation"]["status"], "released")
        self.assertEqual(len(work["handoffs"]), 1)

        finalized_journal_path = (
            fixture.root
            / ".exocortex/local/protocol/transactions/completion-complete-001.json"
        )
        finalized_journal = json.loads(finalized_journal_path.read_text(encoding="utf-8"))
        finalized_journal["before_document"]["title"] = "Semantically tampered completion input"
        finalized_journal["before_digest"] = canonical_digest(finalized_journal["before_document"])
        write_json(finalized_journal_path, finalized_journal)
        completion_capability_path = next(
            path
            for path in (fixture.root / ".exocortex/local/protocol/capabilities").glob("*.json")
            if json.loads(path.read_text(encoding="utf-8"))["operation"] == "complete_local_delivery"
        )
        durable_paths = [
            fixture.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json",
            completion_capability_path,
            events[0],
            finalized_journal_path,
        ]
        durable_before_rejection = {path: path.read_bytes() for path in durable_paths}
        rejected_semantic_tamper = fixture.complete(body)
        self.assertNotEqual(rejected_semantic_tamper.returncode, 0)
        self.assertIn("transition_chain_mismatch", rejected_semantic_tamper.stdout)
        self.assertEqual(
            {path: path.read_bytes() for path in durable_paths},
            durable_before_rejection,
        )

        prepared = self.fixture()
        self.assertEqual(prepared.bootstrap(prepared.write_envelope()).returncode, 0)
        prepared.sealed_work_item()
        (prepared.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(prepared.seal().returncode, 0)
        prepared.prepare_human_uat()
        prepared_body = prepared.write_inbox_text("completion.md", "Fictional prepared recovery completion record.\n")
        preparation_fault = prepared.complete(
            prepared_body,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_completion_prepare"},
        )
        self.assertNotEqual(preparation_fault.returncode, 0)
        preparation_retry = prepared.complete(prepared_body)
        self.assertEqual(preparation_retry.returncode, 0, preparation_retry.stdout + preparation_retry.stderr)
        self.assertEqual(len(list((prepared.root / ".exocortex/events").glob("*.md"))), 1)

        recovered = self.fixture()
        self.assertEqual(recovered.bootstrap(recovered.write_envelope()).returncode, 0)
        recovered.sealed_work_item()
        (recovered.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(recovered.seal().returncode, 0)
        recovered.prepare_human_uat()
        recovered_body = recovered.write_inbox_text("completion.md", "Fictional crash recovery completion record.\n")
        fault = recovered.complete(
            recovered_body,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_completion_event"},
        )
        self.assertNotEqual(fault.returncode, 0)
        completion_capability_path = next(
            path
            for path in (recovered.root / ".exocortex/local/protocol/capabilities").glob("*.json")
            if json.loads(path.read_text(encoding="utf-8"))["operation"] == "complete_local_delivery"
        )
        completion_capability = json.loads(completion_capability_path.read_text(encoding="utf-8"))
        consumed_at = completion_capability["status"]["consumed_at"]
        completion_capability["status"]["consumed_at"] = "2099-01-01T00:00:00Z"
        write_json(completion_capability_path, completion_capability)
        invalid_clock = recovered.complete(recovered_body)
        self.assertNotEqual(invalid_clock.returncode, 0)
        self.assertIn("invalid_recovery_timestamp", invalid_clock.stdout)
        completion_capability["status"]["consumed_at"] = consumed_at
        write_json(completion_capability_path, completion_capability)
        retry = recovered.complete(recovered_body)
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
        self.assertEqual(len(list((recovered.root / ".exocortex/events").glob("*.md"))), 1)

        state_recovered = self.fixture()
        self.assertEqual(state_recovered.bootstrap(state_recovered.write_envelope()).returncode, 0)
        state_recovered.sealed_work_item()
        (state_recovered.root / "allowed.txt").write_text("approved source edit\n", encoding="utf-8")
        self.assertEqual(state_recovered.seal().returncode, 0)
        state_recovered.prepare_human_uat()
        state_body = state_recovered.write_inbox_text(
            "completion.md",
            "Fictional post-state-replacement recovery record.\n",
        )
        state_fault = state_recovered.complete(
            state_body,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_FAULT_POINT": "after_completion_state"},
        )
        self.assertNotEqual(state_fault.returncode, 0)
        state_journal_path = (
            state_recovered.root
            / ".exocortex/local/protocol/transactions/completion-complete-001.json"
        )
        self.assertEqual(json.loads(state_journal_path.read_text(encoding="utf-8"))["status"], "intent")
        state_work_path = state_recovered.root / ".exocortex/work-items/LOCAL-DELIVERY-WORK-001.json"
        state_capability_path = next(
            path
            for path in (state_recovered.root / ".exocortex/local/protocol/capabilities").glob("*.json")
            if json.loads(path.read_text(encoding="utf-8"))["operation"] == "complete_local_delivery"
        )
        state_event_path = next((state_recovered.root / ".exocortex/events").glob("*.md"))
        stable_recovery_bytes = {
            path: path.read_bytes()
            for path in (state_work_path, state_capability_path, state_event_path)
        }
        recovered_state_result = state_recovered.complete(state_body)
        self.assertEqual(
            recovered_state_result.returncode,
            0,
            recovered_state_result.stdout + recovered_state_result.stderr,
        )
        self.assertTrue(json.loads(recovered_state_result.stdout)["replay"])
        self.assertEqual(
            {path: path.read_bytes() for path in stable_recovery_bytes},
            stable_recovery_bytes,
        )
        self.assertEqual(
            json.loads(state_journal_path.read_text(encoding="utf-8"))["status"],
            "finalized",
        )


class RoutingAndEgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = ProtocolFixture()

    def tearDown(self) -> None:
        self.fx.close()

    def model_documents(self) -> tuple[dict, dict, dict]:
        sources = {
            "schema_version": "public-v2",
            "kind": "model_source_registry",
            "registry_version": 1,
            "observed_at": "2026-07-27T11:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "sources": [
                {
                    "id": "openai-models",
                    "provider_id": "openai",
                    "url": "https://developers.openai.com/api/docs/models",
                    "roles": ["models", "pricing", "lifecycle"],
                    "retrieved_at": "2026-07-27T11:00:00Z",
                    "content_sha256": "1" * 64,
                    "refresh_interval_hours": 168,
                }
            ],
        }
        profile = lambda profile_id, cost, evidence: {
            "id": profile_id,
            "status": "verified",
            "attempts": 10,
            "successes": 5,
            "total_cost_microusd": cost,
            "evidence_sha256": evidence,
            "evaluated_at": "2026-01-01T00:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
        }
        catalog = {
            "schema_version": "public-v2",
            "kind": "model_routing_catalog",
            "catalog_version": 1,
            "source_registry_digest": canonical_digest(sources),
            "observed_at": "2026-07-27T11:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
            "models": [
                {
                    "id": "tier-a",
                    "provider_id": "openai",
                    "display_name": "Tier A",
                    "lifecycle": "active",
                    "routing_status": "eligible",
                    "source_ids": ["openai-models"],
                    "input_microusd_per_mtok": 9000000,
                    "output_microusd_per_mtok": 9000000,
                    "capabilities": ["integrate", "search"],
                    "max_risk": "critical",
                    "parent_capable": True,
                    "evaluation_profiles": [
                        profile("integration-v1", 450, "2" * 64),
                        profile("search-v1", 150, "3" * 64),
                    ],
                },
                {
                    "id": "tier-b",
                    "provider_id": "openai",
                    "display_name": "Tier B",
                    "lifecycle": "active",
                    "routing_status": "eligible",
                    "source_ids": ["openai-models"],
                    "input_microusd_per_mtok": 1000000,
                    "output_microusd_per_mtok": 1000000,
                    "capabilities": ["integrate"],
                    "max_risk": "high",
                    "parent_capable": True,
                    "evaluation_profiles": [profile("integration-v1", 200, "4" * 64)],
                },
                {
                    "id": "tier-c",
                    "provider_id": "openai",
                    "display_name": "Tier C",
                    "lifecycle": "active",
                    "routing_status": "eligible",
                    "source_ids": ["openai-models"],
                    "input_microusd_per_mtok": 500000,
                    "output_microusd_per_mtok": 500000,
                    "capabilities": ["search"],
                    "max_risk": "low",
                    "parent_capable": False,
                    "evaluation_profiles": [profile("search-v1", 100, "5" * 64)],
                },
                {
                    "id": "unverified-new",
                    "provider_id": "openai",
                    "display_name": "Unverified New",
                    "lifecycle": "active",
                    "routing_status": "candidate",
                    "source_ids": ["openai-models"],
                    "input_microusd_per_mtok": 1,
                    "output_microusd_per_mtok": 1,
                    "capabilities": ["integrate", "search"],
                    "max_risk": "critical",
                    "parent_capable": True,
                    "evaluation_profiles": [],
                },
            ],
        }
        availability = {
            "schema_version": "public-v2",
            "kind": "model_availability",
            "catalog_digest": canonical_digest(catalog),
            "surface_id": "test-surface",
            "surface_version": "test-v1",
            "surface_session_id": "test-session",
            "scope": "current_surface_session",
            "observed_at": "2026-07-27T11:50:00Z",
            "expires_at": "2026-07-27T12:05:00Z",
            "evidence_sha256": "6" * 64,
            "model_ids": ["tier-a", "tier-b", "tier-c", "unverified-new"],
        }
        return sources, catalog, availability

    def live_model_documents(self) -> tuple[dict, dict, dict, datetime]:
        sources, catalog, availability = self.model_documents()
        route_now = datetime.now(timezone.utc).replace(microsecond=0)
        observed_at = route_now - timedelta(minutes=1)
        evidence_expires_at = route_now + timedelta(days=1)

        sources["observed_at"] = utc_text(observed_at)
        sources["expires_at"] = utc_text(evidence_expires_at)
        for source in sources["sources"]:
            source["retrieved_at"] = utc_text(observed_at)

        catalog["source_registry_digest"] = canonical_digest(sources)
        catalog["observed_at"] = utc_text(observed_at)
        catalog["expires_at"] = utc_text(evidence_expires_at)
        for model in catalog["models"]:
            for profile in model["evaluation_profiles"]:
                profile["evaluated_at"] = utc_text(route_now - timedelta(days=1))
                profile["expires_at"] = utc_text(evidence_expires_at)

        availability["catalog_digest"] = canonical_digest(catalog)
        availability["observed_at"] = utc_text(observed_at)
        availability["expires_at"] = utc_text(observed_at + timedelta(minutes=15))
        return sources, catalog, availability, route_now

    def test_fresh_cost_per_success_routing_without_model_pins(self) -> None:
        task_rel = "task.json"
        sources_rel = "sources.json"
        catalog_rel = "catalog.json"
        availability_rel = "availability.json"
        sources, catalog, availability, route_now = self.live_model_documents()
        write_json(
            self.fx.root / task_rel,
            {
                "required_capabilities": ["integrate"],
                "risk": "high",
                "evaluation_profile_id": "integration-v1",
                "max_cost_per_success_microusd": None,
                "delegates": [
                    {
                        "id": "evidence",
                        "required_capabilities": ["search"],
                        "risk": "low",
                        "evaluation_profile_id": "search-v1",
                        "max_cost_per_success_microusd": 30,
                    }
                ],
            },
        )
        write_json(self.fx.root / sources_rel, sources)
        write_json(self.fx.root / catalog_rel, catalog)
        write_json(self.fx.root / availability_rel, availability)
        result = run(
            [
                "python3",
                str(ORCHESTRATOR),
                "route",
                "--project-root",
                str(self.fx.root),
                "--task",
                task_rel,
                "--sources",
                sources_rel,
                "--catalog",
                catalog_rel,
                "--availability",
                availability_rel,
                "--as-of",
                utc_text(route_now),
                "--current-surface-id",
                "test-surface",
                "--current-surface-version",
                "test-v1",
                "--current-surface-session-id",
                "test-session",
            ],
            check=True,
        )
        output = json.loads(result.stdout)
        self.assertEqual(output["parent_model_id"], "tier-b")
        self.assertEqual(output["delegates"][0]["model_id"], "tier-c")
        self.assertEqual(output["parent_cost_per_success_microusd"], 40)
        self.assertEqual(output["delegates"][0]["cost_per_success_microusd"], 20)
        self.assertEqual(output["policy"], "fresh_source_backed_cost_per_success_v1")
        self.assertIn("source_registry_digest", output)
        self.assertIn("catalog_digest", output)
        self.assertIn("availability_digest", output)
        self.assertEqual(output["surface_id"], "test-surface")
        self.assertEqual(output["surface_version"], "test-v1")
        self.assertEqual(output["surface_session_id"], "test-session")
        self.assertEqual(output["availability_scope"], "current_surface_session")
        self.assertFalse(output["normative_model_pin"])

    def test_routing_rejects_surface_replay_and_overlong_session_evidence(self) -> None:
        task_rel = "task.json"
        sources_rel = "sources.json"
        catalog_rel = "catalog.json"
        availability_rel = "availability.json"
        sources, catalog, availability, route_now = self.live_model_documents()
        write_json(
            self.fx.root / task_rel,
            {
                "required_capabilities": ["integrate"],
                "risk": "high",
                "evaluation_profile_id": "integration-v1",
                "max_cost_per_success_microusd": None,
                "delegates": [],
            },
        )
        write_json(self.fx.root / sources_rel, sources)
        write_json(self.fx.root / catalog_rel, catalog)
        write_json(self.fx.root / availability_rel, availability)
        command = [
            "python3",
            str(ORCHESTRATOR),
            "route",
            "--project-root",
            str(self.fx.root),
            "--task",
            task_rel,
            "--sources",
            sources_rel,
            "--catalog",
            catalog_rel,
            "--availability",
            availability_rel,
            "--as-of",
            utc_text(route_now),
            "--current-surface-id",
            "test-surface",
            "--current-surface-version",
            "test-v1",
            "--current-surface-session-id",
            "other-session",
        ]
        replay = run(command)
        self.assertNotEqual(replay.returncode, 0)
        self.assertIn("availability_surface_mismatch", replay.stdout)

        observed_at = datetime.fromisoformat(availability["observed_at"].replace("Z", "+00:00"))
        availability["expires_at"] = utc_text(observed_at + timedelta(minutes=15, seconds=1))
        write_json(self.fx.root / availability_rel, availability)
        command[-1] = "test-session"
        overlong = run(command)
        self.assertNotEqual(overlong.returncode, 0)
        self.assertIn("invalid_freshness_window", overlong.stdout)

    def test_routing_rejects_stale_and_future_as_of_replay(self) -> None:
        sources, catalog, availability, route_now = self.live_model_documents()
        write_json(
            self.fx.root / "task.json",
            {
                "required_capabilities": ["integrate"],
                "risk": "high",
                "evaluation_profile_id": "integration-v1",
                "max_cost_per_success_microusd": None,
                "delegates": [],
            },
        )
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "availability.json", availability)

        command = [
            "python3",
            str(ORCHESTRATOR),
            "route",
            "--project-root",
            str(self.fx.root),
            "--task",
            "task.json",
            "--sources",
            "sources.json",
            "--catalog",
            "catalog.json",
            "--availability",
            "availability.json",
            "--as-of",
            "",
            "--current-surface-id",
            "test-surface",
            "--current-surface-version",
            "test-v1",
            "--current-surface-session-id",
            "test-session",
        ]
        as_of_index = command.index("--as-of") + 1
        for replay_time in (
            route_now - timedelta(minutes=5),
            route_now + timedelta(minutes=5),
        ):
            command[as_of_index] = utc_text(replay_time)
            replay = run(command)
            self.assertNotEqual(replay.returncode, 0)
            self.assertIn("routing_timestamp_out_of_bounds", replay.stdout)

    def test_stale_unavailable_and_unverified_models_fail_closed(self) -> None:
        task_rel = "task.json"
        sources_rel = "sources.json"
        catalog_rel = "catalog.json"
        availability_rel = "availability.json"
        sources, catalog, availability, route_now = self.live_model_documents()
        write_json(
            self.fx.root / task_rel,
            {
                "required_capabilities": ["integrate"],
                "risk": "high",
                "evaluation_profile_id": "integration-v1",
                "max_cost_per_success_microusd": None,
                "delegates": [],
            },
        )
        write_json(self.fx.root / sources_rel, sources)
        write_json(self.fx.root / catalog_rel, catalog)
        availability["model_ids"] = ["unverified-new"]
        availability["observed_at"] = utc_text(route_now - timedelta(minutes=30))
        availability["expires_at"] = utc_text(route_now - timedelta(minutes=15))
        write_json(self.fx.root / availability_rel, availability)
        command = [
            "python3",
            str(ORCHESTRATOR),
            "route",
            "--project-root",
            str(self.fx.root),
            "--task",
            task_rel,
            "--sources",
            sources_rel,
            "--catalog",
            catalog_rel,
            "--availability",
            availability_rel,
            "--as-of",
            utc_text(route_now),
            "--current-surface-id",
            "test-surface",
            "--current-surface-version",
            "test-v1",
            "--current-surface-session-id",
            "test-session",
        ]
        stale = run(command)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("stale_model_evidence", stale.stdout)
        availability["observed_at"] = utc_text(route_now - timedelta(minutes=1))
        availability["expires_at"] = utc_text(route_now + timedelta(minutes=14))
        write_json(self.fx.root / availability_rel, availability)
        unverified = run(command)
        self.assertNotEqual(unverified.returncode, 0)
        self.assertIn("no_capable_parent", unverified.stdout)

    def test_discovery_quarantines_unknown_models_without_writing(self) -> None:
        sources_rel = "sources.json"
        catalog_rel = "catalog.json"
        observation_rel = "observation.json"
        sources, catalog, _ = self.model_documents()
        write_json(self.fx.root / sources_rel, sources)
        write_json(self.fx.root / catalog_rel, catalog)
        observation = {
            "schema_version": "public-v2",
            "kind": "model_observation",
            "observed_at": "2026-07-27T11:00:00Z",
            "source_registry_digest": canonical_digest(sources),
            "source_observations": [
                {
                    "source_id": "openai-models",
                    "scope": "registered_source",
                    "complete_listing": False,
                    "retrieved_at": "2026-07-27T11:00:00Z",
                    "content_sha256": "1" * 64,
                    "models": [
                        {
                            "id": "brand-new",
                            "provider_id": "openai",
                            "display_name": "Brand New",
                            "lifecycle": "active",
                            "input_microusd_per_mtok": 1,
                            "output_microusd_per_mtok": 2,
                        }
                    ],
                }
            ],
        }
        write_json(self.fx.root / observation_rel, observation)
        before = {
            path.relative_to(self.fx.root).as_posix(): file_digest(path)
            for path in self.fx.root.rglob("*")
            if path.is_file()
        }
        result = run(
            [
                "python3",
                str(MODEL_REGISTRY),
                "discover",
                "--project-root",
                str(self.fx.root),
                "--sources",
                sources_rel,
                "--catalog",
                catalog_rel,
                "--candidate-sources",
                sources_rel,
                "--observation",
                observation_rel,
                "--as-of",
                "2026-07-27T12:00:00Z",
            ],
            check=True,
        )
        after = {
            path.relative_to(self.fx.root).as_posix(): file_digest(path)
            for path in self.fx.root.rglob("*")
            if path.is_file()
        }
        output = json.loads(result.stdout)
        self.assertEqual(before, after)
        self.assertEqual(output["quarantine_candidates"][0]["id"], "brand-new")
        self.assertFalse(any(item["code"] == "not_observed" for item in output["findings"]))
        self.assertFalse(output["auto_activation"])
        self.assertFalse(output["missing_means_deprecated"])
        self.assertFalse(output["network_used"])
        self.assertFalse(output["mutation_performed"])

    def test_prospective_refresh_uses_a_definition_identical_candidate_snapshot(self) -> None:
        baseline, catalog, _ = self.model_documents()
        candidate = copy.deepcopy(baseline)
        candidate["registry_version"] = 2
        candidate["observed_at"] = "2026-07-27T12:00:00Z"
        candidate["sources"][0]["retrieved_at"] = "2026-07-27T12:00:00Z"
        candidate["sources"][0]["content_sha256"] = "7" * 64
        observation = {
            "schema_version": "public-v2",
            "kind": "model_observation",
            "observed_at": "2026-07-27T12:00:00Z",
            "source_registry_digest": canonical_digest(candidate),
            "source_observations": [
                {
                    "source_id": "openai-models",
                    "scope": "registered_source",
                    "complete_listing": False,
                    "retrieved_at": candidate["sources"][0]["retrieved_at"],
                    "content_sha256": candidate["sources"][0]["content_sha256"],
                    "models": [
                        {
                            "id": "refreshed-new",
                            "provider_id": "openai",
                            "display_name": "Refreshed New",
                            "lifecycle": "active",
                            "input_microusd_per_mtok": 3,
                            "output_microusd_per_mtok": 4,
                        }
                    ],
                }
            ],
        }
        write_json(self.fx.root / "sources.json", baseline)
        write_json(self.fx.root / "candidate-sources.json", candidate)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "observation.json", observation)
        catalog_before = file_digest(self.fx.root / "catalog.json")
        command = [
            "python3",
            str(MODEL_REGISTRY),
            "discover",
            "--project-root",
            str(self.fx.root),
            "--sources",
            "sources.json",
            "--catalog",
            "catalog.json",
            "--candidate-sources",
            "candidate-sources.json",
            "--observation",
            "observation.json",
            "--as-of",
            "2026-07-27T12:30:00Z",
        ]
        refreshed = run(command, check=True)
        output = json.loads(refreshed.stdout)
        self.assertEqual(output["baseline_source_registry_digest"], canonical_digest(baseline))
        self.assertEqual(output["candidate_source_registry_digest"], canonical_digest(candidate))
        self.assertEqual(output["quarantine_candidates"][0]["id"], "refreshed-new")
        self.assertEqual(file_digest(self.fx.root / "catalog.json"), catalog_before)

        drifted = copy.deepcopy(candidate)
        drifted["sources"][0]["roles"] = ["models"]
        write_json(self.fx.root / "candidate-sources.json", drifted)
        definition_drift = run(command)
        self.assertNotEqual(definition_drift.returncode, 0)
        self.assertIn("source_definition_mismatch", definition_drift.stdout)

        write_json(self.fx.root / "candidate-sources.json", candidate)
        observation["source_registry_digest"] = canonical_digest(baseline)
        write_json(self.fx.root / "observation.json", observation)
        wrong_binding = run(command)
        self.assertNotEqual(wrong_binding.returncode, 0)
        self.assertIn("source_registry_digest_mismatch", wrong_binding.stdout)

    def test_role_scoped_observations_merge_without_false_changes(self) -> None:
        sources, catalog, _ = self.model_documents()
        sources["sources"][0]["roles"] = ["models", "lifecycle"]
        sources["sources"].append(
            {
                "id": "openai-pricing",
                "provider_id": "openai",
                "url": "https://developers.openai.com/api/docs/pricing",
                "roles": ["pricing"],
                "retrieved_at": "2026-07-27T11:00:00Z",
                "content_sha256": "7" * 64,
                "refresh_interval_hours": 168,
            }
        )
        for model in catalog["models"]:
            model["source_ids"] = ["openai-models", "openai-pricing"]
        catalog["source_registry_digest"] = canonical_digest(sources)
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)

        def observation(source_index: int, model: dict, *, complete: bool = False) -> dict:
            source = sources["sources"][source_index]
            return {
                "schema_version": "public-v2",
                "kind": "model_observation",
                "observed_at": "2026-07-27T11:00:00Z",
                "source_registry_digest": canonical_digest(sources),
                "source_observations": [
                    {
                        "source_id": source["id"],
                        "scope": "registered_source",
                        "complete_listing": complete,
                        "retrieved_at": source["retrieved_at"],
                        "content_sha256": source["content_sha256"],
                        "models": [model],
                    }
                ],
            }

        models_observation = observation(
            0,
            {
                "id": "split-new",
                "provider_id": "openai",
                "display_name": "Split New",
                "lifecycle": "active",
            },
        )
        pricing_observation = observation(
            1,
            {
                "id": "split-new",
                "provider_id": "openai",
                "input_microusd_per_mtok": 11,
                "output_microusd_per_mtok": 22,
            },
        )
        write_json(self.fx.root / "models-observation.json", models_observation)
        write_json(self.fx.root / "pricing-observation.json", pricing_observation)
        base = [
            "python3",
            str(MODEL_REGISTRY),
            "discover",
            "--project-root",
            str(self.fx.root),
            "--sources",
            "sources.json",
            "--catalog",
            "catalog.json",
            "--candidate-sources",
            "sources.json",
        ]
        outputs = []
        for order in (
            ["models-observation.json", "pricing-observation.json"],
            ["pricing-observation.json", "models-observation.json"],
        ):
            command = list(base)
            for path in order:
                command.extend(["--observation", path])
            command.extend(["--as-of", "2026-07-27T12:00:00Z"])
            outputs.append(json.loads(run(command, check=True).stdout))
        self.assertEqual(outputs[0], outputs[1])
        proposal = outputs[0]["quarantine_candidates"][0]
        self.assertEqual(proposal["display_name"], "Split New")
        self.assertEqual(proposal["input_microusd_per_mtok"], 11)
        self.assertEqual(proposal["source_ids"], ["openai-models", "openai-pricing"])

        omitted = observation(
            0,
            {"id": "tier-a", "provider_id": "openai", "display_name": "Tier A"},
        )
        write_json(self.fx.root / "omitted.json", omitted)
        omitted_command = list(base)
        omitted_command.extend(["--observation", "omitted.json", "--as-of", "2026-07-27T12:00:00Z"])
        omitted_output = json.loads(run(omitted_command, check=True).stdout)
        self.assertEqual(omitted_output["findings"], [])

        unauthorized_price = observation(
            0,
            {"id": "tier-a", "provider_id": "openai", "input_microusd_per_mtok": 1},
        )
        write_json(self.fx.root / "unauthorized.json", unauthorized_price)
        unauthorized_command = list(base)
        unauthorized_command.extend(
            ["--observation", "unauthorized.json", "--as-of", "2026-07-27T12:00:00Z"]
        )
        unauthorized_result = run(unauthorized_command)
        self.assertNotEqual(unauthorized_result.returncode, 0)
        self.assertIn("unauthorized_observation_field", unauthorized_result.stdout)

        pricing_complete = observation(
            1,
            {"id": "tier-a", "provider_id": "openai", "input_microusd_per_mtok": 1},
            complete=True,
        )
        write_json(self.fx.root / "unauthorized.json", pricing_complete)
        completeness_result = run(unauthorized_command)
        self.assertNotEqual(completeness_result.returncode, 0)
        self.assertIn("unauthorized_observation_completeness", completeness_result.stdout)

    def test_source_purpose_and_exact_observation_binding_fail_closed(self) -> None:
        sources, catalog, _ = self.model_documents()
        sources_path = self.fx.root / "sources.json"
        catalog_path = self.fx.root / "catalog.json"

        sources["sources"][0]["roles"] = ["availability"]
        catalog["source_registry_digest"] = canonical_digest(sources)
        write_json(sources_path, sources)
        write_json(catalog_path, catalog)
        missing_listing = run(
            [
                "python3",
                str(MODEL_REGISTRY),
                "validate-catalog",
                "--project-root",
                str(self.fx.root),
                "--sources",
                "sources.json",
                "--catalog",
                "catalog.json",
            ]
        )
        self.assertNotEqual(missing_listing.returncode, 0)
        self.assertIn("missing_model_source", missing_listing.stdout)

        sources, catalog, _ = self.model_documents()
        sources["sources"][0]["roles"] = ["models", "lifecycle"]
        catalog["source_registry_digest"] = canonical_digest(sources)
        write_json(sources_path, sources)
        write_json(catalog_path, catalog)
        missing_pricing = run(
            [
                "python3",
                str(MODEL_REGISTRY),
                "validate-catalog",
                "--project-root",
                str(self.fx.root),
                "--sources",
                "sources.json",
                "--catalog",
                "catalog.json",
            ]
        )
        self.assertNotEqual(missing_pricing.returncode, 0)
        self.assertIn("missing_pricing_source", missing_pricing.stdout)

        sources, catalog, _ = self.model_documents()
        write_json(sources_path, sources)
        write_json(catalog_path, catalog)
        observation = {
            "schema_version": "public-v2",
            "kind": "model_observation",
            "observed_at": "2026-07-27T11:00:00Z",
            "source_registry_digest": canonical_digest(sources),
            "source_observations": [
                {
                    "source_id": "openai-models",
                    "scope": "registered_source",
                    "complete_listing": False,
                    "retrieved_at": sources["sources"][0]["retrieved_at"],
                    "content_sha256": "9" * 64,
                    "models": [],
                }
            ],
        }
        write_json(self.fx.root / "observation.json", observation)
        mismatch = run(
            [
                "python3",
                str(MODEL_REGISTRY),
                "discover",
                "--project-root",
                str(self.fx.root),
                "--sources",
                "sources.json",
                "--catalog",
                "catalog.json",
                "--candidate-sources",
                "sources.json",
                "--observation",
                "observation.json",
                "--as-of",
                "2026-07-27T12:00:00Z",
            ]
        )
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("source_content_mismatch", mismatch.stdout)

    def test_source_and_expiry_boundaries_fail_closed(self) -> None:
        task = {
            "required_capabilities": ["integrate"],
            "risk": "high",
            "evaluation_profile_id": "integration-v1",
            "max_cost_per_success_microusd": None,
            "delegates": [],
        }
        sources, catalog, availability, route_now = self.live_model_documents()
        sources["sources"][0]["retrieved_at"] = utc_text(route_now - timedelta(days=8))
        catalog["source_registry_digest"] = canonical_digest(sources)
        availability["catalog_digest"] = canonical_digest(catalog)
        write_json(self.fx.root / "task.json", task)
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "availability.json", availability)
        command = [
            "python3",
            str(ORCHESTRATOR),
            "route",
            "--project-root",
            str(self.fx.root),
            "--task",
            "task.json",
            "--sources",
            "sources.json",
            "--catalog",
            "catalog.json",
            "--availability",
            "availability.json",
            "--current-surface-id",
            "test-surface",
            "--current-surface-version",
            "test-v1",
            "--current-surface-session-id",
            "test-session",
            "--as-of",
            utc_text(route_now),
        ]
        stale_source = run(command)
        self.assertNotEqual(stale_source.returncode, 0)
        self.assertIn("no_capable_parent", stale_source.stdout)

        sources, catalog, availability, route_now = self.live_model_documents()
        availability["expires_at"] = utc_text(route_now)
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "availability.json", availability)
        command[-1] = utc_text(route_now)
        expiry_boundary = run(command)
        self.assertNotEqual(expiry_boundary.returncode, 0)
        self.assertIn("stale_model_evidence", expiry_boundary.stdout)

        sources, catalog, availability, route_now = self.live_model_documents()
        for model in catalog["models"]:
            for profile in model["evaluation_profiles"]:
                profile["expires_at"] = utc_text(route_now)
        availability["catalog_digest"] = canonical_digest(catalog)
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "availability.json", availability)
        command[-1] = utc_text(route_now)
        expired_profile = run(command)
        self.assertNotEqual(expired_profile.returncode, 0)
        self.assertIn("no_capable_parent", expired_profile.stdout)

    def test_availability_requires_fresh_referenced_sources_only(self) -> None:
        sources, catalog, availability = self.model_documents()
        availability["model_ids"] = ["tier-a"]
        availability["catalog_digest"] = canonical_digest(catalog)
        availability["observed_at"] = "2026-08-03T10:55:00Z"
        availability["expires_at"] = "2026-08-03T11:10:00Z"
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "availability.json", availability)
        command = [
            "python3",
            str(MODEL_REGISTRY),
            "validate-availability",
            "--project-root",
            str(self.fx.root),
            "--sources",
            "sources.json",
            "--catalog",
            "catalog.json",
            "--availability",
            "availability.json",
            "--as-of",
            "2026-08-03T11:00:00Z",
        ]
        deadline = run(command)
        self.assertNotEqual(deadline.returncode, 0)
        self.assertIn("stale_source_evidence", deadline.stdout)
        command[-1] = "2026-08-03T10:59:59Z"
        self.assertTrue(json.loads(run(command, check=True).stdout)["ok"])

        sources, catalog, availability = self.model_documents()
        sources["sources"].append(
            {
                "id": "openai-stale",
                "provider_id": "openai",
                "url": "https://developers.openai.com/api/docs/models/stale-fixture",
                "roles": ["models", "pricing", "lifecycle"],
                "retrieved_at": "2026-01-01T00:00:00Z",
                "content_sha256": "7" * 64,
                "refresh_interval_hours": 1,
            }
        )
        catalog["models"][-1]["source_ids"] = ["openai-stale"]
        catalog["source_registry_digest"] = canonical_digest(sources)
        availability["catalog_digest"] = canonical_digest(catalog)
        availability["model_ids"] = ["tier-a"]
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "availability.json", availability)
        command[-1] = "2026-07-27T12:00:00Z"
        absent_stale_source = run(command, check=True)
        self.assertTrue(json.loads(absent_stale_source.stdout)["ok"])

    def test_duplicate_delegate_ids_fail_closed(self) -> None:
        sources, catalog, availability, route_now = self.live_model_documents()
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)
        write_json(self.fx.root / "availability.json", availability)
        base_delegate = {
            "id": "duplicate",
            "required_capabilities": ["search"],
            "risk": "low",
            "evaluation_profile_id": "search-v1",
            "max_cost_per_success_microusd": None,
        }
        command = [
            "python3",
            str(ORCHESTRATOR),
            "route",
            "--project-root",
            str(self.fx.root),
            "--task",
            "task.json",
            "--sources",
            "sources.json",
            "--catalog",
            "catalog.json",
            "--availability",
            "availability.json",
            "--current-surface-id",
            "test-surface",
            "--current-surface-version",
            "test-v1",
            "--current-surface-session-id",
            "test-session",
            "--as-of",
            utc_text(route_now),
        ]
        for second in (
            copy.deepcopy(base_delegate),
            {
                **base_delegate,
                "required_capabilities": ["integrate"],
                "risk": "high",
                "evaluation_profile_id": "integration-v1",
            },
        ):
            write_json(
                self.fx.root / "task.json",
                {
                    "required_capabilities": ["integrate"],
                    "risk": "high",
                    "evaluation_profile_id": "integration-v1",
                    "max_cost_per_success_microusd": None,
                    "delegates": [base_delegate, second],
                },
            )
            duplicate = run(command)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("duplicate_delegate_id", duplicate.stdout)

    def test_model_schema_and_runtime_id_limits_match(self) -> None:
        schema_paths = (
            ".exocortex/schemas/model-source-registry.schema.json",
            ".exocortex/schemas/model-routing-catalog.schema.json",
            ".exocortex/schemas/model-observation.schema.json",
            ".exocortex/schemas/model-availability.schema.json",
        )
        patterns = {
            json.loads((TEMPLATE / path).read_text(encoding="utf-8"))["$defs"]["id"]["pattern"]
            for path in schema_paths
        }
        self.assertEqual(patterns, {"^[a-z0-9][a-z0-9._-]{0,127}$"})
        pattern = re.compile(next(iter(patterns)))
        self.assertIsNotNone(pattern.fullmatch("a" * 128))
        self.assertIsNone(pattern.fullmatch("a" * 129))

        sources, _, _ = self.model_documents()
        sources["sources"][0]["id"] = "a" * 128
        write_json(self.fx.root / "sources.json", sources)
        command = [
            "python3",
            str(MODEL_REGISTRY),
            "validate-sources",
            "--project-root",
            str(self.fx.root),
            "--sources",
            "sources.json",
        ]
        self.assertTrue(json.loads(run(command, check=True).stdout)["ok"])
        sources["sources"][0]["id"] = "a" * 129
        write_json(self.fx.root / "sources.json", sources)
        too_long = run(command)
        self.assertNotEqual(too_long.returncode, 0)
        self.assertIn("invalid_id", too_long.stdout)

    def test_cross_observation_conflicts_and_duplicate_json_keys_fail_closed(self) -> None:
        sources, catalog, _ = self.model_documents()
        sources["sources"].append(
            {
                "id": "openai-models-alt",
                "provider_id": "openai",
                "url": "https://developers.openai.com/api/docs/models/compare",
                "roles": ["models"],
                "retrieved_at": "2026-07-27T11:00:00Z",
                "content_sha256": "7" * 64,
                "refresh_interval_hours": 168,
            }
        )
        catalog["source_registry_digest"] = canonical_digest(sources)
        write_json(self.fx.root / "sources.json", sources)
        write_json(self.fx.root / "catalog.json", catalog)

        def observation(source_index: int, model_id: str, display_name: str) -> dict:
            source = sources["sources"][source_index]
            return {
                "schema_version": "public-v2",
                "kind": "model_observation",
                "observed_at": "2026-07-27T11:00:00Z",
                "source_registry_digest": canonical_digest(sources),
                "source_observations": [
                    {
                        "source_id": source["id"],
                        "scope": "registered_source",
                        "complete_listing": False,
                        "retrieved_at": source["retrieved_at"],
                        "content_sha256": source["content_sha256"],
                        "models": [
                            {
                                "id": model_id,
                                "provider_id": "openai",
                                "display_name": display_name,
                            }
                        ],
                    }
                ],
            }

        base = [
            "python3",
            str(MODEL_REGISTRY),
            "discover",
            "--project-root",
            str(self.fx.root),
            "--sources",
            "sources.json",
            "--catalog",
            "catalog.json",
            "--candidate-sources",
            "sources.json",
        ]
        for model_id in ("conflicting-new", "tier-a"):
            write_json(self.fx.root / "observation-a.json", observation(0, model_id, "First"))
            write_json(self.fx.root / "observation-b.json", observation(1, model_id, "Second"))
            for order in (
                ["observation-a.json", "observation-b.json"],
                ["observation-b.json", "observation-a.json"],
            ):
                command = list(base)
                for path in order:
                    command.extend(["--observation", path])
                command.extend(["--as-of", "2026-07-27T12:00:00Z"])
                result = run(command)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("conflicting_observation", result.stdout)

        duplicate_source = observation(0, "tier-a", "Tier A")
        write_json(self.fx.root / "observation-a.json", duplicate_source)
        write_json(self.fx.root / "observation-b.json", duplicate_source)
        duplicate_source_command = list(base)
        duplicate_source_command.extend(["--observation", "observation-a.json"])
        duplicate_source_command.extend(["--observation", "observation-b.json"])
        duplicate_source_command.extend(["--as-of", "2026-07-27T12:00:00Z"])
        duplicate_source_result = run(duplicate_source_command)
        self.assertNotEqual(duplicate_source_result.returncode, 0)
        self.assertIn("duplicate_source_observation", duplicate_source_result.stdout)

        (self.fx.root / "duplicate.json").write_text(
            '{"schema_version":"public-v2","kind":"model_source_registry",'
            '"kind":"model_source_registry","registry_version":1,'
            '"observed_at":"2026-07-27T11:00:00Z",'
            '"expires_at":"2026-07-28T11:00:00Z","sources":[]}\n',
            encoding="utf-8",
        )
        duplicate = run(
            [
                "python3",
                str(MODEL_REGISTRY),
                "validate-sources",
                "--project-root",
                str(self.fx.root),
                "--sources",
                "duplicate.json",
            ]
        )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("duplicate_json_key", duplicate.stdout)

    def test_production_catalog_is_advisory_and_offline(self) -> None:
        source_text = MODEL_REGISTRY.read_text(encoding="utf-8")
        for forbidden in ("urlopen(", "requests.", "http.client", "os.environ", "socket."):
            self.assertNotIn(forbidden, source_text)
        catalog = json.loads((TEMPLATE / ".exocortex/model-routing-catalog.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(catalog["models"]), 20)
        self.assertTrue(all(model["routing_status"] == "candidate" for model in catalog["models"]))
        self.assertTrue(all(model["evaluation_profiles"] == [] for model in catalog["models"]))
        help_text = run(["python3", str(MODEL_REGISTRY), "--help"], check=True).stdout
        for forbidden in ("fetch", "activate", "promote", "--output", "credential"):
            self.assertNotIn(forbidden, help_text)

    def test_egress_stage_send_and_pre_payload_denials(self) -> None:
        payload_rel = "exports/fixture.json"
        payload_path = self.fx.root / payload_rel
        payload_path.parent.mkdir()
        payload_path.write_text('{"fixture":true}\n', encoding="utf-8")
        inspect_cap = self.fx.capability("inspect", "inspect_egress_payload", 0, [payload_rel])
        inspect = self.fx.egress(
            "inspect", inspect_cap, "inspect-request",
            ["--payload", payload_rel, "--payload-class", "test-evidence", "--media-type", "application/json"],
            check=True,
        )
        proposal = json.loads(inspect.stdout)
        self.assertEqual(json.loads((self.fx.root / inspect_cap).read_text())["status"]["state"], "consumed")
        self.assertFalse((self.fx.root / proposal["object_path"]).exists())
        self.assertFalse((self.fx.root / proposal["descriptor_path"]).exists())
        stage_paths = [
            payload_rel,
            proposal["object_path"],
            proposal["descriptor_path"],
            stage_transaction("stage-request"),
            AUDIT_REL,
        ]
        surplus_stage_cap = self.fx.capability(
            "stage-surplus",
            "prepare_egress_payload",
            0,
            [*stage_paths, ".exocortex/UNRELATED-STAGE.md"],
            target_sha=proposal["payload_digest"],
            payload_digest=proposal["payload_digest"],
        )
        surplus_stage = self.fx.egress(
            "stage",
            surplus_stage_cap,
            "stage-request",
            [
                "--payload", payload_rel,
                "--payload-class", "test-evidence",
                "--media-type", "application/json",
                "--expected-payload-digest", proposal["payload_digest"],
                "--expected-byte-size", str(proposal["byte_size"]),
            ],
        )
        self.assertNotEqual(surplus_stage.returncode, 0)
        self.assertIn("path_set_mismatch", surplus_stage.stdout)
        self.assertEqual(json.loads((self.fx.root / surplus_stage_cap).read_text())["status"]["state"], "active")
        self.assertFalse((self.fx.root / proposal["object_path"]).exists())
        stage_cap = self.fx.capability(
            "stage", "prepare_egress_payload", 0,
            stage_paths,
            target_sha=proposal["payload_digest"], payload_digest=proposal["payload_digest"],
        )
        stage = run([
            "python3", str(EGRESS), "stage", "--project-root", str(self.fx.root),
            "--capability", stage_cap, "--work-item-id", "TEST-WORK-001", "--work-item-revision", "0",
            "--request-id", "stage-request", "--surface-id", self.fx.surface, "--executor-id", self.fx.executor,
            "--adapter-version", self.fx.adapter, "--payload", payload_rel, "--payload-class", "test-evidence",
            "--media-type", "application/json", "--expected-payload-digest", proposal["payload_digest"],
            "--expected-byte-size", str(proposal["byte_size"]),
        ], check=True)
        descriptor = json.loads(stage.stdout)
        self.assertTrue((self.fx.root / proposal["object_path"]).is_file())
        self.assertTrue((self.fx.root / proposal["descriptor_path"]).is_file())

        policy = {"schema_version": "public-v2", "kind": "external_sync_policy", "default": "deny", "policy_version": 1, "destinations": [{"destination_id": "fake-destination", "transport": "fake", "methods": ["POST"], "endpoint": "fixture://sink", "credential_env": None, "status": "active", "max_payload_bytes": 1024}]}
        write_json(self.fx.root / ".exocortex/control/EXTERNAL_SYNC_POLICY.json", policy)
        output_rel = ".exocortex/local/protocol/test-output.json"
        send_paths = [proposal["descriptor_path"], AUDIT_REL, output_rel]
        surplus_send_cap = self.fx.capability(
            "send-surplus",
            "external_sync",
            0,
            [*send_paths, ".exocortex/UNRELATED-SEND.md"],
            target_sha=canonical_digest(policy),
            destination_id="fake-destination",
            method="POST",
            payload_descriptor_id=descriptor["descriptor_id"],
            payload_digest=proposal["payload_digest"],
        )
        surplus_send = self.fx.egress(
            "send",
            surplus_send_cap,
            "send-surplus",
            [
                "--descriptor", proposal["descriptor_path"],
                "--destination-id", "fake-destination",
                "--method", "POST",
                "--fake-output", output_rel,
            ],
            env={"EXOCORTEX_TEST_MODE": "1"},
        )
        self.assertNotEqual(surplus_send.returncode, 0)
        self.assertIn("path_set_mismatch", surplus_send.stdout)
        self.assertEqual(json.loads((self.fx.root / surplus_send_cap).read_text())["status"]["state"], "active")
        self.assertFalse((self.fx.root / output_rel).exists())
        send_cap = self.fx.capability(
            "send", "external_sync", 0, send_paths,
            target_sha=canonical_digest(policy), destination_id="fake-destination", method="POST",
            payload_descriptor_id=descriptor["descriptor_id"], payload_digest=proposal["payload_digest"],
        )
        send_args = [
            "python3", str(EGRESS), "send", "--project-root", str(self.fx.root), "--capability", send_cap,
            "--work-item-id", "TEST-WORK-001", "--work-item-revision", "0", "--request-id", "send-request",
            "--surface-id", self.fx.surface, "--executor-id", self.fx.executor, "--adapter-version", self.fx.adapter,
            "--descriptor", proposal["descriptor_path"], "--destination-id", "fake-destination", "--method", "POST",
            "--fake-output", output_rel,
        ]
        denied = run(send_args)
        self.assertNotEqual(denied.returncode, 0)
        self.assertIn("fake_transport_disabled", denied.stdout)
        self.assertEqual(json.loads((self.fx.root / send_cap).read_text())["status"]["state"], "active")
        sent = run(send_args, env={"EXOCORTEX_TEST_MODE": "1"}, check=True)
        self.assertEqual(json.loads(sent.stdout)["status"], "fake_delivered")
        self.assertTrue((self.fx.root / output_rel).is_file())

    def test_revocation_after_credential_lookup_blocks_transport(self) -> None:
        payload_rel = "exports/revoke.txt"
        (self.fx.root / "exports").mkdir()
        (self.fx.root / payload_rel).write_text("fixture\n", encoding="utf-8")
        inspect_cap = self.fx.capability("inspect-r", "inspect_egress_payload", 0, [payload_rel])
        proposal = json.loads(self.fx.egress("inspect", inspect_cap, "inspect-r", ["--payload", payload_rel, "--payload-class", "fixture"], check=True).stdout)
        stage_cap = self.fx.capability("stage-r", "prepare_egress_payload", 0, [payload_rel, proposal["object_path"], proposal["descriptor_path"], stage_transaction("stage-r"), AUDIT_REL], target_sha=proposal["payload_digest"], payload_digest=proposal["payload_digest"])
        run(["python3", str(EGRESS), "stage", "--project-root", str(self.fx.root), "--capability", stage_cap, "--work-item-id", "TEST-WORK-001", "--work-item-revision", "0", "--request-id", "stage-r", "--surface-id", self.fx.surface, "--executor-id", self.fx.executor, "--adapter-version", self.fx.adapter, "--payload", payload_rel, "--payload-class", "fixture", "--expected-payload-digest", proposal["payload_digest"], "--expected-byte-size", str(proposal["byte_size"])], check=True)
        descriptor = json.loads((self.fx.root / proposal["descriptor_path"]).read_text())
        policy = {"schema_version": "public-v2", "kind": "external_sync_policy", "default": "deny", "policy_version": 1, "destinations": [{"destination_id": "credential-fake", "transport": "fake", "methods": ["POST"], "endpoint": "fixture://sink", "credential_env": "EXO_FIXTURE_CREDENTIAL", "status": "active", "max_payload_bytes": 1024}]}
        write_json(self.fx.root / ".exocortex/control/EXTERNAL_SYNC_POLICY.json", policy)
        output_rel = ".exocortex/local/protocol/revoked-output.json"
        cap = self.fx.capability("send-r", "external_sync", 0, [proposal["descriptor_path"], AUDIT_REL, output_rel], target_sha=canonical_digest(policy), destination_id="credential-fake", method="POST", payload_descriptor_id=descriptor["descriptor_id"], payload_digest=proposal["payload_digest"])
        result = run(["python3", str(EGRESS), "send", "--project-root", str(self.fx.root), "--capability", cap, "--work-item-id", "TEST-WORK-001", "--work-item-revision", "0", "--request-id", "send-r", "--surface-id", self.fx.surface, "--executor-id", self.fx.executor, "--adapter-version", self.fx.adapter, "--descriptor", proposal["descriptor_path"], "--destination-id", "credential-fake", "--method", "POST", "--fake-output", output_rel], env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_TEST_REVOKE_AFTER_CREDENTIAL": "1", "EXO_FIXTURE_CREDENTIAL": "fictional-test-value"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inactive_capability", result.stdout)
        self.assertFalse((self.fx.root / output_rel).exists())

    def test_symlink_payload_is_denied_before_capability_consumption(self) -> None:
        target = self.fx.root / "payload.txt"
        target.write_text("fixture", encoding="utf-8")
        link = self.fx.root / "payload-link.txt"
        link.symlink_to(target)
        cap = self.fx.capability("inspect-link", "inspect_egress_payload", 0, ["payload-link.txt"])
        result = self.fx.egress("inspect", cap, "inspect-link", ["--payload", "payload-link.txt", "--payload-class", "fixture"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink_target", result.stdout)
        self.assertEqual(json.loads((self.fx.root / cap).read_text())["status"]["state"], "active")

    def test_inspect_requires_exact_source_capability(self) -> None:
        payload_rel = "exports/private-fixture.txt"
        (self.fx.root / "exports").mkdir()
        (self.fx.root / payload_rel).write_text("fixture\n", encoding="utf-8")
        wrong = self.fx.capability("inspect-wrong", "inspect_egress_payload", 0, ["exports/other.txt"])
        result = self.fx.egress(
            "inspect", wrong, "inspect-wrong",
            ["--payload", payload_rel, "--payload-class", "fixture"],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("path_not_allowed", result.stdout)
        self.assertEqual(json.loads((self.fx.root / wrong).read_text())["status"]["state"], "active")
        self.assertFalse((self.fx.root / ".exocortex/local/protocol/descriptors").exists())
        surplus = self.fx.capability(
            "inspect-surplus",
            "inspect_egress_payload",
            0,
            [payload_rel, "exports/other.txt"],
        )
        surplus_result = self.fx.egress(
            "inspect", surplus, "inspect-surplus",
            ["--payload", payload_rel, "--payload-class", "fixture"],
        )
        self.assertNotEqual(surplus_result.returncode, 0)
        self.assertIn("path_set_mismatch", surplus_result.stdout)
        self.assertEqual(json.loads((self.fx.root / surplus).read_text())["status"]["state"], "active")

    def test_send_rejects_plaintext_endpoint_for_https_transport(self) -> None:
        payload_rel = "exports/plaintext.txt"
        (self.fx.root / "exports").mkdir()
        (self.fx.root / payload_rel).write_text("fixture\n", encoding="utf-8")
        inspect_cap = self.fx.capability("inspect-plaintext", "inspect_egress_payload", 0, [payload_rel])
        proposal = json.loads(self.fx.egress("inspect", inspect_cap, "inspect-plaintext", ["--payload", payload_rel, "--payload-class", "fixture"], check=True).stdout)
        stage_cap = self.fx.capability("stage-plaintext", "prepare_egress_payload", 0, [payload_rel, proposal["object_path"], proposal["descriptor_path"], stage_transaction("stage-plaintext"), AUDIT_REL], target_sha=proposal["payload_digest"], payload_digest=proposal["payload_digest"])
        self.fx.egress("stage", stage_cap, "stage-plaintext", ["--payload", payload_rel, "--payload-class", "fixture", "--expected-payload-digest", proposal["payload_digest"], "--expected-byte-size", str(proposal["byte_size"])], check=True)
        descriptor = json.loads((self.fx.root / proposal["descriptor_path"]).read_text())
        policy = {"schema_version": "public-v2", "kind": "external_sync_policy", "default": "deny", "policy_version": 1, "destinations": [{"destination_id": "plaintext-https", "transport": "https_json", "methods": ["POST"], "endpoint": "http://sink.example.com/hook", "credential_env": None, "status": "active", "max_payload_bytes": 1024}]}
        write_json(self.fx.root / ".exocortex/control/EXTERNAL_SYNC_POLICY.json", policy)
        cap = self.fx.capability("send-plaintext", "external_sync", 0, [proposal["descriptor_path"], AUDIT_REL], target_sha=canonical_digest(policy), destination_id="plaintext-https", method="POST", payload_descriptor_id=descriptor["descriptor_id"], payload_digest=proposal["payload_digest"])
        result = self.fx.egress(
            "send", cap, "send-plaintext",
            ["--descriptor", proposal["descriptor_path"], "--destination-id", "plaintext-https", "--method", "POST"],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid_endpoint_scheme", result.stdout)
        self.assertEqual(json.loads((self.fx.root / cap).read_text())["status"]["state"], "active")

    def test_policy_change_after_credential_lookup_blocks_transport(self) -> None:
        payload_rel = "exports/policy.txt"
        (self.fx.root / "exports").mkdir()
        (self.fx.root / payload_rel).write_text("fixture\n", encoding="utf-8")
        inspect_cap = self.fx.capability("inspect-policy", "inspect_egress_payload", 0, [payload_rel])
        proposal = json.loads(self.fx.egress("inspect", inspect_cap, "inspect-policy", ["--payload", payload_rel, "--payload-class", "fixture"], check=True).stdout)
        stage_cap = self.fx.capability("stage-policy", "prepare_egress_payload", 0, [payload_rel, proposal["object_path"], proposal["descriptor_path"], stage_transaction("stage-policy"), AUDIT_REL], target_sha=proposal["payload_digest"], payload_digest=proposal["payload_digest"])
        self.fx.egress("stage", stage_cap, "stage-policy", ["--payload", payload_rel, "--payload-class", "fixture", "--expected-payload-digest", proposal["payload_digest"], "--expected-byte-size", str(proposal["byte_size"])], check=True)
        descriptor = json.loads((self.fx.root / proposal["descriptor_path"]).read_text())
        policy = {"schema_version": "public-v2", "kind": "external_sync_policy", "default": "deny", "policy_version": 1, "destinations": [{"destination_id": "policy-fake", "transport": "fake", "methods": ["POST"], "endpoint": "fixture://sink", "credential_env": "EXO_FIXTURE_CREDENTIAL", "status": "active", "max_payload_bytes": 1024}]}
        write_json(self.fx.root / ".exocortex/control/EXTERNAL_SYNC_POLICY.json", policy)
        output_rel = ".exocortex/local/protocol/policy-output.json"
        cap = self.fx.capability("send-policy", "external_sync", 0, [proposal["descriptor_path"], AUDIT_REL, output_rel], target_sha=canonical_digest(policy), destination_id="policy-fake", method="POST", payload_descriptor_id=descriptor["descriptor_id"], payload_digest=proposal["payload_digest"])
        result = self.fx.egress(
            "send", cap, "send-policy",
            ["--descriptor", proposal["descriptor_path"], "--destination-id", "policy-fake", "--method", "POST", "--fake-output", output_rel],
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_TEST_CHANGE_POLICY_AFTER_CREDENTIAL": "1", "EXO_FIXTURE_CREDENTIAL": "fictional-test-value"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("policy_changed", result.stdout)
        self.assertFalse((self.fx.root / output_rel).exists())
        self.assertEqual(json.loads((self.fx.root / cap).read_text())["status"]["state"], "active")

    def test_stage_fault_recovers_once_and_audit_tampering_is_detected(self) -> None:
        payload_rel = "exports/recovery.txt"
        (self.fx.root / "exports").mkdir()
        (self.fx.root / payload_rel).write_text("recoverable fixture\n", encoding="utf-8")
        inspect_cap = self.fx.capability("inspect-recovery", "inspect_egress_payload", 0, [payload_rel])
        proposal = json.loads(self.fx.egress("inspect", inspect_cap, "inspect-recovery", ["--payload", payload_rel, "--payload-class", "fixture"], check=True).stdout)
        request_id = "stage-recovery"
        transaction_rel = stage_transaction(request_id)
        stage_cap = self.fx.capability(
            "stage-recovery",
            "prepare_egress_payload",
            0,
            [payload_rel, proposal["object_path"], proposal["descriptor_path"], transaction_rel, AUDIT_REL],
            target_sha=proposal["payload_digest"],
            payload_digest=proposal["payload_digest"],
        )
        extra = [
            "--payload", payload_rel,
            "--payload-class", "fixture",
            "--expected-payload-digest", proposal["payload_digest"],
            "--expected-byte-size", str(proposal["byte_size"]),
        ]
        faulted = self.fx.egress(
            "stage", stage_cap, request_id, extra,
            env={"EXOCORTEX_TEST_MODE": "1", "EXOCORTEX_EGRESS_STAGE_FAULT": "after_object"},
        )
        self.assertNotEqual(faulted.returncode, 0)
        self.assertIn("injected_stage_fault", faulted.stdout)
        self.assertEqual(json.loads((self.fx.root / stage_cap).read_text())["status"]["state"], "consumed")
        self.assertTrue((self.fx.root / proposal["object_path"]).is_file())
        self.assertFalse((self.fx.root / proposal["descriptor_path"]).exists())

        recovered = self.fx.egress("stage", stage_cap, request_id, extra, check=True)
        self.assertEqual(json.loads(recovered.stdout)["descriptor_id"], proposal["descriptor_id"])
        self.assertEqual(json.loads((self.fx.root / transaction_rel).read_text())["status"], "complete")
        audit_path = self.fx.root / AUDIT_REL
        verified = run(["python3", str(EGRESS), "verify-audit", "--project-root", str(self.fx.root)], check=True)
        self.assertEqual(json.loads(verified.stdout)["record_count"], 1)

        evidence_output = os.environ.get("EXOCORTEX_AUDIT_EVIDENCE_PATH")
        if evidence_output:
            Path(evidence_output).write_bytes(audit_path.read_bytes())

        records = audit_path.read_text(encoding="utf-8").splitlines()
        first = json.loads(records[0])
        first["event"] = "tampered"
        records[0] = json.dumps(first, sort_keys=True)
        audit_path.write_text("\n".join(records) + "\n", encoding="utf-8")
        tampered = run(["python3", str(EGRESS), "verify-audit", "--project-root", str(self.fx.root)])
        self.assertNotEqual(tampered.returncode, 0)
        self.assertIn("invalid_audit_chain", tampered.stdout)

    def test_concurrent_same_request_stage_converges_once(self) -> None:
        payload_rel = "exports/concurrent.txt"
        (self.fx.root / "exports").mkdir()
        (self.fx.root / payload_rel).write_text("concurrent fixture\n", encoding="utf-8")
        inspect_cap = self.fx.capability("inspect-concurrent", "inspect_egress_payload", 0, [payload_rel])
        proposal = json.loads(
            self.fx.egress(
                "inspect",
                inspect_cap,
                "inspect-concurrent",
                ["--payload", payload_rel, "--payload-class", "fixture"],
                check=True,
            ).stdout
        )
        request_id = "stage-concurrent"
        transaction_rel = stage_transaction(request_id)
        stage_cap = self.fx.capability(
            "stage-concurrent",
            "prepare_egress_payload",
            0,
            [payload_rel, proposal["object_path"], proposal["descriptor_path"], transaction_rel, AUDIT_REL],
            target_sha=proposal["payload_digest"],
            payload_digest=proposal["payload_digest"],
        )
        extra = [
            "--payload", payload_rel,
            "--payload-class", "fixture",
            "--expected-payload-digest", proposal["payload_digest"],
            "--expected-byte-size", str(proposal["byte_size"]),
        ]

        def stage_once(_: int) -> subprocess.CompletedProcess:
            return self.fx.egress("stage", stage_cap, request_id, extra)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(stage_once, range(2)))
        self.assertEqual([result.returncode for result in results], [0, 0])
        self.assertTrue(all(json.loads(result.stdout)["descriptor_id"] == proposal["descriptor_id"] for result in results))
        self.assertEqual(json.loads((self.fx.root / transaction_rel).read_text())["status"], "complete")
        verified = run(["python3", str(EGRESS), "verify-audit", "--project-root", str(self.fx.root)], check=True)
        self.assertEqual(json.loads(verified.stdout)["record_count"], 1)
        records = [json.loads(line) for line in (self.fx.root / AUDIT_REL).read_text(encoding="utf-8").splitlines()]
        self.assertEqual([record["event"] for record in records], ["payload_staged"])


class ReconciliationPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="exo-reconciliation-")
        self.root = Path(self.temp.name)
        self.target = self.root / "target"
        self.template = self.root / "template"
        self.target.mkdir()
        self.template.mkdir()
        (self.target / ".exocortex/local/update-reconciliation/objects").mkdir(parents=True)
        (self.target / "AI_START_HERE.md").write_text("target entry\n", encoding="utf-8")
        (self.target / ".exocortex/local/update-reconciliation/objects/AI_START_HERE.md").write_text(
            "reviewed merged entry\n",
            encoding="utf-8",
        )
        (self.template / "AI_START_HERE.md").write_text("candidate entry\n", encoding="utf-8")
        os.chmod(self.target / "AI_START_HERE.md", 0o644)
        os.chmod(
            self.target / ".exocortex/local/update-reconciliation/objects/AI_START_HERE.md",
            0o755,
        )
        os.chmod(self.template / "AI_START_HERE.md", 0o755)
        (self.template / "FILEMODES").write_text(
            "0755  AI_START_HERE.md\n"
            "0644  FILEMODES\n"
            "0644  SHA256SUMS\n",
            encoding="utf-8",
        )
        os.chmod(self.template / "FILEMODES", 0o644)
        candidate_hash = file_digest(self.template / "AI_START_HERE.md")
        filemodes_hash = file_digest(self.template / "FILEMODES")
        (self.template / "SHA256SUMS").write_text(
            f"{candidate_hash}  AI_START_HERE.md\n"
            f"{filemodes_hash}  FILEMODES\n",
            encoding="utf-8",
        )
        os.chmod(self.template / "SHA256SUMS", 0o644)
        self.candidate_digest = file_digest(self.template / "SHA256SUMS")
        self.standard_paths = self.root / "standard-paths.txt"
        self.standard_paths.write_text("", encoding="utf-8")
        self.plan = self.root / "plan.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def prepare(self, *extra: str) -> subprocess.CompletedProcess:
        return run(
            [
                "python3",
                str(RECONCILIATION),
                "prepare",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan-id",
                "TEST-RECONCILIATION-001",
                "--work-item-id",
                "TEST-WORK-001",
                "--work-item-revision",
                "4",
                "--created-at",
                "2026-07-27T12:00:00Z",
                "--standard-changed-paths",
                str(self.standard_paths),
                *extra,
            ]
        )

    def test_plan_is_deterministic_exact_and_materializes_only_rehearsal(self) -> None:
        reviewed_spec = (
            "AI_START_HERE.md="
            ".exocortex/local/update-reconciliation/objects/AI_START_HERE.md"
        )
        first = self.prepare("--reviewed", reviewed_spec)
        second = self.prepare("--reviewed", reviewed_spec)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.plan.write_text(first.stdout, encoding="utf-8")
        validation = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(self.plan),
                "--expected-work-item-id",
                "TEST-WORK-001",
                "--expected-work-item-revision",
                "4",
            ],
            check=True,
        )
        metadata = json.loads(validation.stdout)
        self.assertEqual(metadata["operation"], "apply_template_reconciliation")
        self.assertEqual(metadata["effect_paths"], ["AI_START_HERE.md"])
        rehearsal = self.root / "rehearsal"
        shutil.copytree(self.target, rehearsal)
        spec = importlib.util.spec_from_file_location("reconciliation_fixture", RECONCILIATION)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        plan = json.loads(self.plan.read_text(encoding="utf-8"))
        self.assertEqual(plan["entries"][0]["expected_mode"], "0755")
        module.materialize_plan(
            plan,
            destination_root=rehearsal,
            template=self.template,
            baseline_target=self.target,
        )
        self.assertEqual(
            (rehearsal / "AI_START_HERE.md").read_text(encoding="utf-8"),
            "reviewed merged entry\n",
        )
        self.assertEqual(stat.S_IMODE((rehearsal / "AI_START_HERE.md").stat().st_mode), 0o755)
        self.assertEqual(
            (self.target / "AI_START_HERE.md").read_text(encoding="utf-8"),
            "target entry\n",
        )

    def test_plan_can_live_in_protected_local_state_without_self_invalidating(self) -> None:
        candidate = self.prepare("--adopt", "AI_START_HERE.md")
        self.assertEqual(candidate.returncode, 0, candidate.stdout + candidate.stderr)
        local_plan = self.target / ".exocortex/local/update-reconciliation/plan.json"
        local_plan.write_text(candidate.stdout, encoding="utf-8")
        (self.target / ".exocortex/PROJECT_MEMORY.md").write_text(
            "protected project memory changed after planning\n",
            encoding="utf-8",
        )
        validation = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(local_plan),
                "--expected-work-item-id",
                "TEST-WORK-001",
                "--expected-work-item-revision",
                "4",
            ],
            check=True,
        )
        metadata = json.loads(validation.stdout)
        self.assertEqual(metadata["operation"], "apply_template_reconciliation")
        self.assertEqual(metadata["effect_paths"], ["AI_START_HERE.md"])

    def test_mode_only_target_drift_invalidates_plan(self) -> None:
        prepared = self.prepare("--adopt", "AI_START_HERE.md")
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        self.plan.write_text(prepared.stdout, encoding="utf-8")
        os.chmod(self.target / "AI_START_HERE.md", 0o755)
        validation = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(self.plan),
            ]
        )
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("target_surface_drift", validation.stdout)

    def test_project_owned_root_cursor_rules_require_a_bound_reconciliation(self) -> None:
        cursor_rules = self.target / ".cursorrules"
        cursor_rules.write_text("legacy project Cursor guidance\n", encoding="utf-8")
        os.chmod(cursor_rules, 0o644)
        prepared = self.prepare("--retire", ".cursorrules")
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        self.plan.write_text(prepared.stdout, encoding="utf-8")
        validation = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(self.plan),
            ],
            check=True,
        )
        self.assertEqual(json.loads(validation.stdout)["effect_paths"], [".cursorrules"])
        rehearsal = self.root / "cursor-rules-rehearsal"
        shutil.copytree(self.target, rehearsal)
        spec = importlib.util.spec_from_file_location("reconciliation_cursor_rules", RECONCILIATION)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.materialize_plan(
            json.loads(self.plan.read_text(encoding="utf-8")),
            destination_root=rehearsal,
            template=self.template,
            baseline_target=self.target,
        )
        self.assertFalse((rehearsal / ".cursorrules").exists())
        self.assertTrue(cursor_rules.is_file())
        cursor_rules.write_text("changed after plan\n", encoding="utf-8")
        drifted = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(self.plan),
            ]
        )
        self.assertNotEqual(drifted.returncode, 0)
        self.assertIn("target_surface_drift", drifted.stdout)

    def test_candidate_and_reviewed_object_mode_drift_fail_closed(self) -> None:
        reviewed_spec = (
            "AI_START_HERE.md="
            ".exocortex/local/update-reconciliation/objects/AI_START_HERE.md"
        )
        reviewed = self.prepare("--reviewed", reviewed_spec)
        self.assertEqual(reviewed.returncode, 0, reviewed.stdout + reviewed.stderr)
        reviewed_plan = self.root / "reviewed-mode-plan.json"
        reviewed_plan.write_text(reviewed.stdout, encoding="utf-8")
        os.chmod(
            self.target / ".exocortex/local/update-reconciliation/objects/AI_START_HERE.md",
            0o644,
        )
        validation = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(reviewed_plan),
            ]
        )
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("reviewed_object_mode_mismatch", validation.stdout)

        os.chmod(
            self.target / ".exocortex/local/update-reconciliation/objects/AI_START_HERE.md",
            0o755,
        )
        candidate = self.prepare("--adopt", "AI_START_HERE.md")
        self.assertEqual(candidate.returncode, 0, candidate.stdout + candidate.stderr)
        candidate_plan = self.root / "candidate-mode-plan.json"
        candidate_plan.write_text(candidate.stdout, encoding="utf-8")
        os.chmod(self.template / "AI_START_HERE.md", 0o644)
        validation = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(candidate_plan),
            ]
        )
        self.assertNotEqual(validation.returncode, 0)
        self.assertIn("candidate_mode_mismatch", validation.stdout)

    def test_mode_only_candidate_adoption_materializes_bound_mode(self) -> None:
        (self.target / "AI_START_HERE.md").write_text("candidate entry\n", encoding="utf-8")
        os.chmod(self.target / "AI_START_HERE.md", 0o644)
        prepared = self.prepare("--adopt", "AI_START_HERE.md")
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        plan = json.loads(prepared.stdout)
        self.assertEqual(plan["entries"][0]["expected_mode"], "0755")
        rehearsal = self.root / "mode-rehearsal"
        shutil.copytree(self.target, rehearsal)
        spec = importlib.util.spec_from_file_location("reconciliation_mode_fixture", RECONCILIATION)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.materialize_plan(
            plan,
            destination_root=rehearsal,
            template=self.template,
            baseline_target=self.target,
        )
        self.assertEqual(stat.S_IMODE((rehearsal / "AI_START_HERE.md").stat().st_mode), 0o755)

    def test_atomic_copy_verifies_the_open_source_stream_before_replace(self) -> None:
        spec = importlib.util.spec_from_file_location("reconciliation_stream_fixture", RECONCILIATION)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = self.root / "stream-source.txt"
        destination = self.root / "stream-destination.txt"
        source.write_text("reviewed source\n", encoding="utf-8")
        destination.write_text("preserve destination\n", encoding="utf-8")
        os.chmod(source, 0o644)
        os.chmod(destination, 0o644)
        with self.assertRaises(module.ReconciliationError) as raised:
            module.atomic_copy(source, destination, "0644", "0" * 64)
        self.assertEqual(raised.exception.code, "source_digest_mismatch")
        self.assertEqual(destination.read_text(encoding="utf-8"), "preserve destination\n")
        self.assertEqual(
            list(self.root.glob(".stream-destination.txt.exocortex-reconcile-*.tmp")),
            [],
        )

    def test_reconciliation_schema_requires_bound_modes(self) -> None:
        schema = json.loads(
            (TEMPLATE / ".exocortex/schemas/update-reconciliation-plan.schema.json").read_text(
                encoding="utf-8"
            )
        )
        entry = schema["properties"]["entries"]["items"]
        self.assertIn("expected_mode", entry["required"])
        self.assertEqual(schema["$defs"]["file_mode"]["enum"], ["0644", "0755"])
        self.assertEqual(
            entry["properties"]["expected_mode"]["oneOf"],
            [{"type": "null"}, {"$ref": "#/$defs/file_mode"}],
        )
        self.assertEqual(
            entry["allOf"][0]["then"]["properties"]["expected_mode"],
            {"type": "null"},
        )
        self.assertEqual(
            entry["allOf"][0]["else"]["properties"]["expected_mode"],
            {"$ref": "#/$defs/file_mode"},
        )

    def test_plan_rejects_duplicate_top_level_and_nested_json_keys(self) -> None:
        prepared = self.prepare("--adopt", "AI_START_HERE.md")
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        top_level = '{"effect_paths":[],' + prepared.stdout.lstrip()[1:]
        nested = re.sub(
            r'"work_item":\s*\{',
            '"work_item":{"revision":4,',
            prepared.stdout,
            count=1,
        )
        self.assertNotEqual(nested, prepared.stdout)
        for name, raw in (("top", top_level), ("nested", nested)):
            duplicate_plan = self.root / f"duplicate-{name}.json"
            duplicate_plan.write_text(raw, encoding="utf-8")
            validation = run(
                [
                    "python3",
                    str(RECONCILIATION),
                    "validate",
                    "--target",
                    str(self.target),
                    "--template",
                    str(self.template),
                    "--candidate-digest",
                    self.candidate_digest,
                    "--plan",
                    str(duplicate_plan),
                ]
            )
            self.assertNotEqual(validation.returncode, 0)
            self.assertIn("duplicate_json_key", validation.stdout)

    def test_plan_rejects_protected_paths_drift_and_wrong_candidate(self) -> None:
        protected = self.prepare("--adopt", ".exocortex/PROJECT_MEMORY.md")
        self.assertNotEqual(protected.returncode, 0)
        self.assertIn("protected_path", protected.stdout)
        context_backup = self.prepare("--adopt", ".exocortex/SESSION_CONTEXT.md.backup")
        self.assertNotEqual(context_backup.returncode, 0)
        self.assertIn("protected_path", context_backup.stdout)
        legacy_context_backup = self.prepare("--adopt", ".exocortex/SESSION_CONTEXT_BACKUP_CANARY.md")
        self.assertNotEqual(legacy_context_backup.returncode, 0)
        self.assertIn("protected_path", legacy_context_backup.stdout)
        legacy_context_backup_retire = self.prepare("--retire", ".exocortex/SESSION_CONTEXT_BACKUP_CANARY.md")
        self.assertNotEqual(legacy_context_backup_retire.returncode, 0)
        self.assertIn("protected_path", legacy_context_backup_retire.stdout)
        candidate = self.prepare("--adopt", "AI_START_HERE.md")
        self.assertEqual(candidate.returncode, 0, candidate.stdout + candidate.stderr)
        self.plan.write_text(candidate.stdout, encoding="utf-8")
        (self.target / "AI_START_HERE.md").write_text("concurrent drift\n", encoding="utf-8")
        drift = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                self.candidate_digest,
                "--plan",
                str(self.plan),
            ]
        )
        self.assertNotEqual(drift.returncode, 0)
        self.assertIn("target_surface_drift", drift.stdout)
        wrong_candidate = run(
            [
                "python3",
                str(RECONCILIATION),
                "validate",
                "--target",
                str(self.target),
                "--template",
                str(self.template),
                "--candidate-digest",
                "0" * 64,
                "--plan",
                str(self.plan),
            ]
        )
        self.assertNotEqual(wrong_candidate.returncode, 0)
        self.assertIn("candidate_digest_mismatch", wrong_candidate.stdout)

    def test_safe_update_requires_distinct_plan_bound_authority(self) -> None:
        template_source = self.root / "full-template-source"
        materialize_credential_blind_candidate(TEMPLATE, template_source)
        target = self.root / "full-target"
        target.mkdir()
        (target / ".exocortex/control").mkdir(parents=True)
        (target / ".exocortex/events").mkdir()
        for directory in (
            "capabilities",
            "transactions",
            "descriptors",
            "payloads",
            "audit",
        ):
            (target / f".exocortex/local/protocol/{directory}").mkdir(parents=True)
        (target / ".exocortex/.project-name").write_text("fictional-canary\n", encoding="utf-8")
        for relative, content in (
            ("SESSION_CONTEXT.md", "# Session Context\n"),
            ("SESSION_CONTEXT.md.backup", "KEEP_CONTEXT_BACKUP\n"),
            ("SESSION_CONTEXT_BACKUP_CANARY.md", "KEEP_LEGACY_CONTEXT_BACKUP\n"),
            ("TODO.md", "# TODO\n"),
            ("LESSONS.md", "# Lessons\n"),
            ("PROJECT_MEMORY.md", "KEEP_PROJECT_MEMORY\n"),
            ("OPEN_DECISIONS.md", "# Open Decisions\n"),
            ("control/INTERRUPTS.md", "# Interrupts\n"),
            ("control/BACKLOG.md", "# Backlog\n"),
            ("control/ROADMAP.md", "# Roadmap\n"),
        ):
            (target / f".exocortex/{relative}").write_text(content, encoding="utf-8")
        (target / "AI_START_HERE.md").write_text("legacy target entry\n", encoding="utf-8")
        guard_digest = run(["python3", str(AUTHORITY), "guard-digest"], check=True).stdout.strip()
        registry = {
            "schema_version": "public-v2",
            "kind": "executor_registry",
            "registry_version": 1,
            "default_role": "read_only",
            "executors": [
                {
                    "surface_id": "test-surface",
                    "executor_id": "test-executor",
                    "adapter_version": "test-v1",
                    "guard_digest": guard_digest,
                    "roles": ["read_only", "writer"],
                    "status": "active",
                    "registered_at": "2026-01-01T00:00:00Z",
                    "expires_at": "2099-01-01T00:00:00Z",
                    "revoked_at": None,
                }
            ],
        }
        write_json(target / REGISTRY_REL, registry)
        write_json(
            target / ".exocortex/control/EXTERNAL_SYNC_POLICY.json",
            {
                "schema_version": "public-v2",
                "kind": "external_sync_policy",
                "default": "deny",
                "policy_version": 1,
                "destinations": [],
            },
        )
        candidate_digest = file_digest(template_source / "SHA256SUMS")
        backup = self.root / "backups"
        backup.mkdir()
        dry = run(
            [
                "bash",
                str(TEMPLATE / "scripts/safe-update.sh"),
                "--template",
                str(template_source),
                "--candidate-digest",
                candidate_digest,
                "--backup-dir",
                str(backup),
                "--dry-run",
            ],
            env={"HOME": str(self.root / "fake-home")},
            cwd=target,
        )
        self.assertEqual(dry.returncode, 0, dry.stdout + dry.stderr)
        lines = dry.stdout.splitlines()
        start = next(index for index, line in enumerate(lines) if line.startswith("Rehearsal changed paths: ")) + 1
        standard_paths = []
        for line in lines[start:]:
            if line == "Dry run complete. Real target unchanged.":
                break
            if line:
                standard_paths.append(line)
        standard_path_file = self.root / "full-standard-paths.txt"
        standard_path_file.write_text("".join(f"{path}\n" for path in standard_paths), encoding="utf-8")
        prepared = run(
            [
                "python3",
                str(RECONCILIATION),
                "prepare",
                "--target",
                str(target),
                "--template",
                str(template_source),
                "--candidate-digest",
                candidate_digest,
                "--plan-id",
                "TEST-RECONCILIATION-APPLY",
                "--work-item-id",
                "TEST-UPGRADE-001",
                "--work-item-revision",
                "0",
                "--created-at",
                "2026-07-27T12:00:00Z",
                "--standard-changed-paths",
                str(standard_path_file),
                "--adopt",
                "AI_START_HERE.md",
            ]
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        plan = self.root / "full-plan.json"
        plan.write_text(prepared.stdout, encoding="utf-8")
        duplicate_plan = self.root / "full-plan-duplicate.json"
        duplicate_plan.write_text(
            '{"effect_paths":[],' + prepared.stdout.lstrip()[1:],
            encoding="utf-8",
        )
        backups_before_duplicate = sorted(item.name for item in backup.iterdir())
        duplicate = run(
            [
                "bash",
                str(TEMPLATE / "scripts/safe-update.sh"),
                "--template",
                str(template_source),
                "--candidate-digest",
                candidate_digest,
                "--backup-dir",
                str(backup),
                "--reconciliation-plan",
                str(duplicate_plan),
                "--dry-run",
            ],
            env={"HOME": str(self.root / "fake-home")},
            cwd=target,
        )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn(
            "reconciliation plan failed closed before backup or rehearsal",
            duplicate.stdout + duplicate.stderr,
        )
        self.assertEqual(sorted(item.name for item in backup.iterdir()), backups_before_duplicate)
        plan_document = json.loads(prepared.stdout)
        plan_digest = file_digest(plan)
        capability_rel = ".exocortex/local/protocol/capabilities/reconciliation.json"
        capability = {
            "schema_version": "public-v2",
            "kind": "approval_capability",
            "capability_id": "cap-reconciliation",
            "work_item_id": "TEST-UPGRADE-001",
            "work_item_revision": 0,
            "operation": "apply_template_reconciliation",
            "scope": {
                "allowed_paths": plan_document["effect_paths"],
                "target_sha": candidate_digest,
                "payload_digest": plan_digest,
            },
            "executor": {
                "surface_id": "test-surface",
                "executor_id": "test-executor",
                "adapter_version": "test-v1",
                "guard_digest": guard_digest,
                "registry_version": 1,
            },
            "approval": {
                "approved_by": "fixture-human",
                "accepted_at": "2026-01-01T00:00:00Z",
                "expires_at": "2099-01-01T00:00:00Z",
                "one_time": True,
                "summary": "fictional exact reconciliation fixture",
            },
            "status": {
                "state": "active",
                "revoked_at": None,
                "consumed_at": None,
                "consumed_by_request_id": None,
            },
        }
        write_json(target / capability_rel, capability)
        apply = run(
            [
                "bash",
                str(TEMPLATE / "scripts/safe-update.sh"),
                "--template",
                str(template_source),
                "--candidate-digest",
                candidate_digest,
                "--backup-dir",
                str(backup),
                "--apply",
                "--reconciliation-plan",
                str(plan),
                "--capability",
                capability_rel,
                "--work-item-id",
                "TEST-UPGRADE-001",
                "--work-item-revision",
                "0",
                "--request-id",
                "apply-reconciliation",
                "--surface-id",
                "test-surface",
                "--executor-id",
                "test-executor",
                "--adapter-version",
                "test-v1",
            ],
            env={"HOME": str(self.root / "fake-home")},
            cwd=target,
        )
        self.assertEqual(apply.returncode, 0, apply.stdout + apply.stderr)
        self.assertEqual(
            file_digest(target / "AI_START_HERE.md"),
            file_digest(template_source / "AI_START_HERE.md"),
        )
        self.assertEqual(
            (target / ".exocortex/PROJECT_MEMORY.md").read_text(encoding="utf-8"),
            "KEEP_PROJECT_MEMORY\n",
        )
        consumed = json.loads((target / capability_rel).read_text(encoding="utf-8"))
        self.assertEqual(consumed["status"]["state"], "consumed")
        retry = run(
            [
                "bash",
                str(TEMPLATE / "scripts/safe-update.sh"),
                "--template",
                str(template_source),
                "--candidate-digest",
                candidate_digest,
                "--backup-dir",
                str(backup),
                "--apply",
                "--reconciliation-plan",
                str(plan),
                "--capability",
                capability_rel,
                "--work-item-id",
                "TEST-UPGRADE-001",
                "--work-item-revision",
                "0",
                "--request-id",
                "apply-reconciliation",
                "--surface-id",
                "test-surface",
                "--executor-id",
                "test-executor",
                "--adapter-version",
                "test-v1",
            ],
            env={"HOME": str(self.root / "fake-home")},
            cwd=target,
        )
        self.assertNotEqual(retry.returncode, 0)
        self.assertIn(
            "reconciliation plan failed closed before backup or rehearsal",
            retry.stdout + retry.stderr,
        )
        converged = run(
            [
                "bash",
                str(TEMPLATE / "scripts/safe-update.sh"),
                "--template",
                str(template_source),
                "--candidate-digest",
                candidate_digest,
                "--backup-dir",
                str(backup),
                "--dry-run",
            ],
            env={"HOME": str(self.root / "fake-home")},
            cwd=target,
        )
        self.assertEqual(converged.returncode, 0, converged.stdout + converged.stderr)
        self.assertIn("Rehearsal changed paths: 0", converged.stdout)


class EntryAndPrivacyTests(unittest.TestCase):
    def test_transition_schema_matches_runtime_contract(self) -> None:
        schema = json.loads((TEMPLATE / ".exocortex/schemas/orchestration.schema.json").read_text(encoding="utf-8"))
        acceptance = schema["properties"]["acceptance_criteria"]["items"]
        self.assertEqual(acceptance["properties"]["evidence"]["items"]["minLength"], 1)
        self.assertTrue(acceptance["properties"]["evidence"]["uniqueItems"])
        evidence_gate = acceptance["allOf"][0]
        self.assertEqual(
            evidence_gate["if"]["properties"]["status"]["enum"],
            ["passed", "failed", "blocked"],
        )
        self.assertIn("evidence", evidence_gate["then"]["required"])
        self.assertEqual(evidence_gate["then"]["properties"]["evidence"]["minItems"], 1)
        transition = schema["$defs"]["transition"]
        for field in ("capability_path", "capability_digest", "intent_digest"):
            self.assertIn(field, transition["properties"])
        local_provenance_gate = schema["allOf"][0]
        self.assertEqual(local_provenance_gate["if"], {"required": ["local_delivery"]})
        local_transition_rules = local_provenance_gate["then"]["properties"]["transitions"]["items"]["allOf"]
        self.assertEqual(
            local_transition_rules[0]["required"],
            ["capability_path", "capability_digest", "intent_digest"],
        )
        human_uat_gate = local_transition_rules[1]
        self.assertIn("human_uat_attestor", human_uat_gate["then"]["required"])
        self.assertEqual(human_uat_gate["then"]["properties"]["evidence"]["minItems"], 1)
        self.assertEqual(
            human_uat_gate["else"],
            {"not": {"required": ["human_uat_attestor"]}},
        )
        forbidden_legacy_provenance = local_provenance_gate["else"]["properties"]["transitions"]["items"]
        self.assertEqual(
            forbidden_legacy_provenance,
            {
                "not": {
                    "anyOf": [
                        {"required": ["capability_path"]},
                        {"required": ["capability_digest"]},
                        {"required": ["intent_digest"]},
                        {"required": ["human_uat_attestor"]},
                    ]
                }
            },
        )
        self.assertIn("evidence", transition["required"])
        self.assertEqual(transition["properties"]["from"], {"$ref": "#/$defs/state"})
        expected = {
            ("captured", "triaged", False),
            ("triaged", "refined", False),
            ("refined", "ready", False),
            ("ready", "reserved", False),
            ("reserved", "developing", True),
            ("developing", "developer_verified", True),
            ("developer_verified", "independent_review", False),
            ("independent_review", "qa_sit", True),
            ("qa_sit", "uat_ready", True),
            ("uat_ready", "human_uat", True),
            ("human_uat", "release_ready", True),
            ("release_ready", "awaiting_release", False),
            ("awaiting_release", "deployment_approved", False),
            ("deployment_approved", "deployed", True),
            ("deployed", "hypercare", True),
            ("hypercare", "done", True),
        }
        observed = {
            (
                branch["properties"]["from"]["const"],
                branch["properties"]["to"]["const"],
                branch["properties"]["checkpoint_eligible"]["const"],
            )
            for branch in transition["allOf"][0]["oneOf"]
        }
        self.assertEqual(observed, expected)
        self.assertFalse(
            any(
                branch.get("if", {}).get("properties", {}).get("to", {}).get("const") == "human_uat"
                for branch in transition["allOf"]
            ),
            "legacy transition schema must not impose local Human UAT fields",
        )

    def test_all_entry_surfaces_point_to_canonical_contract(self) -> None:
        paths = [
            TEMPLATE / "CLAUDE.md", TEMPLATE / "AGENTS.md",
            TEMPLATE / ".github/copilot-instructions.md", TEMPLATE / ".rules",
            TEMPLATE / ".cursor/rules/plan-orchestrate.mdc",
            *sorted((TEMPLATE / ".cursor/skills").glob("*/SKILL.md")),
            *sorted((TEMPLATE / ".github/skills").glob("*/SKILL.md")),
            *sorted((TEMPLATE / ".agents/skills").glob("*/SKILL.md")),
            *sorted((TEMPLATE / ".claude/skills").glob("*/SKILL.md")),
            TEMPLATE / ".exocortex/skills/exocortex-reminder/SKILL.md",
            TEMPLATE / ".exocortex/skills/exocortex-reminder/SETUP.md",
        ]
        missing = [str(path.relative_to(TEMPLATE)) for path in paths if "AI_START_HERE.md" not in path.read_text(encoding="utf-8")]
        self.assertEqual(missing, [])
        specs = sorted((TEMPLATE / ".exocortex/commands").glob("*.json"))
        self.assertEqual(len(specs), 24)
        for path in specs:
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(doc["protocol"]["entry_contract"], "AI_START_HERE.md")
            self.assertEqual(doc["protocol"]["default_role"], "read_only")

        for relative in (
            "AI_START_HERE.md",
            ".exocortex/AI_BOOTSTRAP.md",
            ".exocortex/COMMAND_SYSTEM.md",
            "CLAUDE.md",
            "AGENTS.md",
        ):
            command_authority = (TEMPLATE / relative).read_text(encoding="utf-8")
            compact_authority = " ".join(command_authority.split())
            self.assertIn("sole command-flow behavior source", compact_authority)
            self.assertIn("without combining", compact_authority)

    def test_entry_contract_uses_business_envelopes_and_denies_wildcards(self) -> None:
        entry = (TEMPLATE / "AI_START_HERE.md").read_text(encoding="utf-8")
        bootstrap = (TEMPLATE / ".exocortex/AI_BOOTSTRAP.md").read_text(
            encoding="utf-8"
        )
        save = json.loads(
            (TEMPLATE / ".exocortex/commands/save.json").read_text(
                encoding="utf-8"
            )
        )

        entry_contracts = (
            "A narrative save begins as a chat-only draft and never creates a "
            "lifecycle\n  checkpoint.",
            "An ordinary-language sentence that merely contains or begins "
            "with a command-like verb does not invoke a manual-only command.",
            "A broad request such as “Save everything and sync it everywhere "
            "now” authorizes nothing.",
            "`Everything`, `everywhere`, and similar wildcards grant no path, "
            "batch, destination, or egress authority.",
            "The human approves understandable business outcomes.",
            "Those are internal safety mechanics and remain exact, one-time,\n"
            "auditable, and fail-closed.",
            "Use four human-facing gate classes:",
            "`local_delivery`",
            "`publication`",
            "`integration_rollout`",
            "`production_egress`",
            "Human UAT is an observable accept/reject decision, not a request "
            "to approve a\ncapability.",
            "A broad or ambiguous bundled request authorizes none of its "
            "component actions.",
            "Never combine a local record with external synchronization in "
            "one envelope.",
            "When refusing or deferring a bundled local-record and egress "
            "request, state explicitly: no event, lifecycle checkpoint, "
            "repository or temporary file, commit, credential access, network "
            "request, or external synchronization occurred.",
        )
        bootstrap_contracts = (
            "A manual command is invoked only when the user uses the "
            "host-native command\ntrigger or selector, or supplies the exact "
            "bare command token by itself or\nexplicitly frames following text "
            "as command arguments.",
            "An ordinary sentence that merely contains or begins with a "
            "command-like verb\nis ordinary chat.",
            "Arguments and modifiers following an explicit command invocation "
            "are command\ninputs only; they never expand path, mutation, "
            "checkpoint, commit, credential,\nnetwork, egress, or batch "
            "authority.",
            "Materialize, consume, renew, and audit internal reservations and "
            "technical\n   capabilities without turning each one into another "
            "human prompt",
            "Never combine a local record and external synchronization in one\n"
            "envelope.",
        )

        for expected in entry_contracts:
            with self.subTest(source="AI_START_HERE.md", expected=expected):
                self.assertIn(expected, entry)

        for expected in bootstrap_contracts:
            with self.subTest(
                source=".exocortex/AI_BOOTSTRAP.md", expected=expected
            ):
                self.assertIn(expected, bootstrap)

        self.assertEqual(
            [step["type"] for step in save["steps"]],
            ["ai", "user_choice", "ai"],
        )
        self.assertIn("not a checkpoint", save["description"])
        self.assertEqual(
            save["steps"][1]["options"],
            [
                "A) Keep the narrative in chat only",
                "B) Save this exact summary as a project-local event",
            ],
        )
        self.assertNotIn(
            "capability",
            " ".join(save["steps"][1]["options"]).lower(),
        )
        self.assertIn(
            "internal reservation and capability mechanics are not separate "
            "human approvals",
            save["steps"][0]["context"],
        )
        self.assertIn("Never synchronize automatically", save["steps"][2]["context"])
        self.assertNotIn(
            "sync",
            " ".join(save["steps"][1]["options"]).lower(),
        )

    def test_generated_provider_adapters_match_independent_matrix(self) -> None:
        production = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
        golden = json.loads(ADAPTER_TEST_MATRIX.read_text(encoding="utf-8"))
        command_names = sorted(path.stem for path in (TEMPLATE / ".exocortex/commands").glob("*.json"))
        self.assertEqual(command_names, golden["canonical_commands"])
        self.assertEqual(production["expected_command_count"], len(command_names))
        invocation_policy = production["command_invocation_policy"]
        self.assertEqual(invocation_policy, golden["command_invocation_policy"])
        self.assertEqual(set(invocation_policy), {"model_invocable", "manual_only"})
        self.assertEqual(len(invocation_policy["model_invocable"]), 11)
        self.assertEqual(len(invocation_policy["manual_only"]), 13)
        self.assertFalse(set(invocation_policy["model_invocable"]) & set(invocation_policy["manual_only"]))
        self.assertEqual(
            set(invocation_policy["model_invocable"]) | set(invocation_policy["manual_only"]),
            set(command_names),
        )

        production_families = {
            item["id"]: item["path_template"] for item in production["adapter_families"]
        }
        self.assertTrue(all("manual_only" not in item for item in production["adapter_families"]))
        golden_families = {
            item["id"]: item["path_template"] for item in golden["generated_families"]
        }
        self.assertEqual(production_families, golden_families)
        production_providers = [
            {
                "id": item["id"],
                "adapter_family": item["adapter_family"],
                "evidence_adapter_family": item["evidence_adapter_family"],
                "native_invocation": item["native_invocation"],
                "literal_slash_claim": item["literal_slash_claim"],
                "status": item["status"],
                "default_install": item["default_install"],
                "revalidation_required": item["revalidation_required"],
            }
            for item in production["providers"]
        ]
        self.assertEqual(production_providers, golden["providers"])
        kimi = next(item for item in production["providers"] if item["id"] == "kimi-code")
        self.assertEqual(kimi["native_invocation"], "/skill:{name}")
        self.assertNotIn(" or /", kimi["native_invocation"])
        self.assertEqual(sorted(production["status_definitions"]), golden["status_names"])
        for item in production["providers"]:
            self.assertTrue(item["version"])
            self.assertTrue(item["evidence"])
            self.assertTrue(item["limitation"])

        expected_paths = {
            template.format(command=name)
            for template in golden_families.values()
            for name in command_names
        }
        actual_paths = {
            path.relative_to(TEMPLATE).as_posix()
            for root in (TEMPLATE / ".agents/skills", TEMPLATE / ".claude/skills", TEMPLATE / ".cursor/skills")
            for path in root.rglob("*")
            if path.is_file()
            and "GENERATED BY .exocortex/scripts/generate_command_adapters.py" in path.read_text(encoding="utf-8")
        }
        self.assertEqual(len(expected_paths), golden["repository_adapter_count"])
        self.assertEqual(actual_paths, expected_paths)

        for rel in sorted(expected_paths):
            path = TEMPLATE / rel
            name = path.parent.name if path.name == "SKILL.md" else path.stem
            text = path.read_text(encoding="utf-8")
            self.assertIn("GENERATED BY .exocortex/scripts/generate_command_adapters.py", text)
            self.assertIn("AI_START_HERE.md", text)
            self.assertIn(".exocortex/AI_BOOTSTRAP.md", text)
            self.assertEqual(text.count(f".exocortex/commands/{name}.json"), 1)
            self.assertIn("grants no authority", text)
            manual_only = name in invocation_policy["manual_only"]
            self.assertIn("manual-only" if manual_only else "model-invocable read-only", text)
            if rel.startswith(".claude/skills/"):
                self.assertEqual(
                    "disable-model-invocation: true" in text,
                    manual_only,
                )
            elif rel.startswith(".cursor/skills/"):
                frontmatter = text.split("---", 2)[1]
                self.assertEqual(
                    "disable-model-invocation: true" in frontmatter,
                    manual_only,
                )
                self.assertNotIn("argument-hint", frontmatter)
            elif rel.startswith(".agents/skills/"):
                frontmatter = text.split("---", 2)[1]
                keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
                self.assertEqual(keys, ["name", "description"])
                self.assertNotIn("disable-model-invocation", frontmatter)
                self.assertNotIn("argument-hint", frontmatter)

        legacy_retirement_paths = {item["path"] for item in production["legacy_retirements"]}
        windsurf_retirement_paths = set(production["windsurf_retirements"])
        self.assertEqual(legacy_retirement_paths, set(golden["legacy_retirement_paths"]))
        self.assertEqual(windsurf_retirement_paths, set(golden["windsurf_retirement_paths"]))
        self.assertEqual(len(legacy_retirement_paths | windsurf_retirement_paths), 80)
        self.assertFalse(legacy_retirement_paths & windsurf_retirement_paths)
        output_retirement_overlap = legacy_retirement_paths & expected_paths
        self.assertEqual(output_retirement_overlap, set(golden["reactivated_paths"]))
        retired_only = (legacy_retirement_paths | windsurf_retirement_paths) - expected_paths
        self.assertEqual(len(retired_only), 79)
        self.assertTrue(all(not (TEMPLATE / rel).exists() for rel in retired_only))
        self.assertFalse((TEMPLATE / ".windsurfrules").exists())
        self.assertFalse(any((TEMPLATE / ".windsurf/workflows").glob("*.md")))
        self.assertEqual(
            {path.parent.name for path in (TEMPLATE / ".agents/skills").glob("*/SKILL.md")},
            set(command_names),
        )
        self.assertEqual(
            {
                path.parent.name
                for path in (TEMPLATE / ".cursor/skills").glob("*/SKILL.md")
                if "GENERATED BY .exocortex/scripts/generate_command_adapters.py"
                in path.read_text(encoding="utf-8")
            },
            set(command_names),
        )
        self.assertEqual(production["guarantees"]["provider_menu_visibility"], "human_uat_required")
        self.assertFalse(production["guarantees"]["authority_expansion"])

    def test_provider_adapter_generator_is_deterministic(self) -> None:
        checked = run(["python3", str(ADAPTER_GENERATOR), "--check"])
        self.assertEqual(checked.returncode, 0, checked.stderr)
        with tempfile.TemporaryDirectory(prefix="exo-adapter-generator-") as temp:
            root = Path(temp)
            for rel in (
                "AI_START_HERE.md",
                ".exocortex/provider-adapters.json",
                ".exocortex/schemas/provider-adapter-matrix.schema.json",
                ".exocortex/scripts/generate_command_adapters.py",
            ):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(TEMPLATE / rel, target)
            for rel in (".exocortex/commands", ".agents", ".claude", ".cursor/skills"):
                shutil.copytree(TEMPLATE / rel, root / rel)

            generated = root / ".agents/skills/save/SKILL.md"
            generated.unlink()
            writer = root / ".exocortex/scripts/generate_command_adapters.py"
            first = run(["python3", str(writer), "--write"])
            self.assertEqual(first.returncode, 0, first.stderr)
            first_digest = canonical_digest({
                path.relative_to(root).as_posix(): file_digest(path)
                for base in (root / ".agents", root / ".claude", root / ".cursor/skills")
                for path in base.rglob("*")
                if path.is_file()
                and "GENERATED BY .exocortex/scripts/generate_command_adapters.py"
                in path.read_text(encoding="utf-8")
            })
            second = run(["python3", str(writer), "--write"])
            self.assertEqual(second.returncode, 0, second.stderr)
            second_digest = canonical_digest({
                path.relative_to(root).as_posix(): file_digest(path)
                for base in (root / ".agents", root / ".claude", root / ".cursor/skills")
                for path in base.rglob("*")
                if path.is_file()
                and "GENERATED BY .exocortex/scripts/generate_command_adapters.py"
                in path.read_text(encoding="utf-8")
            })
            self.assertEqual(first_digest, second_digest)

    def test_provider_adapter_generator_enforces_complete_schema(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exo-adapter-schema-") as temp:
            root = Path(temp)
            for rel in (
                "AI_START_HERE.md",
                ".exocortex/provider-adapters.json",
                ".exocortex/schemas/provider-adapter-matrix.schema.json",
                ".exocortex/scripts/generate_command_adapters.py",
            ):
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(TEMPLATE / rel, target)
            shutil.copytree(TEMPLATE / ".exocortex/commands", root / ".exocortex/commands")
            writer = root / ".exocortex/scripts/generate_command_adapters.py"
            matrix_path = root / ".exocortex/provider-adapters.json"

            extra_property = json.loads(matrix_path.read_text(encoding="utf-8"))
            extra_property["unexpected"] = True
            write_json(matrix_path, extra_property)
            rejected = run(["python3", str(writer), "--check"])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("schema extra property", rejected.stderr)

            duplicate_provider = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
            duplicate_provider["providers"][-1] = duplicate_provider["providers"][0]
            write_json(matrix_path, duplicate_provider)
            rejected = run(["python3", str(writer), "--check"])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("schema has duplicate items", rejected.stderr)

            missing_limitation = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
            missing_limitation["providers"][0].pop("limitation")
            write_json(matrix_path, missing_limitation)
            rejected = run(["python3", str(writer), "--check"])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("schema missing property", rejected.stderr)

            invalid_status = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
            invalid_status["providers"][0]["status"] = "assumed"
            write_json(matrix_path, invalid_status)
            rejected = run(["python3", str(writer), "--check"])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("schema enum mismatch", rejected.stderr)

            wrong_invocation_policy = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
            wrong_invocation_policy["command_invocation_policy"]["manual_only"][0] = "work"
            write_json(matrix_path, wrong_invocation_policy)
            rejected = run(["python3", str(writer), "--check"])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("command invocation policy mismatch", rejected.stderr)

            stale_windsurf_family = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
            windsurf = next(item for item in stale_windsurf_family["providers"] if item["id"] == "windsurf")
            windsurf["default_install"] = True
            write_json(matrix_path, stale_windsurf_family)
            rejected = run(["python3", str(writer), "--check"])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("Windsurf must remain unavailable", rejected.stderr)

            missing_retirement = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
            missing_retirement["windsurf_retirements"].pop()
            write_json(matrix_path, missing_retirement)
            rejected = run(["python3", str(writer), "--check"])
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("schema has too few items", rejected.stderr)

    def test_provider_adapter_schema_records_closed_migration_contract(self) -> None:
        schema = json.loads((TEMPLATE / ".exocortex/schemas/provider-adapter-matrix.schema.json").read_text(encoding="utf-8"))
        production = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["expected_command_count"]["const"], 24)
        policy_schema = schema["properties"]["command_invocation_policy"]["properties"]
        self.assertEqual(policy_schema["model_invocable"]["minItems"], 11)
        self.assertEqual(policy_schema["model_invocable"]["maxItems"], 11)
        self.assertEqual(policy_schema["manual_only"]["minItems"], 13)
        self.assertEqual(policy_schema["manual_only"]["maxItems"], 13)
        self.assertEqual(schema["properties"]["legacy_retirements"]["minItems"], 55)
        self.assertEqual(schema["properties"]["legacy_retirements"]["maxItems"], 55)
        self.assertEqual(schema["properties"]["windsurf_retirements"]["minItems"], 25)
        self.assertEqual(schema["properties"]["windsurf_retirements"]["maxItems"], 25)
        self.assertEqual(set(production["status_definitions"]), {"verified", "compatible", "failed", "blocked", "unavailable"})
        self.assertEqual(production["migration"]["cumulative_retirement_count"], 80)
        self.assertTrue(production["migration"]["retire_only_when_manifest_owned_and_byte_matching"])
        self.assertTrue(production["migration"]["preserve_customized_or_unknown"])
        self.assertEqual(production["migration"]["collision_code"], "EXOCORTEX_ADAPTER_COLLISION_PRESERVED")
        self.assertEqual(production["migration"]["reactivated_paths"], [".cursor/skills/onboard/SKILL.md"])

    def test_drill_topic_stdin_contract_treats_substitution_canary_literally(self) -> None:
        drill = json.loads((TEMPLATE / ".exocortex/commands/drill.json").read_text(encoding="utf-8"))
        shell_step = drill["steps"][0]
        self.assertEqual(
            shell_step["command"],
            "python3 .exocortex/scripts/drill_memory.py --topic-stdin",
        )
        self.assertEqual(shell_step["stdin"], "{topic}\n")
        self.assertNotIn("{topic}", shell_step["command"])

        with tempfile.TemporaryDirectory(prefix="exo-drill-canary-") as temp:
            canary = Path(temp) / "substitution-ran"
            topic = f"canary $(touch {canary})"
            result = subprocess.run(
                ["python3", str(TEMPLATE / ".exocortex/scripts/drill_memory.py"), "--topic-stdin"],
                input=topic + "\n",
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(canary.exists())
            self.assertIn(f"DRILL - project-local matches for: {topic.lower()}", result.stdout)

    def test_normative_routing_has_no_versioned_model_pin(self) -> None:
        text = "\n".join((TEMPLATE / rel).read_text(encoding="utf-8") for rel in [
            ".exocortex/control/MODEL_ROUTING.md", ".cursor/rules/plan-orchestrate.mdc", "AI_START_HERE.md"
        ]).lower()
        compact = " ".join(text.split())
        for token in ("gpt-", "claude-"):
            self.assertNotIn(token, text)
        self.assertIn("illustrative current adapter mappings", compact)
        self.assertIn("these are examples only", compact)
        self.assertIn("open-source and future models map by demonstrated equivalent capability", compact)

    def test_default_drafts_and_external_reminder_are_non_mutating(self) -> None:
        for name in ("save", "daily-end", "ai-export"):
            text = (TEMPLATE / f".exocortex/commands/{name}.json").read_text(encoding="utf-8")
            self.assertNotIn("/tmp/", text)
            document = json.loads(text)
            self.assertEqual(document["protocol"]["default_role"], "read_only")
        reminder = "\n".join(
            (TEMPLATE / rel).read_text(encoding="utf-8")
            for rel in (
                ".exocortex/skills/exocortex-reminder/SKILL.md",
                ".exocortex/skills/exocortex-reminder/SETUP.md",
            )
        )
        self.assertNotIn("scp ", reminder)
        self.assertNotIn("ssh ", reminder)
        self.assertNotIn("cron add", reminder)
        self.assertIn("separate external-system", reminder)

    def test_private_phase_b_evidence_is_not_in_installable_code_plane(self) -> None:
        blocked = (
            "phase-b-" + "private-",
            "exo-phase-b-" + "evidence.",
            "EXOCORTEX_PRIVATE_" + "FINGERPRINT_FILE",
        )
        roots = [TEMPLATE / "AI_START_HERE.md", TEMPLATE / "AGENTS.md", TEMPLATE / ".agents", TEMPLATE / ".cursor", TEMPLATE / ".github/skills", TEMPLATE / ".claude/skills", TEMPLATE / ".windsurf", TEMPLATE / ".exocortex/provider-adapters.json", TEMPLATE / ".exocortex/commands", TEMPLATE / ".exocortex/scripts", TEMPLATE / ".exocortex/docs"]
        hits = []
        for root in roots:
            files = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
            for path in files:
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if any(value in text for value in blocked):
                    hits.append(str(path.relative_to(TEMPLATE)))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
