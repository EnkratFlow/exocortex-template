---
# Backlog

**Last Groomed:** [DATE]  
**Last Refined:** [DATE]

This file captures **non-executable items under investigation**.
Nothing here is a TODO until explicitly promoted.

Rules:
- Discovery = investigation, clarification, thinking
- No implementation without promotion to `.exocortex/TODO.md`
- No schema, API, or UI changes until item is in TODO
- Promotion to TODO is manual and explicit

---

## How to Use This File

**Add items here that need:**
- Research or investigation
- Clarification of requirements
- Discussion with team members
- Proof of concept or spike work
- More information before becoming executable

**Weekly grooming:**
- Review items in this file
- Promote ready items to `.exocortex/TODO.md`
- Archive or delete items that are no longer relevant
- Break down large items into smaller investigations

**Promotion criteria:**
- Item is well-defined and executable
- Dependencies are clear
- Effort is estimated (roughly)
- Value is understood

---

## Template for Backlog Items

```markdown
## [Item Title]

**Status:** Investigating | Ready | Blocked | Deferred

**Context:** [Why this matters and where it came from]

**Questions to Answer:**
- [Question 1 that needs investigation]
- [Question 2 that needs investigation]

**Investigation Tasks:**
- [ ] [Task 1 to understand this better]
- [ ] [Task 2 to understand this better]

**Acceptance Criteria (for promotion to TODO):**
- [ ] [Criteria 1]
- [ ] [Criteria 2]

**Promotion Target:** `.exocortex/TODO.md` (as "[Task Title]")

**Added:** [DATE]

---
```

---

## Example (Delete After First Real Backlog Item)

## Add User Authentication

**Status:** Investigating

**Context:** Need to secure API endpoints and identify users. Came up during security review.

**Questions to Answer:**
- Which authentication strategy fits our use case? (JWT, sessions, OAuth)
- Do we build our own or use a service? (Auth0, Firebase, custom)
- What are the security requirements?
- How do we handle password resets and account recovery?

**Investigation Tasks:**
- [ ] Research authentication options (JWT vs sessions vs OAuth)
- [ ] Compare auth services (Auth0, Firebase, Supabase)
- [ ] Document security requirements
- [ ] Estimate implementation effort for each option

**Acceptance Criteria (for promotion to TODO):**
- [ ] Authentication strategy is chosen and documented
- [ ] Implementation approach is clear
- [ ] Dependencies and APIs are identified
- [ ] Effort is estimated

**Promotion Target:** `.exocortex/TODO.md` (as "Implement user authentication with [chosen approach]")

**Added:** 2026-01-05

---

## Active Backlog Items

[TODO: Your backlog items will appear here as you discover work that needs investigation]

---

## Deferred / Low Priority

[TODO: Items that are good ideas but not a priority right now]

---
