# Backlog

> Items under investigation. Moved here from INTERRUPTS after grooming.
> Run `/refine-backlog` to promote items to TODO.

## Plan-orchestrate / hooks follow-ups (v3.1.0+)

- **hooks.json relative path for global installs.** `.cursor/hooks.json` registers `./hooks/auto-save-phase.sh`. When the file is copied to `~/.cursor/hooks.json` (global install), Cursor may resolve `./hooks/` relative to its own cwd, not the rules dir. Verify behaviour and either switch to an absolute path (`$HOME/.cursor/hooks/auto-save-phase.sh`) or document the constraint.
- **`.cursor/agents/` install handling.** `install.sh` copies `.cursor/agents/` but the directory is empty in the template. Decide whether to remove the line (simpler) or keep it as a placeholder for future agent definitions.
- **`auto-save-phase.sh` jq fallback robustness.** The script falls back to grep if `jq` is missing. Test on a clean Linux box with no `jq` installed; confirm the grep path actually parses the stdin shape Cursor sends.
- **`GLOBAL_PLAN_HOOK_STATUS` cosmetic.** During UPDATE mode `install.sh` prints `(global: skipped (non-interactive))` even if the global rule was previously installed. Should display `already installed` consistently.
- **Snapshot mechanics docstring.** `tests/helpers.sh::run_install` now layers HEAD → staged → unstaged → untracked-but-not-gitignored. Add a short docblock listing the layering order so future contributors don't accidentally drop a layer.

## Codex adapter install requirements

- **Install Codex command bridge for all Exocortex commands.** Add an installer adapter that writes repo-root `AGENTS.md` and `.agents/skills/{command}/SKILL.md` for every `.exocortex/commands/*.json` command. The Codex skills should be generated from the command specs, preserve command descriptions, and instruct Codex to read `.exocortex/AI_BOOTSTRAP.md` before executing the matching JSON step protocol.
- **Keep IDE adapters isolated.** Codex install output must live only in `AGENTS.md` and `.agents/skills/`. It must not modify `.cursor/`, `CLAUDE.md`, VS Code files, or shared `.exocortex/commands/*.json` unless the user explicitly selects those adapters.
- **Protect existing custom files.** The installer must not overwrite an existing `AGENTS.md` or `.agents/skills/*/SKILL.md` without detecting local edits and preserving/merging user content. In update mode, print a clear summary of created, preserved, skipped, and changed files.
- **Generate safe write scopes.** Skills for write-capable commands (`save`, `interrupt`, `groom`, `refine-backlog`, `prioritize`, `daily-end`, `weekly-review`, `monthly-review`, `pattern-review`, `init-exocortex`) must declare exactly which `.exocortex/` files they may write and require approval before applying changes. Read-only commands must say they are read-only.
- **Preserve secret safety.** `check-keys` and any key-related Codex skill must repeat the no-values rule: never read, print, grep, cat, log, or echo raw API keys, tokens, webhook URLs, or secrets.
- **Support all-command install.** Provide a `--adapter codex --commands all` path, and make the default Codex adapter install all currently defined commands unless the user passes an explicit command allowlist.
- **Add tests.** Add installer tests that verify all `.exocortex/commands/*.json` files produce matching `.agents/skills/{command}/SKILL.md`, no Cursor/Claude files change during Codex-only install, and rerunning the installer is idempotent.
