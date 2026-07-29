# Contributing to exocortex-template

Thanks for your interest in contributing to **exocortex-template**. This project provides a portable memory system for AI-assisted development, and contributions are welcome.

**Last updated:** 2026-07-27

## Getting Started

```bash
git clone https://github.com/EnkratFlow/exocortex-template.git
cd exocortex-template
bash tests/run_tests.sh
bash .exocortex/scripts/tests/test_orchestration_protocol.sh
bash .exocortex/scripts/tests/test_event_tooling.sh
bash tests/phase-b/run.sh
python3 .exocortex/scripts/generate_command_adapters.py --check
```

Every deterministic group must pass. Do not hardcode an expected test count in
documentation; the machine-readable evidence emitted by the current suite is
authoritative.

## Install the Pre-Commit Hook (One-Time)

```bash
bash tests/install-pre-commit-hook.sh
```

The hook runs only `bash tests/run_tests.sh` before a commit that touches:

- `install.sh`
- `tests/`
- `.exocortex/`
- `.cursor/`
- `.claude/`
- `.github/skills/`

If tests fail, the commit is blocked.

The hook does not run the orchestration, event-tooling, Phase B, or adapter
generator checks listed under Getting Started. It also does not trigger for
`.agents/`, the root `scripts/safe-update.sh`, root documentation and
checksums, or root AI-entry files. Run every listed command manually before
review whenever those paths or their contracts may be affected.

## What the suites cover

- pinned-source, complete-checksum, and checksum-bound `FILEMODES` validation;
- clean install, repeated install, migration, collision preservation, and
  guarded existing-repository update;
- protected project data, candidate and target symlink/path safety, hard-link
  denial, durable identity-verified private restore archives, post-consumption
  fault injection, exact in-place code-plane rollback, and idempotency;
- provider adapters, orchestration, lifecycle/checkpoint behavior, egress, and
  privacy;
- official-source registry validation, model quarantine, freshness and
  availability denial, measured cost-per-success routing, and exact
  evidence-digest binding;
- target-specific reconciliation planning, protected-path rejection,
  exact-effect rehearsal, one-time authority, and convergence;
- active documentation and AI-installation contract drift.

## Adding a New Test

Add new test logic in `tests/run_tests.sh` and reuse shared assertions/helpers from `tests/helpers.sh`.

Keep each test focused on one behavior and ensure it is deterministic in CI.

## Pull Request Guidelines

- Every applicable deterministic suite must pass before submitting.
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
- Preserve the documented runtime baseline: Bash 3.2+, Python 3.9+ with Unix
  `fcntl` for guarded apply, Git, `shasum` or `sha256sum`, `awk`, `tar`, `find`, `grep`, `sed`,
  `sort`, `mktemp`, `diff`, `cp`, `mv`, `chmod`, `mkdir`, `rm`, `basename`,
  `dirname`, `cat`, `date`, `tr`, and `wc`; `rsync` is optional.
- Any new runtime dependency requires documentation, deterministic
  cross-platform verification, and explicit review.
