# Exocortex release status

Last updated: 2026-08-08

This is the living, human-readable maintainer view of where the public template
stands. It is release-scoped, not a downstream project's status page, owner
preference, approval record, release claim, or replacement for test evidence.

## Published baseline

- The latest published baseline is `v3.2.8` at commit
  `cd577ab633ac3c8edff52cc2128e986f1ad2785d`.
- The `3.2.9` hardening work described below is an unreleased candidate. This
  page does not claim that it has been merged, published, installed into a
  downstream repository, or used to rewrite public history.

## Candidate state

| Area | State | Current objective |
| --- | --- | --- |
| Model routing | Implemented; focused checks pass | Accountable-parent judgment is the default, with formal routing retained as optional evidence rather than an approval gate. |
| Subagents | Implemented; focused checks pass | The same correct-model-for-the-job and cost-of-correct-outcome judgment applies to every delegate. |
| Command adapters | Focused checks pass | 11 bounded read-only commands are model-discoverable and 13 human-controlled commands remain manual-only; all authority boundaries remain. |
| Public-release safety | Focused checks and independent review pass | The checker rejects protected data, unsafe topology, redacted secret-shaped paths/content/commit/tag metadata, replacement-object history, modified public fixtures, and transient candidate data. |
| CI and integrity | Focused checks and inventories pass | Every pull request produces the required check, push/tag ranges fail closed, the public boundary runs in CI, third-party Actions are pinned, and the exact code-plane checksum and mode inventories are verified. |
| Upgrade/install path | Focused security rehearsal passes | Clean install plus guarded dry-run upgrade passed in disposable fixtures, including source races, import-shadow denial, rsync/tar denial, protected environment preservation, rollback exclusion, and ambient-variable isolation. |

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

## Known release blockers

The candidate cannot by itself settle these maintainer- or GitHub-controlled
decisions:

- choose and provision release authenticity evidence, such as signed tags or
  GitHub artifact attestations, including the trust identity and revocation
  procedure;
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

The complete safety suite has not been run locally, and no CI or provider-menu
Human UAT evidence exists for this candidate yet. Historical provider-menu
results were downgraded to `compatible` because the adapter bytes changed.

## Next verification sequence

1. Let CI run the complete safety suite for an exact branch candidate.
2. Prepare provider-menu and operator Human UAT.
3. Resolve the maintainer- and GitHub-controlled release blockers above.
4. Do not publish or
   roll out to downstream repositories without a new explicit delivery scope.

## Start here

- Read [`AI_START_HERE.md`](../../AI_START_HERE.md) for authority and delivery
  rules.
- Read [`MODEL_ROUTING.md`](../control/MODEL_ROUTING.md) for routing policy.
- Read [`AI_INSTALLATION.md`](AI_INSTALLATION.md) before installation or
  upgrade rehearsal.
- Treat this page as stale if its date or evidence no longer matches the live
  repository state; verify Git and release state before acting.
