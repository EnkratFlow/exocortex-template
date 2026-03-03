---
name: daily-end
description: Complete end-of-day workflow review
disable-model-invocation: true
---

## Scope
✅ MAY WRITE (only these files, nothing else):
- `.exocortex/SESSION_CONTEXT.md`
- `.exocortex/TODO.md`
- `.exocortex/LESSONS.md`
- `.exocortex/OPEN_DECISIONS.md`
- `.exocortex/control/INTERRUPTS.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If you notice something outside `.exocortex/` that looks like it needs fixing, capture it as an interrupt — do not touch it.

**Read `.exocortex/AI_BOOTSTRAP.md` immediately.** It contains the complete command protocol and step execution rules.

**Then execute this command:** Run the steps in `.exocortex/commands/daily-end.json` in order (AI_BOOTSTRAP section 3, Step Execution Protocol). Run shell steps, use their outputs for AI steps, then present any user_choice options.
