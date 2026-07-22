# EXO-PHASE-B-001 — Multi-AI delivery protocol generalization

## Status

- Lifecycle: `refined`
- Revision: 2
- Attempt: 0
- Exact planning base: `0eb3c667a505b90c9221ed768d47039a1638df5e`
- Branch: `codex/exo-phase-b-001-planning`
- G1 refinement approval: consumed
- Writer reservation: none
- Prospective G2 implementation authority: none
- Rehearsal, release, promotion, or rollout authority: none
- Remote publication of this planning branch or its private planning history: prohibited
- Distribution: project-local planning data; never propagated to installed repositories

G1 defines the future implementation and verification boundary. It does not implement that boundary, reserve a writer, reconcile a release branch, touch an application repository, call a provider, synchronize externally, or authorize any downstream gate.

## Outcome sought

Generalize the accepted multi-AI delivery behavior into a privacy-safe, provider-neutral Exocortex template that supports recursive improvement while preserving human sovereignty.

Any supported AI should be able to enter cold, recover exact Git and project-local authority, understand current work and evidence, select or delegate work by capability and cost, enforce one writer, and stop before unauthorized mutation or outward action. A completed cycle may generate measured retrospective evidence and propose a bounded next work item. It may not approve or start that next item itself.

## Reference binding

| Reference | Exact SHA | Use |
|---|---|---|
| Template Phase B base | `0eb3c667a505b90c9221ed768d47039a1638df5e` | Exact base for this isolated planning lane; contains the version-fallback correction |
| Observed template `main` | `c6ccd8358c6896d8456cb4aa19b09744ea44b1e8` | Containment comparison only; it does not contain the approved fallback commit |
| Accepted Mulligan record | `50cd1c3db6d69c6d16a68e8935576016b21276b2` | Recorded private reference identifier and prior privacy-safe audit summary; object absent from this repository |
| Mulligan implementation candidate | `b63463f784d3e51f47b787e29222bba91dce60e0` | Recorded private behavioral reference identifier and prior summary; object absent from this repository |

The private objects are intentionally absent from the template Git object database and cannot be independently verified here. A later conformance comparison requires separately authorized read-only source inspection or a fictionalized privacy-safe evidence packet. Importing the private objects or history is never required or authorized.

The Mulligan references are evidence pointers, not template payload. No private work item, event, handoff, identity, path, branch, SHA, reservation, origin metadata, endpoint, approval history, or application fixture may enter the public candidate.

Installer exclusion alone is insufficient because Git history can leak planning data. This planning branch and any descendant carrying these records must never be pushed, merged, fast-forwarded, or used directly for a public pull request. A later promotion gate must replay only the accepted privacy-scrubbed code-plane diff onto an approved clean public base, create new commits with no private-planning ancestry, and scan the promoted tree plus every newly reachable commit tree/message before publication.

Mulligan release disposition, application/protocol integration, deployment, external synchronization, and template promotion remain outside this work item.

## Public protocol contract

### Universal entry

`AI_START_HERE.md` is the provider-neutral root contract. Thin provider or editor adapters, including native Codex `AGENTS.md`, point to that contract rather than restating independent authority rules. Every installed command and skill entrypoint must load that canonical gate before giving a mutation- or egress-capable instruction.

A zero-context AI must deterministically identify:

1. Repository and exact live Git state.
2. Designated base and integration truth.
3. Active work item, revision, state, and attempt.
4. Exact human authority and its exclusions.
5. Writer reservation and allowed paths.
6. Required tests, evidence, handoff, and blocked gates.
7. Whether it is read-only support, the one accountable writer, or an independent reviewer.

It stops before mutation or outward action whenever exact authority is missing, stale, mismatched, revoked, consumed, or ambiguous.

### Dynamic capability-and-cost orchestration

The protocol does not always start at the largest model, and it does not blindly start at the cheapest model.

