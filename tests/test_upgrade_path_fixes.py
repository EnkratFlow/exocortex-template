#!/usr/bin/env python3
"""Regression tests for the v3.3.12 upgrade-path fixes found during a
multi-project Windows rollout:

- public template files with credential-shaped names can be updated through a
  local-delivery lane, while every other credential-shaped path stays refused;
- installs that predate manifest-tracked .exocortex/.version get a fresh label;
- native Windows rejects over-long target paths before any backup is written.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".exocortex/scripts"))
import orchestrate_work_item as owi  # noqa: E402

BASH = os.environ.get("EXOCORTEX_TEST_BASH") or shutil.which("bash") or "bash"


def envelope(allowed_paths: list[str]) -> dict:
    actor = {"surface_id": "fixture-surface", "executor_id": "fixture-writer", "adapter_version": "fixture-v1"}
    return {
        "schema_version": "public-v2", "kind": "local_delivery_envelope",
        "envelope_id": "fixture-update", "work_item_id": "fixture-update",
        "title": "Fixture update", "type": "maintenance",
        "project_root": str(Path(tempfile.gettempdir()).resolve()),
        "branch": "main", "base_sha": "a" * 40, "allowed_paths": allowed_paths,
        "outcome": "Fictional update.", "risk": "low", "rollback": "Restore fixture.",
        "verification": ["Fixture verified."], "exclusions": ["No external systems."],
        "writer": actor,
        "reviewer": {"surface_id": "fixture-review", "executor_id": "fixture-reviewer", "adapter_version": "fixture-v1"},
        "approval": {"approved_by": "fixture-owner", "accepted_at": "2026-01-01T00:00:00Z",
                     "expires_at": "2099-01-01T00:00:00Z", "summary": "Fictional approval."},
        "lease_expires_at": "2099-01-01T00:00:00Z",
    }


class CredentialShapedTemplateFileTests(unittest.TestCase):
    def test_public_template_files_are_allowed_in_a_lane(self) -> None:
        result = owi.validate_local_delivery_envelope(
            envelope([".exocortex/.env.example", ".exocortex/key-registry.json", "README.md"]),
            require_active=False,
        )
        self.assertIn(".exocortex/key-registry.json", result["allowed_paths"])

    def test_every_other_credential_shaped_path_is_still_refused(self) -> None:
        for path in (
            ".exocortex/.env.local", ".env.example", "app/.env.example",
            "config/key-registry.json", ".exocortex/nested/key-registry.json",
            "config/secrets.json", "keys/id_ed25519",
        ):
            with self.subTest(path=path):
                with self.assertRaises(owi.ProtocolError) as caught:
                    owi.validate_local_delivery_envelope(envelope([path]), require_active=False)
                self.assertEqual(caught.exception.code, "sensitive_allowed_path")


def candidate_digest() -> str:
    return hashlib.sha256((ROOT / "SHA256SUMS").read_bytes()).hexdigest()


def install(target: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, EXOCORTEX_LOCAL_SOURCE=str(ROOT), EXOCORTEX_CANDIDATE_DIGEST=candidate_digest())
    return subprocess.run([BASH, str(ROOT / "install.sh"), "fixture-project"], cwd=target, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


class LegacyVersionLabelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="exo-version-")
        self.target = Path(self.temp.name) / "project"
        self.target.mkdir()
        first = install(self.target)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.version = self.target / ".exocortex/.version"
        self.manifest = self.target / ".exocortex/.install-manifest"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def simulate_legacy_install(self, label: bytes) -> None:
        self.version.write_bytes(label)
        lines = self.manifest.read_bytes().decode("utf-8").splitlines(keepends=True)
        self.manifest.write_bytes("".join(l for l in lines if not l.startswith(".exocortex/.version ")).encode())

    def test_untracked_semantic_version_label_is_refreshed(self) -> None:
        self.simulate_legacy_install(b"3.1.9\n")
        again = install(self.target)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(self.version.read_bytes(), (ROOT / "VERSION").read_bytes())
        self.assertIn(".exocortex/.version ", self.manifest.read_text(encoding="utf-8"))

    def test_untracked_owner_content_is_still_preserved(self) -> None:
        self.simulate_legacy_install(b"pinned by owner: keep 3.1.9 for the audit\n")
        again = install(self.target)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(self.version.read_bytes(), b"pinned by owner: keep 3.1.9 for the audit\n")
        self.assertIn("preserve user-modified or unknown file: .exocortex/.version", again.stdout)


def bash_path(path: Path) -> str:
    """C:\\a\\b -> /c/a/b, the absolute form Git Bash scripts require."""
    value = str(path.resolve()).replace("\\", "/")
    return f"/{value[0].lower()}{value[2:]}" if len(value) > 1 and value[1] == ":" else value


@unittest.skipUnless(os.name == "nt", "native Windows path-length preflight")
class WindowsTargetPathTests(unittest.TestCase):
    def test_overlong_target_is_rejected_before_backup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="exo-path-") as temporary:
            base = Path(temporary).resolve()
            target = base / ("p" * max(1, 150 - len(str(base)) - 1))
            target.mkdir()
            installed = install(target)  # install paths fit; protocol state would not
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            backups = base / "backups"
            backups.mkdir()
            result = subprocess.run(
                [BASH, "--noprofile", "--norc", bash_path(ROOT / "scripts/safe-update.sh"),
                 "--template", bash_path(ROOT), "--candidate-digest", candidate_digest(),
                 "--backup-dir", bash_path(backups), "--dry-run"],
                cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            output = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0, output)
            self.assertIn("EXOCORTEX_TARGET_PATH_TOO_LONG", output)
            self.assertEqual(list(backups.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
