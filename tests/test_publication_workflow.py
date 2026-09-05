#!/usr/bin/env python3
"""Offline security and recovery tests for guarded candidate publication.

The suite deliberately mocks every subprocess boundary that could reach Git or
GitHub.  It may create protocol-shaped files, Git-index stand-ins, and lock
files only inside a disposable temporary directory.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = TEMPLATE_ROOT / ".exocortex" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SPEC = importlib.util.spec_from_file_location(
    "exocortex_publish_candidate_under_test",
    SCRIPT_DIR / "publish_candidate.py",
)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import contract
    raise RuntimeError("unable to load guarded publication module")
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


ZERO_DIGEST = "0" * 64
ONE_DIGEST = "1" * 64
BASE_SHA = "a" * 40
COMMIT_SHA = "b" * 40
OTHER_SHA = "c" * 40


def _timestamp(value: dt.datetime) -> str:
    return publication.isoformat(value)


def _envelope(root: Path, *, active: bool = True) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    if active:
        accepted_at = now - dt.timedelta(minutes=5)
        lease_expires_at = now + dt.timedelta(minutes=45)
        expires_at = now + dt.timedelta(hours=1)
    else:
        accepted_at = now - dt.timedelta(hours=3)
        lease_expires_at = now - dt.timedelta(hours=2)
        expires_at = now - dt.timedelta(hours=1)
    allowed_paths = ["README.md", "SHA256SUMS"]
    return {
        "schema_version": publication.PUBLIC_VERSION,
        "kind": "publication_envelope",
        "envelope_id": "publication-test-1",
        "source_work_item": ".exocortex/work-items/work-test-1.json",
        "source_work_item_id": "work-test-1",
        "source_work_item_revision": 7,
        "source_work_item_digest": ZERO_DIGEST,
        "source_completion_digest": ONE_DIGEST,
        "project_root": str(root.resolve()),
        "base_sha": BASE_SHA,
        "source_seal_digest": "2" * 64,
        "candidate_digest": "3" * 64,
        "path_set_digest": publication.canonical_digest_lines(allowed_paths),
        "allowed_paths": allowed_paths,
        "manifest": {"path": "SHA256SUMS", "sha256": "4" * 64},
        "trusted_runtime": {
            "executor_closure_digest": "7" * 64,
            "public_checker_digest": "8" * 64,
            "python_executable_digest": "9" * 64,
            "git_executable_digest": "a" * 64,
            "gh_executable_digest": "b" * 64,
        },
        "branch": "codex/publication-test",
        "writer": {
            "actor": "offline-test",
            "surface_id": "surface-test",
            "executor_id": "executor-test",
            "adapter_version": "test-v1",
        },
        "approval": {
            "approved_by": "offline-test",
            "accepted_at": _timestamp(accepted_at),
            "expires_at": _timestamp(expires_at),
            "summary": "Approve this exact offline publication test envelope.",
        },
        "lease_expires_at": _timestamp(lease_expires_at),
        "remote": {
            "provider": "github",
            "remote_name": "origin",
            "repository": "example-owner/example-repository",
            "repository_id": "123456789",
            "base_branch": "main",
            "base_sha": BASE_SHA,
            "head_branch": "codex/publication-test",
            "force": False,
            "required_checks": ["public-release"],
        },
        "commit": {
            "subject": "Test guarded publication",
            "body": "Offline test fixture.",
            "trailers": ["Agent: codex"],
            "identity": copy.deepcopy(publication.PUBLIC_IDENTITY),
        },
        "pull_request": {
            "draft": True,
            "maintainer_edits": False,
            "title": "Test guarded publication",
            "body": "Offline test fixture.",
        },
        "effects": copy.deepcopy(publication.REQUIRED_EFFECTS),
        "outcome": "Exercise the guarded publication boundary offline.",
        "risk": "low",
        "rollback": "Delete disposable test state.",
        "verification": ["offline unit tests"],
        "exclusions": ["no network and no outward effects"],
    }


def _unknown_record(operation: str, request_id: str) -> dict:
    last_state = "committed" if operation == "push_publication" else "pushed"
    return {
        "id": "publication-test-1",
        "revision": 2,
        "state": "effect_unknown",
        "allowed_paths": ["README.md", "SHA256SUMS"],
        "commit": {"commit_sha": COMMIT_SHA},
        "push": None,
        "draft_pull_request": None,
        "unknown_effect": {
            "request_id": request_id,
            "recorded_at": _timestamp(dt.datetime.now(dt.timezone.utc)),
            "operation": operation,
            "last_confirmed_state": last_state,
            "intent_digest": "5" * 64,
            "reason_code": "test_indeterminate",
        },
        "idempotency": [],
    }


def _capability(path: Path, record: dict, operation: str, request_id: str) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "schema_version": publication.PUBLIC_VERSION,
        "kind": "approval_capability",
        "capability_id": path.stem,
        "work_item_id": record["id"],
        "work_item_revision": 1 if operation == "push_publication" else 2,
        "operation": operation,
        "scope": {
            "allowed_paths": record["allowed_paths"],
            "target_sha": COMMIT_SHA,
            "payload_digest": record["unknown_effect"]["intent_digest"],
        },
        "executor": {
            "surface_id": "surface-test",
            "executor_id": "executor-test",
            "adapter_version": "test-v1",
            "guard_digest": "6" * 64,
            "registry_version": 1,
        },
        "approval": {
            "approved_by": "offline-test",
            "accepted_at": _timestamp(now - dt.timedelta(hours=2)),
            "expires_at": _timestamp(now - dt.timedelta(hours=1)),
            "one_time": True,
            "summary": "Expired authority retained only as consumed evidence.",
        },
        "status": {
            "state": "consumed",
            "revoked_at": None,
            "consumed_at": _timestamp(now - dt.timedelta(hours=1, minutes=30)),
            "consumed_by_request_id": request_id,
        },
    }


def _exact_consumed_capability(
    path: Path,
    envelope: dict,
    *,
    work_item_id: str,
    work_item_revision: int,
    operation: str,
    request_id: str,
    scope: dict,
) -> dict:
    accepted_at = publication.parse_timestamp(envelope["approval"]["accepted_at"], "accepted_at")
    return {
        "schema_version": publication.PUBLIC_VERSION,
        "kind": "approval_capability",
        "capability_id": path.stem,
        "work_item_id": work_item_id,
        "work_item_revision": work_item_revision,
        "operation": operation,
        "scope": copy.deepcopy(scope),
        "executor": {
            "surface_id": envelope["writer"]["surface_id"],
            "executor_id": envelope["writer"]["executor_id"],
            "adapter_version": envelope["writer"]["adapter_version"],
            "guard_digest": publication.current_guard_digest(),
            "registry_version": 1,
        },
        "approval": {
            "approved_by": envelope["approval"]["approved_by"],
            "accepted_at": envelope["approval"]["accepted_at"],
            "expires_at": envelope["approval"]["expires_at"],
            "one_time": True,
            "summary": "Exact consumed offline publication capability.",
        },
        "status": {
            "state": "consumed",
            "revoked_at": None,
            "consumed_at": _timestamp(accepted_at + dt.timedelta(seconds=1)),
            "consumed_by_request_id": request_id,
        },
    }


def _commit_provenance_record(root: Path, envelope: dict, request_id: str) -> dict:
    record = {
        "id": envelope["envelope_id"],
        "state": "committed",
        "allowed_paths": envelope["allowed_paths"],
        "writer": copy.deepcopy(envelope["writer"]),
        "commit": None,
        "push": None,
        "draft_pull_request": None,
        "completion": None,
        "lifecycle_transition": None,
        "retirement": None,
        "unknown_effect": None,
        "idempotency": [],
    }
    intent_digest = "d" * 64
    capability_path = publication._capability_path(
        root, record["id"], "commit_publication", request_id
    )
    capability = _exact_consumed_capability(
        capability_path,
        envelope,
        work_item_id=record["id"],
        work_item_revision=0,
        operation="commit_publication",
        request_id=request_id,
        scope={
            "allowed_paths": record["allowed_paths"],
            "target_sha": envelope["base_sha"],
            "payload_digest": intent_digest,
            "method": "git_temporary_index_commit",
        },
    )
    publication.atomic_write_json(capability_path, capability)
    capability_digest = publication.json_digest(capability)
    result_id = "commit-result"
    record["commit"] = {
        "request_id": request_id,
        "intent_digest": intent_digest,
        "capability_path": capability_path.relative_to(root).as_posix(),
        "capability_digest": capability_digest,
        "commit_sha": COMMIT_SHA,
    }
    record["idempotency"] = [
        {
            "request_id": request_id,
            "operation": "commit_publication",
            "result_id": result_id,
        }
    ]
    transaction_path = publication._tx_path(
        root, record["id"], "commit_publication", request_id
    )
    publication.atomic_write_json(
        transaction_path,
        {
            "schema_version": publication.PUBLIC_VERSION,
            "kind": "publication_transaction",
            "request_id": request_id,
            "operation": "commit_publication",
            "publication_id": record["id"],
            "record_revision": 0,
            "intent_digest": intent_digest,
            "capability_digest": capability_digest,
            "status": "finalized",
            "created_at": envelope["approval"]["accepted_at"],
            "result_id": result_id,
        },
    )
    return record


def _retirement_record(envelope: dict, state: str = "authorized") -> dict:
    commit = None
    push = None
    unknown_effect = None
    revision = 0
    if state in {"committed", "pushed", "effect_unknown"}:
        commit = {"commit_sha": COMMIT_SHA}
        revision = 1
    if state == "pushed":
        push = {"observed_remote_sha": COMMIT_SHA}
        revision = 2
    if state == "effect_unknown":
        revision = 2
        unknown_effect = {
            "request_id": "request-unknown-retirement",
            "operation": "push_publication",
            "intent_digest": "e" * 64,
            "reason_code": "remote_state_indeterminate",
        }
    return {
        "id": envelope["envelope_id"],
        "revision": revision,
        "state": state,
        "source_work_item": envelope["source_work_item"],
        "source_reservation_path": (
            ".exocortex/local/protocol/publication-reservations/"
            f"{envelope['source_work_item_id']}.json"
        ),
        "base_sha": envelope["base_sha"],
        "allowed_paths": envelope["allowed_paths"],
        "writer": copy.deepcopy(envelope["writer"]),
        "reservation": {"status": "active", "lease_expires_at": envelope["lease_expires_at"]},
        "commit": commit,
        "push": push,
        "draft_pull_request": None,
        "lifecycle_transition": None,
        "completion": None,
        "unknown_effect": unknown_effect,
        "retirement": None,
        "idempotency": [],
    }


def _operation_transaction(
    publication_id: str,
    operation: str,
    request_id: str,
    revision: int,
    intent_digest: str,
    status: str,
    **fields,
) -> dict:
    return {
        "schema_version": publication.PUBLIC_VERSION,
        "kind": "publication_transaction",
        "request_id": request_id,
        "operation": operation,
        "publication_id": publication_id,
        "record_revision": revision,
        "intent_digest": intent_digest,
        "status": status,
        "created_at": _timestamp(dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=5)),
        **fields,
    }


def _pr_observation(envelope: dict, request_id: str, number: int = 17) -> dict:
    body = publication._pr_body(envelope, request_id, COMMIT_SHA).decode("utf-8")
    repository = envelope["remote"]["repository"]
    owner = repository.split("/", 1)[0]
    return {
        "number": number,
        "url": f"https://github.com/{repository}/pull/{number}",
        "state": "OPEN",
        "isDraft": True,
        "maintainerCanModify": False,
        "headRefName": envelope["remote"]["head_branch"],
        "headRefOid": COMMIT_SHA,
        "baseRefName": envelope["remote"]["base_branch"],
        "title": envelope["pull_request"]["title"],
        "body": body,
        "headRepository": {"nameWithOwner": repository},
        "headRepositoryOwner": {"login": owner},
        "isCrossRepository": False,
    }


class PublicationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="exocortex-publication-test-")
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def assert_protocol_error(self, code: str, function, *args, **kwargs) -> None:
        with self.assertRaises(publication.ProtocolError) as raised:
            function(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)


class SchemaRuntimeParityTests(PublicationTestCase):
    def test_schema_and_runtime_accept_the_same_complete_metadata_shape(self) -> None:
        schema = json.loads(
            (TEMPLATE_ROOT / ".exocortex" / "schemas" / "publication-envelope.schema.json").read_text(
                encoding="utf-8"
            )
        )
        envelope = _envelope(self.root)
        self.assertEqual(schema["properties"]["schema_version"]["const"], publication.PUBLIC_VERSION)
        self.assertEqual(schema["properties"]["kind"]["const"], envelope["kind"])
        schema_effects = {
            key: value["const"]
            for key, value in schema["properties"]["effects"]["properties"].items()
        }
        self.assertEqual(schema_effects, publication.REQUIRED_EFFECTS)
        for section in ("remote", "commit", "pull_request"):
            self.assertEqual(
                set(schema["properties"][section]["required"]),
                set(envelope[section]),
            )
        with (
            mock.patch.object(publication, "_pin_trusted_runtime") as pin_runtime,
            mock.patch.object(publication, "_git", return_value=b""),
        ):
            validated = publication.validate_publication_envelope(
                copy.deepcopy(envelope), root=self.root, require_active=True
            )
        pin_runtime.assert_called_once_with(self.root, envelope["trusted_runtime"])
        self.assertEqual(validated, envelope)
        self.assertEqual(set(schema["required"]), set(envelope))

    def test_schema_and_runtime_share_public_constants(self) -> None:
        schema = json.loads(
            (TEMPLATE_ROOT / ".exocortex" / "schemas" / "publication-envelope.schema.json").read_text(
                encoding="utf-8"
            )
        )
        schema_effects = {
            key: value["const"]
            for key, value in schema["properties"]["effects"]["properties"].items()
        }
        self.assertEqual(schema["properties"]["schema_version"]["const"], publication.PUBLIC_VERSION)
        self.assertEqual(schema["properties"]["kind"]["const"], "publication_envelope")
        self.assertEqual(schema_effects, publication.REQUIRED_EFFECTS)

    def test_schema_and_runtime_reject_the_same_credential_shaped_source_paths(self) -> None:
        schema = json.loads(
            (TEMPLATE_ROOT / ".exocortex" / "schemas" / "publication-envelope.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            schema["properties"]["allowed_paths"]["items"],
            {"$ref": "#/$defs/source_path"},
        )
        sensitive_pattern = schema["$defs"]["source_path"]["allOf"][1]["not"]["pattern"]
        for relative in (
            "credentials.json",
            "config/secrets.json",
            "keys/private.pem",
            ".ssh/config",
            "config/.envrc",
        ):
            with self.subTest(relative=relative):
                self.assertIsNotNone(re.search(sensitive_pattern, relative))
                envelope = _envelope(self.root)
                envelope["allowed_paths"] = sorted([relative, "SHA256SUMS"])
                envelope["path_set_digest"] = publication.canonical_digest_lines(
                    envelope["allowed_paths"]
                )
                with mock.patch.object(publication, "_pin_trusted_runtime"):
                    self.assert_protocol_error(
                        "protected_path",
                        publication.validate_publication_envelope,
                        envelope,
                        root=self.root,
                    )

        self.assertIsNone(re.search(sensitive_pattern, "docs/public-guide.md"))

    def test_runtime_rejects_unknown_top_level_and_nested_metadata(self) -> None:
        top_level = _envelope(self.root)
        top_level["surprise"] = "not schema bound"
        with (
            mock.patch.object(publication, "_pin_trusted_runtime"),
            mock.patch.object(publication, "_git", return_value=b""),
        ):
            self.assert_protocol_error(
                "unknown_field",
                publication.validate_publication_envelope,
                top_level,
                root=self.root,
            )

        nested = _envelope(self.root)
        nested["remote"]["redirect_url"] = "https://attacker.invalid/repository.git"
        with (
            mock.patch.object(publication, "_pin_trusted_runtime"),
            mock.patch.object(publication, "_git", return_value=b""),
        ):
            self.assert_protocol_error(
                "unknown_field",
                publication.validate_publication_envelope,
                nested,
                root=self.root,
            )


class ProcessBoundaryTests(PublicationTestCase):
    def test_git_and_transport_environments_drop_injection_and_token_variables(self) -> None:
        hostile = {
            "PATH": "/untrusted/bin",
            "HOME": "/test-home",
            "XDG_CONFIG_HOME": "/test-config",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "url.https://attacker.invalid/.insteadOf",
            "GIT_CONFIG_VALUE_0": "https://github.com/",
            "GIT_CONFIG_PARAMETERS": "malicious",
            "GIT_DIR": "/untrusted/git-dir",
            "GIT_SSH_COMMAND": "untrusted-command",
            "GH_CONFIG_DIR": "/untrusted/gh",
            "GH_TOKEN": "test-token-not-a-secret",
            "GITHUB_TOKEN": "test-token-not-a-secret",
            "PYTHONPATH": "/untrusted/python",
            "PYTHONSTARTUP": "/untrusted/startup.py",
        }
        forbidden = set(hostile) - {
            "PATH",
            "HOME",
            "XDG_CONFIG_HOME",
        }
        with mock.patch.dict(os.environ, hostile, clear=True):
            git_env = publication._safe_git_env()
            transport_env = publication._transport_env()
        self.assertTrue(forbidden.isdisjoint(git_env))
        self.assertTrue(forbidden.isdisjoint(transport_env))
        self.assertNotIn("HOME", git_env)
        self.assertNotIn("XDG_CONFIG_HOME", git_env)
        self.assertEqual(git_env["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(transport_env["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(transport_env["GH_PROMPT_DISABLED"], "1")

    def test_transport_disables_terminal_prompts(self) -> None:
        with mock.patch.dict(os.environ, {"PATH": "/untrusted/bin"}, clear=True):
            transport_env = publication._transport_env()
        self.assertEqual(transport_env.get("GIT_TERMINAL_PROMPT"), "0")

    def test_transport_executable_is_not_selected_from_untrusted_path(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")
        with (
            mock.patch.object(publication, "_assert_safe_git_storage"),
            mock.patch.object(publication, "_trusted_tool", return_value="/usr/bin/git"),
            mock.patch.object(publication, "_trusted_path", return_value="/usr/bin:/bin"),
            mock.patch.object(publication.subprocess, "run", return_value=completed) as run,
        ):
            publication._git(self.root, "status", "--porcelain=v1")
        argv = run.call_args.args[0]
        self.assertTrue(Path(argv[0]).is_absolute())
        self.assertNotEqual(Path(argv[0]).parent, Path("/untrusted/bin"))

    def test_git_remote_observation_disables_http_redirects(self) -> None:
        completed = subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")
        with (
            mock.patch.object(publication, "_assert_safe_git_storage"),
            mock.patch.object(publication, "_trusted_tool", return_value="/usr/bin/git"),
            mock.patch.object(publication, "_trusted_path", return_value="/usr/bin:/bin"),
            mock.patch.object(publication.subprocess, "run", return_value=completed) as run,
        ):
            publication._git(
                self.root,
                "ls-remote",
                "--refs",
                "https://github.com/example-owner/example-repository.git",
            )
        argv = run.call_args.args[0]
        config_values = [argv[index + 1] for index, value in enumerate(argv[:-1]) if value == "-c"]
        self.assertIn("http.followRedirects=false", config_values)

    def test_trusted_checker_receives_the_exact_pinned_git_path_and_digest(self) -> None:
        tools = {"python": "/usr/bin/python3", "git": "/usr/bin/git"}
        with (
            mock.patch.object(publication, "_trusted_tool", side_effect=lambda name: tools[name]),
            mock.patch.object(publication, "_trusted_tool_digest", return_value="d" * 64),
            mock.patch.object(publication, "_run") as run,
        ):
            publication._run_checker_bytes(
                b"print('fictional checker')\n",
                cwd=self.root,
                arguments=("--root", str(self.root), "--source-tree"),
            )
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], "/usr/bin/python3")
        self.assertEqual(argv[argv.index("--git-executable") + 1], "/usr/bin/git")
        self.assertEqual(argv[argv.index("--git-executable-sha256") + 1], "d" * 64)

    def test_same_root_cannot_be_declared_as_trusted_publication_runtime(self) -> None:
        self.assert_protocol_error(
            "untrusted_runtime_root",
            publication._require_trusted_runtime_root,
            self.root,
            self.root,
        )


class TrustedCheckerPinTests(PublicationTestCase):
    def checker_state(self, path: Path) -> dict:
        value = path.stat()
        return {
            "path": path,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "device": value.st_dev,
            "inode": value.st_ino,
            "size": value.st_size,
            "mtime_ns": value.st_mtime_ns,
        }

    def test_checker_bytes_are_read_once_against_the_retained_pin(self) -> None:
        checker = self.root / "scripts" / "check-public-release.py"
        checker.parent.mkdir()
        approved = b"print('approved fictional checker')\n"
        checker.write_bytes(approved)
        state = {"scripts/check-public-release.py": self.checker_state(checker)}
        with mock.patch.object(publication, "_TRUSTED_RUNTIME_STATE", state):
            self.assertEqual(publication._trusted_checker_bytes(), approved)

    def test_stable_checker_replacement_after_pin_is_rejected(self) -> None:
        checker = self.root / "scripts" / "check-public-release.py"
        checker.parent.mkdir()
        approved = b"print('approved fictional checker')\n"
        checker.write_bytes(approved)
        state = {"scripts/check-public-release.py": self.checker_state(checker)}
        replacement = checker.with_name("replacement.py")
        replacement.write_bytes(b"print('replaced fictional checker')\n")
        os.replace(replacement, checker)
        with mock.patch.object(publication, "_TRUSTED_RUNTIME_STATE", state):
            self.assert_protocol_error(
                "untrusted_runtime", publication._trusted_checker_bytes
            )

    def test_checker_read_race_is_rejected(self) -> None:
        checker = self.root / "scripts" / "check-public-release.py"
        checker.parent.mkdir()
        approved = b"print('approved fictional checker')\n"
        checker.write_bytes(approved)
        state = {"scripts/check-public-release.py": self.checker_state(checker)}
        original_read = publication.os.read
        changed = False

        def racing_read(descriptor: int, size: int) -> bytes:
            nonlocal changed
            chunk = original_read(descriptor, size)
            if chunk and not changed:
                changed = True
                checker.write_bytes(b"X" * len(approved))
                pinned_mtime = state["scripts/check-public-release.py"]["mtime_ns"]
                os.utime(checker, ns=(pinned_mtime + 1, pinned_mtime + 1))
            return chunk

        with (
            mock.patch.object(publication, "_TRUSTED_RUNTIME_STATE", state),
            mock.patch.object(publication.os, "read", side_effect=racing_read),
        ):
            self.assert_protocol_error(
                "untrusted_runtime", publication._trusted_checker_bytes
            )


class RemoteIdentityTests(PublicationTestCase):
    def test_remote_url_ignores_all_repository_local_remote_configuration(self) -> None:
        envelope = _envelope(self.root)
        expected = publication._canonical_remote_url(envelope)
        with mock.patch.object(publication, "_git") as git:
            self.assertEqual(publication._require_remote_url(self.root, envelope), expected)
        git.assert_not_called()

    def test_repository_identity_binds_both_name_and_immutable_numeric_id(self) -> None:
        envelope = _envelope(self.root)
        exact = {"id": int(envelope["remote"]["repository_id"]), "full_name": envelope["remote"]["repository"]}

        def connection(payload: dict, *, status: int = 200, location: str | None = None):
            response = mock.Mock()
            response.status = status
            response.getheader.return_value = location
            response.read.return_value = json.dumps(payload).encode()
            client = mock.Mock()
            client.getresponse.return_value = response
            return client

        exact_connection = connection(exact)
        with (
            mock.patch.object(
                publication, "_repository_tls_context", return_value=mock.sentinel.tls_context
            ),
            mock.patch.object(
                publication.http.client, "HTTPSConnection", return_value=exact_connection
            ) as constructor,
        ):
            publication._verify_repository_identity(self.root, envelope)
        constructor.assert_called_once_with(
            publication.GITHUB_API_HOST,
            timeout=15,
            context=mock.sentinel.tls_context,
        )
        request = exact_connection.request.call_args
        self.assertEqual(request.args[:2], ("GET", "/repos/example-owner/example-repository"))
        exact_connection.close.assert_called_once_with()

        attacks = [
            {**exact, "id": 987654321},
            {**exact, "full_name": "attacker/example-repository"},
        ]
        for observed in attacks:
            with self.subTest(observed=observed):
                with (
                    mock.patch.object(
                        publication, "_repository_tls_context", return_value=mock.sentinel.tls_context
                    ),
                    mock.patch.object(
                        publication.http.client,
                        "HTTPSConnection",
                        return_value=connection(observed),
                    ),
                ):
                    self.assert_protocol_error(
                        "repository_identity_mismatch",
                        publication._verify_repository_identity,
                        self.root,
                        envelope,
                    )

        redirected = connection(exact, status=301, location="https://api.github.com/repos/renamed/repository")
        with (
            mock.patch.object(
                publication, "_repository_tls_context", return_value=mock.sentinel.tls_context
            ),
            mock.patch.object(
                publication.http.client, "HTTPSConnection", return_value=redirected
            ),
        ):
            self.assert_protocol_error(
                "repository_identity_redirect",
                publication._verify_repository_identity,
                self.root,
                envelope,
            )

    def test_pr_identity_rejects_forks_and_repository_substitution(self) -> None:
        envelope = _envelope(self.root)
        request_id = "request-pr-identity"
        exact = _pr_observation(envelope, request_id)
        body = publication._pr_body(envelope, request_id, COMMIT_SHA)
        self.assertEqual(publication._verified_pr(envelope, COMMIT_SHA, body, [exact]), exact)

        attacks = []
        fork = copy.deepcopy(exact)
        fork["isCrossRepository"] = True
        attacks.append(fork)
        wrong_owner = copy.deepcopy(exact)
        wrong_owner["headRepositoryOwner"] = {"login": "attacker"}
        attacks.append(wrong_owner)
        wrong_repository = copy.deepcopy(exact)
        wrong_repository["headRepository"] = {"nameWithOwner": "attacker/example-repository"}
        attacks.append(wrong_repository)
        wrong_url = copy.deepcopy(exact)
        wrong_url["url"] = "https://github.com/attacker/example-repository/pull/17"
        attacks.append(wrong_url)
        for observation in attacks:
            with self.subTest(observation=observation):
                self.assert_protocol_error(
                    "pr_state_mismatch",
                    publication._verified_pr,
                    envelope,
                    COMMIT_SHA,
                    body,
                    [observation],
                )

    def test_required_check_digest_is_order_independent_but_metadata_exact(self) -> None:
        envelope = _envelope(self.root)
        envelope["remote"]["required_checks"] = ["alpha", "zeta"]
        alpha = {"name": "alpha", "bucket": "pass", "state": "SUCCESS", "workflow": "release"}
        zeta = {"name": "zeta", "bucket": "pass", "state": "SUCCESS", "workflow": "release"}
        with (
            mock.patch.object(publication, "_verify_repository_identity"),
            mock.patch.object(publication, "_gh", return_value=json.dumps([zeta, alpha]).encode()),
        ):
            first = publication._verified_required_checks(self.root, envelope, 17)
        with (
            mock.patch.object(publication, "_verify_repository_identity"),
            mock.patch.object(publication, "_gh", return_value=json.dumps([alpha, zeta]).encode()),
        ):
            second = publication._verified_required_checks(self.root, envelope, 17)
        self.assertEqual(first, second)

        unexpected = copy.deepcopy(alpha)
        unexpected["conclusion"] = "success"
        with (
            mock.patch.object(publication, "_verify_repository_identity"),
            mock.patch.object(publication, "_gh", return_value=json.dumps([unexpected, zeta]).encode()),
        ):
            self.assert_protocol_error(
                "required_checks_indeterminate",
                publication._verified_required_checks,
                self.root,
                envelope,
                17,
            )


class ReplayAndAuthorityTests(PublicationTestCase):
    def test_expired_envelope_cannot_authorize_a_new_effect(self) -> None:
        envelope = _envelope(self.root, active=False)
        with (
            mock.patch.object(publication, "_pin_trusted_runtime"),
            mock.patch.object(publication, "_git", return_value=b""),
        ):
            self.assert_protocol_error(
                "expired_publication",
                publication.validate_publication_envelope,
                envelope,
                root=self.root,
                require_active=True,
            )

    def test_exact_push_replay_after_expiry_performs_no_outward_observation(self) -> None:
        request_id = "request-push-replay"
        envelope = _envelope(self.root, active=False)
        record = {
            "id": envelope["envelope_id"],
            "revision": 2,
            "state": "pushed",
            "push": {"observed_remote_sha": COMMIT_SHA},
        }
        replay = {
            "request_id": request_id,
            "operation": "push_publication",
            "result_id": "publication-push-result",
        }
        args = argparse.Namespace(
            project_root=self.root,
            publication=f"{publication.PUBLICATION_PREFIX}{record['id']}.json",
            request_id=request_id,
            surface_id=envelope["writer"]["surface_id"],
            executor_id=envelope["writer"]["executor_id"],
            adapter_version=envelope["writer"]["adapter_version"],
        )
        replay_transaction = _operation_transaction(
            record["id"],
            "push_publication",
            request_id,
            1,
            "1" * 64,
            "finalized",
            result_id=replay["result_id"],
            remote_head_sha=COMMIT_SHA,
        )
        with (
            mock.patch.object(
                publication,
                "_load_operation",
                return_value=(self.root / "record.json", record, envelope, replay, False),
            ),
            mock.patch.object(publication, "_assert_actor"),
            mock.patch.object(publication, "load_safe_json", return_value=replay_transaction),
            mock.patch.object(publication, "_observe_remote") as observe,
            mock.patch.object(publication, "_recheck_consumed_operation") as recheck,
            mock.patch.object(publication, "_run") as run,
        ):
            result = publication.push_publication(args)
        self.assertTrue(result["replay"])
        self.assertEqual(result["remote_head_sha"], COMMIT_SHA)
        observe.assert_not_called()
        recheck.assert_not_called()
        run.assert_not_called()

    def test_current_clock_recheck_rejects_expired_recovery_before_effect(self) -> None:
        envelope = _envelope(self.root, active=False)
        record = {"id": envelope["envelope_id"], "allowed_paths": envelope["allowed_paths"]}
        with (
            mock.patch.object(publication, "_pin_trusted_runtime"),
            mock.patch.object(publication, "_git", return_value=b""),
            mock.patch.object(publication, "_verify_executor") as verify_executor,
            mock.patch.object(publication, "check_authority") as check_authority,
        ):
            self.assert_protocol_error(
                "expired_publication",
                publication._recheck_consumed_operation,
                self.root,
                record,
                envelope,
                "push_publication",
                "request-expired-recovery",
                {"operation": "push_publication"},
            )
        verify_executor.assert_not_called()
        check_authority.assert_not_called()

    def test_bootstrap_expiry_recheck_precedes_all_durable_state_writes(self) -> None:
        envelope = _envelope(self.root)
        work = {"id": envelope["source_work_item_id"], "revision": 7}
        args = argparse.Namespace(
            project_root=self.root,
            envelope_source=Path(
                ".exocortex/local/protocol/inbox/publication-test.json"
            ),
            request_id="request-bootstrap-expired-before-write",
        )
        expired = publication.ProtocolError(
            "expired_publication",
            "publication expired during bootstrap validation",
        )
        source_path = self.root / envelope["source_work_item"]
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text("{}\n", encoding="utf-8")
        with (
            mock.patch.object(
                publication,
                "read_local_protocol_input",
                return_value=json.dumps(envelope).encode("utf-8"),
            ),
            mock.patch.object(
                publication,
                "validate_publication_envelope",
                side_effect=[envelope, envelope, expired],
            ),
            mock.patch.object(publication, "_verify_source_candidate", return_value=work),
            mock.patch.object(publication, "_verify_executor", return_value=({}, {})),
            mock.patch.object(publication, "_public_metadata_check"),
            mock.patch.object(publication, "validate_work_item", return_value=work),
            mock.patch.object(
                publication,
                "_recheck_bootstrap_authority",
                wraps=publication._recheck_bootstrap_authority,
            ) as recheck,
            mock.patch.object(
                publication,
                "exclusive_lock",
                side_effect=lambda _path: contextlib.nullcontext(),
            ),
            mock.patch.object(publication, "atomic_write_json") as atomic_write,
            mock.patch.object(publication, "exclusive_write_json") as exclusive_write,
            mock.patch.object(publication, "_claim_source_reservation") as claim,
        ):
            self.assert_protocol_error(
                "expired_publication",
                publication.bootstrap_publication,
                args,
            )
        recheck.assert_called_once_with(self.root, envelope, work)
        atomic_write.assert_not_called()
        exclusive_write.assert_not_called()
        claim.assert_not_called()

    def test_commit_authority_callback_runs_before_shared_git_object_writes(self) -> None:
        envelope = _envelope(self.root)
        approved_sources = {
            "README.md": (b"public readme\n", "100644"),
            "SHA256SUMS": (b"0" * 64 + b"  README.md\n", "100644"),
        }
        expected_evidence = {
            "changed_paths": envelope["allowed_paths"],
            "path_set_digest": envelope["path_set_digest"],
            "candidate_digest": envelope["candidate_digest"],
        }
        expired = publication.ProtocolError(
            "expired_publication",
            "publication expired immediately before object writes",
        )
        commands = []

        def git(_root, *args, **_kwargs):
            commands.append(args)
            return b""

        recheck = mock.Mock(side_effect=expired)
        with (
            mock.patch.object(
                publication,
                "_approved_snapshot_evidence",
                return_value=expected_evidence,
            ),
            mock.patch.object(
                publication,
                "_real_index_path",
                return_value=self.root / "index",
            ),
            mock.patch.object(publication, "_index_digest", return_value=ZERO_DIGEST),
            mock.patch.object(publication, "_git", side_effect=git),
        ):
            self.assert_protocol_error(
                "expired_publication",
                publication._prepare_commit,
                self.root,
                envelope,
                approved_sources,
                recheck,
            )
        recheck.assert_called_once_with()
        self.assertEqual(commands, [("read-tree", envelope["base_sha"])])

    def test_expired_completion_retry_uses_durable_draft_pr_evidence(self) -> None:
        envelope = _envelope(self.root, active=False)
        request_id = "request-complete-recovery"
        pr_url = f"https://github.com/{envelope['remote']['repository']}/pull/17"
        record = {
            "id": envelope["envelope_id"],
            "state": "draft_pr_verified",
            "revision": 3,
            "commit": {"commit_sha": COMMIT_SHA},
            "draft_pull_request": {
                "request_id": "request-create-pr",
                "number": 17,
                "url": pr_url,
                "observation_digest": "e" * 64,
            },
            "reservation": {"status": "active"},
            "lifecycle_transition": None,
            "completion": None,
            "idempotency": [],
        }
        args = argparse.Namespace(
            project_root=self.root,
            publication=f"{publication.PUBLICATION_PREFIX}{record['id']}.json",
            request_id=request_id,
            surface_id=envelope["writer"]["surface_id"],
            executor_id=envelope["writer"]["executor_id"],
            adapter_version=envelope["writer"]["adapter_version"],
        )
        transaction_path = self.root / "complete-transaction.json"
        transaction = {
            "status": "capability_consumed",
            "capability_digest": "c" * 64,
        }
        checks_digest = "d" * 64
        lifecycle = {"transition_id": "transition-recovered"}
        released = {
            "status": "released",
            "released_at": _timestamp(dt.datetime.now(dt.timezone.utc)),
        }
        with (
            mock.patch.object(
                publication,
                "_load_operation",
                return_value=(
                    self.root / "publication.json",
                    record,
                    envelope,
                    None,
                    True,
                ),
            ),
            mock.patch.object(publication, "_assert_actor"),
            mock.patch.object(
                publication,
                "_begin_transaction",
                return_value=(transaction_path, transaction, False),
            ),
            mock.patch.object(
                publication,
                "_consume_operation",
                return_value=("capability.json", "c" * 64),
            ),
            mock.patch.object(
                publication,
                "_recovered_transition_checks_digest",
                return_value=checks_digest,
            ),
            mock.patch.object(
                publication,
                "_ensure_awaiting_release",
                return_value=lifecycle,
            ),
            mock.patch.object(
                publication,
                "_validate_record",
                side_effect=lambda value: value,
            ),
            mock.patch.object(
                publication,
                "_validate_source_reservation",
                return_value=(self.root / "source-reservation.json", released),
            ),
            mock.patch.object(publication, "load_safe_json", return_value=released),
            mock.patch.object(publication, "atomic_write_json"),
            mock.patch.object(publication, "_tx_status") as tx_status,
            mock.patch.object(
                publication,
                "exclusive_lock",
                side_effect=lambda _path: contextlib.nullcontext(),
            ),
            mock.patch.object(publication, "_observe_remote") as observe,
            mock.patch.object(publication, "_query_prs") as query_prs,
            mock.patch.object(publication, "_verified_required_checks") as checks,
            mock.patch.object(publication, "_recheck_consumed_operation") as recheck,
        ):
            result = publication.complete_publication(args)
        self.assertTrue(result["ok"])
        self.assertEqual(result["pr_url"], pr_url)
        self.assertEqual(tx_status.call_args.kwargs["pr_url"], pr_url)
        observe.assert_not_called()
        query_prs.assert_not_called()
        checks.assert_not_called()
        recheck.assert_not_called()


class UnknownEffectReconciliationTests(PublicationTestCase):
    def test_expired_unknown_push_can_be_reconciled_by_exact_observation_only(self) -> None:
        request_id = "request-unknown-push"
        record = _unknown_record("push_publication", request_id)
        envelope = _envelope(self.root, active=False)
        writes = []
        transaction = _operation_transaction(
            record["id"],
            "push_publication",
            request_id,
            1,
            record["unknown_effect"]["intent_digest"],
            "effect_unknown",
            reason_code=record["unknown_effect"]["reason_code"],
        )
        with (
            mock.patch.object(
                publication,
                "_unknown_capability_evidence",
                return_value=("capability.json", "7" * 64),
            ),
            mock.patch.object(publication, "_observe_remote", return_value=(BASE_SHA, COMMIT_SHA)),
            mock.patch.object(publication, "_validate_record", side_effect=lambda value: value),
            mock.patch.object(publication, "atomic_write_json", side_effect=lambda path, value: writes.append((path, copy.deepcopy(value)))),
            mock.patch.object(publication, "load_safe_json", return_value=transaction),
            mock.patch.object(publication, "_tx_status", return_value={"status": "finalized"}) as tx_status,
            mock.patch.object(publication, "_recheck_consumed_operation") as recheck,
            mock.patch.object(publication, "_run") as run,
        ):
            result = publication._reconcile_unknown_push(
                self.root,
                self.root / "record.json",
                record,
                envelope,
                request_id,
            )
        self.assertTrue(result["reconciled"])
        self.assertEqual(result["state"], "pushed")
        self.assertEqual(record["push"]["observed_remote_sha"], COMMIT_SHA)
        self.assertIsNone(record["unknown_effect"])
        self.assertEqual(len(writes), 1)
        tx_status.assert_called_once()
        recheck.assert_not_called()
        run.assert_not_called()

    def test_absent_or_colliding_unknown_push_never_retries_or_writes(self) -> None:
        request_id = "request-unknown-push-absent"
        envelope = _envelope(self.root, active=False)
        observations = [
            ((BASE_SHA, None), "effect_absent"),
            ((BASE_SHA, OTHER_SHA), "remote_head_collision"),
        ]
        for observed, expected_code in observations:
            record = _unknown_record("push_publication", request_id)
            with self.subTest(observed=observed):
                with (
                    mock.patch.object(
                        publication,
                        "_unknown_capability_evidence",
                        return_value=("capability.json", "7" * 64),
                    ),
                    mock.patch.object(publication, "_observe_remote", return_value=observed),
                    mock.patch.object(publication, "atomic_write_json") as write,
                    mock.patch.object(publication, "_tx_status") as tx_status,
                    mock.patch.object(publication, "_run") as run,
                ):
                    self.assert_protocol_error(
                        expected_code,
                        publication._reconcile_unknown_push,
                        self.root,
                        self.root / "record.json",
                        record,
                        envelope,
                        request_id,
                    )
                write.assert_not_called()
                tx_status.assert_not_called()
                run.assert_not_called()

    def test_expired_unknown_pr_can_be_reconciled_by_exact_observation_only(self) -> None:
        request_id = "request-unknown-pr"
        record = _unknown_record("create_draft_pr", request_id)
        envelope = _envelope(self.root, active=False)
        exact = _pr_observation(envelope, request_id)
        transaction = _operation_transaction(
            record["id"],
            "create_draft_pr",
            request_id,
            2,
            record["unknown_effect"]["intent_digest"],
            "effect_unknown",
            reason_code=record["unknown_effect"]["reason_code"],
        )
        with (
            mock.patch.object(
                publication,
                "_unknown_capability_evidence",
                return_value=("capability.json", "7" * 64),
            ),
            mock.patch.object(publication, "_query_prs", return_value=[exact]),
            mock.patch.object(publication, "_validate_record", side_effect=lambda value: value),
            mock.patch.object(publication, "atomic_write_json"),
            mock.patch.object(publication, "load_safe_json", return_value=transaction),
            mock.patch.object(publication, "_tx_status", return_value={"status": "finalized"}),
            mock.patch.object(publication, "_recheck_consumed_operation") as recheck,
            mock.patch.object(publication, "_gh") as gh,
        ):
            result = publication._reconcile_unknown_pr(
                self.root,
                self.root / "record.json",
                record,
                envelope,
                request_id,
            )
        self.assertTrue(result["reconciled"])
        self.assertEqual(result["pr_number"], exact["number"])
        recheck.assert_not_called()
        gh.assert_not_called()

    def test_absent_unknown_pr_never_retries_or_writes(self) -> None:
        request_id = "request-unknown-pr-absent"
        record = _unknown_record("create_draft_pr", request_id)
        envelope = _envelope(self.root, active=False)
        with (
            mock.patch.object(
                publication,
                "_unknown_capability_evidence",
                return_value=("capability.json", "7" * 64),
            ),
            mock.patch.object(publication, "_query_prs", return_value=[]),
            mock.patch.object(publication, "atomic_write_json") as write,
            mock.patch.object(publication, "_tx_status") as tx_status,
            mock.patch.object(publication, "_gh") as gh,
        ):
            self.assert_protocol_error(
                "effect_absent",
                publication._reconcile_unknown_pr,
                self.root,
                self.root / "record.json",
                record,
                envelope,
                request_id,
            )
        write.assert_not_called()
        tx_status.assert_not_called()
        gh.assert_not_called()


class TransactionEvidenceTests(PublicationTestCase):
    def test_transaction_path_binds_publication_operation_and_request(self) -> None:
        first = publication._tx_path(self.root, "publication-a", "push_publication", "request-1")
        second = publication._tx_path(self.root, "publication-b", "push_publication", "request-1")
        third = publication._tx_path(self.root, "publication-a", "create_draft_pr", "request-1")
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertLessEqual(len(first.name.encode("utf-8")), os.pathconf(self.root, "PC_NAME_MAX"))
        self.assertNotIn("publication-a-push_publication-request-1", first.name)

        long_publication = "p" * 200
        long_request = "r" * 200
        long_path = publication._tx_path(
            self.root, long_publication, "retire_publication", long_request
        )
        self.assertLessEqual(len(long_path.name.encode("utf-8")), os.pathconf(self.root, "PC_NAME_MAX"))
        self.assertNotEqual(first, long_path)

    def test_existing_transaction_rejects_immutable_identity_tampering(self) -> None:
        record = {"id": "publication-a", "revision": 1}
        intent = {"operation": "push_publication", "commit_sha": COMMIT_SHA}
        path, transaction, created = publication._begin_transaction(
            self.root, record, "request-1", "push_publication", intent
        )
        self.assertTrue(created)
        transaction["publication_id"] = "publication-b"
        publication.atomic_write_json(path, transaction)
        self.assert_protocol_error(
            "transaction_conflict",
            publication._begin_transaction,
            self.root,
            record,
            "request-1",
            "push_publication",
            intent,
        )

    def test_finalized_result_must_match_exact_idempotency_evidence(self) -> None:
        request_id = "request-provenance"
        envelope = _envelope(self.root)
        record = _commit_provenance_record(self.root, envelope, request_id)
        transaction_path = publication._tx_path(
            self.root, record["id"], "commit_publication", request_id
        )
        transaction = publication.load_safe_json(transaction_path, "publication transaction")
        transaction["result_id"] = "tampered-result"
        publication.atomic_write_json(transaction_path, transaction)
        self.assert_protocol_error(
            "publication_provenance_mismatch",
            publication._verify_record_provenance,
            self.root,
            record,
            envelope,
        )

    def test_unknown_effect_rejects_consumed_capability_request_tampering(self) -> None:
        operation = "push_publication"
        request_id = "request-unknown-evidence"
        record = _unknown_record(operation, request_id)
        capability_path = publication._capability_path(self.root, record["id"], operation, request_id)
        capability = _capability(capability_path, record, operation, request_id)
        capability["status"]["consumed_by_request_id"] = "different-request"
        publication.atomic_write_json(capability_path, capability)
        transaction_path = publication._tx_path(self.root, record["id"], operation, request_id)
        publication.atomic_write_json(
            transaction_path,
            {
                "schema_version": publication.PUBLIC_VERSION,
                "kind": "publication_transaction",
                "request_id": request_id,
                "operation": operation,
                "publication_id": record["id"],
                "record_revision": 1,
                "intent_digest": record["unknown_effect"]["intent_digest"],
                "status": "effect_unknown",
                "reason_code": record["unknown_effect"]["reason_code"],
            },
        )
        self.assert_protocol_error(
            "publication_provenance_mismatch",
            publication._unknown_capability_evidence,
            self.root,
            record,
            operation,
            request_id,
        )

    def test_unknown_effect_rejects_transaction_identity_tampering(self) -> None:
        operation = "push_publication"
        request_id = "request-unknown-transaction"
        envelope = _envelope(self.root)
        record = _commit_provenance_record(self.root, envelope, "request-commit-provenance")
        record["state"] = "effect_unknown"
        record["unknown_effect"] = {
            "request_id": request_id,
            "operation": operation,
            "intent_digest": "5" * 64,
            "reason_code": "test_indeterminate",
        }
        capability_path = publication._capability_path(self.root, record["id"], operation, request_id)
        capability = _exact_consumed_capability(
            capability_path,
            envelope,
            work_item_id=record["id"],
            work_item_revision=1,
            operation=operation,
            request_id=request_id,
            scope={
                "allowed_paths": record["allowed_paths"],
                "target_sha": COMMIT_SHA,
                "payload_digest": record["unknown_effect"]["intent_digest"],
                "destination_id": publication._remote_destination(envelope),
                "method": "git_create_only_branch_push",
            },
        )
        publication.atomic_write_json(capability_path, capability)
        capability_digest = publication.json_digest(capability)
        transaction_path = publication._tx_path(self.root, record["id"], operation, request_id)
        publication.atomic_write_json(
            transaction_path,
            {
                "schema_version": publication.PUBLIC_VERSION,
                "kind": "publication_transaction",
                "request_id": request_id,
                "operation": operation,
                "publication_id": "different-publication",
                "record_revision": 1,
                "intent_digest": record["unknown_effect"]["intent_digest"],
                "capability_digest": capability_digest,
                "status": "effect_unknown",
                "created_at": envelope["approval"]["accepted_at"],
                "reason_code": record["unknown_effect"]["reason_code"],
            },
        )
        self.assert_protocol_error(
            "publication_provenance_mismatch",
            publication._verify_record_provenance,
            self.root,
            record,
            envelope,
        )


class RetirementTests(PublicationTestCase):
    def _retirement_args(self, envelope: dict, request_id: str, capability: str) -> argparse.Namespace:
        return argparse.Namespace(
            project_root=self.root,
            publication=f"{publication.PUBLICATION_PREFIX}{envelope['envelope_id']}.json",
            request_id=request_id,
            capability=capability,
            reason="Retire the abandoned local publication reservation.",
            surface_id=envelope["writer"]["surface_id"],
            executor_id=envelope["writer"]["executor_id"],
            adapter_version=envelope["writer"]["adapter_version"],
        )

    def _fresh_retirement_capability(
        self,
        envelope: dict,
        record: dict,
        request_id: str,
        intent_digest: str,
    ) -> tuple[Path, dict]:
        path = publication._capability_path(
            self.root, record["id"], "retire_publication", request_id
        )
        now = dt.datetime.now(dt.timezone.utc)
        capability = {
            "schema_version": publication.PUBLIC_VERSION,
            "kind": "approval_capability",
            "capability_id": path.stem,
            "work_item_id": record["id"],
            "work_item_revision": record["revision"],
            "operation": "retire_publication",
            "scope": publication._retirement_scope(
                self.root, record, envelope, intent_digest
            ),
            "executor": {
                "surface_id": envelope["writer"]["surface_id"],
                "executor_id": envelope["writer"]["executor_id"],
                "adapter_version": envelope["writer"]["adapter_version"],
                "guard_digest": publication.current_guard_digest(),
                "registry_version": 1,
            },
            "approval": {
                "approved_by": "offline-test",
                "accepted_at": _timestamp(now - dt.timedelta(minutes=5)),
                "expires_at": _timestamp(now + dt.timedelta(hours=1)),
                "one_time": True,
                "summary": "Retire only the exact local publication reservation.",
            },
            "status": {
                "state": "active",
                "revoked_at": None,
                "consumed_at": None,
                "consumed_by_request_id": None,
            },
        }
        publication.atomic_write_json(path, capability)
        return path, capability

    def test_fresh_exact_external_retirement_capability_is_consumed_not_minted(self) -> None:
        envelope = _envelope(self.root)
        record = _retirement_record(envelope)
        request_id = "request-retire-fresh"
        intent_digest = "f" * 64
        capability_path, capability = self._fresh_retirement_capability(
            envelope, record, request_id, intent_digest
        )
        registry_path = self.root / publication.REGISTRY_RELPATH
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("{}\n", encoding="utf-8")
        consumed = copy.deepcopy(capability)
        consumed["status"] = {
            "state": "consumed",
            "revoked_at": None,
            "consumed_at": _timestamp(dt.datetime.now(dt.timezone.utc)),
            "consumed_by_request_id": request_id,
        }
        args = self._retirement_args(
            envelope, request_id, capability_path.relative_to(self.root).as_posix()
        )
        with (
            mock.patch.object(publication, "consume_capability", return_value=consumed) as consume,
            mock.patch.object(publication, "exclusive_write_json") as mint,
        ):
            relative, digest, observed = publication._consume_retirement_capability(
                self.root, record, envelope, args, intent_digest
            )
        self.assertEqual(relative, capability_path.relative_to(self.root).as_posix())
        self.assertEqual(digest, publication.json_digest(consumed))
        self.assertEqual(observed, consumed)
        self.assertEqual(consume.call_args.kwargs["check_kwargs"]["role"], "writer")
        self.assertEqual(
            consume.call_args.kwargs["check_kwargs"]["target_paths"],
            publication._retirement_scope(self.root, record, envelope, intent_digest)["allowed_paths"],
        )
        mint.assert_not_called()

    def test_authorized_retirement_is_local_only_and_releases_reservations(self) -> None:
        envelope = _envelope(self.root)
        record = _retirement_record(envelope)
        request_id = "request-retire-local"
        capability_path = publication._capability_path(
            self.root, record["id"], "retire_publication", request_id
        )
        capability_relative = capability_path.relative_to(self.root).as_posix()
        args = self._retirement_args(envelope, request_id, capability_relative)
        transaction_path = self.root / "retirement-transaction.json"
        now = dt.datetime.now(dt.timezone.utc)
        consumed = {
            "status": {
                "state": "consumed",
                "consumed_at": _timestamp(now),
            },
            "approval": {"expires_at": _timestamp(now + dt.timedelta(hours=1))},
        }
        capability_path.parent.mkdir(parents=True, exist_ok=True)
        capability_path.write_text("{}\n", encoding="utf-8")
        registry_path = self.root / publication.REGISTRY_RELPATH
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("{}\n", encoding="utf-8")
        writes = []
        source_reservation = {"status": "active", "released_at": None}
        with (
            mock.patch.object(
                publication,
                "_load_publication",
                return_value=(self.root / "publication.json", record, envelope),
            ),
            mock.patch.object(
                publication,
                "_begin_transaction",
                return_value=(transaction_path, {"status": "intent"}, True),
            ),
            mock.patch.object(
                publication,
                "_consume_retirement_capability",
                return_value=(capability_relative, "1" * 64, consumed),
            ),
            mock.patch.object(publication, "check_authority"),
            mock.patch.object(publication, "_validate_record", side_effect=lambda value: value),
            mock.patch.object(
                publication,
                "_validate_source_reservation",
                return_value=(self.root / "source-reservation.json", source_reservation),
            ),
            mock.patch.object(
                publication,
                "atomic_write_json",
                side_effect=lambda path, value: writes.append((path, copy.deepcopy(value))),
            ),
            mock.patch.object(publication, "_tx_status", side_effect=lambda path, value, status, **fields: {**value, "status": status, **fields}),
            mock.patch.object(publication, "_observe_remote") as observe,
            mock.patch.object(publication, "_query_prs") as query_prs,
            mock.patch.object(publication, "_run") as run,
            mock.patch.object(publication, "_gh") as gh,
        ):
            result = publication.retire_publication(args)
        self.assertFalse(result["replay"])
        self.assertEqual(result["state"], "retired")
        self.assertEqual(result["preserved_effects"], [])
        self.assertEqual(record["reservation"]["status"], "released")
        self.assertEqual(source_reservation["status"], "released")
        self.assertGreaterEqual(len(writes), 2)
        observe.assert_not_called()
        query_prs.assert_not_called()
        run.assert_not_called()
        gh.assert_not_called()

    def test_exact_retirement_release_allows_source_reuse_and_new_bootstrap_claim(self) -> None:
        old_envelope = _envelope(self.root)
        old_envelope["envelope_id"] = "publication-retired"
        released_at = _timestamp(dt.datetime.now(dt.timezone.utc))
        retirement_request = "request-retired-source"
        retirement_intent = "d" * 64
        reservation_path = publication.publication_reservation_path(
            self.root,
            old_envelope["source_work_item_id"],
        )
        old_reservation = publication._source_reservation_document(old_envelope)
        old_reservation["status"] = "released"
        old_reservation["released_at"] = released_at
        publication.atomic_write_json(reservation_path, old_reservation)
        retired_record = {
            "schema_version": publication.PUBLIC_VERSION,
            "kind": "publication_record",
            "id": old_envelope["envelope_id"],
            "revision": 1,
            "state": "retired",
            "source_work_item": old_envelope["source_work_item"],
            "source_work_item_id": old_envelope["source_work_item_id"],
            "source_work_item_revision": old_envelope["source_work_item_revision"],
            "envelope_digest": publication.json_digest(old_envelope),
            "source_reservation_path": reservation_path.relative_to(self.root).as_posix(),
            "reservation": {
                "status": "released",
                "lease_expires_at": old_envelope["lease_expires_at"],
            },
            "retirement": {
                "request_id": retirement_request,
                "retired_at": released_at,
                "prior_revision": 0,
                "intent_digest": retirement_intent,
            },
            "idempotency": [
                {
                    "request_id": retirement_request,
                    "operation": "retire_publication",
                    "result_id": publication.stable_id(
                        "publication-retirement",
                        old_envelope["envelope_id"],
                        retirement_request,
                        retirement_intent,
                    ),
                }
            ],
        }
        publication.atomic_write_json(
            self.root
            / publication.PUBLICATION_PREFIX
            / f"{old_envelope['envelope_id']}.json",
            retired_record,
        )
        work = {
            "id": old_envelope["source_work_item_id"],
            "revision": old_envelope["source_work_item_revision"],
            "lifecycle": {"state": "release_ready"},
        }

        available = publication.require_publication_lane_available(
            self.root,
            old_envelope["source_work_item"],
            work,
        )
        self.assertEqual(available, old_reservation)

        new_envelope = copy.deepcopy(old_envelope)
        new_envelope["envelope_id"] = "publication-after-retirement"
        publication._claim_source_reservation(self.root, new_envelope, work)
        self.assertEqual(
            publication.load_safe_json(reservation_path, "replacement reservation"),
            publication._source_reservation_document(new_envelope),
        )

    def test_expired_retirement_cannot_make_its_first_local_mutation(self) -> None:
        envelope = _envelope(self.root, active=False)
        record = _retirement_record(envelope)
        request_id = "request-retire-expired-before-write"
        capability_path = publication._capability_path(
            self.root, record["id"], "retire_publication", request_id
        )
        args = self._retirement_args(
            envelope, request_id, capability_path.relative_to(self.root).as_posix()
        )
        capability_path.parent.mkdir(parents=True, exist_ok=True)
        capability_path.write_text("{}\n", encoding="utf-8")
        registry_path = self.root / publication.REGISTRY_RELPATH
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("{}\n", encoding="utf-8")
        expired_at = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        capability = {
            "status": {
                "state": "consumed",
                "consumed_at": _timestamp(expired_at - dt.timedelta(minutes=30)),
            },
            "approval": {"expires_at": _timestamp(expired_at)},
        }
        transaction = {"status": "capability_consumed", "capability_digest": "1" * 64}
        expired = publication.ProtocolError(
            "expired_capability",
            "retirement authority expired before local mutation",
        )
        with (
            mock.patch.object(
                publication,
                "_load_publication",
                return_value=(self.root / "publication.json", record, envelope),
            ),
            mock.patch.object(
                publication,
                "_begin_transaction",
                return_value=(self.root / "transaction.json", transaction, False),
            ),
            mock.patch.object(
                publication,
                "_consume_retirement_capability",
                return_value=("capability.json", "1" * 64, capability),
            ),
            mock.patch.object(
                publication,
                "_retirement_observation",
                return_value=("2" * 64, []),
            ),
            mock.patch.object(
                publication,
                "check_authority",
                side_effect=expired,
            ) as check_authority,
            mock.patch.object(publication, "atomic_write_json") as write,
            mock.patch.object(publication, "_tx_status") as tx_status,
            mock.patch.object(
                publication,
                "exclusive_lock",
                side_effect=lambda _path: contextlib.nullcontext(),
            ),
        ):
            self.assert_protocol_error(
                "expired_capability",
                publication.retire_publication,
                args,
            )
        check_authority.assert_called_once()
        write.assert_not_called()
        tx_status.assert_not_called()

    def test_local_only_retirement_observation_never_touches_remote(self) -> None:
        envelope = _envelope(self.root)
        for state in ("authorized", "committed"):
            record = _retirement_record(envelope, state)
            with self.subTest(state=state):
                with (
                    mock.patch.object(publication, "_observe_remote") as observe,
                    mock.patch.object(publication, "_query_prs") as query_prs,
                ):
                    digest, preserved = publication._retirement_observation(
                        self.root, record, envelope
                    )
                self.assertEqual(
                    digest,
                    publication.json_digest({"mode": "local_only", "outward_effects": []}),
                )
                self.assertEqual(preserved, [])
                observe.assert_not_called()
                query_prs.assert_not_called()

    def test_unknown_push_may_retire_only_when_branch_is_observed_absent(self) -> None:
        envelope = _envelope(self.root)
        record = _retirement_record(envelope, "effect_unknown")
        with (
            mock.patch.object(publication, "_observe_remote", return_value=(BASE_SHA, None)),
            mock.patch.object(publication, "_query_prs") as query_prs,
        ):
            digest, preserved = publication._retirement_observation(
                self.root, record, envelope
            )
        self.assertEqual(
            digest,
            publication.json_digest({"base": BASE_SHA, "head": None, "pull_requests": []}),
        )
        self.assertEqual(preserved, [])
        query_prs.assert_not_called()

        with mock.patch.object(
            publication, "_observe_remote", return_value=(BASE_SHA, COMMIT_SHA)
        ):
            self.assert_protocol_error(
                "unsafe_retirement",
                publication._retirement_observation,
                self.root,
                _retirement_record(envelope, "effect_unknown"),
                envelope,
            )

    def test_pushed_retirement_refuses_missing_changed_branch_or_existing_pr(self) -> None:
        envelope = _envelope(self.root)
        record = _retirement_record(envelope, "pushed")
        for head in (None, OTHER_SHA):
            with self.subTest(head=head):
                with mock.patch.object(
                    publication, "_observe_remote", return_value=(BASE_SHA, head)
                ):
                    self.assert_protocol_error(
                        "unsafe_retirement",
                        publication._retirement_observation,
                        self.root,
                        record,
                        envelope,
                    )

        with (
            mock.patch.object(
                publication, "_observe_remote", return_value=(BASE_SHA, COMMIT_SHA)
            ),
            mock.patch.object(publication, "_query_prs", return_value=[{"number": 17}]),
        ):
            self.assert_protocol_error(
                "unsafe_retirement",
                publication._retirement_observation,
                self.root,
                record,
                envelope,
            )

    def test_retirement_replay_converges_local_journals_without_remote_work(self) -> None:
        envelope = _envelope(self.root, active=False)
        request_id = "request-retire-replay"
        record = _retirement_record(envelope)
        record["state"] = "retired"
        record["revision"] = 1
        record["reservation"]["status"] = "released"
        retired_at = _timestamp(dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1))
        record["retirement"] = {"retired_at": retired_at}
        record["idempotency"] = [
            {
                "request_id": request_id,
                "operation": "retire_publication",
                "result_id": "retirement-result",
            }
        ]
        args = self._retirement_args(envelope, request_id, "unused-capability.json")
        source_reservation = {"status": "active", "released_at": None}
        transaction = _operation_transaction(
            record["id"],
            "retire_publication",
            request_id,
            0,
            "1" * 64,
            "capability_consumed",
        )
        with (
            mock.patch.object(
                publication,
                "_load_publication",
                return_value=(self.root / "publication.json", record, envelope),
            ),
            mock.patch.object(
                publication,
                "_validate_source_reservation",
                return_value=(self.root / "source-reservation.json", source_reservation),
            ),
            mock.patch.object(publication, "load_safe_json", return_value=transaction),
            mock.patch.object(publication, "atomic_write_json") as write,
            mock.patch.object(publication, "_tx_status", return_value={"status": "finalized"}) as tx_status,
            mock.patch.object(publication, "_consume_retirement_capability") as consume,
            mock.patch.object(publication, "_retirement_observation") as observe,
            mock.patch.object(publication, "_run") as run,
            mock.patch.object(publication, "_gh") as gh,
        ):
            result = publication.retire_publication(args)
        self.assertTrue(result["replay"])
        self.assertEqual(source_reservation, {"status": "released", "released_at": retired_at})
        write.assert_called_once()
        tx_status.assert_called_once()
        consume.assert_not_called()
        observe.assert_not_called()
        run.assert_not_called()
        gh.assert_not_called()

    def test_retirement_capability_scope_tampering_is_rejected_before_consumption(self) -> None:
        envelope = _envelope(self.root)
        record = _retirement_record(envelope)
        request_id = "request-retire-tamper"
        intent_digest = "f" * 64
        capability_path, capability = self._fresh_retirement_capability(
            envelope, record, request_id, intent_digest
        )
        capability["scope"]["destination_id"] = "project-local/publication/different"
        publication.atomic_write_json(capability_path, capability)
        registry_path = self.root / publication.REGISTRY_RELPATH
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text("{}\n", encoding="utf-8")
        args = self._retirement_args(
            envelope, request_id, capability_path.relative_to(self.root).as_posix()
        )
        with mock.patch.object(publication, "consume_capability") as consume:
            self.assert_protocol_error(
                "retirement_capability_mismatch",
                publication._consume_retirement_capability,
                self.root,
                record,
                envelope,
                args,
                intent_digest,
            )
        consume.assert_not_called()


class IndexLockRecoveryTests(PublicationTestCase):
    def test_owned_index_lock_can_be_recovered_and_atomically_installed(self) -> None:
        index_path = self.root / "index"
        prepared_path = self.root / "prepared-index"
        index_path.write_bytes(b"original-index")
        prepared_path.write_bytes(b"prepared-index")
        starting_digest = publication._index_digest(index_path)
        lock_path, owner = publication._prepare_real_index_lock(
            index_path, prepared_path, starting_digest, None
        )
        recovered_lock, recovered_owner = publication._prepare_real_index_lock(
            index_path, prepared_path, starting_digest, owner
        )
        self.assertEqual(recovered_lock, lock_path)
        self.assertEqual(recovered_owner, owner)
        publication._finish_real_index_update(index_path, lock_path, owner)
        self.assertEqual(index_path.read_bytes(), b"prepared-index")
        self.assertFalse(lock_path.exists())

    def test_changed_or_unowned_index_lock_is_rejected(self) -> None:
        index_path = self.root / "index"
        prepared_path = self.root / "prepared-index"
        index_path.write_bytes(b"original-index")
        prepared_path.write_bytes(b"prepared-index")
        starting_digest = publication._index_digest(index_path)
        lock_path, owner = publication._prepare_real_index_lock(
            index_path, prepared_path, starting_digest, None
        )
        lock_path.write_bytes(b"tampered-index")
        self.assert_protocol_error(
            "index_lock_conflict",
            publication._prepare_real_index_lock,
            index_path,
            prepared_path,
            starting_digest,
            owner,
        )

        lock_path.unlink()
        lock_path.write_bytes(b"unrelated-index")
        self.assert_protocol_error(
            "index_lock_conflict",
            publication._prepare_real_index_lock,
            index_path,
            prepared_path,
            starting_digest,
            None,
        )


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])
