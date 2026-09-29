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

The guarded closeout path is `complete-local-delivery`, after a matching
`bootstrap-local-delivery`, `seal-local-edit`, ordinary developer verification,
independent review, QA/SIT, UAT-ready, and explicit `human_uat`. Bootstrap
atomically creates/reserves/activates the approved item in `developing`, not a
normal transition or checkpoint. Closeout records `local_state=complete`,
creates one local event and handoff, releases the writer, and leaves lifecycle
at `human_uat`; `release_ready` and publication remain separate gates.
`create_event.sh` remains the manual `/save` helper; it cannot perform UAT
closeout or release the writer. Neither event path authorizes commit, push,
release, deployment, synchronization, credential access, or network egress.

Closeout `--body-file` and bootstrap `--envelope-source` accept only
project-relative regular files under `.exocortex/local/protocol/inbox/` and
reject credential-shaped names (`.env`, `.env.*`, private-key formats,
`credentials`, or `secrets`) before opening. The five verification/UAT gates
require non-empty evidence; local transition capabilities bind the full
transition intent. Human UAT records an attestor matching the envelope
approver. Acceptance criteria remain pending through `uat_ready`; that
Human-UAT transition refuses failed or blocked criteria and atomically records
the remaining criteria as passed with its evidence. Closeout rechecks that
every criterion passed and still contains the exact Human-UAT transition
marker and evidence. These records are cooperative local evidence, not
cryptographic proof of a person's identity. Closeout also verifies the
Human-UAT transition against its consumed one-time capability and finalized
guarded transaction.

Lifecycle checkpoints are different: only an accepted, authorized transition
marked checkpoint-eligible creates one stable idempotent checkpoint. Chat,
tests, support lanes, rejected attempts, retries, saves, and handoffs do not.

`create_event.sh` saves the approved event and refreshes only the generated
Session Context section and local source-hash receipt. Handwritten context
and durable memory are preserved. No model is called. It never accepts
context-refresh authority as an extra command-line flag.

An ordinary authorized local refresh can use `generate_context.sh` or
`refresh_rollups.py --apply`. Guarded completion and handoff transactions need
that separate followup when refresh is in scope. Do not replay them.
If event creation exits 3, the event already exists: retry only the refresh.
`read_memory_stack.sh` warns about source additions, changes, deletions and
window rollover; `refresh_rollups.py --check --json` explains the discrepancy.
That warning begins with `MEMORY_FRESHNESS_WARNING:` so every provider can
surface it without guessing.
Generated context must be reconciled against live Git, the exact work item,
and local event history.

Archiving is read-only preview by default. Moving or deleting event files needs
a separately scoped guarded mutation and rollback evidence.

External publication follows `RAG_INTEGRATION.md` and always uses a separate
immutable descriptor plus destination-specific approval.
