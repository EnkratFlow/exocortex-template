# Exocortex implementation guide

This guide describes how to install, operate, verify, and evolve the current
provider-neutral Exocortex protocol. `AI_START_HERE.md` is the canonical entry
contract; this document does not grant authority.

## Repository layout

```text
AI_START_HERE.md                         canonical multi-AI entry
README.md                                operator overview and install/update path
SHA256SUMS                               code-plane integrity inventory
install.sh                               pinned local installer
scripts/safe-update.sh                   guarded rehearsal and update wrapper
.exocortex/
  AI_BOOTSTRAP.md                        command discovery and execution rules
  commands/*.json                        24 command specifications
  model-source-registry.json             reviewed official-source inventory
  model-routing-catalog.json             advisory normalized model facts
  control/
    DELIVERY_WORKFLOW.md                 minute-scale delivery lifecycle
    MODEL_ROUTING.md                     capability/risk/cost routing
    EXECUTOR_REGISTRY.json               generated protected project data
    EXTERNAL_SYNC_POLICY.json            generated protected project data
  schemas/
    model-source-registry.schema.json    official-source contract
    model-routing-catalog.schema.json    advisory catalog contract
    model-observation.schema.json        normalized discovery evidence
    model-availability.schema.json       current-surface availability
    update-reconciliation-plan.schema.json exact target convergence plan
  scripts/
    authority_guard.py                   executor and capability validation
    orchestrate_work_item.py             orientation and guarded transitions
    model_registry.py                    offline freshness/discovery validation
    prepare_update_reconciliation.py     exact non-mutating plan preparation
    egress_guard.py                      staged destination-bound external action
    create_event.sh                      project-local narrative handoff/save
    tests/                               deterministic protocol tests
  events/                                project-local append-only narrative data
  local/protocol/                        protected runtime transactions and audit
  work-items/                            project-local delivery records
tests/
  run_tests.sh                           installer/update regression suite
  phase-b/run.sh                         disposable Phase B evidence harness
```

The template code plane is generic. Memory, events, work items, approvals,
reservations, executor records, external destinations, and protocol
transactions are project-local data and are never promoted as template
fixtures.

The packaged model catalog has no eligible models or verified evaluation
profiles. Raw availability, evaluation, and quarantine evidence remains
protected under `.exocortex/local/model-routing/**`; a separately reviewed
catalog admission is required before routing can select anything.

## Start every AI surface the same way

Before any action:

1. Read `AI_START_HERE.md`.
2. Read `.exocortex/AI_BOOTSTRAP.md`.
3. Read `.exocortex/reference/MEMORY.md` and its required project files.
4. Read `.exocortex/control/DELIVERY_WORKFLOW.md` and
   `.exocortex/control/MODEL_ROUTING.md`.
5. Resolve live Git and reconcile generated context with exact work-item and
   event evidence.
6. Declare `read_only`, `writer`, or `independent_reviewer`.

Unknown or unregistered surfaces remain read-only. Editor rules, skills, and
command bridges point to the canonical entry; they cannot create authority.

## Install into a new repository

Obtain and review an exact template revision. Do not execute an unpinned remote
installer. Record the SHA-256 of that revision's reviewed `SHA256SUMS` as the
approved candidate digest. Rehearse in a sanitized disposable fixture first.
After the disposable evidence is accepted, use one named-target
`local_delivery` decision to create a clean isolated Git worktree from the
exact target HEAD, run the local installer, verify it, record the permitted
local handoff, and release the writer:

A coding AI with local filesystem and terminal access may operate this exact
flow using the clean-install prompt in
`.exocortex/docs/AI_INSTALLATION.md`. The prompt does not replace any digest,
rehearsal, approval, or verification requirement.

