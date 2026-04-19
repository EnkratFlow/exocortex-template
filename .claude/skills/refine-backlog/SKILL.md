---
name: refine-backlog
description: Promote backlog items to TODO
disable-model-invocation: true
---

## Scope
✅ MAY WRITE (only these files, nothing else):
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

**Then execute this command:** Run the steps in `.exocortex/commands/refine-backlog.json` in order (AI_BOOTSTRAP section 3, Step Execution Protocol). Run shell steps, use their outputs for AI steps, then present any user_choice options.

## Scope
✅ MAY WRITE (only these files, nothing else):
- `.exocortex/control/BACKLOG.md`
- `.exocortex/TODO.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If you notice something outside `.exocortex/` that looks like it needs fixing, capture it as an interrupt — do not touch it.

1) Load Backlogs:
   Read:
   - `.exocortex/control/BACKLOG.md`
   - `.exocortex/TODO.md`

   Show summary of each

2) Refine Backlog Items:
   For each BACKLOG item (one at a time):

   Ask: "Is [Item Title] ready to promote to TODO?"

   User answers:
   - A) Yes, promote to TODO
   - B) Not yet, still investigating
   - C) Defer (decide later)
   - D) Delete (not relevant)

   If YES - PROMOTE:
   - Ask: "What's the executable task title?"
   - Ask: "What's the scope (what needs to be done)?"
   - Save as new TODO item

   If NOT YET:
   - Ask: "What needs to happen before it's ready?"
   - Update BACKLOG item with notes

3) Mark Completed:
   Check TODO.md for [x] marked items

   For each completed item:
   Ask: "Should I remove [Item] from TODO?"

   If yes: remove it

4) Propose Changes:
   Show exactly what will be updated:

   BACKLOG.md:
   - Promoted items removed
   - Deferred items updated with notes
   - Remaining items shown

   TODO.md:
   - New promoted items added
   - Completed [x] items removed
   - Current list shown

   Ask: "Ready to apply these changes?"

5) Write:
   If approved:
   1. Update BACKLOG.md
   2. Update TODO.md
   3. Confirm writes successful

   Summary: "✅ Backlog refined"

   Next: `prioritize` to reorder TODO
