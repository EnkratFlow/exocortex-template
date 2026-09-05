# Exocortex

Exocortex is a project-local memory, delivery, and multi-AI entry protocol for
software repositories. The repository owns its history and gates; AI providers
are interchangeable workers.

This template is public beta. Read `VERSION` for the packaged version.

> **Public releases are authenticity-gated.** Version 3.3.0 selects GitHub's
> immutable-release attestation for the trust identity
> `github.com/EnkratFlow/exocortex-template`. Before executing downloaded code,
> require `gh release verify v3.3.0 -R github.com/EnkratFlow/exocortex-template`
> to pass and
> verify the downloaded `SHA256SUMS` release asset with
> `gh release verify-asset`. Stop if the release is not immutable, either
> verification fails, or the attested asset differs from the exact tag.

If an immutable release is suspected or confirmed to be compromised, treat it
as revoked and stop using it. The repository owner must remove the compromised
release, permanently retire that tag name, and publish a corrected higher patch
version. Never reuse the compromised version or tag.

## Choose your path

| Your repository | Use |
|---|---|
| Exocortex is not installed | **New installation** |
| Any older Exocortex version is installed | **Existing-repository update** |

The recommended path is a coding AI with local filesystem and terminal access.
The CLI fallback is documented below. A chat-only assistant can explain the
process but cannot install or update local files.

## Install or update with a coding AI

Open the repository you want to change in Codex, Claude, Cursor, Copilot, Zed,
or another coding AI with local terminal access. Copy and paste the matching
prompt. The AI must complete the immutable-release and attested-manifest checks
before it executes any candidate-owned script.

### New installation prompt

```text
Prepare a read-only Exocortex clean-install preflight for the repository I
currently have open. Use only the official GitHub release v3.3.0 from
https://github.com/EnkratFlow/exocortex-template.

Require GitHub CLI verification of the immutable release for the exact trust
identity github.com/EnkratFlow/exocortex-template. Download the release's
SHA256SUMS asset and verify it with the release attestation. Clone that exact
tag as a temporary source, require its SHA256SUMS to be byte-for-byte identical
to the attested asset, verify its HEAD against the peeled commit SHA in the
release notes, and verify the SHA-256 of SHA256SUMS against the published
digest. Stop without executing candidate code if any evidence is absent or
differs. Immediately before the first candidate-owned script runs, repeat the
live release verification, downloaded-asset verification, and byte comparison;
do not rely on an earlier preflight. Use the SHA-256 computed from the verified
asset as the candidate digest; release-note text is only a cross-check.

Show me the exact target, current Git state, expected installation paths,
collisions, disposable rehearsal, verification, rollback boundary, and total
time estimate before changing anything. Never read or display .env or
credential values. Ask me once for the complete local installation. If I
approve it, rehearse first and continue to the named-target installation only
when the target, release, scope, risk, and expected result still match the
approved plan. Stop on any mismatch. Do not change application code, global
editor settings, Git history, remotes, services, providers, deployments, or
external systems.
```

### Existing-repository update prompt

```text
Prepare a read-only Exocortex safe-update preflight for the repository I
currently have open. Update it from its installed version to the official
GitHub release v3.3.0 from
https://github.com/EnkratFlow/exocortex-template.

This existing repository and its project-local data are the target. Do not
treat a fresh template clone or a bare Git snapshot that omits local data as a
replacement. A temporary clone of v3.3.0 is the update source only. An approved
disposable rehearsal or isolated worktree is allowed, but it must preserve and
verify the target's protected data. Require GitHub CLI verification of the
immutable release for the exact trust identity
github.com/EnkratFlow/exocortex-template. Download and attest-verify the
release's SHA256SUMS asset, require the release clone's SHA256SUMS to be
byte-for-byte identical, verify the clone HEAD against the peeled commit SHA in
the release notes, and verify the SHA-256 of SHA256SUMS against the published
digest. Stop without executing candidate code if any evidence is absent or
differs. Immediately before the first candidate-owned script runs, repeat the
live release verification, downloaded-asset verification, and byte comparison;
do not rely on an earlier preflight. Use the SHA-256 computed from the verified
asset as the candidate digest; release-note text is only a cross-check.

Preserve all project data byte-for-byte, including project memory, session
context, TODOs, lessons, open decisions, events, archives, recognized Session
Context backup sidecars, planning, work items, local state, control records,
and .env. Never read or display secret values. Plan the disposable rehearsal,
then show me the expected changed paths, protected-data checks, collisions,
tests, rollback plan, and total time estimate. Ask me once for the complete
local update. If I approve it, run the disposable rehearsal and
continue to the named-target update only when the target, release, scope,
risk, and expected result still match the approved plan. Stop and report any
mismatch. Do not change application code, commit, push, merge, deploy,
synchronize, or promote anything.
```

