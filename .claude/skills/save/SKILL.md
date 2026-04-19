---
name: save
description: Save current work state checkpoint
disable-model-invocation: true
---

## Scope
✅ MAY WRITE (only this file, nothing else):
- `.exocortex/SESSION_CONTEXT.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If you notice something outside `.exocortex/` that looks like it needs fixing, capture it as an interrupt — do not touch it.

**Read `.exocortex/AI_BOOTSTRAP.md` immediately.** It contains the complete command protocol and step execution rules.

**Then execute this command:** Run the steps in `.exocortex/commands/save.json` in order (AI_BOOTSTRAP section 3, Step Execution Protocol). Run shell steps, use their outputs for AI steps, then present any user_choice options.

## Scope
✅ MAY WRITE (only this file, nothing else):
- `.exocortex/SESSION_CONTEXT.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If you notice something outside `.exocortex/` that looks like it needs fixing, capture it as an interrupt — do not touch it.

1) Show current git status and what files changed (read-only).
2) Ask ONE question: "In one sentence, what's your focus right now?"
3) Propose the exact 🟢 RIGHT NOW update for `.exocortex/SESSION_CONTEXT.md`.
4) Do NOT write anything until the user says "approve".
