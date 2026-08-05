# What's New in 3.2.8 — Leaner, clearer AI delivery

- Every substantial phase now starts with a plain-English outcome, scope,
  exclusions, estimate, test duration, and model-routing summary.
- One accountable parent with no delegate is the default. Extra models and
  independent reviewers are used only for a concrete bounded need.
- AI-led installation and update now use one understandable local decision
  when the target, candidate, scope, risk, and expected result remain exact.
- Documentation and event changes use focused checks. The complete Exocortex
  safety suite runs once for the unchanged release candidate rather than again
  on merged main and the release tag.
- File-changing tasks leave one local completion event, while ordinary `/save`
  remains manual. Event creation no longer refreshes Session Context; newer
  events produce a stale-context warning, and same-second events cannot
  overwrite one another.
- Active event documentation is shorter and removes obsolete timer, Git-hook,
  provider-specific, and implicit-context behavior.

This document describes packaged 3.2.8 candidate behavior. It does not prove
Git publication, a GitHub release, installation, deployment, or template
promotion.

Everything below this line is preserved historical release documentation.

---

# What's New in 3.2.7 — AI-first installation and updates

- The public README now starts with two clear choices: install Exocortex in a
  new repository or update an existing Exocortex repository.
- Each path has a provider-neutral prompt that can be pasted into a coding AI
  with local filesystem and terminal access.
- Existing-repository updates now say explicitly that the current repository
  remains the target and all memory, events, planning, decisions, recognized
  Session Context backup sidecars, local state, and secrets remain protected
  in place.
- The CLI fallback remains available for independent verification and recovery.
- Platform claims now match evidence: macOS is verified; Linux awaits final
  candidate CI; WSL awaits bounded Human UAT; Git Bash and native Windows
  shells remain unsupported.

This document describes packaged 3.2.7 candidate behavior. It does not prove
Git publication, a GitHub release, installation, deployment, or template
promotion.

---

# What's New in 3.2.6 — Clearer entry and leaner CI

- Project memory references now resolve explicitly from the project root,
  including optional generated session context and the persona and quick
  reference documents.
- Read-only agents report newly discovered follow-ups in chat instead of being
  told to write `.exocortex/TODO.md` without authority.
- Pull-request updates run each workflow once rather than duplicating the same
  work through both push and pull-request events. Only superseded runs for the
  same pull request cancel; `main` and release-tag evidence remains distinct.
- The canonical 24 commands, provider adapters, guarded installer/update path,
  and protected project data behavior are unchanged.

This document describes packaged 3.2.6 candidate behavior. It does not prove
Git publication, a GitHub release, installation, deployment, or template
promotion.

---

# What's New in 3.2.5 — Safe legacy adapter discovery

- Updates now discover the old Claude command-wrapper family, its legacy
  persona wrapper, and four historical Cursor rules that could otherwise
  survive unnoticed after a current Exocortex upgrade.
- The migration remains conservative: it retires a legacy file only when the
  prior manifest proves template ownership and its bytes and mode are unchanged
  and the current canonical replacement is present. Customized or unknown
  files are retained and reported for reviewed reconciliation.
- Root `.cursorrules` is project-owned. It is now topology-checked and covered
  by update rehearsal and private rollback evidence, but ordinary updates never
  overwrite, remove, normalize, or manifest-track it. Known stale command
  guidance is retained and blocks ordinary live apply until reconciled.
- The installer/update and Phase B suites add deterministic coverage for this
  discovery, preservation, archive, and reconciliation behavior.

This document describes packaged 3.2.5 candidate behavior. It does not prove
Git publication, a GitHub release, installation, deployment, or template
promotion.

---

# What's New in 3.2.2 — Command authority and release alignment

- `.exocortex/commands/<name>.json` is now explicitly the sole command-flow
  behavior source beneath `AI_START_HERE.md`. Root and provider instruction
  files may point to a command specification but cannot restate or override
  it; a conflict is reported once and the JSON flow is followed without
  combining instructions.
- Existing customized instruction files remain untouched. The installer emits
  path-only findings for preserved command-authority collisions and known
  obsolete command guidance, while `safe-update.sh --dry-run` requires a
  reviewed target-specific reconciliation. Ordinary guarded apply stops
  before capability consumption while that finding remains.
- Public installation and update instructions now pin the exact `v3.2.2`
  release, verify its peeled commit and published `SHA256SUMS` digest, and
  rehearse the named target before guarded apply.
- A read-only release-state checker and deterministic fixtures catch a dirty
  or stale local `main`, tag/version drift, missing tags, and published digest
  mismatches without fetching or changing repository state.
- The 24 canonical commands and their native adapter families are retained;
  this patch corrects authority and upgrade behavior rather than removing
  commands.

This document describes packaged 3.2.2 candidate behavior. It does not prove
Git publication, a GitHub release, installation, deployment, or template
promotion.

---

# What's New in 3.2.1 — Legacy upgrade path fixes

This patch makes `scripts/safe-update.sh` work against repositories installed
from earlier template versions. It was driven by a twelve-repository fleet
rehearsal of 3.2.0 in which every existing repository failed one of two guards
while clean installs passed, then hardened by an independent adversarial
review of the first fix attempt.

- A legacy target missing `.exocortex/local` now updates cleanly in both
  dry-run and guarded apply, including the case where provisioning the apply
  capability itself creates a partial protocol tree: protected comparison of
  `.exocortex/local` tracks runtime records exactly while ignoring installer
  scaffolding directories, and installer-created empty protected directories
  are content-verified bootstraps, re-verified after apply.
- Project identity stays owner-approved: `.exocortex/.project-name` is never
  created or inferred by the updater. A legacy target is seeded once with
  `init-project.sh`; otherwise the update fails closed and says exactly that.
- Editor session worktrees (`.claude/worktrees` in any form, at any depth) are
  runtime state, not update surface. They are excluded with identical segment
  matching from preflight scans, inventory digests, the rehearsal copy, the
  rollback archive and its member checks, changed-path evidence, and the
  reconciliation planner's target-surface digest. This also fixes a macOS
  bsdtar behavior where unanchored exclude patterns silently stripped a nested
  worktree's protected-named paths from the rollback archive, failing
  reconstruction.
- Five installer-suite regression tests pin these behaviors, including a full
  guarded apply on a legacy target.

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
