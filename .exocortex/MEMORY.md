# Project Memory – [PROJECT_NAME]

This folder contains the canonical memory for this project.

**Governance:** [PROJECT_NAME] does not define its own QA or Architecture governance. All such rules are inherited from [PARENT_PROJECT]:
- QA governance: `[PARENT_PROJECT]/qa/QA_MEMORY.md`
- Architecture governance: `[PARENT_PROJECT]/docs/architecture/ARCHITECTURE_MEMORY.md`
- Integration contracts: `[PARENT_PROJECT]/integrations/brain.md` (system-level)

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
   Unresolved decisions affecting architecture, logic, QA strategy, or product direction.

For cross-project lessons (Python, Docker, cost optimization), see:  
`[PARENT_PROJECT]/docs/WORKFLOWS/LESSONS_LEARNED.md`

If work involves cross-system behavior or synchronization, read the system-level integration contract: `[PARENT_PROJECT]/integrations/brain.md`.

Rule:
If you have not read these, do not make changes.

If work discovers new tasks, risks, or follow-ups, the agent MUST update `.exocortex/TODO.md`.

Note:
If an agent is instructed to "read memory", "load memory", "use project memory", or similar,
this file is the intended entry point.

Global system context and canonical integrations live in [PARENT_PROJECT].

---
