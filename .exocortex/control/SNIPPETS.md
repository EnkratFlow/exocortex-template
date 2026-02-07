# Workflow Snippets Reference

**Purpose:** Catalog of all Cursor snippets available for workflow management  
**Location:** Global snippets in `/Users/guyrobo/Library/Application Support/Cursor/User/snippets/`  
**Last Updated:** February 7, 2026

---

## Quick Reference

| Snippet | Prefix | Purpose | When to Use |
|---------|--------|---------|-------------|
| Work | `/work` | Load context & identify tasks | Morning, after break, context switch |
| Scrum | `/scrum` or `/dsu` | Daily standup (yesterday/today/blockers) | Morning daily scrum/standup |
| Brief | `/brief` | Quick status check | Quick check without full context load |
| Interrupt | `/interrupt` | Quick capture during work | When you have an idea/bug/concern mid-task |
| Groom | `/groom` | Process interrupts to backlog | When INTERRUPTS.md has items to review |
| Refine Backlog | `/refine-backlog` | Promote backlog items to TODO | When backlog items are ready |
| Save | `/save` | Save current work state | Before breaks, mid-day checkpoints |
| Daily End | `/daily-end` | End-of-day workflow review | End of work session |
| Prioritize | `/prioritize` | Reorder TODO items | When TODO needs reorganization |
| History | `/history` | Search older events | Looking for old work by keyword or date |
| Short-term Memory | `/shortterm` | 7-31 day semantic memory | Need recent context beyond last week |
| Long-term Memory | `/longterm` | 31+ day compressed memory | Need long-term project context |
| Subconscious | `/subconscious` | Cross-cutting pattern detection | Need meta-cognitive insights across ALL events |
| Drill | `/drill <topic>` | Topic deep-dive | Deep context on a specific topic |
| Weekly Review | `/weekly-review` | Weekly planning & review | End of week |
| Monthly Review | `/monthly-review` | Monthly planning & review | End of month |
| System Scan | `/system-scan` | System health check | Periodic maintenance |
| AI Export | `/ai-export` | Generate system understanding doc | Need comprehensive system document |
| Ecosystem | `/ecosystem` | Cross-project activity view | Cross-project overview |
| Init Exocortex | `/init-exocortex` | Initialize exocortex structure | First-time setup |

---

## Detailed Snippet Descriptions

### `/work` - Work Entry Point
**Purpose:** Load context, show what to work on, confirm direction, start work  
**When:** Morning, after break, context switch, mid-day  
**Reads:** 
- `.exocortex/reference/MEMORY.md` (entry point)
- `.exocortex/PROJECT_MEMORY.md` (system purpose, philosophy, constraints)
- `.exocortex/docs/LESSONS.md` (if exists - project-specific lessons)
- `.exocortex/SESSION_CONTEXT.md` (🟢 RIGHT NOW section)
- `.exocortex/TODO.md` (available tasks)
- `.exocortex/control/INTERRUPTS.md` (urgent/important interrupts)

**Output:** Brief showing:
- What you were last working on (from RIGHT NOW)
- Current state of that work (done | paused | blocked)
- Next uncompleted task in TODO (if different)
- Any high-priority interrupts
- Any relevant lessons for today's work

**Next Steps:** Asks "What would you like to work on?" with options to continue, start new task, handle interrupt, or explore

---

### `/scrum` or `/dsu` - Daily Standup

**Purpose:** Daily scrum/standup following classic format: What did I do yesterday? What will I do today? Any blockers?  
**When:** Morning daily scrum/standup  
**Triggers:** `scrum`, `standup`, `daily scrum`, or `dsu`  
**Reads:**
- `.exocortex/SESSION_CONTEXT.md` (RECENT WORK section)
- `.exocortex/TODO.md` (all sections)
- `.exocortex/OPEN_DECISIONS.md` (blockers)
- `.exocortex/control/INTERRUPTS.md` (urgent items)
- Git log (commits since last scrum)

**Output:** Formatted scrum report:
- ✅ Yesterday: Completed tasks and work in progress
- 🎯 Today: Current/next task and plan
- 🚧 Blockers: Decisions needed, urgent interrupts, blocked tasks

**Optional Updates:**
- Can update TODO.md status (Ready → In Progress, etc.)
- Can update SESSION_CONTEXT.md RIGHT NOW section

**Next Steps:** Asks "Ready to start work on [task]?" and transitions to work mode

---

### `/interrupt` - Quick Capture
**Purpose:** Capture ideas, bugs, concerns, questions without stopping work  
**When:** During active work when something comes up  
**Time:** < 1 minute  
**Writes:** `.exocortex/control/INTERRUPTS.md`

