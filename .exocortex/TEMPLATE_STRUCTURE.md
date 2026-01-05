# Exocortex Template Structure

**Purpose:** Portable template for initializing the Exocortex memory system in new projects

---

## Complete Folder Structure

```
project-root/
├── .exocortex/                    ← Memory system (all files here)
│   ├── README.md                  ← Human-readable guide (this explains the system)
│   ├── MEMORY.md                  ← Entry point for AI (navigation file)
│   ├── PROJECT_MEMORY.md          ← System constraints and invariants
│   ├── SESSION_CONTEXT.md         ← Current work state
│   ├── TODO.md                    ← Executable tasks
│   ├── LESSONS.md                 ← Project-specific lessons
│   ├── ESSENTIAL_FILES.md         ← File location map
│   ├── OPEN_DECISIONS.md          ← Unresolved decisions
│   └── TEMPLATE_STRUCTURE.md      ← This file (template reference)
│
├── docs/
│   └── control/                   ← Control system (strategic planning)
│       ├── README.md              ← Control system guide
│       ├── INTERRUPTS.md          ← Capture lane (parking lot)
│       ├── BACKLOG.md             ← Items under investigation
│       ├── ROADMAP.md             ← Strategic planning
│       ├── SNIPPETS.md            ← Workflow command catalog
│       └── DAILY_WORKFLOW.md      ← Detailed workflow guide
│
└── .cursorrules                   ← Workflow command definitions
```

---

## File Relationships

### Memory System (`.exocortex/`)

```
MEMORY.md (entry point)
    ↓
    ├─→ PROJECT_MEMORY.md (system constraints)
    ├─→ SESSION_CONTEXT.md (current state)
    ├─→ TODO.md (tasks)
    ├─→ LESSONS.md (anti-patterns)
    ├─→ ESSENTIAL_FILES.md (file locations)
    └─→ OPEN_DECISIONS.md (pending decisions)
```

### Control System (`docs/control/`)

```
INTERRUPTS.md (capture)
    ↓ (groom)
BACKLOG.md (investigation)
    ↓ (refine)
TODO.md (execution)
    ↓ (work)
DONE
```

### Integration Points

- **INTERRUPTS → BACKLOG → TODO:** Flow of ideas to tasks
- **OPEN_DECISIONS → PROJECT_MEMORY:** Resolved decisions become constraints
- **LESSONS → PROJECT_MEMORY:** Patterns become constraints
- **SESSION_CONTEXT → TODO:** Current work drives tasks

---

## File Templates

### `MEMORY.md` (Entry Point)

```markdown
# Project Memory – [project-name]

This folder contains the canonical memory for this project.

**Governance:** [project-name] does not define its own QA or Architecture governance. All such rules are inherited from [parent-project]:
- QA governance: `[parent-project]/qa/QA_MEMORY.md`
- Architecture governance: `[parent-project]/docs/architecture/ARCHITECTURE_MEMORY.md`
- Integration contracts: `[parent-project]/integrations/brain.md` (system-level)

Local memory files below are project-specific only.

Before making any changes, read these files in order:

1. PROJECT_MEMORY.md  
   System purpose, philosophy, and non-obvious constraints.

2. SESSION_CONTEXT.md  
   Current focus, open questions, and frozen areas.

3. ESSENTIAL_FILES.md  
   Where core truth lives vs reference vs tests.

4. LESSONS.md  
   Project-specific lessons learned and anti-patterns to avoid.

5. OPEN_DECISIONS.md (if exists)  
   Unresolved decisions affecting architecture/logic/QA.

For cross-project lessons, see:  
`[parent-project]/docs/WORKFLOWS/LESSONS_LEARNED.md`

If work involves cross-system behavior or synchronization, read the system-level integration contract: `[parent-project]/integrations/brain.md`.

Rule:
If you have not read these, do not make changes.

If work discovers new tasks, risks, or follow-ups, the agent MUST update `.exocortex/TODO.md`.

Note:
If an agent is instructed to "read memory", "load memory", "use project memory", or similar,
this file is the intended entry point.

Global system context and canonical integrations live in [parent-project].

---
```

### `PROJECT_MEMORY.md` (System Constraints)

```markdown
# Project Memory

**Last Updated:** [date]  
**Purpose:** Durable orientation for future contributors (human or AI)

---

## What This System Is

[Describe what the system is and what problem it solves]

---

## What This System Is Not

[Describe what it is NOT to prevent scope creep]

---

## Core Design Philosophy

1. **[Principle 1]**
   [Explanation]

2. **[Principle 2]**
   [Explanation]

---

## Non-Obvious Constraints

| Constraint | Reason |
|------------|--------|
| [Constraint 1] | [Why it exists] |
| [Constraint 2] | [Why it exists] |

---

## Intentional Trade-offs

| Trade-off | Why |
|-----------|-----|
| [Trade-off 1] | [Rationale] |

---

## What Not to Break

- [Invariant 1]
- [Invariant 2]

---
```

