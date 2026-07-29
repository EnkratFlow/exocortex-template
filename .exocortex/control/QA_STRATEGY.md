# Project QA strategy

This project-local document defines which evidence is required for each bounded
work item. Replace project placeholders only through an approved local writer;
template installation does not infer application tests or release authority.

## Risk-based matrix

| Change class | Minimum deterministic evidence | Independent evidence | Human evidence |
|---|---|---|---|
| Documentation/process | syntax, link/path, scope, privacy, diff checks | when authority or public guidance changes | meaning and usability when material |
| Feature or bug | focused unit/component tests plus affected integration and regression paths | risk-based correctness review | observable acceptance cases |
| Security/privacy/data | negative authorization, boundary, race, recovery, and tamper tests | required independent review | owner acceptance of residual risk |
| Migration/install/update | clean fixture, protected-state hashes, idempotency, rollback, fault injection | required migration/privacy review | disposable-target rehearsal acceptance |
| Model routing/freshness | source-role and digest binding, partial-observation scope, quarantine, stale/expiry denial, exact-surface availability, measured cost-per-success | required policy/privacy review | Human review of any catalog admission |
| Release/deployment | exact candidate and artifact hashes, build/package evidence, rollback readiness | release-specific review | applicable publication, integration/rollout, or exact-target production/egress decision and hypercare exit |

## Evidence rules

- Bind every result to the exact base, candidate, tool command/version, test
  case, return code, artifact digest, and unresolved limitation.
- Use deterministic tools for repeatable calculations and protocol behavior.
- Test both pure logic and the real container/entry surface that consumes it.
- A stale, skipped, unrelated-SHA, or assertion-only result is not passing
  evidence.
- Rejection, retry, crash recovery, race, idempotent replay, privacy, and
  rollback cases are mandatory when the affected risk exists.
- Application suites may be skipped only with a recorded reason showing the
  slice cannot affect them; the skip is visible to Human UAT and release review.

## Delivery gates

1. Developer verification covers the exact writer diff.
2. Independent review occurs before QA/SIT for every required risk class; it is
   not bypassed by a normal lifecycle transition.
3. QA/SIT covers affected integrations, regressions, security/privacy, data,
   migration, and recovery behavior.
4. Human UAT checks meaning, usability, and operational acceptance that the
   model cannot self-certify. Ask for a simple accept/reject result; record it
   inside the active local-delivery envelope without another capability prompt.
5. Publication, integration/rollout, and exact-target production/egress remain
   later business decisions. Internal capabilities are not separate human
   approvals.

## Exocortex code-plane verification

For a template/protocol slice, run in a clean isolated checkout with no real
credentials, provider, network, target repository, or deployment access:

```bash
bash tests/run_tests.sh
bash .exocortex/scripts/tests/test_orchestration_protocol.sh
bash .exocortex/scripts/tests/test_event_tooling.sh
bash tests/phase-b/run.sh
```

The Phase B harness must use a newly created temporary evidence directory,
fake `HOME`, deny-network shims, fictional fixtures, and fake in-process
transport. A real clean install, existing-repository upgrade, release, or
promotion remains a later Human UAT/downstream gate.

## Definition of done

`done` requires every applicable acceptance criterion, deterministic and
independent QA result, Human UAT decision, release/deployment record, and
hypercare exit. Code completion, a local commit, or a passing subset is not
Done.
