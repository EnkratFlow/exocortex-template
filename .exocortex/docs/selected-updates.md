# Selected-project updates

**Candidate status: local integration verified; unpublished.** The disposable
guarded-update fixture passes preview, apply and installation verification while
preserving handwritten memory. Independent review and native Windows validation
of this combined candidate remain pending.

Ordinary installations contain two public examples, `.exocortex/.env.example`
and `.exocortex/key-registry.json`. The coordinator accepts them only when declared
in the installed manifest and byte-identical to the packaged public examples.
It compares hashes without decoding or reporting their contents. Modified copies
require separate review and block before updater execution; this includes copies
with changed line endings. Other credential-shaped files retain their existing
protection. The interface below describes an unpublished candidate.

`/updates` lists projects and versions. `/updates release` manages optional release
notices. `/updates selected` coordinates updates only for projects explicitly chosen
by their owner. All three use the same project identity and checkout facts.

The initial implementation is local and sequential: choose one working folder per
Git family and at most 20 projects. Other machines require their own local plan.
Personal and work account scopes must be selected separately. An account label is
an organizational boundary, not a credential or proof of repository ownership.

## Workflow

1. Select exact project roots, the template source and a separate recovery folder.
2. Create and inspect a machine-local plan. Unavailable targets appear as blocked.
3. Preview each selected project. This writes a recovery archive and local receipts;
   the target is unchanged. Inspect readiness, changed paths and any customization
   collision before requesting apply approval.
4. Use the existing guarded-update workflow to supply exact per-project authority.
   The coordinator does not create or broaden that authority. Every apply repeats
   source authentication and preview before delegating to the guarded updater.
5. Read per-project outcomes. Successful installation requires the guarded updater's
   completion receipt and a second preview with zero changes. It says nothing about
   Git commits, pushes, merges, application deployment or service restarts.

Plans live in `.exocortex/local/update-plans/` in the controlling project. They bind
the selected roots, Git identities, installed code, template digest and revision.
Changing the selection requires a new plan. Every mutating command requires the
current `plan_sha256` returned by `show`; a stale digest is rejected.

## Helper interface

Run `python3 .exocortex/scripts/update_selected.py --help` for arguments. These are
placeholders, not commands to run without choosing real targets and permissions:

```text
create PLAN --template SOURCE --digest MANIFEST_SHA256 --backup-root RECOVERY
  --target PROJECT_ROOT [--target SECOND_ROOT] --account-scope SCOPE
  --repository OWNER/REPO --tag vX.Y.Z --commit COMMIT_SHA --manifest-asset ASSET
show PLAN
preview PLAN --expected PLAN_SHA256
apply PLAN --expected PLAN_SHA256 --authority-file LOCAL_AUTHORITY_REFERENCES
recovery PLAN --target-id target-1
confirm-restored PLAN --target-id target-1 --expected PLAN_SHA256 --evidence TEXT
```

`--project-root` selects the controlling project. Omitting all four release fields
creates an explicitly local, preview-only candidate. It cannot authorize apply.
For live updates, retain the verified release asset named `SHA256SUMS`. The source
must match its exact GitHub repository, stable release tag and commit. GitHub CLI
release and asset verification must succeed immediately before candidate execution;
offline, deleted or unverifiable releases block the operation. The selected source
and all targets must be disjoint from the recovery folder.

The authority-reference file must be named `authority-NAME.json` under the
controlling project's `.exocortex/local/update-authorities/`. It maps selected IDs such as `target-1` to existing
`capability`, `work_item_id`, `work_item_revision`, `request_id`, `surface_id`,
`executor_id` and `adapter_version` values. Capabilities must be project-relative
paths under `.exocortex/local/protocol/capabilities/`. This file carries references,
not secrets. Guard validation remains in the existing updater; a plan, selection,
version notice or conversational approval cannot bypass it.

## Failure and recovery

Outcomes include ready, current, blocked, applying, applied, recovery required,
verification failed and restored. A blocked target does not prevent independent
selected projects from being inspected. Failed or uncertain apply leaves a durable
recovery marker for that Git family and never retries automatically. Retain the
archive, local diagnostics and guarded transaction records.

`recovery` reports the stored packet. Review actual target state and capability
consumption before separately authorizing any restoration. Never restore project
memory, credentials or consumed capabilities from a code archive. No automatic
extraction is implemented. `confirm-restored` records the review only after the prior
managed code, file modes and Git identity match exactly; it does not restore files.
Then create a new plan and obtain fresh authority. Do not delete locks to force a
retry. An interrupted process may require manual inspection of both lock ownership
and persistent recovery evidence before a lock can be retired.

Customized command collisions stop ordinary apply. Use the existing exact command
reconciliation process rather than broad exclusions or overwrite switches.
Unclassified files inside the installed code surfaces also block preflight without
opening their contents. Review them separately; do not relocate or delete unique
configuration or notes just to force an update through.
Windows uses the shipped PowerShell launcher with Git for Windows; native Windows
validation runs in CI. No schedule, background service or consumer update is enabled
by installing this helper.

## Customized repositories are separate review targets

A repository with local changes to managed Exocortex instructions, commands or
scripts is blocked before preview or apply. The coordinator reports relative
paths, hashes and a three-way classification against the installed manifest and
selected incoming manifest: `local-only`, `upstream-only`, `converged`, `conflict`,
`deleted` (locally removed), or `unknownbaseline`. Unchanged files are omitted.
Local-only changes, conflicts, local deletions and unknown baselines require
separate review. Converged bytes already match the incoming template and are
allowed, as are upstream-only changes. This compares contents; the existing
updater still verifies file modes and the complete candidate. No contents are
included in this report. Unclassified local code is blocked without opening it,
with an actionable path in the reason. Protected memory and runtime data are
excluded from this comparison and remain preserved by the updater. Template CI
workflows are not installed. The project-owned root `.gitignore` is not compared
with the template repository's `.gitignore`; the installer only appends its managed
ignore blocks. Declare that path in policy if it needs separate project review.

A project owner may separately create the private, machine-local policy
`.exocortex/local/update-policy.json`:

```json
{
  "mode": "review_only",
  "protected_paths": ["firebase.json", "docs/SDLC.md"],
  "reason": "Project-specific deployment and delivery workflow"
}
```

`mode` must be `standard`, `review_only` or `excluded`; `protected_paths` is
required and contains up to 100 unique exact relative paths, without globs,
traversal, credential paths or protected memory/runtime paths. The optional
`reason` is private prose and is not copied into inventory or plan output.
Absent policy defaults to standard inspection. Both `review_only` and `excluded`
block batch execution. Any declared protected path also requires separate review,
even in standard mode. Paths can describe deployment or SDLC customizations
outside Exocortex; their contents are never opened by this policy check, and a
path need not currently exist. Firebase presence alone does not imply a conflict.
The coordinator cannot infer the semantics of every application configuration.

Selection binds the policy's presence and exact bytes plus the customization
report. A changed, removed, malformed or linked policy fails closed before
execution. The coordinator never creates policies, offers no force override,
and never interprets a reconciliation capability as approval to sweep a custom
project into an ordinary batch. Resolve such projects through a separately
reviewed project-specific update. Other independently selected standard projects
may continue. Inventory displays declared policy state; it does not perform the
incoming-template comparison or certify update readiness.
