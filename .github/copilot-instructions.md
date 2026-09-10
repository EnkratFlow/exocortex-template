# GitHub Copilot adapter

Read `AI_START_HERE.md` before substantive action and follow its read order, authority, routing, delivery, save/checkpoint, egress, and approval-gate rules.

This is a thin editor adapter. It does not independently grant authority. Guarded operations (work-item transitions, guarded template updates, guarded egress) require the registered executor and capability checks in `AI_START_HERE.md`. Ordinary project work, including edits, tests, commits, branch pushes to the project's own remote, pull requests, and `/save`, is not guarded and needs no registration.

For manual commands, `.exocortex/commands/<name>.json` is the sole command-flow behavior source after the canonical entry contract has been loaded. This adapter cannot restate or override it; if they conflict, report the deviation and follow the JSON without combining instructions. Never read or expose secret values or `.env` contents.
