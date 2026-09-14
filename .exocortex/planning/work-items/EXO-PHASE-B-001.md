# EXO-PHASE-B-001 — Multi-AI delivery protocol generalization

## Status

- Lifecycle: `refined`
- Revision: 6
- Attempt: 0
- Exact planning base: `0eb3c667a505b90c9221ed768d47039a1638df5e`
- Branch: `codex/exo-phase-b-001-planning`
- C1 runtime revision 3: historical predecessor; authority expired
- C2 runtime revision 27: `uat_ready`; 12/12 passed; writer released
- C3 runtime revision 17: `human_uat`; 8/8 passed; owner accepted; writer released
- C4 runtime revision 13: `human_uat`; 10/10 passed; owner accepted; writer released
- C5 runtime revision 13: `qa_sit`; AC-01 through AC-09 passed; AC-10
  partial/pending; writer released
- G3 findings: resolved in the C1-C3 chain and revalidated on the clean RC
- Final 3.2.0 RC: complete local QA/SIT; independent review unconditional PASS
  with P0/P1/P2 all zero on `codex/exo-phase-b-001-rc2`
- RC Git HEAD/base: `f87fe7384ca32387772b05d591fbbd18342c458c`
- Public code-plane binding: `SHA256SUMS`
  `963dca709573b799bb17971be3ed6a4ee49508ec65f56ae6fe0ad24a402800b3`
- Current valid writer reservation: none
- Commit, live-target, release, promotion, or rollout authority: none
- Remote publication of this planning branch or its private planning history: prohibited
- Distribution: project-local planning data; never propagated to installed repositories

Revision 6 reconciles the accepted C1-C4 chain and C5 revision 13. C5 is
evidence-supported through `qa_sit`, not `uat_ready` or `release_ready`.
This parent correction creates no runtime lifecycle transition, checkpoint,
reservation, commit, outward action, live-target authority, or promotion
authority.

## Revision 6 C5 local closeout — authoritative

The final local 3.2.0 candidate is an uncommitted and unstaged working tree at
`/Users/guyrobo/EnkratFlow/exocortex-template-phase-b-rc2`.

Exact evidence:

- 262 valid manifest entries and 263 valid file-mode bindings.
- Candidate binding:
  `963dca709573b799bb17971be3ed6a4ee49508ec65f56ae6fe0ad24a402800b3`.
- Candidate-tree evidence:
  `693d6ea536a6c9c5df2ff13aaea118896ea6c63d47f71a1f734e70c284e1b6a4`.
- Git payload: 136 modified, 23 intentional removals, and 105 untracked
  manifest-covered paths; 264 total; zero staged.
- Full offline evidence:
  `d5800ea95b7b3c099046d882b14fcee95cdb17f4d35bbf733916c7fb693307fd`.
- Installer/update: 118 passed, 0 failed.
- Orchestration/routing/egress: 53 passed, 0 failed.
- Event tooling, documentation contract, checksum, mode, privacy, rollback,
  replay, idempotency, fault, and restrictive-`umask` coverage passed.
- Independent review: unconditional PASS; P0 0, P1 0, P2 0.
- No credentials, live provider, live target, or external synchronization was
  used.

The approval experience now groups human decisions into four business
envelopes: local delivery, publication, integration/rollout, and
production/egress. Exact reservations, capabilities, checkpoints, tests,
review records, lane release, and local handoffs remain internal mechanics
inside the selected envelope.

The owner accepted R3 UAT-2 semantic behavior. UAT-1 zero-context orientation,
UAT-3 routing, and UAT-4 Mulligan protections remain pending, so C5 AC-10
remains pending and C5 correctly stops at `qa_sit`.

The local handoff is `handoff-e291fb5d2eef5f6de5e5b155dfc98bf0`.
All writer lanes are released and all C5 closeout executor registrations are
expired. Commit, push, PR, merge, live installation, deployment, external
synchronization, and template promotion remain separately gated.

## Revision 5 clean-RC consolidation — historical predecessor

The isolated RC replays only the accepted public code plane onto local main
`c6ccd8358c6896d8456cb4aa19b09744ea44b1e8`. It includes the required
privacy-safe behavior from
`0eb3c667a505b90c9221ed768d47039a1638df5e` without inheriting the private
planning branch.

