#!/usr/bin/env python3
"""Read-only evidence collector for /onboard.

Reports, as one JSON document on stdout, what the active checkout is and how
far the recorded project context actually covers it: identity (root, branch or
detached HEAD, commit, working tree, installed Exocortex version and where that
version was read from), provenance (which events and commits the generated
context covers), the commits and changed paths that nothing recorded covers,
checkout-local uncommitted changes, discrepancies, and truncation.

It never certifies comprehension. A model still has to read the events and the
diffs it names and explain them; this script only says what exists and what is
newer than what.

Guarantees:
  - read-only: no file is written, no ref, index or worktree is touched;
  - offline: no fetch, pull, push or ls-remote; cached remote refs are reported
    as cached, never as fresh remote state;
  - bounded: every list is capped and reports `truncated` when the cap bit;
  - stdlib only, exits 0 with a JSON body even when evidence is missing.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_COMMITS = 40
MAX_PATHS_PER_COMMIT = 25
MAX_EVENTS_LISTED = 15
MAX_EVENTS_SCANNED_FOR_SHAS = 12
MAX_WORKTREE_PATHS = 60
MAX_RECORDS = 20

DOC_PREFIXES = (".exocortex/events/", ".exocortex/archive/", "docs/")
DOC_SUFFIXES = (".md", ".txt", ".rst")
VERSION_SOURCES = (
    (".exocortex/.version", "text"),
    ("VERSION", "text"),
    (".exocortex/release-baseline.json", "json:version"),
    (".exocortex/.install-manifest", "manifest"),
)
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
# generate_context.sh writes each covered event as "**Event:** %B %d at %I:%M %p • machine • editor • Branch: `x`"
DISPLAY_RE = re.compile(r"(?m)^\*\*Event:\*\*\s*([A-Z][a-z]+) (\d{1,2}) at (\d{1,2}):(\d{2}) (AM|PM)\b")
LAST_UPDATED_RE = re.compile(r"(?m)^\*\*Last Updated:\*\*.*?\b(20\d{2})\b")
MONTHS = {m: i for i, m in enumerate(("January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"), start=1)}
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[_T](\d{2})[-:](\d{2})[-:](\d{2})")
SHA_RE = re.compile(r"(?m)^\s*([0-9a-f]{7,40})\b")


def git(root: Path, *args: str) -> tuple[int, str]:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, env=env, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - defensive
        return 1, str(exc)
    return proc.returncode, proc.stdout.strip("\n")


def read_text(path: Path, limit: int = 2_000_000) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return None


def event_datetime(name: str, body: str | None) -> str | None:
    if body:
        match = re.search(r"(?m)^timestamp:\s*(\S+)", body)
        if match:
            return match.group(1)
    match = DATE_RE.match(name)
    if match:
        return f"{match.group(1)}T{match.group(2)}:{match.group(3)}:{match.group(4)}Z"
    return None


def display_stamps(context_text: str, mtime_iso: str) -> list[str]:
    """Recover ISO timestamps from the human-readable event lines the context generator writes.

    The generator formats the event's UTC timestamp with `date -j -f` (no zone conversion), so the
    digits shown are the UTC digits; the year comes from the Last Updated line, else the file's mtime.
    A month later than the Last Updated month belongs to the previous year (week spanning New Year).
    """
    year_match = LAST_UPDATED_RE.search(context_text)
    base_year = int(year_match.group(1)) if year_match else int(mtime_iso[:4])
    updated_month = None
    if year_match:
        month_match = re.search(r"([A-Z][a-z]+) \d{1,2}, 20\d{2}", year_match.group(0))
        updated_month = MONTHS.get(month_match.group(1)) if month_match else None
    out = []
    for month_name, day, hour, minute, ampm in DISPLAY_RE.findall(context_text):
        month = MONTHS.get(month_name)
        if not month:
            continue
        h = int(hour) % 12 + (12 if ampm == "PM" else 0)
        year = base_year - 1 if updated_month and month > updated_month else base_year
        out.append(f"{year:04d}-{month:02d}-{int(day):02d}T{h:02d}:{int(minute):02d}:00Z")
    return out


def is_documentation(path: str) -> bool:
    return path.startswith(DOC_PREFIXES) or path.endswith(DOC_SUFFIXES)


def collect(start: Path) -> dict:
    out: dict = {"ok": True, "schema": "onboard-evidence/1", "errors": [], "truncated": False, "truncated_lists": [],
                 "limits": {"commits": MAX_COMMITS, "paths_per_commit": MAX_PATHS_PER_COMMIT,
                            "events_listed": MAX_EVENTS_LISTED, "worktree_paths": MAX_WORKTREE_PATHS}}
    rc, top = git(start, "rev-parse", "--show-toplevel")
    if rc != 0 or not top:
        out["ok"] = False
        out["errors"].append("not_a_git_repository")
        out["identity"] = {"repository_root": str(start.resolve())}
        return out
    root = Path(top)

    # ── identity ────────────────────────────────────────────────────────────
    _, head = git(root, "rev-parse", "HEAD")
    rc_b, branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    detached = rc_b != 0
    _, status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    lines = [line for line in status.splitlines() if line.strip()]
    staged = [l[3:] for l in lines if l[0] not in " ?"]
    modified = [l[3:] for l in lines if l[1] == "M" or l[1] == "D"]
    untracked = [l[3:] for l in lines if l.startswith("??")]
    paths = [l[3:] for l in lines]
    version_value, version_source = None, None
    for rel, kind in VERSION_SOURCES:
        text = read_text(root / rel, 200_000)
        if text is None:
            continue
        if kind == "text":
            candidate = text.strip().splitlines()[0].strip() if text.strip() else ""
        elif kind == "json:version":
            try:
                candidate = str(json.loads(text).get("version", "")).strip()
            except ValueError:
                candidate = ""
        else:
            match = re.search(r"(?im)^(?:template_)?version[=:\s]+\"?(\d+\.\d+\.\d+)", text)
            candidate = match.group(1) if match else ""
        if re.fullmatch(r"\d+\.\d+\.\d+", candidate or ""):
            version_value, version_source = candidate, rel
            break
    out["identity"] = {
        "repository_root": str(root),
        "branch": None if detached else branch,
        "detached_head": detached,
        "head_commit": head or None,
        "head_commit_date": git(root, "log", "-1", "--format=%cI", "HEAD")[1] or None,
        "head_commit_date_basis": "committer date (%cI); git show prints the author date, which can differ",
        "head_author_date": git(root, "log", "-1", "--format=%aI", "HEAD")[1] or None,
        "working_tree": {
            "clean": not lines,
            "staged": len(staged), "modified": len(modified), "untracked": len(untracked),
            "paths": paths[:MAX_WORKTREE_PATHS],
            "truncated": len(paths) > MAX_WORKTREE_PATHS,
        },
        "exocortex_version": version_value,
        "exocortex_version_source": version_source or "absent",
        "role": "read_only",
    }
    if version_value is None:
        out["errors"].append("exocortex_version_unknown")
    if len(paths) > MAX_WORKTREE_PATHS:
        out["truncated"] = True
        out["truncated_lists"].append("identity.working_tree.paths")

    # ── recorded context: what it says it covers ────────────────────────────
    exo = root / ".exocortex"
    context_path = exo / "SESSION_CONTEXT.md"
    context_text = read_text(context_path)
    context: dict = {"path": ".exocortex/SESSION_CONTEXT.md", "exists": context_text is not None}
    if context_text is not None:
        context["mtime"] = datetime.fromtimestamp(context_path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        gen = re.search(r"(?m)^\*\*Generated from events:\*\*\s*(.+)$", context_text)
        context["generated_from"] = gen.group(1).strip() if gen else None
        stamps = set(ISO_RE.findall(context_text))
        stamps.update(display_stamps(context_text, context["mtime"]))
        stamps = sorted(stamps)
        context["newest_event_timestamp_covered"] = stamps[-1] if stamps else None
        context["event_timestamps_covered"] = len(stamps)
    out["context"] = context

    events_dir = exo / "events"
    events: list[dict] = []
    if events_dir.is_dir():
        names = sorted(p.name for p in events_dir.iterdir() if p.suffix == ".md")
        for name in reversed(names[-max(MAX_EVENTS_LISTED, MAX_EVENTS_SCANNED_FOR_SHAS):]):
            body = read_text(events_dir / name, 400_000)
            events.append({"name": name, "timestamp": event_datetime(name, body), "_body": body})
        total_events = len(names)
    else:
        total_events = 0
    newest_event = events[0]["timestamp"] if events else None
    covered_ts = context.get("newest_event_timestamp_covered") if context_text is not None else None
    events_newer_than_context = [e for e in events if e["timestamp"] and (covered_ts is None or e["timestamp"] > covered_ts)]
    out["events"] = {
        "directory": ".exocortex/events", "exists": events_dir.is_dir(), "count": total_events,
        "newest_timestamp": newest_event,
        "newer_than_context": [{"name": e["name"], "timestamp": e["timestamp"]} for e in events_newer_than_context[:MAX_EVENTS_LISTED]],
        "newer_than_context_truncated": len(events_newer_than_context) > MAX_EVENTS_LISTED,
    }
    if len(events_newer_than_context) > MAX_EVENTS_LISTED:
        out["truncated"] = True
        out["truncated_lists"].append("events.newer_than_context")

    # ── commit ancestry: the newest commit any recent event records ─────────
    covered_commit, covered_by = None, None
    for event in events[:MAX_EVENTS_SCANNED_FOR_SHAS]:
        body = event.get("_body") or ""
        for sha in SHA_RE.findall(body):
            rc_v, full = git(root, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
            if rc_v != 0 or not full:
                continue
            if git(root, "merge-base", "--is-ancestor", full, "HEAD")[0] == 0:
                covered_commit, covered_by = full, event["name"]
                break
        if covered_commit:
            break
    for event in events:
        event.pop("_body", None)

    commits: list[dict] = []
    substantive = 0
    if covered_commit:
        rng = f"{covered_commit}..HEAD"
    else:
        rng = "HEAD"
    _, log = git(root, "log", f"--max-count={MAX_COMMITS + 1}", "--format=%H%x1f%cI%x1f%s", rng)
    entries = [l.split("\x1f") for l in log.splitlines() if l]
    commits_truncated = len(entries) > MAX_COMMITS
    for sha, date, subject in entries[:MAX_COMMITS]:
        _, names = git(root, "show", "--format=", "--name-only", sha)
        changed = [n for n in names.splitlines() if n]
        sub_paths = [n for n in changed if not is_documentation(n)]
        if sub_paths:
            substantive += 1
        commits.append({
            "sha": sha, "date": date, "subject": subject,
            "changed_paths": changed[:MAX_PATHS_PER_COMMIT],
            "changed_paths_truncated": len(changed) > MAX_PATHS_PER_COMMIT,
            "substantive": bool(sub_paths),
        })
        if len(changed) > MAX_PATHS_PER_COMMIT:
            out["truncated"] = True
            out["truncated_lists"].append(f"commits.after_coverage[{sha[:8]}].changed_paths")
    if commits_truncated:
        out["truncated"] = True
        out["truncated_lists"].append("commits.after_coverage")
    out["commits"] = {
        "last_commit_covered_by_events": covered_commit,
        "covered_by_event": covered_by,
        "coverage_basis": "event_recorded_commit_ancestry" if covered_commit else "none_recorded",
        "after_coverage": commits,
        "after_coverage_count": len(entries) if not commits_truncated else f">{MAX_COMMITS}",
        "after_coverage_truncated": commits_truncated,
        "substantive_after_coverage": substantive,
    }

    # ── handoff and task records ────────────────────────────────────────────
    records = []
    candidates = [exo / "TODO.md", exo / "control" / "HANDOFF.md", exo / "control" / "INTERRUPTS.md"]
    for sub in ("control", "planning", "work-items", "handoffs"):
        d = exo / sub
        if d.is_dir():
            candidates.extend(sorted(p for p in d.iterdir() if p.is_file() and re.search(r"handoff|todo|task|work", p.name, re.I)))
    seen = set()
    for p in candidates:
        if p in seen or not p.is_file():
            continue
        seen.add(p)
        mtime = datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        records.append({"path": str(p.relative_to(root)), "mtime": mtime,
                        "newer_than_context": bool(context_text is not None and mtime > context["mtime"])})
    out["records"] = {"items": records[:MAX_RECORDS], "truncated": len(records) > MAX_RECORDS}
    if len(records) > MAX_RECORDS:
        out["truncated"] = True
        out["truncated_lists"].append("records.items")

    # ── default branch relation, local refs only ────────────────────────────
    relation: dict = {"note": "local refs only; remote-tracking refs are cached, not freshly verified"}
    for base in ("main", "master"):
        if git(root, "rev-parse", "--verify", "--quiet", base)[0] == 0:
            _, counts = git(root, "rev-list", "--left-right", "--count", f"{base}...HEAD")
            behind, ahead = (counts.split() + ["0", "0"])[:2]
            relation.update({"default_branch": base, "ahead": int(ahead), "behind": int(behind),
                             "differs": ahead != "0" or behind != "0"})
            break
    else:
        relation["default_branch"] = None
    out["default_branch_relation"] = relation

    # ── discrepancies and readiness blockers ────────────────────────────────
    disc: list[dict] = []
    if context_text is None:
        disc.append({"code": "context_missing", "detail": "no .exocortex/SESSION_CONTEXT.md; recover coverage from events and Git"})
    if events_newer_than_context:
        disc.append({"code": "events_newer_than_context", "count": len(events_newer_than_context)})
    if commits:
        disc.append({"code": "commits_after_event_coverage", "count": out["commits"]["after_coverage_count"],
                     "substantive": substantive})
    head_date = out["identity"]["head_commit_date"] or ""
    head_date_utc = datetime.fromisoformat(head_date).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if head_date else ""
    # "recent" means the file was written after the newest uncovered commit: a regenerated context that still
    # does not record the work. Being newer than the last event is normal (contexts are generated right after saves).
    context_is_recent = bool(context.get("mtime")) and bool(head_date_utc) and context["mtime"] > head_date_utc
    if context_text is not None and commits and context_is_recent:
        disc.append({"code": "context_recent_but_uncovered",
                     "detail": "SESSION_CONTEXT.md was written after the newest commit yet commits exist that no event records; a regenerated file is not evidence of coverage"})
    if lines:
        disc.append({"code": "uncommitted_changes_present", "count": len(lines),
                     "detail": "checkout-local; preserve, and distinguish from committed work"})
    if relation.get("differs"):
        disc.append({"code": "branch_differs_from_default", "ahead": relation["ahead"], "behind": relation["behind"]})
    if version_value is None:
        disc.append({"code": "exocortex_version_unknown", "detail": "no version file found; report as unknown, do not guess"})
    if not events and context_text is None:
        disc.append({"code": "no_recorded_context", "detail": "neither events nor generated context exist"})
    if out["truncated"]:
        disc.append({"code": "evidence_truncated", "lists": list(out["truncated_lists"]),
                     "detail": "these lists hit their cap; inspect beyond the cap yourself (e.g. git show --stat <sha>, ls .exocortex/events) or report the uncertainty"})
    out["discrepancies"] = disc
    blockers = [d["code"] for d in disc if d["code"] in ("commits_after_event_coverage", "events_newer_than_context",
                                                          "context_recent_but_uncovered", "evidence_truncated",
                                                          "no_recorded_context")]
    out["readiness"] = {
        "material_gaps": blockers,
        "note": ("Each gap must be resolved by reading the named events and inspecting the named commits' "
                 "diffs or current implementations before 'Ready to work' may be claimed; missing optional "
                 "files do not block when other evidence resolves the context."),
    }
    return out


def main(argv: list[str]) -> int:
    start = Path(argv[1]).expanduser() if len(argv) > 1 else Path.cwd()
    result = collect(start)
    json.dump(result, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
