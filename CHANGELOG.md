# Changelog

All notable changes to this project will be documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.3.0] - 2026-09-05

### Security

- **Public-template privacy boundary** — current source, immutable candidate
  trees, every commit, transient blob and path in the exact reviewed release
  slice, merge messages, and annotated tag
  objects now reject high-confidence personal host, home-path, private-network,
  tailnet-hostname, non-public-email, and personal Git-identity disclosures
  in common UTF-8 and UTF-16 text forms without rendering matched values.
  Generic credential-registry metadata is exact-digest locked so local
  customization cannot silently enter a public candidate.
- **Provider adapter cleanup** — replaced private machine capacity and workload
  notes with a generic resource-aware verification policy.

### Added

- **Guarded local-delivery envelopes** — a single bounded local business
  decision can bind the exact repository, base, worktree, path set, writer,
  reviewer, verification plan, expiry, rollback, and exclusions without
  turning internal reservations or one-time capabilities into repeated human
  prompts.

### Changed

- **Evidence-bound delivery lifecycle** — developer verification, independent
  review, QA/SIT, and Human UAT now carry exact transition provenance. Human
  UAT records the owner decision against the sealed candidate, and guarded
  completion creates one local event and handoff before releasing the writer.
- **Credential-blind source handling** — local protocol inputs and public
  candidate materialization reject credential-shaped paths before content
  access while still accounting for ordinary untracked source and ignored
  non-sensitive source dirt.

### Fixed

- **Release-slice closeout** — a tagged merge now uses its first parent as the
  reviewed candidate boundary while retaining the previous published tag as
  the version and ancestry anchor. Hosting-provider identity headers on the
  merge commit are excluded from template-payload scanning; its message,
  non-merge candidate identities, transient objects, complete tree, and tagger
  remain checked. Older already-public history is neither reclassified as a
  new release payload nor claimed clean.
- **Tamper-resistant recovery and replay** — duplicate-key JSON, wrong-root
  envelopes, altered transition or completion journals, forged gate evidence,
  missing completion records, and mismatched capabilities now fail closed.
  Exact interrupted operations remain recoverable and exact completed requests
  remain idempotent without rewriting durable state.

## [3.2.9] - 2026-08-08

### Changed

- **Judgment-led model routing** — the accountable parent selects the correct
  model using expected cost through a verified result, applies the same rule to
  every subagent, reports route and ETA without requesting routine approval,
  and treats the formal catalog as optional empirical evidence.
- **Command invocation policy** — 11 read-only orientation and analysis
  commands are model-discoverable; 13 commands involving records, planning,
  credential-adjacent checks, bootstrap, or cross-project boundaries remain
  explicitly human-triggered. All 72 adapters remain thin and non-authorizing.
- **Living project status** — added a linked current-status page separating the
  published baseline, local candidate, verification state, blockers, and next
  work.

### Security

- **Public release boundary** — a metadata-only checker denies protected
  project data, environment files, secret-shaped material, and transient blobs
  added then deleted within a candidate range without printing matched content.
- **Installer/update environment reduction** — candidate-owned validation runs
  with an explicit sanitized environment, and the installer rejects forbidden
  tracked or untracked source data before target mutation.
- **Release and CI hardening** — pull requests always produce the required
  safety check, third-party Actions are pinned to immutable commits, and
  release closeout requires an annotated exact-main tag plus a reviewed
  baseline range.
- **Verifiable release authenticity** — public installation now requires the
  GitHub immutable-release attestation for the exact
  `EnkratFlow/exocortex-template` release and an attested `SHA256SUMS` release
  asset before any downloaded installer or updater is executed.
- **Real tag-event verification** — the quick GitHub workflow now fetches the
  exact remote annotated tag object into an isolated ref namespace before
  validating it, covering GitHub checkout's peeled-tag event shape without
  weakening the direct-tag or baseline checks.

## [3.2.8] - 2026-08-05

### Changed

- **Plain-English execution contract** — agents now state the outcome, scope,
  exclusions, estimate, checks, and model routing before substantial work, and
  pause when a new long test, material estimate increase, or scope/risk change
  appears.
- **Lean cost-aware orchestration** — one accountable parent with no delegate
  is the default; delegation and independent review are added only for a
  concrete bounded need.
- **Right-sized verification** — documentation and event changes use focused
  checks, while the complete Exocortex safety suite runs once for an unchanged
  exact candidate instead of repeating on pull request, merged main, and tag.
