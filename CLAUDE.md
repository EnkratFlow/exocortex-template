# Claude adapter

Read `AI_START_HERE.md` before substantive action and follow its read order, authority, routing, delivery, save/checkpoint, egress, and approval-gate rules.

For manual commands, `.exocortex/commands/<name>.json` is the sole command-flow behavior source. This file may point to that specification but cannot restate or override it; if they conflict, report the deviation and follow the JSON without combining instructions.

This is a thin provider adapter. It does not independently grant authority. Without an exact current approval, registered guarded executor, and writer reservation when applicable, remain read-only. Never read or expose secret values or `.env` contents.

## ⛔ PERFORMANCE — DO NOT RUN FULL TEST SUITES ON KRATO

krato is a base M1 Mac mini: 8 cores, 16GB RAM, not upgradeable. It also
serves the trading journal, the vault pipeline, the krato app, several VS
Code remote sessions, and always-on agent sessions. A parallel test suite
saturates it — on 2026-08-06 one pytest run with five workers took the
machine to load 29.95 (roughly 4x oversubscribed) and made every other
session unresponsive.

Therefore, in this repo:

- **Run targeted tests only.** A single test file or a focused `-k` filter
  is fine. `npm test`, `pytest` with no path, or anything that spawns
  parallel workers across the whole suite is NOT.
- **Let CI run the full suite.** Push the branch; the GitHub Actions
  workflow runs it with proper parallelism and costs krato nothing.
- **For a heavy local run, use the laptop** — a fresh clone there, not this
  machine.
- If you believe a full local run is genuinely necessary, say so and ask
  first. Do not just run it.

This is about shared-machine courtesy, not test quality. Tests still matter;
they just do not run here.
