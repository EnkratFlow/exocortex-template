# Exocortex help

A compact guide to all 30 commands. Use `/help command-name` for more detail.

## Start here

- New to a project? `/onboard` explains its code, memory and unfinished work.
- Returning to a task? `/work` resumes the selected brief and current context.
- New request? `/brief-work` turns it into a brief before implementation.
- Unsure which folder? `/where` identifies this project and its working folders.
- Ready to preserve progress? `/save` prepares a local narrative for saving.
- Want Exocortex versions? `/updates` inspects versions; `release status` reads the cache.
- Need one command explained? `/help command-name` gives focused help.

Local saves do not push to GitHub. Update notices do not install software.
Write actions reuse applicable owner approval; help itself only reads this guide.

For delegation and model choice, use `.exocortex/control/ORCHESTRATION.md`.

## Daily

| Command | Purpose |
|---|---|
| `/work` | Load current context and identify the next bounded task |
| `/scrum` | Prepare a daily standup from project-local evidence |
| `/save` | Draft a local narrative save; it is not a lifecycle checkpoint |
| `/daily-end` | Reflect on the day and prepare a summary to save |
| `/interrupt` | Capture an idea, bug or concern for later triage |
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
| `/brief-work` | Draft, revise, select and review a task brief with explicit local approval |
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
| `/help [command]` | List commands or explain one command without running it |
| `/onboard` | Build a read-only mental model of the repository |
| `/system-scan` | Run a read-only system health analysis |
| `/ai-export` | Prepare a comprehensive system-understanding document |
| `/ecosystem` | Prepare a read-only cross-project activity view |
| `/init-exocortex` | Set up Exocortex for a chosen project |
| `/check-keys` | Review API-key validation requirements without exposing values |
| `/handoff` | Prepare context and next steps for another assistant |
| `/where` | Show this project and its working folders; optionally inspect memory preservation |
| `/updates` | Inspect project versions; `release` manages opt-in notices; `selected` plans and previews chosen projects, then uses per-project guarded approval to apply |

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

Menu availability depends on the host and installed version. For workflow
details, use the matching command or read `.exocortex/COMMAND_SYSTEM.md`.
