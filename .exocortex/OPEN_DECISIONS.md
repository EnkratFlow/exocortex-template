# Open Decisions – [PROJECT_NAME]

**Last Updated:** [DATE]  
**Purpose:** Track unresolved decisions affecting architecture, logic, QA strategy, or product direction.

---

## How to Use This File

**When to add a decision:**
- You encounter a choice that affects architecture, design, or implementation
- You need input from others before proceeding
- Multiple approaches are possible and you're unsure which is best
- You discover an inconsistency or ambiguity that needs resolution

**When to remove a decision:**
- The decision has been made and communicated
- Move important resolved decisions to PROJECT_MEMORY.md if they create constraints

**Decision Format:**
Each decision should include:
- Clear question or choice to be made
- Context explaining why it matters
- Options being considered (if known)
- Impact of the decision
- Confidence level (high/medium/low)

---

## Architecture & Design Decisions

[TODO: Add unresolved architecture and design decisions]

### Example Decision (Delete This After Adding Real Decisions)

**1. Should we use REST or GraphQL for the API?**
- **Context:** Need to design API for frontend-backend communication. Both options are viable.
- **Options:**
  - REST: Simpler, well-understood, good tooling
  - GraphQL: More flexible, reduces over-fetching, steeper learning curve
- **Impact:** Affects entire API design, frontend data fetching, and long-term maintainability
- **Confidence:** Medium (team has experience with REST, limited with GraphQL)

---

## Technical Implementation Decisions

[TODO: Add unresolved technical implementation decisions]

Examples:
- Which database migration tool should we use?
- Should we implement caching at database or application level?
- What authentication strategy (JWT, sessions, OAuth)?

---

## Testing & Quality Decisions

[TODO: Add unresolved testing and quality decisions]

Examples:
- What test coverage threshold should we enforce?
- Should we use integration tests or E2E tests for this workflow?
- How should we handle flaky tests?

---

## Product & Feature Decisions

[TODO: Add unresolved product and feature decisions]

Examples:
- Should feature X be in MVP or deferred to v2?
- What is the priority order for features Y and Z?
- Should we support mobile devices in first release?

---

## Process & Workflow Decisions

[TODO: Add unresolved process and workflow decisions]

Examples:
- What branching strategy should we use (Git Flow, trunk-based)?
- How often should we deploy (continuous, weekly, on-demand)?
- What code review process should we follow?

---

## Resolved Decisions (Move to PROJECT_MEMORY.md)

When a decision is resolved, **remove it from this file**.

If the decision creates an important constraint, document it in `.exocortex/PROJECT_MEMORY.md` under "Non-Obvious Constraints" or "Intentional Trade-offs".

---

## Notes

- **High Confidence:** Strong evidence or team consensus for direction
- **Medium Confidence:** Some evidence, but uncertainty remains
- **Low Confidence:** Limited information, need more research

**Remember:** This file tracks only UNRESOLVED decisions. Once resolved, move important ones to PROJECT_MEMORY.md and delete the rest.

---
