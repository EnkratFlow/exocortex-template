# Install or update Exocortex with a coding AI

This is the provider-neutral operator contract for asking a coding AI to
install or update Exocortex in a local repository. It does not grant authority.
The AI must have local filesystem and terminal access to the target repository.
A chat-only assistant or a provider menu that can only discuss files cannot
perform an installation.

The AI uses the same pinned `install.sh` and `scripts/safe-update.sh` paths as a
human operator. It does not invent a provider-specific installer, fetch
`latest`, pipe a remote script into a shell, read credentials, change a global
editor home, or combine installation with Git publication.

For every manual command, `.exocortex/commands/<name>.json` is the sole
command-flow behavior source beneath `AI_START_HERE.md`. Project/provider
instructions may point to it but cannot restate or override it. If they
conflict, report the deviation in one line and follow the JSON without
combining the conflicting instructions.

## Acquire an exact GitHub release

The release notes must publish the exact tag, its peeled 40-character commit
SHA, and the SHA-256 of that tag's `SHA256SUMS`. For version 3.2.6, acquire and
verify the public artifact like this:

```bash
git clone --depth 1 --branch v3.2.6 \
  https://github.com/EnkratFlow/exocortex-template.git \
  /tmp/exocortex-template-v3.2.6
git -C /tmp/exocortex-template-v3.2.6 rev-parse HEAD
shasum -a 256 /tmp/exocortex-template-v3.2.6/SHA256SUMS
```

Compare both outputs with the release notes. Stop on either mismatch. Never
replace the exact tag with `main`, `latest`, or another mutable reference.
After verification, use that clone as `<absolute-pinned-template-path>` and
its published digest in the prompts below.

## Local prerequisites

The current installer and updater require Bash 3.2+, Python 3.9+, `shasum` or
`sha256sum`, `awk`,
`tar`, `find`, `grep`, `sed`, `sort`, `mktemp`, `diff`, `cp`, `mv`, `chmod`,
`mkdir`, `rm`, `basename`, `dirname`, `cat`, `date`, `tr`, and `wc`. Git is
required to acquire, pin, and inspect the template revision; the installer and
updater do not invoke Git. `rsync` is optional because the installer has a
`tar` fallback, while `tar` remains mandatory for safe-update restore archives.
The guarded apply uses Python's Unix-only `fcntl` module, which is available on
the supported macOS/Linux/WSL path but not native Windows Python. Deterministic
repository verification additionally uses `rg` and the dependencies of the
target application's own tests; `rg` is not an install/update runtime
dependency.

The AI must inventory these command names and versions during read-only
preflight. A missing prerequisite blocks installation; it does not authorize
the AI to install packages or substitute an untested tool.

## Platform status

| Environment | Status | Boundary |
|---|---|---|
| macOS with Bash and the documented Unix tools | `verified` | Current local deterministic and disposable-target evidence |
| Linux | `compatible_pending_candidate_CI` | The repository CI is configured for Ubuntu; the final candidate must pass before promotion |
| Windows through WSL | `human_uat_pending` | Use only after the exact WSL environment passes the same bounded rehearsal |
| Windows through Git Bash | `unsupported` | Required tools and path behavior have not been verified |
| Native Windows PowerShell or Command Prompt | `unsupported` | No native shared installer exists; do not translate the security logic ad hoc |

WSL is not native Windows support. A future native Windows claim requires one
shared cross-platform implementation, deterministic Windows CI, rollback
verification, and Human UAT. An AI must report an unsupported platform rather
than silently improvising.

## Before pasting a prompt

1. Open the exact target repository in a coding agent with local terminal
   access, such as Codex, Claude Code, Cursor, GitHub Copilot coding tools, Zed's
   built-in Agent, or Kimi Code CLI.
2. Identify the exact reviewed Exocortex template Git SHA. Never request
   `latest` or an unpinned branch.
3. Obtain the separately reviewed SHA-256 of that revision's `SHA256SUMS`.
   Its checksum-listed `FILEMODES` inventory binds normalized `0644`/`0755`
   source permissions and must validate before target mutation.
   The AI may recompute and compare it, but it must not choose and approve the
   digest on the owner's behalf.
