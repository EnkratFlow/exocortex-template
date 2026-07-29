#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


PROTECTED = [
    "SESSION_CONTEXT.md", "SESSION_CONTEXT.local.md", "TODO.md", "LESSONS.md",
    "PROJECT_MEMORY.md", "OPEN_DECISIONS.md", "subconscious_patterns.md", ".env",
    "events/canary.md", "archive/canary.md", "hub/canary.md", "local/canary.md",
    "planning/canary.md", "work-items/canary.md", "control/ACTIVE_WORK.md",
    "control/BRANCH_POLICY.md", "control/REPO_STATE.md", "control/INTERRUPTS.md",
    "control/BACKLOG.md", "control/ROADMAP.md", ".hub_enabled", ".hub_disabled",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    if target.exists():
        raise SystemExit("target must not already exist")
    target.mkdir(parents=True)
    for rel in PROTECTED:
        path = target / ".exocortex" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"FICTIONAL_CANARY:{rel}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
