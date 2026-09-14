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
4. Obtain the exact implementation approval and register one guarded writer.
5. Implement the smallest useful slice.
6. Run developer verification on the exact diff.
7. Run independent review with a registered read-only reviewer distinct from the writer; bind the reviewer identity and evidence SHA-256 to the transition, then reference that transition when entering QA/SIT.
8. Run applicable unit, integration, regression, SIT, security/privacy, migration, and recovery tests.
9. Prepare Human UAT with concrete user-observable cases; the model cannot accept its own UAT.
10. Obtain separate release, deployment, and outward-action approvals.
11. Observe bounded hypercare and rollback triggers.
12. Mark Done only after required evidence and approvals exist.
13. Produce a retrospective that may propose, but never authorize, the next captured item.

## Transition rules

- Every transition has a stable request/idempotency key.
- Current revision, state, writer, executor registration, approval, target digest, expiry, and revocation are checked immediately before mutation.
- A checkpoint-eligible accepted transition and its checkpoint are one atomic durable operation.
- Retry/replay returns the existing accepted result.
- Invalid or unauthorized transitions create no checkpoint or partial state.
- Release, deployment, external synchronization, promotion, and each live rollout are separate operations and capabilities.

## Definition of evidence

Evidence names the exact base/candidate, test case, tool version, result, artifact digest, reviewer, and unresolved limitation. A passing test from another SHA or an assertion without artifacts is not gate evidence.

## Human UAT

Human UAT validates user-visible or operational outcomes that deterministic tests cannot establish alone. It is intentionally bounded: automation proves repeatable calculations and low-level cases; the human checks meaning, usability, and acceptance. A model may prepare evidence but cannot record acceptance without the human's explicit decision.

## Hypercare

Hypercare duration, operation count, evidence cadence, rollback triggers, and exit criteria are defined before release. A rollback trigger contains the candidate and requires a new corrective item; it never permits silent fix-forward.