1. Select the least-expensive available model that can reliably own the whole task's planning, authority interpretation, risk decisions, integration, and final accountability.
2. Use deterministic tools first for Git truth, validation, searches, checksums, tests, and repeatable transformations.
3. Decompose approved work into bounded deliverables with acceptance criteria and authority boundaries.
4. Delegate each bounded task to the least-cost capable role. Support lanes remain read-only unless the exact approval says otherwise.
5. Escalate ambiguity, repeated failure, scope drift, sensitive data, destructive change, external action, or material design decisions to the accountable parent or a stronger role.
6. Return every delegated result to the parent for integration, deterministic verification, and gate decisions.
7. Use one writer, the minimum useful parallel lanes, compact evidence packets, and stop duplicate reviews when evidence converges.

Provider/model catalogues are optional versioned adapters. No named provider, product, model, or permanent highest-model-first rule is normative.

### Minute-scale Kanban lifecycle

`Captured → Triaged → Refined → Ready → Reserved → Developing → Developer Verified → Independent Review → QA/SIT → UAT Ready → Human UAT → Release Ready → Awaiting Release → Deployment Approved → Deployed → Hypercare → Done`

Blocked is explicit. Code, tests, a commit, a push, a merge, or a deployment does not independently mean Done.

### Authority capabilities

R-06 remains open until a machine guard enforces one current, exact, expiring, revocable, one-time human approval bound to:

- registered `surface_id`, guarded executor identity, adapter version, and guard executable digest;
- work item and revision;
- operation;
- target path, SHA, destination, or content digest as applicable;
- approver and acceptance time;
- expiry and revocation state;
- writer reservation where mutation is involved.

Executor registration is a separate local human gate. It records exact surface/executor identity, adapter version, guard digest, allowed role classes, expiry, and revocation in a project-local registry; it grants no work-item action by itself. Every writer/egress capability binds to that registration. Missing, unknown, unregistered, wrong-executor, wrong-adapter, digest-mismatched, expired, revoked, or cross-surface identity fails before reservation or side effect.

The guard rechecks executor registry, current target, and authority digests immediately before the write, child process, credential lookup, content read, copy, or network attempt. Approval for planning never authorizes implementation; implementation never authorizes rehearsal, release, external sync, promotion, or rollout.

This is enforceable only inside the guarded execution boundary. An AI surface with direct unmanaged filesystem or network tools that cannot be constrained to the guarded executor is classified read-only/advisory and cannot receive an approved writer or egress role. Instructions alone are not treated as machine enforcement.

### Saves, checkpoints, and handoffs

- A narrative `/save` is a user-requested project-local event. It is not a lifecycle transition or external-sync authorization.
- A lifecycle checkpoint is created only as part of an accepted durable transition explicitly marked checkpoint-eligible.
- The transition and checkpoint are atomic and idempotent; retry/replay converges on the same one checkpoint.
- Rejected, invalid, unauthorized, blocked, stale, conflicting, read-only, support, test, ordinary-chat, narrative-save, and explicitly non-checkpointing transitions create no lifecycle checkpoint.
- Automatic hooks may remind or propose a narrative save; they may not invent a transition or outward authority.
- Handoffs are local by default and carry exact base, candidate, state, evidence, writer status, closed gates, and first verification step.

### Fail-closed egress

Every outward-capable path—direct sync, saves and reviews, interrupt capture, hub copy, key validation, memory-provider calls, hooks, subprocesses, and retries—must pass one auditable egress guard.

Egress uses two stages:

1. A separately authorized local-only operation creates or selects a finalized immutable payload and records its object ID, byte size, class, and cryptographic digest without credential lookup or transport. A new event gets this descriptor as part of local event creation; dynamic provider content is first staged as a local immutable preview. The human approves the exact destination, method, payload class, size, digest, expiry, and outward effect. No descriptor means no egress capability.
2. The guard first reads only policy, approval metadata, and the stored descriptor. Any missing or mismatched authority stops before payload open/read, credential lookup, destination initialization, process spawn, copy, or network. After metadata passes, the guard opens the payload once and stream-verifies size and digest before credential lookup. A mismatch denies with no transport. Only then may it resolve the exact destination credential, recheck expiry/revocation/destination/method/digest, and invoke transport.

Changed or dynamic content always needs a new descriptor and approval. Local event creation remains independently complete.

### Recursive improvement

After accepted hypercare, a retrospective may measure:

- routing accuracy, escalations, latency, and cost;
- duplicated or failed work;
- authorization denials and retries;
- missing tests, safeguards, or documentation;
- install/upgrade friction and protected-state evidence;
- a proposed small protocol improvement with acceptance criteria.

