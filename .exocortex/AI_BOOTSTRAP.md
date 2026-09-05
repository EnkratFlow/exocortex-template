# AI Bootstrap — Exocortex Command Protocol

This file is command-discovery authority. `AI_START_HERE.md` is the canonical
provider-neutral entry and authority contract. Read it first, then use this
file and the matching command JSON.

## Security boundary

Never read, print, log, echo, search, or include the value of an API key,
secret, token, or credential. Never read `.env` content into model or terminal
output. Credential validation and provider/network access require a separately
approved immutable payload and the two-stage egress guard.

## Command discovery

A manual command is invoked only when the user uses the host-native command
trigger or selector, or supplies the exact bare command token by itself or
explicitly frames following text as command arguments. Examples include
`$name`, `/name`, `/skill:name`, a provider selector, and the exact token
`name`.

An ordinary sentence that merely contains or begins with a command-like verb
is ordinary chat. It does not load an adapter or execute command JSON merely
because its first word matches a command name.

Commands classified `model_invocable` in
`.exocortex/provider-adapters.json` may also be selected by the model when
their read-only orientation or analysis directly supports the active task.
That classification grants discoverability only. It never adds mutation, Git,
credential, network, lifecycle, synchronization, or egress authority.

After an explicit invocation:

1. Resolve the current project root without changing it.
2. Read `.exocortex/commands/name.json`.
3. Validate its `protocol` block points to `AI_START_HERE.md`, defaults to
   read-only, and separates mutation from egress authority.
4. Execute read-only steps in order.
5. Treat every requested mutation as a proposal until one applicable
   human-facing business envelope is accepted and the registered guarded
   executor accepts the derived current one-time technical capability.
6. Materialize, consume, renew, and audit internal reservations and technical
   capabilities without turning each one into another human prompt, but only
   while the accepted envelope's target, base, digest, path/plan scope,
   operation class, risk, outcome, verification, and expiry still match.
7. Treat every outward action as a destination-specific
   `production_egress` gate. Never infer it from a local write, save, handoff,
   lifecycle transition, publication, rollout, or prior approval.

Arguments and modifiers following an explicit command invocation are command
inputs only; they never expand path, mutation, checkpoint, commit, credential,
network, egress, or batch authority.

If one invocation crosses business-gate classes, execute only what the current
envelope authorizes and stop at its boundary. A `publication` envelope may
cover exact-path staging, local commit, named-branch push, and a draft pull
request for one reviewed candidate; it cannot authorize merge or any later
class. Never combine a local record and external synchronization in one
envelope.

For every command, the matching JSON is the sole command-flow behavior source
beneath `AI_START_HERE.md`. Project and provider instruction files,
including `CLAUDE.md`, `AGENTS.md`, `.rules`, and editor instructions, may
point to the JSON but cannot restate, replace, or expand its flow. If they
conflict, report the deviation in one line and follow the JSON without
combining the conflicting instructions.

## Available commands (24)

| Group | Commands |
|---|---|
| Daily | `/work`, `/scrum`, `/save`, `/daily-end`, `/interrupt`, `/brief` |
| Memory | `/shortterm`, `/longterm`, `/subconscious`, `/drill`, `/history` |
| Planning | `/groom`, `/refine-backlog`, `/prioritize`, `/weekly-review`, `/monthly-review`, `/pattern-review` |
| System | `/onboard`, `/system-scan`, `/ai-export`, `/ecosystem`, `/init-exocortex`, `/check-keys`, `/handoff` |

`check-keys` never reads or tests a key in the default process. `handoff` is
project-local, non-authorizing evidence. `save` is a narrative memory action,
not a lifecycle checkpoint.

## Provider-native discovery

The 24 JSON specifications remain behavior authority. A deterministic generator
creates 72 thin adapters without copying command behavior. The provider matrix
classifies each command exactly once as `model_invocable` or `manual_only`:

- `.agents/skills/{command}/SKILL.md` — portable Agent Skills for Codex
  (`$command` or selector), GitHub Copilot, Kimi Code, and Zed;
