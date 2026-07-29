# Exocortex Upgrade Manifest — Public-v2

## Plane classification

### Code plane: template-managed

Generic entry adapters, command specifications, schemas, guards, installer and
updater code, documentation, and deterministic tests may flow from the public
template to projects. Manifest updates apply only when the installed hash still
matches the prior template hash.

The adapter code plane includes `.agents/skills`, `.claude/skills`, and
`.cursor/skills`. Their 72 command-adapter files are generated from the 24 canonical JSON
commands and validated before any install target mutation.

The public model-routing code plane includes the source registry, reviewed
routing catalog, schemas, validator, and provider-neutral routing policy.
Those files contain normalized public facts and protocol logic only. They do
not contain availability for a user's account, raw source responses,
credentials, or provider-session state. A future reviewed catalog admission
may contain only the aggregate evaluation status, counts, cost total,
freshness window, and evidence digest needed for deterministic routing. Raw
prompts, outputs, project context, and detailed evaluation records remain
protected project data.

The packaged 3.2.0 catalog is advisory: all entries are candidates, with zero eligible models
and zero verified evaluation profiles.

### Data plane: protected project truth

Never copy from the template, overwrite, delete, or manifest-track:

```text
SESSION_CONTEXT.md
SESSION_CONTEXT.local.md
TODO.md
LESSONS.md
PROJECT_MEMORY.md
OPEN_DECISIONS.md
subconscious_patterns.md
.env
.project-name
.install-manifest
events/**
archive/**
hub/**
local/**
planning/**
work-items/**
control/ACTIVE_WORK.md
control/BRANCH_POLICY.md
control/REPO_STATE.md
control/EXECUTOR_REGISTRY.json
control/EXTERNAL_SYNC_POLICY.json
control/INTERRUPTS.md
control/BACKLOG.md
control/ROADMAP.md
control/ARCH_OVERVIEW.md
control/REPO_ORGANIZATION_REPORT.md
.hub_enabled
.hub_disabled
```

The `local/**` protection includes
`.exocortex/local/model-routing/**` observations, availability, evaluations,
and quarantine evidence, plus
`.exocortex/local/update-reconciliation/**` reviewed objects and plans.
Installation and ordinary update never create, copy, checksum, infer, or
overwrite those paths.

Under a separate exact missing-default bootstrap, only these absent protected
defaults may be created:

- the exact generic file bytes emitted by the pinned candidate's reviewed
  `install.sh` `ensure_data_stubs` function for `SESSION_CONTEXT.md`, `TODO.md`,
  `LESSONS.md`, `PROJECT_MEMORY.md`, `OPEN_DECISIONS.md`,
  `control/INTERRUPTS.md`, `control/BACKLOG.md`, `control/ROADMAP.md`, an empty
  read-only `control/EXECUTOR_REGISTRY.json`, and deny-all
  `control/EXTERNAL_SYNC_POLICY.json`;
- real, non-symlink directories at `events`, `control`, and
  `local/protocol/{capabilities,transactions,descriptors,payloads,audit}`; and
- `.project-name` with one exact project-specific value supplied and approved
  by the owner, never inferred as generic content.

Every file must be a real regular file checked with non-following metadata.
Existing paths are never overwritten. All of these remain data-plane paths and
the bootstrap grants no writer, apply, Git, or outward authority.

### External plane: explicit immutable payload

There is no automatic hub or upward summary plane. External sync is a separate
operation over one content-addressed local payload descriptor and one exact
destination/method approval. Project memory never flows sideways.

## Update rules

1. Pin the exact template source, preserve the separately approved SHA-256 of
   `SHA256SUMS`, and verify that candidate digest, all complete checksums, and
   the checksum-bound `FILEMODES` inventory before target mutation.
2. Reject malformed, duplicate, missing, extra in-scope, traversal, or
   mismatched checksum entries. `FILEMODES` must bind exactly the sorted
   checksum path set plus `SHA256SUMS` itself, permit only normalized `0644`
   and `0755`, and match every source file before installation or update
   rehearsal.
3. Validate the provider matrix and exact 24-command/72-adapter generated set.
4. Require an owner-controlled, non-group/world-writable disposable backup
   directory with no non-sticky writable ancestor. Create a collision-resistant
   `0600` restore archive there without reopening a substitutable path. Verify
   its inode, single-link state, mode, digest, safe member types, exact
   code-plane reconstruction, file fsync, and directory fsync before capability
   consumption. Archive only the code plane; exclude protected project data
   and local authority state that the updater does not mutate.