Exact local evidence:

- 250 valid manifest entries; portable `SHA256SUMS` digest
  `aca144f7b774aab4099b963694a39d9076b80dd2046ba3bf06689dc1b267ed40`.
- 251-path public payload digest
  `89902e8d73eb04e1a74c0651abf176a7130a612a0d7c7e30a05dc437654e0f1b`.
- 247-path RC delta digest
  `2716391d4a5ff085016244dfdfff65c219e196cf7d23926a8d049ba87aac1eff`.
- Full Phase B evidence manifest
  `2e3dff1475dd14dafb1223ed0b2dc0c64146d9d0f121c9fea4930f944f942a03`:
  57 installer/update groups, 29 orchestration tests, and event tooling passed;
  credentials, live providers, and live targets were not used.
- Healthy disposable clean-install evidence
  `fb032faef1fdfc8bd4777b8cbb85deb931529313b55e2a7bf154765e604d8c54`:
  two idempotent installs, 24 commands, 72 adapters, preserved
  `.claude/launch.json`, 112 application tests, and 37 Functions tests.
- Existing-repository fictional update evidence
  `a0f1418082ebf1975a483acafa91c725695cb5bd1105cf8bda5da008b23ba950`:
  complete 202-path dry-run, guarded apply, protected-data preservation,
  zero-path rerun, and rollback without authority resurrection.
- Privacy/history evidence
  `289f900aa4c72bbfe1edf4e2c38ec7f1155880397d4090891a4739cb7195857c`:
  the RC excludes planning, runtime authority, real events, session context,
  private application evidence, and private planning ancestry.
- Independent review
  `aa25f3a9d744057c7789c41f2428978996967535d655cde40e4a98c1a98954b7`:
  PASS with no P0 or P1 findings.
- Combined evidence manifest
  `fea91a133e3a9572bdf664ce0e6929d5bf7b0f3baedf8eb288c7882dde7f2f9b`.
- Local narrative handoff:
  `.exocortex/events/2026-07-24_11-46-56_macbook-cursor.md`, SHA-256
  `c0594ea4506c5cf44aa4336c7608b9b480aba8e4e5dcdb52b0d6ed6c4f99279a`.

Current provider evidence is version-scoped:

| Surface | Exact version | Current status | Evidence boundary |
|---|---|---|---|
| Cursor | Stable 3.12.30 | `verified` | 24/24 |
| Claude Desktop | 1.24012.1 (0adcae) | `verified` | 24/24 |
| Kimi Code CLI | 1.14.0 | `verified` | 24/24 using `/skill:{name}` |
| Zed built-in Agent | 1.12.0 stable.328 | `verified` | 24/24; ACP excluded |
| Codex | Current documented surface | `compatible` | No stronger native-menu claim |
| GitHub Copilot | Exact client version not captured | `compatible` | No version-scoped verified claim |
| Kimi Desktop | 3.1.3 | `failed` | 0/24; distinct non-default surface |
| Windsurf | Not installed | `unavailable` | Excluded from default installation |
| Generic fallback | Not applicable | Native-menu status not applicable | No native-menu claim |

Four P2 caveats remain visible rather than being hidden:

1. Healthy Functions declares Node 22; the available offline Node 20.20 run is
   smoke evidence, not exact engine-parity evidence.
2. The clean base already has three deleted operational-event paths in reachable
   history. Their blobs passed the privacy-marker scans, but zero operational
   narratives in all history would require a separately approved sanitized root
   or history rewrite.
3. The public `.gitignore` is not a complete staging barrier for all
   project-local data-plane paths. Any later commit must use the exact reviewed
   path set unless a separately approved CI/path-allowlist hardening slice lands.
4. The candidate-tree evidence includes linked-worktree `.git` pointer
   metadata and is not a portable tree identity. `SHA256SUMS` is the portable
   content binding.

The RC remains uncommitted and unstaged. No immutable release SHA exists.

## Historical G3 Human UAT reconciliation

The section below preserves the state that originally created C1-C3. Its open
findings are historical; the authoritative revision 5 section above records
their resolution and clean-RC revalidation.

