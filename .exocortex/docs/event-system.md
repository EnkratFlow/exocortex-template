# Event system

Events are append-only, project-local work records. They preserve what
happened, why decisions were made, verification status, and the next useful
step. They do not grant authority and are not lifecycle checkpoints.

## When an event is created

- An approved local-delivery task that changes project files ends with exactly
  one concise completion event before the writer is released. The orchestrator
  permits that closeout only after a matching `bootstrap-local-delivery`,
  `seal-local-edit`, and `human_uat`.
- `/save` is manual for ordinary chat. It first drafts the narrative in chat
  and records it only within an applicable local-delivery authorization.
- Read-only work, tests, elapsed time, failed attempts, branch changes, and Git
  hooks do not create events automatically.

No event is pushed, synchronized, published, or sent to a provider
automatically.

`bootstrap-local-delivery` binds one clean isolated worktree to its exact base,
branch, and allowed paths, then atomically creates/reserves/activates the item
in `developing` without a normal transition or checkpoint. `seal-local-edit`
records the actual changed set and rejects an extra path. Ordinary developer
verification, independent review, QA/SIT, UAT-ready, and explicit `human_uat`
still follow. `complete-local-delivery` then records `local_state=complete`,
creates the one local completion event and handoff, releases the writer, and
leaves lifecycle at `human_uat`; `release_ready` and publication are separate.
These cooperative local operations never authorize commit, push, release,
deployment, credential access, or network egress. `create_event.sh` remains
the manual `/save` helper for narrative events and is not closeout authority.

`bootstrap-local-delivery --envelope-source` and
`complete-local-delivery --body-file` accept only project-relative regular
files under `.exocortex/local/protocol/inbox/`; credential-shaped names
(`.env`, `.env.*`, private-key formats, `credentials`, or `secrets`) are
rejected before opening. Developer verification, independent review, QA/SIT,
UAT-ready, and Human UAT require non-empty evidence. Every local transition
capability binds full transition intent; Human UAT records an attestor matching
the envelope approver. Acceptance criteria remain pending through `uat_ready`;
that Human-UAT transition refuses failed or blocked criteria and atomically
records the remaining criteria as passed with its evidence. Closeout rechecks
that every criterion passed and still contains the exact Human-UAT transition
marker and evidence. This is cooperative local evidence, not cryptographic
proof of a person's identity. Closeout also verifies the Human-UAT transition
against its consumed one-time capability and finalized guarded transaction.

## Record an approved event

Pass the reviewed body directly and call the helper once:

```bash
bash .exocortex/scripts/create_event.sh <<'EVENT'
# Completion record

<approved narrative>
EVENT
```

The helper records metadata and current Git evidence. It does not regenerate
`.exocortex/SESSION_CONTEXT.md`, does not accept context-refresh authority, and
does not create a preview file.

If a caller already owns a body file it may use `--body-file`; the event helper
never creates a preview/body file itself. A Session Context refresh is a
separate protected-memory mutation. Only a registered guarded writer may run
it inside matching local-delivery scope:

```bash
bash .exocortex/scripts/generate_context.sh
```

Never add that refresh to event creation or treat an event-recording capability
as refresh authority.

## Freshness and authority

Events are source evidence. Session Context and other summaries are derived
views and can become stale. `.exocortex/scripts/read_memory_stack.sh` prints a
freshness warning when a newer event exists; prefer the event history and live
Git state until an explicit refresh is requested.

A retrospective may propose additions to `PROJECT_MEMORY.md`, `LESSONS.md`,
or `OPEN_DECISIONS.md`. Those proposals require applicable local-delivery
scope before they become durable memory. No retrospective can authorize its
own protocol or code change.

External memory follows `RAG_INTEGRATION.md` and requires a separate exact
destination-specific authorization.
