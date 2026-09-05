# User Guide

## Starting any AI session

Ask the AI to read `AI_START_HERE.md`. It should identify the current project,
live Git state, exact work item/revision/base, writer status, passed and pending
evidence, and the next gate without changing anything.

Use `/work` for a normal entry, `/onboard` for deeper code orientation, and
`/system-scan` for a read-only health report.

## Giving approval

Approve understandable business outcomes, not internal protocol artifacts.
The AI should present one concise plain-language envelope:

1. local delivery for one bounded local outcome, tests, review, UAT recording,
   local handoff, and writer release;
2. publication for one reviewed commit, named-branch push, and draft PR;
3. integration/rollout for an exact merge, release, promotion, or named
   repository update; or
4. production/egress for one exact deployment, service action, or external
   payload to a named destination and method.

The orchestrator still binds the exact work item, operation, allowed paths,
target/base digest, executor, expiry, and verification internally. Do not
approve work-item bookkeeping, writer reservations, technical capabilities,
checkpoints, evidence records, handoffs, or writer release one by one when
they are fully contained in an active business envelope.

A changed target, base, digest, path/plan, operation class, risk, or ambiguous
effect requires one replacement decision. A broad “yes,” “everything,” or
“everywhere” grants no scope. Business-gate classes never carry authority
forward.

For a file-changing local task, the system first uses
`bootstrap-local-delivery` to check the approved clean isolated worktree, exact
base, branch, and allowed paths, then atomically creates/reserves/activates the
item in `developing`; that is not a normal transition or checkpoint. It then
uses `seal-local-edit` to record the actual changed set. Developer verification,
independent review, QA/SIT, UAT-ready, and an explicit Human-UAT transition
still occur. Only then can `complete-local-delivery` record
`local_state=complete`, create one local completion event and handoff, and
release the writer while lifecycle remains `human_uat`; `release_ready` and
publication are separate. This does not approve a commit, push, release,
deployment, synchronization, credential access, or network action.

The bootstrap `--envelope-source` and completion `--body-file` must be
project-relative regular files under `.exocortex/local/protocol/inbox/`.
Credential-shaped names (`.env`, `.env.*`, private-key formats, `credentials`,
or `secrets`) are rejected before opening. You should see non-empty evidence
at developer verification, independent review, QA/SIT, UAT-ready, and Human
UAT; each transition capability binds its full transition intent. The Human-UAT
record names an attestor matching the envelope approver. This is cooperative
local evidence, not cryptographic proof of that person's identity. Acceptance
criteria remain pending through `uat_ready`; the accepted Human-UAT transition
refuses failed or blocked criteria, records the remaining criteria as passed
with its evidence, and closeout rechecks that every criterion still carries
the exact Human-UAT transition marker and evidence. Closeout also verifies the
transition against its consumed one-time capability and finalized guarded
transaction.

## Saves and checkpoints

`/save` first drafts useful local narrative memory in chat. Choose either
“keep in chat” or “save this exact summary locally.” It does not mark work
complete or create a lifecycle checkpoint. When local recording is already
inside an active local-delivery envelope, the orchestrator handles the exact
internal record capability without another approval prompt. A checkpoint
exists only for an accepted authorized transition designated
checkpoint-eligible.

Nothing is sent to RAG, a vault, hub, provider, or another repository
automatically.

`create_event.sh` remains the manual `/save` helper for narrative events. It
does not perform local-delivery closeout, accept UAT, or release a writer.

## Multi-AI work

Any capable AI can enter through the same contract. One parent owns integration
and one registered writer mutates. Other models gather bounded evidence or
review read-only. The parent chooses the best expected cost of a correct
outcome and applies the same judgment to every subagent. It reports route and
ETA for visibility without turning routine model selection into an approval
gate.

When maintained, fresh source, exact-surface availability, and measured
evaluation evidence can support an optional formal route; advertised newness
or price cannot. The packaged catalog is advisory and cannot formally route as
shipped, but that does not block parent judgment. Discovery quarantines new
entries and never activates them.

`/handoff` prepares strict local evidence for another provider. It does not
transfer the writer lane or authorize continuation by itself.

## Recursive improvement

Run `/pattern-review` or a retrospective after a bounded pilot. The result is a
proposal: recurring friction, candidate skills, memory facts, missing tests, or
protocol improvements. Choose one low-risk item, approve one bounded
local-delivery outcome, verify it, complete Human UAT, and use a later
integration/rollout decision if it should be promoted. The system never
approves its own recommendation.

## Installation and updates

For a new repository, rehearse a pinned local template install in a clean
sanitized disposable fixture with fake `HOME` and an exact reviewed candidate
digest. The human-facing flow has two local decisions: approve the disposable
rehearsal, then approve installation into one named clean isolated Git
worktree from the accepted target HEAD. Bootstrap, reservation, technical
apply capability, tests, local handoff, and writer release are internal
mechanics of that second decision. Direct installation in a shared or primary
checkout is unsupported; the primary checkout is unsupported as an install
target.
For an existing repository, use `safe-update.sh` with that exact
`--candidate-digest`, an explicit disposable backup directory, and dry-run first.
Run the AI installation guide's metadata-only legacy protected-default
preflight before dry run. Missing generic scaffolding is created only as an
internal fail-closed bootstrap under the accepted named-target apply decision
and must never overwrite project data. Verify protected project data remains
byte-identical. Never use a live app as the first installer or updater test.

If the ordinary updater preserves customized collisions, do not merge them
implicitly. Use the AI installation guide's target-specific reconciliation
contract, exact reviewed plan, disposable rehearsal, and internally derived
`apply_template_reconciliation` capability. A changed plan or effect set
requires a replacement named-target apply decision.

You may give the clean-install or existing-update prompt from
`.exocortex/docs/AI_INSTALLATION.md` to a coding AI with local terminal access.
It must begin read-only, ask once for the disposable rehearsal, ask once for
the named-target local apply, and later use separate publication,
integration/rollout, and production/egress decisions as applicable.

See the root `README.md` and `.exocortex/docs/UPGRADE_MANIFEST.md` for exact
boundaries.
