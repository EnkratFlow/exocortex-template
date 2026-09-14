# User Guide

## Starting any AI session

Ask the AI to read `AI_START_HERE.md`. It should identify the current project,
live Git state, exact work item/revision/base, writer status, passed and pending
evidence, and the next gate without changing anything.

Use `/work` for a normal entry, `/onboard` for deeper code orientation, and
`/system-scan` for a read-only health report.

## Giving approval

Approve one bounded gate at a time. Local implementation, local recording,
commit, push/PR, merge, release/deployment, service action, external sync, and
template promotion are distinct. A broad “yes” never carries authority forward.

For a mutation, expect the exact work item revision, operation, allowed paths,
target/base digest, executor, and expiry. For egress, also expect the immutable
descriptor, payload digest/size/class, destination, method, and outward effect.

## Saves and checkpoints

`/save` captures useful local narrative memory after you review it. It does not
mark work complete or create a lifecycle checkpoint. A checkpoint exists only
for an accepted authorized transition designated checkpoint-eligible.

Nothing is sent to RAG, a vault, hub, provider, or another repository
automatically.

## Multi-AI work

Any capable AI can enter through the same contract. One parent owns integration
and one registered writer mutates. Other models gather bounded evidence or
review read-only. Routing favors the least-expensive capable model, then
escalates when risk or evidence requires stronger capability.

`/handoff` prepares strict local evidence for another provider. It does not
transfer the writer lane or authorize continuation by itself.

## Recursive improvement

Run `/pattern-review` or a retrospective after a bounded pilot. The result is a
proposal: recurring friction, candidate skills, memory facts, missing tests, or
protocol improvements. Choose one low-risk item, approve it as a new work item,
verify it, complete Human UAT, and promote separately. The system never approves
its own recommendation.

## Installation and updates

For a new repository, rehearse a pinned local template install in a clean
sanitized disposable fixture with fake `HOME` and a separately approved
candidate digest. After separate approval, install only in a clean isolated Git
worktree from the approved target HEAD. Direct installation in a shared or
primary checkout is unsupported.
For an existing repository, use `safe-update.sh` with that exact
`--candidate-digest`, an explicit disposable backup directory, and dry-run first.
Run the AI installation guide's metadata-only legacy protected-default
preflight before dry run. Missing generic scaffolding is separately
bootstrapped and must never overwrite project data. Verify protected project
data remains byte-identical. Never use a live app as the first installer or
updater test.

You may give the clean-install or existing-update prompt from
`.exocortex/docs/AI_INSTALLATION.md` to a coding AI with local terminal access.
It must begin read-only and stop for exact approval before rehearsal, isolated
worktree creation and installation, local commit, and each outward action.

See the root `README.md` and `.exocortex/docs/UPGRADE_MANIFEST.md` for exact
boundaries.
