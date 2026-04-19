  # GitHub Copilot Instructions

---
## ⛔ SECURITY RULE — NEVER VIOLATE

**NEVER read, print, log, echo, grep, cat, or include the VALUE of any API key, secret, or token in any chat message, code snippet, tool output, or terminal command output.**

This includes:
- Running `cat`, `grep`, `echo`, or any command that outputs key values to stdout
- Hardcoding key values into any Python, shell, or JS snippet you write
- Reading `.env` files with tools that return their contents

To test a key: write a shell script to `/tmp/`, run it, return only `valid`/`invalid`. The key value must never appear in your context or output.

If you are about to read or display a key value — **stop and refuse**.

---

Read `.exocortex/reference/MEMORY.md` at session start for the project memory entry point.

---

## Command Protocol

When the user types any of these commands (with or without `/`), execute the corresponding `.exocortex/commands/<name>.json` step sequence:

### Daily Workflow
| Command | Purpose |
|---------|---------|
| `/work` | Load context, see what to work on |
| `/scrum` | Daily standup (yesterday/today/blockers) |
| `/save` | Save work state before breaks |
| `/daily-end` | End of day review |
| `/interrupt` | Capture ideas without breaking flow |
| `/brief` | Quick status check |

### Memory
| Command | Purpose |
|---------|---------|
| `/shortterm` | 7-31 day semantic memory |
| `/longterm` | 31+ day compressed memory |
| `/subconscious` | Cross-cutting pattern detection |
| `/drill <topic>` | Deep-dive on a specific topic |
| `/history` | Search older events (7+ days) |

### Planning
| Command | Purpose |
|---------|---------|
| `/groom` | Process interrupts to backlog/TODO |
| `/refine-backlog` | Promote backlog items to TODO |
| `/prioritize` | Reorder TODO items |
| `/weekly-review` | Weekly planning & review |
| `/monthly-review` | Monthly strategic review |

### System
| Command | Purpose |
|---------|---------|
| `/onboard` | Read and understand the codebase before working |
| `/system-scan` | Repository health check |
| `/ai-export` | Generate system understanding document |
| `/ecosystem` | Cross-project activity view |
| `/init-exocortex` | Initialize exocortex for a new project |
| `/check-keys` | Validate all API keys — run `bash .exocortex/scripts/check_keys.sh`, display output verbatim. Never read key values. |

Full command schemas: `.exocortex/commands/*.json` — read the relevant JSON for exact steps before executing any command.