### `SESSION_CONTEXT.md` (Current State)

```markdown
# Session Context – [project-name]

**Last Updated:** [date]

## 🟢 RIGHT NOW

**Active Work:** [What you're working on]
**Status:** 🟢 Active | 🟡 Paused | 🔴 Blocked

---

## 📅 RECENT WORK (Last 7 Days)

**[Date]**
- **[Work Item]**
  - [Details]

---

## 🚀 NEXT UP

- [What comes next]
- [What comes after]

---
```

### `TODO.md` (Tasks)

```markdown
# TODO – [project-name]

**Prioritized executable tasks, ordered by strategic importance.**

- [ ] Task 1 — [What needs to be done]
- [ ] Task 2 — [What needs to be done]
- [x] Task 3 — [Completed task]

---
```

### `LESSONS.md` (Anti-Patterns)

```markdown
# Project Lessons – [project-name]

**Last Updated:** [date]  
**Purpose:** Prevent repeating mistakes in this codebase

---

## How to Use This File

1. **Before major changes:** Scan relevant lessons
2. **After painful debugging:** Add new lesson
3. **When stuck:** Check if similar problem happened before

For cross-project lessons, see:  
`[parent-project]/docs/WORKFLOWS/LESSONS_LEARNED.md`

---

## [Month Year] Lessons

### LESSON 1: [Title] ([Date])

**What Went Wrong:**
[Description]

**Why It Happened:**
[Root cause]

**What Worked:**
[Solution]

**Prevention:**
[How to avoid]

---
```

### `ESSENTIAL_FILES.md` (File Locations)

```markdown
# Essential Files – [project-name]

**Purpose:** Map of where core truth lives vs reference vs tests

---

## Core Truth (Source of Truth)

| File | Purpose | Don't Change Without |
|------|---------|---------------------|
| [file] | [purpose] | [approval needed] |

---

## Reference (Documentation)

| File | Purpose |
|------|---------|
| [file] | [purpose] |

---

## Tests (Validation)

| File | Purpose |
|------|---------|
| [file] | [purpose] |

---
```

### `OPEN_DECISIONS.md` (Pending Decisions)

```markdown
# Open Decisions – [project-name]

**Last Updated:** [date]  
**Purpose:** Track unresolved decisions affecting architecture, logic, QA strategy, or product direction.

---

## Architecture & Logic Decisions

1. **[Decision Question]**
   - Context: [Why this decision matters]

---

## Maintenance

- **Remove resolved decisions:** When a decision is made, remove it from this file
- **Do not keep resolved decisions:** This file tracks only unresolved decisions
- **Document resolution elsewhere:** Resolved decisions may be documented in `.exocortex/PROJECT_MEMORY.md` if they establish new constraints

---
```

---

## Control System Templates

### `docs/control/INTERRUPTS.md`

```markdown
# Interrupts

Raw capture during work. Ideas, bugs, concerns — captured quickly without processing.

**Weekly processing:** Run `/groom` to process items.

---

## [Date] | [TYPE] | [Title]

**What:** [Brief description]

**Why Valuable:** [If idea, why it matters]

---
```

### `docs/control/BACKLOG.md`

```markdown
# Backlog

Items under investigation. Questions, spikes, bugs that need understanding.

**Promotion to TODO:** Run `/refine-backlog` when ready to work on items.

---

## [Item Title]

**Status:** Investigating | Ready | Deferred

**Context:** [Why this matters]

**Questions:**
- [Question 1]
- [Question 2]

**Promotion Target:** `.exocortex/TODO.md` (as "[Task Title]")

---
```

---

## Initialization Checklist

When setting up a new project:

- [ ] Create `.exocortex/` directory
- [ ] Create `docs/control/` directory
- [ ] Copy templates and customize:
  - [ ] MEMORY.md (update project name, parent project references)
  - [ ] PROJECT_MEMORY.md (fill in system description)
  - [ ] SESSION_CONTEXT.md (set initial state)
  - [ ] TODO.md (add initial tasks)
  - [ ] LESSONS.md (start empty, add as needed)
  - [ ] ESSENTIAL_FILES.md (map file locations)
  - [ ] OPEN_DECISIONS.md (start empty, add as needed)
  - [ ] README.md (copy from template)
  - [ ] TEMPLATE_STRUCTURE.md (copy this file)
- [ ] Create control files:
  - [ ] INTERRUPTS.md (start empty)
  - [ ] BACKLOG.md (start empty)
  - [ ] ROADMAP.md (if needed)
  - [ ] README.md (copy from template)
- [ ] Copy `.cursorrules` from parent project (or create new)
- [ ] Run `/init-exocortex` command to verify structure

---

## Usage Notes

1. **Start simple:** Don't overthink the initial setup
2. **Customize as needed:** Adapt templates to your project
3. **Use consistently:** The value comes from regular use
4. **Don't perfect it:** Good enough is better than perfect

---

**See `.exocortex/README.md` for complete usage guide.**

