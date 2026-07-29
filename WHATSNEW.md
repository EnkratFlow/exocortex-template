# What's New in 3.2.1 — Legacy upgrade path fixes

This patch makes `scripts/safe-update.sh` work against repositories installed
from earlier template versions. It was driven by a twelve-repository fleet
rehearsal of 3.2.0 in which every existing repository failed one of two guards
while clean installs passed.

- A legacy target missing `.exocortex/.project-name` or `.exocortex/local` now
  updates cleanly: installer-created defaults appearing only on the rehearsal
  side are treated as approved bootstraps (exact-content checked, and verified
  again on apply), not as protected-data drift.
- Embedded editor session worktrees under `.claude/worktrees/` are runtime
  state, not update surface. They are now excluded from preflight symlink and
  hard-link scans, inventory digests, the rehearsal copy, the rollback archive,
  and changed-path evidence. This also fixes a macOS bsdtar behavior where
  unanchored exclude patterns silently stripped a nested worktree's
  protected-named paths from the rollback archive, failing reconstruction.
- Two installer-suite regression tests pin both behaviors.

This document describes packaged 3.2.1 candidate behavior. It does not prove
Git publication, a GitHub release, installation, deployment, or template
promotion.

---

# What's New in 3.2.0 — Multi-AI delivery and source-backed model routing

- `AI_START_HERE.md` is now the provider-neutral entry contract, with
  minute-scale delivery gates, model-neutral cost-aware routing, one guarded
  writer, deterministic checkpoints, local handoffs, and deny-by-default
  external egress.
- Human-facing approvals are four understandable business envelopes: local
  delivery, publication, integration/rollout, and exact-target
  production/egress. Internal reservations, one-time capabilities, UAT
  records, handoffs, and writer release no longer become repeated owner
  prompts.
- The 24 canonical command JSON files remain the behavior source and all 24
  commands are retained.
- Generated parity remains 24 portable Agent Skills, 24 Claude skills, and 24
  dedicated Cursor skills.
- Version-scoped visibility UAT verified all 24 Exocortex entries in Cursor
  Stable 3.12.30, Claude Desktop 1.24012.1 (0adcae), Kimi Code CLI 1.14.0,
  and Zed 1.12.0 stable.328 built-in Agent.
- Kimi Desktop Work 3.1.3 is explicitly separate from Kimi Code CLI and remains
  `failed` at 0/24.
- Codex and GitHub Copilot remain `compatible` with their recorded limitations.
- Windsurf remains unavailable and absent from active/default installation.
- Provider evidence now uses the version-scoped statuses `verified`,
  `compatible`, `failed`, `blocked`, and `unavailable`.
- Direct pre-C1 and C1 updates retain 51 manifest-byte-and-mode-gated migration
  protections. Customized or unknown paths remain untouched.
- A provider-neutral AI installation guide now supplies copy-paste clean-install
  and existing-repository prompts, the complete guarded apply contract, the
  two-decision local flow (disposable rehearsal, then named-target apply), the
  GitHub publication boundary, and simple accept/reject Human UAT.
- The current platform matrix records macOS as verified, Linux as pending
  final-candidate CI, WSL as Human-UAT-pending, and Git Bash/native Windows as
  unsupported.
- Active security, contributing, save, installation, upgrade, and internal
  documentation have been reconciled with deterministic drift tests.
- Model freshness now uses a configured official-source registry, normalized
  advisory catalog, offline validation, quarantine, exact-surface
  availability, and measured cost per successful completion.
- The packaged catalog has zero eligible models and zero verified evaluation
  profiles. New or cheaper models cannot route until a separately reviewed
  admission and fresh local availability evidence exist.
- Source purpose, retrieval digest, refresh interval, partial-observation
  scope, duplicate keys, conflicting observations, and exact expiry boundaries
  fail closed.
- Prospective discovery now compares an immutable catalog-bound baseline with
  a definition-identical refreshed source snapshot, merges only role-authorized
  facts, and rejects duplicate sources or conflicting facts across files.
- Existing-repository collisions can now converge through a deterministic
  target-specific plan and the distinct one-time
  `apply_template_reconciliation` capability. Ordinary update authority cannot
  be reused.
- Installer and updater integrity now binds reviewed file modes, rejects
  candidate symlinks and external hard-linked targets, preserves mode-only
  local customization, emits durable identity-verified private code-plane-only
  rollback archives, proves live-fault rollback removes added paths, and
  verifies the complete applied code plane against its disposable rehearsal.

All provider UAT was discovery-only: no command or model request was executed,
and no repository authority was granted.

This document describes packaged 3.2.0 candidate behavior. It does not prove
Git publication, a GitHub release, installation, deployment, or template
promotion.

---

Everything below this line is preserved historical release documentation. Its
old commands, flags, counts, model defaults, and provider claims describe those
earlier versions and are not current operator instructions. Use the root
`README.md`, `SECURITY.md`, and `.exocortex/docs/AI_INSTALLATION.md` for the
current path.

# What's New in 3.1.9

This release switches the Anthropic fallback model from haiku to sonnet across the memory scripts.

What changed:

- `.exocortex/scripts/check_keys.py`, `get_rightnow_memory.sh`, `get_shortterm_memory.sh`, `get_longterm_memory.sh`, and `_api_helpers.py` now default `ANTHROPIC_MODEL` to `claude-sonnet-4-6`
- `MEMORY_TIERS.md`, `docs/architecture.md`, `docs/implementation.md`, `docs/SUBCONSCIOUS_ARCHITECTURE.md`, and `docs/memory-system.md` updated to match
- Primary path (OpenAI `gpt-4o-mini`) is unchanged
- Override remains via `.exocortex/.env`: set `ANTHROPIC_MODEL=claude-3-haiku-20240307` to keep the old fallback

Heads up on cost: the Anthropic fallback now costs roughly 3x more per call (sonnet ~$3/$15 per MTok input/output vs haiku ~$1/$5). The fallback only fires when no `OPENAI_API_KEY` is set or OpenAI returns an error, so for most users the bill impact is minimal. If you rely on the Anthropic side, pin haiku via `.env`.

---

# Previous: 3.1.8

Bug fix in `generate_context.sh`. The event loop used `for FILE in $EVENTS`, which word-splits on whitespace, so any project path containing a space silently produced a `SESSION_CONTEXT.md` with the correct event count but all event bodies blank. Switched to `while IFS= read -r FILE; ... done <<< "$EVENTS"`. Added T19 regression test.

---

# Previous: 3.1.7

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
