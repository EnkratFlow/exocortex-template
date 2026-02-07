# Essential Files Reference

**Last Updated:** January 17, 2026  
**Purpose:** Map of the most important files and their relationships

---

## Project Structure Overview

```
trading-journal/
├── .exocortex/              # Project memory (workflow, decisions, lessons)
├── client/                  # React frontend
│   ├── src/
│   │   ├── __tests__/       # Unit tests (vitest) - 2,555 tests
│   │   ├── components/      # React components
│   │   │   └── ui/          # Reusable UI primitives (shadcn-style)
│   │   ├── utils/           # Business logic, registries
│   │   ├── engine/          # Trade evaluation engine
│   │   └── types/           # TypeScript types
│   ├── test-all-scenarios.js      # 2,160 order flow combinations
│   ├── run-complete-tests.js      # Full regression suite
│   └── comprehensive-logic-test.js # Deep logic validation
├── server/                  # Backend (Fastify + Prisma)
├── docs/
│   ├── architecture/        # System architecture
│   ├── audits/              # Audits (VWAP alignment, etc.)
│   ├── control/             # Workflow, backlog, QA strategy
│   ├── requirements/        # PRD, VWAP docs
│   ├── rules/               # Trading rules contracts
│   ├── strategies/          # Strategy contracts
│   ├── testing/             # QA playbook, test specs, UAT checklist
│   └── ux-ui/               # Design docs, figma chunks, contracts
│       ├── contracts/       # Component specifications (props, states, behavior)
│       ├── design-system/   # HTML design system prototypes
│       └── figma-chunks/    # Code exports for Figma
├── figma/                   # Design tokens, Figma files
│   ├── Stoic DNA*.json      # Design tokens
│   └── KEY_LEVELS_INVENTORY.md
└── Psych-Mirror-*.html      # Design system prototypes (move to docs/ux-ui/design-system/)
```

---

## Testing Infrastructure (CRITICAL)

**Total: 2,555 automated tests across 10 test files**

| Test File | Purpose | Tests |
|-----------|---------|-------|
| `TechnicalGate.logic.test.ts` | Core evaluation logic | ~2,000+ |
| `orderFlowContract.test.ts` | Order flow signal validation | ~100+ |
| `priority-order.test.ts` | Guard/conflict/signature priority | ~50+ |
| `clientServerSync.test.ts` | Client/server logic parity | ~50+ |
| `compatibilityMatrix.test.ts` | Context/setup compatibility | ~50+ |
| `strategyRegistry.test.ts` | Strategy configuration | ~50+ |
| `strategySnapshots.test.ts` | Strategy output stability | ~50+ |
| `briefingSnapshots.test.ts` | Briefing output stability | ~50+ |
| `generateBriefing.test.ts` | Briefing generation | ~50+ |
| `symbolSpec.test.ts` | Symbol/instrument specs | ~10+ |

**Run tests:** `cd client && npm run test:run`

---

## Design System Files

| File | Purpose | Status |
|------|---------|--------|
| `Psych-Mirror-Current-Design-System.html` | Original design system (single file) | Production reference |
| `Psych-Mirror-Design-System-Accordion.html` | Accordion nav + interactive buttons | Active development |
| `figma/Stoic DNA-v2.json` | Design tokens export from Figma | Source of truth for tokens |
| `figma/KEY_LEVELS_INVENTORY.md` | 15 key levels with PRIMARY designations | Reference |

---

## UX/UI Documentation

| Location | Purpose |
|----------|---------|
| `docs/ux-ui/DESIGN_SYSTEM.md` | Design system overview |
| `docs/ux-ui/DESIGN_TOKENS.md` | Token documentation |
| `docs/ux-ui/FLOW_MAPS.md` | User flow diagrams |
| `docs/ux-ui/PROGRESSIVE_DISCLOSURE_SPEC.md` | Progressive disclosure spec |
| `docs/ux-ui/figma-chunks/` | 11 code chunks for Figma Make |
| `docs/ux-ui/contracts/` | Component contracts (props, states, behavior) |

---

## Source of Truth Files

These files define authoritative behavior. Changes here propagate outward.

| File | Purpose | Notes |
|------|---------|-------|
| `client/src/utils/tradeLogic.ts` | Core evaluation logic (client) | Exports `getTradeGuidance()`, all priority checks |
| `server/src/engine/tradeLogic.ts` | Core evaluation logic (server) | **Duplicate of client logic — must sync manually** |
| `client/src/utils/tradeMessageRegistry.ts` | Message definitions | Maps messageId → user-facing text |
| `server/src/engine/tradeMessageRegistry.ts` | Message definitions (server) | **Duplicate — must sync manually** |
| `server/prisma/schema.prisma` | Database schema | Defines enums, models, relations |
| `docs/MASTER_TRADING_RULES.md` | Plain English rules | Canonical rule reference for traders |

---

## Implementation Files

These files consume the source of truth and implement UI or API behavior.

| File | Purpose | Depends On |
|------|---------|------------|
| `client/src/components/TechnicalGate.tsx` | Technical evaluation UI | `tradeLogic.ts`, `tradeMessageRegistry.ts` |
| `client/src/components/TradeGate.tsx` | Psychology gating UI | `psychEngine` (server) |
| `client/src/engine/tradeEngine.ts` | Trade evaluation engine | `tradeLogic.ts` |
| `client/src/engine/technicalCoaching.ts` | Coaching message generation | `tradeMessageRegistry.ts` |
| `server/src/index.ts` | Fastify API routes | Prisma client, engine modules |
| `server/src/psychEngine.ts` | Psychology evaluation | Called by TradeGate via API |

