---
name: interrupt
description: Quick capture for ideas, bugs, concerns
disable-model-invocation: true
---

## Scope
✅ MAY WRITE (only this file, nothing else):
- `.exocortex/control/INTERRUPTS.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If the user mentions a bug or issue in code, capture it as an interrupt — do not attempt to fix it.

**Read `.exocortex/AI_BOOTSTRAP.md` immediately.** It contains the complete command protocol and step execution rules.

**Then execute this command:** Run the steps in `.exocortex/commands/interrupt.json` in order (AI_BOOTSTRAP section 3, Step Execution Protocol). Run shell steps, use their outputs for AI steps, then present any user_choice options.

## Scope
✅ MAY WRITE (only this file, nothing else):
- `.exocortex/control/INTERRUPTS.md`

🚫 NEVER TOUCH — treat as strictly read-only, do not propose or make edits to:
- Any source code (`.ts`, `.tsx`, `.js`, `.py`, `.sh`, `.json`, etc.)
- Any config files (`package.json`, `tsconfig.json`, `vite.config.*`, etc.)
- Any tooling or installer files (`install.sh`, `init-project.sh`, `dev.sh`, etc.)
- Anything in `.cursor/`, `.github/`, `.claude/`, `.exocortex/commands/`
- Any file outside `.exocortex/`

If the user mentions a bug or issue in code, capture it as an interrupt — do not attempt to fix it.

1) Ask: "What type of interrupt?"
   Options:
   - A) Bug — Something is broken or not working right
   - B) New Idea — Feature or improvement idea
   - C) Wild Thought — Random idea, might explore later
   - D) Concern — Something feels wrong or risky
   - E) Question — Need an answer before proceeding

2) Capture (type-specific):

   If BUG:
   - Ask: "What's broken?"
   - Ask: "How urgent?" (Blocking | Important | Low priority)

   If NEW IDEA:
   - Ask: "What's the idea?"
   - Ask: "Why would this be valuable?"

   If WILD THOUGHT:
   - Ask: "What's the thought?"
   - Ask: "Worth exploring?" (Yes, investigate later | No, just parking)

   If CONCERN:
   - Ask: "What are you worried about?"
   - Ask: "What risk does it represent?"

   If QUESTION:
   - Ask: "What's the question?"
   - Ask: "When do you need an answer?" (Before proceeding | Eventually)

3) Save to `.exocortex/control/INTERRUPTS.md` with:
   - Date timestamp
   - Type
   - User's captured text

4) Confirm: "✅ Saved to INTERRUPTS.md"
   "Back to work. Run 'groom' when ready to review."
