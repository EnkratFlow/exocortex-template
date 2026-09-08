#!/usr/bin/env python3
"""Focused regression tests for the /onboard completion contract.

Run as: python3 tests/test_onboard_contract.py <template-root>

Every fixture is a fictional repository built in a temporary directory; nothing
here reads or writes a real project, contacts a network, or depends on a
particular provider. The tests cover the evidence collector's findings for the
failure classes the contract must catch, prove that collecting evidence leaves
the repository byte-identical and touches no network, and pin the command JSON
to its conditional-completion wording.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

TEMPLATE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
COLLECTOR = TEMPLATE / ".exocortex" / "scripts" / "onboard_evidence.py"
COMMAND = TEMPLATE / ".exocortex" / "commands" / "onboard.json"
FAILURES: list[str] = []


def check(condition: bool, message: str) -> None:
    if condition:
        print(f"  ok   {message}")
    else:
        print(f"  FAIL {message}")
        FAILURES.append(message)


def git(root: Path, *args: str, env: dict | None = None) -> str:
    base = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.invalid",
                GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.invalid",
                GIT_TERMINAL_PROMPT="0")
    if env:
        base.update(env)
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env=base, check=True)
    return proc.stdout.strip()


def commit_all(root: Path, message: str, when: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message, env={"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when})
    return git(root, "rev-parse", "HEAD")


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def event(root: Path, stamp: str, body: str, shas: list[str] | None = None) -> str:
    """A fictional narrative event in the real file shape: metadata header, then a git log block."""
    name = f"{stamp.replace(':', '-').replace('T', '_').rstrip('Z')}_fixture-agent.md"
    log_block = "\n".join(f"{s[:7]} recorded commit" for s in (shas or []))
    write(root, f".exocortex/events/{name}", f"<!-- Event Metadata -->\ntimestamp: {stamp}\nmachine: fixture\neditor: fixture\nproject: fixture\nbranch: main\n\n---\n\n# Narrative save\n\n{body}\n\n## Code state\n\n**Branch:** main\n\n**Recent commits:**\n{log_block}\n")
    return name


MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def context(root: Path, covered_stamps: list[str]) -> None:
    """A generated context in the exact shape generate_context.sh writes: human-readable event lines, no ISO stamps."""
    newest = max(covered_stamps)
    y, mo, d = int(newest[0:4]), int(newest[5:7]), int(newest[8:10])
    lines = ["# SESSION_CONTEXT – fixture", "", f"**Last Updated:** {MONTHS[mo - 1]} {d:02d}, {y}",
             f"**Generated from events:** Last 7 days ({len(covered_stamps)} events)", "", "---", "", "## 🟢 RIGHT NOW", ""]
    for s in sorted(covered_stamps, reverse=True):
        mo, d, h, mi = int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16])
        ampm = "PM" if h >= 12 else "AM"
        lines.append(f"**Event:** {MONTHS[mo - 1]} {d:02d} at {(h % 12) or 12:02d}:{mi:02d} {ampm} • fixture • fixture • Branch: `main`\n\ncovered\n\n---\n")
    write(root, ".exocortex/SESSION_CONTEXT.md", "\n".join(lines))


def new_repo(prefix: str) -> Path:
    root = Path(tempfile.mkdtemp(prefix=prefix))
    git(root, "init", "-q", "-b", "main")
    write(root, ".exocortex/.version", "9.9.9\n")
    write(root, "src/app.py", "def run():\n    return 'v1'\n")
    write(root, "README.md", "# fixture\n")
    commit_all(root, "initial", "2020-01-01T10:00:00Z")
    return root


def collect(root: Path) -> dict:
    proc = subprocess.run([sys.executable, str(COLLECTOR), str(root)], capture_output=True, text=True, check=False)
    check(proc.returncode == 0, f"collector exits 0 ({root.name})")
    return json.loads(proc.stdout)


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            p = Path(base) / name
            rel = p.relative_to(root).as_posix()
            try:
                data = p.read_bytes()
            except OSError:
                data = b""
            h.update(rel.encode() + b"\0" + data + b"\0" + str(p.stat().st_mtime_ns).encode())
    return h.hexdigest()


def codes(result: dict) -> set[str]:
    return {d["code"] for d in result["discrepancies"]}


def case_stale_context_newer_event_newer_commits() -> None:
    print("case: stale generated context, a newer event, and still-newer substantive commits")
    root = new_repo("exo-onboard-stale-")
    base = git(root, "rev-parse", "HEAD")
    context(root, ["2020-01-02T09:00:00Z"])
    event(root, "2020-01-02T09:00:00Z", "first day", [base])
    write(root, "src/app.py", "def run():\n    return 'v2'\n")
    second = commit_all(root, "v2 behaviour", "2020-01-05T10:00:00Z")
    event(root, "2020-01-05T11:00:00Z", "recorded v2", [second])
    write(root, "src/app.py", "def run():\n    return 'v3'\n\ndef extra():\n    return 1\n")
    third = commit_all(root, "v3: extra()", "2020-01-08T10:00:00Z")
    write(root, "docs/notes.md", "notes only\n")
    fourth = commit_all(root, "docs only", "2020-01-08T11:00:00Z")
    r = collect(root)
    check(r["identity"]["exocortex_version"] == "9.9.9" and r["identity"]["exocortex_version_source"] == ".exocortex/.version", "version and its source reported")
    check(r["context"]["newest_event_timestamp_covered"] == "2020-01-02T09:00:00Z", "context coverage read from its own content")
    check([e["timestamp"] for e in r["events"]["newer_than_context"]] == ["2020-01-05T11:00:00Z"], "the newer event is listed")
    check(r["commits"]["last_commit_covered_by_events"] == second, "coverage basis is the commit the newest event records")
    after = [c["sha"] for c in r["commits"]["after_coverage"]]
    check(after == [fourth, third], "both commits after coverage are listed, newest first")
    subs = {c["sha"]: c["substantive"] for c in r["commits"]["after_coverage"]}
    check(subs[third] is True and subs[fourth] is False, "substantive versus documentation classification")
    check({"events_newer_than_context", "commits_after_event_coverage"} <= codes(r), "discrepancies name the event and commit gaps")
    check("commits_after_event_coverage" in r["readiness"]["material_gaps"], "uninspected substantive commits are a material gap")
    shutil.rmtree(root)


def case_recent_context_without_coverage() -> None:
    print("case: recently timestamped context without evidence that it covers current work")
    root = new_repo("exo-onboard-recent-")
    base = git(root, "rev-parse", "HEAD")
    event(root, "2020-02-01T09:00:00Z", "day one", [base])
    write(root, "src/app.py", "def run():\n    return 'changed'\n")
    commit_all(root, "change after the only event", "2020-02-03T10:00:00Z")
    context(root, ["2020-02-01T09:00:00Z"])  # regenerated just now: newest mtime of all
    time.sleep(0.01)
    os.utime(root / ".exocortex/SESSION_CONTEXT.md", None)
    r = collect(root)
    check("context_recent_but_uncovered" in codes(r), "a fresh mtime does not count as coverage")
    check(r["commits"]["substantive_after_coverage"] == 1, "the uncovered substantive commit is counted")
    check(r["readiness"].get("ready") is None and not r["readiness"]["note"].startswith("Ready"), "the collector never claims readiness")
    shutil.rmtree(root)


def case_missing_optional_context_recoverable() -> None:
    print("case: missing generated context, recoverable from events and Git")
    root = new_repo("exo-onboard-missing-")
    head = git(root, "rev-parse", "HEAD")
    event(root, "2020-03-01T09:00:00Z", "everything so far", [head])
    r = collect(root)
    check(r["context"]["exists"] is False and "context_missing" in codes(r), "missing context is reported, not hidden")
    check(r["commits"]["last_commit_covered_by_events"] == head and r["commits"]["after_coverage"] == [], "coverage recovered from the event's recorded commit")
    check(r["readiness"]["material_gaps"] == ["events_newer_than_context"] and "context_missing" not in r["readiness"]["material_gaps"], "the missing context is not itself a gap; reading the covering event is the only one")
    shutil.rmtree(root)


def case_feature_branch_with_foreign_uncommitted_changes() -> None:
    print("case: feature branch differing from main, with foreign uncommitted changes")
    root = new_repo("exo-onboard-branch-")
    head = git(root, "rev-parse", "HEAD")
    event(root, "2020-04-01T09:00:00Z", "main so far", [head])
    context(root, ["2020-04-01T09:00:00Z"])
    git(root, "switch", "-q", "-c", "feat/x")
    write(root, "src/feature.py", "def feature():\n    return True\n")
    commit_all(root, "feature commit", "2020-04-02T10:00:00Z")
    write(root, "src/app.py", "def run():\n    return 'someone else edited this'\n")
    write(root, "scratch.txt", "untracked foreign file\n")
    r = collect(root)
    check(r["identity"]["branch"] == "feat/x" and r["identity"]["detached_head"] is False, "branch identity")
    check(r["default_branch_relation"]["default_branch"] == "main" and r["default_branch_relation"]["ahead"] == 1, "relation to main from local refs")
    check("remote" in r["default_branch_relation"]["note"], "remote refs are declared cached, not verified")
    wt = r["identity"]["working_tree"]
    check(wt["modified"] == 1 and wt["untracked"] == 1 and set(wt["paths"]) == {"src/app.py", "scratch.txt"}, "checkout-local changes listed by path")
    check({"uncommitted_changes_present", "branch_differs_from_default", "commits_after_event_coverage"} <= codes(r), "discrepancies cover the branch, the changes and the uncovered commit")
    check(git(root, "status", "--porcelain").count("\n") == 1, "the foreign changes are still there afterwards")
    shutil.rmtree(root)


def case_truncation_blocks_readiness() -> None:
    print("case: truncated material evidence prevents a readiness claim")
    root = new_repo("exo-onboard-trunc-")
    head = git(root, "rev-parse", "HEAD")
    event(root, "2020-05-01T09:00:00Z", "start", [head])
    context(root, ["2020-05-01T09:00:00Z"])
    for i in range(45):
        write(root, f"src/m{i}.py", f"VALUE = {i}\n")
        commit_all(root, f"module {i}", f"2020-05-02T10:{i:02d}:00Z")
    r = collect(root)
    check(r["commits"]["after_coverage_truncated"] is True and len(r["commits"]["after_coverage"]) == r["limits"]["commits"], "commit list capped and flagged")
    check(r["truncated"] is True and "evidence_truncated" in r["readiness"]["material_gaps"], "truncation is a material gap")
    shutil.rmtree(root)


def case_detached_head_and_unknown_version() -> None:
    print("case: detached HEAD and no version file")
    root = new_repo("exo-onboard-detached-")
    (root / ".exocortex/.version").unlink()
    commit_all(root, "drop version file", "2020-06-01T10:00:00Z")
    git(root, "checkout", "-q", "--detach", "HEAD")
    r = collect(root)
    check(r["identity"]["detached_head"] is True and r["identity"]["branch"] is None, "detached HEAD reported as such")
    check(r["identity"]["exocortex_version"] is None and r["identity"]["exocortex_version_source"] == "absent", "unknown version is reported as absent, not guessed")
    check("exocortex_version_unknown" in codes(r), "unknown version is a discrepancy")
    shutil.rmtree(root)


def case_no_writes_no_network() -> None:
    print("case: evidence collection writes nothing and contacts nothing")
    root = new_repo("exo-onboard-readonly-")
    event(root, "2020-07-01T09:00:00Z", "x", [git(root, "rev-parse", "HEAD")])
    context(root, ["2020-07-01T09:00:00Z"])
    write(root, "dirty.txt", "uncommitted\n")
    git(root, "remote", "add", "origin", "https://127.0.0.1:9/never-contacted.git")
    before = tree_digest(root)
    refs_before = git(root, "for-each-ref")
    proc = subprocess.run([sys.executable, str(COLLECTOR), str(root)], capture_output=True, text=True, check=False,
                          env=dict(os.environ, GIT_TERMINAL_PROMPT="0", http_proxy="http://127.0.0.1:9", https_proxy="http://127.0.0.1:9"))
    check(proc.returncode == 0 and json.loads(proc.stdout)["ok"] is True, "runs to completion with an unreachable remote configured")
    check(tree_digest(root) == before, "repository bytes and mtimes unchanged")
    check(git(root, "for-each-ref") == refs_before, "refs unchanged")
    source = COLLECTOR.read_text(encoding="utf-8")
    forbidden = re.findall(r"\b(fetch|pull|push|ls-remote|urllib|requests|socket|http\.client|curl|wget)\b", source)
    forbidden = [f for f in forbidden if f not in ("fetch", "pull", "push", "ls-remote") or re.search(rf"\"{f}\"", source)]
    check(not forbidden, f"collector source contains no network primitives ({forbidden})")
    shutil.rmtree(root)


def case_command_contract() -> None:
    print("case: the canonical command pins the conditional completion")
    cmd = json.loads(COMMAND.read_text(encoding="utf-8"))
    steps = cmd["steps"]
    check(steps[0]["type"] == "shell" and "onboard_evidence.py" in steps[0]["command"], "first step runs the read-only collector")
    final = steps[-1]["context"]
    check("Onboarding incomplete:" in final and "Ready to work. What do you need?" in final, "final step carries both outcomes")
    check("only" in cmd["constraints"]["completion"] and "never silently" in cmd["constraints"]["completion"], "completion is conditional and missing required evidence never becomes success")
    read_steps = [s for s in steps if s["type"] == "read"]
    check(read_steps and read_steps[0].get("on_error") == "record_gap", "memory read errors are recorded as gaps, not continued past")
    joined = json.dumps(cmd)
    check("commit titles alone" in joined.lower() or "Commit titles alone" in joined, "commit titles alone are declared insufficient")
    check(all(word in joined for word in ("what remains unfinished", "verify first", "unverified")), "report sections required")
    check("network" in cmd["constraints"]["read_only"] and "regenerates context" in cmd["constraints"]["read_only"], "read-only constraint states the forbidden actions")
    for family in (".agents", ".claude", ".cursor"):
        adapter = TEMPLATE / family / "skills" / "onboard" / "SKILL.md"
        text = adapter.read_text(encoding="utf-8") if adapter.exists() else ""
        check("GENERATED BY" in text and "onboard_evidence" not in text, f"{family} adapter stays a generated thin pointer")


def main() -> int:
    if not COLLECTOR.exists():
        print(f"missing collector: {COLLECTOR}")
        return 1
    for case in (case_stale_context_newer_event_newer_commits, case_recent_context_without_coverage,
                 case_missing_optional_context_recoverable, case_feature_branch_with_foreign_uncommitted_changes,
                 case_truncation_blocks_readiness, case_detached_head_and_unknown_version,
                 case_no_writes_no_network, case_command_contract):
        try:
            case()
        except Exception as exc:  # noqa: BLE001 - a fixture failure is a test failure
            FAILURES.append(f"{case.__name__}: {exc!r}")
            print(f"  FAIL {case.__name__}: {exc!r}")
    print(f"{'PASS' if not FAILURES else 'FAIL'}: {len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
