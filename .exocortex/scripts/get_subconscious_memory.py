#!/usr/bin/env python3
"""Extract project-local retrospective pattern evidence without providers."""
from pathlib import Path

events_dir = Path(__file__).resolve().parent.parent / "events"
needles = ("Recurring", "Friction", "Candidate skill", "Candidate PROJECT_MEMORY", "Context gap")
hits = []
for path in sorted(events_dir.glob("*.md"), reverse=True) if events_dir.exists() else []:
    for line in path.read_text(encoding="utf-8").splitlines():
        if any(value.lower() in line.lower() for value in needles):
            hits.append((path.name, line))
print("SUBCONSCIOUS - project-local pattern evidence")
if not hits:
    print("No explicit pattern evidence found; no external source was queried.")
for name, line in hits[:100]:
    print(f"{name}: {line}")
