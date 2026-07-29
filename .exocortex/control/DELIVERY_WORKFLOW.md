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

## Delivery loop

1. Capture the observed problem and intended outcome.
2. Refine requirements, scope, risks, dependencies, and acceptance criteria.
3. Define the exact allowed paths, base, rollback, and verification matrix.
4. Obtain one plain-language `local_delivery` authorization for the bounded
   outcome. Internally materialize the exact work item, registry entries,
   reservation, technical capabilities, and transaction records without
   asking the human to approve those mechanics one by one.
5. Implement the smallest useful slice.
6. Run developer verification on the exact diff.
7. Run independent review with a registered read-only reviewer distinct from the writer; bind the reviewer identity and evidence SHA-256 to the transition, then reference that transition when entering QA/SIT.
8. Run applicable unit, integration, regression, SIT, security/privacy, migration, and recovery tests.
9. Prepare Human UAT with concrete user-observable cases; the model cannot
   accept its own UAT. Ask only for an observable accept/reject decision, then
   record it inside the active local-delivery envelope without another owner
   prompt.
10. Obtain the next business-level envelope only when needed:
    `publication`, `integration_rollout`, or exact-target
    `production_egress`.
11. Observe bounded hypercare and rollback triggers.
12. Mark Done only after required evidence and approvals exist.
13. Produce a retrospective that may propose, but never authorize, the next captured item.

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

Human UAT validates user-visible or operational outcomes that deterministic tests cannot establish alone. It is intentionally bounded: automation proves repeatable calculations and low-level cases; the human checks meaning, usability, and acceptance. A model may prepare evidence but cannot record acceptance without the human's explicit decision.

## Hypercare

Hypercare duration, operation count, evidence cadence, rollback triggers, and exit criteria are defined before release. A rollback trigger contains the candidate and requires a new corrective item; it never permits silent fix-forward.
