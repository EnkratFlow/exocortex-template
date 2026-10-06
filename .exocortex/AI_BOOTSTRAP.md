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
5. Reuse applicable owner approval for ordinary project edits and saves. Only
   protocol-managed mutations require registered guarded execution and the
   exact current capability; follow AI_START_HERE section 3.
6. Materialize, consume, renew, and audit internal reservations and technical
   capabilities without turning each one into another human prompt, but only
   while the accepted envelope's target, base, digest, path/plan scope,
   operation class, risk, outcome, verification, and expiry still match.
7. Guarded payload delivery requires its destination-specific authority.
   Ordinary Git operations against this project’s remote follow section 3;
   a local save never implies a push, synchronization or deployment.

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

## Available commands (26)

| Group | Commands |
|---|---|
| Daily | `/work`, `/scrum`, `/save`, `/daily-end`, `/interrupt`, `/brief` |
| Memory | `/shortterm`, `/longterm`, `/subconscious`, `/drill`, `/history` |
| Planning | `/groom`, `/refine-backlog`, `/prioritize`, `/weekly-review`, `/monthly-review`, `/pattern-review`, `/preflight`, `/orchestrate` |
| System | `/onboard`, `/system-scan`, `/ai-export`, `/ecosystem`, `/init-exocortex`, `/check-keys`, `/handoff` |

`check-keys` never reads or tests a key in the default process. `handoff` is
project-local, non-authorizing evidence. `save` is a narrative memory action,
not a lifecycle checkpoint.

## Provider-native discovery

The 26 JSON specifications remain behavior authority. A deterministic generator
creates 78 thin adapters without copying command behavior. The provider matrix
classifies each command exactly once as `model_invocable` or `manual_only`:

- `.agents/skills/{command}/SKILL.md` — portable Agent Skills for Codex
  (`$command` or selector), GitHub Copilot, Kimi Code, and Zed;
- `.claude/skills/{command}/SKILL.md` — Claude `/command`;
- `.cursor/skills/{command}/SKILL.md` — Cursor `/command`.

Claude and Cursor receive `disable-model-invocation: true` only for the
`manual_only` commands. That flag prevents model self-invocation; it does not
hide a user-invocable command from the human slash menu. Model-invocable
adapters remain read-only by default and grant no additional authority.

When adapter validation is requested, use the shared launcher operation
`script generate_command_adapters.py --check` to verify
the repository mapping. Generic or unidentified hosts use `AI_START_HERE.md`
and the matching JSON directly. Repository validation does not replace bounded
Human UAT of a provider's current menu. Provider evidence is version-scoped and
uses only `verified`, `compatible`, `failed`, `blocked`, or `unavailable`.
Windsurf is currently `unavailable` and has no active/default adapter; it may
return only after later version-specific evidence.

## Local command execution

Read this routing rule once per session and reuse it for the same checkout.
On native Windows use PowerShell and the step's `windows_command`; do not run
its POSIX `command` as well. On macOS/Linux or an explicitly selected WSL/Git
Bash shell use `command`. Never infer native PowerShell syntax from Bash text.
For an operation named in AI steps, use the same launcher:

- Windows: `& .\.exocortex\scripts\run_exocortex.ps1 OPERATION ARGUMENTS`
- macOS/Linux: `bash .exocortex/scripts/run_exocortex.sh OPERATION ARGUMENTS`

The launcher resolves only configured/PATH Python, never scans disks or installs
software. `EXOCORTEX_PYTHON` may name an explicit machine-local interpreter.
Windows remembers its validated executable in the current PowerShell session;
a new shell resolves it again using at most three bounded probes. No runtime
path is committed or written by read-only commands. For approved specialist
helpers, use `script helper_name.py ARGUMENTS` through the same launcher.
Pass arguments as separate literal values; use `--body-file` for saved prose.
A missing runtime is one clear stop, not permission to search for unrelated
CLIs, change execution policy, install tools, or keep trying alternative shells.
Routine local commands never discover `gh`, check authentication/releases,
contact providers or invoke install/update verification. Git is used only when
the command needs repository evidence; report unavailable evidence honestly.

Reuse a helper's evidence within that invocation. Do not rerun entry checks,
coverage or Git scans already included in its result. Read-only chat/help and
planning need no blanket runtime preflight. Recheck when a new command requires
it or the checkout/evidence changes; do not claim old coverage is still fresh.
Generated context remains dated supporting evidence, never complete truth.

## Step execution

Command specs may contain:

- `read`: inspect only project-local, non-secret evidence.
- `shell`: select exactly one platform command. Read-only programs need no
  capability; ordinary local writes reuse owner approval. Actual guarded
  operations still require their exact capability.
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

For multi-phase work, follow `.exocortex/control/ORCHESTRATION.md`,
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

Executor registration, writer reservations, and one-time capabilities govern
the guarded runtime operations only: work-item mutations through
`orchestrate_work_item.py`, guarded template updates through
`scripts/safe-update.sh --apply`, and payload delivery through
`egress_guard.py`. For those operations, unregistered, unavailable, expired,
revoked, mismatched, or unknown executors remain read-only, and registration
does not grant a work-item operation. Ordinary project work is not a guarded
operation: editing, tests, commits, pushing a branch to the project's own
remote, pull requests, and the manual `/save` and `/interrupt` commands need
no registration and no capability.

A private project's own trusted executors may hold long-lived registrations;
a year is reasonable. A registration that expires within a day turns the
first write of every day into a re-approval and protects nothing.

Use `.exocortex/scripts/orchestrate_work_item.py` for read-only orientation,
capability/cost routing, and guarded runtime-work-item mutations. Planning-v1
records may be oriented through a read-only compatibility view but cannot be
mutated by that runtime protocol.

For an approved protocol-managed local-delivery work item, run its lifecycle in this order:
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

Egress is payload delivery through the guard to a configured destination
(vault, hub, provider, and key-check adapters). Git operations against the
project's own remote, including branch pushes and pull requests, are ordinary
version control and are not governed by the guard or by
`EXTERNAL_SYNC_POLICY.json`.

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
2. Resolve live Git; resolve a runtime work item only for protocol-managed work.
3. Reuse the current command’s orientation evidence; do not rerun a scan.
4. Reconcile generated context against live Git and local event evidence.
5. For protocol-managed operations, stop if authority, base, revision, registry,
   capability, or writer ownership is missing or contradictory. Ordinary work
   follows section 3 without creating these records.

## Generated memory freshness

Use the current command's coverage result; never repeat its scan on entry.
When a command needs verified coverage and has not collected it, use the
shared launcher operation `refresh --check --json`. Treat exit 1 as stale and
exit 2 as inspection failure. Otherwise describe context as dated evidence,
not verified fresh. Reconcile source events and live Git without silently
writing memory. Approved saves use the launcher `save --body-file` operation;
after a saved-event refresh failure, retry only `refresh --apply` if authorized.
Guarded completion/handoff transactions do not refresh implicitly.
Durable lessons, decisions, tasks and patterns need reviewed proposals; see
`.exocortex/docs/memory-system.md`. No provider is called by default.
