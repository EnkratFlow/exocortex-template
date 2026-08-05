# Event System

Events are append-only project-local narrative memory. They may describe work,
decisions, evidence, and next steps. They are not approvals, lifecycle
transitions, checkpoints, commits, release evidence, or deployment authority.

`/save` drafts a narrative event and shows it first. It remains manual for
ordinary chat. Recording requires the applicable local mutation gate. No event
is synchronized automatically.

An approved local-delivery task that changes files ends with exactly one
concise completion event. This is task closeout, not an automatic chat save,
and it stays inside the existing local-delivery authorization.

Lifecycle checkpoints are different: only an accepted, authorized transition
marked checkpoint-eligible creates one stable idempotent checkpoint. Chat,
tests, support lanes, rejected attempts, retries, saves, and handoffs do not.

`create_event.sh` records only the event. It never accepts context-refresh
authority, refreshes Session Context, or creates a preview as a side effect.

Inside a separately authorized guarded writer operation,
`generate_context.sh` may derive a project-local session view from existing
events. It is never part of event recording. `read_memory_stack.sh` warns when
newer events make that view stale.
That warning begins with `MEMORY_FRESHNESS_WARNING:` so every provider can
surface it without guessing.
Generated context must be reconciled against live Git, the exact work item,
and local event history.

Archiving is read-only preview by default. Moving or deleting event files needs
a separately scoped guarded mutation and rollback evidence.

External publication follows `RAG_INTEGRATION.md` and always uses a separate
immutable descriptor plus destination-specific approval.