4. For an existing repository, decide where an external disposable backup and
   rehearsal can be created.

Provider command-menu visibility is not installation authority. The same
read-only preflight and approval boundary applies to every provider.

## Human-facing installation decisions

Installation and update use two local business decisions:

1. `disposable rehearsal`: one exact pinned candidate, sanitized fixture,
   target snapshot, failure-containment plan, and verification matrix;
2. `named-target local apply`: one exact target repository/worktree, accepted
   base, candidate digest, changed paths or reviewed reconciliation plan,
   rollback, tests, local handoff, and writer release.

Work-item creation, missing-default bootstrap, executor registration, writer
reservation/release, one-time technical capabilities, transaction records,
eligible checkpoints, evidence files, and the permitted local handoff are
internal safety mechanics. The AI must not ask the human to approve them one
by one after the applicable business decision is accepted.

The guard still fails closed on a changed target, base, candidate digest,
path/plan set, operation class, risk, verification boundary, expiry, or
ambiguous prior effect. Such a mismatch requires one replacement business
decision. Local delivery never authorizes Git publication, merge,
release/deployment, service action, external synchronization, template
promotion, or another live-repository rollout.

## Copy-paste prompt: clean installation

Replace every angle-bracket placeholder before approval. It is acceptable to
give the AI the target path first and let it report the other exact values
during read-only preflight.

```text
Prepare a read-only Exocortex clean-install preflight for this repository.

Target repository: <absolute-target-path>
Pinned template source: <absolute-local-template-path>
Approved template Git SHA: <40-character-sha>
Approved SHA-256 of SHA256SUMS: <64-character-digest>

Read the pinned template's .exocortex/docs/AI_INSTALLATION.md and
AI_START_HERE.md. Confirm the exact target, target Git branch and HEAD, dirty
state, platform, template SHA, manifest digest, expected code-plane paths,
pre-existing path collisions, and disposable rehearsal location. Do not read
or display .env or credential values. Do not change the target, HOME, global
editor state, services, providers, Git index, remotes, or external systems.

Explain the disposable rehearsal and failure-containment plan, the exact files
expected to change, the tests that will run, and the later business gates.
Stop and ask once for my disposable-rehearsal decision. Do not install into
the named target, commit, push, open a PR, merge, deploy, synchronize, or
promote in the same step.
```

After the AI reports the exact preflight, the owner may approve the disposable
rehearsal in plain language. A bare “yes” without the displayed candidate,
target snapshot, and rehearsal scope is not approval for a named-target apply,
Git, or outward action. The AI then:

1. inventories only the manifest-defined install surfaces and known collision
   paths. It may hash approved non-secret regular files on those surfaces, but
   must exclude `.env`, credential-bearing content, raw user/project data, and
   every unapproved path. A symlink on an install surface blocks the rehearsal;
2. creates a sanitized disposable fixture containing only the approved
   non-secret install surfaces and known collisions, plus a fake `HOME`;
3. verifies the pinned template SHA, approved `SHA256SUMS` digest, complete
   checksums, and checksum-bound `FILEMODES` inventory;
4. in one disposable fixture, injects an unsafe symlink or path-type collision
   that the installer must reject before target mutation;
5. in another disposable fixture, injects a controlled write failure after at
   least one install copy. It proves all partial changes stayed inside that
   disposable fixture, then quarantines or discards it and recreates from the
   clean baseline. If this mid-copy containment cannot be demonstrated, the
   platform fails the rehearsal;
6. runs the installer in a fresh disposable target twice;
7. proves approved pre-existing files and fake/global state were preserved;
8. reports exact changed paths and deterministic test evidence;
9. presents one concise named-target local-apply envelope for a clean isolated
   Git worktree from the approved target HEAD, with no untracked credential
   files;
10. after that single decision, internally creates the worktree authority,
    installs and verifies only in the isolated worktree, records the permitted
    local handoff, releases the writer, and stops; and
11. leaves publication, integration/rollout, and production/egress as later
    business decisions.