- **One-decision AI installation/update** — one plain-language local-delivery
  decision can cover rehearsal, named-target apply, verification, completion
  record, and rollback while the displayed target and scope remain unchanged.

### Fixed

- **Recursive local memory** — approved file-changing tasks require one local
  completion event; `/save` remains manual for ordinary chat, newer events
  produce an explicit stale-Session-Context warning, and event recording no
  longer accepts or performs Session Context refresh authority. Refresh is a
  separate guarded protected-memory operation.
- **Append-only event collisions** — two events created in the same second now
  receive distinct filenames instead of overwriting the first event.
- **Stale event guidance** — removed obsolete automatic timers, Git-hook event
  creation, provider-specific behavior duplication, and implicit context
  regeneration from active documentation.

### Tests

- Added focused coverage for event uniqueness, event-helper context-refresh
  denial, explicit separate context refresh, freshness warnings, right-sized CI triggers, and
  the plain-English documentation contract.

## [3.2.7] - 2026-08-04

### Changed
- **AI-first public setup** — the README now starts with separate copy-paste
  prompts for a new installation and an existing-repository update instead of
  mixing those workflows with the advanced safety contract.
- **Memory-preserving update guidance** — the existing-repository prompt says
  explicitly that the current repository remains the target, a release clone
  is source-only, and project memory and local data must remain byte-for-byte
  unchanged.
- **Manual fallback and platform truth** — concise macOS, Linux, and WSL
  verification commands remain available, while Git Bash and native Windows
  shells remain clearly unsupported rather than being advertised without
  evidence.

### Tests
- Updated the active documentation contract to keep the public README concise
  while retaining all detailed installer, updater, collision, rollback, and
  platform invariants in the authoritative installation guide.

## [3.2.6] - 2026-08-03

### Fixed
- **Project-root memory references** — required project memory, session,
  decision, lesson, persona, and quick-reference paths now resolve explicitly
  from the project root. Optional generated session context is labeled as
  optional.
- **Authority-aware follow-up capture** — read-only work reports newly found
  tasks in chat and updates `.exocortex/TODO.md` only when the current task
  authorizes that local write.
- **Cost-aware CI triggers** — feature branches no longer run duplicate push
  and pull-request suites. Superseded runs cancel only within the same pull
  request, while `main` and version-tag runs use unique groups and retain their
  own evidence.

### Tests
- Revalidated generated command adapters, documentation and release-state
  contracts, complete checksums and file modes, and workflow structure. The
  complete Phase B suite remains the required GitHub CI gate before merge.

## [3.2.5] - 2026-08-01

### Fixed
- **Legacy adapter discovery** — updates now recognize 24 old Claude command
  wrappers, its legacy persona wrapper, and four obsolete Cursor rule files.
  Manifest-owned, byte-and-mode-matching files retire only after their current
  canonical replacement has been installed; customized or unknown files remain
  in place with a path-only collision finding.
- **Project-owned Cursor rules** — root `.cursorrules` is now safety-checked,
  included in update rehearsal and rollback evidence, and scanned for known
  obsolete command mechanics. Ordinary updates never copy, delete, normalize,
  or manifest-track it; an exact reviewed reconciliation is required to change
  it.

### Tests
- Added regression coverage for legacy Claude and Cursor retirement ordering,
  project-owned root Cursor guidance preservation, archival, and
  reconciliation-plan binding.

## [3.2.4] - 2026-08-01

Patch release closing a legacy session-context backup filename gap found while
preparing the first real existing-repository update.

### Fixed
- **Legacy backup-family protection** — the direct
  `.exocortex/SESSION_CONTEXT_BACKUP_*.md` family is now protected project
  data everywhere the exact `.backup` sidecar is protected: installation,
  manifests, update rehearsal, integrity inventories, reconciliation, and
  private restore archives. This does not broadly exempt arbitrary backup
  files.
- **Tracked legacy-sidecar warning** — the updater preserves already-tracked
  legacy sidecars and reports the condition without changing Git tracking.

### Tests
- Added legacy source/target preservation, manifest, tracking-warning,
  reconciliation-rejection, code-plane, and restore-archive regression
  coverage.

## [3.2.3] - 2026-08-01

Patch release closing a project-memory backup sidecar gap found during a
disposable existing-repository upgrade rehearsal.