**Process:**
1. Asks for interrupt type: Bug, New Idea, Wild Thought, Concern, Question
2. Type-specific capture (minimal questions)
3. Saves to INTERRUPTS.md with date, type, and captured text
4. Confirms and continues work

**Next Step:** Run `/groom` when ready to review

---

### `/groom` - Process Interrupts
**Purpose:** Review captured interrupts, decide what matters, move to BACKLOG or TODO  
**When:** When INTERRUPTS.md has accumulated items  
**Reads:** `.exocortex/control/INTERRUPTS.md`  
**Writes:** `.exocortex/control/BACKLOG.md`, `.exocortex/TODO.md`, `.exocortex/control/INTERRUPTS.md`

**Process:**
1. Loads all items from INTERRUPTS.md
2. Groups by type (Bugs, Ideas, Wild Thoughts, Concerns, Questions)
3. For each item, asks: "What should we do?"
   - A) Add to BACKLOG for investigation
   - B) Add to TODO (urgent/clear enough)
   - C) Delete (not relevant)
   - D) Keep in INTERRUPTS (decide later)
4. Proposes changes before writing
5. Updates files and shows summary

**Next Step:** `/refine-backlog` to promote ready items

---

### `/refine-backlog` - Refine Backlog
**Purpose:** Review BACKLOG items, promote ready ones to TODO, mark completed tasks  
**When:** When backlog items are ready for promotion  
**Reads:** `.exocortex/control/BACKLOG.md`, `.exocortex/TODO.md`  
**Writes:** `.exocortex/control/BACKLOG.md`, `.exocortex/TODO.md`

**Process:**
1. Loads BACKLOG.md and TODO.md
2. For each BACKLOG item, asks: "Is [Item Title] ready to promote to TODO?"
   - A) Yes, promote to TODO
   - B) Not yet, still investigating
   - C) Defer (decide later)
   - D) Delete (not relevant)
3. If promoting: asks for executable task title and scope
4. Checks TODO.md for completed [x] items and removes them
5. Proposes all changes before writing

**Next Step:** `/prioritize` to reorder TODO

---

### `/save` - Save Work State
**Purpose:** Quick memory checkpoint without closing session  
**When:** Before breaks, mid-day checkpoints, interruptions, context switches  
**Writes:** `.exocortex/SESSION_CONTEXT.md` (🟢 RIGHT NOW section), optionally `.exocortex/docs/LESSONS.md`

**Process:**
1. Detects current state (last commits, uncommitted changes, current file)
2. Asks: "In one sentence, what's your current focus right now?"
3. Optional: Captures quick lesson learned (one-liner)
4. Proposes update to RIGHT NOW section
5. Writes if approved

**Next Step:** Run `/work` when you return

---

### `/daily-end` - End of Day
**Purpose:** Complete end-of-day workflow review  
**When:** End of work session  
**Reads:** 
- `.exocortex/SESSION_CONTEXT.md`
- `.exocortex/TODO.md`
- `.exocortex/PROJECT_MEMORY.md`
- `.exocortex/docs/LESSONS.md`
- `.exocortex/OPEN_DECISIONS.md` (if exists)
- `.exocortex/control/INTERRUPTS.md` (if exists)

**Writes:**
- `.exocortex/SESSION_CONTEXT.md` (if execution slice changed)
- `.exocortex/TODO.md` (check off completed, add discovered tasks)
- `.exocortex/PROJECT_MEMORY.md` (new constraints if any)
- `.exocortex/docs/LESSONS.md` (new lessons if any)
- `.exocortex/OPEN_DECISIONS.md` (add new OR remove resolved)

**Process:**
1. Reviews today's work
2. Identifies completed TODO items, new constraints, execution slice changes, new decisions, resolved decisions, new lessons
3. Proposes updates (focus on structural changes only)
4. Waits for approval before writing

---

### `/prioritize` - Prioritize TODO
**Purpose:** Reorder TODO items by strategic importance  
**When:** When TODO needs reorganization  
**Reads:** `.exocortex/TODO.md`  
**Writes:** `.exocortex/TODO.md`

**Process:**
1. Loads current TODO order
2. Asks strategic questions:
   - What's blocking other work?
   - What has the highest business/product value?
   - What's most urgent (time-sensitive)?
   - Are there dependencies?
   - What should come first given all factors?
3. Proposes new priority order with reasons
4. Writes if approved

**Next Step:** `/work` to see prioritized list

---

### `/weekly-review` - Weekly Review
**Purpose:** Weekly planning and review  
**When:** End of week  
**Reads:** All memory files, `.exocortex/control/INTERRUPTS.md`  
**Writes:** `.exocortex/TODO.md`, `.exocortex/SESSION_CONTEXT.md` (if direction changed)

