#!/usr/bin/env python3
"""Write .exocortex/template-file-history.txt from this repository's history.

Each line is "<installed path> <sha256>" for one version of a file the
installer copies into projects, taken from every first-parent commit of HEAD
and every v* tag. The installer treats a project file whose bytes match a line
for its path as unmodified template content, so updates work from a fresh
clone without a manifest and files the template stops shipping can be retired.

Only public template code-plane paths are recorded. Project data paths are
excluded even where they once appeared in history. Run before each release:

    python3 scripts/build-template-history.py
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ".exocortex/template-file-history.txt"
INSTALLED = (".exocortex", ".agents", ".cursor", ".claude/skills", ".github/skills",
             ".github/copilot-instructions.md", "AI_START_HERE.md", "AGENTS.md",
             "CLAUDE.md", ".rules")
DATA_FILES = {
    "SESSION_CONTEXT.md", "SESSION_CONTEXT.md.backup", "SESSION_CONTEXT.local.md",
    "TODO.md", "LESSONS.md", "PROJECT_MEMORY.md", "OPEN_DECISIONS.md",
    "subconscious_patterns.md", ".project-name", ".install-manifest", ".version",
    ".hub_enabled", ".hub_disabled", "control/ACTIVE_WORK.md",
    "control/BRANCH_POLICY.md", "control/REPO_STATE.md",
    "control/EXECUTOR_REGISTRY.json", "control/EXTERNAL_SYNC_POLICY.json",
    "control/INTERRUPTS.md", "control/BACKLOG.md", "control/ROADMAP.md",
    "control/ARCH_OVERVIEW.md", "control/REPO_ORGANIZATION_REPORT.md",
}
DATA_DIRS = ("events/", "archive/", "hub/", "local/", "planning/", "work-items/")


def git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True).stdout


def recorded(path: str) -> bool:
    if path == OUTPUT or path.startswith("/") or ".." in path.split("/"):
        return False
    if path.startswith(".exocortex/"):
        rel = path[len(".exocortex/"):]
        name = rel.rsplit("/", 1)[-1]
        if (rel in DATA_FILES or rel.startswith(DATA_DIRS)
                or rel.startswith("SESSION_CONTEXT_BACKUP_")
                or (name.startswith(".env") and rel != ".env.example")
                or name == ".envrc"):
            return False
    return True


def main() -> int:
    commits = git("rev-list", "--first-parent", "HEAD").decode().split()
    commits += git("tag", "--list", "v*").decode().split()
    blobs: dict[str, set[str]] = {}
    for commit in commits:
        listing = git("ls-tree", "-r", "-z", commit, "--", *INSTALLED)
        for entry in filter(None, listing.split(b"\0")):
            meta, path = entry.split(b"\t", 1)
            mode, kind, oid = meta.decode().split()
            if kind == "blob" and mode in ("100644", "100755"):
                blobs.setdefault(oid, set()).add(path.decode("utf-8"))
    lines = set()
    for oid, paths in blobs.items():
        digest = hashlib.sha256(git("cat-file", "blob", oid)).hexdigest()
        lines.update(f"{path} {digest}" for path in paths if recorded(path))
    for line in lines:
        if " " in line.rsplit(" ", 1)[0]:
            raise SystemExit(f"path with whitespace cannot be recorded: {line}")
    body = "".join(f"{line}\n" for line in sorted(lines))
    (ROOT / OUTPUT).write_bytes(body.encode("utf-8"))
    print(f"wrote {OUTPUT}: {len(lines)} fingerprints from {len(commits)} revisions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
