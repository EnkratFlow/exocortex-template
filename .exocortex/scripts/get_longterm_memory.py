#!/usr/bin/env python3
"""Deterministic project-local long-term evidence (older than 31 days)."""
from datetime import datetime, timedelta
from pathlib import Path

events_dir = Path(__file__).resolve().parent.parent / "events"
cutoff = datetime.now() - timedelta(days=31)
matches = []
for path in sorted(events_dir.glob("*.md"), reverse=True) if events_dir.exists() else []:
    try:
        date = datetime.strptime(path.name[:10], "%Y-%m-%d")
    except ValueError:
        continue
    if date < cutoff:
        matches.append(path)
print("LONG TERM - project-local evidence (31+ days)")
if not matches:
    print("No long-term events found.")
for path in matches[:50]:
    text = path.read_text(encoding="utf-8")
    headings = [line for line in text.splitlines() if line.startswith("#") or line.startswith("- ")]
    print(f"\n--- {path.name} ---\n" + "\n".join(headings[:40]))
