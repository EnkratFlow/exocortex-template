# What's New in 3.1.7

This release adds a safer customer update path.

What changed:

- Added `scripts/safe-update.sh`
- The safe updater creates a restore archive before touching anything
- It rehearses the update in a temporary copy first
- It verifies protected Exocortex memory/data files are unchanged
- It shows the rehearsal diff and asks before applying the real update
- It supports `--dry-run`, `--yes`, `--template`, and `--backup-dir`

This is the foundation for future npm/npx update tooling.

---

# Previous: 3.1.6

This release cleans up public documentation so it matches the current template.

What changed:

- Updated README command counts, test counts, backlog flow, and editor support notes
- Clarified that Codex works today through the universal adapter prompt, while native `.agents/skills/*` bridges are planned
- Updated the command system reference to describe all 23 commands and the editor-neutral JSON command protocol
- Added a regression test that catches stale README claims about command counts, test counts, Codex, and unknown IDE setup

This is a documentation-only release. It does not add native Codex bridge files yet.

---

# Previous: 3.1.5

This release softens the plan-orchestrate branch and testing guidance so it works better as a public template default.

What changed:

- Added public-safe branching and rollback guidance for production or team code-shipping phases
- Kept solo/local/trivial work exempt when that matches the user's workflow
- Avoided assuming every subagent can commit and push to a remote
- Changed hard testing requirements into recommended acceptance criteria with practical skip language
- Added tests so future edits do not reintroduce too-strict public-template wording

The key rule is simple: stronger orchestration discipline should help teams and production work without making small local work painful.

---

# Previous: 3.1.4

This release makes Exocortex easier to use from editors we do not know about yet.

What changed:

- Added `.exocortex/docs/IDE_INTEGRATION_GUIDE.md`
- Added a universal adapter prompt for Codex, Zed, VS Code, Cursor, Claude, Windsurf, and unknown AI editors
- `install.sh` now prints the useful other-IDE setup instructions directly in the terminal
- Added tests so the guide is installed and the terminal instructions stay visible

The key rule is simple: IDE adapters stay thin, and `.exocortex/commands/*.json` remains the source of truth.
