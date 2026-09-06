# Exocortex Command Quick Reference

The canonical registry contains exactly 26 commands. Each command begins
read-only, and its JSON specification beneath `.exocortex/commands/` is the
single behavior source. A command name, argument, model statement, or adapter
never grants mutation or egress authority.

For delegation, use `.exocortex/control/MODEL_ROUTING.md`. The public catalog
is advisory; discovery quarantines new entries, and only fresh, digest-bound,
measured, current-surface evidence can admit a model to routing.

## Daily

| Command | Purpose |
|---|---|
| `/work` | Load current context and identify the next bounded task |
| `/scrum` | Prepare a daily standup from project-local evidence |
| `/save` | Draft a local narrative save; it is not a lifecycle checkpoint |
| `/daily-end` | Review the day and prepare a guarded local record request |
| `/interrupt` | Capture an idea, bug, or concern through the guarded workflow |
| `/brief` | Produce a short read-only status view |

## Memory

| Command | Purpose |
|---|---|
| `/shortterm` | Review 7–31 day project-local memory |
| `/longterm` | Review 31–365 day project-local memory |
| `/subconscious` | Detect patterns across project-local events |
| `/drill <topic>` | Deep-dive into one memory topic |
| `/history` | Search or browse older project-local events |

## Planning

| Command | Purpose |
|---|---|
| `/preflight <topic>` | Check relevant project lessons and incidents before work |
| `/orchestrate` | Draft a bounded plan with cost-aware model routing |
| `/groom` | Process captured interrupts |
| `/refine-backlog` | Propose promotion, deferral, or removal of backlog items |
| `/prioritize` | Propose strategic TODO ordering |
| `/weekly-review` | Review weekly delivery evidence and follow-ups |
| `/monthly-review` | Review longer-term direction and course corrections |
| `/pattern-review` | Identify recurring friction and prospective improvements |

## System

| Command | Purpose |
|---|---|
| `/onboard` | Build a read-only mental model of the repository |
| `/system-scan` | Run a read-only system health analysis |
| `/ai-export` | Prepare a guarded system-understanding export request |
| `/ecosystem` | Prepare a read-only cross-project activity view |
| `/init-exocortex` | Propose a guarded Exocortex bootstrap |
| `/check-keys` | Report guarded key-validation requirements without reading values |
| `/handoff` | Prepare or record a strict project-local cross-provider handoff |

## Provider invocation

| Surface | Invocation |
|---|---|
| Codex | `$command` or the skills selector |
| Claude | `/command` |
| Cursor | `/command` |
| GitHub Copilot | `/command` where repository skills are supported |
| Kimi Code | `/skill:{name}` |
| Zed built-in Agent | Skills selector; no literal-slash claim |
| Windsurf | Unavailable; no active/default adapter |
| Generic or unidentified host | Read `AI_START_HERE.md`, then the matching JSON |

Run `python3 .exocortex/scripts/generate_command_adapters.py --check` to verify
the exact 26-name/78-adapter repository mapping. Native provider-menu visibility
still requires bounded Human UAT for the installed provider version. Evidence
statuses are `verified`, `compatible`, `failed`, `blocked`, or `unavailable`.

For the complete protocol, read `AI_START_HERE.md`,
`.exocortex/AI_BOOTSTRAP.md`, and `.exocortex/COMMAND_SYSTEM.md`.