- `.claude/skills/{command}/SKILL.md` — Claude `/command`;
- `.cursor/skills/{command}/SKILL.md` — Cursor `/command`.

Claude and Cursor receive `disable-model-invocation: true` only for the
`manual_only` commands. That flag prevents model self-invocation; it does not
hide a user-invocable command from the human slash menu. Model-invocable
adapters remain read-only by default and grant no additional authority.

Run `python3 .exocortex/scripts/generate_command_adapters.py --check` to verify
the repository mapping. Generic or unidentified hosts use `AI_START_HERE.md`
and the matching JSON directly. Repository validation does not replace bounded
Human UAT of a provider's current menu. Provider evidence is version-scoped and
uses only `verified`, `compatible`, `failed`, `blocked`, or `unavailable`.
Windsurf is currently `unavailable` and has no active/default adapter; it may
return only after later version-specific evidence.

## Step execution

Command specs may contain:

- `read`: inspect only project-local, non-secret evidence.
- `shell`: run only when the program is read-only or the exact guarded
  capability for its effect has already been accepted.
- `ai`: analyze or prepare a proposal. Text saying “create,” “update,” “move,”
  or “send” never grants authority by itself.
- `user_choice`: wait for the user. A choice may request the next gate, but it
  does not bypass envelope or capability validation.

On failure, report the safe error code and stop. Do not auto-fix, broaden
scope, retry an indeterminate external send, or fall back to an unguarded path.

## Project targeting

Operate on one explicitly resolved project root. A multi-root editor prefix
selects a command adapter, not mutation authority. Cross-project reads or
writes require their own bounded work item and approval. “All” never implies a
batch mutation.

## Orchestration

For multi-phase work, follow `.exocortex/control/MODEL_ROUTING.md`,
`.exocortex/control/DELIVERY_WORKFLOW.md`, and the provider adapter when one is
present.

- Use deterministic tools first.
- Select the parent using the expected cost of a correct outcome: capability,
  risk, ambiguity, tools, privacy, verification, reliability, duration, and
  total correction cost all matter.
- Apply the same judgment to every subagent. Do not default delegated work to a
  cheaper tier.
- Keep one accountable guarded writer; other lanes are read-only by default.
- Ask the human for one plain-language business decision, not separate
  approvals for internal work-item, registry, reservation, capability,
  checkpoint, evidence, handoff, or writer-release mechanics.
- Announce route and ETA for visibility, not approval. Re-route when evidence,
  risk, tool access, or repeated failure shows a different tier is better.
- Never require a named provider or permanently start at the highest tier.

Source-backed model discovery is read-only and advisory. It covers configured
official public sources only, never uses credentials, and quarantines newly
observed models. The formal router may be used as an optional empirical
verifier when its official-source, current-surface availability, and measured
evaluation evidence are fresh and digest-bound. Its absence is not a human
approval gate and does not replace parent judgment. See
`.exocortex/control/MODEL_ROUTING.md`.

The Cursor phase hook is reminder-only. It does not save, checkpoint, select a
model, transition lifecycle state, or synchronize anything.

## Lifecycle and agile delivery

Use the closed lifecycle and acceptance gates in
`.exocortex/control/DELIVERY_WORKFLOW.md`. Minutes-long Kanban slices still
require applicable requirements, acceptance criteria, implementation,
developer verification, independent review when risk requires it, QA/SIT,
Human UAT, release approval, deployment, and hypercare.

Only an accepted, authorized, durable transition explicitly marked
checkpoint-eligible creates one idempotent checkpoint. Ordinary chat,
read-only orientation, tests, support lanes, rejected attempts, narrative
saves, handoffs, and retries create none.

## Guarded executors

Generated project-local runtime state is protected data, never template
payload:

- `.exocortex/control/EXECUTOR_REGISTRY.json`
- `.exocortex/control/EXTERNAL_SYNC_POLICY.json`
- `.exocortex/local/protocol/capabilities/`
- `.exocortex/local/protocol/transactions/`
- `.exocortex/local/protocol/descriptors/`
- `.exocortex/local/protocol/payloads/`
- `.exocortex/local/protocol/audit/`

