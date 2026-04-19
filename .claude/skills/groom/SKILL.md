---
name: groom
description: Process interrupts to backlog or TODO
disable-model-invocation: true
---

## Scope
✅ MAY WRITE (only these files, nothing else):
- `.exocortex/control/INTERRUPTS.md`
- `.exocortex/control/BACKLOG.md`
- `.exocortex/TODO.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If you notice something outside `.exocortex/` that looks like it needs fixing, capture it as an interrupt — do not touch it.

**Read `.exocortex/AI_BOOTSTRAP.md` immediately.** It contains the complete command protocol and step execution rules.

**Then execute this command:** Run the steps in `.exocortex/commands/groom.json` in order (AI_BOOTSTRAP section 3, Step Execution Protocol). Run shell steps, use their outputs for AI steps, then present any user_choice options.

## Scope
✅ MAY WRITE (only these files, nothing else):
- `.exocortex/control/INTERRUPTS.md`
- `.exocortex/control/BACKLOG.md`
- `.exocortex/TODO.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If you notice something outside `.exocortex/` that looks like it needs fixing, capture it as an interrupt — do not touch it.

1) Load Interrupts:
   Read `.exocortex/control/INTERRUPTS.md`
   Show all items captured since last groom
   Group by type:
   - Bugs
   - Ideas
   - Wild Thoughts
   - Concerns
   - Questions

2) Process Each Item:
   For each interrupt, ask: "[Type] - [Title]: What should we do?"

   Options:
   - A) Add to BACKLOG for investigation
   - B) Add to TODO (urgent/clear enough to work on)
   - C) Delete (not relevant)
   - D) Keep in INTERRUPTS (decide later)

3) Propose Changes:
   Show exactly what will be written:

   BACKLOG.md additions:
   - Item 1: [title and captured details]

   TODO.md additions:
   - Item X: [as new task]

   INTERRUPTS.md changes:
   - Remove processed items
   - Keep deferred items

   Ask: "Ready to apply these changes?"

4) Write:
   If approved:
   1. Update BACKLOG.md (add new items)
   2. Update TODO.md (add urgent items)
   3. Update INTERRUPTS.md (remove processed)
   4. Confirm all writes successful

   Summary: "✅ Grooming complete
   [X] items moved to BACKLOG
   [Y] items moved to TODO
   [Z] items deleted
   [W] items deferred

   Next: 'refine-backlog' to promote ready items"
