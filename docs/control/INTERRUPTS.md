---
# INTERRUPTS

**Purpose:** Capture ideas, issues, observations, and concerns discovered during active execution without disrupting current work.

This file is a **parking lot**, not a commitment list.

## What Belongs Here
- Ideas discovered mid-task
- Potential refactors or improvements
- Bugs noticed but not addressed
- Architecture or design concerns
- Questions that require later thought
- "This feels wrong" observations

## What Does NOT Belong Here
- Decided work (use `.exocortex/TODO.md`)
- Approved changes (use `.exocortex/SESSION_CONTEXT.md`)
- Architectural decisions (use `.exocortex/OPEN_DECISIONS.md`)
- Rules or constraints (use `.exocortex/PROJECT_MEMORY.md`)

## Usage Rules
- Capture quickly and continue current task
- No prioritization required
- No guarantees anything here will be acted on
- Items are reviewed during end-of-day or weekly cleanup

## Promotion Paths (Manual)
- INTERRUPT → `.exocortex/TODO.md` (if ready to execute)
- INTERRUPT → `BACKLOG.md` (if needs investigation)
- INTERRUPT → `.exocortex/OPEN_DECISIONS.md` (if decision needed)
- INTERRUPT → Deleted (if no longer relevant)

Most items should eventually be deleted.

**Authority:** Human-only. This file has no governance power.
---

## Template for Capturing Interrupts

Use this format when capturing interrupts during work:

```markdown
## [DATE] | [TYPE] | [Title]

**What:** [Brief description]

**Context:** [Why this came up]

**Next Action:** [Optional - capture if known]

---
```

**Types:** IDEA, BUG, CONCERN, QUESTION, REFACTOR, IMPROVEMENT

---

## Example (Delete After First Real Interrupt)

## 2026-01-05 | IDEA | Add dark mode support

**What:** Users might prefer dark mode for late-night work

**Context:** Working on UI components, noticed all designs use light theme

**Next Action:** Research CSS variable approach for theming

---

## Your Interrupts Start Here

[TODO: Your captured interrupts will appear below as you work]

---