A clean installation has no updater restore archive and the current installer
writes in place. Its rollback boundary is therefore isolation: a partial
failure is contained by quarantining or discarding the isolated fixture or
worktree and recreating it from the approved clean Git base. Direct installation
into a shared or primary checkout remains unsupported until the installer has a
tested atomic commit or target-specific restore mechanism.

After the named-target local-apply decision, the underlying local command on
macOS or a verified Linux/WSL environment is:

```bash
cd <absolute-approved-isolated-worktree-path>
HOME=<absolute-disposable-home> \
EXOCORTEX_LOCAL_SOURCE=<absolute-pinned-template-path> \
EXOCORTEX_CANDIDATE_DIGEST=<approved-sha256-of-SHA256SUMS> \
  bash <absolute-pinned-template-path>/install.sh "<project-name>"
```

The fake `HOME` is mandatory for the rehearsal. The approved real-target action
must still avoid global editor-home changes.

## Copy-paste prompt: existing-repository update

```text
Prepare a read-only Exocortex safe-update preflight for this repository.

Target repository: <absolute-target-path>
Pinned template source: <absolute-local-template-path>
Approved template Git SHA: <40-character-sha>
Approved SHA-256 of SHA256SUMS: <64-character-digest>
Disposable backup root: <absolute-path-outside-target-and-template>

Read the pinned template's .exocortex/docs/AI_INSTALLATION.md,
AI_START_HERE.md, and .exocortex/docs/UPGRADE_MANIFEST.md. Confirm the target
Git state, installed Exocortex version and manifest, platform, template SHA and
digest, full protected-data inventory, expected migration paths, collision
behavior, and rollback method. Never read or display .env or credential values.
Report presence and path type only for the required legacy protected defaults
listed below. If any is absent or the wrong path type, stop before dry run and
include the exact missing-default bootstrap in the disposable-rehearsal
envelope; do not create it implicitly.

Plan the updater's built-in dry run with fake HOME and no network. It must hash
protected paths before and after, print the complete sorted changed-path list
and its digest, and leave the live repository untouched. State explicitly that
one --dry-run does not apply the update, run application tests, prove a
post-apply zero-change rerun, or restore the archive. Those are separate
deterministic checks inside the rehearsal described below. Stop and ask once
for my disposable-rehearsal decision. Do not apply to the named target,
commit, push, open a PR, merge, deploy, synchronize, or promote.
```

The dry run also classifies command-contract drift. A preserved customized
command specification, canonical entry/bootstrap file, or generated command
adapter emits `EXOCORTEX_COMMAND_AUTHORITY_COLLISION_PRESERVED`. Known obsolete
command mechanics in a preserved root instruction file emit
`EXOCORTEX_STALE_COMMAND_GUIDANCE_PRESERVED`. Either condition produces
`EXOCORTEX_COMMAND_RECONCILIATION_REQUIRED`; an ordinary live apply must stop
before capability consumption and use the target-specific reconciliation
workflow.

The root `.cursorrules` file is project-owned. It is safety-checked, included
in disposable-rehearsal and rollback evidence, and retained byte-for-byte by
ordinary installation and update. It is never copied from the template,
deleted, normalized, or added to the install manifest. Known obsolete command
guidance there is reported by path only and requires the same target-specific
reconciliation; only an exact reviewed reconciliation plan can intentionally
replace or retire it.

## Legacy protected-default preflight

Before any existing-repository dry run, confirm these protected prerequisites
with non-following path metadata without reading project-memory content. Every
file prerequisite must be a real regular file, never a symlink:

- `.exocortex/.project-name`;
- `.exocortex/SESSION_CONTEXT.md`, `TODO.md`, `LESSONS.md`,
  `PROJECT_MEMORY.md`, and `OPEN_DECISIONS.md`;
- `.exocortex/control/INTERRUPTS.md`, `BACKLOG.md`, and `ROADMAP.md`;
- `.exocortex/control/EXECUTOR_REGISTRY.json` and
  `EXTERNAL_SYNC_POLICY.json`; and
- `.exocortex/events` and `.exocortex/control` as real directories, never
  symlinks; and
- `.exocortex/local/protocol/{capabilities,transactions,descriptors,payloads,audit}`
  as real directories, never symlinks.

