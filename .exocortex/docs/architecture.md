# Exocortex architecture

Exocortex is a project-local memory, delivery, and multi-AI control protocol.
The repository owns its context, authority, evidence, and lifecycle state. AI
systems are interchangeable workers operating through the same checked entry
contract.

## Design goals

- Give any AI surface a zero-context path into the repository.
- Default unknown or unregistered actors to read-only behavior.
- Route work to the least-expensive available model capable of the complete
  bounded task and its risk.
- Keep one accountable writer while parallel evidence and review lanes remain
  read-only.
- Separate narrative memory, lifecycle checkpoints, handoffs, and outward
  actions.
- Preserve project data during installation, update, and public-template
  promotion.
- Turn retrospectives into prospective improvements without allowing a system
  to expand its own authority.

## System boundary

```text
human approval
      |
      v
AI_START_HERE.md -> command adapter -> authority/orchestration guards
      |                                      |
      v                                      v
project memory and Git truth          bounded local mutation
      |                                      |
      +--------------> evidence <------------+
                             |
                             v
              independent review and gates
                             |
                             v
            separately approved outward action
```

`AI_START_HERE.md` is the canonical entry contract. Editor rules, skills,
command bridges, and automations are thin adapters: they may discover the
contract, but they cannot broaden it.

## Three planes

| Plane | Direction | Contents |
|---|---|---|
| Code | Promoted template to a project | Generic entry files, commands, guards, schemas, adapters, documentation, and tests |
| Data | Project-local only | Memory, events, work items, approvals, reservations, registries, policies, and protocol transactions |
| External | One explicitly approved destination | One immutable, digest-bound payload sent by one approved method |

Code may flow down after review and promotion. Project data never flows
sideways into the template or another repository. Nothing flows outward
automatically.

## Canonical entry and orientation

Every AI, editor, command, skill, and automation follows the same sequence:

1. Read `AI_START_HERE.md`.
2. Read `.exocortex/AI_BOOTSTRAP.md` and the matching command specification.
3. Load the project memory entry point and its required files.
4. Resolve live Git, the active work item, its revision, current state, and
   exact approval records.
5. Declare one role: `read_only`, `writer`, or `independent_reviewer`.
6. Stop before mutation if any base, path, reservation, executor, capability,
   expiry, revocation, or verification requirement is missing or ambiguous.

Generated session context and prior chat are convenience evidence. Live Git
and project-local protocol records are authoritative.

## Command system

The 24 JSON specifications in `.exocortex/commands/` describe read, shell, AI,
and user-choice steps. The bootstrap discovers those commands and specifies
read-only defaults; guarded executors enforce mutations. A command description
containing an action verb is a proposal, not permission.

Command adapters exist for supported editor surfaces. All adapters point back
to the same entry contract and command JSON; none owns a separate authority
model.

## Memory and event system

Project-local events are append-only narrative records. Deterministic scripts
select events for four views:

```text
RIGHT NOW       0-7 days     detailed current work
SHORT TERM      7-31 days    recurring themes
LONG TERM       31+ days     historical arcs
SUBCONSCIOUS    all events   cross-cutting patterns
```

The active conversation model can summarize selected local evidence without a
network call. Provider-assisted curation is unavailable by default and, if
ever enabled, must use the same immutable outward-action protocol as any other
external delivery.

`SESSION_CONTEXT.md` is generated from events for convenience. It must be
reconciled against live Git and exact work-item records before decisions.

## Saves, checkpoints, and handoffs

These mechanisms intentionally differ:

- A save is a user-requested local narrative event.
- A lifecycle checkpoint is created only as part of an accepted, durable,
  checkpoint-eligible state transition.
- A handoff records evidence for the next actor but grants no authority.

Rejected, invalid, unauthorized, stale, conflicting, read-only, test, support,
ordinary-chat, and replay activity creates no new lifecycle checkpoint. A
retry of an accepted transition converges on its existing checkpoint.

## Orchestration and model routing

`.exocortex/control/MODEL_ROUTING.md` defines capability- and cost-aware
routing. The accountable parent must be capable of interpreting authority,
decomposing the task, integrating results, making risk decisions, and
validating final evidence. Parent judgment is the default; route reporting is
for visibility and routine model choice is not a human approval gate.

The routing sequence is:

1. Classify complexity, ambiguity, context, tools, and outward effects.
2. Classify privacy, security, data, financial, migration, destructive, and
   deployment risk.
