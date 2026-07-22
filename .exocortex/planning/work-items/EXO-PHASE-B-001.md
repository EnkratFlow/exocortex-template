# EXO-PHASE-B-001 — Multi-AI delivery protocol generalization

## Status

- Lifecycle: `captured`
- Attempt: 0
- Exact planning base: `0eb3c667a505b90c9221ed768d47039a1638df5e`
- Branch: `codex/exo-phase-b-001-planning`
- Writer reservation: none
- Implementation authority: none
- Release or promotion authority: none
- Distribution: project-local planning data; never propagated to installed repositories

This is the captured human-readable Phase B planning draft. It defines the proposed destination, safeguards, and future verification without changing protocol behavior. Its contents have not yet received a refinement, readiness, or implementation acceptance.

## Why this work exists

The Mulligan pilot demonstrated that multiple AI providers can enter a repository cold, recover exact authority and state, respect one-writer and approval boundaries, reject bundled escalation, create deterministic local transition records, and complete Human UAT. Those behaviors now need to become a privacy-safe, provider-neutral Exocortex template capability rather than remain Mulligan-specific.

The goal is recursive improvement with human sovereignty: a completed delivery cycle can produce evidence and propose a better protocol, but no model may approve its own mutation, release, external action, or promotion.

## Reference binding

| Reference | Exact SHA | Use |
|---|---|---|
| Template Phase B base | `0eb3c667a505b90c9221ed768d47039a1638df5e` | Approved base for this isolated planning lane; includes the version-fallback correction |
| Observed template `main` | `c6ccd8358c6896d8456cb4aa19b09744ea44b1e8` | Containment comparison only; it does not contain the approved fallback commit |
| Accepted Mulligan record | `50cd1c3db6d69c6d16a68e8935576016b21276b2` | Accepted Human UAT history and final local reference |
| Mulligan implementation candidate | `b63463f784d3e51f47b787e29222bba91dce60e0` | Selective behavioral and test comparison |

The Mulligan references are private local evidence. No private work item, event, handoff, identity, absolute path, branch history, origin metadata, application terminology, endpoint, or authorization history may be copied into the public template.

Mulligan remains at Human UAT: QA-08 release disposition and bounded hypercare are pending, R-04 application/protocol integration is open, and no release or template-promotion claim is made.

## Desired public contract

### 1. Universal AI entry

One canonical root entry tells any AI how to:

1. Identify the repository and exact live Git state.
2. Read project-local authority and current work-item evidence.
3. Identify lifecycle state, writer reservation, tests, gates, and handoff.
4. Declare whether it is read-only support, the one approved writer, or an independent reviewer.
5. Stop before mutation or outward action when exact authority is missing.

Claude, Codex, Kimi, DeepC, Cursor, Copilot, Windsurf, and future systems use thin adapters that point to this same contract. Provider behavior may differ; authority and evidence rules do not.

### 2. Capability- and cost-aware orchestration

Normative roles:

- Deterministic tooling for Git truth, validation, searches, checksums, tests, and idempotency.
- Bounded evidence lanes for low-risk read-only inventory and comparisons.
- One accountable writer for approved compatibility-sensitive implementation.
- Independent review for security, privacy, data, migrations, architecture, finance, destructive operations, or required gates.
- A low-cost record formatter only when the parent provides a complete evidence packet.

Provider adapters may map models to these roles. No named model or provider is required for compliance. Parallelism stays at the minimum useful level, and duplicate audits stop when evidence converges.

### 3. Minute-scale Kanban lifecycle

The target flow is:

`Captured → Triaged → Refined → Ready → Reserved → Developing → Developer Verified → Independent Review → QA/SIT → UAT Ready → Human UAT → Release Ready → Awaiting Release → Deployment Approved → Deployed → Hypercare → Done`

Blocked is an explicit condition, not a hidden pause. Code, tests, a commit, or a merge do not independently mean Done.

### 4. Saves, checkpoints, and handoffs

