#!/usr/bin/env python3
"""Deterministic project-local RIGHT NOW evidence (0-7 days)."""
from datetime import datetime, timedelta
from pathlib import Path

events_dir = Path(__file__).resolve().parent.parent / "events"
cutoff = datetime.now() - timedelta(days=7)
matches = []
for path in sorted(events_dir.glob("*.md"), reverse=True) if events_dir.exists() else []:
    try:
        date = datetime.strptime(path.name[:10], "%Y-%m-%d")
    except ValueError:
        continue
    if date >= cutoff:
        matches.append(path)
print("RIGHT NOW - project-local evidence (0-7 days)")
if not matches:
    print("No recent events found.")
for path in matches[:20]:
    print(f"\n--- {path.name} ---\n{path.read_text(encoding='utf-8')}")