The AI should show one understandable local-install or local-update decision.
That decision may include the disposable rehearsal, named-target apply,
verification, one local completion record, and rollback when the displayed
target and scope remain unchanged. Internal work-item, reservation,
capability, evidence, handoff, and writer-release mechanics stay hidden and
are not separate human approvals. A collision, safety failure, or material
change stops the work and returns one plain-English explanation. Git
publication, merge, deployment, and external synchronization remain separate
actions.

For the complete prompts and deterministic safety contract, see the
[AI installation and update guide](.exocortex/docs/AI_INSTALLATION.md).

## CLI fallback

Use this path when no capable coding AI is available or when independently
checking what the AI did. Never pipe an unpinned remote script into a shell.
The commands that execute `install.sh` or `safe-update.sh` must not be run until
the exact immutable release and downloaded manifest asset pass the checks
below.

### 1. Download and verify the exact release

```bash
(
set -eu
gh release verify v3.3.0 -R github.com/EnkratFlow/exocortex-template
mkdir -m 700 /tmp/exocortex-release-verify-v3.3.0
gh release download v3.3.0 -R github.com/EnkratFlow/exocortex-template \
  --pattern SHA256SUMS --dir /tmp/exocortex-release-verify-v3.3.0
gh release verify-asset v3.3.0 \
  /tmp/exocortex-release-verify-v3.3.0/SHA256SUMS \
  -R github.com/EnkratFlow/exocortex-template
git clone --depth 1 --branch v3.3.0 \
  https://github.com/EnkratFlow/exocortex-template.git \
  /tmp/exocortex-template-v3.3.0
cmp -s /tmp/exocortex-release-verify-v3.3.0/SHA256SUMS \
  /tmp/exocortex-template-v3.3.0/SHA256SUMS
git -C /tmp/exocortex-template-v3.3.0 rev-parse HEAD
)
```

On macOS:

```bash
shasum -a 256 /tmp/exocortex-template-v3.3.0/SHA256SUMS
```

On Linux or inside WSL:

```bash
sha256sum /tmp/exocortex-template-v3.3.0/SHA256SUMS
```

Compare both outputs with the peeled commit and candidate digest in the
v3.3.0 GitHub release notes. Stop if either differs. Do not substitute `main`,
`latest`, another checkout, or an unattested manifest. The immutable-release
attestation and verified asset establish the selected repository identity; the
peeled commit and digest checks establish exact byte consistency. Use the
SHA-256 computed from the verified asset—not mutable release-note text—as the
candidate digest passed below.

### Revalidate immediately before execution

An immutable release can be removed after an earlier preflight. Immediately
before running either candidate-owned command below, repeat these checks against
the retained asset and exact tag clone:

```bash
(
set -eu
gh release verify v3.3.0 -R github.com/EnkratFlow/exocortex-template
gh release verify-asset v3.3.0 \
  /tmp/exocortex-release-verify-v3.3.0/SHA256SUMS \
  -R github.com/EnkratFlow/exocortex-template
cmp -s /tmp/exocortex-release-verify-v3.3.0/SHA256SUMS \
  /tmp/exocortex-template-v3.3.0/SHA256SUMS
)
```

Failure means the release is unavailable, revoked, or mismatched. Stop without
executing `install.sh` or `safe-update.sh`.

### 2A. New installation

Rehearse first and install only in an approved clean isolated Git worktree.
The detailed guide explains how to choose the target. Create a new empty,
owner-only disposable `HOME` for this run; do not reuse an existing one.
The underlying installation command is:

```bash
cd /path/to/approved-isolated-worktree
HOME=<new-empty-owner-only-disposable-home> \
EXOCORTEX_LOCAL_SOURCE=/tmp/exocortex-template-v3.3.0 \
EXOCORTEX_CANDIDATE_DIGEST=<sha256-computed-from-verified-release-asset> \
  bash /tmp/exocortex-template-v3.3.0/install.sh "project-name"
```

### 2B. Existing-repository update

Run the read-only dry run from the existing repository. The update source is
temporary; the repository containing your memory remains the target. Create a
fresh owner-only backup directory outside both the target and template first.

```bash
cd /path/to/existing-project
mkdir -m 700 /tmp/exocortex-restore
bash /tmp/exocortex-template-v3.3.0/scripts/safe-update.sh \
  --template /tmp/exocortex-template-v3.3.0 \
  --candidate-digest <sha256-computed-from-verified-release-asset> \
  --backup-dir /tmp/exocortex-restore \
  --dry-run
```

