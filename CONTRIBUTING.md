# Contributing to exocortex-template

Thanks for your interest in contributing to **exocortex-template**. This project provides a portable memory system for AI-assisted development, and contributions are welcome.

**Last updated:** 2026-04-19

## Getting Started

```bash
git clone https://github.com/EnkratFlow/exocortex-template.git
cd exocortex-template
bash tests/run_tests.sh
```

The expected result is all 8 tests passing.

## Install the Pre-Commit Hook (One-Time)

```bash
bash tests/install-pre-commit-hook.sh
```

The hook runs the full test suite before any commit that touches:

- `install.sh`
- `tests/`
- `.exocortex/`
- `.cursor/`
- `.claude/`
- `.github/skills/`

If tests fail, the commit is blocked.

## What the 8 Tests Cover

| Test | What it verifies |
|------|------------------|
| T01 fresh install | Skeleton files created, manifest written |
| T02 update no manifest | User data preserved, new template files added |
| T03 system file updates | Manifest-tracked files updated when template changes |
| T04 user-modified preserved | Files you've edited are never overwritten |
| T05 idempotent | Running install twice produces identical results |
| T06 critical data files | `SESSION_CONTEXT`, `TODO`, `LESSONS`, `PROJECT_MEMORY` untouched |
| T07 events preserved | Event files byte-for-byte identical after update |
| T08 events not in manifest | Event files never added to the hash manifest |

## Adding a New Test

Add new test logic in `tests/run_tests.sh` and reuse shared assertions/helpers from `tests/helpers.sh`.

Keep each test focused on one behavior and ensure it is deterministic in CI.

## Pull Request Guidelines

- All 8 tests must pass before submitting.
- Keep PRs focused (one change per PR).
- Write a clear PR description of what changed and why.
- Install and use the pre-commit hook; it must pass.

## What Not to Change

Never modify user data files in template update logic:

- `SESSION_CONTEXT.md`
- `TODO.md`
- `LESSONS.md`
- `PROJECT_MEMORY.md`
- `events/`

## Reporting Bugs

Report bugs through [GitHub Issues](https://github.com/EnkratFlow/exocortex-template/issues).

## Code Style

- Use plain Bash.
- Keep scripts POSIX-compatible where practical.
- Do not add external runtime dependencies beyond `git` and `bash`.
