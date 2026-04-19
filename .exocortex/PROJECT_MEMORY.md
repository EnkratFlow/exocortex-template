# Project Memory

**Last Updated:** [DATE]  
**Purpose:** Durable orientation for future contributors (human or AI)

---

## What This System Is

[TODO: Describe what your system is and what problem it solves. Include the main purpose, key capabilities, and primary use cases.]

Example:
- A web application for tracking user activities
- A CLI tool for automating deployment workflows
- An API service for processing data pipelines

---

## What This System Is Not

[TODO: Describe what your system is NOT to prevent scope creep and clarify boundaries.]

Example:
- Not a data warehouse or analytics platform
- Not responsible for user authentication (handled by external service)
- Not a real-time monitoring system

---

## Core Design Philosophy

[TODO: Add 3-5 core principles that guide design decisions in this project.]

1. **[Principle 1 - e.g., "User Experience First"]**  
   [Explanation of why this matters and how it affects decisions]

2. **[Principle 2 - e.g., "Explicit Over Implicit"]**  
   [Explanation of why this matters and how it affects decisions]

3. **[Principle 3 - e.g., "Performance Is a Feature"]**  
   [Explanation of why this matters and how it affects decisions]

---

## Non-Obvious Constraints

[TODO: Document constraints that aren't immediately obvious from the code. These are things future contributors need to know before making changes.]

| Constraint | Reason |
|------------|--------|
| [TODO: Add constraint] | [Why it exists] |
| Example: API rate limited to 100 req/min | External service limitation, cannot be changed |
| Example: Database queries must use connection pooling | Prevents connection exhaustion under load |

---

## Intentional Trade-Offs

[TODO: Document trade-offs that were made consciously. This prevents future contributors from "fixing" intentional decisions.]

| Trade-Off | Decision | Rationale |
|-----------|----------|-----------|
| [TODO: Add trade-off] | [What was chosen] | [Why this was the right choice] |
| Example: Code duplication vs. abstraction | Allowed duplication | Faster iteration during early development |
| Example: Eventual consistency vs. strong consistency | Eventual consistency | Better performance at scale |

---

## Known Accepted Risks

[TODO: Document risks that are known but accepted for now. Include mitigation plans if any.]

| Risk | Status | Notes |
|------|--------|-------|
| [TODO: Add risk] | Accepted/Mitigated | [Context and any mitigation] |
| Example: No automated backups | Accepted | Manual weekly backups; automation planned for Q2 |

---

## Things Future Contributors Must Not Break

[TODO: List invariants and behaviors that must be preserved. These are red lines that should never be crossed without extensive discussion.]

1. **[Invariant 1]**  
   [Why this must not change]

2. **[Invariant 2]**  
   [Why this must not change]

Examples:
- API backward compatibility for v1 endpoints
- Database migration scripts must be idempotent
- User data must never be logged or cached
- Authentication token refresh must happen before expiry

---

## Related Documents

[TODO: Add links to other important documentation in your project]

- `docs/architecture/SYSTEM_DESIGN.md` — Overall system architecture
- `docs/api/API_SPEC.md` — API specifications and contracts
- `docs/deployment/DEPLOYMENT_GUIDE.md` — How to deploy the system

---

**Note:** This file should evolve as you discover new constraints, make important decisions, or identify patterns. Update it when you learn something that future contributors need to know.
