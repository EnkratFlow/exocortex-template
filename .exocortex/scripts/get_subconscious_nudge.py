#!/usr/bin/env python3
"""Return one deterministic local pattern reminder."""
from pathlib import Path

events_dir = Path(__file__).resolve().parent.parent / "events"
for path in sorted(events_dir.glob("*.md"), reverse=True) if events_dir.exists() else []:
    for line in path.read_text(encoding="utf-8").splitlines():
        if any(word in line.lower() for word in ("friction", "recurring", "context gap")):
            print(line.strip())
            raise SystemExit(0)
print("No local pattern nudge available.")