The output is a proposed work item in `captured`, with no writer or mutation capability. A human must accept or narrow the next gate.

## Exact prospective G2 path boundary — not authorized

G2 may be requested later for one fresh local writer. The following is the complete prospective path boundary; no unlisted path may change.

### Create

```text
AGENTS.md
AI_START_HERE.md
.exocortex/control/MODEL_ROUTING.md
.exocortex/control/DELIVERY_WORKFLOW.md
.exocortex/schemas/orchestration.schema.json
.exocortex/schemas/authorization.schema.json
.exocortex/schemas/executor-registry.schema.json
.exocortex/schemas/external-sync-policy.schema.json
.exocortex/examples/EXECUTOR_REGISTRY.read-only.json
.exocortex/examples/EXTERNAL_SYNC_POLICY.deny.json
.exocortex/scripts/orchestrate_work_item.py
.exocortex/scripts/authority_guard.py
.exocortex/scripts/egress_guard.py
.exocortex/scripts/resolve_designated_base.sh
.exocortex/scripts/git_event_crosscheck.sh
.exocortex/scripts/tests/test_orchestration_protocol.sh
.exocortex/scripts/tests/test_event_tooling.sh
.exocortex/commands/handoff.json
.cursor/commands/handoff.md
tests/phase-b/run.sh
tests/phase-b/test_phase_b.py
tests/phase-b/verify_evidence.py
tests/phase-b/test-plan.json
tests/phase-b/fault_shims.sh
tests/phase-b/hash_tree.py
tests/phase-b/assert_tree_delta.py
tests/phase-b/make_upgrade_fixture.py
```

### Modify