**Process:**
1. Summarizes the week (what worked, what shipped, what stalled)
2. Reviews INTERRUPTS.md and groups by type
3. Asks:
   - Do any of these now deserve focus next week?
   - Anything that should explicitly stay parked?
   - Anything that no longer matters?
4. Proposes updates for next week
5. Waits for approval

**Rules:** No rewriting history, no retroactive perfection, promote only what earns attention

---

### `/monthly-review` - Monthly Review
**Purpose:** Monthly planning and review  
**When:** End of month  
**Reads:** All memory files, `.exocortex/control/ROADMAP.md`  
**Writes:** `.exocortex/PROJECT_MEMORY.md` (if direction changed), `.exocortex/SESSION_CONTEXT.md`, high-level TODO priorities

**Process:**
1. High-level reflection (what built/learned, what felt aligned, what felt heavy)
2. Reviews trends (repeated interrupt themes, blockers, energy vs output mismatch)
3. Asks:
   - What should I stop doing next month?
   - What deserves more focus?
   - Is the current direction still correct?
4. Proposes directional updates
5. Waits for approval

**Rules:** About direction, not productivity. No task-level micromanagement. Fewer priorities is better.

---

### `/system-scan` - System Health Check
**Purpose:** Read repository end-to-end and produce system report  
**When:** Periodic maintenance, onboarding, system understanding  
**Reads:** Application code, architecture docs, requirements, QA docs, project memory, control files  
**Output:** Single markdown report

**Report Answers:**
1. What this system is and what problem it solves
2. What is implemented and considered complete
3. What is currently in progress
4. What is explicitly planned next (based only on existing docs)
5. Where that next work belongs (which repo/folder)
6. Any documented risks, gaps, or open decisions

**Constraints:** Read-only. No file modifications. No memory updates. No speculation beyond documented evidence.

---

### `/init-exocortex` - Initialize Exocortex
**Purpose:** Initialize exocortex structure for new project  
**When:** First-time setup  
**Writes:** Exocortex structure files

**Creates:**
- `.exocortex/` directory
- `.exocortex/SESSION_CONTEXT.md`
- `.exocortex/TODO.md`
- `.exocortex/control/` directory
- `.exocortex/control/INTERRUPTS.md`
- `.exocortex/control/BACKLOG.md`

**Also:** Guides copying documentation and snippets from EnkratFlow-Project

---

## Workflow Integration

### Daily Workflow
1. **Morning:** `/work` (load context, identify tasks)
2. **During work:** `/interrupt` (capture ideas/bugs/concerns)
3. **Before breaks:** `/save` (save work state)
4. **End of day:** `/daily-end` (review & update memory)

### Weekly Workflow
1. **Process interrupts:** `/groom` (move to backlog)
2. **Refine backlog:** `/refine-backlog` (promote to TODO)
3. **Prioritize:** `/prioritize` (reorder TODO)
4. **End of week:** `/weekly-review` (planning)

### Monthly Workflow
1. **End of month:** `/monthly-review` (strategic planning)

### Setup Workflow
1. **New project:** `/init-exocortex` (bootstrap structure)

### Maintenance Workflow
1. **Periodic:** `/system-scan` (health check, onboarding)

---

## Snippet File Locations

All snippets are stored in:
```
/Users/guyrobo/Library/Application Support/Cursor/User/snippets/
```

**Core Workflow Snippets:**
- `work.code-snippets`
- `interrupt.code-snippets`
- `save.code-snippets`
- `daily-end.code-snippets`
- `groom.code-snippets`
- `refine-backlog.code-snippets`
- `prioritize.code-snippets`

**Review Snippets:**
- `weekly-review.code-snippets`
- `monthly-review.code-snippets`

**System Snippets:**
- `system-scan.code-snippets`
- `init-exocortex.code-snippets`
- `ai System Export.code-snippets`

---

## Related Documents

- `.exocortex/control/DAILY_WORKFLOW.md` - Daily workflow process
- `.exocortex/control/BACKLOG.md` - Backlog management
- `.exocortex/control/INTERRUPTS.md` - Interrupts capture
- `.exocortex/TODO.md` - Current tasks
- `.exocortex/SESSION_CONTEXT.md` - Current work state
- `.exocortex/PROJECT_MEMORY.md` - Project constraints and invariants

---

## Usage Tips

1. **Start your day:** Run `/work` to load context and see what to work on
2. **During work:** Use `/interrupt` to capture ideas without breaking flow
3. **Before breaks:** Use `/save` to checkpoint your work state
4. **End of day:** Run `/daily-end` to review and update memory
5. **Weekly:** Run `/groom` to process interrupts, then `/refine-backlog` to promote items
6. **When stuck:** Run `/system-scan` to get a fresh perspective on the system

---

**End of Snippets Reference**

