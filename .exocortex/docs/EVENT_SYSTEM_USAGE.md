# Event System

Events are append-only project-local narrative memory. They may describe work,
decisions, evidence, and next steps. They are not approvals, lifecycle
transitions, checkpoints, commits, release evidence, or deployment authority.

`/save` drafts a narrative event and shows it first. Recording requires the
applicable local mutation gate. No event is synchronized automatically.

Lifecycle checkpoints are different: only an accepted, authorized transition
marked checkpoint-eligible creates one stable idempotent checkpoint. Chat,
tests, support lanes, rejected attempts, retries, saves, and handoffs do not.

`generate_context.sh` may derive a project-local session view from existing
events. Generated context can be stale and must be reconciled against live Git,
the exact work item, and local event history.

Archiving is read-only preview by default. Moving or deleting event files needs
a separately scoped guarded mutation and rollback evidence.

External publication follows `RAG_INTEGRATION.md` and always uses a separate
immutable descriptor plus destination-specific approval.