```text
CLAUDE.md
.github/copilot-instructions.md
.github/skills/ai-architect/SKILL.md
.github/skills/architect/SKILL.md
.github/skills/behavioral/SKILL.md
.github/skills/chief-of-staff/SKILL.md
.github/skills/cx-strategist/SKILL.md
.github/skills/data-engineer/SKILL.md
.github/skills/deep-agent/SKILL.md
.github/skills/devops/SKILL.md
.github/skills/engineer/SKILL.md
.github/skills/onboard/SKILL.md
.github/skills/product-manager/SKILL.md
.github/skills/project-planner/SKILL.md
.github/skills/qa-strategist/SKILL.md
.github/skills/roster/SKILL.md
.github/skills/security/SKILL.md
.github/skills/sre/SKILL.md
.github/skills/technical-writer/SKILL.md
.github/skills/ux-designer/SKILL.md
.rules
.windsurfrules
.cursor/rules/plan-orchestrate.mdc
.cursor/hooks.json
.cursor/hooks/auto-save-phase.sh
.cursor/commands/ai-export.md
.cursor/commands/brief.md
.cursor/commands/save.md
.cursor/commands/daily-end.md
.cursor/commands/weekly-review.md
.cursor/commands/monthly-review.md
.cursor/commands/drill.md
.cursor/commands/groom.md
.cursor/commands/history.md
.cursor/commands/init-exocortex.md
.cursor/commands/interrupt.md
.cursor/commands/longterm.md
.cursor/commands/onboard.md
.cursor/commands/prioritize.md
.cursor/commands/refine-backlog.md
.cursor/commands/work.md
.cursor/commands/ecosystem.md
.cursor/commands/scrum.md
.cursor/commands/shortterm.md
.cursor/commands/subconscious.md
.cursor/commands/system-scan.md
.cursor/skills/ai-architect/SKILL.md
.cursor/skills/architect/SKILL.md
.cursor/skills/behavioral/SKILL.md
.cursor/skills/chief-of-staff/SKILL.md
.cursor/skills/cx-strategist/SKILL.md
.cursor/skills/data-engineer/SKILL.md
.cursor/skills/deep-agent/SKILL.md
.cursor/skills/devops/SKILL.md
.cursor/skills/engineer/SKILL.md
.cursor/skills/onboard/SKILL.md
.cursor/skills/product-manager/SKILL.md
.cursor/skills/project-planner/SKILL.md
.cursor/skills/qa-strategist/SKILL.md
.cursor/skills/roster/SKILL.md
.cursor/skills/security/SKILL.md
.cursor/skills/sre/SKILL.md
.cursor/skills/technical-writer/SKILL.md
.cursor/skills/ux-designer/SKILL.md
.claude/skills/ai-export/SKILL.md
.claude/skills/save/SKILL.md
.claude/skills/daily-end/SKILL.md
.claude/skills/groom/SKILL.md
.claude/skills/interrupt/SKILL.md
.claude/skills/refine-backlog/SKILL.md
.claude/skills/system-scan/SKILL.md
.claude/skills/work/SKILL.md
.exocortex/AI_BOOTSTRAP.md
.exocortex/COMMAND_SYSTEM.md
.exocortex/PERSONA_AND_COMMANDS.md
.exocortex/MEMORY_TIERS.md
.exocortex/control/README.md
.exocortex/control/QA_STRATEGY.md
.exocortex/control/SNIPPETS.md
.exocortex/reference/ESSENTIAL_FILES.md
.exocortex/docs/IDE_INTEGRATION_GUIDE.md
.exocortex/docs/EVENT_SYSTEM_USAGE.md
.exocortex/docs/RAG_INTEGRATION.md
.exocortex/docs/UPGRADE_MANIFEST.md
.exocortex/docs/getting-started.md
.exocortex/docs/memory-system.md
.exocortex/docs/SUBCONSCIOUS_ARCHITECTURE.md
.exocortex/docs/user-guide.md
.exocortex/commands/ai-export.json
.exocortex/commands/brief.json
.exocortex/commands/save.json
.exocortex/commands/daily-end.json
.exocortex/commands/weekly-review.json
.exocortex/commands/monthly-review.json
.exocortex/commands/history.json
.exocortex/commands/init-exocortex.json
.exocortex/commands/groom.json
.exocortex/commands/interrupt.json
.exocortex/commands/onboard.json
.exocortex/commands/pattern-review.json
.exocortex/commands/prioritize.json
.exocortex/commands/refine-backlog.json
.exocortex/commands/work.json
.exocortex/commands/ecosystem.json
.exocortex/commands/check-keys.json
.exocortex/commands/drill.json
.exocortex/commands/longterm.json
.exocortex/commands/shortterm.json
.exocortex/commands/subconscious.json
.exocortex/commands/scrum.json
.exocortex/commands/system-scan.json
.exocortex/scripts/_api_helpers.py
.exocortex/scripts/archive_events.sh
.exocortex/scripts/auto_snapshot.sh
.exocortex/scripts/capture_interrupt.sh
.exocortex/scripts/check_keys.py
.exocortex/scripts/check_keys.sh
.exocortex/scripts/create_event.sh
.exocortex/scripts/drill_memory.py
.exocortex/scripts/generate_context.sh
.exocortex/scripts/get_longterm_memory.py
.exocortex/scripts/get_longterm_memory.sh
.exocortex/scripts/get_rightnow_memory.py
.exocortex/scripts/get_rightnow_memory.sh
.exocortex/scripts/get_shortterm_memory.py
.exocortex/scripts/get_shortterm_memory.sh
.exocortex/scripts/get_subconscious_memory.py
.exocortex/scripts/get_subconscious_nudge.py
.exocortex/scripts/install_openclaw_reminder.sh
.exocortex/scripts/post_to_hub.sh
.exocortex/scripts/run_brief_status.sh
.exocortex/scripts/run_morning_workflow.sh
.exocortex/scripts/run_scrum.sh
.exocortex/scripts/save_work_state.sh
.exocortex/scripts/sync_event_to_vault.sh
.exocortex/scripts/upgrade-exocortex.sh
.exocortex/scripts/launchd/com.exocortex.autosave.plist.template
.exocortex/scripts/launchd/README.md
.exocortex/scripts/launchd/install_autosave.sh
.exocortex/scripts/launchd/uninstall_autosave.sh
.exocortex/skills/exocortex-reminder/SETUP.md
.exocortex/skills/exocortex-reminder/SKILL.md
README.md
CONTRIBUTING.md
install.sh
init-project.sh
scripts/safe-update.sh
scripts/install-cursor-skills.sh
scripts/update-all-repos.sh
.exocortex/.env.example
.exocortex/.gitignore
.gitignore
tests/helpers.sh
tests/run_tests.sh
.github/workflows/checksums.yml
.github/workflows/test.yml
SHA256SUMS
```

