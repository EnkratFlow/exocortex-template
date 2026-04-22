What's new in 3.1.0
─────────────────────

✦ Plan orchestration is now a global Cursor rule. Plan-class tasks
  decompose into named phases, each phase runs on the cheapest model
  that can do the job, Opus stays for orchestration. Typical cost
  saving: 3-5x versus all-Opus.

✦ Auto-save phase hook. When a phase subagent finishes
  ("Phase N: ..."), an exocortex `/save` is injected automatically
  so checkpoints are never forgotten.

✦ Batch updater. Run `bash scripts/update-all-repos.sh ~/code` to
  bring every exocortex-installed project under a directory up to
  this template version (interactive by default; `--yes` to skip
  prompts, `--dry-run` to list only).

Read the full notes:
  https://github.com/EnkratFlow/exocortex-template/blob/main/CHANGELOG.md

Optional: during install you'll be asked whether to also install
the plan-orchestrate rule and the auto-save hook globally to
~/.cursor/ so they apply to non-exocortex projects too. Default is
yes; press Enter to accept.
