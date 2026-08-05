# Event system

Events are append-only, project-local work records. They preserve what
happened, why decisions were made, verification status, and the next useful
step. They do not grant authority and are not lifecycle checkpoints.

## When an event is created

- An approved local-delivery task that changes project files ends with exactly
  one concise completion event before the writer is released.
- `/save` is manual for ordinary chat. It first drafts the narrative in chat
  and records it only within an applicable local-delivery authorization.
- Read-only work, tests, elapsed time, failed attempts, branch changes, and Git
  hooks do not create events automatically.

No event is pushed, synchronized, published, or sent to a provider
automatically.

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
