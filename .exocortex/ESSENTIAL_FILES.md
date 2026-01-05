# Essential Files Reference

**Last Updated:** [DATE]  
**Purpose:** Map of the most important files and their relationships

---

## How to Use This File

This file helps you (and AI assistants) quickly understand:
- Where the "source of truth" lives for different concerns
- Which files are documentation/reference vs. actual implementation
- Which files are tests that validate behavior

Update this file when:
- You add new core modules or components
- File structure changes significantly
- You discover that something you thought was truth is actually reference

---

## Source of Truth Files

[TODO: List files that define authoritative behavior. Changes here propagate outward.]

These files define authoritative behavior. Changes here propagate outward.

| File | Purpose | Notes |
|------|---------|-------|
| [TODO: Add core files] | [What they define] | [Important notes] |

Example:
| `src/models/user.ts` | User data model and validation | Schema source of truth |
| `src/api/routes.ts` | API endpoint definitions | All routes defined here |
| `config/database.json` | Database configuration | Production settings |

---

## Implementation Files

[TODO: List files that consume the source of truth and implement UI, API, or business logic.]

These files consume the source of truth and implement features.

| File | Purpose | Depends On |
|------|---------|------------|
| [TODO: Add implementation files] | [What they do] | [What they depend on] |

Example:
| `src/components/UserProfile.tsx` | User profile UI component | `models/user.ts` |
| `src/services/userService.ts` | User business logic | `models/user.ts`, `api/client.ts` |

---

## Test Files

[TODO: List test files and what they validate.]

These files validate behavior. Keep them in sync with implementation.

| File | Purpose | Notes |
|------|---------|-------|
| [TODO: Add test files] | [What they test] | [Important notes] |

Example:
| `src/__tests__/user.test.ts` | User model unit tests | Run with `npm test` |
| `src/__tests__/api.test.ts` | API integration tests | Requires test database |

---

## Documentation Files

[TODO: List important documentation that defines requirements or specifications.]

These files define requirements, specifications, and design decisions.

| File | Purpose | Relationship |
|------|---------|--------------|
| [TODO: Add documentation] | [What it specifies] | [How it relates to code] |

Example:
| `docs/api/API_SPEC.md` | API endpoint specifications | Source of truth for routes |
| `docs/architecture/DESIGN.md` | System architecture | Guides implementation structure |

---

## Configuration Files

[TODO: List important configuration files.]

| File | Purpose |
|------|---------|
| [TODO: Add config files] | [What they configure] |

Example:
| `package.json` | Dependencies and scripts |
| `tsconfig.json` | TypeScript compiler settings |
| `.env.example` | Required environment variables |

---

## File Relationships Diagram

[TODO: Add a simple diagram showing how your core files relate to each other]

Example:
```
docs/API_SPEC.md (Specification)
    ↓
    └─→ src/api/routes.ts (Implementation)
            ↓
            └─→ src/__tests__/api.test.ts (Tests)

src/models/user.ts (Model)
    ↓
    ├─→ src/components/UserProfile.tsx (UI)
    └─→ src/services/userService.ts (Logic)
```

---

## Files That Define Truth vs. Reference vs. Tests

| Category | Files |
|----------|-------|
| **Truth** | [TODO: Add source of truth files] |
| **Reference** | [TODO: Add documentation/reference files] |
| **Tests** | [TODO: Add test files] |

Example:
| **Truth** | `src/models/*.ts`, `src/api/routes.ts`, `config/*.json` |
| **Reference** | `docs/api/API_SPEC.md`, `docs/architecture/DESIGN.md` |
| **Tests** | `src/__tests__/*.test.ts`, `cypress/integration/*.spec.ts` |

---

## Orphaned or Unclear Files

[TODO: Document files whose purpose is unclear or that might be safe to delete]

| File | Status | Notes |
|------|--------|-------|
| [TODO: Add unclear files] | [Status] | [What needs to be determined] |

Example:
| `old_backup/` | Legacy | Previous implementation, safe to delete |
| `temp_script.js` | Unclear | Purpose unknown, investigate before deleting |

---

**Note:** Keep this file updated as your project evolves. It's a map for navigating your codebase - make sure it stays accurate!