### Implementation slice order

1. G2-A: root entry, provider-neutral routing, schemas, documentation, and non-executing validation.
2. G2-B: machine-enforced authority, lifecycle, checkpoint, handoff, and egress guards with deterministic tests.
3. G2-C: installer, updater, manifest, generated-local-stub, native-adapter, and protected-data behavior.
4. G2-D: isolated Phase B harness, privacy scan, fault injection, documentation reconciliation, and integrity manifest.

This order constrains one future implementation lane. It does not authorize separate writers or any target rehearsal.

## Protected project-local data plane

The installer and updater must never copy these paths from the template or manifest-track their contents:

```text
.exocortex/SESSION_CONTEXT.md
.exocortex/SESSION_CONTEXT.local.md
.exocortex/TODO.md
.exocortex/LESSONS.md
.exocortex/PROJECT_MEMORY.md
.exocortex/OPEN_DECISIONS.md
.exocortex/subconscious_patterns.md
.exocortex/.env
.exocortex/.project-name
.exocortex/.install-manifest
.exocortex/events/**
.exocortex/archive/**
.exocortex/hub/**
.exocortex/local/**
.exocortex/planning/**
.exocortex/work-items/**
.exocortex/control/ACTIVE_WORK.md
.exocortex/control/BRANCH_POLICY.md
.exocortex/control/REPO_STATE.md
.exocortex/control/EXECUTOR_REGISTRY.json
.exocortex/control/EXTERNAL_SYNC_POLICY.json
.exocortex/control/INTERRUPTS.md
.exocortex/control/BACKLOG.md
.exocortex/control/ROADMAP.md
.exocortex/control/ARCH_OVERVIEW.md
.exocortex/control/REPO_ORGANIZATION_REPORT.md
.exocortex/.hub_enabled
.exocortex/.hub_disabled
```

A new install may generate blank project-local control/work-item storage, a generic executor registry in which every unregistered surface is read-only, and a generic deny-by-default `EXTERNAL_SYNC_POLICY.json`. Generated stubs contain no template identity, destination, approval, expiry, event, origin fingerprint, or source planning history, and never enter the manifest or template checksum payload.

## Migration contract — not authorized

1. Detect and classify without mutation: blank/new, generic legacy-v0, normalized generic-v1, current public-v2, unknown, malformed, duplicate, or future-version.
2. New installations create empty public-v2 local state; they do not import template history.
3. Supported legacy state may be read for orientation, but mutation stops until the owner separately approves the exact target migration and one writer.
4. Verify a local immutable backup, then stage generic legacy-v0 to normalized generic-v1.
5. Validate normalized generic-v1, then stage it to public-v2 in a separate temporary tree.
6. Recheck schema, references, authority, privacy, and exact target digest immediately before one atomic replacement.
7. Rerun and prove idempotency. Rehearsal restoration occurs only into a second disposable target.
8. Unknown, malformed, duplicate, future-version, changed-target, or unverifiable state fails closed without changing the source.

All public fixtures are generated fictional records. Private Mulligan records are not migration fixtures. Neither `install.sh` nor the updater automatically migrates live project-local work items.

## Future isolated verification contract — not authorized

The future `tests/phase-b/run.sh` must refuse to run unless its target is an absolute newly created temporary directory. It rejects the template source, user home, workspace root, and all live application repositories as targets. It uses a fake `HOME`, deny-network mode, and ordered fake transports.

Required evidence groups:

| ID | Evidence |
|---|---|
| QA-01 | Schema, base, revision, lifecycle, allowlist, and no-extra-path validation |
| QA-02 | Cold entry, dynamic routing, delegation, escalation, rejection, retry, replay, checkpoint, and handoff |
| QA-03 | Two-stage immutable-payload authorization: metadata denial before payload read, then streamed digest verification before credential, destination, child-process, copy, or network access |
| QA-04 | Public privacy, generated fixtures, data-plane/manifest exclusion, exact-diff review, and scan of the promoted tree plus every newly reachable commit |
| QA-05 | Exact-candidate syntax, integrity, installer/updater regression, and zero required skips |
| QA-06 | Disposable Healthy clean install, byte hashes, fake-home isolation, idempotency, and UAT preparation |
| QA-07 | Disposable existing-repository upgrade, protected state, first/second run, failure, and restore |
| QA-08 | Sterile Human UAT from at least two materially distinct AI/provider surfaces |
| QA-09 | Exact release disposition and bounded hypercare evidence |
| QA-10 | Executor-registry admission/rejection, approval capability, pinned source, 32-writer races, TOCTOU, revocation, and migration compatibility |
| QA-11 | Required-case completeness, mutation sensitivity, ordered fakes, and independent review |
| QA-12 | Fault-injected recovery, containment, queued-retry cancellation, and second-target restoration |

