# Memory System

Project-local markdown events are the source evidence. Generated session and
tier views are derived, can be stale, and never outrank live Git, the exact work
item, or durable transition records.

The four views are right-now, short-term, long-term, and subconscious pattern
analysis. The active conversation model can summarize them locally. No memory
script reads credentials or calls a provider directly.

Narrative events improve future orientation but do not grant authority. A save
does not create a lifecycle checkpoint. Pattern analysis can propose a new
work item; it cannot approve, reserve, implement, send, or promote it.

External memory uses a separately staged immutable payload and exact egress
authorization. No automatic hub, vault, RAG, or cross-project flow exists.

## Refresh and verify the generated view

```bash
# Read-only; exit 0 fresh, 1 stale, 2 inspection failure.
python3 .exocortex/scripts/refresh_rollups.py --check --json
# An approved local refresh, including the first backfill:
python3 .exocortex/scripts/refresh_rollups.py --apply
```

The refresh reads both narrative saves and short handoffs without depending on
particular headings. It indexes every event's content hash, uses recorded UTC
dates instead of modification times, and renders the latest recorded work,
seven days of bounded excerpts and the previous 7 to 30 days of source links.
Older, undated and future-dated evidence remains on disk. Large collections or
unsafe paths are refused; excerpt/index truncation is explicit.

Only the marked generated section changes. Existing context stays below it as
historical material, and a first-refresh `.backup` is created only if absent.
No handwritten text or existing backup is replaced. A lock coordinates these
helpers, and atomic file replacements avoid partial files. Independent editors
do not share that lock: pause competing edits before refreshing. An interrupted
context/receipt pair is detected as stale on the next check.

An approved save through `create_event.sh` performs that refresh. Exit 3 means
the event already saved and needs only a refresh retry. Guarded completion and
handoff transactions need an explicit in-scope refresh afterward. Session entry,
`/onboard`, `/work`, and `/preflight` check coverage without writing. There is no
new background job or provider-specific startup hook.

## Review durable memory separately

Fresh coverage is not proof that a historical next step remains open. A later
event may finish, cancel or roll back the work. Copying every old next action
into TODO would create false work; copying conversation patterns into LESSONS
would promote observations into facts.

```bash
# Local read-only source packet; defaults to the last 30 days.
python3 .exocortex/scripts/curate_memory.py packet
# Explicit full-history packet for an authorized backfill.
python3 .exocortex/scripts/curate_memory.py packet --all-events
# Review an owned proposal, without changing its targets.
python3 .exocortex/scripts/curate_memory.py preview \
  --proposal .exocortex/local/memory/proposals/review.json
```

Use `.exocortex/prompts/memory-curator.md` with the packet. Packets contain
project-local event and durable-memory text; do not send them to an external
provider without the applicable data and destination authorization. A proposal
names a stable subject, target, status and exact source quotations. Preview
rejects invented quotations, unsupported targets, or drift in the original
events or durable files. The preview does not apply changes. Reconcile it with
live evidence and handwritten notes, then make the reviewed edits within the
approved task. No script automatically changes PROJECT_MEMORY, LESSONS, TODO,
OPEN_DECISIONS, subconscious_patterns or control/BACKLOG.

## Optional GEPA pilot

See [the pilot guide](../evals/memory/README.md). GEPA may optimize the curation
prompt against fixed reference answers. It does not decide whether source
events are fresh or grant approval to write memory. The shipped fictional
fixtures and fake-model tests verify the infrastructure, not model quality.

## Rollout and owner instruction replacement

This is a template change. Existing projects need their normal reviewed upgrade
in an isolated project worktree before using it. Check coverage, perform one
authorized refresh, then build and review a historical curation packet. Keep
existing backups. Do not automatically upgrade other active checkouts.

Suggested replacement for an owner's global `/save` instruction:

> An approved project-local save through create_event.sh records the reviewed
> event and refreshes only the generated Session Context section and its local
> coverage receipt. Handwritten memory is preserved. Lessons, decisions, tasks
> and patterns require source-backed review before they change. Session entry
> checks freshness read-only and reconciles stale views against events and live
> Git. A save never creates a lifecycle checkpoint or synchronizes externally.
