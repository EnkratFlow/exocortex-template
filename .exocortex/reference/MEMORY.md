# Project Memory – [PROJECT_NAME]

This folder contains the canonical memory for this project.

**Workflow Commands:** All workflow commands (/save, /work, /history, /groom, etc.) are defined as JSON specs in:
→ `.exocortex/commands/*.json` (one file per command)
→ `.exocortex/COMMAND_SYSTEM.md` (schema reference and full command index)
→ Referenced automatically via `.cursorrules` in Cursor
→ Load once per session in VS Code: "Read .cursorrules"

**AI Persona & Commands:** The AI assistant is configured as a senior multidisciplinary expert. Quick help:
→ `QUICK_REFERENCE.md` - Fast lookup for commands and when to use them
→ `PERSONA_AND_COMMANDS.md` - Complete documentation of persona and all commands

---

## Reading Order

Before making any changes, read these files in order:

1. **PROJECT_MEMORY.md** — System purpose, philosophy, and non-obvious constraints.
2. **SESSION_CONTEXT.md** — Current focus, open questions, and frozen areas.
3. **ESSENTIAL_FILES.md** — Where core truth lives vs reference vs tests.
4. **LESSONS.md** — Project-specific lessons learned and anti-patterns to avoid.
5. **OPEN_DECISIONS.md** (if exists) — Unresolved decisions affecting architecture, logic, QA strategy, or product direction.

**Rule:** If you have not read these, do not make changes.

If work discovers new tasks, risks, or follow-ups, the agent MUST update `.exocortex/TODO.md`.

**Note:** If an agent is instructed to "read memory", "load memory", "use project memory", or similar, this file is the intended entry point.

---

**Last Updated:** [DATE]