An older installation may lack some of this scaffolding.
`.exocortex/.project-name` is not generic: its exact
project-specific value must be supplied and approved by the owner, and it is
never created or inferred by the updater. Seed it first (for example via
`init-project.sh` with the approved name), or the update fails closed and
prints the missing path with that instruction. Empty scaffolding directories and the exact
reviewed defaults emitted by the pinned candidate's `install.sh`
`ensure_data_stubs` function (including an empty read-only registry and
deny-by-default policy) are the only protected content the update may adopt:
each is content-verified against the reviewed defaults during rehearsal and
verified again after apply, and anything else fails closed. Stop and show the
exact missing-path list and directory types before seeding.
When that value is initialized, the helper uses a private same-directory
temporary file, exact `0644` mode, file fsync, no-replace publication, and
directory fsync. Caught failures remove only the inode created by that
invocation. A crash may leave a private temporary file, but it cannot expose a
partially written final `.project-name`; review any residue before retrying.

### Existing Git-tracked backup sidecars

`.exocortex/SESSION_CONTEXT.md.backup` and the direct legacy family
`.exocortex/SESSION_CONTEXT_BACKUP_*.md` are optional protected project data,
not required legacy defaults. The classification is deliberately narrow; it
does not broadly exempt arbitrary backup files. Git-ignore rules affect only files Git does not
already track. Before a dry run, inspect their tracking metadata without
reading their content:

```bash
git ls-files -- .exocortex/SESSION_CONTEXT.md.backup \
  '.exocortex/SESSION_CONTEXT_BACKUP_*.md'
```

If the command lists either form, that sidecar is already tracked. The updater
emits `EXOCORTEX_TRACKED_PROTECTED_SIDECAR` for the exact sidecar or
`EXOCORTEX_TRACKED_LEGACY_SESSION_CONTEXT_BACKUP` for legacy sidecars,
preserves the files, and never changes Git tracking. Removing an existing
sidecar from the Git index or history is a separate owner-approved cleanup
decision; an installation or update must never
perform it automatically.

Inside the accepted disposable-rehearsal envelope, create only absent paths in
disposable state; never overwrite an existing path or read/copy real memory
into the fixture. Recheck path types with non-following metadata, then start
the dry run. The later named-target local-apply decision may internally repeat
only the same reviewed bootstrap against the exact target.

The AI may run this dry run only after the disposable-rehearsal decision:

```bash
cd <absolute-target-path>
bash <absolute-pinned-template-path>/scripts/safe-update.sh \
  --template <absolute-pinned-template-path> \
  --candidate-digest <approved-sha256-of-SHA256SUMS> \
  --backup-dir <absolute-disposable-backup-root> \
  --dry-run
```

The live target remains unchanged. The owner reviews:

- the complete changed-path list and its digest;
- protected-data before/after hashes;
- adapter collision and managed-retirement results;
- the named-target local-apply envelope proposed next. Executor,
  reservation, and one-time capability details remain available as audit
  evidence but are not separate human decisions.

## Complete disposable update evidence

`safe-update.sh --dry-run` creates one unique private `0600` code-plane-only
restore archive and performs one internal installation rehearsal. The backup
root must be owner-controlled and not group/world writable; writable ancestors
must be sticky. Before any capability can be consumed, the updater verifies
the archive's reserved inode, single-link state, mode, digest, safe contents,
fsync durability, and exact reconstruction of the prior code plane. Protected
project data, local authority state, and editor session worktrees
(`.claude/worktrees` at any depth, which are runtime state outside the update
surface) are excluded from the archive and from every update-evidence digest. The
command does not run the target application's test suite, apply the update,
rerun after apply, or perform a restore. An AI must not claim those results
from the dry-run command alone.

Before proposing a real-target apply, use a newly created disposable snapshot
of the exact repository revision and perform these separately observable steps:

1. Record the baseline code-plane and protected-data hashes.
2. Run `safe-update.sh --dry-run` and preserve its complete changed-path list,
   digest, and restore archive.
3. In separate disposable fault fixtures, exercise the deterministic integrity
   and target-race failures required by
   [the upgrade contract](UPGRADE_MANIFEST.md). Require byte-identical target
   state and the expected fail-closed capability state after each
   pre-consumption rejection.
