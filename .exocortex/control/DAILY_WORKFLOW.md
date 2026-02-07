# Daily Execution Workflow

**Purpose:** Simple, repeatable daily workflow for operating trading-journal

This workflow minimizes context switching and centralizes when memory, TODO, and decisions are updated.

---

## Morning Start (5 minutes)

1. **Run:** `/scrum` or `/dsu` for daily standup (or `/work` for quick start)
   - Review: What did I do yesterday?
   - Plan: What will I do today?
   - Check: Any blockers?
   - Update task status (Ready → In Progress)

2. **Read:** `.exocortex/SESSION_CONTEXT.md`
   - Understand today's execution slice
   - Note any frozen areas

3. **Read:** `.exocortex/TODO.md`
   - See what's actually in scope today
   - Maximum 5 items

4. **Briefly glance:** `.exocortex/control/ROADMAP.md`
   - Understand strategic context
   - Do not pull tasks from here

**Rule:** If it's not in TODO, it is not worked on today.

**Workflow Snippets:** See `.exocortex/control/SNIPPETS.md` for all available commands (`/work`, `/interrupt`, `/save`, `/daily-end`, etc.)

---

## Execution Mode

**Focus:**
- Coding
- Testing
- Fixing bugs
- Refactoring (if in TODO)

**Do not do during execution:**
- Update memory files
- Edit roadmap
- Make architectural decisions
- Switch to different work

**If you need to change direction:**
- Capture in INTERRUPTS.md
- Continue current work
- Review at end of day

---

## Interruptions

**When an idea, bug, or concern appears:**

1. **Use `/interrupt` snippet** (or write a short entry to `.exocortex/control/INTERRUPTS.md`)
   - One line is enough
   - No detail required
   - No prioritization needed
   - Takes < 1 minute

2. **Do not act on it immediately**
   - Continue current task
   - Finish what you started

3. **Treat INTERRUPTS as a parking lot, not a backlog**
   - Most items will be deleted
   - Some may become TODO items later
   - No pressure to act on anything

**Process interrupts later:** Run `/groom` snippet to review and move items to BACKLOG or TODO

**Examples of interruptions:**
- "Noticed potential bug in tradeLogic.ts line 45"
- "Should we add validation for X?"
- "This feels like it could be refactored"
- "Question about schema enum handling"

---

## Mid-Day Check (Optional)

**Only if you have time and want to review:**

1. **Open:** `.exocortex/control/INTERRUPTS.md`

2. **If an item blocks today's TODO:**
   - Move one item into TODO
   - Update SESSION_CONTEXT if focus changes
   - Continue with updated TODO

3. **Otherwise:**
   - Ignore INTERRUPTS
   - Continue with original TODO
   - Review at end of day

**This step is optional.** You can skip it and review everything at end of day.

---

## End of Day (5–10 minutes)

1. **Run:** `/daily-end` snippet (or `end session` or `end session confirm`)

2. **Agent reviews work and proposes:**
   - SESSION_CONTEXT updates (if execution slice changed)
   - TODO updates (completed items, new discoveries)
   - OPEN_DECISIONS entries (if new decisions needed)

3. **You approve or reject:**
   - Review each proposal
   - Accept only real structural changes
   - Reject routine progress updates
   - Silence is valid (no changes needed)

**What gets updated:**
- ✅ Completed TODO items (check them off)
- ✅ New constraints discovered (add to PROJECT_MEMORY)
- ✅ Execution slice changes (update SESSION_CONTEXT)
- ✅ Resolved decisions (remove from OPEN_DECISIONS)

**What does not get updated:**
- ❌ Normal code changes
- ❌ Bug fixes
- ❌ Test additions
- ❌ Routine refactoring

---

## File Responsibilities

| File | Purpose | When Updated |
|------|---------|--------------|
| `SESSION_CONTEXT.md` | Current execution slice and focus | When slice changes or major blockers found |
| `TODO.md` | Executable work items (max 5) | Daily: check off completed, add discovered tasks |
| `ROADMAP.md` | Strategic direction and future phases | Rarely: strategic planning sessions only |
| `OPEN_DECISIONS.md` | Unresolved decisions affecting architecture/logic/QA | When new decisions discovered or resolved |
| `INTERRUPTS.md` | Idea capture during execution | Anytime during work (parking lot, not backlog) |

---

## Quick Reference

**Start of day:**
1. Run `/scrum` or `/dsu` for daily standup (or `/work` for quick start)
2. Review: Yesterday's work, Today's plan, Blockers
3. Update task status (Ready → In Progress)
4. Work from TODO.md (focus on In Progress task)

**During work:**
- Code, test, fix
- Use `/interrupt` snippet to capture ideas/bugs/concerns
- Use `/save` snippet before breaks
- Do not update memory

**End of day:**
1. Run `/daily-end` snippet (or `end session`)
2. Review proposals
3. Approve only structural changes

**Weekly:**
- Run `/groom` to process interrupts
- Run `/refine-backlog` to promote backlog items
- Run `/prioritize` to reorder TODO

**Remember:**
- TODO is your source of truth for daily work
- ROADMAP is strategic, not tactical
- INTERRUPTS is a parking lot, not a commitment
- Memory updates happen at end of day, not during execution
- **See `.exocortex/control/SNIPPETS.md` for all available workflow commands**

---

**Last Updated:** February 7, 2026

