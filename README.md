# Exocortex Template

> A portable memory system for developers and AI assistants that never forgets context

## What is This?

The **Exocortex** is an external memory system for your development projects. It helps you (and AI coding assistants) maintain context, track decisions, capture lessons, and manage daily work without losing momentum.

**Think of it as:** Your project's external brain that remembers what you're working on, what you've learned, and what needs to be done.

## Why Use the Exocortex?

**Without it:**
- ❌ Waste time re-explaining context to AI assistants
- ❌ Forget why you made important decisions
- ❌ Repeat the same mistakes
- ❌ Lose track of what you were working on after breaks
- ❌ Context switch penalties when switching between projects

**With it:**
- ✅ Pick up exactly where you left off, even after weeks away
- ✅ AI assistants understand your project immediately
- ✅ Decisions and constraints are documented automatically
- ✅ Lessons learned prevent repeating mistakes
- ✅ Clear task board shows exactly what to work on

## Quick Start

### 1. Copy Template to Your Project

```bash
# Clone this template into your project
cp -r template-export/.exocortex /path/to/your-project/
cp -r template-export/docs/control /path/to/your-project/docs/
cp template-export/.cursorrules /path/to/your-project/
```

### 2. Run Initialization Script

**On macOS/Linux:**
```bash
cd /path/to/your-project
bash template-export/init-project.sh
```

**On Windows (PowerShell):**
```powershell
cd C:\path\to\your-project
.\template-export\init-project.ps1
```

The script will:
- Prompt for your project name and parent project (optional)
- Replace all `[PROJECT_NAME]`, `[PARENT_PROJECT]`, and `[DATE]` placeholders
- Clean up backup files
- Show you next steps

### 3. Customize Core Files

After initialization, customize these files for your project:

1. **`.exocortex/PROJECT_MEMORY.md`** - Describe your system, constraints, and design philosophy
2. **`.exocortex/ESSENTIAL_FILES.md`** - Map where core files live in your codebase
3. **`.exocortex/TODO.md`** - Add your first real tasks

That's it! You're ready to start working with the Exocortex.

---

## What's Included

```
template-export/
├── README.md                          ← You are here
├── init-project.sh                    ← Bash initialization script
├── init-project.ps1                   ← PowerShell initialization script
├── .cursorrules                       ← Lightweight pointer to AI instructions
├── .exocortex/                        ← Memory system
│   ├── README.md                      ← System guide (keep as-is)
│   ├── AI_INSTRUCTIONS.md             ← Full workflow commands (1900+ lines)
│   ├── MEMORY.md                      ← Entry point for AI
│   ├── PROJECT_MEMORY.md              ← System constraints & philosophy
│   ├── SESSION_CONTEXT.md             ← Current work state (generated from events)
│   ├── TODO.md                        ← Daily task board
│   ├── LESSONS.md                     ← Lessons learned & anti-patterns
│   ├── ESSENTIAL_FILES.md             ← File location map
│   ├── OPEN_DECISIONS.md              ← Unresolved decisions
│   ├── TEMPLATE_STRUCTURE.md          ← Template reference
│   ├── EVENT_SYSTEM_USAGE.md          ← Event system quick guide
│   ├── PHASE_1_EVENT_SYSTEM_PLAN.md   ← Implementation details
│   ├── PHASE_2_TRANSITION_PLAN.md     ← Future RAG integration
│   ├── events/                        ← Append-only work events
│   │   └── .gitkeep                   ← Keep directory in git
│   └── scripts/
│       ├── generate_context.sh        ← Regenerate SESSION_CONTEXT from events
│       └── archive_events.sh          ← Archive old events (7+ days)
└── docs/control/                      ← Control system
    ├── README.md                      ← Control system guide
    ├── INTERRUPTS.md                  ← Capture lane for ideas
    ├── BACKLOG.md                     ← Items under investigation
    └── ROADMAP.md                     ← Strategic planning (optional)
```

---

## 🎯 New in v2.0: Event-Based Memory System

**The Problem This Solves:**
- ❌ Using VS Code and Cursor simultaneously would overwrite SESSION_CONTEXT.md
- ❌ Lost work context when switching between editors
- ❌ No cross-machine sync without git conflicts

**The Solution:**
- ✅ **Append-only event files** - Each `/save` creates a new event file (no overwrites)
- ✅ **Multi-editor support** - VS Code and Cursor work simultaneously without conflicts
- ✅ **Auto-regeneration** - SESSION_CONTEXT.md regenerated from events automatically
- ✅ **Cross-machine sync** - Git-based (Phase 1) → RAG API-based (Phase 2)
- ✅ **Comprehensive history** - All work events preserved in timeline

