# AI Bootstrap — Exocortex Command Protocol

> **Read this first.** This is the single source of truth for the exocortex command system.
> Any AI agent (Cursor, VS Code Copilot, Claude, Windsurf, etc.) should follow these rules when the user types a `/command`.

**After reading this file, also read:**
→ `.exocortex/reference/MEMORY.md` (project memory entry point and reading order)

---

## 1. Command Discovery

When the user types a command (`/work`, `work`, `/save`, `save`, `/scrum`, etc.):

1. **Strip the `/` prefix** if present → `work`
2. **Look for:** `.exocortex/commands/{command}.json`
3. **If found:** Execute via the step protocol below
4. **If not found:** Tell the user — all valid commands have JSON specs

Commands work **with or without** the `/` prefix:
- `/work` = `work` = execute `work.json`
- `/save` = `save` = execute `save.json`
- `/drill supabase` = `drill supabase` = execute `drill.json` with arg "supabase"

---

## 2. All 20 Commands

### Daily Workflow
| Command | Purpose |
|---------|---------|
| `/work` | Load context, see what to work on |
| `/scrum` | Daily standup (yesterday/today/blockers) |
| `/save` | Save work state before breaks |
| `/daily-end` | End of day review |
| `/interrupt` | Capture ideas without breaking flow |
| `/brief` | Quick status check |

### Memory (AI-powered)
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

**Command schemas:** `.exocortex/commands/*.json` (one file per command)
**Command index:** `.exocortex/COMMAND_SYSTEM.md`

---

## 3. Step Execution Protocol

Each command JSON has a `steps` array. Execute steps **in order**.

### Step type: `shell`
```json
{
  "type": "shell",
  "command": "python3 .exocortex/scripts/get_rightnow_memory.py",
  "description": "Curate RIGHT NOW memory",
  "outputs": { "right_now_section": "AI-curated episodic memory" }
}
```
- **Run the command** in the terminal
- **Capture output** — assign to the named output variable
- **If it fails:** Show the error and ask user yes/no to continue

### Step type: `ai`
```json
{
  "type": "ai",
  "action": "Format and display the work brief",
  "inputs": ["right_now_section", "shortterm_memory"],
  "context": "Display sections verbatim, add git state..."
}
```
- **You (the AI) do this step** — read the `action` and `context` fields
- **Use outputs from previous steps** as inputs
- **Follow the context instructions** exactly

### Step type: `user_choice`
```json
{
  "type": "user_choice",
  "options": ["A) Start next task", "B) Commit first", "C) Something else"]
}
```
- **Present the options** to the user
- **Wait for their choice** before proceeding

### Step type: `read`
```json
{
  "type": "read",
  "files": [".exocortex/control/INTERRUPTS.md"],
  "description": "Load current interrupts list"
}
```
- **Read the file(s)** and hold the content for later steps

---

## 3.1 Multi-Root Workspace Rule

In a multi-root workspace (multiple repos open), the IDE prefix (e.g. `enkratflow-rag-api/save`) only determines which command spec is loaded. It does **not** determine which repo the command runs in.

Before running any command's shell steps, determine the target repo:

1. **User specifies in message** (e.g. "/save exocenter" or "/save all") — use that.
2. **File is focused** — use the workspace root that contains it.
3. **Session context** — if the AI modified files in specific repos during this session, list them by name and number, then offer "all" or pick by number/name (e.g. "This session touched 3 repos: 1. exocenter, 2. rag-api, 3. pkb-api. Save to all 3, or pick by number/name?"). The user should never need to remember repo names.
4. **Neither** — ask: "Which repo should this run in?" and list the workspace roots.

Run **every** shell step with the target repo's absolute path as the working directory.

For `/save` and `/daily-end`: accept "all" or comma-separated repo names to run in multiple repos sequentially.

For all other commands: always target a single repo.

This ensures events, SESSION_CONTEXT, TODO updates, and all other exocortex writes go to the correct repo's `.exocortex/`.

---

## 4. Response Format

After executing all steps, show a compact summary:

```
✓ Step 1 name (key data)
✓ Step 2 name (key data)
✓ Step 3 name (key data)

[1-2 line state summary]

[Decision question with options]
```

If a step fails:
```
✓ Steps completed so far
✗ Step N FAILED (reason)

[Fix description]? (y/n)
```

