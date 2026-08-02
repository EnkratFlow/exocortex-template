# Exocortex

Exocortex is a project-local memory, delivery, and multi-AI entry protocol for
software repositories. The repository owns its history and gates; AI providers
are interchangeable workers.

This template is public beta. Read `VERSION` for the packaged version.

## Install in 60 seconds

Works on macOS and Linux today; on Windows, run everything inside WSL.

**With a coding AI** (Cursor, Claude, Copilot, or any agent with local
filesystem and terminal access): open the repository you want Exocortex
installed into and paste this prompt:

> Install Exocortex into this repository. Clone
> `https://github.com/EnkratFlow/exocortex-template` at the exact `v3.2.4`
> release tag into a sibling directory. Confirm the clone's HEAD equals the
> peeled commit SHA published in that release's notes. Compute the SHA-256 of the clone's
> `SHA256SUMS` file and confirm it equals the candidate digest published in
> that release's notes; stop if it does not match. Then, from this
> repository's root, run
> `EXOCORTEX_LOCAL_SOURCE=<clone path> EXOCORTEX_CANDIDATE_DIGEST=<digest> bash <clone path>/install.sh <project-name>`
> and show me the full result. Do not commit, push, publish, or configure
> anything beyond that.

**By hand**, run these commands from the repository you are installing into:

```bash
git clone --depth 1 --branch v3.2.4 https://github.com/EnkratFlow/exocortex-template.git ../exocortex-template-v3.2.4
git -C ../exocortex-template-v3.2.4 rev-parse HEAD # compare with the peeled commit in the release notes
shasum -a 256 ../exocortex-template-v3.2.4/SHA256SUMS # compare with the digest in the release notes
EXOCORTEX_LOCAL_SOURCE=../exocortex-template-v3.2.4 EXOCORTEX_CANDIDATE_DIGEST=<digest from release notes> bash ../exocortex-template-v3.2.4/install.sh my-project
```

**Already running an older Exocortex?** Use the rehearsed updater instead of
reinstalling: run `scripts/safe-update.sh --dry-run` with the same template
path and digest to see the exact change list first, then follow the guarded
update flow in
[`.exocortex/docs/AI_INSTALLATION.md`](.exocortex/docs/AI_INSTALLATION.md).
Your project data, customized files, and anything you have added to the
repository are preserved; a verified rollback archive is created before any
byte changes.

## Core model

- `AI_START_HERE.md` is the canonical provider-neutral entry point.
- `.exocortex/AI_BOOTSTRAP.md` discovers the 24 command specifications.
- `.exocortex/control/MODEL_ROUTING.md` selects by capability, risk,
  exact current-session availability, a route timestamp within 60 seconds of
  current UTC, and measured cost per successful completion—not latency claims
  or permanent model names.
- `.exocortex/control/DELIVERY_WORKFLOW.md` applies minutes-long Kanban/SDLC
  gates from requirements through hypercare.
- `.exocortex/scripts/authority_guard.py` and
  `.exocortex/scripts/orchestrate_work_item.py` enforce registered one-writer,
  one-time scoped mutation capabilities for public-v2 runtime work items.
- `.exocortex/scripts/egress_guard.py` separates local immutable payload staging
  from destination-specific outward authorization.

Unknown or unregistered AI surfaces are read-only. A save is local narrative
memory, not a lifecycle checkpoint. A handoff transfers evidence, not
authority. Human-facing decisions use four business-level envelopes:
`local_delivery`, `publication`, `integration_rollout`, and exact-target
`production_egress`. Internal reservations, capabilities, evidence records,
handoffs, and writer release are not separate human approvals.

## Install with a coding AI

You do not have to type the installation commands yourself. Open the intended
repository in a coding AI that has local filesystem and terminal access, then
paste the clean-install or existing-update prompt from
[`.exocortex/docs/AI_INSTALLATION.md`](.exocortex/docs/AI_INSTALLATION.md).

