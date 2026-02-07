# QA Strategy – trading-journal

**Purpose:** Day-to-day procedural guide for running QA on trading-journal

**Note:** This aligns with system-level QA governance but focuses on procedural execution, not policy.

---

## What Counts as Regression

**Critical Regression (Blocks Release):**
- Any change to priority ordering (guards → conflicts → signatures → structure)
- Breaking early exit semantics (higher priority gates must prevent lower ones from running)
- Structural validation requirement for A+ (must check `structuralComplete` before Unicorn)
- Psychology → Technical gate separation (must remain distinct)
- Guardian fires before Unicorn (conflicts must block before signatures)
- Grade assignment logic (A+, A, B, C, F, WAITING)
- Message registry changes that affect user-facing guidance

**Non-Critical Regression (Document and Fix):**
- UI styling changes
- Error message wording (unless it changes meaning)
- Test infrastructure improvements
- Documentation updates
- Performance optimizations that don't change behavior

**Not Regression:**
- Adding new features
- Expanding test coverage
- Fixing bugs (unless fix breaks existing behavior)
- Refactoring that preserves behavior

---

## What Is Considered Critical Path

**Critical Path (Must Pass for Release):**

1. **Core Evaluation Logic**
   - All 2,160 order flow combinations pass (`test-all-scenarios.js`)
   - Priority ordering tests pass (`priority-order.test.ts`)
   - Guardian conflicts correctly block trades
   - Unicorn signatures correctly detect A+ setups
   - Structural validation checkbox states work (manual validation required)

2. **Client/Server Sync**
   - Client and server logic produce identical results
   - Message registries match between client and server
   - Both implementations handle same edge cases

3. **Schema Integrity**
   - No orphaned enum values in use
   - All enum values have corresponding rules or are removed
   - Database migrations apply cleanly

4. **Data Persistence**
   - Order flow signals save correctly (liquiditySignal, shelfLocation, aggressionSignal, deltaSignal)
   - Engine results store correctly (technicalGrade, technicalZone, technicalMessageId)
   - Psychology data persists correctly

**Non-Critical Path (Can Ship with Known Issues):**
- Test copy sync (if documented and accepted)
- Structural validation automated tests (manual validation acceptable)
- News event capping automated tests (manual validation acceptable)
- Lunch time warnings automated tests (manual validation acceptable)

---

## When Automated Tests Must Be Run

**Before Every Commit:**
- Run `test-all-scenarios.js` (2,160 order flow combinations)
- Run `priority-order.test.ts` (priority ordering validation)
- Run any unit tests for changed files

**Before Every Release:**
- Full test suite (all automated tests)
- Manual validation of structural validation checkbox states
- Manual validation of news event capping
- Manual validation of lunch time warnings
- Client/server logic comparison (run same inputs through both, verify identical outputs)

**When Changing Evaluation Logic:**
- Run full test suite
- If test copy model is used, manually verify test copy matches actual implementation
- Run client and server logic with same inputs, verify identical outputs
- Manual validation of structural validation states

**When Changing Schema:**
- Run migration tests
- Verify no orphaned enum values are in use
- Test all enum values have corresponding handling

---

## When Manual Validation Is Required

**Always Manual (Not Automated):**
- Structural validation checkbox state combinations
  - Test with checkboxes checked: A+ requires structure
  - Test with checkboxes unchecked: A doesn't require structure
  - Test all combinations of checkbox states

**Manual When Automated Tests Don't Cover:**
- News event capping behavior
- Lunch time warning behavior
- Psychology → Technical gate flow (integration test)
- RESPONSIVE_FAILED_BREAK enum scenarios (if kept)
- LIQUIDITY_VACUUM_BREAKOUT enum scenarios (if kept)

**Manual Verification Required:**
- Client/server logic sync (run same inputs, compare outputs)
- Test copy sync with actual implementation (if copy model is used)
- Message registry sync between client and server

**Manual When Adding New Features:**
- New setup types require manual validation of all conflict rules
- New signature detection requires manual validation of all scenarios
- New message registry entries require manual validation of user-facing text

---

## What Qualifies as UAT

**UAT Scenarios (User Acceptance Testing):**