- A narrative `/save` requires an explicit user command or confirmation and creates a project-local event describing current work; it implies neither a lifecycle transition nor external synchronization.
- A lifecycle checkpoint is different: it is created only after an authorized transition is accepted and durably recorded.
- A transition designated as checkpoint-eligible by the approved schema must create exactly one deterministic, idempotent checkpoint. An accepted transition explicitly designated non-checkpointing creates none.
- Rejected, invalid, unauthorized, blocked, stale, conflicting, read-only, test-only, support-agent, ordinary-chat, or replay activity creates no lifecycle checkpoint.
- Another model is not required merely to create a checkpoint. A lower-cost formatter may draft narrative content when appropriate, but deterministic state controls checkpoint identity.
- Handoffs are project-local by default and identify the exact base, candidate, state, evidence, writer status, gates, and first verification step.

### 5. External synchronization

Local event or checkpoint creation completes independently of external delivery.

RAG, vault, hub, network, or other external delivery requires a current, exact, destination-specific human authorization. The authorization check must pass before:

- credential lookup,
- event-content reads for delivery,
- destination initialization,
- file copy, or
- network activity.

Configuration, credentials, markers, documentation, automatic invocation, or a model assertion never grant authority.

### 6. Recursive improvement

After bounded hypercare, the system may generate a retrospective containing:

- observed friction,
- failed or duplicated work,
- routing accuracy and cost evidence,
- missing tests or safeguards,
- proposed protocol changes,
- a bounded new work item with acceptance criteria.

The retrospective is evidence, not authorization. A human accepts, rejects, or narrows the next improvement.

## Privacy and generalization contract

Transfer only:

- generic lifecycle rules,
- provider-neutral role contracts,
- generic schemas and validators,
- generic scripts,
- deterministic tests,
- fictional fixtures using reserved example domains.

Never transfer:

- personal or account identities,
- product/application terminology,
- absolute paths,
- private work-item IDs, events, handoffs, approvals, or event content,
- source branches, SHAs, session/reservation IDs, or origin fingerprints,
- real endpoints, vault locations, or organization-specific credential names,
- secrets or secret-derived data.

The later candidate must pass automated prohibited-data searches, data-plane exclusion tests, fictional-fixture review, and an independent human-readable privacy review.

## Prospective implementation scope — not authorized

The later implementation proposal must provide an exact path allowlist. Expected areas are:

- one canonical root AI entry and thin provider/editor adapters;
- bootstrap and command documentation;
- canonical lifecycle schema and deterministic orchestration tooling;
- writer reservation, transitions, checkpoints, handoffs, retry, and replay behavior;
- narrative save versus lifecycle-checkpoint separation;
- destination-bound egress authorization before credential or content access;
- provider-neutral routing rules and optional model mappings;
- privacy-generic documentation and fixtures;
- installer, updater, checksum, manifest, and migration handling;
- protocol, privacy, installer, updater, rollback, and idempotency tests;
- release notes and bounded hypercare criteria.

No file in those areas may change until a later exact implementation scope is approved and one writer is reserved.

## Healthy clean-install rehearsal — not authorized

Observed candidate when planned: clean `Healthy/main` at `87cd63cd9b87efb6d3b234dd2362c78242492a24`. Reverify before execution.

The future rehearsal must:

1. Use a disposable isolated copy of the exact Healthy source.
2. Pin the exact template candidate and run non-interactively.
3. Make no global editor-home changes.
4. Use no real secrets, browser profile, Firebase credentials, network, build, deployment, or production authority.
5. Baseline every existing tracked file.
6. Preserve `.claude/launch.json`, `app/healthy.html`, Firebase configuration, and all other pre-existing tracked files byte-for-byte during installation.
7. Create only expected Exocortex/editor additions, ignored placeholder configuration, and one controlled ignore block.
8. Re-run the installer and prove idempotency without duplicate ignore entries.
9. Run local Healthy regressions only if that later rehearsal gate explicitly permits them.
10. Perform a fresh AI cold start and verify that it identifies the disposable boundary and takes no automatic external or production action.

A passing rehearsal does not authorize installing into the live Healthy repository.

## Existing-repository upgrade rehearsal — not authorized

Observed candidate when planned: dirty `enkratflow-ui` branch `chore/lessons-layout-and-build-errors` at `a875dca137bd6959f1308f223f3003fdaf733f75`. Reverify before execution and never exercise its live checkout.

The future rehearsal must:

