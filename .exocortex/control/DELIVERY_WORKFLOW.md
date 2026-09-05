# Minute-scale delivery workflow

## Lifecycle

`captured → triaged → refined → ready → reserved → developing → developer_verified → independent_review → qa_sit → uat_ready → human_uat → release_ready → awaiting_release → deployment_approved → deployed → hypercare → done`

`blocked` is an explicit condition attached to the current state; it is not a shortcut around a gate.

## Work-item classes

Classify every bounded item as one of:

- feature;
- bug;
- maintenance;
- security/privacy;
- migration;
- documentation/process;
- retrospective improvement.

## Plain-English work contract

Before a substantial phase, state one short contract containing the intended
outcome, repository, scope and exclusions, estimate, planned checks with their
expected duration, and model routing. Use one accountable parent and no
delegate by default. Internal IDs may follow as evidence, but they are never
the explanation the owner must understand.

Pause and report before continuing if:

- a newly discovered check is expected to take more than five minutes;
- the elapsed-time estimate increases materially;
- the target, base, path set, outcome, risk, or outward effect changes; or
- the same unchanged candidate already has accepted equivalent evidence.

The report explains what changed, why it matters, and the smallest useful next
step. It does not manufacture a new approval when the work remains inside the
accepted business envelope.

## Delivery loop

1. Capture the observed problem and intended outcome.
2. Refine requirements, scope, risks, dependencies, and acceptance criteria.
3. Define the exact allowed paths, base, rollback, and verification matrix.
4. Obtain one plain-language `local_delivery` authorization for the bounded
   outcome. Internally materialize the exact work item, registry entries,
   reservation, technical capabilities, and transaction records without
   asking the human to approve those mechanics one by one.
   Start with `bootstrap-local-delivery`, which binds the approved envelope to
   one clean isolated worktree, exact base, branch, and allowed-path list, then
   atomically creates/reserves/activates the item in `developing`. This is not
   a normal lifecycle transition or checkpoint.
   Its `--envelope-source` must be a project-relative regular file under
   `.exocortex/local/protocol/inbox/`; credential-shaped names (`.env`,
   `.env.*`, private-key formats, `credentials`, or `secrets`) fail before
   opening.
5. Implement the smallest useful slice.
6. Run `seal-local-edit` and developer verification on the exact diff. Sealing
   records the actual changed-path set and rejects an extra path.
   For developer verification, independent review, QA/SIT, UAT-ready, and
   Human UAT, omit caller `--capability`: the orchestrator derives and consumes
   the deterministic one-time capability from the accepted envelope and exact
   transition intent.
7. Record non-empty evidence for developer verification, then run independent
   review with a registered read-only reviewer distinct from the writer; bind
   the reviewer identity and non-empty evidence SHA-256 to the transition.
8. Run applicable unit, integration, regression, SIT, security/privacy,
   migration, and recovery tests; QA/SIT and UAT-ready each require non-empty
   evidence.
9. Prepare Human UAT with concrete user-observable cases; the model cannot
   accept its own UAT. Ask only for an observable accept/reject decision, then
   record non-empty Human-UAT evidence and an attestor matching the envelope
   approver inside the active local-delivery envelope without another owner
   prompt. Acceptance criteria remain pending through `uat_ready`; this
   Human-UAT transition refuses failed or blocked criteria and atomically
   records the remaining criteria as passed with its evidence. This is
   cooperative local evidence, not cryptographic identity proof.
10. Obtain the next business-level envelope only when needed:
    `publication`, `integration_rollout`, or exact-target
    `production_egress`.
11. Observe bounded hypercare and rollback triggers.
12. Mark Done only after required evidence and approvals exist.
13. Only after `human_uat`, run `complete-local-delivery`. For an approved
    local-delivery task that changed files it writes exactly one
    concise project-local completion event and handoff, records `local_state=complete`,
    and releases the writer while lifecycle remains `human_uat`. Do not
    regenerate Session Context, create a preview, checkpoint, or sync as a
    side effect. `release_ready` is rejected until that local completion exists,
    and publication remains a separate gate. This
    does not grant commit, push, release, deployment, credential access, or
    network egress.
    Its `--body-file` must be a project-relative regular file under
    `.exocortex/local/protocol/inbox/`; credential-shaped names are rejected
    before opening.
14. Produce a retrospective that may propose, but never authorize, the next
    captured item or a permanent memory/lesson change.

## Human-facing approval envelopes

The protocol presents four business decisions to the owner:

- `local_delivery`: bounded local work, tests, review, UAT recording, local
  handoff, and writer release; never Git publication or outward action.
- `publication`: exact-path stage, local commit, named-branch push, and draft
  pull request for one reviewed candidate; never merge.
- `integration_rollout`: one exact merge, release, promotion, or named
  repository rollout; never deployment or egress by implication.
- `production_egress`: one exact deployment, service action, or external
  payload to one named target/destination and method.