---

## Test Files

These files validate behavior. Test logic is a **copy**, not a direct import.

| File | Purpose | Notes |
|------|---------|-------|
| `client/src/__tests__/TechnicalGate.logic.test.ts` | Unit tests for evaluation logic | **Contains copy of logic — sync required** |
| `client/src/__tests__/priority-order.test.ts` | Priority ordering tests | Validates gate sequence |
| `client/test-all-scenarios.js` | Exhaustive 2,160 scenario runner | Node.js script, not Vitest |
| `client/run-complete-tests.js` | Full test suite runner | Wraps scenario tests |
| `client/comprehensive-logic-test.js` | Additional logic validation | Supplements main tests |
| `client/test-results-detailed.json` | Test output (38K lines) | Reference only, not source |

---

## Documentation Files

These files define requirements, specifications, and audit results.

| File | Purpose | Relationship |
|------|---------|--------------|
| `docs/MASTER_TRADING_RULES.md` | Plain English rules | **Source of truth for rule definitions** |
| `docs/requirements/trade_grading_matrix.md` | Grade criteria | Defines A+, A, B, C, F logic |
| `docs/requirements/trade_scenarios_catalog.md` | All 2,160 scenarios | Exhaustive combination reference |
| `docs/requirements/grading_system_implementation.md` | Implementation details | Links rules to code |
| `docs/audit_checklist.md` | Setup validation checklist | Manual audit reference |
| `docs/logic_corrections.md` | Bug fixes and clarifications | Historical corrections |
| `TRADING_RULES_AUDIT.md` | Full system audit | December 2025 audit results |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local development orchestration |
| `Dockerfile.client` | Client container build |
| `Dockerfile.server` | Server container build |
| `client/vite.config.ts` | Vite dev server config |
| `client/vitest.config.ts` | Test runner config |
| `server/tsconfig.json` | TypeScript config (server) |
| `client/tsconfig.json` | TypeScript config (client) |

---

## File Relationships Diagram

```
docs/MASTER_TRADING_RULES.md (Source of Truth - Rules)
    ↓
    ├─→ client/src/utils/tradeLogic.ts (Implementation)
    │       ↓
    │       ├─→ client/src/components/TechnicalGate.tsx (UI)
    │       └─→ client/src/__tests__/TechnicalGate.logic.test.ts (Tests - COPY)
    │
    └─→ server/src/engine/tradeLogic.ts (Server Implementation - DUPLICATE)

server/prisma/schema.prisma (Source of Truth - Data)
    ↓
    └─→ server/src/index.ts (API Routes)
            ↓
            └─→ Prisma Client (Generated)

client/src/utils/tradeMessageRegistry.ts (Source of Truth - Messages)
    ↓
    ├─→ client/src/engine/technicalCoaching.ts
    └─→ server/src/engine/tradeMessageRegistry.ts (DUPLICATE)
```

---

## Files That Define Truth vs. Reference vs. Tests

| Category | Files |
|----------|-------|
| **Truth** | `tradeLogic.ts`, `schema.prisma`, `MASTER_TRADING_RULES.md`, `tradeMessageRegistry.ts` |
| **Reference** | `trade_grading_matrix.md`, `trade_scenarios_catalog.md`, `audit_checklist.md`, `TRADING_RULES_AUDIT.md` |
| **Tests** | `TechnicalGate.logic.test.ts`, `priority-order.test.ts`, `test-all-scenarios.js` |

---

## Orphaned or Unclear Files

| File | Status | Notes |
|------|--------|-------|
| `client/src/components/TechnicalGate.old.tsx` | Legacy | Previous version, may be removed |
| `server/server/src/engine/` | Unclear | Nested duplicate path; appears unused |
| `notion-scripts/` | Utility | Notion API scripts; not part of core app |
| `scripts/` | Utility | Audit and debugging scripts |
| `client/server/` | Unclear | Nested directory; purpose unknown |

---

## Design System to React Implementation Workflow

**Current approach (validated Jan 2026):**

```
Figma (visualization) 
    ↓
HTML Design System (Psych-Mirror-Design-System-Accordion.html)
    - Interactive prototypes with real button states
    - Exact Tailwind classes documented
    - Hover/click behavior testable
    ↓
Component Contract (docs/ux-ui/contracts/*.md)
    - Props, states, behavior documented
    - Design tokens extracted
    - Test cases defined
    ↓
React Implementation (client/src/components/)
    - Reference contract for props/states
    - Copy Tailwind classes from HTML
    - Write component tests
```

**When to extract tokens/contracts:**
- When a section of HTML design system is finalized
- Before starting React implementation for that section
- Not during active iteration on HTML

**Implementation phases:**
1. Symbol/Bias/Context cards
2. Setup/Levels/Entry flows
3. Order Flow section

---

## Quick Commands

```bash
# Run all tests (2,555 tests)
cd client && npm run test:run

# Start dev server
cd client && npm run dev

# Check Docker services
docker compose ps
```
