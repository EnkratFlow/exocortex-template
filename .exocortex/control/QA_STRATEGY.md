# QA Strategy – [PROJECT_NAME]

**Purpose:** Day-to-day procedural guide for running QA on [PROJECT_NAME]

---

## What Counts as Regression

**Critical Regression (Blocks Release):**
- _Define what breaking changes look like for your project_

**Non-Critical Regression (Document and Fix):**
- UI styling changes
- Error message wording (unless it changes meaning)
- Documentation updates

**Not Regression:**
- Adding new features
- Expanding test coverage
- Fixing bugs (unless fix breaks existing behavior)

---

## Critical Path

_Define your project's critical path — what must pass for release._

---

## When Automated Tests Must Be Run

**Before Every Commit:**
- Run relevant unit tests for changed files

**Before Every Release:**
- Full test suite
- Manual validation of critical workflows

---

## When Manual Validation Is Required

_Define scenarios that require manual testing._

---

## QA Checklist Before Release

- [ ] All automated tests pass
- [ ] Manual validation complete
- [ ] Data integrity verified
- [ ] Known issues documented

---

**Last Updated:** [DATE]