The full guarded `--apply` command requires the exact target-specific values
produced by the accepted rehearsal. Copy it from the
[AI installation and update guide](.exocortex/docs/AI_INSTALLATION.md); never
remove or invent its safety arguments.

## What an update preserves

Project memory stays in the existing repository. The updater protects memory,
session context, TODOs, lessons, decisions, events, archives, recognized
Session Context backup sidecars, planning, work items, local protocol state,
live control records, `.env`, and custom untracked extensions. It compares
protected paths before and after rehearsal and apply, and stops if their bytes,
path types, or modes change.

An update changes the Exocortex code plane only. It never replaces the project,
moves memory into a new worktree, commits, pushes, deploys, or synchronizes
anything automatically. See the [upgrade manifest](.exocortex/docs/UPGRADE_MANIFEST.md)
for collision handling and the [security policy](SECURITY.md) for the complete
failure model.

## Platform support

| Environment | Status |
|---|---|
| macOS with the documented Bash/Unix tools | `verified` |
| Linux | `compatible` |
| Windows through WSL, using the WSL filesystem | `human_uat_pending` |
| Git Bash or native Windows PowerShell/Command Prompt | `unsupported` |

There is no supported native Windows command today. WSL uses the Linux commands
above, but remains Human-UAT-pending until the exact Windows, WSL, distribution,
filesystem, and coding-AI combination passes the documented rehearsal. Do not
translate the Bash safety logic into PowerShell ad hoc.

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

For an approved local change, the orchestrator uses a guarded sequence:
`bootstrap-local-delivery` binds one clean isolated worktree to its exact base,
branch, and allowed paths, then atomically creates/reserves/activates the item
in `developing` without fabricating a normal transition or checkpoint.
`seal-local-edit` records and checks the actual changed set. The ordinary
developer-verification, independent-review, QA/SIT, UAT-ready, and explicit
Human-UAT gates still follow. Only then does `complete-local-delivery` record
`local_state=complete`, create one local completion event and handoff, and
release the writer while lifecycle remains `human_uat`; `release_ready` and
publication are separate. This sequence is cooperative local enforcement only.
It never grants commit, push, release, deployment, synchronization, credential,
or network authority. The existing `create_event.sh` helper remains the manual
`/save` path for ordinary narrative events.

The bootstrap `--envelope-source` and completion `--body-file` must be
project-relative regular files under `.exocortex/local/protocol/inbox/`.
Credential-shaped names (`.env`, `.env.*`, private-key formats, `credentials`,
or `secrets`) are rejected before opening. Each of developer verification,
independent review, QA/SIT, UAT-ready, and Human UAT needs non-empty evidence;
the local transition capability binds the full transition intent. Human UAT
records an attestor matching the envelope approver. Acceptance criteria remain
pending through `uat_ready`; that Human-UAT transition refuses failed or
blocked criteria and atomically records the remaining criteria as passed with
its evidence. Completion rechecks that every criterion passed and still
contains the exact Human-UAT transition marker and evidence, and verifies that
transition against its consumed one-time capability and finalized guarded
transaction. These are cooperative local evidence, not cryptographic proof of
a person's identity.

## Three planes

| Plane | Direction | Contents |
|---|---|---|
| Code | Template to project | generic commands, adapters, guards, docs, tests |
| Data | Project-local only | memory, events, work items, control state, registry, policy, protocol transactions |
| External | Explicitly staged and approved | one immutable payload to one exact destination/method |

Code can flow down after promotion. Project memory never flows sideways.
Nothing flows out automatically.

## Multi-AI orchestration

The parent model owns integration and gate decisions. It selects the correct
model for the complete task using the expected cost of a correct outcome, not
advertised price alone, and applies the same judgment to every subagent. One
registered guarded writer holds the mutation lane; parallel workers are
read-only unless exact project authority says otherwise. Deterministic tools
precede model work. The parent reports its route, reason, and ETA for
visibility; routine model choice is not a human approval gate.

One parent and no delegate is the default. Add only independently useful lanes
expected to improve time, total cost, context quality, or review quality. No
vendor or named model is required. Escalate for risk, ambiguity, tool mismatch,
weak verification, or repeated failure rather than permanently starting at
either the cheapest or strongest tier.

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

Newly observed models are quarantined for formal-verifier use. They do not
become empirical routing evidence merely because they are newer or advertise a
lower price. The optional formal route requires a current local availability
observation and fresh, digest-bound, measured capability and cost-per-success
evidence. Stale or mismatched evidence disables that route, and missing
observations never silently deprecate a model. The formal route also rejects a
caller timestamp more than 60 seconds behind or ahead of runtime UTC;
deterministic historical validation is a separate non-routing operation.