The provider-neutral prompt works by contract, not by provider identity. The AI
must start read-only, identify the exact target, pin and verify the template,
rehearse in disposable state, and show the complete scope. Installation uses
two understandable local decisions: disposable rehearsal, then one
named-target local apply. The second decision contains isolated-worktree
setup, internal authority mechanics, installation/update, verification, local
handoff, and writer release. It never bundles publication, merge,
deployment, synchronization, or promotion.

Chat-only assistants and provider menus without local repository and terminal
access can explain the process but cannot perform it.

Current platform truth:

| Environment | Status |
|---|---|
| macOS with the documented Bash/Unix tools | `verified` |
| Linux | `compatible_pending_candidate_CI` |
| Windows through WSL | `human_uat_pending` |
| Git Bash or native Windows PowerShell/Command Prompt | `unsupported` |

Do not advertise native Windows support. WSL must pass the same bounded
rehearsal before its status changes. See the AI installation guide for the
copy-paste prompts, guarded update command, GitHub boundary, and Human UAT.

## Safe installation

Do not pipe an unpinned remote installer into a shell. Clone or otherwise
obtain an exact reviewed template revision and verify `SHA256SUMS`. Rehearse in
a sanitized disposable fixture first. After that evidence is accepted, a
named-target local-delivery decision may create one clean isolated Git worktree
from the exact approved target HEAD, run the installer, verify it,
record the permitted local handoff, and release the writer. Preserve the
SHA-256 of the reviewed `SHA256SUMS` as the accepted candidate digest; do not
derive it from an unreviewed source at install time:

`FILEMODES` is checksum-bound and records the only accepted source modes:
`0644` or `0755` for every checksum-listed path. A byte-valid candidate with a
changed executable bit fails before target mutation.

```bash
git clone https://github.com/EnkratFlow/exocortex-template.git /tmp/exocortex-template
git -C /tmp/exocortex-template checkout <approved-exact-sha>
git -C /path/to/project worktree add --detach \
  /path/to/approved-isolated-worktree <approved-target-head>
cd /path/to/approved-isolated-worktree
HOME=<absolute-disposable-home> \
EXOCORTEX_LOCAL_SOURCE=/tmp/exocortex-template \
EXOCORTEX_CANDIDATE_DIGEST=<approved-sha256-of-SHA256SUMS> \
  bash /tmp/exocortex-template/install.sh "project-name"
```

Worktree creation, installation, verification, local handoff, and writer
release are internal steps inside that one local-delivery envelope. Exact
technical capabilities still fail closed on any target, base, digest,
path/plan, operation, risk, or expiry mismatch. The installer must run
non-interactively with a fake `HOME`. Direct installation into a shared or primary checkout is unsupported because the current clean installer writes in
place and has no restore archive. Project installation never grants global
editor-home, launchd, provider, credential, hub, deployment, Git publication,
or external-sync authority.

New installs generate project-local defaults when absent:

- `.exocortex/control/EXECUTOR_REGISTRY.json`: no registered writers or egress
  executors; default role read-only.
- `.exocortex/control/EXTERNAL_SYNC_POLICY.json`: deny by default; no
  destinations.

These files are protected data, not template payload or manifest content.

## Safe update path

Use a pinned local template and the safe updater. Rehearse only in a newly
created disposable copy, hash every protected path, and keep the restore
archive outside the target:

To test the same public path as any other user, acquire only the exact GitHub
release and verify both values published in its release notes before reading
the update instructions from that clone:

```bash
git clone --depth 1 --branch v3.2.4 \
  https://github.com/EnkratFlow/exocortex-template.git \
  /tmp/exocortex-template-v3.2.4
git -C /tmp/exocortex-template-v3.2.4 rev-parse HEAD
shasum -a 256 /tmp/exocortex-template-v3.2.4/SHA256SUMS
```

The first output must equal the release's peeled commit SHA and the second
must equal its published candidate digest. Do not substitute `main`, `latest`,
or a different checkout.