```bash
git clone <approved-template-repository> /tmp/exocortex-template
git -C /tmp/exocortex-template checkout <approved-exact-sha>
git -C /path/to/project worktree add --detach \
  /path/to/approved-isolated-worktree <approved-target-head>
cd /path/to/approved-isolated-worktree
HOME=<absolute-disposable-home> \
EXOCORTEX_LOCAL_SOURCE=/tmp/exocortex-template \
EXOCORTEX_CANDIDATE_DIGEST=<approved-sha256-of-SHA256SUMS> \
  bash /tmp/exocortex-template/install.sh "project-name"
```

Creating the worktree, installing, verifying, recording the local handoff, and
releasing the writer are internal steps of that one accepted local-delivery
envelope. The orchestrator still derives exact one-time technical
capabilities and fails closed on drift. Direct installation into a shared or
primary checkout is unsupported while the clean installer writes in place
without a restore archive.

For a rehearsal:

- use a sanitized disposable fixture containing only approved non-secret
  install surfaces and known collisions;
- set `HOME` to a newly created disposable directory;
- run non-interactively;
- use no real credentials, provider access, or project data;
- reject install-surface symlinks and hash only approved non-secret regular
  files;
- exercise a controlled mid-copy failure and prove its partial writes remain
  contained in the disposable fixture;
- verify that no global editor-home, scheduler, service, network, or external
  destination changed.

The installer verifies the candidate inventory before mutation. When absent,
it creates project-local deny-by-default executor and external-sync records.
Those records are protected data and are not manifest payload.

## Update an existing repository

Use the same pinned local source and candidate digest. Rehearse first in a
newly created disposable copy and place restore material outside the target.
Before dry run, complete the metadata-only legacy protected-default preflight
in `.exocortex/docs/AI_INSTALLATION.md`; missing generic scaffolding uses an
internal guarded bootstrap under the active local-delivery envelope and
existing protected data is never overwritten:

```bash
cd /path/to/existing-project
bash /tmp/exocortex-template/scripts/safe-update.sh \
  --template /tmp/exocortex-template \
  --candidate-digest <approved-sha256-of-SHA256SUMS> \
  --backup-dir /tmp/exocortex-restore \
  --dry-run
```

Accept the rehearsal evidence before asking once for a named-target local
apply. A real apply uses the same pinned template and digest plus `--apply`,
one exact internally derived unconsumed capability, and the registered
executor identity. There is no interactive or implicit approval prompt inside
the command.

The complete command is:

```bash
cd /path/to/existing-project
bash /tmp/exocortex-template/scripts/safe-update.sh \
  --template /tmp/exocortex-template \
  --candidate-digest <approved-sha256-of-SHA256SUMS> \
  --backup-dir /tmp/exocortex-restore \
  --apply \
  --capability <project-relative-capability-path> \
  --work-item-id <exact-work-item-id> \
  --work-item-revision <exact-current-revision> \
  --request-id <unique-request-id> \
  --surface-id <registered-surface-id> \
  --executor-id <registered-executor-id> \
  --adapter-version <registered-adapter-version>
```

The work item, active writer reservation, registered executor, and one-time
`apply_template_update` capability must already match the exact candidate and
changed-path scope. See `.exocortex/docs/AI_INSTALLATION.md` for the
provider-neutral prompt, required preflight report, retry/idempotency sequence,
GitHub boundary, platform matrix, and Human UAT.

Customized or unknown collisions remain preserved by the ordinary updater.
Reviewed target-specific convergence uses
`.exocortex/scripts/prepare_update_reconciliation.py`, a digest-bound exact
plan, disposable rehearsal, and an internally distinct one-time
`apply_template_reconciliation` capability. Ordinary update authority cannot
be reused. A changed plan or effect set requires a replacement named-target
local-delivery decision.

The updater must preserve:

- project memory, TODO, lessons, decisions, and generated context;
- events, archives, planning, work items, and local protocol state;
- executor registry, external-sync policy, live control records, and hub
  markers;
- user-modified manifest files and untracked project extensions.

Missing, malformed, incomplete, or mismatched checksums fail before target
mutation. Apply revalidates the target and exact changed-path set immediately
before consuming authority. Update one repository at a time; a request for
“all” never authorizes a batch rollout.

