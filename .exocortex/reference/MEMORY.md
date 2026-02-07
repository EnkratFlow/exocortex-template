# Project Memory – trading-journal

This folder contains the canonical memory for this project.

**Governance:** trading-journal does not define its own QA or Architecture governance. All such rules are inherited from EnkratFlow-project:
- QA governance: `EnkratFlow-project/qa/QA_MEMORY.md`
- Architecture governance: `EnkratFlow-project/docs/architecture/ARCHITECTURE_MEMORY.md`
- Integration contracts: `EnkratFlow-project/integrations/brain.md` (system-level)

Local memory files below are project-specific only.

**Workflow Commands:** All workflow commands (/save, /work, /history, /groom, etc.) are defined as JSON specs in:
→ `.exocortex/commands/*.json` (one file per command)
→ `.exocortex/COMMAND_SYSTEM.md` (schema reference and full command index)
→ Referenced automatically via `.cursorrules` in Cursor
→ Load once per session in VS Code: "Read .cursorrules"

**AI Persona & Commands:** The AI assistant is configured as a senior multidisciplinary expert. Quick help:
→ `QUICK_REFERENCE.md` - Fast lookup for commands and when to use them
→ `PERSONA_AND_COMMANDS.md` - Complete documentation of persona and all commands
→ **Note:** Persona is always active - you don't need commands for expert responses

---

## Trading System Quick Reference

**Auto-Loaded Context:** When you ask about trades, setups, psychology, or grading, the AI automatically loads:

1. **`docs/TRADING_SYSTEM_PRIMER.md`** (500+ lines)
   - Complete trading rules (Guardian Gates, Unicorn Signatures, Structure Logic)
   - Full psychology system (Pre-trade gating, emotional grading, circuit breaker)
   - Drysdale mental execution framework
   - Order flow signals and key levels
   - Design philosophy and non-negotiables

2. **`.exocortex/PROJECT_MEMORY.md`**
   - System purpose: Psychology-first pre-trade decision support
   - Core design principles (8 principles)
   - Non-obvious constraints and intentional trade-offs
   - Things that must not be broken

3. **`docs/audits/ALL_FIELDS_MAPPING.md`**
   - Complete field reference (UI → Database)
   - Psychology fields (pre/post emotion, confidence, energy, state, quality, mistakes)
   - Technical fields (setup, market, signals, grading)
   - Execution fields (P&L, prices, contracts)

**For Deep Analysis:** Use the `trading-psychology-context` skill
- Loads archived docs and historical context
- Provides comprehensive system design review
- Pattern analysis across psychology + technical dimensions
- Located at: `~/.cursor/skills/trading-psychology-context/`

**Key Documents by Topic:**

| Topic | Primary Doc | Deep Dive Docs |
|-------|-------------|----------------|
| Trading Rules | TRADING_SYSTEM_PRIMER.md | MASTER_TRADING_RULES.md, TRADING_RULES_AUDIT.md |
| Psychology | TRADING_SYSTEM_PRIMER.md | PSYCHOLOGICAL_ACCOUNTABILITY_README.md, EMOTIONAL_GRADING_GUIDE.md |
| Field Mapping | ALL_FIELDS_MAPPING.md | schema.prisma |
| Implementation | tradeLogic.ts | TradeGate.tsx, TechnicalGate.tsx, PostTradeCapture.tsx |
| Research | Why_Disciplined_Traders_Fail_Prop_Firms.md | archive/TRADING_RULES_ANALYSIS.md |

**You never need to say "go read the trading docs" - it happens automatically.**

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

6. TRADING_RULES_AUDIT.md (only if touching trading logic or rules)  
   Known behavior, risks, and gaps.

For cross-project lessons (Python, Docker, cost optimization), see:  
`EnkratFlow-Project/docs/WORKFLOWS/LESSONS_LEARNED.md`

If work involves cross-system behavior or synchronization, read the system-level integration contract: `EnkratFlow-project/integrations/brain.md`.

Rule:
If you have not read these, do not make changes.

If work discovers new tasks, risks, or follow-ups, the agent MUST update `.exocortex/TODO.md`.

Note:
If an agent is instructed to "read memory", "load memory", "use project memory", or similar,
this file is the intended entry point.

Global system context and canonical integrations live in EnkratFlow-project.

---