The owner accepted the two disposable-target rehearsals against template HEAD
`da49a5d4bfb42acd9839b189febbe95f60b4c843` and `SHA256SUMS` digest
`d1e1d633097f8223699f3ab424524d31e7f8a26ffc7dd8eead51b343f1724443`.
The evidence remains local and is summarized by
`.exocortex/events/2026-07-22_20-28-21_macbook-cursor.md`.

Accepted outcomes:

- The disposable Healthy clean installation preserved the live source and
  passed its recorded deterministic checks.
- The fictionalized existing-repository update preserved protected and
  customized state, converged on rerun, and passed verified rollback.
- No live repository, credential, provider, network, service, deployment,
  production target, or external synchronization was used.

Open findings remain:

- `G3-F01` — P1: the stock safe-update review display omits changed paths after
  the first 120, despite reporting the correct total.
- `G3-F02` — P2: generic rollback extraction can create AppleDouble sidecars;
  the verified native macOS restore path remains required.
- `G3-F03` — P1: all 24 canonical commands are not yet available through every
  claimed provider's current native command or skill surface, and current
  reference documentation still contains live 20-command and 22-of-24 claims.

Acceptance of this UAT does not accept the open findings, authorize their fix,
or establish release, promotion, or live-rollout readiness.

## Historical C1 corrective plan — runtime superseded; no authority remains

`EXO-PHASE-B-001-C1` defined the bounded local maintenance slice for `G3-F01`
and `G3-F03`. Local implementation and deterministic independent-review
evidence are recorded in the 2026-07-23 C1 handoff. The runtime item remains
`developing`; its writer lease and executor registrations are expired, no Human
UAT acceptance is recorded, and nothing was committed.

The contract below is preserved as the historical C1 plan. Its Cursor and
Windsurf support assumptions are superseded by C2 and must not be used as
current provider truth.

The exact command-name set is:

```text
ai-export brief check-keys daily-end drill ecosystem groom handoff history
init-exocortex interrupt longterm monthly-review onboard pattern-review
prioritize refine-backlog save scrum shortterm subconscious system-scan
weekly-review work
```

Provider-native contract:

| Surface | Repository adapter | Native invocation |
|---|---|---|
| Codex | `.agents/skills/{command}/SKILL.md` | `$command` or skills selector |
| Claude | `.claude/skills/{command}/SKILL.md` | `/command` |
| Cursor | `.agents/skills/{command}/SKILL.md` | `/command` |
| GitHub Copilot | `.agents/skills/{command}/SKILL.md` | `/command` where repository skills are supported |
| Kimi Code | `.agents/skills/{command}/SKILL.md` | `/skill:command`, or `/command` when collision-free |
| Windsurf | `.windsurf/workflows/{command}.md` | `/command` |
| Generic or unidentified host | `AI_START_HERE.md` plus matching JSON | Host-dependent; no false native-menu claim |

The `{command}` placeholder expands only to the exact 24-name set above. The
prospective create/modify templates are:

```text
.agents/skills/{command}/SKILL.md
.claude/skills/{command}/SKILL.md
.windsurf/workflows/{command}.md
```

The exact fixed-file boundary is:

```text
.cursor/skills/onboard/SKILL.md
.github/skills/onboard/SKILL.md
.exocortex/AI_BOOTSTRAP.md
.exocortex/COMMAND_SYSTEM.md
.exocortex/provider-adapters.json
.exocortex/schemas/provider-adapter-matrix.schema.json
.exocortex/scripts/generate_command_adapters.py
.exocortex/docs/IDE_INTEGRATION_GUIDE.md
.exocortex/docs/UPGRADE_MANIFEST.md
.exocortex/reference/ESSENTIAL_FILES.md
.exocortex/reference/MEMORY.md
.exocortex/reference/QUICK_REFERENCE.md
.github/workflows/checksums.yml
.github/workflows/test.yml
README.md
SHA256SUMS
install.sh
scripts/safe-update.sh
tests/helpers.sh
tests/run_tests.sh
tests/phase-b/provider-adapter-matrix.json
tests/phase-b/test-plan.json
tests/phase-b/test_phase_b.py
```

