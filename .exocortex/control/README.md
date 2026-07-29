# Control Center – [PROJECT_NAME]

**Purpose:** Your command center for daily work and strategic planning.

This folder contains the files you use to control project direction, capture ideas, and plan work. All files here are **human-controlled** — they represent your decisions and priorities, not automated suggestions.

---

## Files in This Folder

### `README.md` (this file)
- Explains the control center structure and purpose

### `INTERRUPTS.md`
- Capture lane for ideas, issues, and observations discovered during execution
- Reviewed during `/groom`, not during execution

### `BACKLOG.md`
- Investigation items promoted from INTERRUPTS via `/groom`
- Promoted to TODO via `/refine-backlog` when ready

### `ROADMAP.md`
- Strategic planning (strategic only, not task-level)
- Execution tasks belong in `.exocortex/TODO.md`

### `DAILY_WORKFLOW.md`
- Simple, repeatable daily operating rhythm
- References workflow commands (`/work`, `/save`, `/interrupt`, `/daily-end`)

### `SNIPPETS.md`
- Catalog of all 24 workflow commands and their read-only defaults
- Reference for when to use each command

### `ARCH_OVERVIEW.md`
- High-level map of how the project is structured
- Links to deeper docs for implementation details

### `QA_STRATEGY.md`
- Day-to-day procedural guide for running QA
- Defines regression criteria, critical path, manual validation, release blockers

### `DELIVERY_WORKFLOW.md`
- Defines the minute-scale Kanban/SDLC lifecycle and its independent gates

### `MODEL_ROUTING.md`
- Defines source-backed capability, risk, availability, and cost-per-success routing
- New catalog entries remain quarantined until reviewed and measured

### `END_SESSION_PROMPT.md`
- Template prompt for triggering end-of-day workflow

---

## Authority

`AI_START_HERE.md` is canonical. This folder records project-local planning and
delivery evidence but does not grant authority. Mutation requires a current
one-time capability accepted by a registered guarded executor. External action
is always a separate exact gate.

**Human authority:**
- All files in `.exocortex/control/` are human-controlled
- These override automated suggestions, AI-generated plans, and implied priorities

**When in doubt:** Check control center files first.

---

## Workflow

1. **Daily Start:** Run `/work` to load context and identify next task
2. **Before Changes:** Check `.exocortex/OPEN_DECISIONS.md` for relevant decisions
3. **During Work:** Use `/interrupt` to capture ideas (parking lot, not backlog)
4. **Before Breaks:** Use `/save` for local narrative memory; it is not a
   lifecycle checkpoint
5. **End of Day:** Run `/daily-end` to review and update memory
6. **Weekly:** Run `/groom` → `/refine-backlog` → `/prioritize`

**Full command reference:** `.exocortex/COMMAND_SYSTEM.md` or `SNIPPETS.md`

---

**Last Updated:** [DATE]