---

## 5. Self-Correction Rules

- **Never auto-fix** without asking
- **Always show** what failed
- **Always ask yes/no** before proceeding
- If user says `y`: do ONLY that fix, then continue
- If user says `n`: stop and wait

---

## 6. Memory System (4-Tier)

The exocortex uses a **4-tier memory** system based on Conway's autobiographical memory model:

| Tier | Time Range | Script | Style |
|------|-----------|--------|-------|
| RIGHT NOW | 0-7 days | `get_rightnow_memory.py` | Vivid episodic — like just sitting back down |
| SHORT-TERM | 7-31 days | `get_shortterm_memory.py` | Semantic themes — "the last few weeks..." |
| LONG-TERM | 31+ days | `get_longterm_memory.py` | Compressed by era — older = broader strokes |
| SUBCONSCIOUS | ALL events | `get_subconscious_memory.py` | Cross-cutting patterns — what you haven't noticed |

**Additional scripts:**
- `get_subconscious_nudge.py` — Single-sentence pattern probe (runs automatically in `/work`)
- `drill_memory.py` — Deep-dive into a specific topic across all events

All Python scripts use a **2-pass Ralph-style self-critique** pipeline:
1. Pass 1: Generate the reconstruction
2. Pass 2: Quality check against format/tone rules, fix issues, output final version

API calls go through `_api_helpers.py` — validates keys, detects auth errors, shows human-readable messages.

---

## 7. Event System

Events are the raw data for memory. Stored in `.exocortex/events/` as markdown files:
- **Filename format:** `YYYY-MM-DD_HH-MM-SS_machine-editor.md`
- **Append-only:** Events are never edited or deleted
- **Created by:** `/save` command (via `create_event.sh`)

---

## 8. File Structure

```
.exocortex/
├── AI_BOOTSTRAP.md              ← YOU ARE HERE — single source of truth
├── .env                         ← API keys (gitignored)
├── .env.example                 ← API key template
├── COMMAND_SYSTEM.md            ← Full command schema reference
├── PERSONA_AND_COMMANDS.md      ← AI persona & mode documentation
├── MEMORY_TIERS.md              ← Memory architecture details
├── PROJECT_MEMORY.md            ← System purpose, philosophy, constraints
├── SESSION_CONTEXT.md           ← Current work state
├── TODO.md                      ← Task board
├── LESSONS.md                   ← Project-specific lessons
├── OPEN_DECISIONS.md            ← Unresolved decisions
├── commands/                    ← 20 JSON command specs
├── control/                     ← Human-controlled planning
│   ├── INTERRUPTS.md            ← Parking lot for ideas
│   ├── BACKLOG.md               ← Investigation items
│   ├── ROADMAP.md               ← Strategic direction
│   └── ...
├── docs/                        ← System documentation
├── events/                      ← Append-only work events
├── reference/                   ← Quick reference files
│   ├── MEMORY.md                ← Memory entry point (read-order guide)
│   ├── ESSENTIAL_FILES.md       ← File location map
│   ├── QUICK_REFERENCE.md       ← Fast lookup
│   └── CHEAT_SHEET.md           ← One-page cheat sheet
└── scripts/                     ← Shell + Python automation
    ├── _api_helpers.py           ← Shared API module
    ├── get_rightnow_memory.py    ← RIGHT NOW (0-7 days)
    ├── get_shortterm_memory.py   ← SHORT-TERM (7-31 days)
    ├── get_longterm_memory.py    ← LONG-TERM (31+ days)
    ├── get_subconscious_memory.py ← SUBCONSCIOUS (all events)
    ├── get_subconscious_nudge.py ← DMN activation nudge
    ├── drill_memory.py           ← Topic deep-dive
    └── *.sh                      ← Shell automation scripts
```

---

## 9. Getting Started

The first command to run is always:

```
/work
```

This loads RIGHT NOW + SHORT-TERM memory, fires a subconscious nudge, reads git state and TODO.md, then presents you with options to start your next task.

---

## 10. Emergency Recovery

If the AI seems to not know workflow commands:
1. Type: "Read `.exocortex/AI_BOOTSTRAP.md`"
2. Confirm it loaded
3. Then proceed with your command

---

**Version:** Exocortex v3
**Last updated:** February 2026
