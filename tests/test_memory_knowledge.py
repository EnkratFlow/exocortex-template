"""Knowledge map regressions using disposable fictional histories only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import date

SCRIPTS = Path(__file__).resolve().parents[1] / ".exocortex/scripts"
sys.path.insert(0, str(SCRIPTS))
sys.dont_write_bytecode = True
import knowledge_map
import refresh_rollups as memory

DAY = date(2025, 2, 28)

FIRST = """# Narrative save — 2025-02-10 09:00

## What was accomplished
- Built the fictional ledger importer.

## Knowledge

### Entities
- `ledger-importer` (service): reads fictional bank exports
- Northwind (company): fictional supplier in the fixtures

### Relationships
- `ledger-importer` -> writes to -> `fixture-db`

### Concepts
- `dry run first`: every import is previewed before writing
"""

SECOND = """# Narrative save — 2025-02-20 09:00

## Knowledge

### Entities
- `Ledger-Importer` (service): reads fictional bank and card exports
- `fixture-db` (database): disposable test store

### Relationships
- `ledger-importer` → writes to → `fixture-db`

### Concepts
- none

## Conversation patterns
- Not knowledge; must be ignored.
"""


class ParseTests(unittest.TestCase):
    def test_event_without_section_has_no_knowledge(self):
        self.assertIsNone(knowledge_map.parse("# Save\n\n## What's next\n- `a` (b): c\n"))

    def test_sections_are_parsed_and_section_ends_at_next_heading(self):
        items = knowledge_map.parse(SECOND)
        self.assertEqual([e["name"] for e in items["entities"]], ["Ledger-Importer", "fixture-db"])
        self.assertEqual(items["relationships"][0],
                         {"subject": "ledger-importer", "relation": "writes to", "object": "fixture-db"})
        self.assertEqual(items["concepts"], [])
        self.assertEqual(items["unparsed"], [])

    def test_unmatched_lines_are_kept_for_review_not_dropped(self):
        items = knowledge_map.parse("## Knowledge\n### Entities\n- just prose\n### Other\n- stray\n- loose\n")
        self.assertEqual([u["section"] for u in items["unparsed"]], ["entities", "other", "other"])

    def test_knowledge_quoted_in_a_code_fence_is_ignored(self):
        body = "# Handoff\n\n```markdown\n## Knowledge\n### Entities\n- `quoted` (draft): not this event\n```\n"
        self.assertIsNone(knowledge_map.parse(body))

    def test_long_values_are_truncated(self):
        items = knowledge_map.parse("## Knowledge\n### Concepts\n- `long`: " + "x" * 900 + "\n")
        self.assertLessEqual(len(items["concepts"][0]["text"]), knowledge_map.MAX_TEXT)


class BuildTests(unittest.TestCase):
    def events(self):
        return [{"name": "2025-02-20_save.md", "timestamp": "2025-02-20T09:00:00Z", "body": SECOND},
                {"name": "2025-02-10_save.md", "timestamp": "2025-02-10T09:00:00Z", "body": FIRST},
                {"name": "2025-02-15_plain.md", "timestamp": "2025-02-15T09:00:00Z", "body": "# No knowledge"}]

    def test_merge_is_case_insensitive_and_latest_wording_wins(self):
        model = knowledge_map.build(self.events())
        self.assertEqual(model["events_indexed"], 3)
        self.assertEqual(model["events_with_knowledge"], 2)
        importer = next(e for e in model["entities"] if e["name"] == "Ledger-Importer")
        self.assertEqual(importer["notes"][-1]["text"], "reads fictional bank and card exports")
        self.assertEqual([s["event"] for s in importer["sources"]], ["2025-02-10_save.md", "2025-02-20_save.md"])
        self.assertEqual(len(model["relationships"]), 1)
        self.assertEqual(len(model["relationships"][0]["sources"]), 2)

    def test_repeated_older_wording_moves_to_latest(self):
        again = "## Knowledge\n### Entities\n- `ledger-importer` (service): reads fictional bank exports\n"
        events = self.events() + [{"name": "2025-02-25_save.md", "timestamp": "2025-02-25T09:00:00Z", "body": again}]
        importer = next(e for e in knowledge_map.build(events)["entities"] if e["name"] == "ledger-importer")
        self.assertEqual(importer["notes"][-1]["text"], "reads fictional bank exports")
        self.assertEqual(len(importer["notes"]), 2)

    def test_output_is_deterministic_and_jsonl_is_valid(self):
        first = knowledge_map.build(self.events())
        second = knowledge_map.build(list(reversed(self.events())))
        self.assertEqual(knowledge_map.render_markdown(first), knowledge_map.render_markdown(second))
        rows = [json.loads(line) for line in knowledge_map.render_jsonl(first).splitlines()]
        self.assertEqual(rows[0]["type"], "header")
        self.assertEqual({r["type"] for r in rows[1:]}, {"entity", "relationship", "concept"})

    def test_markdown_neutralizes_markers_and_html(self):
        body = ("## Knowledge\n### Concepts\n- `trap`: <!-- hidden --> " + knowledge_map.MARKER + " "
                + memory.START + "\n")
        text = knowledge_map.render_markdown(knowledge_map.build([{"name": "x.md", "timestamp": None, "body": body}]))
        self.assertEqual(text.count(knowledge_map.MARKER), 1)
        self.assertNotIn("<!-- hidden", text)
        self.assertNotIn(memory.START, text)


class RefreshIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="knowledge fixture ")
        self.root = Path(self.tmp.name).resolve()
        (self.root / ".exocortex/events").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, name, body):
        (self.root / ".exocortex/events" / name).write_text(body)

    def test_no_files_until_a_save_carries_knowledge(self):
        self.event("2025-02-01_save.md", "# Plain save")
        self.assertEqual(memory.apply(self.root, DAY)["status"], "fresh")
        self.assertFalse((self.root / ".exocortex/knowledge").exists())

    def test_apply_writes_map_and_check_tracks_event_changes(self):
        self.event("2025-02-10_save.md", FIRST)
        self.assertEqual(memory.apply(self.root, DAY)["status"], "fresh")
        md = (self.root / memory.KNOWLEDGE_MD).read_text()
        self.assertTrue(md.startswith(knowledge_map.MARKER))
        self.assertIn("**ledger-importer** (service)", md.replace("\\-", "-"))
        self.assertIn("(../events/2025-02-10_save.md)", md)
        before = (self.root / memory.KNOWLEDGE_JSONL).read_bytes()
        self.assertEqual(memory.apply(self.root, DAY)["status"], "fresh")
        self.assertEqual((self.root / memory.KNOWLEDGE_JSONL).read_bytes(), before)
        self.event("2025-02-20_save.md", SECOND)
        result = memory.check(self.root, DAY)
        self.assertEqual(result["status"], "stale")
        self.assertIn("knowledge_view_changed", result["reasons"])
        memory.apply(self.root, DAY)
        self.assertIn("fixture-db", (self.root / memory.KNOWLEDGE_MD).read_text().replace("\\-", "-"))

    def test_removed_knowledge_regenerates_an_empty_map_instead_of_leaving_stale_facts(self):
        self.event("2025-02-10_save.md", FIRST)
        memory.apply(self.root, DAY)
        (self.root / ".exocortex/events/2025-02-10_save.md").write_text("# Corrected save without knowledge")
        memory.apply(self.root, DAY)
        self.assertIn("## Entities (0)", (self.root / memory.KNOWLEDGE_MD).read_text())
        self.assertEqual(memory.check(self.root, DAY)["status"], "fresh")

    def test_handwritten_map_is_refused_and_nothing_is_replaced(self):
        self.event("2025-02-10_save.md", FIRST)
        path = self.root / memory.KNOWLEDGE_MD
        path.parent.mkdir(parents=True)
        path.write_text("# My own notes\n")
        with self.assertRaises(memory.MemoryError):
            memory.apply(self.root, DAY)
        self.assertEqual(path.read_text(), "# My own notes\n")
        self.assertFalse((self.root / memory.CONTEXT).exists())
        self.assertFalse((self.root / memory.KNOWLEDGE_JSONL).exists())


if __name__ == "__main__":
    unittest.main()