The 22 current template-managed `.cursor/commands/*.md` wrappers named in the
JSON record may be superseded only after the shared native skills are proven
visible and collision-free. A downstream customized adapter must be preserved.
The `onboard` persona collisions in `.cursor/skills` and `.github/skills` must
also be resolved without losing the canonical command.

C1's corrective verification required exact 24-name equality, thin-delegate
semantics, no authority expansion, fresh-install and safe-update coverage,
customized-adapter preservation, complete change-path evidence above 120 paths,
current documentation consistency, checksums, CI, privacy coverage, and an
independent review. Its native-menu exercise then produced the provider
evidence that created C2.

## Historical C2 corrective plan — verified predecessor; superseded by C3

The detailed text below is the preserved revision 1 preimplementation plan, not
current provider truth. C2 later reached runtime revision 27 at `uat_ready` with
12/12 criteria passed and its writer released; C3 revision 17 is authoritative
for current provider status.

The historical revision 1 plan corrected the provider claims exposed by C1's
read-only native-menu exercise. It was bound to the post-C1 local candidate
evidence:

- Git HEAD: `da49a5d4bfb42acd9839b189febbe95f60b4c843`
- `SHA256SUMS` SHA-256:
  `61ec14ded36f244704ad7cdb44ce74b321697e201a97cb0c82cd8b38976edb31`
- Candidate-tree evidence SHA-256:
  `e13c2754d5a18bb982ba280d4635a7bfa4797d99e6a03a8570dcfffc5394ef0f`
- Pre-record status fingerprint, captured before revision 4 planning edits:
  `9500fec3e4f69af1d94ae3e7b3f7cfb9a171cf065567ac6f5ccc8d2b8c23d3d8`

Those values are historical planning evidence, not current release truth.

### Provider evidence statuses

Statuses are scoped to the recorded version and evidence set. A provider,
client, adapter, discovery, or configuration change invalidates stale evidence
and requires revalidation before a support claim is promoted.

| Status | Meaning |
|---|---|
| `verified` | The recorded installed version passed complete native-menu Human UAT |
| `compatible` | The documented contract and static structure match, but complete Human UAT is pending or partial |
| `failed` | The recorded installed version produced a concrete reproducible failure |
| `blocked` | A prerequisite such as authentication prevented Human UAT |
| `unavailable` | No installed local surface exists for Human UAT |

Current evidence:

| Surface | Version | Status | Evidence boundary |
|---|---|---|---|
| GitHub Copilot | Exact client version not captured | `compatible` | 24/24 observed; capture the client version before promoting to verified |
| Codex | Current desktop task | `compatible` | Repository catalog 24/24; literal selector observation pending |
| Cursor | 3.6.21 | `failed` | `.agents/skills` commands absent while `.cursor/skills` entries appeared |
| Claude Code | 2.1.214 | `blocked` | Expired OAuth; authentication and session remain separate user actions |
| Kimi Code | 1.14.0 | `compatible` | Native contract matches; Human UAT pending and syntax is `/skill:{name}` |
| Zed | 0.230.1 | `compatible` | Built-in Agent documents `.agents/skills`; Human UAT pending |
| Windsurf | Not installed | `unavailable` | Remove from current advertised/default support |
| Generic fallback | Not applicable | Native-menu status not applicable | Provider-neutral entry makes no native-menu claim |

### Cursor/Windsurf correction

The corrected default remains exactly 72 generated adapters:

- 24 portable `.agents/skills/{command}/SKILL.md` adapters for provider-neutral
  Agent Skills consumers;
- 24 `.claude/skills/{command}/SKILL.md` adapters; and
- 24 `.cursor/skills/{command}/SKILL.md` adapters.

Cursor adapters remain manual-only with
`disable-model-invocation: true` and point to `AI_START_HERE.md` plus exactly
one canonical command JSON. Verification must cover duplicate discovery across
`.agents` and `.cursor` roots and the `onboard` name collision.

Windsurf workflows and `.windsurfrules` leave the active support claims and
fresh/default installation. Historical changelog entries remain historical.
Windsurf may return only through a later, version-specific evidence gate.

### Exact 68-path boundary

- Exact path count: 68
- SHA-256:
  `4189e80b105b07170e796d95c9dd9eab2426cadf7ac128f7d9d588150574ac48`
