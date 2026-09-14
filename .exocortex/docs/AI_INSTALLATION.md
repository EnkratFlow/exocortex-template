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

## Local prerequisites

The current installer and updater require Bash 3.2+, Python 3.9+, `shasum`, `awk`,
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
   The AI may recompute and compare it, but it must not choose and approve the
   digest on the owner's behalf.
4. For an existing repository, decide where an external disposable backup and
   rehearsal can be created.

Provider command-menu visibility is not installation authority. The same
read-only preflight and approval boundary applies to every provider.

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
expected to change, the tests that will run, and every action that remains
separately gated. Stop and ask for my exact disposable-rehearsal approval. Do
not install into the real target, commit, push, open a PR, merge, deploy,
synchronize, or promote in the same step.
```

After the AI reports the exact preflight, the owner may approve only the
disposable rehearsal. A bare “yes” is not approval for an isolated-worktree
install, recording write, Git, or outward action. The AI then:

1. inventories only the manifest-defined install surfaces and known collision
   paths. It may hash approved non-secret regular files on those surfaces, but
   must exclude `.env`, credential-bearing content, raw user/project data, and
   every unapproved path. A symlink on an install surface blocks the rehearsal;
2. creates a sanitized disposable fixture containing only the approved
   non-secret install surfaces and known collisions, plus a fake `HOME`;
3. verifies the pinned template SHA and approved `SHA256SUMS` digest;
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
9. requests a separate exact approval to create one clean isolated Git worktree
   from the approved target HEAD, with no untracked credential files;
10. installs and verifies only in that isolated worktree, never directly in a
    shared or primary checkout, then stops; and
11. proposes handoff recording, commit, push, and integration as later separate
    gates.

A clean installation has no updater restore archive and the current installer
writes in place. Its rollback boundary is therefore isolation: a partial
failure is contained by quarantining or discarding the isolated fixture or
worktree and recreating it from the approved clean Git base. Direct installation
into a shared or primary checkout remains unsupported until the installer has a
tested atomic commit or target-specific restore mechanism.

After the separate isolated-worktree approval, the underlying local command on
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
propose the separate missing-default bootstrap; do not create it implicitly.

Plan the updater's built-in dry run with fake HOME and no network. It must hash
protected paths before and after, print the complete sorted changed-path list
and its digest, and leave the live repository untouched. State explicitly that
one --dry-run does not apply the update, run application tests, prove a
post-apply zero-change rerun, or restore the archive. Those are separate
disposable QA steps described below. Stop for my exact dry-run approval. Do not
apply, commit, push, open a PR, merge, deploy, synchronize, or promote.
```

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

An older installation may lack some of this scaffolding. Do not let
`safe-update.sh` create it after apply authority is consumed. Stop and show the
exact missing-path list and directory types. For generic files, show the exact
default bytes emitted by the pinned candidate's reviewed `install.sh`
`ensure_data_stubs` function, including an empty read-only registry and
deny-by-default policy. `.exocortex/.project-name` is not generic: its exact
project-specific value must be supplied and approved by the owner.

Under a separate, exact missing-default bootstrap approval, create only absent
paths in disposable state; never overwrite an existing path or read/copy real
memory into the fixture. Recheck path types with non-following metadata, then
start the dry run. A real repository needs its own later approval for the same
bounded bootstrap.

The AI may run this dry run only after the bounded dry-run approval:

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
- the exact registered executor and one-time apply capability proposed next.

## Complete disposable update evidence

`safe-update.sh --dry-run` creates a restore archive and performs one internal
installation rehearsal. It does not run the target application's test suite,
apply the update, rerun after apply, or perform a restore. An AI must not claim
those results from the dry-run command alone.

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
   a controlled write failure after the capability is consumed and at least one
   apply copy occurs. Restore the snapshot with the captured archive, require
   its code-plane and protected-data hashes to match the baseline, prove the
   consumed capability remains consumed and cannot be replayed, and record that
   a fresh capability would be required for retry.
5. In a fresh disposable snapshot with a fresh separately approved
   disposable-QA capability, run the guarded apply command below successfully.
6. Recompute protected-data hashes and run the repository's applicable tests.
7. Run `safe-update.sh --dry-run` again with the same pinned candidate. Require
   a zero-path change set and the SHA-256 of the empty path list.
8. In a second disposable snapshot, exercise the operating-system-specific
   restore procedure using the captured archive. Compare the restored
   code-plane hash with the baseline and require protected data to remain
   unchanged.
9. Confirm that capability paths were excluded from the archive. Inventory any
   archived transaction records and prove that restoring them cannot reactivate
   a consumed, missing, expired, or revoked capability.

The AI must show the exact target-specific restore commands and validated
directories before executing them. This guide intentionally provides no broad
recursive deletion command. A platform without a verified restore procedure
cannot pass this evidence gate.

## Cooperative authority bootstrap

