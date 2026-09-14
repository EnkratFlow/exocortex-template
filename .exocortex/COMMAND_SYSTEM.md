# Command System — Public-v2 Reference

`AI_START_HERE.md` is the sole entry/authority contract.
`.exocortex/AI_BOOTSTRAP.md` defines command discovery and execution.
`.exocortex/commands/*.json` defines the 24 individual command behaviors.

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
24-name/72-file repository mapping. Generated adapters are manual-only thin
delegates to `AI_START_HERE.md`, this bootstrap, and exactly one matching JSON.
They cannot add command behavior or authority.

Codex uses `$command` or its skills selector, so the template does not make a
false literal-slash claim for Codex. Generic or unidentified hosts enter through
`AI_START_HERE.md` and the matching JSON until a native repository convention is
verified. Provider-menu visibility remains version-scoped Human UAT evidence.
The matrix uses the closed status vocabulary `verified`, `compatible`, `failed`,
`blocked`, and `unavailable`. Windsurf is unavailable and excluded from the
active/default adapter families.

## Script boundaries

- `orchestrate_work_item.py`: read-only orientation/routing and guarded local
  lifecycle mutations.
- `authority_guard.py`: executor, capability, scope, expiry, revocation, and
  one-time/idempotent consumption checks.
- `egress_guard.py`: immutable payload inspection/staging and exact external
  transport.
- `create_event.sh` and `capture_interrupt.sh`: record project-local state only.
  External delivery is available solely as a distinct guarded egress operation.
- legacy provider/global-install adapters: deny or return a prospective plan.

Unknown commands, missing protocol metadata, stale authority, unregistered
executors, direct provider calls, and implicit batch/cross-project behavior all
fail closed.