The current implementation is verified on macOS with the documented Bash/Unix
tools. Linux must pass final-candidate CI; WSL still requires Human UAT. Git
Bash and native Windows shells are unsupported.

## Define a bounded work item

Every implementation slice records:

- a stable work-item ID, class, revision, and current state;
- intended outcome, requirements, and acceptance criteria;
- exact base and allowed path set;
- risks, dependencies, rollback, and verification matrix;
- writer reservation and registered executor;
- the human-facing business envelope plus exact internal operation, expiry,
  revocation, and capability-consumption state;
- evidence required for the next gate.

Use the smallest useful slice. A feature, bug, maintenance item, migration,
security/privacy change, documentation/process change, or retrospective
improvement follows the same lifecycle.

## Route and delegate work

Routing is role-based and model-neutral:

1. Use deterministic tooling for Git truth, schemas, searches, checksums,
   tests, and repeatable transformations.
2. Classify complexity, novelty, ambiguity, context, tools, and risk.
3. Bind production routing to an explicit UTC timestamp no more than 60 seconds
   from the runtime clock. Use the separate deterministic validator for
   historical evidence inspection; it does not select a model.
4. Select the least-expensive available model capable of owning the whole
   bounded task as accountable parent.
5. Delegate only independently useful evidence or review work to the
   least-cost capable lanes.
6. Register one guarded writer for the exact mutation scope; keep every other
   lane read-only.
7. Escalate when ambiguity, repeated failure, sensitive data, scope drift,
   outward action, or material design judgment exceeds the selected role.
8. Return results to the parent for integration and deterministic verification.

Adapters may maintain versioned mappings from available models to roles using
capability, reliability, latency, and cost. A named model or permanent
largest-first rule is never normative.

## Execute a guarded local mutation

Immediately before mutation, the high-level entry validates:

- the accepted human-facing business envelope and its gate class;
- work-item ID, revision, state, and attempt;
- exact operation, base, target, and allowed paths;
- active writer reservation and registered guarded executor;
- approval acceptance, expiry, revocation, and prior consumption;
- required upstream evidence.

Use `.exocortex/scripts/orchestrate_work_item.py` and
`.exocortex/scripts/authority_guard.py` for protocol-managed mutations. Prose,
configuration, credentials, branch names, and allowlists are context only;
none independently grants permission.

The owner approves one bounded business outcome. The orchestrator may create
and consume the exact internal work-item, registry, reservation, capability,
transition, evidence, local-handoff, and writer-release records needed for
that outcome without another human prompt. A changed target, base, digest,
path/plan set, operation class, risk, ambiguous effect, or expired/revoked
business envelope stops before mutation and requires one replacement
decision.

After the bounded edit, verify the exact diff and evidence before proposing a
transition. An accepted checkpoint-eligible transition and its checkpoint are
one durable idempotent transaction. Invalid attempts create neither partial
state nor checkpoints.

## Apply the delivery lifecycle

Follow this sequence without skipping applicable gates:

```text
captured -> triaged -> refined -> ready -> reserved -> developing
-> developer_verified -> independent_review -> qa_sit -> uat_ready
-> human_uat -> release_ready -> awaiting_release -> deployment_approved
-> deployed -> hypercare -> done
```

Developer verification proves the implementation on the exact candidate.
Independent review is performed by a registered read-only reviewer distinct
from the writer when required by gate or risk. QA/SIT includes applicable unit,
integration, regression, security/privacy, migration, and recovery evidence.

Human UAT is prepared as concrete, observable cases. The human accepts or
rejects it in plain language; the implementing model cannot accept its own
UAT. Recording that decision and performing local closeout are internal
mechanics of the active local-delivery envelope. Publication,
integration/rollout, and exact-target production/egress remain later business
decisions.

Define hypercare duration or operation count, observation cadence, rollback
triggers, and exit criteria before release. A rollback trigger creates a new
corrective item; it does not allow silent fix-forward.

