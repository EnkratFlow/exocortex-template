# Backlog

> Items under investigation. Moved here from INTERRUPTS after grooming.
> Run `/refine-backlog` to promote items to TODO.

## Plan-orchestrate / hooks follow-ups (v3.1.0+)

- **hooks.json relative path for global installs.** `.cursor/hooks.json` registers `./hooks/auto-save-phase.sh`. When the file is copied to `~/.cursor/hooks.json` (global install), Cursor may resolve `./hooks/` relative to its own cwd, not the rules dir. Verify behaviour and either switch to an absolute path (`$HOME/.cursor/hooks/auto-save-phase.sh`) or document the constraint.
- **`.cursor/agents/` install handling.** `install.sh` copies `.cursor/agents/` but the directory is empty in the template. Decide whether to remove the line (simpler) or keep it as a placeholder for future agent definitions.
- **`auto-save-phase.sh` jq fallback robustness.** The script falls back to grep if `jq` is missing. Test on a clean Linux box with no `jq` installed; confirm the grep path actually parses the stdin shape Cursor sends.
- **`GLOBAL_PLAN_HOOK_STATUS` cosmetic.** During UPDATE mode `install.sh` prints `(global: skipped (non-interactive))` even if the global rule was previously installed. Should display `already installed` consistently.
- **Snapshot mechanics docstring.** `tests/helpers.sh::run_install` now layers HEAD → staged → unstaged → untracked-but-not-gitignored. Add a short docblock listing the layering order so future contributors don't accidentally drop a layer.
