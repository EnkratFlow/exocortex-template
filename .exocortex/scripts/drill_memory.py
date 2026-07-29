#!/usr/bin/env python3
"""Search all project-local events for a topic; no provider or network."""
from pathlib import Path
import sys

if len(sys.argv) < 2 or not " ".join(sys.argv[1:]).strip():
    print("Usage: drill_memory.py TOPIC")
    raise SystemExit(2)
topic = " ".join(sys.argv[1:]).strip().lower()
events_dir = Path(__file__).resolve().parent.parent / "events"
matches = []
for path in sorted(events_dir.glob("*.md"), reverse=True) if events_dir.exists() else []:
    text = path.read_text(encoding="utf-8")
    if topic in text.lower():
        matches.append((path.name, text))
print(f"DRILL - project-local matches for: {topic}")
if not matches:
    print("No matching event found.")
for name, text in matches[:30]:
    lines = [line for line in text.splitlines() if topic in line.lower()]
    print(f"\n--- {name} ---\n" + "\n".join(lines[:30]))
