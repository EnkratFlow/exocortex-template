# What's New in 3.1.5

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
