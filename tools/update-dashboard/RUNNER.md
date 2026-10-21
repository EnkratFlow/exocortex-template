# Update pull-request runner

This Python library publishes an already verified Exocortex update as a draft
GitHub pull request. A bounded session worker supports an administrator-pinned
disposable pilot from a private dashboard. The trusted preparation controller
connects reviewed local plans to the artifact freezer. Separate attended hosts
run read-only preparation and exactly reviewed, isolated disposable rehearsal.
Hosted apply approval and real-repository activation remain separate work.
The runner does not merge a pull
request, deploy an application, synchronize local clones, or grant itself
update authority.

## Implemented flow

1. `pr_runner_prepare.prepare` consumes an existing successful guarded update
   in a disposable checkout. It verifies the published release and attested
   manifest through the trusted coordinator, checks the exact repository/base
   and plan, and performs a real post-apply dry run. It freezes only the recorded
   effect paths into a bounded, signed artifact. A preview cannot enter this
   path. This function does not create the checkout or run the initial apply.
2. A trusted controller separately grants publication for the exact job, account,
   artifact and expiry using a different signing key. Job lifetime is at most
   one hour. The library does not expose either signing operation to a browser.
3. `pr_runner_authority.RepositoryAuthority` rereads an owner-private signed
   control record and explicit repository policy. Missing declarations,
   exclusions, review-required policies, protected paths, changed revisions,
   changed grants and expired records stop publication. There is no enrollment
   or policy-writing endpoint.
4. `pr_runner_github.GitHubBackend` checks immutable repository identity, current
   default branch, exact base commit, complete tree and previous blob identities.
   It creates content-addressed blobs/tree/commit, a dedicated branch, and a
   draft pull request through the Git data API. The tree retains `base_tree`.
   It cannot update an existing ref or merge a PR.
5. `pr_runner.Runner` records intent and results in a private SQLite store with
   signed state and a per-job process lock. Repeating an identical signed job
   returns the same job. After an uncertain write, recovery observes the exact
   branch and PR before proceeding. An absent result after a timeout requires
   reconciliation; the runner does not blindly repeat that write.

The fixed transport uses only `https://api.github.com`, rejects redirects,
restricts endpoints/methods, bounds input/output, and accepts an injected token
supplier. It does not search environment files, CLI configuration or keychains.
Provider diagnostics and secret values are never persisted in job errors.

## Validation cost and failure recovery

Full release attestation and repository/tree verification run initially and
before branch and PR effects. While creating immutable Git objects, exact
in-process job/artifact bindings are reused; signed control records, policy,
grants and expiry are still checked before every write. A restart starts with
empty validation caches and must perform full validation again.

Pending branch/PR observations may settle after expiry or policy changes, using
current read access and exact repository identity. They cannot authorize another
write. If the base moves during PR creation, the result is
`published_needs_review`, with the observed PR URL, rather than a successful
verified update claim.

Closing an unmerged PR leaves the default branch unchanged. After a merge,
recovery is a separately reviewed revert through the project's own delivery
process. The installer's local backup and restore evidence is a different
recovery mechanism; neither mechanism restores an application's deployment.

## Data and credential boundaries

- POSIX host only; owner-private directory (0700), database/control files (0600).
  SQLite state is not a hosted, encrypted multi-tenant database.
- Two distinct injected signing keys: preparation and publication/control.
  Domain-separated signatures protect packets and durable state.
- Signed controller records select policy/source paths; browser jobs cannot.
  Policy files live beneath the private controller directory.
- Installation credentials belong only in the publisher process. The credential
  broker must bind them to the recorded App installation and repository.
  Preparation must not receive repository write credentials.
- `pr_runner_credentials` supplies a local, single-repository pilot broker.
  An explicit owner-private PEM path is passed to a POSIX OpenSSL signer; the
  key is never discovered, returned to Python, placed in argv/environment, or
  logged. The file must be owner-only, regular, singly linked and beneath a
  0700 directory. Keep it outside repositories and hosted source bundles.
  The broker verifies the exact App/installation/account, selected-repository
  mode and exact permission set. A temporary metadata-only token verifies the
  installation contains exactly one pinned private repository, then is revoked.
  The write token is requested with that immutable repository ID and exact
  permissions, and its accessible repository list is checked again.
