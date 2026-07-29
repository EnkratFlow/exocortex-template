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

Command JSON is behavior authority beneath `AI_START_HERE.md`. Provider and
editor bridges are thin adapters and cannot expand it.

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
creates 72 manual-only thin adapters without copying command behavior:

- `.agents/skills/{command}/SKILL.md` — portable Agent Skills for Codex
  (`$command` or selector), GitHub Copilot, Kimi Code, and Zed;
- `.claude/skills/{command}/SKILL.md` — Claude `/command`;
- `.cursor/skills/{command}/SKILL.md` — Cursor `/command`, with
  `disable-model-invocation: true`.

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
- Select the least-expensive available parent capable of owning the complete
  risk and integration judgment.
- Delegate bounded evidence tasks to cheaper capable workers.
- Keep one accountable guarded writer; other lanes are read-only by default.
- Ask the human for one plain-language business decision, not separate
  approvals for internal work-item, registry, reservation, capability,
  checkpoint, evidence, handoff, or writer-release mechanics.
- Escalate only when evidence shows the current tier is insufficient.
- Never require a named provider or permanently start at the highest tier.

Source-backed model discovery is read-only and advisory. It covers configured
official public sources only, never uses credentials, and quarantines newly
observed models. Route only from fresh, digest-bound official-source,
current-surface availability, and measured evaluation evidence. See
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
