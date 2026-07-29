# Essential Files

## Entry and command authority

- `AI_START_HERE.md` — provider-neutral entry and authority contract
- `.exocortex/AI_BOOTSTRAP.md` — command discovery/execution
- `.exocortex/commands/` — 24 JSON command specifications
- `.exocortex/provider-adapters.json` — provider invocation and migration matrix
- `.exocortex/scripts/generate_command_adapters.py` — deterministic 72-adapter generator/check
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