The packaged catalog is advisory and has zero route-eligible models or verified
evaluation profiles. Therefore the optional verifier cannot select a model as
shipped. Accountable parent judgment remains the default; an empty catalog is
not a human approval gate. Formal eligibility requires a reviewed catalog
update that binds measured evaluation evidence plus fresh availability for the
exact current surface.

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
| Claude Desktop 1.24012.1 (0adcae) | `.claude/skills/{command}/SKILL.md` | `/command` | `compatible`; historical 24/24 visibility predates the invocation-policy change, so candidate UAT is required |
| Cursor Stable 3.12.30 | `.cursor/skills/{command}/SKILL.md` | `/command` | `compatible`; historical 24/24 visibility predates the invocation-policy change, so candidate UAT is required |
| GitHub Copilot | `.agents/skills/{command}/SKILL.md` | `/command` where repository skills are supported | `compatible`; 24/24 was observed, but the exact client version was not captured |
| Kimi Code CLI 1.14.0 | `.agents/skills/{command}/SKILL.md` | `/skill:{name}` | `compatible`; historical 24/24 visibility predates the portable-adapter change, so candidate UAT is required |
| Kimi Desktop Work 3.1.3 | No Desktop-specific adapter claim | Not advertised | `failed`; 0/24 appeared and exact `/skill:ai-export` produced no match |
| Zed 1.12.0 stable.328 built-in Agent | `.agents/skills/{command}/SKILL.md` | Built-in Agent skills selector | `compatible`; historical 24/24 visibility predates the portable-adapter change, so candidate UAT is required |
| Windsurf | None in active/default installation | Not advertised | `unavailable`; no installed version was available for Human UAT |
| Generic or unidentified host | `AI_START_HERE.md` plus the matching JSON | Host-dependent | No native-menu claim |

Kimi Desktop Work and Kimi Code CLI are different discovery surfaces. The
Desktop 0/24 result does not invalidate the historical CLI result; the changed
portable adapters still require candidate CLI UAT before that result is verified.

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

Match checks to the change instead of running everything repeatedly:

- Documentation-only changes: documentation contract, generated-adapter check,
  checksum verification, and diff checks.
- Event or memory-tool changes: the event-tooling suite plus the documentation
  contract and checksum verification.
- Installer, updater, authority, orchestration, or protocol changes: focused
  affected checks first, then the complete Exocortex safety suite once for the
  exact release candidate.

The complete Exocortex safety suite (internal path
`tests/phase-b/run.sh`) normally takes more than five minutes and is
deliberately long. Report its expected duration before starting it. Reuse a
passing result for the unchanged exact candidate; do not repeat it merely
because the same commit later becomes `main` or a tag.

Available deterministic commands are:

```bash
bash tests/run_tests.sh
bash .exocortex/scripts/tests/test_orchestration_protocol.sh
bash .exocortex/scripts/tests/test_event_tooling.sh
bash tests/phase-b/run.sh
python3 .exocortex/scripts/generate_command_adapters.py --check
```

The complete safety suite uses only newly created disposable targets, a
sanitized child-process environment, fake transports, and common-command
denial shims. It emits hashes and machine-readable evidence. No test requires
real credentials, providers, repositories, or deployment access. PATH shims
prove that the exercised code did not call those command names; they are not a
network sandbox and cannot contain malicious candidate code.

The public-release boundary also rejects high-confidence personal source data:
absolute home paths, private or tailnet network coordinates, non-public email
addresses or Git identities, and host-specific machine, workload, or
test-policy disclosures.
Unapproved credential-shaped paths are rejected before content access. Known
provider formats, high-risk generic credential assignments, and bearer
credentials are reported only by sanitized rule/count/class/digest evidence.
It scans current source, immutable candidate trees, introduced commit and tag
objects, and transient candidate paths and blobs, including common UTF-16LE and
UTF-16BE text forms. Reserved example domains and generic CI home paths remain
usable in documentation and fixtures. Findings contain only a rule, count,
coarse class, and digest; matched values and raw paths are never shown.
The shipped credential registry is generic metadata and exact-digest locked.

`SHA256SUMS` and its published digest prove byte consistency only. They do not
independently prove repository-owner authenticity when the repository, tag,
release notes, and digest share one trust domain. Public installation must stop
unless the release also carries the owner-selected signature or attestation
evidence and the operator verifies it against its documented trust identity.
Version 3.3.0 selects GitHub's immutable-release attestation for
`github.com/EnkratFlow/exocortex-template` and publishes `SHA256SUMS` as an
attested release asset. Verify both with `gh release verify` and
`gh release verify-asset`; an absent, mutable, mismatched, or unverifiable
release remains blocked.

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
