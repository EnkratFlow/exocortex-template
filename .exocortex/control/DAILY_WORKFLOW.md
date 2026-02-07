# Daily Execution Workflow

**Purpose:** Simple, repeatable daily workflow for operating [PROJECT_NAME]

This workflow minimizes context switching and centralizes when memory, TODO, and decisions are updated.

---

## Morning Start (5 minutes)

1. **Run:** `/scrum` or `/dsu` for daily standup (or `/work` for quick start)
   - Review: What did I do yesterday?
   - Plan: What will I do today?
   - Check: Any blockers?

2. **Read:** `.exocortex/SESSION_CONTEXT.md` — current execution slice
3. **Read:** `.exocortex/TODO.md` — what's in scope today (max 5 items)

**Rule:** If it's not in TODO, it is not worked on today.

---

## Execution Mode

**Focus:** Coding, testing, fixing bugs, refactoring (if in TODO)

**Do not do during execution:**
- Update memory files
- Edit roadmap
- Make architectural decisions
- Switch to different work

---

## Interruptions

**When an idea, bug, or concern appears:**

1. **Use `/interrupt`** to capture it (< 1 minute)
2. **Do not act on it immediately** — continue current task
3. **Process later** with `/groom`

**Examples:**
- "Noticed potential bug in module X"
- "Should we add validation for Y?"
- "This could be refactored"

---

## End of Day (5–10 minutes)

1. **Run:** `/daily-end`
2. **Agent reviews** work and proposes updates
3. **You approve or reject** — only real structural changes

**What gets updated:**
- ✅ Completed TODO items
- ✅ New constraints discovered
- ✅ Execution slice changes
- ✅ Resolved decisions

**What does NOT get updated:**
- ❌ Normal code changes, bug fixes, test additions, routine refactoring

---

## Quick Reference

| When | Action |
|------|--------|
| Start of day | `/scrum` or `/work` |
| During work | Code, test. Use `/interrupt` for ideas |
| Before breaks | `/save` |
| End of day | `/daily-end` |
| Weekly | `/groom` → `/refine-backlog` → `/prioritize` |

---

**Last Updated:** [DATE]