A fresh installation creates a read-only executor registry. After the legacy
protected-default preflight above, an older installation can still have no
public-v2 work item or registered writer. The AI cannot promote itself to
writer. If the exact work item, registered writer, reservation, and apply
capability do not already exist, the real apply remains blocked after dry-run
until the owner separately approves this cooperative local bootstrap.

The changed-path list is not final while the registry is absent. The earlier
missing-default bootstrap creates a deny-by-default read-only registry but
grants no writer. After the first dry run, propose the next registry version
with one time-bounded local writer, read-only and writer roles, no egress role,
and the pinned guard digest. Rerun the dry run after that writer registry
exists, and use only the stable post-registry path list and digest when
materializing apply authority.

Copy-paste bootstrap-planning prompt:

```text
Prepare a read-only cooperative Exocortex update-authority bootstrap.

Use the accepted dry-run changed-path list and digest. Read
.exocortex/schemas/orchestration.schema.json,
.exocortex/schemas/executor-registry.schema.json,
.exocortex/schemas/authorization.schema.json,
.exocortex/scripts/orchestrate_work_item.py, and
.exocortex/scripts/authority_guard.py from the pinned candidate.

Propose, but do not write:
1. one ready public-v2 delivery work item whose designated base is the approved
   candidate digest and whose lane.allowed_paths exactly equals the accepted
   changed-path list;
2. the next executor-registry version with exactly one time-bounded local
   writer using read_only and writer roles only, no egress role, and the guard
   digest printed by authority_guard.py guard-digest;
3. one one-time reserve_writer capability bound to work-item revision 0, only
   the work-item record path, and `scope.target_sha` exactly equal to the
   approved candidate digest used by the work item's `designated_base.sha`;
4. the exact reserve command, request ID, writer ID, and lease expiry;
5. a field checklist for the later `apply_template_update` proposal: the
   post-reservation revision, exact changed paths, candidate digest, executor
   identity, registry version, guard digest, expiry, and revocation state. Do
   not assign an acceptance time, materialize an active apply capability, or
   create its file during bootstrap.

Show the complete non-secret JSON, exact file paths, sorted path-set digest,
and every expiry. Explain that this is cooperative local enforcement, not a
privileged cryptographic broker. Stop for my exact bootstrap approval. Do not
write records, reserve a lane, apply, record a handoff, use Git, or act outward.
```

After exact bootstrap approval, the coding AI may write only the approved work
item, executor registry, and reserve capability. It must not create transaction
journals manually or materialize the apply capability. The orchestrator alone
creates its atomic transaction records while performing an accepted operation.
The AI then validates the work item:

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

After reservation, the AI shows the complete proposed apply-capability JSON in
chat without writing it. The capability must bind the resulting current
revision. Before showing it, the AI must run one mandatory post-bootstrap dry
run with the same pinned candidate. Its complete sorted path list and digest
must exactly equal the work item's `lane.allowed_paths` and the accepted
pre-bootstrap evidence. If they differ, do not create the apply capability;
stop and propose a separately approved replacement work item or scoped
reconciliation, then rerun until the path set is stable. Never edit the lane
silently.

Only after the owner gives exact apply approval may the AI materialize that
current one-time active capability and immediately present it to the guarded
updater. Schema validation, a successful reservation, stable post-bootstrap
dry-run evidence, and guard preflight are evidence only; none replaces the
owner's exact apply approval. If any bootstrap field or tool is unavailable,
stop after dry-run.

## Guarded apply contract

An existing-repository apply is a different gate from the dry run. Before
applying, the AI must:

1. create or identify one public-v2 delivery work item bound to the exact
   target revision, candidate digest, and allowed paths;
2. verify one active registered executor with the `writer` role and no egress
   role;
3. acquire one active writer reservation;
4. propose, but do not write, one current, one-time
   `apply_template_update` capability whose work-item ID/revision, target
   digest, executor identity, adapter version, guard digest, and exact allowed
   paths all match;
5. show the complete non-secret proposed JSON and accepted changed-path digest
   to the owner;
6. receive a new exact apply approval;
7. only then materialize the approved active capability; and
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
the dry run to prove zero remaining changes, and stops. Releasing the writer
and creating a local handoff are separately approved record mutations.

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
result, the owner may separately ask the AI to prepare an exact-path local
commit. Push and pull-request creation require another explicit approval.
Merge, release, deployment, external synchronization, and template promotion
remain separately gated.

## Human UAT

The owner should be able to confirm:

1. the AI chose the intended repository and pinned template;
2. it started read-only and stopped at every mutation boundary;
3. no secret value or credential file was read or displayed;
4. clean-install versus update behavior was selected correctly;
5. rehearsal, retry, idempotency, rollback, and protected-data evidence are
   understandable;
6. the installed AI reads `AI_START_HERE.md` and orients correctly;
7. no Git or outward action occurred without its own approval.