- Digest rule: SHA-256 over the UTF-8 lexicographically sorted exact relative
  paths, with one LF after every path including the final path
- Composition: 20 fixed paths, 24 new Cursor skills, and 24 retiring Windsurf
  workflows

The full expanded path list in the JSON planning record is normative. The
generated groups are:

```text
.cursor/skills/{one of the 24 canonical commands}/SKILL.md
.windsurf/workflows/{one of the 24 canonical commands}.md
```

The 20 fixed paths are:

```text
.exocortex/AI_BOOTSTRAP.md
.exocortex/COMMAND_SYSTEM.md
.exocortex/docs/IDE_INTEGRATION_GUIDE.md
.exocortex/docs/UPGRADE_MANIFEST.md
.exocortex/provider-adapters.json
.exocortex/reference/ESSENTIAL_FILES.md
.exocortex/reference/MEMORY.md
.exocortex/reference/QUICK_REFERENCE.md
.exocortex/schemas/provider-adapter-matrix.schema.json
.exocortex/scripts/generate_command_adapters.py
.windsurfrules
CHANGELOG.md
README.md
SHA256SUMS
WHATSNEW.md
install.sh
scripts/safe-update.sh
tests/phase-b/provider-adapter-matrix.json
tests/phase-b/test_phase_b.py
tests/run_tests.sh
```

This boundary is prospective planning evidence only. It grants no mutation
authority.

### Cumulative migration protections

C2 preserves C1's 24 prior retirement mappings and adds 25 Windsurf retirement
mappings: 24 workflows plus `.windsurfrules`. The cumulative protected
retirement inventory is therefore 49 paths.

A file may be retired only when the prior install manifest proves template
ownership and the current file is byte-identical to the owned template version.
Customized, unknown, or conflicting files remain untouched with
`EXOCORTEX_ADAPTER_COLLISION_PRESERVED`. Tests must cover direct upgrades from
both pre-C1 and C1 installations, already-absent files, collisions, rerun
idempotency, and rollback.

### Claude, Kimi, and Zed Human UAT plans

- **Claude 2.1.214:** after separately authorized owner authentication, use
  masked valid/invalid status only; capture a fresh Git baseline before
  launching; use a no-history, plan-permission, non-persistent, no-browser
  session; type all 24 commands without pressing Enter; require the Exocortex
  descriptions; execute nothing; compare post-session Git state with that
  baseline.
- **Kimi 1.14.0:** under separate temporary-state approval, redirect all state
  into one exact disposable directory, disable update checks, unset
  `KIMI_API_KEY`, use empty inline configuration, and select only the candidate
  work and skills directories. Capture a fresh Git baseline before launching,
  confirm 24 `/skill:{name}` entries plus two built-ins, send no model request,
  compare post-session Git state with the baseline, and delete only the
  validated disposable directory.
- **Zed 0.230.1:** capture a fresh Git baseline before opening Zed, use the
  built-in Zed Agent against the candidate, verify all 24 project-local Agent
  Skills without invocation, and compare post-session Git state with the
  baseline. ACP-hosted agents are separate surfaces and remain out of scope.

C2 passes only after deterministic install/update/migration/privacy coverage,
the applicable provider UAT, and independent correctness, compatibility,
migration, privacy, and authority review produce no actionable P0 or P1.

Implementation, authentication, provider sessions, commit, installation,
push/PR, merge, release/deployment, external synchronization, and template
promotion remain closed.

## Outcome sought

Generalize the accepted multi-AI delivery behavior into a privacy-safe, provider-neutral Exocortex template that supports recursive improvement while preserving human sovereignty.

Any supported AI should be able to enter cold, recover exact Git and project-local authority, understand current work and evidence, select or delegate work by capability and cost, enforce one writer, and stop before unauthorized mutation or outward action. A completed cycle may generate measured retrospective evidence and propose a bounded next work item. It may not approve or start that next item itself.

## Reference binding

