# Command System - Quick Reference

**Status:** Implemented and editor-neutral
**Last updated:** May 2, 2026
**Purpose:** Reliable workflow commands driven by JSON specs.

---

## Source of Truth

When a user types `/work`, `work`, `/save`, `save`, or any other
Exocortex command, the AI should:

1. Read `.exocortex/AI_BOOTSTRAP.md`.
2. Find `.exocortex/commands/{command}.json`.
3. Execute the JSON steps in order.
4. Treat the JSON command as the source of truth if an IDE adapter,
   bridge skill, old doc, or memory conflicts with it.

The command system is designed to work from any AI-capable editor that
can read project files and run shell commands.

See also:

- `.exocortex/docs/IDE_INTEGRATION_GUIDE.md` for Cursor, Claude,
  VS Code Copilot, Codex, Windsurf, Zed, and unknown editor setup.
- `.exocortex/AI_BOOTSTRAP.md` for the full execution protocol,
  security rules, multi-root workspace rules, and orchestration notes.

---

## Available Commands

### Daily Workflow

| Command | Purpose | Key scripts/files |
|---------|---------|-------------------|
| `/work` | Load context and identify next task | `get_rightnow_memory.py`, `get_shortterm_memory.py`, `get_subconscious_nudge.py` |
| `/scrum` | Daily standup | `run_scrum.sh` |
| `/save` | Save current work state checkpoint | `create_event.sh`, `sync_event_to_vault.sh`, `save.json` |
| `/daily-end` | End of day review | `run_end_day.sh` |
| `/interrupt` | Quick-capture idea during work | `capture_interrupt.sh` |
| `/brief` | Quick status check | `run_brief_status.sh` |

### Memory

| Command | Purpose | Key scripts/files |
|---------|---------|-------------------|
| `/shortterm` | 7-31 day semantic memory | `get_shortterm_memory.py` |
| `/longterm` | 31+ day compressed memory | `get_longterm_memory.py` |
| `/subconscious` | Cross-cutting pattern detection | `get_subconscious_memory.py` |
| `/drill <topic>` | Deep-dive into a specific topic | `drill_memory.py` |
| `/history` | Search older events | AI reads `events/` |

### Planning And Review

| Command | Purpose | Type |
|---------|---------|------|
| `/groom` | Process interrupts into backlog/TODO/delete/keep decisions | AI-guided |
| `/refine-backlog` | Promote backlog items to executable TODOs | AI-guided |
| `/prioritize` | Reorder TODO by strategic importance | AI-guided |
| `/weekly-review` | End-of-week review and interrupt triage | AI-guided |
| `/monthly-review` | Directional review and course correction | AI-guided |
| `/pattern-review` | Analyze recurring friction and propose skills or memory updates | AI-guided |

### System

| Command | Purpose | Type |
|---------|---------|------|
| `/onboard` | Read and understand the codebase before working | AI-guided |
| `/system-scan` | Full read-only system health check | AI read-only |
| `/ai-export` | Generate a project-generic system understanding document | AI writes report |
| `/ecosystem` | Cross-project activity view from Exocortex hub | AI read-only |
| `/init-exocortex` | Bootstrap Exocortex for a new project | AI creates files |
| `/check-keys` | Validate API key status, purpose, and location without exposing values | `check_keys.sh`, `check_keys.py` |

---

## Backlog Flow

Exocortex deliberately separates ideas from executable work:

1. `/interrupt` captures ideas into `.exocortex/control/INTERRUPTS.md`.
2. `/groom` reviews those interruptions and moves investigation-worthy
   items into `.exocortex/control/BACKLOG.md`.
3. `/refine-backlog` promotes ready items into `.exocortex/TODO.md`.
4. `/prioritize` orders `.exocortex/TODO.md`.

This prevents every thought from becoming a task immediately.

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

Step types:

- `shell` - run a bash or Python command and capture output.
- `ai` - the AI reads the action/context and performs the instruction.
- `read` - read files and hold the content for later steps.
- `user_choice` - present options and wait for user choice.

If a shell step fails, show the failure and ask before continuing.

---

## Editor Adapters

Known adapter surfaces:

- Cursor: `.cursor/commands/*.md`, `.cursor/rules/*.mdc`, `.cursor/hooks/`
- Claude Code: `CLAUDE.md`, `.claude/skills/*/SKILL.md`
- VS Code Copilot: `.github/copilot-instructions.md`, `.github/skills/*/SKILL.md`
- Windsurf: `.windsurfrules`
- Codex: universal adapter prompt today; native `.agents/skills/*`
  bridges are planned but not shipped in this template yet.
- Zed/other editors: copy the universal adapter prompt from
  `.exocortex/docs/IDE_INTEGRATION_GUIDE.md`.

Adapters should stay thin. They should point the AI at
`.exocortex/AI_BOOTSTRAP.md` and `.exocortex/commands/*.json`, not
duplicate command behavior.

---

## Plan Orchestration

For multi-phase work, use `.cursor/rules/plan-orchestrate.mdc` where
Cursor supports rules and subagent hooks. The protocol decomposes work
into named phases, routes phases to appropriate model lanes, and saves
between phases.

Outside Cursor, the same orchestration guidance can be followed
manually by any AI agent that reads the rule file, but the Cursor
`subagentStop` hook is Cursor-specific.

---

## Script Architecture

Python scripts (`.py`) handle memory summaries and key checks.
Bash scripts (`.sh`) handle workflow automation, event creation,
context regeneration, and vault/hub sync.

Important scripts:

- `create_event.sh` - record work sessions.
- `sync_event_to_vault.sh` - optionally sync events to the RAG API.
- `generate_context.sh` - rebuild `SESSION_CONTEXT.md` from events.
- `capture_interrupt.sh` - quick interrupt capture.
- `groom_interrupts.sh` - review captured interrupts.
- `run_scrum.sh` - daily standup data.
- `run_end_day.sh` - end-of-day data.
- `check_keys.sh` / `check_keys.py` - validate keys without exposing values.

---

## File Layout

```text
.exocortex/
├── AI_BOOTSTRAP.md              # command protocol and security rules
├── COMMAND_SYSTEM.md            # this quick reference
├── commands/                    # JSON command specifications
├── control/                     # human-controlled planning and backlog
│   ├── INTERRUPTS.md
│   ├── BACKLOG.md
│   ├── ROADMAP.md
│   └── QA_STRATEGY.md
├── docs/                        # system documentation and IDE guide
├── events/                      # append-only event storage
├── reference/                   # quick reference files
├── scripts/                     # automation scripts
├── PROJECT_MEMORY.md            # project purpose and constraints
├── TODO.md                      # daily task board
├── LESSONS.md                   # lessons learned
└── SESSION_CONTEXT.md           # current work state
```
