# Exocortex Memory System

**Last Updated:** January 2, 2026  
**Purpose:** Human-readable guide to the project memory system

---

## What is the Exocortex?

The **Exocortex** is your project's memory system. It helps you (and AI assistants) remember what you're working on, what needs to be done, and what you've learned. Think of it as an external brain that never forgets.

**Why it matters:** Without it, you waste time re-explaining context, repeating mistakes, and losing track of decisions. With it, you can pick up exactly where you left off, even after days or weeks away.

---

## How It Works

### The Core Concept

Instead of relying on memory or scattered notes, the Exocortex stores:
- **What you're working on** (SESSION_CONTEXT.md)
- **What needs to be done** (TODO.md)
- **What the system is** (PROJECT_MEMORY.md)
- **What you've learned** (LESSONS.md)
- **What decisions are pending** (OPEN_DECISIONS.md)
- **Where things live** (ESSENTIAL_FILES.md)

### The Flow

```
Daily Start → Read Memory → Work → Capture Interrupts → End of Day → Update Memory
```

1. **Morning:** Read SESSION_CONTEXT.md and TODO.md to know what to work on
2. **During Work:** Focus on TODO items only, capture interruptions quickly
3. **End of Day:** Review what changed, update memory files if needed

---

## File Structure

### `.exocortex/` Directory

All memory files live in `.exocortex/` at the project root:

```
.exocortex/
├── README.md              ← You are here (this file)
├── MEMORY.md              ← Entry point for AI (read this first)
├── PROJECT_MEMORY.md      ← System constraints and invariants
├── SESSION_CONTEXT.md     ← Current work state
├── TODO.md                ← Executable tasks
├── LESSONS.md             ← Project-specific lessons learned
├── ESSENTIAL_FILES.md     ← Where core truth lives
├── OPEN_DECISIONS.md      ← Unresolved decisions
└── TEMPLATE_STRUCTURE.md  ← Portable template for new projects
```

---

## File Descriptions

### `MEMORY.md` (Entry Point)
- **Purpose:** Entry point for AI assistants
- **When to read:** Always (first file AI reads)
- **Contains:** Reading order and file locations
- **You don't edit this:** It's a navigation file

### `PROJECT_MEMORY.md` (System Constraints)
- **Purpose:** What the system is, isn't, and must not break
- **When to read:** Before making architectural changes
- **Contains:** 
  - System purpose and philosophy
  - Non-obvious constraints
  - Intentional trade-offs
  - What NOT to break
- **When to update:** When you discover new constraints or change direction

### `SESSION_CONTEXT.md` (Current State)
- **Purpose:** What you're working on RIGHT NOW
- **When to read:** Every morning, before breaks
- **Contains:**
  - 🟢 RIGHT NOW section (current focus)
  - 📅 RECENT WORK (last 7 days)
  - 🚀 NEXT UP (what comes next)
- **When to update:** End of day, or when focus changes

### `TODO.md` (Task Board)
- **Purpose:** Your daily task board with status tracking
- **When to read:** Every morning, during work
- **Contains:** Tasks organized by status:
  - 🟦 **Discovery** - Items being explored (not executable yet)
  - 🟨 **Ready** - Well-defined work ready to execute (prioritized)
  - 🟧 **In Progress** - Exactly ONE item at a time (current focus)
  - 🟩 **Review** - Completed work pending verification
  - ✅ **Done** - Completed work (can be removed weekly/monthly)
- **When to update:** 
  - Add tasks when discovered (start in Discovery or Ready)
  - Move tasks between columns as status changes
  - Check off when completed (move to Review, then Done)
  - Remove Done items at end of week/month

### `LESSONS.md` (Anti-Patterns)
- **Purpose:** Prevent repeating mistakes
- **When to read:** Before major changes, when stuck
- **Contains:** 
  - What went wrong
  - Why it happened
  - What worked instead
  - Prevention strategies
- **When to update:** After painful debugging or discovering patterns

### `ESSENTIAL_FILES.md` (File Locations)
- **Purpose:** Map of where core truth lives
- **When to read:** When you need to find where something is defined
- **Contains:** 
  - Core truth locations (vs reference vs tests)
  - File purposes and relationships
- **When to update:** When file structure changes significantly

### `OPEN_DECISIONS.md` (Pending Decisions)
- **Purpose:** Track unresolved decisions affecting architecture/logic/QA
- **When to read:** Before making changes that touch these areas
- **Contains:** 
  - Unresolved decisions
  - Context for each decision
  - Confidence level
- **When to update:** 
  - Add when new decisions discovered
  - Remove when decisions are resolved
  - Document resolution in PROJECT_MEMORY.md if it creates constraints

---

## Integration with Control System

The Exocortex works with `docs/control/` files:

### Control Files (Strategic)
- **INTERRUPTS.md** → Capture ideas/bugs during work
- **BACKLOG.md** → Items under investigation
- **ROADMAP.md** → Strategic planning (not daily tasks)

