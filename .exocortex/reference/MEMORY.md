# Project Memory – [PROJECT_NAME]

This folder contains the canonical memory for this project.

**Workflow Commands:** The exact 30 commands are defined as JSON specs in:
→ `.exocortex/commands/*.json` (the single behavior source)
→ `.exocortex/COMMAND_SYSTEM.md` (schema reference and full command index)
→ `.exocortex/provider-adapters.json` (provider invocation and migration matrix)
→ `.agents/skills/`, `.claude/skills/`, and `.cursor/skills/` (90 generated thin command adapters)

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
6. **`.exocortex/planning/MASTER_BRIEF.md`** (if exists) — The active program's full objective, workstreams, decisions, status and approval boundaries. Read any project-local execution record it names as well.

7. **Selected task brief**, when present — run `brief_work.py context`, then `show <id>` from `.exocortex/scripts/`. Load its objective, constraints, criteria and unresolved questions. A stale or ambiguous selection requires explicit reconciliation; missing optional briefs are normal.

**Rule:** If you have not read these, do not make changes.

For a program with a master brief, reread it at session start, after context
compaction or resumption, and before each substantial phase. Reconcile it with
live evidence and current owner instructions. Do not let the newest task,
example, event or inventory replace the whole objective. State the current
slice and its relationship to the overall program before acting. A brief is
context, never new authority. Update it only within authorized memory-edit
scope; handoffs should point to it rather than create competing plans. Missing
optional briefs are normal; a known brief or its pointer becoming unavailable
is an explicit continuity gap. Project briefs are protected project records,
not template release payloads.

Before claiming verified Session Context coverage, use the current command's
coverage result. If no check was collected and verification is needed, run
`refresh --check --json` once through the platform launcher in AI_BOOTSTRAP.md.
Simply reading memory does not require interpreter discovery or a full scan.
A stale or missing receipt requires reconciliation with source events and live
Git. Fresh coverage certifies the generated index only, not the correctness of
handwritten lessons, decisions, or tasks. Never silently regenerate on entry.

If work discovers new tasks, risks, or follow-ups, report them in chat. Update
`.exocortex/TODO.md` only when the current task authorizes that local write.

**Note:** If an agent is instructed to "read memory", "load memory", "use project memory", or similar, this file is the intended entry point.

---

**Last Updated:** [DATE]
