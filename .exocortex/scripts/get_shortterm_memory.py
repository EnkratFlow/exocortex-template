#!/usr/bin/env python3
"""Deterministic project-local short-term evidence (7-31 days)."""
from datetime import datetime, timedelta
from pathlib import Path

events_dir = Path(__file__).resolve().parent.parent / "events"
now = datetime.now()
matches = []
for path in sorted(events_dir.glob("*.md"), reverse=True) if events_dir.exists() else []:
    try:
        age = now - datetime.strptime(path.name[:10], "%Y-%m-%d")
    except ValueError:
        continue
    if timedelta(days=7) <= age <= timedelta(days=31):
        matches.append(path)
print("SHORT TERM - project-local evidence (7-31 days)")
if not matches:
    print("No short-term events found.")
for path in matches[:30]:
    print(f"\n--- {path.name} ---\n{path.read_text(encoding='utf-8')}")