**How It Works:**
```
/save → Creates event file → Regenerates SESSION_CONTEXT
/work → Regenerates SESSION_CONTEXT from events → Shows current work
/history → Searches older events (7+ days)
```

**Files:**
- `.exocortex/events/*.md` - Append-only event files (last 7 days)
- `.exocortex/scripts/generate_context.sh` - Regenerates SESSION_CONTEXT from events
- `.exocortex/SESSION_CONTEXT.md` - Generated file (do not edit manually)

**Documentation:**
- [EVENT_SYSTEM_USAGE.md](.exocortex/EVENT_SYSTEM_USAGE.md) - Quick usage guide
- [PHASE_1_EVENT_SYSTEM_PLAN.md](.exocortex/PHASE_1_EVENT_SYSTEM_PLAN.md) - Implementation details
- [PHASE_2_TRANSITION_PLAN.md](.exocortex/PHASE_2_TRANSITION_PLAN.md) - Future RAG integration

---

## Daily Workflow

### Morning (5 minutes)

1. Type `/work` in your AI assistant (or read `.exocortex/SESSION_CONTEXT.md`)
2. Review what you were working on
3. Check your task board (`.exocortex/TODO.md`)
4. Pick ONE task to work on (move to "In Progress")

### During Work

- **Focus on ONE task** from TODO.md at a time
- **Got an idea?** Capture it in `docs/control/INTERRUPTS.md` and keep working (don't act on it now)
- **Before breaks:** Type `/save` to checkpoint your state
- **Code, test, commit:** Normal development work

### End of Day (5-10 minutes)

1. Type `/daily-end` command
2. Review proposed memory updates
3. Approve if structural changes occurred (new constraints, lessons, decisions)
4. Move completed tasks to Done

**Note:** You don't need to update memory every day. Normal progress doesn't require memory updates.

---

## Key Principles

### 1. Memory is for Structure, Not Progress
Don't update memory files for normal code changes. Only update when you discover:
- New system constraints or boundaries
- Important design decisions
- Lessons learned from mistakes
- Changes in project direction

### 2. TODO is Source of Truth for Daily Work
- Work only from `.exocortex/TODO.md`
- Keep only ONE item "In Progress" at a time
- Don't pull tasks directly from roadmap or backlog

### 3. Interrupts are Parking Lot, Not Backlog
- Capture quickly in `docs/control/INTERRUPTS.md`
- Don't act on interrupts during work
- Process weekly (or when you feel like it)

### 4. Decisions Belong in Memory
- **Unresolved:** `.exocortex/OPEN_DECISIONS.md`
- **Resolved:** `.exocortex/PROJECT_MEMORY.md` (if they create constraints)

### 5. Lessons Prevent Repetition
- Add after painful debugging or discovering patterns
- Read before major changes
- Include what went wrong, why, what worked, and how to prevent

---

## Workflow Commands

These commands work with AI assistants that support the `.cursorrules` file:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/work` | Load context and see what to work on | Morning, after breaks, context switches |
| `/scrum` or `/dsu` | Daily standup briefing | Start of day for status update |
| `/interrupt` | Quick capture during work | When ideas or issues come up mid-task |
| `/save` | Save work state checkpoint | Before breaks, end of session |
| `/groom` | Process interrupts to backlog/TODO | Weekly cleanup |
| `/refine-backlog` | Promote backlog items to TODO | Weekly planning |
| `/daily-end` | End of day workflow | End of work session |
| `/prioritize` | Reorder TODO items | When priorities change |

**See `.cursorrules` for complete command definitions**

---

## File Descriptions

### Memory System (`.exocortex/`)

| File | Purpose | When to Update |
|------|---------|----------------|
| `MEMORY.md` | Entry point for AI (navigation) | Rarely (already generic) |
| `PROJECT_MEMORY.md` | System constraints & philosophy | When constraints or direction change |
| `SESSION_CONTEXT.md` | Current work state | End of day (if needed) |
| `TODO.md` | Daily task board | Throughout the day as tasks progress |
| `LESSONS.md` | Lessons learned | After painful debugging or discoveries |
| `ESSENTIAL_FILES.md` | File location map | When file structure changes |
| `OPEN_DECISIONS.md` | Unresolved decisions | When decisions discovered or resolved |

### Control System (`docs/control/`)

| File | Purpose | When to Update |
|------|---------|----------------|
| `INTERRUPTS.md` | Quick capture during work | During work (capture quickly) |
| `BACKLOG.md` | Items under investigation | Weekly grooming |
| `ROADMAP.md` | Strategic planning | Monthly or quarterly |

---

## Integration with AI Assistants

### For GitHub Copilot / Cursor

1. Copy `.cursorrules` to your project root
2. Type workflow commands (e.g., `/work`, `/save`, `/daily-end`)
3. AI will read memory files and guide you through workflows

### For Other AI Assistants

Instruct your AI to:
1. Read `.exocortex/MEMORY.md` first (entry point)
2. Follow the reading order specified
3. Check relevant memory files before making changes
4. Update memory only when structural changes occur

---

## Customization Tips

### Minimal Setup
Start with just these files:
- `.exocortex/PROJECT_MEMORY.md` (describe your system)
- `.exocortex/TODO.md` (track tasks)
- `.exocortex/SESSION_CONTEXT.md` (current state)

Add other files as needed when complexity grows.

### For Solo Developers
- Skip `ROADMAP.md` if you don't need strategic planning
- Focus on `TODO.md` and `LESSONS.md`
- Update memory sparingly (only when needed)

### For Teams
- Use `OPEN_DECISIONS.md` for team decisions
- Update `PROJECT_MEMORY.md` when constraints discovered
- Review `LESSONS.md` in team meetings
- Use `ROADMAP.md` for alignment

### Parent Project Integration
If your project is part of a larger ecosystem:
- Set `[PARENT_PROJECT]` during initialization
- Reference parent project governance in `MEMORY.md`
- Link to parent lessons in `LESSONS.md`

---

## Documentation

**Internal Docs:**
- `.exocortex/README.md` - Complete system guide
- `docs/control/README.md` - Control system guide
- `.exocortex/TEMPLATE_STRUCTURE.md` - File relationships

**Workflow Guides:**
- `.cursorrules` - Command definitions
- See `.exocortex/README.md` for detailed daily/weekly workflows

---

## Troubleshooting

### "AI doesn't read memory files"
- Make sure `.cursorrules` is in your project root
- Try saying "read memory" or "load project memory" explicitly
- Provide the path: "Read .exocortex/MEMORY.md"

### "Too much overhead"
- Start minimal: just PROJECT_MEMORY.md and TODO.md
- Don't update memory for normal progress
- Only capture lessons after truly painful experiences

### "Files are out of date"
- That's okay! The Exocortex is a tool, not a requirement
- Update when it helps you, skip when it doesn't
- Focus on TODO.md for daily work

### "Placeholders still showing"
- Run the initialization script (`init-project.sh` or `init-project.ps1`)
- Or manually find/replace `[PROJECT_NAME]`, `[PARENT_PROJECT]`, `[DATE]`

### "Script fails with special characters in project name"
- **Best practice**: Use simple alphanumeric names with hyphens or underscores
- **Examples**: `my-project`, `awesome_app`, `project123`
- **Avoid**: Special characters like `&`, `/`, `\`, `(`, `)`, `[`, `]`, `.`, `*`
- If needed, manually edit files after initialization

---

## Credits

This template was created from the [trading-journal](https://github.com/EnkratFlow/trading-journal) project by EnkratFlow.

The Exocortex memory system was developed to help developers maintain context across long breaks and complex projects, and to make AI assistants more effective by providing them with project memory.

---

## License

MIT License - use this template freely in your projects, no attribution required (but appreciated!).

---

## Testing the Template

### Quick Test

Want to test the template before using it in your real project?

```bash
# Create a test directory
mkdir ~/test-exocortex && cd ~/test-exocortex

# Copy the template files
cp -r /path/to/template-export/.exocortex .
cp -r /path/to/template-export/docs .
cp /path/to/template-export/.cursorrules .
cp /path/to/template-export/init-project.sh .

# Run initialization
bash init-project.sh
# Enter: my-test-app
# Enter: (leave blank for no parent)
# Confirm: y

# Verify placeholders were replaced
head -3 .exocortex/MEMORY.md
# Should show: "# Project Memory – my-test-app"

# Check for leftover placeholders (should return nothing)
grep -r "\[PROJECT_NAME\]" .exocortex/ docs/control/
grep -r "\[DATE\]" .exocortex/ docs/control/
```

**Expected results:**
- All `[PROJECT_NAME]` replaced with your project name
- All `[PARENT_PROJECT]` replaced (or "None")
- All `[DATE]` replaced with current date
- No `.bak` files remaining
- All files readable and properly formatted

---

## Next Steps

1. ✅ Run initialization script (`init-project.sh` or `init-project.ps1`)
2. ✅ Customize `PROJECT_MEMORY.md` with your system description
3. ✅ Map your files in `ESSENTIAL_FILES.md`
4. ✅ Add your first tasks to `TODO.md`
5. ✅ Start working with `/work` command

**Welcome to the Exocortex. May you never lose context again.**