Reservations, one-time capabilities, eligible checkpoints, evidence records,
handoffs, and writer release remain internal enforcement artifacts. They do
not each require a new human approval while they stay within the active
envelope. A mismatch or material scope/risk change fails closed and requires
one replacement business decision.

## Publication trust contract

A publication envelope binds both the exact GitHub `OWNER/REPO` name and the
repository's immutable REST `.id`, rendered as a canonical decimal string.
The guarded publisher compares both values with GitHub's current `full_name`
and `.id` before every external-state observation or effect using a bounded,
unauthenticated public REST request that does not follow redirects and accepts
only HTTP 200. A redirect, transfer, rename, identity mismatch, or indeterminate
response fails closed; continuation requires a newly reviewed envelope for the
new identity.

The same envelope binds one `trusted_runtime` object containing exact SHA-256
digests for the executor closure, public-release checker, Python executable,
Git executable, and GitHub CLI executable. The executor implementation root
must be outside the candidate root. The runtime verifies all five digests
before reading candidate-owned executable code and again at every outward
effect boundary. It must not import or execute Python, hooks, filters,
credential helpers, configuration, or checkers from the candidate. The trusted
checker receives the exact pinned Git path and digest and revalidates them for
every Git-backed check.

Version 3.3.0 is the bootstrap release for this contract, so its candidate
cannot establish trust in its own new publisher or checker. Publication must
use a separately installed and reviewed external runtime whose five digests
were approved independently of the candidate. After an immutable release
establishes that trust root, a later candidate may use the exact verified
runtime from a prior immutable release; candidate-owned replacements remain
untrusted until a later release completes.

The external runtime's read-only `runtime-facts` command reports only the five
approved digests; it never reports executable or home-directory paths. An
expired or abandoned publication is not allowed to hold its source forever.
`retire-publication` therefore requires a new, exact, one-time capability for
the publication record revision and releases only the project-local writer and
source reservation. If a branch may exist, it first confirms the immutable
repository identity and exact remote state. It never deletes or changes a
branch or pull request, and it records any preserved named branch. A verified
draft pull request or completed publication cannot use this retirement path.

Publication inputs are deliberately bounded: the serialized envelope is at
most 128 KiB, each candidate source file is at most 64 MiB, and the combined
derived public commit/branch/pull-request metadata is at most 64 KiB of UTF-8.
The schema additionally limits the commit subject to 200 characters, commit
body to 4,000, pull-request title to 256, pull-request body to 20,000, and
individual verification/exclusion entries to 1,000. Carriage returns, NULs,
and line breaks in one-line fields fail closed.

Privacy evidence is scoped evidence, not a universal privacy guarantee. A
passing result proves only that the bound trusted runtime applied its exact
checker bytes and declared rules to the exact inspected source and public
metadata bytes at that time. Reports disclose only rule identifiers, counts,
coarse classes, and digests—not matched values or raw paths. They do not prove
that no undiscovered disclosure pattern exists, provide cryptographic human
identity, attest the host, or turn cooperative local enforcement into an OS
sandbox.

## Transition rules

- Every transition has a stable request/idempotency key.
- Current revision, state, writer, executor registration, approval, target digest, expiry, and revocation are checked immediately before mutation.
- Short-lived technical authority may be renewed under the same unexpired
  business envelope only when the exact target, base, digest, paths/plan,
  operation class, risk, intended outcome, and verification remain unchanged.
- A checkpoint-eligible accepted transition and its checkpoint are one atomic durable operation.
- Retry/replay returns the existing accepted result.
- Invalid or unauthorized transitions create no checkpoint or partial state.
- Business-gate classes never cascade. External synchronization remains
  destination-specific and cannot share a local-record envelope.

## Definition of evidence

Evidence names the exact base/candidate, test case, tool version, result, artifact digest, reviewer, and unresolved limitation. A passing test from another SHA or an assertion without artifacts is not gate evidence.

## Human UAT

Human UAT validates user-visible or operational outcomes that deterministic tests cannot establish alone. It is intentionally bounded: automation proves repeatable calculations and low-level cases; the human checks meaning, usability, and acceptance. A model may prepare evidence but cannot record acceptance without the human's explicit decision. The accepted transition records remaining criteria as passed; task completion fails unless every criterion still carries that exact Human-UAT transition marker and evidence.

Completion also verifies that the seal and all five pre-UAT transitions form
one exact chain of consumed one-time capabilities and finalized guarded
transactions; a manually fabricated transition or edited history is not
acceptance.

Ordinary chat and `/save` are separate from task closeout. `/save` stays
manual; read-only work, elapsed time, tests, and failed attempts never create a
completion event automatically.

`create_event.sh` remains the manual `/save` event helper. It does not replace
`complete-local-delivery`, record Human UAT, or release a writer.

## Hypercare

Hypercare duration, operation count, evidence cadence, rollback triggers, and exit criteria are defined before release. A rollback trigger contains the candidate and requires a new corrective item; it never permits silent fix-forward.
