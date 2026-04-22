# SESSION_CONTEXT – exocortex-template

**Last Updated:** April 22, 2026
**Generated from events:** Last 7 days (4 events)

---

## 🟢 RIGHT NOW

**Event:** April 22 at 11:47 AM • macbook • cursor • Branch: `main`


# Phase checkpoint — Phase 3: CHANGELOG + WHATSNEW + README

## What was accomplished

- Created `CHANGELOG.md` at repo root (27 lines): Keep-a-Changelog 1.1.0 format with SemVer notice, single v3.1.0 entry containing Added/Changed/Security sections (plan-orchestrate rule, auto-save hook, batch updater, local-source offline installs, EXOCORTEX_LOCAL_SOURCE env var, update-all-repos.sh script, hook re-install protection), includes link reference section at bottom
- Created `WHATSNEW.md` at repo root (24 lines): concise release blurb optimized for terminal display (no markdown headings, ASCII em-rule separator, ~24 lines max), highlights plan-orchestrate + auto-save hook pattern, auto-save hook as Cursor automation, batch updater for multi-repo installs; intended for `install.sh` post-install echo and GitHub release body
- Updated `README.md` with three surgical edits:
  - 3a (lines ~162-173): replaced single `.cursor/commands/` tree listing with full `.cursor/` tree showing `commands/`, `skills/`, `rules/`, `agents/`, `hooks/`, and `hooks.json` file; demonstrates new project structure
  - 3b (lines ~216-237): inserted new "Plan Orchestration & Auto-Save Hook" section before "20 Workflow Commands" explaining the `.cursor/rules/plan-orchestrate.mdc` rule, the `auto-save-phase.sh` hook triggered by `subagentStop`, the hybrid `/save` pattern, and global installation prompt
  - 3c (lines ~459-481): inserted new "Updating an Existing Install" section before "Disclaimer" covering re-run `install.sh` idempotency, batch updater usage (`--dry-run`, `--yes` modes), and `EXOCORTEX_LOCAL_SOURCE` for offline installs
- All changes preserve existing README structure and anchor links; no sections removed or merged
- Integration test suite still 10/10 PASS (no code changed in Phase 3, only documentation)

## Decisions made

- CHANGELOG starts at v3.1.0 with no fabricated history for earlier versions; honesty preferred over false completeness — no v3.0.0 changelog to back-fill against
- WHATSNEW kept to ~24 lines unindented (no markdown headings, ASCII em-rule separators for visual breaks); optimized for `cat` to terminal display rather than GitHub markdown render, ensures readability in post-install echo
- README "Plan Orchestration & Auto-Save Hook" section inserted before "20 Workflow Commands" (high visibility, positioned before detailed command reference); rationale: new users will encounter the rule and hook first in their workflow, so explain it before command details
- README "Updating an Existing Install" section inserted before "Disclaimer" (last natural content slot before legal boilerplate); rationale: upgrade workflows are late-stage user questions
- Did NOT update "Cursor Setup (One-Time, Cursor Users Only)" section even though plan-orchestrate-as-a-rule technically also applies to that context; scope discipline — keep documentation updates surgical (each edit serves one purpose) rather than "while we're here" expansions; future README updates can link to plan-orchestrate section if needed
- Em-rule unicode (U+2014) used in WHATSNEW for visual separation instead of ASCII dashes; requires explicit "preserve exactly" guidance in future prompts to avoid replacement

## Code state

- Branch: main
- Uncommitted files: 16 (README.md, CHANGELOG.md, WHATSNEW.md, plus Phase 2 files: install.sh, tests/helpers.sh, tests/run_tests.sh, scripts/update-all-repos.sh, .cursor/hooks.json, .cursor/hooks/, .cursor/rules/, VERSION, .exocortex/AI_BOOTSTRAP.md, .github/workflows/checksums.yml, .exocortex/SESSION_CONTEXT.md, and one event file)
- Key files touched: `README.md` (three surgical insertions), `CHANGELOG.md` (created), `WHATSNEW.md` (created)
- Tests: 10/10 PASS (no new tests added in Phase 3; all changes documentation-only)

## What's next

