# Command System — Public-v2 Reference

`AI_START_HERE.md` is the sole entry/authority contract.
`.exocortex/AI_BOOTSTRAP.md` defines command discovery and execution.
`.exocortex/commands/*.json` defines the 24 individual command behaviors.

For each manual command, its matching JSON is the sole command-flow behavior
source beneath `AI_START_HERE.md`. Project and provider instruction files may
point to the specification but must not restate or override its flow. If a
`CLAUDE.md`, `AGENTS.md`, `.rules`, or editor instruction conflicts with the
JSON, report the deviation in one line and follow the JSON without combining
the conflicting instructions.

Every JSON specification contains:

```json
{
  "name": "/command",
  "description": "purpose",
  "protocol": {
    "entry_contract": "AI_START_HERE.md",
    "authority": "exact_capability_required_for_mutation",
    "egress": "separate_destination_specific_authorization",
    "default_role": "read_only"
  },
  "steps": []
}
```

Step text is not authority. A shell or AI step that proposes a mutation runs
only after the registered guarded executor accepts a current, exact, expiring,
revocable, one-time capability for the work item revision, operation, paths,
and target digest. Egress is always a later exact gate.

## Command index

- Daily: `work`, `scrum`, `save`, `daily-end`, `interrupt`, `brief`
- Memory: `shortterm`, `longterm`, `subconscious`, `drill`, `history`
- Planning: `groom`, `refine-backlog`, `prioritize`, `weekly-review`,
  `monthly-review`, `pattern-review`
- System: `onboard`, `system-scan`, `ai-export`, `ecosystem`,
  `init-exocortex`, `check-keys`, `handoff`

`save` records local narrative memory only when authorized. `handoff` records
strict local evidence and never transfers authority. `check-keys` reports that
guarded validation is required without reading credential values.

## Adapter parity

All 24 JSON commands generate into each of three repository adapter families:

- `.agents/skills/{command}/SKILL.md` for portable Agent Skills consumers;
- `.claude/skills/{command}/SKILL.md` for Claude;
- `.cursor/skills/{command}/SKILL.md` for Cursor.

`.exocortex/provider-adapters.json` records provider-specific invocation truth,
and `.exocortex/scripts/generate_command_adapters.py --check` proves the exact
24-name/72-file repository mapping. The matrix classifies every command exactly
once as `model_invocable` or `manual_only`. Generated adapters are thin
delegates to `AI_START_HERE.md`, this bootstrap, and exactly one matching JSON.
Invocation policy changes discoverability only; adapters cannot add command
behavior or authority.

Codex uses `$command` or its skills selector, so the template does not make a
false literal-slash claim for Codex. Generic or unidentified hosts enter through
`AI_START_HERE.md` and the matching JSON until a native repository convention is
verified. Provider-menu visibility remains version-scoped Human UAT evidence.
The matrix uses the closed status vocabulary `verified`, `compatible`, `failed`,
`blocked`, and `unavailable`. Windsurf is unavailable and excluded from the
active/default adapter families.

## Script boundaries

- `orchestrate_work_item.py`: read-only orientation/routing and guarded local
  lifecycle mutations. Its `bootstrap-local-delivery`, `seal-local-edit`, and
  `complete-local-delivery` operations bind one clean isolated worktree to an
  exact base, branch, and path envelope; atomically create/reserve/activate
  the approved item in `developing` without creating a transition/checkpoint;
  seal the actual changed set; then, after the normal verification/review/QA
  gates and explicit `human_uat`, record `local_state=complete`, create exactly
  one local event/handoff, and release the writer while lifecycle stays
  `human_uat`.
- `authority_guard.py`: executor, capability, scope, expiry, revocation, and
  one-time/idempotent consumption checks.
- `egress_guard.py`: immutable payload inspection/staging and exact external
  transport.
- `create_event.sh` and `capture_interrupt.sh`: record project-local state only.
  External delivery is available solely as a distinct guarded egress operation.

The local-delivery operations are cooperative local enforcement. They do not
grant staging, commit, push, release, deployment, service action, external
synchronization, credential access, or network egress. `release_ready` and
publication remain separate gates. `create_event.sh` remains the manual `/save`
helper and is not task-closeout authority.

The bootstrap `--envelope-source` and completion `--body-file` are limited to
project-relative regular files under `.exocortex/local/protocol/inbox/` and
reject credential-shaped names (`.env`, `.env.*`, private-key formats,
`credentials`, or `secrets`) before opening. All five verification/UAT gates
require non-empty evidence; each local transition capability binds the full
transition intent. Human UAT records an attestor matching the envelope
approver. Acceptance criteria remain pending through `uat_ready`; that
Human-UAT transition refuses failed or blocked criteria and atomically records
the remaining criteria as passed with its evidence. Completion rechecks that
every criterion passed and still contains the exact Human-UAT transition
marker and evidence. This is cooperative local evidence, not cryptographic
identity proof; completion also verifies the Human-UAT transition against its
consumed one-time capability and finalized guarded transaction.
- legacy provider/global-install adapters: deny or return a prospective plan.

Unknown commands, missing protocol metadata, stale authority, unregistered
executors, direct provider calls, and implicit batch/cross-project behavior all
fail closed.