4. In another disposable snapshot, use a one-time disposable-QA capability and
   a live-only controlled write failure after the capability is consumed and at
   least one apply copy occurs. On a copy of that partially mutated target,
   preserve the protected plane, remove the mutable code plane, restore the
   captured archive, and require added paths to disappear and the baseline path
   types, bytes, modes, and protected-data hash to return. Prove the consumed
   capability remains consumed and cannot be replayed, and record that a fresh
   capability would be required for retry.
5. In a fresh disposable snapshot with a fresh internally derived
   disposable-QA capability under the same rehearsal envelope, run the guarded
   apply command below successfully.
6. Recompute protected-data hashes and run the repository's applicable tests.
7. Run `safe-update.sh --dry-run` again with the same pinned candidate. Require
   a zero-path change set and the SHA-256 of the empty path list.
8. In a second disposable snapshot, exercise the operating-system-specific
   restore procedure using the captured archive. Compare the restored
   code-plane hash with the baseline and require protected data to remain
   unchanged.
9. Confirm that all `.exocortex/local` authority and evidence paths, including
   capabilities and transactions, were excluded from the archive. Restoration
   must not replace or reactivate a consumed, missing, expired, or revoked
   capability.

The AI must show the exact target-specific restore commands and validated
directories before executing them. This guide intentionally provides no broad
recursive deletion command. A platform without a verified restore procedure
cannot pass this evidence gate.

## Internal cooperative authority mechanics

A fresh installation creates a read-only executor registry. After the legacy
protected-default preflight above, an older installation can still have no
public-v2 work item or registered writer. The AI cannot promote itself to
writer. If the exact work item, registered writer, reservation, and apply
capability do not already exist, the real apply remains blocked after dry-run
until the named-target local-apply envelope is accepted. That one business
decision authorizes only the internal bootstrap required for its exact target,
candidate digest, changed paths or reconciliation plan, verification, local
handoff, and writer release.

The changed-path list is not final while the registry is absent. The earlier
missing-default bootstrap creates a deny-by-default read-only registry but
grants no writer. After the first dry run and the named-target decision,
internally create the next registry version with one time-bounded local writer,
read-only and writer roles, no egress role, and the pinned guard digest. Rerun
the dry run after that writer registry exists, and use only the stable
post-registry path list and digest when materializing apply authority.

The human-facing prompt is concise:

```text
Apply the accepted Exocortex candidate locally to <exact-named-target>.
Bind the displayed target/base, candidate digest, exact changed paths or
reviewed reconciliation plan, rollback, tests, and local-only handoff. Handle
the work item, read-only registry upgrade, one writer reservation, one-time
technical capabilities, verification records, handoff, and writer release as
internal fail-closed mechanics. Stop on any target/base/digest/path/plan/risk
change. Do not stage, commit, push, merge, deploy, synchronize, promote, or
touch another repository.
```

After that decision, the coding AI may write only the bounded work item,
executor registry, reserve capability, and transaction state required by the
envelope. It must validate
`.exocortex/schemas/orchestration.schema.json`,
`.exocortex/schemas/executor-registry.schema.json`,
`.exocortex/schemas/authorization.schema.json`,
`.exocortex/scripts/orchestrate_work_item.py`, and
`.exocortex/scripts/authority_guard.py`. It must not create transaction
journals manually. The orchestrator alone creates its atomic transaction
records while performing an accepted operation. The complete non-secret JSON,
path-set digest, guard digest, and expiries remain audit evidence. The AI then
validates the work item:

```bash
python3 <absolute-pinned-template-path>/.exocortex/scripts/orchestrate_work_item.py \
  orient \
  --project-root <absolute-target-path> \
  --work-item .exocortex/work-items/<exact-work-item-id>.json
```

It then acquires the one writer reservation with the approved capability:

```bash
python3 <absolute-pinned-template-path>/.exocortex/scripts/orchestrate_work_item.py \
  reserve \
  --project-root <absolute-target-path> \
  --work-item .exocortex/work-items/<exact-work-item-id>.json \
  --capability <project-relative-reserve-capability-path> \
  --request-id <unique-reserve-request-id> \
  --surface-id <registered-surface-id> \
  --executor-id <registered-executor-id> \
  --adapter-version <registered-adapter-version> \
  --writer <registered-surface-id>/<registered-executor-id> \
  --lease-expires-at <approved-UTC-expiry>
```

After reservation, the AI runs one mandatory post-bootstrap dry run with the
same pinned candidate. Its complete sorted path list and digest must exactly
equal the work item's `lane.allowed_paths` and the accepted pre-bootstrap
evidence. If they differ, do not create the apply capability; stop and ask
once for a replacement named-target local-delivery decision with the changed
scope. Never edit the lane silently.

When the scope remains exact, the AI may internally materialize the current
one-time active capability and immediately present it to the guarded updater.
Schema validation, a successful reservation, stable post-bootstrap dry-run
evidence, and guard preflight remain mandatory. If any bootstrap field or tool
is unavailable, stop after dry-run.

## Guarded apply contract

An existing-repository apply is the second local business decision after the
disposable rehearsal. Before applying, the AI must:

1. confirm the named-target local-delivery envelope still matches;
2. create or identify one public-v2 delivery work item bound to the exact
   target revision, candidate digest, and allowed paths;
3. verify one active registered executor with the `writer` role and no egress
   role;
4. acquire one active writer reservation;
5. derive one current, one-time
   `apply_template_update` capability whose work-item ID/revision, target
   digest, executor identity, adapter version, guard digest, and exact allowed
   paths all match;
6. retain the complete non-secret JSON and changed-path digest as audit
   evidence rather than another approval prompt;
7. materialize the active capability; and
8. immediately present it to the guarded updater for one consumption attempt.

The guarded command is:

```bash
cd <absolute-target-path>
bash <absolute-pinned-template-path>/scripts/safe-update.sh \
  --template <absolute-pinned-template-path> \
  --candidate-digest <approved-sha256-of-SHA256SUMS> \
  --backup-dir <absolute-disposable-backup-root> \
  --apply \
  --capability <project-relative-capability-path> \
  --work-item-id <exact-work-item-id> \
  --work-item-revision <exact-current-revision> \
  --request-id <unique-request-id> \
  --surface-id <registered-surface-id> \
  --executor-id <registered-executor-id> \
  --adapter-version <registered-adapter-version>
```

Missing, expired, revoked, consumed, stale, or mismatched authority fails
closed. A failed attempt does not become approval. After a successful apply,
the AI verifies protected data, runs the applicable repository tests, reruns
the dry run to prove zero remaining changes, records the permitted local
handoff, releases the writer, and stops. Those record mechanics are internal
to the named-target local-delivery envelope.

## Target-specific reconciliation contract

The ordinary update intentionally preserves customized or unknown collisions.
It must not guess how to merge them. If the owner wants the complete candidate
surface after reviewing those collisions, include the exact reviewed
reconciliation plan in the named-target local-delivery envelope. A later plan
or effect-set change requires one replacement decision:

1. retain the accepted ordinary dry-run path list and digest;
2. classify every additional target path as exact candidate adoption,
   reviewed-object replacement, or managed retirement;
3. place each reviewed object only under the target's protected
   `.exocortex/local/update-reconciliation/objects/` directory and bind its
   exact content digest;
4. use `.exocortex/scripts/prepare_update_reconciliation.py prepare` to emit a
   deterministic JSON proposal to standard output;
5. store that proposal only under the envelope's exact protected local
   evidence path;
6. validate the exact plan bytes, candidate digest, target surface, work-item
   ID and revision, standard path list, complete union effect set, and every
   source hash and expected `0644`/`0755` mode;
7. run the complete plan in a disposable rehearsal and independently review
   its exact resulting bytes; and
8. internally derive a distinct current one-time
   `apply_template_reconciliation` capability whose `allowed_paths` is exactly
   the plan's effect paths and whose `scope.payload_digest` is the SHA-256 of
   the exact plan file.

The target-surface digest covers only the mutable template code plane.
Protected project data is excluded from that digest and verified separately
for preservation by the updater. Therefore storing the plan, reviewed objects,
authority records, or evidence under `.exocortex/local/**` does not invalidate
the plan; changing a code-plane collision path still does.