### Fixed
- **Exact session-context backup protection** —
  `.exocortex/SESSION_CONTEXT.md.backup` is now protected project data. The
  installer never copies or manifest-tracks it; the safe updater excludes it
  from rehearsal, code-plane inventory, reconciliation, and private restore
  archives; and the reconciliation planner rejects it as an effect path.
- **Checksum and Git-ignore parity** — public checksum CI and the installed
  `.exocortex/.gitignore` use the same exact sidecar classification, preventing
  a later code-plane mismatch or accidental new Git tracking.
- **Tracked-sidecar warning** — when a project already tracks that optional
  sidecar, the updater reports the condition and preserves it. It never
  auto-untracks files or rewrites Git history.

### Tests
- Added source-sidecar, target-preservation, manifest, Git-ignore,
  reconciliation-rejection, and restore-archive regression coverage.
- Re-ran the full installer/update suite, Phase B protocol tests, and a
  disposable downstream-project reconciliation rehearsal with protected-data
  and archive checks.

## [3.2.2] - 2026-07-31

Patch release preventing project instruction files and customized command
surfaces from silently overriding the canonical Exocortex command contracts.

### Added
- **Explicit command-spec precedence** — `AI_START_HERE.md`, the bootstrap and
  command-system references, and the installed provider instruction adapters
  now state that `.exocortex/commands/<name>.json` is the sole command-flow
  behavior source beneath the entry contract. A conflicting project
  instruction is reported once and is never combined with the JSON flow.
- **Deterministic command-drift findings** — preserved customized authority
  paths and known stale root-instruction patterns are reported by path only.
  Dry runs surface `EXOCORTEX_COMMAND_RECONCILIATION_REQUIRED`; ordinary
  guarded apply stops before consuming its one-time capability until a
  reviewed target-specific reconciliation clears the finding.
- **Release-state closeout check** — `scripts/check-release-state.sh` verifies,
  without network access or repository mutation, that clean local `main`,
  cached `origin/main`, `v<VERSION>`, tag ancestry, packaged version, and the
  published `SHA256SUMS` digest agree.

### Changed
- **Exact public update source** — active installation and update guidance now
  pins `v3.2.2`, verifies the peeled release commit and published candidate
  digest, rehearses with `safe-update.sh --dry-run`, and keeps guarded apply a
  separate named-target action.
- **Release closeout procedure** — contributors must preserve a dirty primary
  checkout, fast-forward a clean local `main`, publish the exact release
  evidence, run the read-only closeout check, and verify a fresh tag clone.

### Tests
- Added command-authority collision, stale-guidance preservation,
  idempotency, pre-consumption denial, exact-tag documentation, tag/version
  CI, and read-only release-state regression coverage.

## [3.2.1] - 2026-07-29

Patch release fixing the existing-repository upgrade path, discovered during a
twelve-repository fleet rehearsal of 3.2.0. Clean installs were unaffected.

### Fixed
- **Legacy protected-scaffolding adoption, dry-run and apply** — a target
  predating `.exocortex/local` no longer fails `safe-update.sh` with
  "protected data changed in rehearsal", including the apply case where
  provisioning the apply capability itself creates a partial
  `.exocortex/local/protocol` tree: protected comparison of `.exocortex/local`
  now tracks runtime records (files) exactly while ignoring installer
  scaffolding directories, and empty protected directories adopted from the
  reviewed installer are content-verified bootstraps treated as absent in
  digest evidence and re-verified after apply. `.exocortex/.project-name` is
  deliberately NOT bootstrapped: project identity is owner-approved, never
  inferred (per `UPGRADE_MANIFEST.md`), so a legacy target must be seeded once
  with `init-project.sh` and the updater fails closed with that exact
  instruction otherwise.
- **Runtime editor worktrees excluded from the update surface at any depth** —
  `.claude/worktrees` (editor session state, whether a directory, file, or
  symlink, at any nesting depth) previously tripped the update-surface symlink
  guard, and on macOS bsdtar's unanchored `--exclude` patterns stripped a
  nested worktree's protected-named paths from the rollback archive while the
  root-anchored code-plane digest still counted them, failing archive
  reconstruction. The exclusion is now segment-matched identically across
  preflight scans, inventory digests, the rehearsal copy, the rollback archive
  and its member safety check, changed-path evidence, and the reconciliation
  planner's target-surface digest, so no form or depth of session worktree can
  block, skew, or leak into update evidence.