## Record memory correctly

Use project-local events for narrative memory:

```bash
bash .exocortex/scripts/create_event.sh --body-file /path/to/local-body.md
```

A save or handoff records facts, decisions, tests, limitations, and the next
verification. It does not grant a writer lane, create a lifecycle transition,
commit changes, or synchronize externally.

Automatic phase hooks are reminders only. They do not save, checkpoint,
transition, select a model, or send data. Legacy editor-history harvesting is
disabled; durable context comes from explicitly authorized project-local
events and deterministic Git evidence.

## Stage an external action

Do not access an outward payload, credential, or destination without the full
external-action chain:

1. Under a `local_delivery` envelope that explicitly permits preparation of
   the named outward source, derive and accept an exact local inspection
   capability before opening the source.
2. Propose digest, size, class, source, object path, and descriptor.
3. Derive a second exact capability to stage those values immutably. Do not ask
   the human to approve the internal inspect/stage capabilities separately.
4. Have the human review the immutable descriptor and make one exact
   `production_egress` decision for the destination, method, digest, executor,
   and expiry.
5. Validate metadata before payload access, verify bytes before credential
   lookup, and revalidate immediately before transport.

Use `.exocortex/scripts/egress_guard.py`; legacy delivery adapters must fail
closed or delegate to it. Never auto-retry an indeterminate external send.

## Deterministic verification

Run the local suites from the template checkout:

```bash
bash tests/run_tests.sh
bash .exocortex/scripts/tests/test_orchestration_protocol.sh
bash .exocortex/scripts/tests/test_event_tooling.sh
bash tests/phase-b/run.sh
```

Also verify, as applicable:

- Python syntax without creating repository bytecode;
- shell syntax;
- JSON schema and fixture parsing;
- `git diff --check`;
- exact changed-path containment;
- checksum inventory completeness and candidate digest;
- absence of private identifiers, project data, credentials, direct provider
  calls, and live destinations;
- install/update idempotency, rollback, protected-data preservation, and
  target-race denial.

The Phase B harness uses disposable targets, a disposable `HOME`, fake
transports, and deny-network shims. It must report exact artifact hashes and
whether credentials, live providers, or live targets were used.

## Build a handoff evidence packet

Record:

- exact branch, base SHA, candidate tree or diff digest, and work-item revision;
- writer identity and lane state;
- changed paths and scope verification;
- test cases, results, tool versions, and artifact hashes;
- independent reviewer identity and findings;
- unresolved limitations and risks;
- which approvals remain closed.

Evidence from another candidate is not gate evidence. A clean branch, passing
unit tests, or a model assertion does not establish Human UAT, release,
deployment, hypercare, or Done.

## Promote safely

Promotion is not an update and is never implied by successful local tests.
Under one exact `integration_rollout` decision, replay only the accepted
privacy-scrubbed code-plane diff onto an approved clean public base. Exclude
project-local planning history, memory, events, identities, destinations,
approvals, and reservations. Scan the resulting tree and newly reachable
history, regenerate and verify the checksum inventory, and rerun the complete
deterministic suites. Production deployment or egress remains outside that
envelope.

## Recursive improvement loop

After a bounded item completes, produce a retrospective containing observed
evidence, the smallest proposed improvement, expected benefit, risks, and a
verification plan. The proposal starts a new isolated item only after human
local-delivery authorization. The orchestrator internally provides the fresh
writer reservation and technical capabilities, then runs verification and
Human UAT when applicable. Publication, integration/rollout, and
production/egress remain later decisions.

This creates recursive improvement without self-modifying authority: the
system may discover and propose a better protocol, but it cannot approve or
deploy that proposal itself.

## Known trust boundary

The local guards provide cooperative repository enforcement. They are not an
operating-system sandbox, and unsigned local JSON cannot prove a human decision
against a process able to rewrite both trust records and guard inputs. A
privileged broker and trusted signing or attestation root are required before
the protocol can make externally trusted enforcement claims.
