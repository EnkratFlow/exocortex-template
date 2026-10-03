"""Focused regression tests using disposable fictional histories only."""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / ".exocortex/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True
import refresh_rollups as memory
import curate_memory as curator
import record_event

DAY = date(2025, 2, 28)


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="memory fixture ")
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".exocortex/events").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, name, body):
        path = self.root / ".exocortex/events" / name
        path.write_text(body)
        return path

    def test_onboard_detects_old_event_edit_under_new_managed_context(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        source = self.event('2025-02-01_save.md', '# Earlier fact')
        memory.apply(self.root)
        command = [sys.executable, str(SCRIPTS / 'onboard_evidence.py'), str(self.root)]
        fresh = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
        self.assertEqual(fresh['context']['rollup_coverage']['status'], 'fresh')
        source.write_text('# Earlier fact corrected')
        stale = json.loads(subprocess.run(command, capture_output=True, text=True, check=True).stdout)
        self.assertEqual(stale['context']['rollup_coverage']['status'], 'stale')
        self.assertIn('rollup_coverage_stale', [d['code'] for d in stale['discrepancies']])

    def test_corrupt_receipt_is_refused_and_apply_repairs_it(self):
        memory.apply(self.root, DAY)
        path = self.root / memory.RECEIPT
        path.write_text(json.dumps({'schema': 1, 'sources': {'old.md': None}}))
        with self.assertRaises(memory.MemoryError): memory.check(self.root, DAY)
        self.assertEqual(memory.apply(self.root, DAY)['status'], 'fresh')

    def test_generated_size_limit_refuses_before_replacing_handwritten_context(self):
        path = self.root / memory.CONTEXT
        path.write_text('# Handwritten note\n')
        before = path.read_bytes()
        with patch.object(memory, 'MAX_FILE', 400):
            with self.assertRaisesRegex(memory.MemoryError, 'existing context preserved'):
                memory.apply(self.root, DAY)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / memory.RECEIPT).exists())

    def test_mixed_formats_source_dates_and_historical_actions(self):
        self.event("2025-02-28_10-00-00_narrative.md", "# Save\n## What was accomplished\nFixed it.\n**What’s next**\nDeploy.\n")
        self.event("2025-02-27_10-00-00_short.md", "# Handoff\n## Outcome\nRolled back.\n## Next verification\nCheck errors.")
        self.event("2025-02-15_10-00-00_bold.md", "# Save\n**Decisions made**\nUse plain words.")
        self.event("2024-01-01_00-00-00_old.md", "# Old event")
        result = memory.apply(self.root, DAY)
        text = (self.root / memory.CONTEXT).read_text()
        self.assertEqual(result["status"], "fresh")
        self.assertIn("Last 7 days (2 events)", text)
        self.assertIn("Previous 7–30 days (1 events)", text)
        self.assertNotIn("Old event", text)
        self.assertIn("historical proposals", text)
        self.assertEqual(result["event_count"], 4)
        self.assertEqual(memory.normalized_heading("**What’s next**"), "what's next")

    def test_metadata_beats_filename_and_mtime(self):
        self.event("2025-02-28_12-00-00_copy.md", "<!-- Event Metadata -->\ntimestamp: 2020-01-01T00:00:00Z\n---\n# Old source")
        memory.apply(self.root, DAY)
        text = (self.root / memory.CONTEXT).read_text()
        self.assertIn("Last 7 days (0 events)", text)
        self.assertIn("2020-01-01", text)

    def test_idle_empty_unknown_future_and_example(self):
        self.event(memory.EXAMPLE, "# Fictional shipped sample")
        self.assertEqual(memory.apply(self.root, DAY)["event_count"], 0)
        self.event("undated.md", "# Undated evidence")
        self.event("2099-01-01_future.md", "# Future")
        memory.apply(self.root, DAY)
        text = (self.root / memory.CONTEXT).read_text()
        self.assertIn("Undated or future-dated events (2)", text)
        self.assertIn("No dated event at or before", text)

    def test_preserves_manual_context_and_durable_files_and_backup(self):
        initial = "# My handwritten focus\nKeep this exact text.\n"
        (self.root / memory.CONTEXT).write_text(initial)
        durable = self.root / ".exocortex/LESSONS.md"
        durable.write_text("# My lessons\nNever erase this.\n")
        memory.apply(self.root, DAY)
        self.assertTrue((self.root / memory.CONTEXT).read_text().endswith(initial))
        self.assertEqual((self.root / (memory.CONTEXT + ".backup")).read_text(), initial)
        self.assertEqual(durable.read_text(), "# My lessons\nNever erase this.\n")
        (self.root / memory.CONTEXT).write_text((self.root / memory.CONTEXT).read_text() + "Another manual note.\n")
        memory.apply(self.root, DAY)
        self.assertTrue((self.root / memory.CONTEXT).read_text().endswith("Another manual note.\n"))

    def test_idempotent_same_day_does_not_touch_bytes_or_mtimes(self):
        self.event("2025-02-28_save.md", "# Save\nA fact.")
        memory.apply(self.root, DAY)
        paths = [self.root / memory.CONTEXT, self.root / memory.RECEIPT]
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
        memory.apply(self.root, DAY)
        self.assertEqual(before, [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths])

    def test_modified_old_events_deleted_and_late_arrivals_are_stale(self):
        old = self.event("2024-01-01_old.md", "# Old")
        self.event("2025-02-28_new.md", "# New")
        memory.apply(self.root, DAY)
        old.write_text("# Corrected old evidence")
        self.assertEqual(memory.check(self.root, DAY)["changed_events"], [old.name])
        memory.apply(self.root, DAY)
        old.unlink()
        self.assertEqual(memory.check(self.root, DAY)["removed_events"], [old.name])
        memory.apply(self.root, DAY)
        self.event("2023-01-01_late.md", "# Late historical save")
        self.assertEqual(memory.check(self.root, DAY)["status"], "stale")

    def test_readonly_missing_and_changed_day(self):
        self.assertEqual(memory.check(self.root, DAY)["status"], "stale")
        self.assertFalse((self.root / ".exocortex/local").exists())
        memory.apply(self.root, DAY)
        self.assertIn("window_date_changed", memory.check(self.root, date(2025, 3, 1))["reasons"])

    def test_editing_generated_section_is_detected(self):
        memory.apply(self.root, DAY)
        p = self.root / memory.CONTEXT
        p.write_text(p.read_text().replace("No dated event", "Fake current state"))
        self.assertIn("generated_view_changed", memory.check(self.root, DAY)["reasons"])

    def test_symlink_source_destination_and_state_refused(self):
        external = self.root / "external.md"
        external.write_text("Private fixture. Never traverse.")
        for rel in (".exocortex/events/linked.md", memory.CONTEXT, memory.RECEIPT):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(external)
            with self.assertRaises(memory.MemoryError):
                memory.apply(self.root, DAY)
            path.unlink()
        self.assertEqual(external.read_text(), "Private fixture. Never traverse.")

    def test_ambiguous_markers_preserved(self):
        value = memory.START + "\n" + memory.START + "\n" + memory.END
        (self.root / memory.CONTEXT).write_text(value)
        with self.assertRaises(memory.MemoryError):
            memory.apply(self.root, DAY)
        self.assertEqual((self.root / memory.CONTEXT).read_text(), value)

    def test_utf16_sources_and_bounded_excerpt(self):
        p = self.event("2025-02-28_unicode.md", "")
        p.write_bytes(("# Café\n" + "Long text.\n" * 300).encode("utf-16"))
        memory.apply(self.root, DAY)
        text = (self.root / memory.CONTEXT).read_text()
        self.assertIn("Café", text)
        self.assertIn("Excerpt shortened", text)

    def test_concurrent_events_and_refreshes_cover_both(self):
        with patch.object(record_event, "git", return_value="fixture"):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                paths = list(pool.map(lambda n: record_event.record(self.root, f"# Save {n}"), range(2)))
        self.assertEqual(len(set(paths)), 2)
        self.assertTrue(all("## Git State" in p.read_text() for p in paths))
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: memory.apply(self.root), range(2)))
        self.assertEqual(memory.check(self.root)["event_count"], 2)
        self.assertEqual(memory.check(self.root)["status"], "fresh")

    def test_saved_event_survives_refresh_failure(self):
        dest = self.root / ".exocortex/scripts"
        dest.mkdir()
        for name in ("create_event.sh", "record_event.py", "refresh_rollups.py", "run_exocortex.sh", "command_runtime.py"):
            shutil.copy(SCRIPTS / name, dest / name)
        (self.root / memory.CONTEXT).write_text(memory.START)  # malformed managed block
        result = subprocess.run(["bash", str(dest / "create_event.sh")], input="# Handoff\nSaved once.",
                                text=True, capture_output=True, cwd=self.root)
        self.assertEqual(result.returncode, 3)
        self.assertIn("EVENT_SAVED_REFRESH_FAILED", result.stderr)
        self.assertTrue(Path(result.stdout.strip().splitlines()[-1]).is_file())
        self.assertEqual(len(list((self.root / ".exocortex/events").glob("*.md"))), 1)
        # Repair only the malformed context, then retry refresh, never save.
        (self.root / memory.CONTEXT).write_text('# Preserved handwritten focus\n')
        memory.apply(self.root)
        self.assertEqual(memory.check(self.root)['status'], 'fresh')
        self.assertEqual(len(list((self.root / '.exocortex/events').glob('*.md'))), 1)

    def test_existing_backup_all_durable_files_and_manual_surroundings_preserved(self):
        prefix, suffix = '# Handwritten priority\n', '\n## Handwritten detail\nKeep café.\n'
        (self.root / memory.CONTEXT).write_text(prefix + memory.render([], DAY) + suffix)
        backup = self.root / (memory.CONTEXT + '.backup')
        backup.write_bytes(b'An older backup must remain unchanged.\r\n')
        paths = [backup]
        for target in curator.TARGETS:
            path = self.root / '.exocortex' / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'# Handwritten\r\nExact original bytes.\r\n')
            paths.append(path)
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
        self.event('2025-02-28_new.md', '# New event')
        memory.apply(self.root, DAY)
        text = (self.root / memory.CONTEXT).read_text()
        self.assertTrue(text.startswith(prefix)); self.assertTrue(text.endswith(suffix))
        self.assertEqual(before, [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths])

    def test_interrupted_receipt_write_repaired_without_duplicate_event(self):
        (self.root / memory.CONTEXT).write_text('# Handwritten note\n')
        with patch.object(record_event, 'git', return_value='fixture'):
            event = record_event.record(self.root, '# One saved event')
        original = memory.atomic_write
        def fail_receipt(path, data):
            if path == self.root / memory.RECEIPT:
                raise OSError('simulated receipt disk failure')
            original(path, data)
        with patch.object(memory, 'atomic_write', fail_receipt):
            with self.assertRaises(OSError): memory.apply(self.root)
        self.assertTrue(event.exists())
        self.assertEqual(memory.check(self.root)['status'], 'stale')
        self.assertTrue((self.root / memory.CONTEXT).read_text().endswith('# Handwritten note\n'))
        self.assertEqual(memory.apply(self.root)['status'], 'fresh')
        self.assertEqual(len(list((self.root / '.exocortex/events').glob('*.md'))), 1)

    def test_proposal_preview_sources_and_drift(self):
        name = "2025-02-28_task.md"
        self.event(name, "# Task\nTask export is complete.")
        evidence = curator.packet(self.root)
        proposal = {"schema": 1, "since": None, "packet_sha256": evidence["packet_sha256"],
                    "items": [{"key": "export", "target": "TODO.md", "status": "closed",
                               "evidence": [{"event": name, "quote": "Task export is complete."}]}]}
        self.assertIn("Review required", curator.preview(self.root, proposal))
        self.assertFalse((self.root / ".exocortex/TODO.md").exists())
        (self.root / ".exocortex/TODO.md").write_text("A new manual note")
        with self.assertRaisesRegex(memory.MemoryError, "changed"):
            curator.preview(self.root, proposal)

    def test_proposal_forged_quotes_and_targets(self):
        events = {"e1": {"body": "Still an open task."}}
        item = {"key": "task", "target": "TODO.md", "status": "closed", "evidence": [{"event": "e1", "quote": "Task complete."}]}
        with self.assertRaises(memory.MemoryError):
            curator.validate_items([item], events)
        item["target"] = "../AI_START_HERE.md"
        with self.assertRaises(memory.MemoryError):
            curator.validate_items([item], events)


if __name__ == "__main__":
    unittest.main()