- Pilot tokens stay in memory and are refreshed only after retiring the prior
  token. Failed revocations retain an inaccessible token for retry; pending
  cleanup blocks reuse and replacement until deletion succeeds or verified
  expiry passes. Call `revoke()` when ending the pilot. A lost token-creation
  response may leave an unknown provider token until its one-hour expiry.
  This local mechanism is not a vault, remote service or OS isolation boundary.
- No target-repository script is executed by the publisher. Preparation imports
  its coordinator from the trusted application tree, not from the target.
- Maximum 1,000 changed files, 2 MiB per file, 8 MiB decoded content and 12 MiB
  packet. Symlinks, protected memory/runtime data, credentials, application
  files and workflows are rejected.
- Root `.gitignore` is deliberately blocked: the coordinator's managed snapshot
  does not yet prove preservation of owner additions to that file. An artifact
  containing it needs a reviewed preservation implementation before publication.
- Customized repositories remain blocked in this standard lane. A separately
  reconciled installer fixture does not enroll its real repository for updates.

## Bounded dashboard pilot

`pr_runner_pilot_worker.py` polls one administrator-configured private HTTPS
origin. It accepts only signed requests for one existing, signed prepared job;
the dashboard cannot provide commands, filesystem paths, release choices or
artifacts. The hosted controller binds the enrolled GitHub account, explicit
Standard treatment, source commit, and connection/preference revisions to a
short-lived preview and persistent request. Only one request per owner may be
active. Other repositories remain in the read-only inspection workflow.

The worker uses a separate RSA signing key for request authentication. Signatures
bind method, origin, path, timestamp, nonce and body digest; the controller
rejects replayed nonces. Private Sites service access arrives on hidden stdin
and stays in memory. It supplies no visitor identity and grants no publication
capability. The App key and preparation/publication signing keys stay local.
No HTTP listener is opened. Run only as an attended session, for at most four
hours; this is not a permanent daemon or OS isolation boundary.

Before new writes the existing signed authority and hosted cancellation,
connection, source and treatment checks must all pass. The worker never submits
a replacement job or renews an expired grant. Completed or interrupted jobs can
be observed after expiry, without renewed write authority. An existing PR is
reused and checked for exact repository, branch, commit, base and draft state.
A result already requiring review cannot become a successful completion merely
because it was read again. Cancellation after a provider effect retains the PR
link and a review-required result. Owners can cancel their requests after their
GitHub connection expires or is disconnected.

One credential broker lives for the session. Revocation must succeed, or the
credential reach verified expiry, before polling/minting again. Pending results
remain retryable across transient transport failure; a lost lease recovers the
same durable job. The original per-job process lock still protects publisher
state. The server stores progress independently of browser tabs; refresh does
not create another request.

## Preparation controller

`pr_runner_controller.PreparationController` connects the selected updater to
artifact preparation for a host-provisioned disposable checkout. The host supplies
fixed paths, the existing signed repository authority callback and a current
read-only provider observer. Browser input cannot choose local paths or supply
policy declarations. The observer returns exactly `repository_id`, `repository`,
`base_branch` and `base_sha`; it must obtain these from the current provider state.

`preview(plan_id, job)` verifies the published release, private controller policy,
repository identity and exact base before creating an immutable one-target plan.
Repeating the same plan reuses its preview; different bindings are rejected.
`rehearse(plan_id, expected_digest, job, authorities, preparation_key)` requires
an exact reviewed plan digest and existing target-specific guarded apply authority.
It delegates apply, preservation and post-apply verification to the existing
coordinator. It neither creates capabilities nor treats a preview as consent.

Only a verified rehearsal reaches the artifact freezer. Release, policy, source
and expiry are checked again after freezing, including when slow verification
crosses the expiry boundary. `freeze` can retry artifact creation from an already
verified plan without repeating apply. Failed updates retain the coordinator's
recovery state and cannot be signed as successful. The publisher still requires
its separate, exact artifact-bound grant; this module cannot create a PR itself.