Preparation and validation do not mutate the target. The helper accepts
repeatable `--adopt <path>`, `--retire <path>`, and
`--reviewed <effect-path>=<object-path>` decisions. It rejects protected paths,
symlinks, path traversal, non-regular sources, stale target bytes, candidate
checksum or mode drift, unapproved reviewed-object locations, reviewed-object
mode drift, duplicate JSON keys, duplicate paths, and empty plans. Before the
helper reads target collision bytes, the guarded updater rejects target-surface
symlinks and external hard-linked mutable files.

The guarded apply adds the reviewed absolute plan path to the ordinary
safe-update command:

```bash
cd <absolute-target-path>
bash <absolute-pinned-template-path>/scripts/safe-update.sh \
  --template <absolute-pinned-template-path> \
  --candidate-digest <approved-sha256-of-SHA256SUMS> \
  --backup-dir <absolute-disposable-backup-root> \
  --reconciliation-plan <absolute-reviewed-plan-path> \
  --apply \
  --capability <project-relative-capability-path> \
  --work-item-id <exact-work-item-id> \
  --work-item-revision <exact-current-revision> \
  --request-id <unique-request-id> \
  --surface-id <registered-surface-id> \
  --executor-id <registered-executor-id> \
  --adapter-version <registered-adapter-version>
```

The updater validates the plan before backup or rehearsal, proves the
rehearsal changed exactly the approved effect paths, rechecks the target and
authority immediately before consumption, then materializes only the already
reviewed bytes and bound modes. One final deterministic installer pass inside the same
rehearsal and guarded apply reconciles candidate adoptions with the install
manifest and must remain inside the approved effect set. An `apply_template_update` capability cannot authorize this
operation. A consumed reconciliation capability cannot be replayed; retry
requires a fresh request and capability. Protected memory, events, work items,
control records, local model-routing evidence, application files, and outward
systems remain outside the effect set.

This path is for reviewed target-specific convergence, not automatic conflict
resolution. The standard updater remains the default for collision-free
targets. After materializing the reviewed objects, the final rehearsal
installer pass must emit no command-authority or stale-command-guidance drift;
otherwise reconciliation fails before live mutation.

## WSL evidence required before support

For one exact Windows version, WSL version, distribution, and coding-agent
terminal surface:

1. use a target stored inside the WSL filesystem, not a mounted Windows path;
2. record the Bash, Git, Python, hash-tool, archive-tool, and filesystem
   versions without reading credentials;
3. run the complete deterministic template suite;
4. run clean install twice with fake `HOME`;
5. run the complete disposable existing-update cycle above, including rollback;
6. confirm file modes, path handling, symlink rejection, and no Windows-host
   file or editor-home mutation;
7. complete Human UAT and record the exact environment.

Until all seven pass, WSL remains `human_uat_pending`. Mounted Windows paths,
Git Bash, PowerShell, and Command Prompt remain separate unsupported surfaces.

## GitHub is a later gate

Installation does not authorize Git publication. After accepting the local
result, the owner may make one `publication` decision for the exact reviewed
candidate. That envelope may cover exact-path staging, one local commit, push
to a named branch, and creation of a draft pull request. It does not authorize
merge. Integration/rollout and exact-target production/egress remain later
business decisions.

## Human UAT

The owner should be able to confirm:

1. the AI chose the intended repository and pinned template;
2. it started read-only and stopped at every mutation boundary;
3. no secret value or credential file was read or displayed;
4. clean-install versus update behavior was selected correctly;
5. rehearsal, retry, idempotency, rollback, and protected-data evidence are
   understandable;
6. the installed AI reads `AI_START_HERE.md` and orients correctly;
7. the human was asked only for the disposable rehearsal and named-target
   local apply—not internal work-item, registry, reservation, capability,
   handoff, or writer-release approvals; and
8. no publication, integration/rollout, or production/egress action occurred
   without its matching business decision.

The owner answers Human UAT with a simple accept or reject plus any failed
case. Recording that result and completing local closeout are internal
mechanics of the active local-delivery envelope.
