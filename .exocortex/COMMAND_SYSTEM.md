# Command System - Quick Reference

**Status:** ✅ Implemented (Feb 7, 2026)  
**Purpose:** Reliable, auto-verifying workflow commands

---

## How It Works

**You type:** `/work` or `work`  
**AI:** Reads `.exocortex/commands/work.json` → Executes steps → Auto-verifies → Shows brief

**Key features:**
- Auto-verification after each step
- 6-10 line compact responses
- Yes/no self-correction if step fails
- Works in both Cursor and VS Code

---

## Available Commands

### Workflow Commands
| Command | Purpose | Key Scripts |
|---------|---------|-------------|
| `/work` | Load context, identify next task | `get_rightnow_memory.py`, `get_shortterm_memory.py` |
| `/save` | Save current work state checkpoint | `save_work_state.sh` |
| `/scrum` | Daily standup (yesterday/today/blockers) | `run_scrum.sh` |
| `/daily-end` | End of day review | `run_end_day.sh` |
| `/interrupt` | Quick-capture idea during work | `capture_interrupt.sh` |
| `/groom` | Process captured interrupts | `groom_interrupts.sh` |
| `/brief` | Quick status check | `run_brief_status.sh` |

### Memory Commands
| Command | Purpose | Key Scripts |
|---------|---------|-------------|
| `/shortterm` | 7-31 day semantic memory | `get_shortterm_memory.py` |
| `/longterm` | 31+ day compressed memory | `get_longterm_memory.py` |
| `/subconscious` | Cross-cutting pattern detection (ALL events) | `get_subconscious_memory.py` |
| `/drill <topic>` | Deep-dive into a specific topic | `drill_memory.py` |
| `/history` | Search older events by keyword or date | AI-driven (reads events/) |

### Planning & Review Commands
| Command | Purpose | Type |
|---------|---------|------|
| `/prioritize` | Reorder TODO.md by strategic importance | AI-guided |
| `/refine-backlog` | Process backlog: promote, defer, or delete | AI-guided |
| `/weekly-review` | End-of-week review and interrupt triage | AI-guided |
| `/monthly-review` | Directional review and course correction | AI-guided |

### System Commands
| Command | Purpose | Type |
|---------|---------|------|
| `/system-scan` | Full read-only system health check | AI (read-only) |
| `/ai-export` | Generate system understanding document from code | AI → writes file |
| `/ecosystem` | Cross-project activity view from EnkratFlow hub | AI (read-only) |
| `/init-exocortex` | Bootstrap .exocortex for a new project | AI → creates files |

---

## Command Schema

All commands use a consistent JSON format:

```json
{
  "name": "/command",
  "description": "What this command does",
  "steps": [
    {
      "type": "shell",
      "command": "script to run",
      "description": "Human-readable step name"
    },
    {
      "type": "ai",
      "action": "What the AI should do",
      "inputs": ["data from previous steps"],
      "context": "Additional instructions"
    },
    {
      "type": "user_choice",
      "options": ["A) Option one", "B) Option two"]
    }
  ]
}
```

**Step types:**
- `shell` — Run a bash or python script
- `ai` — AI processes/formats output or interacts with user
- `user_choice` — Present options and wait for user decision

---

## Script Architecture

**Python scripts** (`.py`) — Call OpenAI/Anthropic with 2-pass Ralph-style self-critique:
- `get_rightnow_memory.py` — Episodic memory (0-7 days)
- `get_shortterm_memory.py` — Semantic memory (7-31 days)
- `get_longterm_memory.py` — Compressed memory (31+ days)
- `get_subconscious_memory.py` — Pattern detection (all events, no time filter)
- `drill_memory.py` — Topic-specific deep-dive (all events)

**Bash scripts** (`.sh`) — Utility and workflow automation:
- `create_event.sh` — Record work sessions
- `capture_interrupt.sh` — Quick interrupt capture
- `groom_interrupts.sh` — Review captured interrupts
- `run_scrum.sh` — Daily standup routine
- `run_end_day.sh` — End of day review
- `run_brief_status.sh` — Quick status dashboard
- `save_work_state.sh` — Checkpoint current state
- `generate_context.sh` — Rebuild SESSION_CONTEXT.md from events
- `detect_work_state.sh` — Git state as JSON
- `get_next_task.sh` — Parse TODO.md for next task
- `post_to_hub.sh` — Post to EnkratFlow ecosystem hub

---

## File Layout

```
.exocortex/
├── .env                        # API keys (OpenAI, Anthropic)
├── commands/                   # JSON command specifications
│   ├── work.json               # Context loading + next task
│   ├── save.json               # Checkpoint current state
│   ├── scrum.json              # Daily standup
│   ├── daily-end.json          # End of day review
│   ├── interrupt.json          # Quick interrupt capture
│   ├── groom.json              # Process interrupts
│   ├── brief.json              # Quick status
│   ├── shortterm.json          # 7-31 day memory
│   ├── longterm.json           # 31+ day memory
│   ├── subconscious.json       # Pattern detection (all events)
│   ├── drill.json              # Topic deep-dive
│   ├── history.json            # Search events
│   ├── prioritize.json         # Reorder TODO
│   ├── refine-backlog.json     # Process backlog
│   ├── weekly-review.json      # Weekly review
│   ├── monthly-review.json     # Monthly review
│   ├── system-scan.json        # System health check
│   ├── ai-export.json          # System understanding doc
│   ├── ecosystem.json          # Cross-project view
│   └── init-exocortex.json     # Bootstrap new project
├── scripts/                    # Processing scripts
│   ├── get_rightnow_memory.py  # Python (OpenAI 2-pass)
│   ├── get_shortterm_memory.py # Python (OpenAI 2-pass)
│   ├── get_longterm_memory.py  # Python (OpenAI 2-pass)
│   ├── get_subconscious_memory.py # Python (OpenAI 2-pass)
│   ├── drill_memory.py        # Python (OpenAI 2-pass)
│   └── *.sh                   # Bash utility scripts
├── control/                    # Human-controlled planning
│   ├── INTERRUPTS.md          # Parking lot for ideas
│   ├── BACKLOG.md             # Non-executable investigation
│   ├── DAILY_WORKFLOW.md      # Operating procedures
│   └── ROADMAP.md             # Strategic planning
├── events/                     # Append-only event storage
└── *.md                        # Context and documentation
```

---

## Bootstrap

**Cursor:** Auto-loads `.cursorrules` (zero setup)  
**VS Code:** First message: "read .cursorrules"  
**Then:** All commands work identically in both editors

---

**Last Updated:** February 7, 2026
