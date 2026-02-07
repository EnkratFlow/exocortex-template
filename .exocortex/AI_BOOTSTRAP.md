# AI Bootstrap — Exocortex Command Protocol

> **Read this first.** This is the portable execution protocol for the exocortex command system.
> Any AI agent (Cursor, VS Code Copilot, Claude, etc.) should follow these rules when the user types a `/command`.

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

## 2. Step Execution Protocol

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

## 3. Response Format

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

## 4. Self-Correction Rules

- **Never auto-fix** without asking
- **Always show** what failed
- **Always ask yes/no** before proceeding
- If user says `y`: do ONLY that fix, then continue
- If user says `n`: stop and wait

---

## 5. Memory System Overview

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

## 6. Event System

Events are the raw data for memory. Stored in `.exocortex/events/` as markdown files:
- **Filename format:** `YYYY-MM-DD_HH-MM-SS_machine-editor.md`
- **Append-only:** Events are never edited or deleted
- **Created by:** `/save` command (via `create_event.sh`)

---

## 7. Key Files

```
.exocortex/
├── AI_BOOTSTRAP.md          ← YOU ARE HERE — execution protocol
├── .env                     ← API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY)
├── commands/                ← JSON command specifications (20 total)
│   └── work.json            ← Start here: context + next task
├── scripts/                 ← Processing scripts
│   ├── _api_helpers.py      ← Shared API call + error handling
│   ├── get_rightnow_memory.py
│   └── ...
├── events/                  ← Append-only work event storage
├── control/                 ← Human-controlled planning docs
│   ├── TODO.md              ← Current task queue
│   ├── INTERRUPTS.md        ← Parking lot for ideas
│   ├── BACKLOG.md           ← Non-executable investigation
│   └── ROADMAP.md           ← Strategic direction
├── COMMAND_SYSTEM.md        ← Full command reference
├── MEMORY_TIERS.md          ← Memory architecture details
└── PERSONA_AND_COMMANDS.md  ← AI persona + all 20 commands listed
```

---

## 8. Getting Started

The first command to run is always:

```
/work
```

This loads RIGHT NOW + SHORT-TERM memory, fires a subconscious nudge, reads git state and TODO.md, then presents the user with options to start their next task.

---

*Last updated: February 2026*
