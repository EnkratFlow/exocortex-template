# Control Center – trading-journal

**Purpose:** Your command center for daily work and strategic planning.

This folder contains the files you use to control project direction, capture ideas, and plan work. All files here are **human-controlled** — they represent your decisions and priorities, not automated suggestions.

---

## Files in This Folder

### `README.md` (this file)
- Explains the control center structure and purpose
- Entry point for understanding project control

### `INTERRUPTS.md`
- Capture lane for ideas, issues, and observations discovered during execution
- Prevents context switching and mid-task derailment
- Reviewed during `/groom`, not during execution

### `BACKLOG.md`
- Investigation items promoted from INTERRUPTS via `/groom`
- Each item has acceptance criteria and open questions
- Promoted to TODO via `/refine-backlog` when ready

### `ROADMAP.md`
- Strategic planning artifact showing current phase, next steps, and future work
- Reference for understanding project evolution and priorities (strategic only, not task-level)
- Execution tasks belong in `.exocortex/TODO.md`, not in the roadmap

### `DAILY_WORKFLOW.md`
- Simple, repeatable daily operating rhythm for human operators
- Defines morning start, execution mode, interruption handling, and end-of-day procedures
- References workflow commands (`/work`, `/save`, `/interrupt`, `/daily-end`)

### `SNIPPETS.md`
- Catalog of all 20 workflow commands
- Reference for when to use each command (`/work`, `/interrupt`, `/groom`, etc.)
- Detailed descriptions of what each command reads, writes, and produces

### `ARCH_OVERVIEW.md`
- High-level map of how trading-journal is structured (client/server, logic, data flow)
- Not the territory — links to deeper docs for implementation details

### `QA_STRATEGY.md`
- Day-to-day procedural guide for running QA
- Defines regression criteria, critical path, manual validation, UAT scenarios, release blockers

### `END_SESSION_PROMPT.md`
- Template prompt for triggering the complete end-of-day workflow
- Equivalent to running `/daily-end`

### `REPO_ORGANIZATION_REPORT.md`
- Classification report for all repository files (Dec 2025)
- Recommendations for organizing files into docs/ subdirectories

---

## Related Files (Outside control/)

| File | Location | Purpose |
|------|----------|---------|
| `TODO.md` | `.exocortex/TODO.md` | Concrete, testable tasks for current execution slice |
| `SESSION_CONTEXT.md` | `.exocortex/SESSION_CONTEXT.md` | Current execution slice and immediate focus |
| `PROJECT_MEMORY.md` | `.exocortex/PROJECT_MEMORY.md` | System purpose, philosophy, constraints, invariants |
| `OPEN_DECISIONS.md` | `.exocortex/OPEN_DECISIONS.md` | Unresolved decisions affecting architecture/logic/QA |
| `LESSONS.md` | `.exocortex/docs/LESSONS.md` | Project-specific lessons learned and anti-patterns |
| `ESSENTIAL_FILES.md` | `.exocortex/reference/ESSENTIAL_FILES.md` | File relationships and source of truth mapping |
| `MEMORY.md` | `.exocortex/reference/MEMORY.md` | Entry point to project memory (read-order guide) |
| `COMMAND_SYSTEM.md` | `.exocortex/COMMAND_SYSTEM.md` | Schema reference and full command index (20 commands) |

---

## Authority

**This control center is authoritative for:**
- Daily execution priorities (via `.exocortex/TODO.md`)
- Strategic planning direction (via `ROADMAP.md`)
- Decision tracking and resolution (via `.exocortex/OPEN_DECISIONS.md`)
- Project phase definition (via `.exocortex/SESSION_CONTEXT.md`)

**Human authority:**
- All files in `.exocortex/control/` are human-controlled
- All files in `.exocortex/` are human-controlled
- These override automated suggestions, AI-generated plans, and implied priorities

**When in doubt:** Check control center files first.

---

## Workflow

1. **Daily Start:** Run `/work` to load context and identify next task
2. **Before Changes:** Check `.exocortex/OPEN_DECISIONS.md` for relevant decisions
3. **During Work:** Use `/interrupt` to capture ideas (parking lot, not backlog)
4. **Before Breaks:** Use `/save` to checkpoint your work state
5. **End of Day:** Run `/daily-end` to review and update memory
6. **Weekly:** Run `/groom` → `/refine-backlog` → `/prioritize`
7. **Strategic Planning:** Reference `ROADMAP.md` for context (strategic only)

**Full command reference:** `.exocortex/COMMAND_SYSTEM.md` or `SNIPPETS.md`

---

**Last Updated:** February 7, 2026

