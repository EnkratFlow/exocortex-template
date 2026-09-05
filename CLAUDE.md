# Claude adapter

Read `AI_START_HERE.md` before substantive action and follow its read order, authority, routing, delivery, save/checkpoint, egress, and approval-gate rules.

For manual commands, `.exocortex/commands/<name>.json` is the sole command-flow behavior source. This file may point to that specification but cannot restate or override it; if they conflict, report the deviation and follow the JSON without combining instructions.

This is a thin provider adapter. It does not independently grant authority. Without an exact current approval, registered guarded executor, and writer reservation when applicable, remain read-only. Never read or expose secret values or `.env` contents.

## Resource-aware verification

Prefer focused checks while developing. Run the complete safety suite once for
an unchanged release candidate in CI or on an explicitly provisioned runner.
Never bind test policy to a private hostname, machine specification, workload,
or remembered capacity. If a heavy local run is necessary, inspect current
capacity, state its expected duration, and use only an authorized runner.