1. Create a disposable isolated source copy and a disposable backup location.
2. Baseline protected memory, control files, events, custom commands/scripts, sidecars, and registry filenames without reading secret values.
3. Exercise its missing-version legacy path against a pinned template candidate.
4. Preserve manifest-diverged and untracked extensions.
5. Add synthetic `local/`, `archive/`, `hub/`, `planning/`, subconscious, and hub-marker fixtures only in the disposable copy.
6. Prove dry-run reporting, first apply, second-run idempotency, protected-path equality, and restore into a second disposable copy.
7. Detect or close the current safe-update protected-path coverage gap before any live rollout.
8. Perform no credential access, external synchronization, service action, or production access.

A passing rehearsal does not authorize upgrading the live repository.

## Future verification matrix

| Area | Deterministic evidence | Human or independent evidence |
|---|---|---|
| Entry and routing | Zero-context parse, exact-state resolution, no mandatory provider/model dependency | Independent AI or provider can orient and refuse out-of-scope mutation |
| Lifecycle and checkpoints | Accepted transition yields one checkpoint; replay and invalid/rejected paths yield none | Owner confirms lifecycle wording and approval separation |
| Egress | No credential/content/network/copy access without exact destination authorization | Owner reviews the exact authorization and destination |
| Privacy | Prohibited-token/path scan, data-plane exclusions, fictional fixtures, exact diff review | Independent privacy review |
| Template regression | JSON/shell/Python validation, checksums, full installer/updater suite | Maintainer review of migration and release notes |
| Healthy install | Disposable install, file hashes, idempotent re-run, local regression if approved | Cold-start command-flow UAT |
| Existing upgrade | Manifest preservation, protected fixtures, backup, second run, restore | Confirm project-local records survive and no external sync occurs |
| Release/hypercare | Exact artifact, rollback, bounded monitoring evidence | Separate owner decisions for promotion and each rollout |

## Acceptance criteria

1. A zero-context AI resolves exact authority, active work, state, writer, evidence, and closed gates in under five minutes.
2. Routing is provider-neutral, capability- and cost-based, deterministic-first, and one-writer.
3. Lifecycle transition, rejection, retry, replay, narrative save, checkpoint, and handoff behavior is deterministic and unambiguous.
4. External delivery fails closed before credential, event-content, destination, copy, or network access without exact authorization.
5. The public candidate contains no private Mulligan or owner-specific data and installs no project-local history.
6. Disposable Healthy installation preserves the source repository and external state.
7. Disposable existing-repository upgrade preserves sovereign data and supports idempotent re-run and rollback.
8. Independent cross-provider Human UAT passes entry, rejection, retry, handoff, install, and upgrade cases.
9. Every later implementation, rehearsal, release, promotion, and live rollout remains separately approved.

## Dependencies and open decisions

- Decide how the fallback commit is reconciled with `main` before promotion.
- Approve an exact future implementation path allowlist before reserving a writer.
- Decide the canonical schema version and migration path for repositories that already contain Mulligan-derived work items.
- Decide which provider adapters ship and how example model mappings are versioned without becoming normative.
- Close or explicitly fail the safe-update protected-path coverage gap before real upgrades.
- Define exact hypercare duration, evidence, rollback trigger, and exit criteria before promotion.

## Risks

- The fallback base could be mistaken for released `main` truth.
- Private Mulligan evidence could leak through copied fixtures or documentation.
- Provider pins could undermine universal entry.
- automatic save/checkpoint behavior could duplicate state or imply external authority.
- Installer/updater changes could overwrite sovereign project data or editor configuration.
- Planning approval could be mistaken for implementation or promotion authority.

The canonical JSON record contains the detailed mitigations and gate statuses.

## Explicit exclusions for this gate

- No protocol, installer, updater, command, hook, adapter, documentation, or test implementation.
- No writer reservation.
- No fallback/main reconciliation.
- No Healthy or `enkratflow-ui` changes, copies, installs, upgrades, builds, tests, or browser/service access.
- No push, pull request, merge, release, deployment, service action, credential access, external synchronization, or template promotion.

## Next gate

The project owner reviews this captured plan. A separately approved gate may then record refinement/readiness and, only with an exact implementation allowlist, authorize one local writer. No downstream action is inferred from plan acceptance.
