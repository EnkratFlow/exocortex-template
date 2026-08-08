#!/usr/bin/env python3
"""Search all project-local events for a literal topic; no provider or network."""
from pathlib import Path
import sys

arguments = sys.argv[1:]
if arguments == ["--topic-stdin"]:
    topic_input = sys.stdin.read()
elif arguments and arguments[0] != "--topic-stdin":
    topic_input = " ".join(arguments)
else:
    topic_input = ""

if not topic_input.strip():
    print("Usage: drill_memory.py --topic-stdin | TOPIC")
    raise SystemExit(2)
topic = topic_input.strip().lower()
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