These are trusted host APIs, not public HTTP routes. The caller is responsible
for provisioning an isolated disposable checkout without write credentials and
for durably retaining the returned signed packet. Production activation still
requires deployment-specific isolation evidence, registration, release approval
and repository consent.

## Activation work still required

The prepared disposable pilot does not complete general activation. Remaining
work requires implementation, review and evidence for:

1. Complete authenticated hosted-owner acceptance of the isolated preparation
   host described below. The attended host and network-free preview execution
   are implemented; no reviewed apply-request path is enabled.
2. Hosted credential provisioning and an isolated execution host, with private
   durable storage, logging limits and secret rotation. The implemented local
   pilot broker does not provide those hosted boundaries.
3. Extending the bounded pilot controller to newly prepared jobs, with exact
   signed authority, revocation and policy checks for every enrolled repository.
4. An authenticated published target release. An unpublished candidate remains
   invalid for a real update; tests never introduce a production bypass.
5. A disposable GitHub pilot with provider timeouts/restarts, human PR review
   and browser acceptance before any real repository or selected batch. The
   offline recovery tests do not prove live provider timeout behavior.

Keep the existing read-only discovery App intact. Its permission checks reject
write grants. The recommended external setup is a **separate update App**, with
Metadata read, Contents write and Pull requests write, initially installed only
on one disposable test repository. Do not request Actions, Administration,
Workflows, Secrets or organization write permissions. The hosting/controller
choice and any paid service require a concrete deployment proposal before setup.

No API keys, App private keys or access tokens should be pasted into chat or
committed. Provision them only through the selected host's secret interface.
App consent and repository selection must occur in GitHub's own interface.

## Tests

