# What's New in 3.1.4

This release makes Exocortex easier to use from editors we do not know about yet.

What changed:

- Added `.exocortex/docs/IDE_INTEGRATION_GUIDE.md`
- Added a universal adapter prompt for Codex, Zed, VS Code, Cursor, Claude, Windsurf, and unknown AI editors
- `install.sh` now prints the useful other-IDE setup instructions directly in the terminal
- Added tests so the guide is installed and the terminal instructions stay visible

The key rule is simple: IDE adapters stay thin, and `.exocortex/commands/*.json` remains the source of truth.