5. Before dry run, verify the required legacy protected defaults by path
   metadata. Bootstrap only missing generic scaffolding under a separate exact
   approval; never overwrite existing project data or let apply create defaults
   after capability consumption. Project-name initialization must use a
   private same-directory file, exact mode, file fsync, no-replace publication,
   and directory fsync so caught failures leave no partial final file.
6. Rehearse in a newly created disposable copy with fake `HOME` and no network.
7. Hash the complete protected data plane before and after rehearsal.
8. Emit the SHA-256, count, and complete sorted changed-path list. The digest
   covers UTF-8 relative paths in bytewise sorted order, each terminated by LF;
   an empty change set hashes the empty byte string.
9. Preserve user-modified and unknown files; never silently adopt them into the
   manifest. Preserve reviewed source executable bits whenever a fresh or
   manifest-owned file is actually written. A byte-identical existing file is not
   normalized solely for mode, because the previous install manifest records
   bytes rather than permission provenance. Do not create unreported mode-only mutations
   with blanket permission changes. Retire a legacy adapter only when its
   manifest hash and reviewed legacy text mode `0644` both still match.
10. If reviewed target-specific convergence is required, prepare a
    deterministic reconciliation plan whose candidate, target surface,
    ordinary dry-run path set, exact final bytes, expected `0644`/`0755` mode,
    and complete effect paths are digest-bound. Candidate modes come only from
    `FILEMODES`; reviewed-object modes are captured and rechecked explicitly.
    The target-surface digest includes code-plane file modes but excludes protected project data,
    which the updater verifies separately, so protected local plan and
    authority records cannot self-invalidate the code-plane plan. Rehearse it
    in disposable state and require the distinct one-time
    `apply_template_reconciliation` capability; never reuse ordinary
    `apply_template_update` authority. Duplicate top-level or nested plan keys
    fail before backup, rehearsal, or capability consumption.
11. Require a separate exact approval before applying to the real target.
12. Run twice to prove idempotency. Inject a live-only failure after capability
   consumption and at least one target copy. On a disposable copy of that
   partially mutated target, remove the mutable code plane while preserving the
   protected plane, restore the exact archive, and prove that post-fault
   additions disappear, prior path types/bytes/modes return, protected data is
   unchanged, and consumed authority remains consumed. After a successful
   apply attempt, compare the complete non-protected code-plane path types,
   presence, bytes, and modes against the rehearsal.
13. Update one target at a time. Batch `--yes` behavior is not part of the
   public-v2 authority model.
14. Promote only scrubbed code-plane changes from an approved clean base; scan
    the promoted tree and newly reachable history for private evidence.

The provider-neutral operator prompt, complete dry-run and guarded-apply
commands, required authority fields, GitHub boundary, and Human UAT are in
`.exocortex/docs/AI_INSTALLATION.md`.

## Provider-adapter migration

The canonical command JSON files are never retired by the adapter migration.
The matrix records two cumulative groups:

- 26 prior Cursor/GitHub paths: 24 old Cursor command wrappers plus duplicate
  Cursor and GitHub `onboard` entries, all with canonical portable replacements; and
- 25 retired Windsurf paths: 24 workflows plus `.windsurfrules`.

For replacement-backed paths, the replacement must first be present and
canonical. For either group, the installer removes a path only when it is
recorded in the prior install manifest and its current bytes still match the
recorded hash and its mode is the reviewed legacy text mode `0644`. Windsurf
remains in safe-update inventory and restore archives so managed deletions are
visible, authorized, and recoverable even though it is not part of
fresh/default installation.

If the replacement or legacy path has customized bytes or mode, is unknown,
missing, or
noncanonical, preserve the old path and emit
`EXOCORTEX_ADAPTER_COLLISION_PRESERVED`. Do not advertise the target as having
collision-free provider parity until that target-specific finding is resolved.

`.cursor/skills/onboard/SKILL.md` is the sole reactivated path. A
manifest-owned, byte-matching legacy copy is retired before the current Cursor
adapter is copied. Customized or unknown content is preserved, and the current
adapter does not overwrite it. The resulting manifest must contain at most one
record per path.

## Restore portability

Use the verified native restore procedure for the target operating system. On
macOS, disable copyfile metadata when extracting the archive so AppleDouble
sidecars are not materialized. A generic archive reader is not equivalent to a
verified rollback.

Current evidence supports macOS. Linux must pass the final candidate's Ubuntu
CI before promotion. WSL remains Human-UAT-pending. Git Bash and native Windows
PowerShell/Command Prompt are unsupported because their archive, hash, path,
permission, and rollback behavior has not been verified. Do not infer native
Windows support from provider availability.