3. Use deterministic tooling first.
4. Select the model with the best expected cost of a correct outcome for the
   complete bounded task.
5. Apply the same judgment to each subagent and delegate only independently
   useful evidence, implementation, or review slices.
6. Keep one registered guarded writer; keep other lanes read-only.
7. Escalate when risk, ambiguity, repeated failure, or material design judgment
   exceeds the selected role.
8. Stop duplicate reviews when evidence converges.

Provider adapters may map available models to these roles using versioned
capability, reliability, latency, and cost metadata. Those mappings are
advisory; no provider, model name, or permanent highest-tier-first rule is part
of the protocol.

The public source registry defines configured official-source coverage and
freshness limits. The reviewed catalog normalizes public lifecycle and price
facts, while protected `.exocortex/local/model-routing/**` evidence records
current-surface availability and measured evaluation results. This machinery
is an optional empirical verifier, not an authority or prerequisite. Discovery
is offline and proposal-only: new models enter quarantine and missing
observations do not imply deprecation. A formal route requires fresh eligible
evidence and binds its timestamp to runtime UTC within 60 seconds, so the
historical validator cannot replay a stale or future live route.

## Agile delivery lifecycle

`.exocortex/control/DELIVERY_WORKFLOW.md` defines the minute-scale Kanban/SDLC
path:

```text
captured -> triaged -> refined -> ready -> reserved -> developing
-> developer_verified -> independent_review -> qa_sit -> uat_ready
-> human_uat -> release_ready -> awaiting_release -> deployment_approved
-> deployed -> hypercare -> done
```

Each transition checks the exact revision, state, writer, executor,
capability, target, expiry, revocation, and required evidence immediately
before mutation. Implementation, local commit, push or pull request, merge,
release, deployment, service action, external synchronization, and template
promotion remain separate approvals.

Human UAT establishes acceptance of meaning and usability that deterministic
tests cannot prove. A model may prepare UAT evidence but cannot accept its own
UAT.

## Authority and transaction layer

The runtime protocol consists of:

- `.exocortex/scripts/orchestrate_work_item.py` for orientation, routing, and
  guarded work-item operations;
- `.exocortex/scripts/authority_guard.py` for registered executors and exact
  one-time capabilities;
- JSON schemas for work items, approvals, reservations, transitions,
  capabilities, registries, and external-sync policy;
- `.exocortex/local/protocol/` for project-local immutable transactions and
  idempotency records.

The guard verifies exact allowed paths at the high-level entry point, not only
inside leaf helpers. Accepted transitions and their checkpoint records are one
durable operation. Invalid attempts fail before partial state is written.

## External-action architecture

`.exocortex/scripts/egress_guard.py` separates inspection, immutable staging,
and sending:

1. An exact local inspection capability is accepted before source content is
   opened or hashed.
2. A second capability binds digest, size, class, source, object path, and
   descriptor before immutable local staging.
3. A human reviews that descriptor and separately approves one destination,
   method, digest, executor, and expiry.
4. Send-time checks occur before payload access and again immediately before
   transport.

Without the complete chain, the system does not inspect outward content, read
credentials, initialize a destination, open the payload for delivery, spawn a
transport, or make a network call. Sends are never retried automatically after
an indeterminate result.

## Installation and update architecture

Installation and update use an exact local template revision plus the approved
SHA-256 of `SHA256SUMS`. The installer verifies the code plane before target
mutation and creates deny-by-default project-local registry and external-sync
policy files when absent.

Updates rehearse in a newly created disposable copy, keep restore material
outside the target, preserve the full data plane and user-modified manifest
files, and revalidate exact authority immediately before apply. Batch and
legacy update paths fail closed.

## Recursive improvement

Recursive improvement is a sequence of separately governed work items:

1. complete a bounded delivery slice;
2. collect deterministic, reviewer, Human UAT, and operational evidence;
3. produce a local retrospective proposal;
4. approve a new isolated work item;
5. implement and verify it under the same controls;
6. rehearse and promote it through separate gates.

A retrospective cannot mutate the protocol, grant a writer lane, accept UAT,
or authorize promotion. This prevents self-approval while allowing evidence to
compound into safer future behavior.

## Security limits

The repository guards are cooperative controls. They do not sandbox an
unrestricted operating-system account or prove that a human signed local JSON.
Host-level bypass prevention requires an external trusted broker plus signed or
attested authority. Until that trust root exists, externally trusted execution
remains an open risk and must be treated accordingly.
