# Update pull-request runner

This is an inactive Python library for publishing an already verified Exocortex
update as a draft GitHub pull request. It is not a deployed service or a complete
dashboard-to-update workflow. It does not merge a pull request, deploy an
application, synchronize local clones, or grant itself update authority.

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

## Activation work still required

The library is intentionally not reachable from the hosted dashboard. Activation
requires an implementation and review of:

1. The authenticated controller that validates the selected repository, prepares
   a disposable checkout, obtains exact guarded-apply authority and records the
   result. It must never manufacture capability records from a preview.
2. Hosted credential provisioning and an isolated execution host, with private
   durable storage, logging limits and secret rotation. The implemented local
   pilot broker does not provide those hosted boundaries.
3. Hosted dispatch/status and cancellation, tying connection revocation and
   policy revisions to the publisher's current signed control records.
4. An authenticated published target release. An unpublished candidate remains
   invalid for a real update; tests never introduce a production bypass.
5. A disposable GitHub pilot with provider timeouts/restarts, human PR review
   and browser acceptance before any real repository or selected batch.

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
failure recovery. They make no network requests and do not prove a live
deployment. Real guarded installer and restore tests are separate.

The implementation follows GitHub's
[Git tree API](https://docs.github.com/en/rest/git/trees),
[Git reference API](https://docs.github.com/en/rest/git/refs) and
[Git commit API](https://docs.github.com/en/rest/git/commits).
App authentication follows GitHub's
[JWT signing](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app)
and [installation token scope](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app)
contracts.