From the template checkout, Python 3.12 on a POSIX host:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_pr_runner*.py' -v
```

The tests use fictional identities, real local files/SQLite and mocked GitHub
responses/release attestation. They cover account isolation, state tampering,
explicit policy, expiry/revocation, restart deduplication, uncertain writes,
changed bases, closed/foreign PRs, size/path limits, bounded transport and
multi-file validation cost. Credential tests use real disposable RSA signing
and fictional provider responses to verify scope, expiry and revocation
failure recovery. Session-worker tests exercise real SQLite recovery after
cancellation, exact PR identity, and terminal input echo suppression. They make
no network requests and do not prove a live
deployment. Real guarded installer and restore tests are separate.

The implementation follows GitHub's
[Git tree API](https://docs.github.com/en/rest/git/trees),
[Git reference API](https://docs.github.com/en/rest/git/refs) and
[Git commit API](https://docs.github.com/en/rest/git/commits).
App authentication follows GitHub's
[JWT signing](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app)
and [installation token scope](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
contracts.

## Preparation request bridge

`pr_runner_preparation_worker.PreparationWorker` connects an attended host to a
separate authenticated preparation queue. The host injects its provisioned
`PreparationController`, one exact job, GitHub identity and a
`SiteClient(lane="preparation")`. There is no credential discovery, CLI that
accepts browser paths, automatic checkout provisioning or daemon installation.

The private hosted queue binds encrypted owner previews to the configured job,
repository/base, published target metadata, GitHub account, connection epoch and
explicit Standard preference revision. Requests persist independently of tabs;
one active request per owner is enforced in SQLite. Signed worker requests use
fresh nonces and leases. Cancellation, changed access, changed base, expired
configuration and expired leases cannot produce a successful plan result.

The worker only calls `controller.preview()`. It cannot rehearse, apply, freeze,
publish or merge. The controller itself authenticates the published release and
private policy. A returned plan requires separate review and existing guarded
apply authority before the previously implemented rehearsal path may be used.
The queue has no endpoint that creates that authority. Missing administrator
configuration leaves preparation unavailable, with an explanation in the UI.

A restarted request chooses the same local plan ID. Lost result responses retry
the identical bounded result without repeating preview; the server accepts exact
terminal-result retries. Lost leases discard the pending delivery and allow
normal queue recovery. The host must enforce one writer per disposable checkout
and protect its durable coordinator state. A session lasts at most four hours;
private Sites access remains injected in memory and is not a durable credential.

Offline queue, encryption, lease, worker, transport and built-UI tests establish
these boundaries. They do not demonstrate a provisioned isolated execution host,
an actual hosted-owner preparation request, a new guarded apply, or publication
of a real repository update. Real activation still requires those proofs.


## Isolated preparation execution

`pr_runner_isolation.DockerPreview` is an optional preview invoker for the
coordinator and preparation controller. It is rejected for apply. The trusted
host performs fixed read-only GitHub observations and published-release
attestation; only the authenticated updater dry run executes in Docker.
Provider credentials, signed controller policy and coordinator state stay out
of the container. This separates provider access from untrusted execution; it
does not sandbox the trusted host controller or Docker daemon itself.

The adapter pins a local Unix-socket Docker endpoint, an empty temporary client
configuration and an immutable local image ID. Ambient Docker host/context and
proxy configuration are excluded. The container has no network, runs as the
nonroot host UID, drops all capabilities and disallows privilege escalation.
Its root, release, target checkout and authenticated private launcher snapshot
are read-only. Only the selected backup subdirectory and a 256 MiB temporary
filesystem are writable. Limits are one CPU, 512 MiB RAM, 128 processes, 240
seconds and 8 MiB captured output. Docker logging and restart are disabled.
Actual inspect results are checked before start. A unique ownership label/name
allows reconciliation after a lost create response; cleanup failure is a failure.

Build the runtime separately with `tools/update-dashboard/isolation.Dockerfile`,
review it, and use its local `sha256:` image ID in the private host configuration.
The runner never starts Docker, pulls an image, clones a target, discovers keys,
or installs a daemon. The image's installed package versions are captured by the
resulting image ID; rebuilding the Dockerfile may produce a different ID.

For a standalone diagnostic preview:

```sh
python3 tools/update-dashboard/pr_runner_isolation.py --config /absolute/private/host.json
```

That owner-only (0600), absolute-path JSON file has exactly these fields:
`image`, `source`, `checkout`, `backup_root`, `controller`, `plan_id`,
`account_scope`, `repository`, `repository_id`, `base_branch`, `base_sha`.
`source` is the existing coordinator's authenticated published-source record
(`path`, `manifest_sha256`, `release`), not a browser-supplied release selector.
The repository ID and base SHA must match current GitHub observations before
and after preview. Paths must be canonical, separate local directories; the
checkout must be a standalone disposable clone. No credentials belong in this
file. The CLI reports bounded evidence and never applies or publishes.

A clone lacks local-only identity and memory. Provision verified local context
through the existing approved process before rehearsal. Missing context remains
a preservation failure; never invent it to make a real repository pass.
Disposable fixture tests may restore their explicitly declared fictional context.

For the hosted preparation queue, run:

```sh
python3 tools/update-dashboard/pr_runner_preparation_host.py --config /absolute/private/session.json --duration 900
```

The session file has exactly `host`, `job`, `authority_directory`, `control_key`,
`worker_key`, `origin`, `github_id`. `host` is the standalone configuration above
without `plan_id` (the immutable hosted request chooses that ID). `job` names an
owner-private, unexpired, exact job record. `authority_directory` and
`control_key` refer to the existing signed RepositoryAuthority policy; they do
not grant publication. `worker_key` is the existing request-signing key. No
writer App key or publication grant is accepted. Service access arrives as one
hidden-stdin JSON object with `service_token`, and stays in memory. The session
holds an exclusive controller lock and expires after at most four hours.

The host's `configuration(job, github_id)` output must exactly match the private
Site's `UPDATE_PREPARATION_CONFIG`; the existing worker public key must match.
The owner still requests preparation through the signed-in dashboard. Service
access cannot impersonate that owner. This entrypoint composes the same queue
checks for cancellation, connection/preference changes, lease expiry and retry.
A completed preview is evidence only; applying, freezing and publishing remain
separate guarded operations.

## Separately reviewed isolated rehearsal

`DockerRehearsal` supplies the distinct writable lane. It pins existing
target-specific authority references and passes them to the published installer's
guard; it creates no capability. Only the disposable checkout and exact backup
directory are writable. Git metadata remains a separate read-only mount. All
dry runs, including the artifact freezer's final check, use read-only checkout
mounts. Writable trees reject hard links, symlinks and special files. The same
network, privilege, image, resource, inspection and cleanup restrictions as
`DockerPreview` apply. Preview callbacks still cannot authorize apply.

An attended host can run one independently reviewed plan:

```sh
python3 tools/update-dashboard/pr_runner_rehearsal_host.py --config /absolute/private/rehearsal.json
```

This owner-private configuration has exactly `host`, `job`, `review`,
`authorities`, `authority_directory`, `control_key`, and `preparation_key`.
The latter six values name already provisioned private files/directories; no
writer App key or Sites service access is accepted. `host` has exactly `image`,
`source`, `checkout`, `backup_root`, `controller`, and `output`. The output is
one new JSON file directly within the controller directory, outside every
container mount. The source has the coordinator's authenticated release pin.

The control-key-signed `rehearsal-review` packet binds the complete job,
`host_sha256`, `plan_id`, `plan_sha256`, `target_id`, and
`authorities_sha256`. The job binds account, connection epoch, repository ID,
base, published release, preference/policy revision and expiry. A preview packet
is not a review packet. The host also requires the existing exact guarded apply
capability and executor records in the disposable checkout. Provisioning those
records requires the separately accepted rehearsal scope; neither this command
nor browser input creates them.

Live policy, provider identity and expiry are rechecked between phases and again
immediately before starting each container. Successful apply and final zero-change
verification freeze only the recorded effect paths. The signed artifact is saved
privately with an atomic no-overwrite write. Repeating a completed request returns
that exact artifact after revalidation. An interrupted apply or a missing artifact
after apply never causes automatic reapplication: retain the saved plan and archive,
review recovery, and use the controller's separately scoped freeze recovery where
appropriate. Cancellation during execution can leave a disposable change requiring
recovery; it cannot authorize later freezing or publication.

The hosted preparation queue remains preview-only. The standalone command does not add a
dashboard action or publication grant. A frozen artifact still needs its
separate exact publication review before the existing PR runner may act.

The optional container integration tests use fictional accounts and an unpublished
local candidate, substituting provider provenance checks only. They exercise the
real installer, capability consumption, memory/knowledge/application preservation,
artifact freezing, exact replay and a lost apply response. They do not prove an
authenticated release, a hosted human approval, a real PR, or a production upgrade.

Docker options follow the official [container execution reference](https://docs.docker.com/engine/containers/run/).


## Hosted plan review and attended test

Preparation results now include bounded review evidence: exact repository/base,
installed version and release tag, a sorted list of at most 1,000 template paths
(each at most 240 ASCII characters), and protected-data dry-run verification.
Only relative publishable template paths are included; never contents, host paths,
keys or local control records. Older count-only results remain historical evidence
and cannot request a test. A current, zero-change result needs no update PR.

The private dashboard displays the complete path list in searchable pages. The
owner opens the saved plan and explicitly requests **Test this plan** after
reviewing it. A five-minute, account-bound receipt binds the exact result digest,
connection epoch, policy revision and configuration. A separate durable rehearsal
queue records that request; it never converts a preparation receipt into installer
authority. The request lasts at most 15 minutes and cannot outlive its pinned job.

The attended bridge is:

```sh
python3 tools/update-dashboard/pr_runner_rehearsal_worker.py --config /absolute/private/review-worker.json --duration 900
```

Its private configuration has exactly `host`, `preview_job`, `review`,
`authorities`, `authority_directory`, `control_key`, `preparation_key`, `github_id`,
`worker_key`, and `origin`. The host fields match the standalone rehearsal host.
`preview_job` is the original pinned preparation job. The separate signed review's
job differs only by its concrete plan digest. The review must additionally bind
`hosted_review`, with the full `preparation_id` and canonical `result_sha256`.
The plan ID must be `prep-` followed by the preparation ID's first 32 characters.
This bridge cannot create any of these authority records. Service access is
accepted only through hidden stdin and kept in memory.

Polling selects only that exact preparation/result. Before execution, the bridge
recomputes the displayed result from the ready local plan. Dashboard cancellation,
access, preference, source/base and expiry checks supplement the existing installer
authority checks before every isolated execution boundary. Hosted-bound reviews
cannot use the standalone host without the hosted request gate. No browser input
selects paths, commands, capabilities, releases or credentials.

A ten-minute renewable boundary lease covers the supported 240-second container
operation and bounded checks. An expired writable lease is never reclaimed.
Cancellation after claim, lost execution status or a failed test requires explicit
recovery review. A lost report retries the exact result without repeating apply.
Only artifact digest, changed-file count and outcome return to the dashboard;
the actual signed artifact stays private on the host. Success means a disposable
copy passed its update checks, not a repository update, PR, merge or deployment.
Separate artifact publication review is still required.

## Reviewed artifact publication

The new publication lane continues a **verified** hosted rehearsal. The owner
opens **Review draft PR request**, checks the repository, installed/target
versions and complete tested path list, and explicitly chooses **Create draft
update PR**. This uses a separate five-minute `publication-review` receipt; a
preparation or rehearsal receipt cannot request publication. Each saved request
retains its own repository, version and artifact digest, independent of the old
fixed pilot and any later configuration. Nothing automatically merges or deploys.

The host validates the rehearsal's private `{review_sha256, packet}` wrapper,
its separately signed review, the original preview job and the exact rich
preparation result. The tested packet must retain the original job's identity,
base, release, policy and expiry, and contain exactly the reviewed paths. Only
its post-apply plan/artifact digests may change. The handoff emits metadata only;
file contents and signatures remain on the host.

```sh
python3 tools/update-dashboard/pr_runner_publication_worker.py --config /absolute/private/publication-worker.json --duration 900
```

The owner-private configuration has exactly `saved`, `review`, `preview_job`,
`result`, `control_key`, `preparation_key`, `publication_key`, `runtime`,
`github_id`, `worker_key`, `origin`, `app_key`, `app_id`, and `account_id`.
The first four name the saved rehearsal wrapper, signed review, original
preparation job and its exact rich result (retain this before rehearsal changes
the plan). Keys and runtime are already provisioned host paths. The runtime
retains the existing `authority` directory, independent `grant.json`, and durable
`jobs` state. There is no key discovery, grant issuance, capability creation or
browser-supplied path. Service access arrives through hidden stdin only.

`handoff(...)` returns the exact non-secret `UPDATE_PUBLICATION_CONFIG` value:
`preparation_id`, `result_sha256`, `artifact_sha256`, `job_id`, and `preparation`
(the original preparation configuration). A trusted operator provisions this
value alongside the matching, unexpired `UPDATE_PREPARATION_CONFIG`; the browser
cannot choose it. Keeping it unset disables publication. A local
`publish-update-pr` grant must separately bind that complete job/artifact/account
and expiry, with current repository authority. The hosted receipt is an additional
live gate, never a replacement for that grant.

Polling claims only the matching artifact. Live account/access, preference,
base, lease and expiry are checked before publication writes. Exact result
retries do not repeat publication. Cancellation after claim, lost leases and
ambiguous provider results retain `recovery_required`; they are not automatically
reclaimed. Preserve the runner database and reconcile its exact branch/PR using
the existing recovery path before any new request. Never discard the database,
renew a grant blindly or interpret an absent result as proof of no GitHub effects.
Temporary installation credentials are revoked before another poll or shutdown.

The offline bridge tests exercise the actual durable Runner with a fictional
provider: missing/wrong grants and rejected hosted checks produce zero writes;
an exact accepted artifact creates only its dedicated branch and draft PR.
Hosted tests cover separate approval, artifact/identity substitution, cancellation,
expiry, final-write races, safe PR links and account-bound history. These are not
a live changed-repository acceptance test or evidence of an upgraded consumer.