- Phase 4 (parent Opus, no delegation): final review of all Phase 1-3 artifacts, run integration test suite one final time to confirm 10/10 PASS, `git add` all uncommitted files from Phases 1-3, single commit "release: v3.1.0 — plan-orchestrate + auto-save hook + batch updater", tag commit as `v3.1.0`, push to origin main, create GitHub release with `gh release create v3.1.0 --body-file WHATSNEW.md`
- Post-Phase-4: execute `bash scripts/update-all-repos.sh ~/EnkratFlow --dry-run` to preview rollout across all managed exocortex repos, then live with `--yes` once happy; target is all EnkratFlow/* branches updated to v3.1.0 within hours
- Optional: monitor bash execution and note any repos that skip or error; gather feedback on batch updater UX for future refinement

## Conversation patterns

- Recurring topic: scope discipline in documentation. Phase 3 deliberately did NOT expand the "Cursor Setup" section even though plan-orchestrate-as-a-rule belongs there conceptually; keeping documentation updates surgical (one edit = one purpose) prevents scope creep and makes future edits predictable. Candidate PROJECT_MEMORY: "README structure updates should be surgical by section, not opportunistic — each insertion solves one problem, future edits cross-reference rather than merge"
- Friction: em-rule unicode (U+2014) in WHATSNEW.md — easy for text processors or copy-paste tools to replace with ASCII dashes. Prompts now need explicit "preserve em-rule unicode exactly" guidance or acceptance criteria should forbid substitution
- Candidate skill: "release-notes-from-changelog" — converting a CHANGELOG entry (structured bullets) to a CLI-ready WHATSNEW blurb (short, unindented, visual separators) is mechanical enough to template; could save ~15 minutes per release
- Candidate PROJECT_MEMORY: README anchor convention — section headings drift by line number as content grows, but insertion points should always be specified by surrounding-section names (e.g., "before '20 Workflow Commands'") not by line numbers. Phase 3 used ~216 and ~459 as approximate guides, but future editors MUST use section names to stay stable
- Context gap: None identified; Phase 3 execution was clean, decisions were explicit, and all three documentation artifacts (CHANGELOG, WHATSNEW, README edits) align with release goals

## Git State

**Last Commits:**
93e26b2 ci: run test job on all PRs, skip suite for docs-only changes
38a976d docs: expand API key section with cost, privacy, and data disclosure info
6ec9ccf security: add installer integrity verification via SHA256SUMS
22b6e46 feat: exocortex v3 — initial public release (history squashed for open-source)

**Branch:** main

**Uncommitted Changes:**
```
 M .exocortex/AI_BOOTSTRAP.md
 M .exocortex/SESSION_CONTEXT.md
 M .github/workflows/checksums.yml
 M README.md
 M install.sh
 M tests/helpers.sh
 M tests/run_tests.sh
?? .cursor/hooks.json
?? .cursor/hooks/
?? .cursor/rules/
?? .exocortex/events/2026-04-22_11-36-51_macbook-cursor.md
?? .exocortex/events/2026-04-22_11-43-50_macbook-cursor.md
?? CHANGELOG.md
?? VERSION
?? WHATSNEW.md
?? scripts/update-all-repos.sh
```

**Diff Stats:**
```
 .exocortex/AI_BOOTSTRAP.md      |  16 ++++
 .exocortex/SESSION_CONTEXT.md   | 193 ++++++++++++++++++++++++++++++++++++++--
 .github/workflows/checksums.yml |   6 ++
 README.md                       |  77 ++++++++++++++--
 install.sh                      | 132 +++++++++++++++++++++++++--
 tests/helpers.sh                |  12 +++
 tests/run_tests.sh              |  45 ++++++++++
 7 files changed, 465 insertions(+), 16 deletions(-)
```

---

**Event:** April 22 at 11:43 AM • macbook • cursor • Branch: `main`


# Phase checkpoint — Phase 2: tests + EXOCORTEX_LOCAL_SOURCE + update-all-repos.sh

## What was accomplished

- Added test T09 to `tests/run_tests.sh` (lines 193-217): verifies fresh install copies `.cursor/hooks.json`, `.cursor/hooks/auto-save-phase.sh` to target, registers `subagentStop` event, and preserves executable bit on scripts
- Added test T10 to `tests/run_tests.sh` (lines 219-240): verifies that a user-modified hook script (e.g., `auto-save-phase.sh` with custom edits) is never overwritten on re-install, using manifest-aware skip logic
- Extended `install.sh` with `EXOCORTEX_LOCAL_SOURCE` environment variable support: when set, copies exocortex files from a local directory via `rsync` (with tar fallback) instead of cloning from GitHub; enables offline installs, vendored deployments, and batch updater workflows
- Created `scripts/update-all-repos.sh` (4.9 KB, executable): walks a root directory, discovers all repos with `.exocortex/` subdirectory, prompts per-repo (interactive or `--yes`/`--dry-run` modes), skips dirty git trees, runs `install.sh` per repo with `EXOCORTEX_LOCAL_SOURCE` pointing at the v3.1.0 template, prints final summary
- Fixed critical snapshot bug in `tests/helpers.sh::run_install` (lines 43-49): overlays uncommitted tracked-file modifications AND untracked (non-gitignored) files on top of HEAD; uses `git ls-files --others --exclude-standard` instead of copying `.git/index`. Without this fix, T09/T10 failed because new hook files are still untracked in the working tree during the test run
- All 10 tests pass (T01-T10) with 60 assertions; full suite runtime ~66 seconds

## Decisions made

- Folded `EXOCORTEX_LOCAL_SOURCE` feature into Phase 2/v3.1.0 release instead of treating as follow-up E1 commit, because `update-all-repos.sh` explicitly depends on it. Ship them together so batch updater works out-of-box
- `update-all-repos.sh` defaults to interactive per-repo prompts `[y/N/q]` rather than auto-yes; too easy to clobber many repos at once, and `--yes` remains opt-in for CI/automation
- Skip dirty-tree repos rather than abort or prompt user; goal is bulk update with minimal friction, not interactive merge resolution
- Used `git ls-files --others --exclude-standard` for snapshot overlay instead of copying raw `.git/index` state — simpler, respects `.gitignore`, avoids dragging entire git object store into memory
- Test T10 uses `make_installed_project` (which calls `run_install` internally) — slow per-test (~6s) but realistic; trade-off accepted because it exercises the exact re-install workflow users hit

## Code state

- Branch: main
- Uncommitted files: 9 (install.sh, tests/helpers.sh, tests/run_tests.sh, scripts/update-all-repos.sh, .cursor/hooks.json, .cursor/hooks/, .cursor/rules/, VERSION, .exocortex/AI_BOOTSTRAP.md, .github/workflows/checksums.yml, .exocortex/SESSION_CONTEXT.md)
- Key files touched: `tests/run_tests.sh` (T09, T10), `install.sh` (EXOCORTEX_LOCAL_SOURCE), `tests/helpers.sh` (snapshot fix), `scripts/update-all-repos.sh` (created)
- Tests: 10/10 PASS (60 assertions, ~66s runtime)

## What's next

- Phase 3 (claude-4.5-haiku-thinking subagent): create `CHANGELOG.md` (Keep-a-Changelog format, v3.1.0 section with bullet list of features, fixes, decisions), create `WHATSNEW.md` (concise per-release blurb shown by `install.sh` post-install), update `README.md` (add three sections: What's Included with .cursor/ tree, Plan Orchestration rules pattern, Updating an Existing Install)
- Phase 4 (parent Opus): final review of all Phase 1-3 work, run full integration test suite once more, git add/commit all files, tag `v3.1.0`, push, `gh release create` with WHATSNEW.md as release body
- Post-Phase-4: execute `bash scripts/update-all-repos.sh ~/EnkratFlow --yes` to roll v3.1.0 out across all managed exocortex clones in the monorepo

## Conversation patterns

- Recurring topic: snapshot mechanics in `tests/helpers.sh::run_install`. This is the second refinement (first: include staged changes for pre-commit hooks; this time: include untracked files for new releases). Worth a permanent comment block at the top of `run_install` documenting the layering order: `HEAD` (baseline) → staged changes (pre-commit) → unstaged tracked changes → untracked files. Future test authors MUST use `run_install` if they need to see uncommitted/untracked files; don't try reading directly from `$TEMPLATE_DIR` because that bypasses install behavior
- Friction: T09/T10 failures only revealed themselves when Phase 2 test code ran; snapshot gap was invisible until we shipped a feature with brand-new untracked files. Validates the dog-fooding approach — running tests in Phase 2 instead of Phase 4 caught this early
- Candidate skill: "release shipping checklist" — versioning, test coverage, snapshot mechanics, changelog, what's-new, batch updater, GH release. We're walking through it manually each phase; a reusable skill could template the order and catch gaps
- Candidate PROJECT_MEMORY: `tests/helpers.sh::run_install` snapshot mechanism is a load-bearing abstraction. Document it as: "New tests needing to see uncommitted files MUST call `run_install` to get the overlay layering (HEAD + staged + unstaged + untracked); direct filesystem reads won't match what real users see after install"
- Context gap: None identified; Phase 2 execution was clean and dependencies were correctly ordered

## Git State

**Last Commits:**
93e26b2 ci: run test job on all PRs, skip suite for docs-only changes
38a976d docs: expand API key section with cost, privacy, and data disclosure info
6ec9ccf security: add installer integrity verification via SHA256SUMS
22b6e46 feat: exocortex v3 — initial public release (history squashed for open-source)

**Branch:** main

**Uncommitted Changes:**
```
 M .exocortex/AI_BOOTSTRAP.md
 M .exocortex/SESSION_CONTEXT.md
 M .github/workflows/checksums.yml
 M install.sh
 M tests/helpers.sh
 M tests/run_tests.sh
?? .cursor/hooks.json
?? .cursor/hooks/
?? .cursor/rules/
?? .exocortex/events/2026-04-22_11-36-51_macbook-cursor.md
?? VERSION
?? scripts/update-all-repos.sh
```

**Diff Stats:**
```
 .exocortex/AI_BOOTSTRAP.md      |  16 +++++
 .exocortex/SESSION_CONTEXT.md   | 111 +++++++++++++++++++++++++++++++--
 .github/workflows/checksums.yml |   6 ++
 install.sh                      | 132 ++++++++++++++++++++++++++++++++++++++--
 tests/helpers.sh                |  12 ++++
 tests/run_tests.sh              |  45 ++++++++++++++
 6 files changed, 311 insertions(+), 11 deletions(-)
```

---

**Event:** April 22 at 11:36 AM • macbook • cursor • Branch: `main`


# Phase checkpoint — Phase 1: versioning + checksums + prompt fix

## What was accomplished

- Created `VERSION` file at repo root with single source of truth version `3.1.0`
- Updated `install.sh` to read installed version from `.exocortex/.version` (with AI_BOOTSTRAP.md fallback), read template version from cloned `VERSION` file, and print `📌 Version: <old> → <new>` during update operations
- Added conditional `WHATSNEW.md` print block to `install.sh` that displays release notes after successful install/update if the template ships the file
- Fixed `.cursor/rules/plan-orchestrate.mdc` Step 5b with one-line prompt addition: instructs the haiku save subagent NOT to include `<!-- Event Metadata -->` block (prevents duplication since `create_event.sh` already adds it)
- Extended `.github/workflows/checksums.yml` to hash `.cursor/hooks/**`, `.cursor/hooks.json`, and `VERSION` file; added them to `paths:` trigger so checksum job runs on changes
- All Phase 1 edits verified with git diff inspection — no surprises, ready for integration

## Decisions made

- Chose single `VERSION` file at repo root over scattering version strings; install.sh and future `update-all-repos.sh` will read from this source of truth
- Chose `.exocortex/.version` (dotfile) over `.exocortex/VERSION` — signals it's internal state, not user-editable, reduces config sprawl
- Dog-fooding `plan-orchestrate.mdc` for this release: parent (Opus) orchestrates phases, subagents execute work autonomously; Phase 1 used composer-2-fast for mechanical edits, Phase 1 save uses haiku-thinking hybrid Step 5b
- Kept AI_BOOTSTRAP grep fallback for `.exocortex/.version` to handle users on old install versions that never created the dotfile
- Auto-save hook uncommitted in this session, so parent runs /save manually per Step 5b. Once v3.1.0 ships and users install it, the hook will fire automatically for future saves

## Code state

- Branch: main
- Uncommitted files: 6 (VERSION, .cursor/hooks.json, .cursor/hooks/, .cursor/rules/, install.sh, .exocortex/AI_BOOTSTRAP.md, .github/workflows/checksums.yml)
- Key files touched: `VERSION` (created), `install.sh`, `.cursor/rules/plan-orchestrate.mdc`, `.github/workflows/checksums.yml`, `.exocortex/AI_BOOTSTRAP.md`
- Tests: not run yet (Phase 4 will run integration suite)

## What's next

- Phase 2 (gpt-5.3-codex subagent): add test T09 (hooks copy + chmod enforcement) and T10 (user-modified hook preserved on re-install) to `tests/run_tests.sh`; create `scripts/update-all-repos.sh` batch updater for users managing multiple exocortex clones
- Phase 3 (claude-4.5-haiku-thinking subagent): create `CHANGELOG.md` (cumulative release history), create `WHATSNEW.md` (v3.1.0 release notes), update `README.md` with three new sections (What's Included, Plan Orchestration, Updating an Existing Install)
- Phase 4 (parent Opus): integration review, run full test suite, commit all work, tag v3.1.0, push, run `gh release create` with WHATSNEW.md body
- E1 follow-up commit: support `EXOCORTEX_LOCAL_SOURCE` env var for offline / vendored installs

## Conversation patterns

- Recurring topic: dog-fooding plan-orchestrate — every phase save exercises the same orchestration loop and hook-driven patterns the rule is designed to encode. If hybrid /save works smoothly across all 3 phases, that's strong validation that the pattern scales
- Friction: the auto-save hook itself is uncommitted in the working tree, so it cannot fire during the v3.1.0 release session itself — meta-irony noted and planned for (parent saves manually per Step 5b rules). Once shipped, future releases will use the hook automatically
- Candidate PROJECT_MEMORY: `.exocortex/.version` location convention — it's a dotfile under .exocortex/, written only by the installer, never by users, and serves as the "current installed version" for future install runs. Worth documenting once v3.1.0 ships
- Context gap: future AI sessions need to know that `WHATSNEW.md` is intentionally per-release (rewritten each release), not cumulative — `CHANGELOG.md` is the cumulative log. This distinction should go in PROJECT_MEMORY once Phase 3 ships
- Candidate skill: the orchestration pattern itself (parent phase rules, subagent phase execution, save event checkpoints, async verification) could become a reusable "multi-phase release orchestration" skill, but it's too new to abstract until Phase 4 completes

## Git State

**Last Commits:**
93e26b2 ci: run test job on all PRs, skip suite for docs-only changes
38a976d docs: expand API key section with cost, privacy, and data disclosure info
6ec9ccf security: add installer integrity verification via SHA256SUMS
22b6e46 feat: exocortex v3 — initial public release (history squashed for open-source)

**Branch:** main

**Uncommitted Changes:**
```
 M .exocortex/AI_BOOTSTRAP.md
 M .github/workflows/checksums.yml
 M install.sh
?? .cursor/hooks.json
?? .cursor/hooks/
?? .cursor/rules/
?? VERSION
```

**Diff Stats:**
```
 .exocortex/AI_BOOTSTRAP.md      |  16 ++++++
 .github/workflows/checksums.yml |   6 +++
 install.sh                      | 105 +++++++++++++++++++++++++++++++++++++++-
 3 files changed, 125 insertions(+), 2 deletions(-)
```

---

**Event:** January 01 at 12:00 AM • your-machine • your-editor • Branch: `main`


# Example Event — This Is What a Saved Event Looks Like

This file is an example only. Real events are created automatically by /save and /daily-end.
Delete this file when you're ready — it's just here to show the format.

## What Got Done
- Example: Completed feature X
- Example: Fixed bug in Y

## Key Decisions and Insights
- Example: Decided to use approach A over B because of Z

## State at Close
- Branch: main
- Working tree: clean

---

## 📅 OLDER HISTORY

For work older than 7 days, use the `/history` command.

You can also browse events manually:
```bash
ls -lt .exocortex/events/
```

Or search for keywords:
```bash
grep -r "authentication" .exocortex/events/
```

---

## 📚 RECENT WORK (Last 7 Days)

The sections above show your active work from the last 7 days. This is your **short-term memory** - the context you need to stay in flow.

For older work (7+ days), that content has been moved to **long-term memory**. Use the `/history` command to search through it.

**Phase 2 (Future):** When RAG API integration is complete, you'll be able to query semantically:
- "What did I work on related to trading psychology?"
- "Show me all authentication work across projects"
- "When did I last work on circuit breaker?"

---

**Session Status:** Active development. Event system operational.
