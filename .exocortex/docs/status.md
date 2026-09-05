# Exocortex release status

Last updated: 2026-09-05

This is the living, human-readable maintainer view of the public template. It
is release-scoped, not a downstream project's status page, approval record,
release attestation, or replacement for exact test and Git evidence.

## Published baseline

- The previous reviewed published baseline is `v3.2.9` at peeled commit
  `8559add4edb35182cd655a62c59fe451425667a9`.
- The packaged candidate version is `3.3.0`. This tracked file does not prove a
  branch push, merge, annotated tag, immutable GitHub release, attested asset,
  installation, deployment, or template promotion.

## Candidate state

| Area | State | Current objective |
| --- | --- | --- |
| Local delivery | Implemented; exact-candidate verification required | Bind one understandable local decision to the exact repository, base, worktree, paths, writer, reviewer, verification, expiry, rollback, and exclusions. |
| Lifecycle evidence | Implemented; exact-candidate verification required | Link developer verification, independent review, QA/SIT, and Human UAT; create one local completion event and handoff before releasing the writer. |
| Recovery and replay | Implemented; exact-candidate verification required | Reject altered or missing transition and completion records while preserving exact interrupted recovery and idempotent replay. |
| Public-template privacy | Implemented; focused and complete verification required | Apply the bound checker and declared rules to the complete tagged tree, exact reviewed release slice, merge message, and annotated tag without displaying matched values; this scoped evidence is not proof that older public history is clean or that no undiscovered disclosure pattern exists. |
| Credential-blind handling | Implemented; focused and complete verification required | Reject credential-shaped paths before content access while accounting for ordinary untracked source and safe ignored dirt. |
| Model routing | Retained | Use provider-neutral, capability-, risk-, and cost-aware parent judgment; the formal catalog remains optional evidence and activates nothing by default. |
| Install and update | Compatibility verification required | Preserve project memory, events, decisions, customizations, protected local state, credentials, and rollback boundaries during future named-target rehearsals. |
| Release authenticity | Selected; publication verification required | Bind canonical GitHub `OWNER/REPO`, immutable REST repository ID, an external trusted executor closure, its checker, and exact Python/Git/GitHub CLI executable digests before using immutable-release verification plus an attested `SHA256SUMS` asset. |

## Operating decisions

- One accountable parent owns integration and final evidence. Add a distinct
  read-only reviewer for security-sensitive work, not as a delegate quota.
- Human-facing local approval covers the bounded outcome. Internal work items,
  reservations, one-time capabilities, checkpoints, evidence, handoffs, and
  writer release remain exact protocol mechanics rather than repeated prompts.
- Publication, merge/release, project rollout, and production egress are
  separate business gates. No earlier gate implies a later one.
- Private project events, memories, identities, host details, network details,
  and runtime records are data plane and never public-template payload.

## Publication gates and residual limitations

Before version 3.3.0 may be used as a public installation or update source:

1. Provision a separately installed, independently reviewed publication
   runtime outside the candidate root. Bind its executor-closure, checker,
   Python, Git, and GitHub CLI SHA-256 digests; 3.3.0 cannot bootstrap trust
   from its own new publisher or checker.
2. Freeze one exact candidate and run the focused checks plus the complete
   Exocortex safety suite once.
3. Obtain independent review and Human UAT for that exact sealed candidate.
4. Under a separate publication decision, bind GitHub's canonical
   `OWNER/REPO` and immutable REST repository ID, then stage only reviewed paths, commit,
   push the named branch, and open a draft pull request.
5. Require exact-commit CI before any separately authorized merge.
6. Under a later integration/release decision, create the exact annotated tag,
   publish the immutable release and `SHA256SUMS` asset together, then verify
   both with the GitHub CLI before any installation or update.

The following limitations remain visible without weakening those gates:

- decide whether to enable GitHub secret scanning, push protection, private
  vulnerability reporting, restricted Actions, and stronger branch rules;
- decide how to handle protected project data already present in old public
  history; no history rewrite is implied or authorized;
- provide genuine operating-system or broker-enforced network/filesystem
  containment when executing an untrusted candidate.

Checksums establish byte consistency only; they do not independently prove
repository-owner authenticity.

The guarded publisher also rejects an envelope over 128 KiB, a candidate
source file over 64 MiB, or combined derived public metadata over 64 KiB.
These bounds and a sanitized privacy-check result are fail-closed runtime
evidence, not host attestation, cryptographic human identity, or proof that no
unknown disclosure pattern exists.

## Candidate evidence contract

- `origin/main` and the exact designated base must be reconciled immediately
  before candidate creation.
- The previous published annotated tag and its direct commit target must match
  `.exocortex/release-baseline.json`.
- The tagged release must preserve a genuine merge boundary. Its first parent
  starts the reviewed release slice while the previous published tag remains
  the version and ancestry anchor; only the merge commit's hosting-provider
  identity headers are outside template-payload inspection.
- Provider adapters, documentation, public privacy, checksums, file modes,
  shell syntax, authority, orchestration, recovery, install, update, and
  rollback checks must agree on the same candidate.
- Every changed release candidate must pass the complete required checks on
  its exact state using CI or an explicitly provisioned runner. Local focused
  checks are insufficient unless current capacity and authority support the
  complete run.
- Test output, independent-review evidence, the seal, and Human UAT belong to
  protected local records or exact-commit CI; this public status page does not
  manufacture those claims.

## Local preparation boundary

- The 3.3.0 metadata and integrity inventories are part of the candidate;
  changing any candidate byte invalidates earlier evidence and requires a new
  exact-candidate verification and seal.
- Complete safety evidence, independent review, and Human UAT must bind the
  same candidate before a separate publication decision can be considered.
- Local preparation stops before staging or any outward action. Publication is
  never implied by a prepared or locally accepted candidate.

## Start here

- Read [`AI_START_HERE.md`](../../AI_START_HERE.md) for authority and delivery
  rules.
- Read [`MODEL_ROUTING.md`](../control/MODEL_ROUTING.md) for routing policy.
- Read [`AI_INSTALLATION.md`](AI_INSTALLATION.md) before installation or
  update rehearsal.
- Treat this page as stale whenever its date or evidence no longer matches live
  Git and release state.
