# Exocortex release status

Last updated: 2026-08-08

This is the living, human-readable maintainer view of where the public template
stands. It is release-scoped, not a downstream project's status page, owner
preference, approval record, release claim, or replacement for test evidence.

## Published baseline

- The previous reviewed published baseline is `v3.2.8` at commit
  `cd577ab633ac3c8edff52cc2128e986f1ad2785d`.
- The packaged version is `3.2.9`. Live GitHub tag, release, immutability, and
  attestation evidence remains authoritative; this tracked page does not turn
  a candidate into a published release.

## Candidate state

| Area | State | Current objective |
| --- | --- | --- |
| Model routing | Implemented; focused checks pass | Accountable-parent judgment is the default, with formal routing retained as optional evidence rather than an approval gate. |
| Subagents | Implemented; focused checks pass | The same correct-model-for-the-job and cost-of-correct-outcome judgment applies to every delegate. |
| Command adapters | Focused checks pass | 11 bounded read-only commands are model-discoverable and 13 human-controlled commands remain manual-only; all authority boundaries remain. |
| Public-release safety | Focused checks and independent review pass | The checker rejects protected data, unsafe topology, redacted secret-shaped paths/content/commit/tag metadata, replacement-object history, modified public fixtures, and transient candidate data. |
| CI and integrity | Tag-event hotfix in verification | Every pull request produces the required check, push/tag ranges fail closed, the public boundary runs in CI, third-party Actions are pinned, and the exact code-plane checksum and mode inventories are verified. The first live v3.2.9 tag-event verification exposed GitHub checkout's peeled-tag shape; the bounded hotfix fetches the exact remote annotated object before validation. |
| Upgrade/install path | Focused security rehearsal passes | Clean install plus guarded dry-run upgrade passed in disposable fixtures, including source races, import-shadow denial, rsync/tar denial, protected environment preservation, rollback exclusion, and ambient-variable isolation. |
| Release authenticity | Selected and enabled; publication verification required | Version 3.2.9 uses GitHub's immutable-release attestation for `github.com/EnkratFlow/exocortex-template` and an attested `SHA256SUMS` release asset. The repository setting was verified enabled on 2026-08-08; live GitHub state remains authoritative. |

## Operating decisions

- One accountable parent owns synthesis and delivery. Delegation is optional,
  not a quota.
- The parent selects models without asking for routine approval, announces the
  route and expected timing before substantial work, and changes route when
  evidence warrants it.
- Selection is provider-neutral and based on the expected cost of a correct
  outcome: capability, task risk, ambiguity, tool access, privacy, duration,
  verification strength, and prior failures all matter. The same rule applies
  to subagents.
- Named model products are advisory examples, not permanent normative mappings
  or downstream owner preferences.
- A second reviewer is added only for a genuinely separate risk discipline.

## Publication gates and residual limitations

Before version 3.2.9 may be used as a public installation or update source,
GitHub immutable releases must be enabled, the exact annotated tag and
`SHA256SUMS` asset must be published together, and both the release and asset
verification operations must pass.

The following maintainer- or platform-controlled limitations remain visible
without silently weakening that release gate:

- decide whether to enable GitHub secret scanning, push protection, private
  vulnerability reporting, restricted Actions, and stronger branch rules;
- decide how to handle protected project data already present in old public
  commits and tags; no history rewrite is authorized;
- provide genuine operating-system or broker-enforced network/filesystem
  containment for rehearsal of an untrusted candidate.

Published checksums establish byte consistency only; they do not independently
prove repository-owner authenticity.

## Candidate evidence recorded

- Provider adapter generation: 24 commands and 72 adapters match.
- Focused invocation-policy schema and adapter tests: pass.
- Public-release fictional tree/range, topology, fixture, replacement-object,
  commit/tag metadata, and redaction tests: pass.
- Read-only release-state tests, including annotated-tag and transient-range
  denial: pass.
- Independent security review of routing, authority, release, install, update,
  protected-data, topology, and changed-path boundaries: clean, subject to the
  owner-controlled blockers listed above.
- Active documentation contract: pass.
- Changed shell syntax and Python compilation checks: pass.
- Clean disposable install and guarded dry-run upgrade security test: pass.
- Complete integrity inventory: 269 code-plane checksums and 270 file-mode
  records verify for the exact candidate.
- PR 14's complete GitHub safety suite passed on the reviewed hardening head,
  which was merged as `efb6bbb4ad7cc1ff1da85787fe3a64203fe8e91c`.
- PR 15's complete GitHub safety suite and checksum check passed on exact head
  `9a09c04b99dd2a3fc70d6cf815441be2bc1d5a05`, merged as
  `0cdd18222ec35d918d8ec0589b286b1a265a6a32`. The subsequent tag event correctly
  stopped publication when checkout exposed the peeled commit instead of the
  annotated tag object; the hotfix regression reproduces that live shape.

The complete safety suite is intentionally not run locally on krato. Every
changed release candidate must pass the required GitHub checks on its exact
head. Provider-menu Human UAT has not yet been recorded; historical results
were downgraded to `compatible` because the adapter bytes changed.

## Next verification sequence

1. Require the exact tag-CI hotfix candidate to pass GitHub's `phase-b` and
   `checksums` checks before merge.
2. Replace the unpublished provisional `v3.2.9` tag on the exact hotfix merge,
   require the corrected tag quick check to pass, then publish the tag and
   attested manifest asset and verify the release and asset.
3. Run the read-only release closeout and fresh-tag verification.
4. Use the published README prompt for one bounded downstream operator update;
   do not treat release publication as authority to mutate every repository.

## Start here

- Read [`AI_START_HERE.md`](../../AI_START_HERE.md) for authority and delivery
  rules.
- Read [`MODEL_ROUTING.md`](../control/MODEL_ROUTING.md) for routing policy.
- Read [`AI_INSTALLATION.md`](AI_INSTALLATION.md) before installation or
  upgrade rehearsal.
- Treat this page as stale if its date or evidence no longer matches the live
  repository state; verify Git and release state before acting.