1. **Pre-Trade Workflow**
   - Psychology gate blocks when TILTED
   - Psychology gate allows when FOCUSED
   - Technical gate evaluates correctly after psychology pass
   - Structural validation checkboxes affect grade correctly

2. **Grade Assignment**
   - A+ requires structure + Unicorn signature
   - A requires structure only (no order flow needed)
   - B requires partial structure
   - C requires minimal structure
   - F correctly blocks invalid setups
   - WAITING correctly blocks incomplete inputs

3. **Conflict Detection**
   - Price Discovery in Balanced Market → F
   - Fade VA Extreme in Imbalanced → F
   - VWAP Bounce LONG + Shelf ABOVE → F
   - VWAP Bounce LONG + ABSORPTION_BUY → F

4. **Signature Detection**
   - Vacuum Signature (PULLING + SWEEP + ALIGNED) → A+
   - Backtest Signature → A+
   - Brick Wall Signature → A+
   - Retest Signature → A+
   - Trap Signature → A+

5. **Data Persistence**
   - Order flow signals save to database
   - Engine results save to database
   - Psychology data saves to database
   - All data retrievable after save

**UAT Does NOT Include:**
- Code review
- Test coverage metrics
- Performance benchmarks
- Documentation accuracy

---

## What Blocks a Release

**Hard Blocks (Cannot Release):**

1. **Critical Path Failures**
   - Any 2,160 order flow combination fails
   - Priority ordering broken
   - Guardian conflicts don't block
   - Unicorn signatures don't detect
   - Structural validation doesn't work (manual validation fails)

2. **Data Loss Risk**
   - Database migrations fail
   - Data persistence broken
   - Schema drift creates undefined behavior

3. **Client/Server Drift**
   - Client and server produce different results for same inputs
   - Message registries don't match

4. **Orphaned Schema Elements**
   - LIQUIDITY_VACUUM_BREAKOUT or RESPONSIVE_FAILED_BREAK in use without implementation

**Soft Blocks (Document and Accept Risk):**

1. **Test Coverage Gaps**
   - Structural validation not in automated tests (if manual validation passes)
   - News event capping not in automated tests (if manual validation passes)
   - Test copy out of sync (if documented and accepted)

2. **Known Issues**
   - Accepted risks documented in `.exocortex/PROJECT_MEMORY.md`
   - Open decisions in `.exocortex/OPEN_DECISIONS.md` that don't affect current release

**Does NOT Block Release:**
- UI styling issues
- Documentation gaps
- Performance optimizations not yet implemented
- Future roadmap items not yet started
- Deferred architecture consolidation

---

## QA Checklist Before Release

**Automated Tests:**
- [ ] All 2,160 order flow combinations pass
- [ ] Priority ordering tests pass
- [ ] Unit tests for changed files pass
- [ ] Database migrations apply cleanly

**Manual Validation:**
- [ ] Structural validation checkbox states work correctly
- [ ] News event capping works correctly
- [ ] Lunch time warnings work correctly
- [ ] Client/server logic produces identical results
- [ ] Test copy matches actual implementation (if copy model used)

**Data Integrity:**
- [ ] Order flow signals persist correctly
- [ ] Engine results persist correctly
- [ ] Psychology data persists correctly
- [ ] No orphaned enum values in use

**UAT Scenarios:**
- [ ] Pre-trade workflow end-to-end
- [ ] Grade assignment for all scenarios
- [ ] Conflict detection for all documented conflicts
- [ ] Signature detection for all documented signatures

**Documentation:**
- [ ] Known issues documented in `.exocortex/PROJECT_MEMORY.md`
- [ ] Test coverage gaps documented
- [ ] Client/server sync verified and documented

---

## Quick Reference

**Run Before Every Commit:**
- `test-all-scenarios.js`
- `priority-order.test.ts`
- Unit tests for changed files

**Run Before Every Release:**
- Full automated test suite
- Manual validation checklist
- Client/server sync verification
- UAT scenarios

**Block Release If:**
- Critical path tests fail
- Data persistence broken
- Client/server drift detected
- Orphaned schema elements in use

**Don't Block Release For:**
- Test coverage gaps (if manual validation passes)
- Known accepted risks
- UI styling issues
- Documentation gaps

---

**Last Updated:** December 15, 2025

