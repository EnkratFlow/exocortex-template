# Essential Files

## Entry and command authority

- `AI_START_HERE.md` — provider-neutral entry and authority contract
- `.exocortex/AI_BOOTSTRAP.md` — command discovery/execution
- `.exocortex/commands/` — 26 JSON command specifications
- `.exocortex/provider-adapters.json` — provider invocation and migration matrix
- `.exocortex/scripts/generate_command_adapters.py` — deterministic 78-adapter generator/check
- `.agents/skills/` — portable generated Agent Skills
- `.claude/skills/` — generated Claude command skills
- `.cursor/skills/` — generated Cursor command skills alongside preserved persona skills
- `.exocortex/control/MODEL_ROUTING.md` — capability/cost routing
- `.exocortex/model-source-registry.json` — configured official-source evidence
- `.exocortex/model-routing-catalog.json` — advisory reviewed catalog; zero packaged eligibility
- `.exocortex/scripts/model_registry.py` — offline freshness, discovery, and availability validation
- `.exocortex/control/DELIVERY_WORKFLOW.md` — agile lifecycle gates

## Runtime protocol

- `.exocortex/scripts/authority_guard.py`
- `.exocortex/scripts/orchestrate_work_item.py`
- `.exocortex/schemas/local-delivery-envelope.schema.json` — exact clean
  worktree/base/branch/path envelope for guarded local delivery
- `.exocortex/scripts/prepare_update_reconciliation.py`
- `.exocortex/scripts/egress_guard.py`
- `.exocortex/control/EXECUTOR_REGISTRY.json` — generated protected data
- `.exocortex/control/EXTERNAL_SYNC_POLICY.json` — generated protected data
- `.exocortex/local/protocol/` — protected runtime state
- `.exocortex/local/model-routing/` — protected availability, evaluation, and quarantine evidence

## Project-local truth

- `.exocortex/PROJECT_MEMORY.md`
- `.exocortex/LESSONS.md`
- `.exocortex/OPEN_DECISIONS.md`
- `.exocortex/TODO.md`
- `.exocortex/events/`
- `.exocortex/work-items/`

Generated `SESSION_CONTEXT.md` is a convenience view and must be reconciled
against live Git, exact work items, and events.

For an approved file-changing local delivery, the orchestrator performs
`bootstrap-local-delivery`, `seal-local-edit`, and, only after `human_uat`,
`complete-local-delivery`. Bootstrap atomically creates/reserves/activates the
approved item in `developing` from the exact clean worktree/base/branch/path
envelope; it is not a normal transition or checkpoint. After seal, ordinary
developer verification, independent review, QA/SIT, UAT-ready, and explicit
`human_uat` still occur. Completion records `local_state=complete`, writes one
project-local completion event and handoff, and releases the writer while
lifecycle stays `human_uat`; `release_ready` and publication are separate. It
is not authority for commit, push, release, deployment, synchronization,
credential access, or network egress; `create_event.sh` remains manual `/save`.

`bootstrap-local-delivery --envelope-source` and
`complete-local-delivery --body-file` use only project-relative regular files
under `.exocortex/local/protocol/inbox/`; credential-shaped names (`.env`,
`.env.*`, private-key formats, `credentials`, or `secrets`) fail before opening.
Developer verification, independent review, QA/SIT, UAT-ready, and Human UAT
each require non-empty evidence, and every local transition capability binds
the full transition intent. Human UAT records an attestor matching the envelope
approver. Acceptance criteria remain pending through `uat_ready`; that
Human-UAT transition refuses failed or blocked criteria and atomically records
the remaining criteria as passed with its evidence. Completion rechecks that
every criterion passed and still contains the exact Human-UAT transition
marker and evidence. This is cooperative local evidence, not cryptographic
proof of a person's identity. Completion also verifies the Human-UAT transition
against its consumed one-time capability and finalized guarded transaction.