The evidence bundle contains JUnit plus a local manifest naming the exact candidate SHA/tree, generated fixture digest, every required case ID, ordered audit-log hashes, and exit status. Required cases cannot be skipped or undiscovered. Removing authority, atomicity, protected-path, or checksum safeguards must make the corresponding tests fail.

No future test runner is permitted to save, synchronize, call a real provider, read a real credential, push, deploy, install a service, or mutate a live repository.

## Target rehearsals — separately gated and not authorized

### Healthy clean install

The last read-only observation was clean `Healthy/main` at `87cd63cd9b87efb6d3b234dd2362c78242492a24`; reverify before any rehearsal.

The later test uses only a disposable copy and an exact pinned template candidate. Every pre-existing tracked file, including `.claude/launch.json`, `app/healthy.html`, and Firebase configuration, remains byte-identical. No browser profile, health data, credentials, network, build, Firebase command, service, deployment, or global editor-home action is allowed. A second installer run must create no unexpected delta or duplicate ignore entry.

A pass does not authorize installation into live Healthy.

### Existing-repository upgrade

The last read-only observation was dirty `enkratflow-ui` at `a875dca137bd6959f1308f223f3003fdaf733f75`; reverify before any rehearsal and never exercise its live checkout.

The later test uses a disposable source copy, disposable backup directory, runtime-generated generic legacy/protected fixtures, exact hashes, first apply, second-run idempotency, injected failure, and restoration into a second disposable target. It must preserve manifest-diverged files, untracked extensions, events, memory, control, `local/`, `archive/`, `hub/`, `planning/`, subconscious state, and hub markers. It performs no credential, provider, external-sync, service, browser, or production action.

A pass does not authorize upgrading the live repository.

## Twelve risk-closure gates

| Risk | Closure summary | Residual handling |
|---|---|---|
| R-01 base/release truth | Exact integration decision, containment proof or accepted supersession, immutable candidate, same tested/released SHA | Later divergence requires a new release gate |
| R-02 privacy | Exact public allowlist, generated fictional fixtures, private local-only fingerprint scan with a legitimate-public-domain allowlist, scan of candidate/installed output/promoted ancestry, independent privacy review | Any leak contains the candidate and triggers remediation assessment |
| R-03 provider neutrality | Provider-free schema plus two materially distinct adapters/surfaces passing the same contract | Adapter/provider changes require revalidation |
| R-04 checkpoints | Atomic transition/checkpoint, stable idempotency, concurrency and crash tests, zero checkpoint on non-eligible activity | Corruption fails closed into recovery |
| R-05 install/update | Complete protected hashes, unknown/diverged/untracked cases, two runs, injected failure, verified restore | Unknown paths preserve-and-stop; live targets get separate preflight |
| R-06 authority | Capabilities bind to an attested registered executor plus exact, expiring, revocable, one-time approval; missing/unregistered/mismatched surfaces fail before reservation or effect | Human approval remains non-delegable and unmanaged surfaces remain read-only/advisory |
| R-07 supply chain | Pinned candidate, complete executable integrity manifest, missing/extra/mismatch rejection before mutation | Publication and consumption pin an independently reviewed digest |
| R-08 concurrency/TOCTOU | 32-writer races, one winner, stale-writer denial, commit-time digest/expiry/revocation recheck | Unsupported atomic storage blocks use |
| R-09 migration | Explicit v0 → v1 → v2, backup, staged validation, atomicity, idempotency, unknown/future refusal | Bespoke extensions preserve-and-stop for project-local migration |
| R-10 indirect egress | One guard for every transport-capable command/helper/hook plus static bypass scan | New executable surfaces must update inventory and integrity evidence |
| R-11 false confidence | Required-case plan, zero skip, mutation sensitivity, ordered fakes, sterile cross-provider UAT | Disposable rehearsal and hypercare remain mandatory |
| R-12 recovery | Boundary fault injection, revocation, queued-retry cancellation, containment, second-target restore | Unverifiable backup blocks rollout |

