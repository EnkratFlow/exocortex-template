#!/usr/bin/env python3
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional
import unittest


TEMPLATE = Path(__file__).resolve().parents[2]
AUTHORITY = TEMPLATE / ".exocortex/scripts/authority_guard.py"
ORCHESTRATOR = TEMPLATE / ".exocortex/scripts/orchestrate_work_item.py"
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


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage_transaction(request_id: str) -> str:
    return f".exocortex/local/protocol/transactions/egress-stage-{request_id}.json"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(command: List[str], *, env: Optional[Dict[str, str]] = None, check: bool = False) -> subprocess.CompletedProcess:
    current = os.environ.copy()
    current["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        current.update(env)
    result = subprocess.run(command, text=True, capture_output=True, env=current, check=False)
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

    def orchestration(self, command: str, capability: str, request: str, extra: Optional[List[str]] = None) -> subprocess.CompletedProcess:
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
            ]
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


class RoutingAndEgressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = ProtocolFixture()

    def tearDown(self) -> None:
        self.fx.close()

    def test_least_cost_capable_routing_without_model_pins(self) -> None:
        task_rel = "task.json"
        catalog_rel = "catalog.json"
        write_json(self.fx.root / task_rel, {"required_capabilities": ["integrate"], "risk": "high", "delegates": [{"id": "evidence", "required_capabilities": ["search"], "risk": "low"}]})
        write_json(self.fx.root / catalog_rel, {"models": [
            {"id": "tier-a", "available": True, "parent_capable": True, "capabilities": ["integrate", "search"], "max_risk": "critical", "cost_rank": 9},
            {"id": "tier-b", "available": True, "parent_capable": True, "capabilities": ["integrate"], "max_risk": "high", "cost_rank": 4},
            {"id": "tier-c", "available": True, "parent_capable": False, "capabilities": ["search"], "max_risk": "low", "cost_rank": 1},
        ]})
        result = run(["python3", str(ORCHESTRATOR), "route", "--project-root", str(self.fx.root), "--task", task_rel, "--catalog", catalog_rel], check=True)
        output = json.loads(result.stdout)
        self.assertEqual(output["parent_model_id"], "tier-b")
        self.assertEqual(output["delegates"][0]["model_id"], "tier-c")
        self.assertFalse(output["normative_model_pin"])

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


class EntryAndPrivacyTests(unittest.TestCase):
    def test_transition_schema_matches_runtime_contract(self) -> None:
        schema = json.loads((TEMPLATE / ".exocortex/schemas/orchestration.schema.json").read_text(encoding="utf-8"))
        transition = schema["$defs"]["transition"]
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

    def test_all_entry_surfaces_point_to_canonical_contract(self) -> None:
        paths = [
            TEMPLATE / "CLAUDE.md", TEMPLATE / ".github/copilot-instructions.md", TEMPLATE / ".rules",
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

    def test_generated_provider_adapters_match_independent_matrix(self) -> None:
        production = json.loads(ADAPTER_MATRIX.read_text(encoding="utf-8"))
        golden = json.loads(ADAPTER_TEST_MATRIX.read_text(encoding="utf-8"))
        command_names = sorted(path.stem for path in (TEMPLATE / ".exocortex/commands").glob("*.json"))
        self.assertEqual(command_names, golden["canonical_commands"])
        self.assertEqual(production["expected_command_count"], len(command_names))

        production_families = {
            item["id"]: item["path_template"] for item in production["adapter_families"]
        }
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
            self.assertIn("manual-only", text)
            if rel.startswith(".claude/skills/"):
                self.assertIn("disable-model-invocation: true", text)
            elif rel.startswith(".cursor/skills/"):
                frontmatter = text.split("---", 2)[1]
                self.assertIn("disable-model-invocation: true", frontmatter)
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
        self.assertEqual(len(legacy_retirement_paths | windsurf_retirement_paths), 49)
        self.assertFalse(legacy_retirement_paths & windsurf_retirement_paths)
        output_retirement_overlap = legacy_retirement_paths & expected_paths
        self.assertEqual(output_retirement_overlap, set(golden["reactivated_paths"]))
        retired_only = (legacy_retirement_paths | windsurf_retirement_paths) - expected_paths
        self.assertEqual(len(retired_only), 48)
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
        self.assertEqual(schema["properties"]["legacy_retirements"]["minItems"], 24)
        self.assertEqual(schema["properties"]["legacy_retirements"]["maxItems"], 24)
        self.assertEqual(schema["properties"]["windsurf_retirements"]["minItems"], 25)
        self.assertEqual(schema["properties"]["windsurf_retirements"]["maxItems"], 25)
        self.assertEqual(set(production["status_definitions"]), {"verified", "compatible", "failed", "blocked", "unavailable"})
        self.assertEqual(production["migration"]["cumulative_retirement_count"], 49)
        self.assertTrue(production["migration"]["retire_only_when_manifest_owned_and_byte_matching"])
        self.assertTrue(production["migration"]["preserve_customized_or_unknown"])
        self.assertEqual(production["migration"]["collision_code"], "EXOCORTEX_ADAPTER_COLLISION_PRESERVED")
        self.assertEqual(production["migration"]["reactivated_paths"], [".cursor/skills/onboard/SKILL.md"])

    def test_normative_routing_has_no_named_model_pin(self) -> None:
        text = "\n".join((TEMPLATE / rel).read_text(encoding="utf-8") for rel in [
            ".exocortex/control/MODEL_ROUTING.md", ".cursor/rules/plan-orchestrate.mdc", "AI_START_HERE.md"
        ]).lower()
        for token in ("gpt-", "claude-", "opus", "sonnet", "haiku"):
            self.assertNotIn(token, text)

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
            "/Us" + "ers/",
            "guy" + "robo",
            "M" + "UL-ORCH",
            "M" + "UL-PILOT",
            "EXO-" + "PHASE-B",
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