Older installations must first pass the metadata-only protected-default
preflight in `.exocortex/docs/AI_INSTALLATION.md`. Missing generic scaffolding
uses an internal guarded bootstrap under the accepted named-target local
apply; the updater must not create it after consuming apply authority.

```bash
cd /path/to/existing-project
bash /tmp/exocortex-template-v3.2.4/scripts/safe-update.sh \
  --template /tmp/exocortex-template-v3.2.4 \
  --candidate-digest <approved-sha256-of-SHA256SUMS> \
  --backup-dir /tmp/exocortex-restore \
  --dry-run
```

Apply to a real repository only after the rehearsal evidence is accepted and
one exact named-target local-delivery decision is approved. Re-run with the
same pinned template and candidate digest, `--apply`, the exact internally
derived one-time capability, and the registered executor identity. The
updater has no interactive or implicit approval prompt.

The updater protects the full project data plane, including:

- memory, TODO, lessons, decisions, generated session context, and `.env`;
- events, archive, hub, local protocol state, planning, and work items;
- interrupt/backlog/roadmap and live control records;
- executor registry, external-sync policy, hub markers, and custom untracked
  extensions.

The optional `.exocortex/SESSION_CONTEXT.md.backup` and the direct legacy
family `.exocortex/SESSION_CONTEXT_BACKUP_*.md` are protected too. This is
deliberately narrow: it does not broadly exempt arbitrary backup files. If an
older project already tracks either sidecar form in Git, the updater reports
that fact and preserves the files. For a tracked sidecar, Git-ignore rules cannot untrack it.
Any Git cleanup is a separate owner decision and is never part of an Exocortex update.

