#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--allow", action="append", default=[])
    args = parser.parse_args()
    left = json.loads(args.before.read_text(encoding="utf-8"))["files"]
    right = json.loads(args.after.read_text(encoding="utf-8"))["files"]
    changed = sorted(key for key in set(left) | set(right) if left.get(key) != right.get(key))
    unexpected = [path for path in changed if path not in set(args.allow)]
    print(json.dumps({"changed": changed, "unexpected": unexpected}, sort_keys=True))
    return 1 if unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