All twelve remain `open`. A written mitigation is not closure evidence. R-06 specifically cannot move out of open until machine enforcement and independent negative testing exist.

## Rollback and containment — not authorized

Before any future mutation, record candidate, target, schema, approval, manifest, and protected-tree digests; verify an immutable local backup; stage separately; and recheck authority plus target digest immediately before atomic replacement.

Immediate containment triggers include unauthorized egress, protected hash drift, duplicate checkpoint, stale-writer mutation, integrity mismatch, schema ambiguity, failed restore, provider-contract failure, or a skipped/insensitive required test.

On a trigger:

1. Stop new mutations and transports.
2. Revoke outstanding capabilities and queued retries.
3. Mark the candidate contained or blocked without asserting release or Done.
4. Preserve append-only local evidence without external sync.
5. Verify the original source remains intact.
6. Restore only into a second disposable target and compare it byte-for-byte with baseline.
7. Require a new human decision before touching an original target or resuming promotion.

## Bounded hypercare — not authorized

Minimum: seven calendar days and at least 25 checkpoint-eligible protocol operations, whichever finishes later.

Coverage must include at least two materially distinct AI/provider entry surfaces; cold entry, rejection, retry, handoff, save/checkpoint separation, and a recursive-improvement proposal; both disposable install and upgrade classes; and daily local review of denials, retries, duplicate IDs, routing escalations, protected hashes, and transport audit order.

Any containment trigger restarts the process through a newly approved corrective work item and a fresh complete hypercare window. The owner separately accepts hypercare evidence and residual risks. Hypercare completion never self-authorizes promotion or live rollout.

## Acceptance criteria

1. A zero-context AI resolves exact authority, active work, state, writer, evidence, and closed gates in under five minutes.
2. Routing chooses the least-expensive orchestration-capable parent, delegates each bounded task to the least-cost capable role, escalates when needed, and returns work to one accountable parent.
3. Lifecycle transition, rejection, retry, replay, narrative save, checkpoint, and handoff behavior is deterministic and unambiguous.
4. Egress fails closed before credential, content, destination, process, copy, or network access without exact authorization.
5. The public candidate contains no private or owner-specific data and installs no project-local history.
6. Disposable Healthy installation preserves the source repository and every external-state boundary.
7. Disposable existing-repository upgrade preserves sovereign data and supports idempotent re-run and verified recovery.
8. Independent cross-provider Human UAT passes entry, rejection, retry, handoff, install, and upgrade cases.
9. Implementation, rehearsals, Human UAT, release/hypercare, promotion, and each live rollout remain separate approvals.
10. Protocol-managed authority binds to an attested registered guarded executor, is exact, current, scoped, expiring, one-time, revocable, and is revalidated immediately before effect; missing/unregistered/mismatched or unconstrained AI surfaces cannot hold writer or egress roles.
11. Supply-chain, concurrency, TOCTOU, migration, fault, evidence-completeness, and recovery cases pass with zero required skips.
12. Recursive improvement can propose—but never authorize or execute—the next bounded work item.

## Explicit G1 exclusions

- No protocol, schema, guard, installer, updater, command, hook, adapter, documentation, or test implementation.
- No implementation writer reservation.
- No fallback/main reconciliation.
- No Healthy or `enkratflow-ui` copy, install, upgrade, test, build, browser, service, or write.
- No credential lookup, provider call, push, pull request, merge, release, deployment, service action, external synchronization, version bump, template promotion, or live rollout.
- No push, merge, fast-forward, or public pull request may ever use this private-planning branch or a descendant carrying its history; public promotion requires a later clean replay and history scan.

## Next gate

The work item ends G1 at `refined`, with no writer. The next possible step is a separately approved G2 local implementation gate for exactly the create/modify paths above and one fresh writer reservation. G2 would still exclude both target rehearsals and every downstream or outward action.
