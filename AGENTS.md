# AI agent instructions

Read `AI_START_HERE.md` before any other task instruction. It is the provider-neutral authority and delivery contract for this repository.

Then read `.exocortex/AI_BOOTSTRAP.md` and `.exocortex/reference/MEMORY.md` in the order they specify.

For manual commands, `.exocortex/commands/<name>.json` is the sole command-flow behavior source. This file may point to that specification but cannot restate or override it; if they conflict, report the deviation and follow the JSON without combining instructions.

This file is a thin Codex-compatible adapter. It does not grant mutation, Git, release, deployment, service, credential, external-sync, or promotion authority. Unknown or unattested surfaces remain read-only. Protocol-managed writes and outward actions must pass the registered guarded-executor and exact capability checks described in `AI_START_HERE.md`.

Never read or expose secret values or `.env` contents.

## Resource-aware verification

Prefer focused checks while developing. Run the complete safety suite once for
an unchanged release candidate in CI or on an explicitly provisioned runner.
Never bind test policy to a private hostname, machine specification, workload,
or remembered capacity. If a heavy local run is necessary, inspect current
capacity, state its expected duration, and use only an authorized runner.