User-modified manifest files are preserved. Missing, malformed, incomplete, or
mismatched checksums and any candidate-source symlink fail before target
mutation. Target symlinks and external hard-linked mutable files also fail
before backup. Dry-run leaves the target unchanged and writes one
collision-resistant `0600` code-plane-only restore archive beneath an
owner-controlled, non-group/world-writable backup directory. The archive is
streamed to its reserved inode, fsynced, integrity-checked, reconstructed, and
compared with the exact prior code plane before durable publication or any
capability consumption. Private staging remains beneath `${TMPDIR:-/tmp}` (or
the platform's equivalent system temporary directory). Protected project data
and local authority state are excluded from the archive because the updater
never mutates them. Treat both locations as disposable evidence storage and
verify their permissions.

Every dry run prints the SHA-256, count, and complete sorted list of changed
paths. The digest covers the full UTF-8 path list with one LF after every path,
including the last. It is evidence for review, not approval by itself.

Provider adapters are validated against the canonical command registry before
target mutation. During an update, a superseded legacy wrapper is removed only
when its current bytes still match its prior install-manifest hash, its mode is
the reviewed legacy text mode `0644`, and its canonical replacement installed
successfully. Customized bytes or modes and unknown wrappers are preserved
with an `EXOCORTEX_ADAPTER_COLLISION_PRESERVED` warning.

Customized command-authority files and generated command adapters are
preserved with `EXOCORTEX_COMMAND_AUTHORITY_COLLISION_PRESERVED`. A preserved
project instruction file containing known obsolete command mechanics produces
`EXOCORTEX_STALE_COMMAND_GUIDANCE_PRESERVED`. Either finding makes the dry run
report `EXOCORTEX_COMMAND_RECONCILIATION_REQUIRED` and blocks an ordinary live
apply before capability consumption. Use the reviewed target-specific
reconciliation path below; a version marker alone never proves those command
surfaces converged.

Target-specific collisions are not silently resolved by the ordinary updater.
After its dry run, use the separately reviewed reconciliation workflow in
`.exocortex/docs/AI_INSTALLATION.md`. A deterministic reconciliation plan
binds the candidate digest, target surface, prior dry-run path set, exact final
bytes, and complete effect-path set. Applying it requires the distinct
one-time `apply_template_reconciliation` capability; ordinary
`apply_template_update` authority cannot be reused. The same plan is rehearsed
before capability consumption, and protected project data remains outside its
effect set. After apply, the complete non-protected code plane—path type,
presence, bytes, and mode—must exactly match the disposable rehearsal.

Broad legacy and batch updaters fail closed. Update projects one at a time with
fresh evidence; “all” never grants batch authority.

The complete AI-operated dry-run and guarded-apply sequence, including every
required executor and capability argument, is documented in
`.exocortex/docs/AI_INSTALLATION.md`.

## Three planes

| Plane | Direction | Contents |
|---|---|---|
| Code | Template to project | generic commands, adapters, guards, docs, tests |
| Data | Project-local only | memory, events, work items, control state, registry, policy, protocol transactions |
| External | Explicitly staged and approved | one immutable payload to one exact destination/method |

Code can flow down after promotion. Project memory never flows sideways.
Nothing flows out automatically.

## Multi-AI orchestration

The parent model owns integration and gate decisions. It selects the least
expensive available model capable of the complete task and risk, then delegates
bounded evidence work to cheaper capable models. One registered guarded writer
holds the mutation lane; parallel workers are read-only unless separately
approved. Deterministic tools precede model work. Routing changes and estimates
are reported to the owner.

No vendor or named model is required. A stronger model is used when the work's
capability or risk requires it, not as a permanent starting rule.

### Source-backed model freshness

The packaged source registry covers only configured official public sources.
It does not promise knowledge of every model worldwide. Refreshing those
sources is an explicit external read with no credentials; the local registry
tool never fetches, authenticates, or writes.

Discovery compares the catalog-bound baseline registry with a separately
normalized refreshed snapshot. Stable source definitions must match exactly,
while retrieval timestamps and content digests may advance. Model, lifecycle,
and pricing facts are accepted only from sources registered for those roles;
cross-file duplicates or conflicting facts fail closed.

Newly observed models are quarantined for review. They do not become routing
choices merely because they are newer or advertise a lower price. Routing
requires a current local availability observation and fresh, digest-bound,
measured capability and cost-per-success evidence. Stale or mismatched
evidence fails closed, and missing observations never silently deprecate a
model. Production routing also rejects a caller timestamp more than 60 seconds
behind or ahead of the runtime UTC clock; deterministic historical validation
is a separate non-routing operation.

The packaged 3.2.0 catalog is advisory and has zero route-eligible models or
verified evaluation profiles. It cannot select a model as shipped. A model
becomes eligible only through a separately reviewed guarded catalog update
that binds measured evaluation evidence, followed by fresh availability
evidence for the exact current surface.

See [the routing policy](.exocortex/control/MODEL_ROUTING.md) for the evidence
planes, discovery command, admission rules, and deterministic selection
contract. Project-local observations and availability live under
`.exocortex/local/model-routing/**`; installation and update never create,
copy, checksum, or overwrite them.

## Agile delivery and recursive improvement

Work is sliced into small Kanban items with requirements, acceptance criteria,
implementation, developer verification, risk-based independent review, QA/SIT,
Human UAT, release, deployment, and hypercare evidence as applicable.

Retrospectives generate prospective improvement proposals only. They cannot
self-authorize implementation or modify the protocol that grants their own
authority. Recursive improvement therefore compounds safely:

1. execute a bounded item;
2. collect deterministic and human evidence;
3. record a local retrospective proposal;
4. approve one bounded local-delivery outcome;
5. verify, rehearse, and promote separately.

## Commands

- Daily: `/work`, `/scrum`, `/save`, `/daily-end`, `/interrupt`, `/brief`
- Memory: `/shortterm`, `/longterm`, `/subconscious`, `/drill`, `/history`
- Planning: `/groom`, `/refine-backlog`, `/prioritize`, `/weekly-review`,
  `/monthly-review`, `/pattern-review`
- System: `/onboard`, `/system-scan`, `/ai-export`, `/ecosystem`,
  `/init-exocortex`, `/check-keys`, `/handoff`

The 24 JSON specifications are retained as the single behavior source; the
commands are not being removed. The deterministic adapter generator produces
72 thin repository adapters from them: 24 portable Agent Skills, 24 Claude
skills, and 24 Cursor skills.

Current evidence is version- and surface-scoped. `verified` means the recorded
client displayed every Exocortex entry during bounded Human UAT; it does not
mean a command was executed or that mutation authority was granted.

| Surface | Repository adapter | Native invocation | Recorded evidence |
|---|---|---|---|
| Codex | `.agents/skills/{command}/SKILL.md` | `$command` or the skills selector | `compatible`; repository catalog resolves 24/24, but desktop selector UAT remains pending |
| Claude Desktop 1.24012.1 (0adcae) | `.claude/skills/{command}/SKILL.md` | `/command` | `verified`; all 24 Exocortex commands appeared exactly once |
| Cursor Stable 3.12.30 | `.cursor/skills/{command}/SKILL.md` | `/command` | `verified`; all 24 Exocortex commands appeared exactly once among 72 unique skills |
| GitHub Copilot | `.agents/skills/{command}/SKILL.md` | `/command` where repository skills are supported | `compatible`; 24/24 was observed, but the exact client version was not captured |
| Kimi Code CLI 1.14.0 | `.agents/skills/{command}/SKILL.md` | `/skill:{name}` | `verified`; all 24 Exocortex entries appeared exactly once among 26 unique skills |
| Kimi Desktop Work 3.1.3 | No Desktop-specific adapter claim | Not advertised | `failed`; 0/24 appeared and exact `/skill:ai-export` produced no match |
| Zed 1.12.0 stable.328 built-in Agent | `.agents/skills/{command}/SKILL.md` | Built-in Agent skills selector | `verified`; all 24 Exocortex skills appeared exactly once among 25 unique skills; ACP agents excluded |
| Windsurf | None in active/default installation | Not advertised | `unavailable`; no installed version was available for Human UAT |
| Generic or unidentified host | `AI_START_HERE.md` plus the matching JSON | Host-dependent | No native-menu claim |

Kimi Desktop Work and Kimi Code CLI are different discovery surfaces. The
Desktop 0/24 result does not invalidate the verified CLI result.

Run `python3 .exocortex/scripts/generate_command_adapters.py --check` to prove
repository parity. File generation does not certify provider-menu visibility.
Any provider version, adapter-family, discovery, or configuration change
requires new bounded Human UAT before its evidence is reused. Evidence uses only
`verified`, `compatible`, `failed`, `blocked`, or `unavailable`; see
`.exocortex/docs/IDE_INTEGRATION_GUIDE.md` for the current matrix and limits.

Provider-assisted memory and key validation are unavailable by default. The
active conversation model can summarize local evidence without keys or network
access. Any external provider call uses the same immutable egress protocol.

## Verification

Run deterministic local tests from the template checkout:

```bash
bash tests/run_tests.sh
bash .exocortex/scripts/tests/test_orchestration_protocol.sh
bash .exocortex/scripts/tests/test_event_tooling.sh
bash tests/phase-b/run.sh
python3 .exocortex/scripts/generate_command_adapters.py --check
```

The Phase B harness uses only newly created disposable targets, fake `HOME`,
fake transports, and deny-network shims. It emits hashes and machine-readable
evidence. No test requires real credentials, providers, repositories, or
deployment access.

## Limits

The guards enforce cooperative project-local entrypoints. They do not turn an
unrestricted editor or operating-system account into a security sandbox.
Host-level prevention of bypass, network access, or binary replacement requires
an OS sandbox or privileged broker and a trusted signing/attestation root.
The current local JSON approval records are not cryptographic proof of a human
decision against a process that can rewrite both the registry and capability;
that external trust-root risk remains open until such a broker is integrated.

## License

MIT. See `LICENSE`.
