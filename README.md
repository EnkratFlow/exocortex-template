# Exocortex v3

> A portable memory system for developers and AI assistants that never forgets context.

> **📚 Full Documentation**: For comprehensive architecture, user guides, and system details, see [.exocortex/README.md](.exocortex/README.md)

---

## What is This?

The **Exocortex** is an external memory system for your development projects. It helps you (and AI coding assistants) maintain context, track decisions, capture lessons, and manage daily work — across sessions, machines, and editors.

**Think of it as:** Your project's external brain that remembers what you're working on, what you've learned, and what needs to be done.

---

## Install (One Command)

```bash
cd /path/to/your-project
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash
```

Or with a project name:

```bash
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash -s "my-project"
```

**The installer will:**
1. Download the latest exocortex template
2. Copy `.exocortex/` and editor pointer files to your project
3. Replace all placeholders with your project name
4. Make scripts executable
5. Optionally set up API keys for AI memory features
6. Update `.gitignore` to protect secrets

**Editor pointer files created:**
- `.cursorrules` → Cursor (thin pointer to AI_BOOTSTRAP.md)
- `CLAUDE.md` → Claude Code (thin pointer to AI_BOOTSTRAP.md)
- `.github/copilot-instructions.md` → VS Code Copilot (thin pointer to AI_BOOTSTRAP.md)
- `.windsurfrules` → Windsurf (thin pointer to AI_BOOTSTRAP.md)

**Cursor commands & rules:**
- Template includes `.cursor-example/` with 20 exocortex commands & rules
- Installer automatically:
  - Creates `.cursor/` from template if you don't have one
  - Keeps `.cursor-example/` for reference if you already have `.cursor/`
- This prevents overwriting your existing Cursor setup

---

## Manual Install

```bash
# Clone template
git clone https://github.com/EnkratFlow/exocortex-template.git /tmp/exocortex

# Copy to your project
cp -r /tmp/exocortex/.exocortex /path/to/your-project/
cp /tmp/exocortex/.cursorrules /path/to/your-project/

# Initialize
cd /path/to/your-project
bash init-project.sh

# Clean up
rm -rf /tmp/exocortex
```

---

## What's Included

```
.cursorrules                              ← Thin pointer (Cursor auto-loads)
CLAUDE.md                                 ← Thin pointer (Claude Code auto-loads)
.windsurfrules                            ← Thin pointer (Windsurf auto-loads)
.github/copilot-instructions.md           ← Thin pointer (VS Code Copilot auto-loads)
.cursor-example/                          ← Cursor commands & rules (20 commands)
  ├── commands/                           ← Exocortex workflow commands
  │   ├── work.md, save.md, ...           ← One file per command
  └── rules/                              ← Cursor rules for project bootstrap
      └── 05-project-bootstrap.mdc
.exocortex/
  ├── AI_BOOTSTRAP.md                     ← HEAVY — single source of truth
  ├── COMMAND_SYSTEM.md                   ← Schema reference & full command index
  ├── PERSONA_AND_COMMANDS.md             ← AI persona & mode documentation
  ├── MEMORY_TIERS.md                     ← Memory tier architecture
  ├── PROJECT_MEMORY.md                   ← [CUSTOMIZE] System purpose & constraints
  ├── SESSION_CONTEXT.md                  ← Current work state (auto-generated)
  ├── TODO.md                             ← [CUSTOMIZE] Daily task board
  ├── LESSONS.md                          ← Lessons learned
  ├── OPEN_DECISIONS.md                   ← Unresolved decisions
  ├── commands/                           ← 20 JSON command specs
  │   ├── work.json, save.json, ...       ← One file per command
  ├── control/                            ← Project control center
  │   ├── INTERRUPTS.md                   ← Capture lane for ideas
  │   ├── BACKLOG.md                      ← Items under investigation
  │   ├── ROADMAP.md                      ← Strategic planning
  │   ├── QA_STRATEGY.md                  ← [CUSTOMIZE] QA procedures
  │   └── ...
  ├── docs/                               ← System documentation
  ├── events/                             ← Append-only work events
  ├── reference/                          ← Quick reference files
  │   ├── MEMORY.md                       ← Memory entry point
  │   ├── ESSENTIAL_FILES.md              ← [CUSTOMIZE] File location map
  │   └── ...
  └── scripts/                            ← Automation
      ├── _api_helpers.py                 ← Shared API module
      ├── get_*_memory.py                 ← AI memory scripts (4 tiers)
      ├── drill_memory.py                 ← Topic deep-dive
      └── *.sh                            ← Shell automation
```

---

## 20 Workflow Commands

### Daily
| Command | Purpose |
|---------|---------|
| `/work` | Load context, see what to work on |
| `/scrum` | Daily standup |
| `/save` | Save progress before breaks |
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
| `/history` | Search older events |

### Planning
| Command | Purpose |
|---------|---------|
| `/groom` | Process interrupts |
| `/refine-backlog` | Promote backlog → TODO |
| `/prioritize` | Reorder TODO |
| `/weekly-review` | Weekly planning |
| `/monthly-review` | Monthly strategic review |

### System
| Command | Purpose |
|---------|---------|
| `/system-scan` | Repository health check |
| `/ai-export` | Generate system doc |
| `/ecosystem` | Cross-project view |
| `/init-exocortex` | Bootstrap new project |

---

## Four-Tier Memory System

| Tier | Window | Purpose | Script |
|------|--------|---------|--------|
| **RIGHT NOW** | 0–7 days | Current work events | `get_rightnow_memory.py` |
| **SHORT-TERM** | 7–31 days | Semantic themes & patterns | `get_shortterm_memory.py` |
| **LONG-TERM** | 31+ days | Compressed context | `get_longterm_memory.py` |
| **SUBCONSCIOUS** | All events | Cross-cutting patterns, emotional valence | `get_subconscious_memory.py` |

Memory scripts use OpenAI (primary) with Anthropic fallback. Requires API key in `.exocortex/.env`.

---

## Daily Workflow

### Morning (2 minutes)
1. Type `/work` — loads context, shows next task
2. Pick ONE task from TODO
3. Start coding

### During Work
- Focus on your task
- Got an idea? → `/interrupt` (< 1 minute capture, keep working)
- Before a break? → `/save`

### End of Day (5 minutes)
1. Type `/daily-end`
2. Review proposed updates
3. Approve structural changes only

### Weekly
- `/groom` → process interrupts
- `/refine-backlog` → promote ready items
- `/prioritize` → reorder TODO

---

## After Installation

1. **Customize** `.exocortex/PROJECT_MEMORY.md` — describe your system
2. **Map files** in `.exocortex/reference/ESSENTIAL_FILES.md`
3. **Add tasks** to `.exocortex/TODO.md`
4. **Start working** with `/work`

### For Cursor Users

If you have existing Cursor commands/rules, the installer will copy exocortex commands to `.cursor-example/` instead of overwriting your `.cursor/` directory. You can:
- Keep using your existing setup (exocortex still works via `.cursorrules`)
- Manually merge commands from `.cursor-example/` if desired
- Delete `.cursor-example/` if not needed

---

## Requirements

- **git** (for installation)
- **bash** (macOS/Linux — Windows WSL works too)
- **OpenAI API key** (optional, for AI memory features)
- **Works with:** Cursor, VS Code + Copilot, Claude Code, Windsurf, any AI that reads files
- Each editor gets a thin pointer file that auto-loads → reads `AI_BOOTSTRAP.md` → full system

---

## License

MIT — use freely, no attribution required (but appreciated).