| Reference | Exact SHA | Use |
|---|---|---|
| Required privacy-safe correction | `0eb3c667a505b90c9221ed768d47039a1638df5e` | Replay its behavior without inheriting planning ancestry |
| Approved clean-RC base | `c6ccd8358c6896d8456cb4aa19b09744ea44b1e8` | Exact local-main base for the isolated clean candidate |
| Accepted C3 public code plane | `SHA256SUMS aca144f7b774aab4099b963694a39d9076b80dd2046ba3bf06689dc1b267ed40` | Only accepted source plane for the clean replay; planning/runtime/private material excluded |
| Accepted Mulligan record | `50cd1c3db6d69c6d16a68e8935576016b21276b2` | Recorded private reference identifier and prior privacy-safe audit summary; object absent from this repository |
| Mulligan implementation candidate | `b63463f784d3e51f47b787e29222bba91dce60e0` | Recorded private behavioral reference identifier and prior summary; object absent from this repository |

The private objects are intentionally absent from the template Git object database and cannot be independently verified here. A later conformance comparison requires separately authorized read-only source inspection or a fictionalized privacy-safe evidence packet. Importing the private objects or history is never required or authorized.

The Mulligan references are evidence pointers, not template payload. No private work item, event, handoff, identity, path, branch, SHA, reservation, origin metadata, endpoint, approval history, or application fixture may enter the public candidate.

Installer exclusion alone is insufficient because Git history can leak planning
data. This planning branch and any descendant carrying these records must never
be pushed, merged, fast-forwarded, or used directly for a public pull request.
The clean RC branch now provides the only permitted public-candidate route, but
it remains local and uncommitted.

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
6. **Passed on the clean RC:** Disposable Healthy installation preserves every
   pre-existing tracked file byte-for-byte except for one deterministic
   appended Exocortex-managed `.gitignore` block, which leaves all pre-existing
   `.gitignore` bytes and order intact. Exact Node 22 Functions engine parity
   remains a disclosed environment check.
7. **Passed on the clean RC:** Disposable existing-repository upgrade preserves
   sovereign data, emits the complete deterministic changed-path evidence, and
   supports guarded apply, zero-change rerun, and verified recovery.
8. **Passed through accepted C2/C3 Human UAT and clean-RC review:** Exact-version
   provider evidence is complete for the four verified surfaces, with honest
   limitations recorded for every other surface.
9. Implementation, rehearsals, Human UAT, release/hypercare, promotion, and each live rollout remain separate approvals.
10. Protocol-managed authority binds to an attested registered guarded executor, is exact, current, scoped, expiring, one-time, revocable, and is revalidated immediately before effect; missing/unregistered/mismatched or unconstrained AI surfaces cannot hold writer or egress roles.
11. Supply-chain, concurrency, TOCTOU, migration, fault, evidence-completeness, and recovery cases pass with zero required skips.
12. Recursive improvement can propose—but never authorize or execute—the next bounded work item.

## Historical G1 exclusions

- No protocol, schema, guard, installer, updater, command, hook, adapter, documentation, or test implementation.
- No implementation writer reservation.
- No fallback/main reconciliation.
- No Healthy or `enkratflow-ui` copy, install, upgrade, test, build, browser, service, or write.
- No credential lookup, provider call, push, pull request, merge, release, deployment, service action, external synchronization, version bump, template promotion, or live rollout.
- No push, merge, fast-forward, or public pull request may ever use this private-planning branch or a descendant carrying its history; public promotion requires a later clean replay and history scan.

## Next gate

The planning-v1 item remains `refined` at revision 5. This reconciliation
creates no lifecycle transition or checkpoint, and no writer is reserved.

The owner-approved local clean-RC preparation is complete. The exact candidate
is the uncommitted working tree on `codex/exo-phase-b-001-rc1`, based at
`c6ccd8358c6896d8456cb4aa19b09744ea44b1e8` and bound by `SHA256SUMS`
`aca144f7b774aab4099b963694a39d9076b80dd2046ba3bf06689dc1b267ed40`.

Before any commit decision, the owner should review the Node 22 engine-parity,
pre-existing base-history, and staging-barrier caveats. A later exact commit
gate must bind the 247-path delta digest
`2716391d4a5ff085016244dfdfff65c219e196cf7d23926a8d049ba87aac1eff`,
use exact-path staging, rerun the final checks against the staged tree, and
produce an immutable local candidate SHA.

No `release_ready` transition, commit, push or PR, merge, release, deployment,
live-target action, external synchronization, template promotion, or hypercare
acceptance is authorized.