### Added
- Installer-suite regression tests: legacy scaffolding bootstraps in dry-run;
  a guarded apply succeeds on a legacy target whose capability created a
  partial protocol tree; a missing `.project-name` fails closed with the
  seeding instruction; symlinked and nested worktrees are absent from all
  rollback evidence; a non-directory `.claude/worktrees` never reaches the
  changed-path evidence.

## [3.2.0] - 2026-07-27

Historical release entries below preserve what earlier versions shipped. Their
installation commands and support claims are not current instructions; the
root `README.md`, `SECURITY.md`, and
`.exocortex/docs/AI_INSTALLATION.md` are authoritative.

This entry describes the packaged local release candidate. It does not prove
that a Git commit, tag, GitHub release, deployment, or template promotion
exists.

### Added
- **Provider-neutral entry and delivery protocol** — added
  `AI_START_HERE.md`, minute-scale Kanban/SDLC gates, model-neutral
  capability/risk/cost routing, public-v2 work items, one-writer authority,
  checkpoint/handoff separation, and deny-by-default external egress.
- **AI-guided installation and update** — added copy-paste clean-install and
  existing-repository prompts for coding agents with local filesystem and
  terminal access. The AI must pin and verify the template and rehearse before
  one named-target local apply.
- **Business-level approval envelopes** — human-facing decisions are now
  local delivery, publication, integration/rollout, and exact-target
  production/egress. Work-item bookkeeping, writer reservations, one-time
  technical capabilities, UAT recording, local handoffs, and writer release
  remain fail-closed internal mechanics instead of repeated owner prompts.
- **Safe existing-repository migration** — added complete protected-data
  inventory, hard-link denial, durable identity-verified private code-plane-only
  restore archives, complete changed-path evidence, guarded apply, retry,
  idempotency, exact post-apply rehearsal parity, live-fault rollback, and
  one-target-at-a-time rules.
- **Platform evidence matrix** — macOS is verified; Linux requires
  final-candidate CI; WSL requires Human UAT; Git Bash and native Windows remain
  unsupported.
- **Documentation contract tests** — active documentation now fails
  deterministically on obsolete manual-copy, credential-creation,
  remote-pipe-install, save-as-checkpoint, stale test-count, wrong upgrade-link,
  unsupported-platform, implicit-approval, or bundled-publication guidance.
- **Source-backed model registry** — added configured-official-source
  inventory, normalized advisory catalog, offline discovery validation,
  quarantine, exact-surface availability, source freshness and purpose checks,
  prospective baseline-versus-refreshed snapshot comparison, role-authorized
  fact merging, and digest-bound measured cost-per-success routing.
- **Target-specific update reconciliation** — added deterministic
  non-mutating plan preparation and the distinct one-time
  `apply_template_reconciliation` path for reviewed candidate adoption,
  reviewed objects, and managed retirements after ordinary update collisions.

### Changed
- **Provider-native command parity** — the 72 generated command adapters are
  now 24 portable Agent Skills, 24 Claude skills, and 24 dedicated Cursor
  skills. All remain thin, manual-only pointers to the canonical JSON commands.
- **Accepted provider visibility evidence** — Cursor Stable 3.12.30, Claude
  Desktop 1.24012.1 (0adcae), Kimi Code CLI 1.14.0, and Zed 1.12.0 stable.328
  built-in Agent each passed version-scoped native visibility UAT for all 24
  Exocortex entries. No command was executed during those checks.
- **Kimi surface distinction** — Kimi Desktop Work 3.1.3 is recorded separately
  as `failed` at 0/24. That result does not invalidate the verified Kimi Code
  CLI result.
- **Remaining evidence limits** — Codex and GitHub Copilot remain `compatible`;
  Codex selector UAT is pending and the passing Copilot client version was not
  captured. Cursor 3.6.21's earlier portable-adapter failure remains historical
  version-and-family evidence.
- **Windsurf status** — removed Windsurf from active/default support and
  installation because no installed version was available for Human UAT.
  Older Windsurf entries below remain historical release records.
- **Routing admission** — the packaged catalog contains public candidate facts
  only: zero eligible models and zero verified evaluation profiles. Admission
  requires a separately reviewed catalog update and fresh project-local
  current-surface availability evidence.

