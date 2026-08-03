# Project Memory – [PROJECT_NAME]

This folder contains the canonical memory for this project.

**Workflow Commands:** The exact 24 commands are defined as JSON specs in:
→ `.exocortex/commands/*.json` (the single behavior source)
→ `.exocortex/COMMAND_SYSTEM.md` (schema reference and full command index)
→ `.exocortex/provider-adapters.json` (provider invocation and migration matrix)
→ `.agents/skills/`, `.claude/skills/`, and `.cursor/skills/` (72 generated thin command adapters)

Every provider starts at `AI_START_HERE.md`. Codex invokes a skill with
`$command` or its selector; other supported surfaces use the syntax recorded in
the provider matrix. An unidentified host reads the matching JSON directly and
does not receive a native-menu claim. Windsurf is currently unavailable and is
not part of active/default installation.

**AI Persona & Commands:** The AI assistant is configured as a senior multidisciplinary expert. Quick help:
→ `.exocortex/reference/QUICK_REFERENCE.md` - Fast lookup for commands and when to use them
→ `.exocortex/PERSONA_AND_COMMANDS.md` - Complete documentation of persona and all commands

---

## Reading Order

Before making any changes, read these files in order. Paths are relative to the
project root, not to this folder:

1. **`.exocortex/PROJECT_MEMORY.md`** — System purpose, philosophy, and non-obvious constraints.
2. **`.exocortex/SESSION_CONTEXT.md`** (if exists) — Current focus, open questions, and frozen areas.
3. **`.exocortex/reference/ESSENTIAL_FILES.md`** — Where core truth lives vs reference vs tests.
4. **`.exocortex/LESSONS.md`** — Project-specific lessons learned and anti-patterns to avoid.
5. **`.exocortex/OPEN_DECISIONS.md`** (if exists) — Unresolved decisions affecting architecture, logic, QA strategy, or product direction.

**Rule:** If you have not read these, do not make changes.

If work discovers new tasks, risks, or follow-ups, report them in chat. Update
`.exocortex/TODO.md` only when the current task authorizes that local write.

**Note:** If an agent is instructed to "read memory", "load memory", "use project memory", or similar, this file is the intended entry point.

---

**Last Updated:** [DATE]
