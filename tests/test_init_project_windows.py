"""Initializer smoke checks, run on Windows in CI and locally on Unix."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "init-project.sh"


class InitProjectWindowsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="exo-init-windows-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / ".exocortex").mkdir()
        shutil.copyfile(SOURCE, self.root / "init-project.sh")

    def initialize(self, fault=None):
        environment = dict(os.environ)
        if fault is not None:
            environment.update(
                EXOCORTEX_TEST_MODE="1", EXOCORTEX_TEST_INIT_FAULT=fault
            )
        return subprocess.run(
            ["bash", "init-project.sh", "fixture-project"],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_creates_once_and_preserves_handwritten_file(self):
        handwritten = self.root / ".exocortex" / "manual.md"
        handwritten.write_bytes(b"Handwritten project notes.\n")
        original = handwritten.stat()

        first = self.initialize()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        project_name = self.root / ".exocortex" / ".project-name"
        self.assertEqual(project_name.read_bytes(), b"fixture-project\n")
        created = project_name.stat()

        second = self.initialize()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(project_name.read_bytes(), b"fixture-project\n")
        self.assertEqual(project_name.stat().st_mtime_ns, created.st_mtime_ns)
        self.assertEqual(handwritten.read_bytes(), b"Handwritten project notes.\n")
        self.assertEqual(handwritten.stat().st_mtime_ns, original.st_mtime_ns)

    def test_faults_leave_no_partial_project_name(self):
        for fault in ("write", "file-fsync", "directory-fsync"):
            with self.subTest(fault=fault):
                result = self.initialize(fault)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(
                    "injected test-only project-name " + fault + " failure",
                    result.stdout + result.stderr,
                )
                self.assertEqual(list((self.root / ".exocortex").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