### Migration
- Preserved 26 earlier Cursor/GitHub retirement mappings and added 25 Windsurf
  retirements. Removal requires prior manifest ownership, byte equality, and
  the reviewed legacy text mode; customized or unknown files remain with
  `EXOCORTEX_ADAPTER_COLLISION_PRESERVED`.

### Tests
- Added deterministic provider-matrix, frontmatter, generated-path,
  pre-C1/C1 direct-update, collision-preservation, manifest-uniqueness, and
  idempotency coverage.
- Added source digest/purpose/freshness, partial observation, duplicate-key,
  cross-observation conflict, expiry-boundary, availability-version,
  quarantine, reconciliation-plan, and one-time exact-effect coverage.
- Added checksum-bound file-mode, source-topology, restrictive-umask,
  mid-copy fault containment, private archive, exact rollback, and pre- and
  post-consumption race coverage.

[3.3.0]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.3.0
[3.2.9]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.9
[3.2.8]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.8
[3.2.2]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.2
[3.2.7]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.7
[3.2.6]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.6
[3.2.5]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.5
[3.2.4]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.4
[3.2.3]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.3
[3.2.1]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.1
[3.2.0]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.2.0

## [3.1.9] - 2026-05-18

### Changed
- **Default Anthropic fallback model** — `.exocortex/scripts/check_keys.py`, `get_rightnow_memory.sh`, `get_shortterm_memory.sh`, `get_longterm_memory.sh`, and `_api_helpers.py` now default the Anthropic fallback to `claude-sonnet-4-6` instead of `claude-3-haiku-20240307`. The primary provider path (OpenAI `gpt-4o-mini`) is unchanged. Users who want the prior fallback can pin `ANTHROPIC_MODEL=claude-3-haiku-20240307` in `.exocortex/.env`.
- **Documentation** — `MEMORY_TIERS.md`, `docs/architecture.md`, `docs/implementation.md`, `docs/SUBCONSCIOUS_ARCHITECTURE.md`, and `docs/memory-system.md` now describe sonnet as the fallback.

### Upgrade Notes
- The Anthropic fallback costs roughly 3x more per call than the previous haiku default (sonnet ~$3/$15 per MTok input/output vs haiku ~$1/$5). The fallback only fires when no `OPENAI_API_KEY` is set or OpenAI returns an error. If you rely heavily on it, pin `ANTHROPIC_MODEL=claude-3-haiku-20240307` in `.exocortex/.env` to retain the prior cost profile.

[3.1.9]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.9

## [3.1.8] - 2026-05-12

### Fixed
- **`generate_context.sh` paths-with-spaces bug** — the event loop used `for FILE in $EVENTS` which word-splits on whitespace, so project paths containing a space (e.g. `My Project/.exocortex/events/...`) silently produced an empty SESSION_CONTEXT (event count correct, all event bodies blank). Switched to `while IFS= read -r FILE; ... done <<< "$EVENTS"` so spaced paths survive intact.

### Tests
- Added T19: installs into a project at a path containing spaces, writes an event with a canary string, runs `generate_context.sh`, and asserts the canary appears in `SESSION_CONTEXT.md`. Regression coverage for the word-split bug.

[3.1.8]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.8

## [3.1.7] - 2026-05-02

### Added
- **Safe update script** - added `scripts/safe-update.sh`, a customer-safe updater that creates a restore archive, rehearses the update in a temporary copy, verifies protected memory/data files are unchanged, shows the diff summary, and asks before applying the real update.

### Tests
- Added coverage that the safe updater can run in dry-run mode, creates a backup, preserves real project files, and does not apply changes without approval.

[3.1.7]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.7

## [3.1.6] - 2026-05-02

### Changed
- **README accuracy** - updated command counts, test-suite expectations, backlog flow, editor support, and Codex support wording.
- **Command system reference** - refreshed `.exocortex/COMMAND_SYSTEM.md` so it describes all 23 commands, editor-neutral JSON execution, backlog flow, and current adapter reality.

### Tests
- Added coverage that prevents stale README claims about "20 Workflow Commands", old 8-test output, missing Codex guidance, or missing unknown-IDE setup guidance from returning.

[3.1.6]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.6

## [3.1.5] - 2026-05-02

### Changed
- **Plan-orchestrate branching guidance** - softened the new branching/rollback section so it is recommended for production or team code-shipping phases, while solo/local/trivial work can stay on the current branch when that matches the user's workflow.
- **Plan-orchestrate testing guidance** - changed strict completion language into recommended acceptance criteria, with practical wording for coverage tooling, smoke checks, UI checks, and skipped layers.