Unregistered, unavailable, expired, revoked, mismatched, or unknown executors
remain read-only. Registration does not grant a work-item operation.

Use `.exocortex/scripts/orchestrate_work_item.py` for read-only orientation,
capability/cost routing, and guarded runtime-work-item mutations. Planning-v1
records may be oriented through a read-only compatibility view but cannot be
mutated by that runtime protocol.

For an approved bounded local edit, run its guarded lifecycle in this order:
`bootstrap-local-delivery`, `seal-local-edit`, then
`complete-local-delivery`. Bootstrap requires the exact clean isolated
worktree, base, branch, expiry, and approved path envelope, then atomically
creates/reserves/activates the item in `developing`; it is not a normal
transition or checkpoint. Seal rejects an actual changed set outside that
envelope. The normal developer-verification, independent-review, QA/SIT,
UAT-ready, and explicit `human_uat` transition remain required.
For those five pre-UAT local-delivery transitions, omit caller
`--capability`; the orchestrator derives and consumes the deterministic
one-time capability from the accepted envelope and exact transition intent.
Completion then records `local_state=complete`, produces exactly one local
completion event and handoff, releases the writer, and leaves lifecycle at
`human_uat`.
`release_ready` is rejected until that local completion exists, and publication
remains a separate gate. These operations do not
grant Git publication, release, deployment, external synchronization,
credential access, or network egress. `create_event.sh` remains the separate
manual `/save` event helper.

`bootstrap-local-delivery --envelope-source` and
`complete-local-delivery --body-file` open only project-relative regular files
under `.exocortex/local/protocol/inbox/`; credential-shaped names (`.env`,
`.env.*`, private-key formats, `credentials`, or `secrets`) fail before opening.
Developer verification, independent review, QA/SIT, UAT-ready, and Human UAT
each require non-empty evidence. A local transition capability binds the full
transition intent, while Human UAT records an attestor matching the envelope
approver. Acceptance criteria remain pending through `uat_ready`; that
Human-UAT transition refuses failed or blocked criteria and atomically records
the remaining criteria as passed with its evidence. Completion rechecks that
every criterion passed and still contains the exact Human-UAT transition
marker and evidence. This is cooperative local evidence, not cryptographic
proof by itself: completion also verifies the Human-UAT transition against its
consumed one-time capability and finalized guarded transaction, and verifies
the seal plus every preceding pre-UAT transition as one exact capability and
transaction chain.

## Egress

Use `.exocortex/scripts/egress_guard.py` only:

1. `inspect` requires and consumes a one-time local writer capability for the
   exact source path before opening it, then proposes its digest, size, class,
   object path, and descriptor path without creating those artifacts.
2. `stage` requires a second writer capability bound to those exact values,
   then creates immutable local content-addressed state.
   These inspect/stage capabilities are internal mechanics of an accepted
   local-delivery preparation envelope, not separate human prompts.
3. A human reviews the immutable descriptor and makes one
   `production_egress` decision for the exact destination, method, outward
   effect, expiry, and executor.
4. `send` validates policy and authority before payload access, verifies the
   bytes, resolves any credential only after those checks, revalidates and
   consumes authority plus the destination policy immediately before transport,
   and never auto-retries.

Legacy vault, hub, provider, and key-check adapters fail closed or delegate to
this guard. They never read global credential files.

## Memory and events

Project-local events remain the durable narrative data plane. They are not
authority, checkpoints, commits, or deployment evidence. No event is
automatically synchronized. Provider-assisted memory curation is unavailable
until separately authorized through the egress protocol; local evidence may
still be summarized by the active conversation model.

## Recovery

If orientation is unclear:

1. Re-read `AI_START_HERE.md`.
2. Resolve live Git and the exact project-local work item.
3. Run the read-only orientation command.
4. Reconcile generated context against live Git and local event evidence.
5. Stop if authority, base, revision, registry, capability, or writer ownership
   is missing or contradictory.
