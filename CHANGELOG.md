# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] — 2026-04-22

### Added
- **Plan-orchestrate rule** (`.cursor/rules/plan-orchestrate.mdc`) — a global Cursor rule that decomposes plan-class work into named phases, delegates each phase to the cheapest model that can do the job (composer-2-fast for mechanical edits, gpt-5.3-codex for tests/feature code, claude-4.5-haiku-thinking for docs, claude-4.6-sonnet-medium-thinking for tricky debugging), and keeps Opus for orchestration and review. Typical cost saving: 3-5x versus all-Opus.
- **Auto-save phase hook** (`.cursor/hooks.json` + `.cursor/hooks/auto-save-phase.sh`) — a `subagentStop` hook that detects a phase subagent (description matches `Phase N: ...` or `phase-N-...`) and injects a follow-up message telling the parent agent to run `/save` before the next phase. Non-phase subagents are silently ignored.
- **`VERSION` file** at the repo root — single source of truth for the template version. `install.sh` reads it to show `<old> → <new>` during updates and writes `.exocortex/.version` so future runs can compare.
- **`WHATSNEW.md` print block** in `install.sh` — if the template ships a `WHATSNEW.md`, the installer prints it after a successful install/update so users see what's new immediately.
- **`EXOCORTEX_LOCAL_SOURCE` env var** — when set to a local template directory, `install.sh` copies from that directory instead of cloning. Useful for offline installs, vendoring, and the batch updater.
- **Batch updater** (`scripts/update-all-repos.sh`) — walks a root directory, finds every `.exocortex/`-bearing project, optionally prompts before each (`--yes` to skip prompts, `--dry-run` to list only), skips dirty git trees, and runs `install.sh` per repo using `EXOCORTEX_LOCAL_SOURCE`. Useful for keeping many projects on the same template version.
- **Tests T09 and T10** in `tests/run_tests.sh` — T09 verifies hooks are copied and executable on fresh install; T10 verifies a user-modified hook script is never overwritten on re-install.

### Changed
- **`install.sh` `.cursor/` handling** — now copies `.cursor/hooks/` (manifest-aware merge) and `.cursor/hooks.json` (manifest-aware single-file merge), and runs `chmod +x` on every `.sh` under `.cursor/hooks/` after the merge.
- **Optional global install** — `install.sh` now prompts during fresh installs whether to copy `plan-orchestrate.mdc` and the hook files into `~/.cursor/` so they apply to non-exocortex projects too. Skipped silently if the global rule is already installed or stdin isn't a TTY.
- **Test helper `tests/helpers.sh::run_install`** — snapshot now layers HEAD → staged → unstaged → untracked-but-not-gitignored so new files added in the working tree (but not yet `git add`ed) are visible to the test suite. Required for shipping new files like the hooks.
- **`.github/workflows/checksums.yml`** — `paths:` trigger and `sha256sum` invocation now include `.cursor/hooks/**`, `.cursor/hooks.json`, and `VERSION` so integrity coverage stays in sync with what `install.sh` actually copies.

### Security
- Integrity check in `install.sh` (added in a previous release, expanded here) now verifies the new hook files against `SHA256SUMS` before any copy step runs.

[3.1.0]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.0