### Tests
- Added coverage that prevents the public template from reintroducing hard direct-to-main bans, mandatory subagent push assumptions, or hard UI E2E requirements.

[3.1.5]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.5

## [3.1.4] - 2026-04-30

### Added
- **Other IDE adapter guidance** - added `.exocortex/docs/IDE_INTEGRATION_GUIDE.md` with a universal adapter prompt for Codex, Zed, VS Code, Cursor, Claude, Windsurf, and unknown AI-capable editors.
- **Installer onboarding output** - `install.sh` now prints the practical other-IDE setup instructions directly in the terminal instead of only pointing users to documentation.

### Tests
- Added coverage proving the IDE guide exists, installs into fresh projects, and the installer prints the copy-paste adapter prompt.

[3.1.4]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.4

## [3.1.3] - 2026-04-30

### Fixed
- **Save bridge cleanup** - removed the legacy "ask one question" save flow from the Claude save bridge. The bridge now delegates to `.exocortex/commands/save.json`, keeping the JSON command as the source of truth.
- **Save documentation cleanup** - updated `SNIPPETS.md` and `EVENT_SYSTEM_USAGE.md` so they describe the current autonomous event-based `/save` flow.

### Tests
- Added a regression test that fails if active save docs or bridge files reintroduce the legacy focus prompt.

[3.1.3]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.3

## [3.1.2] — 2026-04-30

### Fixed
- **`/ai-export` is now project-generic** — removed downstream-project-specific file names from `.exocortex/commands/ai-export.json`. The command now discovers the current project structure and exports evidence-backed architecture from files that actually exist in the installed repo.
- **Installer data-plane boundary hardened** — `install.sh` no longer copies or manifest-tracks project memory/state files from the public template. Existing user data remains untouched, and fresh installs receive blank local stubs where needed.
- **Public template data cleaned** — removed live template session context and release checkpoint events from the public install surface; only the example event remains.

### Security
- **User data preservation is now enforced by tests** — added coverage proving Exocortex data-plane files are not tracked in `.exocortex/.install-manifest`, reducing the risk that future template updates overwrite local memory, events, todos, lessons, or project state.
- **Template privacy guard added** — added coverage that prevents live session context or real event markdown files from shipping in the public template.

### Upgrade Notes
- If you installed a version where `/ai-export` mentioned project-specific files, rerun the installer from your project root after this release:
  use the exact pinned local release procedure documented in
  `.exocortex/docs/AI_INSTALLATION.md`. The former remote pipe-to-shell command
  is intentionally retired.
- The update preserves user-modified files and never overwrites `.exocortex/events/`, `.exocortex/SESSION_CONTEXT.md`, `.exocortex/TODO.md`, `.exocortex/LESSONS.md`, or `.exocortex/PROJECT_MEMORY.md`.

[3.1.2]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.2

## [3.1.1] — 2026-04-22

### Added
- **Model pins section** in `.cursor/rules/plan-orchestrate.mdc` — single source of truth table mapping named pins (`<ORCHESTRATOR>`, `<SCAFFOLDER>`, `<EXECUTOR>`, `<UI_IMPLEMENTER>`, `<TEST_WRITER>`, `<SAVE_FORMATTER>`, `<DOC_DRAFTER>`, `<DEEP_REVIEWER>`) to current model slugs. Bump a model in one place; every reference downstream picks it up. The Step 3 routing table is now an explicit duplicate view; the pin table wins on drift.

### Changed
- **Step 5b `/save` prompt template strengthened** — replaced the brief "Do NOT include any metadata block" guidance with a `CRITICAL FORMATTING RULES` block that enumerates every forbidden field (`<!-- Event Metadata -->`, `timestamp:`, `machine:`, `editor:`, `project:`, `branch:`), pins the file's first line to the `# Phase checkpoint —` header, and lists the five required sections explicitly. Materially reduces duplicate-metadata events when the haiku save subagent drafts an event body.
- **Step 5b `Task` example** now references `model=<SAVE_FORMATTER>` (with an inline current-value reminder) instead of the literal model slug, so future haiku-tier bumps need a single edit at the top of the rule.

[3.1.1]: https://github.com/EnkratFlow/exocortex-template/releases/tag/v3.1.1

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
