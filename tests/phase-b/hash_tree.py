#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def inventory(root: Path):
    result = {}
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(name for name in dirs if name != ".git")
        for name in sorted(files):
            path = Path(base) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[rel] = {"kind": "symlink", "target": os.readlink(path)}
            else:
                result[rel] = {"kind": "file", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    document = {"root_name": root.name, "files": inventory(root)}
    raw = json.dumps(document, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(raw, encoding="utf-8")
    else:
        print(raw, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
