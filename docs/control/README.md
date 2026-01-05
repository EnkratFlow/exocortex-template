# Control Center – [PROJECT_NAME]

**Purpose:** Your command center for daily work and strategic planning.

This folder contains the files you use to control project direction, capture ideas, and plan work. All files here are **human-controlled** - they represent your decisions and priorities, not automated suggestions.

---

## Files in This Folder

### `README.md` (this file)
- Explains the control center structure and purpose
- Entry point for understanding project control

### `INTERRUPTS.md`
- Capture lane for ideas, issues, and observations discovered during execution
- Prevents context switching and mid-task derailment
- Reviewed during cleanup, not during execution

### `BACKLOG.md`
- Items under investigation that aren't ready for execution yet
- Requires clarification, research, or discussion before becoming tasks
- Promoted to TODO.md when ready

### `ROADMAP.md` (Optional)
- Strategic planning artifact showing phases and future direction
- High-level only - not for daily task tracking
- Reference for understanding project evolution

---

## Related Control Files

### `.exocortex/OPEN_DECISIONS.md`
- **Purpose:** Tracks unresolved decisions affecting architecture, logic, QA strategy, or product direction
- **Use:** Review before making changes that touch these areas
- **Authority:** Human-controlled decision log

### `.exocortex/SESSION_CONTEXT.md`
- **Purpose:** Current execution slice and immediate focus
- **Use:** Daily work alignment
- **Authority:** Human-controlled execution context

### `.exocortex/TODO.md`
- **Purpose:** Concrete, testable tasks for current execution slice
- **Use:** Daily task tracking
- **Authority:** Human-controlled task list

---

## Authority

**This control center is authoritative for:**
- Daily execution priorities (via `.exocortex/TODO.md`)
- Strategic planning direction (via `ROADMAP.md`)
- Decision tracking and resolution (via `.exocortex/OPEN_DECISIONS.md`)
- Project phase definition (via `.exocortex/SESSION_CONTEXT.md`)

**Human authority:**
- All files in `docs/control/` are human-controlled
- All files in `.exocortex/` are human-controlled
- These override automated suggestions, AI-generated plans, and implied priorities

**When in doubt:** Check control center files first.

---

## Workflow

1. **Daily Start:** Run `/work` snippet or read `.exocortex/SESSION_CONTEXT.md` for current execution slice
2. **Before Changes:** Check `.exocortex/OPEN_DECISIONS.md` for relevant decisions
3. **During Work:** Use `/interrupt` snippet or capture interruptions in `INTERRUPTS.md` (parking lot, not backlog)
4. **Strategic Planning:** Reference `ROADMAP.md` for context (strategic only)
5. **Task Management:** Use `.exocortex/TODO.md` for concrete work items
6. **Workflow Commands:** See `.cursorrules` for all available workflow commands

---

## Daily Workflow (Operator Guide)

This workflow defines how to operate [PROJECT_NAME] day to day.
Follow this exactly. Do not improvise unless intentionally changing process.

### Morning Start (5 minutes)
1. Run: `/work` command to load context
   - See what you did yesterday
   - Plan what you'll do today
   - Check for blockers
2. Read:
   - `.exocortex/SESSION_CONTEXT.md` - Current focus
   - `.exocortex/TODO.md` - Task board (Ready → In Progress)

**Purpose:**
- Establish today's execution slice
- Prevent roadmap-driven thrashing
- Update task status (Ready → In Progress)

### During the Day (Execution)
- Work only from `.exocortex/TODO.md` (focus on the In Progress task)
- Coding, bug fixes, refactors, and tests are allowed
- Do NOT update memory files for normal progress

**If you have an idea or find a bug:**
- Use `/interrupt` to capture it quickly (don't act on it)
- Continue working on your current task

**If a decision, boundary, or invariant changes:**
- Defer to end of day (`/daily-end`)

### Testing & QA
- Test as you go
- Add tests for new features
- Run full test suite before committing
- Document test patterns in `.exocortex/LESSONS.md`

### End of Day (5-10 minutes)
1. Run: `/daily-end` snippet (or `end session`)
2. Review proposed memory updates:
   - Completed tasks (move to Done)
   - New constraints discovered
   - Lessons learned
   - Resolved decisions
3. Approve only if structural changes occurred (not routine progress)

**Remember:** Silence is a valid outcome. You don't need to update memory every day.

### Roadmap Usage
- `ROADMAP.md` is strategic only
- Never pull daily work directly from the roadmap
- Use `.exocortex/TODO.md` for executable tasks

---

## Weekly Workflow

### Process Interrupts
- Review `INTERRUPTS.md`
- Move items to `BACKLOG.md` or `.exocortex/TODO.md`
- Delete items that no longer matter

### Refine Backlog
- Review `BACKLOG.md`
- Promote ready items to `.exocortex/TODO.md`
- Update items that need more investigation

### Clean Up Done Tasks
- Review `.exocortex/TODO.md` Done section
- Remove completed tasks that are no longer relevant
- Keep important achievements for reference

---

**Last Updated:** [DATE]