### Flow Between Systems

```
INTERRUPTS → BACKLOG → TODO → DONE
     ↓          ↓        ↓
  (groom)  (refine)  (work)
```

1. **During work:** Capture interruptions in `docs/control/INTERRUPTS.md`
2. **Weekly:** Run `/groom` to move interrupts to BACKLOG or TODO
3. **Weekly:** Run `/refine-backlog` to promote backlog items to TODO
4. **Daily:** Work from `.exocortex/TODO.md` only

---

## Daily Workflow

### Morning (5 minutes)
1. Run `/scrum` or `/dsu` for daily standup (or `/work` for quick start)
   - Review: What did I do yesterday?
   - Plan: What will I do today?
   - Check: Any blockers?
2. Update task status if needed (Ready → In Progress)
3. Start working on the In Progress task

### During Work
- Work only from TODO.md
- Use `/interrupt` to capture ideas/bugs (don't act on them)
- Use `/save` before breaks to checkpoint state

### End of Day (5-10 minutes)
1. Run `/daily-end` command
2. Review proposed memory updates
3. Approve only if structural changes occurred

---

## Weekly Workflow

### Process Interrupts
- Run `/groom` to review INTERRUPTS.md
- Move items to BACKLOG or TODO
- Delete items that no longer matter

### Refine Backlog
- Run `/refine-backlog` to review BACKLOG.md
- Promote ready items to TODO
- Update backlog items that need more investigation

### Prioritize
- Run `/prioritize` to reorder TODO items
- Consider: blockers, value, urgency, dependencies

---

## Lessons Integration

### Project-Specific Lessons
- Stored in `.exocortex/LESSONS.md`
- Project-specific anti-patterns and gotchas
- Read before major changes

### Cross-Project Lessons
- Stored in parent project: `EnkratFlow-Project/docs/WORKFLOWS/LESSONS_LEARNED.md`
- Broadly applicable lessons (Python, Docker, cost optimization)
- Reference from LESSONS.md when relevant

### When to Add Lessons
- After painful debugging
- When you discover a pattern
- When you find a better way to do something
- When you want to prevent future mistakes

---

## Decisions Integration

### Where Decisions Live
- **Unresolved:** `.exocortex/OPEN_DECISIONS.md`
- **Resolved:** `.exocortex/PROJECT_MEMORY.md` (if they create constraints)

### Decision Lifecycle
1. **Discover:** Add to OPEN_DECISIONS.md during work or end-of-day review
2. **Investigate:** Add context, research options
3. **Resolve:** Make decision, remove from OPEN_DECISIONS.md
4. **Document:** If decision creates constraints, add to PROJECT_MEMORY.md

### When to Check Decisions
- Before architectural changes
- Before logic changes
- Before QA strategy changes
- Before product direction changes

---

## Workflow Commands

All workflows are triggered by typing commands in chat. See `.cursorrules` for complete details:

- `/work` - Load context, show what to work on
- `/scrum` or `/dsu` - Daily standup (yesterday/today/blockers)
- `/interrupt` - Quick capture during work
- `/save` - Save work state checkpoint
- `/groom` - Process interrupts to backlog
- `/refine-backlog` - Promote backlog items to TODO
- `/daily-end` - End of day workflow
- `/prioritize` - Reorder TODO items
- `/weekly-review` - Weekly planning
- `/monthly-review` - Monthly planning
- `/system-scan` - System health check
- `/ai-export` - Export system understanding
- `/init-exocortex` - Initialize in new project

---

## For New Projects

To use this system in a new project:

1. Run `/init-exocortex` command
2. It will create the `.exocortex/` structure
3. Customize PROJECT_MEMORY.md for your project
4. Start using the workflows

See `.exocortex/TEMPLATE_STRUCTURE.md` for the complete structure and relationships.

---

## Key Principles

1. **Memory is for structure, not progress**
   - Don't update memory for normal code changes
   - Only update for structural changes (constraints, direction, decisions)

2. **TODO is source of truth for daily work**
   - Work only from TODO.md
   - Don't pull tasks from roadmap or backlog directly

3. **Interrupts are parking lot, not backlog**
   - Capture quickly, process later
   - Don't act on interrupts during work

4. **Decisions belong in memory**
   - Unresolved → OPEN_DECISIONS.md
   - Resolved → PROJECT_MEMORY.md (if they create constraints)

5. **Lessons prevent repetition**
   - Add after painful debugging
   - Read before major changes
   - Separate project-specific from cross-project

---

## Related Documentation

- `.cursorrules` - Workflow command definitions
- `docs/control/README.md` - Control system integration
- `docs/control/SNIPPETS.md` - Workflow command catalog
- `docs/control/DAILY_WORKFLOW.md` - Detailed daily workflow

---

**Remember:** The Exocortex is a tool to reduce cognitive load and maintain context. Use it consistently, but don't overthink it. The goal is to work better, not to maintain perfect documentation.

