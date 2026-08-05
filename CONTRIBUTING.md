# Contributing to exocortex-template

Thanks for your interest in contributing to **exocortex-template**. This project provides a portable memory system for AI-assisted development, and contributions are welcome.

**Last updated:** 2026-07-31

## Getting Started

```bash
python3 tests/test_documentation_contract.py
python3 .exocortex/scripts/generate_command_adapters.py --check
```

These are the quick checks appropriate to documentation-only changes. Match
the rest of the evidence to the affected surface:

| Change | Checks before review |
|---|---|
| Markdown documentation only | documentation contract, adapter check, checksum verification, and `git diff --check` |
| Event or memory tooling | event-tooling suite plus the documentation-only checks |
| Commands/adapters | adapter check, affected command-contract tests, orchestration when authority changes, and the quick checks |
| Installer, updater, authority, orchestration, protocol, or release mechanics | focused affected checks, then the complete Exocortex safety suite once for the exact candidate |

The complete Exocortex safety suite is `bash tests/phase-b/run.sh`. Report its
expected duration before starting it. Every applicable deterministic group
must pass, but do not repeat the complete suite for an unchanged candidate on
merged `main` or a tag. Do not hardcode an expected test count in
documentation; machine-readable evidence is authoritative.

## Install the Pre-Commit Hook (One-Time)

```bash
bash tests/install-pre-commit-hook.sh
```

The hook runs right-sized checks from staged paths:

- Markdown-only work gets the documentation contract, adapter check, checksum
  verification, and staged diff check.
- Event/memory tooling gets its focused suite plus the quick checks.
- Other code-plane changes get `bash tests/run_tests.sh`, adapter verification,
  and the staged diff check.

If tests fail, the commit is blocked.

The hook runs only focused or quick checks; it never runs the complete
Exocortex safety suite. The complete suite remains the once-per-exact-candidate
review/CI gate described above.

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

## Release closeout

Release work from an isolated branch does not update the original local
`main` worktree automatically. Prepare and validate one exact candidate in
this order:

1. Finish the candidate and its checksums in an isolated worktree.
2. Rehearse a clean installation and at least one representative
   existing-repository update in disposable targets. Preserve project memory
   and verify a second update is a zero-change result.
3. Run focused checks, independent review when the risk matrix requires it,
   and Human UAT on the disposable outcomes.
4. Run the complete Exocortex safety suite once for that exact candidate. A
   changed candidate invalidates the result; a status-label change does not.
5. Review and merge the exact candidate.
6. Stop if the primary `main` worktree is dirty. Preserve and reconcile those
   local files; never force-update, reset, or overwrite them.
7. In a clean `main` worktree, run `git fetch --prune --tags origin` and
   fast-forward only with `git merge --ff-only origin/main`.
8. Run only the lightweight release-identity checks on unchanged merged main,
   then tag the merged commit as `v<VERSION>` and publish a GitHub release that
   names the peeled commit SHA and SHA-256 of that tag's `SHA256SUMS`.
9. Fetch the published tag, then run:

   ```bash
   bash scripts/check-release-state.sh \
     --published-digest <digest-from-the-GitHub-release-notes>
   ```

10. Clone the exact tag into a new disposable directory and verify its peeled
    commit and published digest. The public installation/update instructions
    were already exercised against the candidate; repeat them only if the
    published artifact differs. Do not substitute an unrelated development
    worktree.

The checker is read-only and uses already-fetched refs. It fails when local
`main`, `origin/main`, the packaged version, tag ancestry, main-worktree
cleanliness, or the published digest disagree.

## What Not to Change

Never modify user data files in template update logic:

- `SESSION_CONTEXT.md`
- `SESSION_CONTEXT.md.backup`
- `SESSION_CONTEXT_BACKUP_*.md` (the direct legacy session-backup family)
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
