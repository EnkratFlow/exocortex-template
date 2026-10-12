# Exocortex 4.0 migration and acceptance

**Candidate: Exocortex 4.0.0.** This release scope covers project/checkout discovery,
scoped task briefs and saves, optional release awareness, and selected guarded
updates. Candidate metadata is not a published release or consumer installation.

Semantic versioning calls for a major release when supported public behavior is
incompatible. Adding `/help`, `/where` and optional release notices alone would fit
a minor release. The proposed task-memory contract changes existing integrations:

| Change | Migration requirement |
|---|---|
| New event metadata uses scoped work, brief identity and save IDs | Consumers that parse legacy machine/project fields must accept the new schema and retain support for historical events |
| Selected briefs bind exact revisions and checkout identity | Review and explicitly select the intended brief after changing work context |
| Ambiguous or stale brief selection can block saves and context refresh | Resolve the selection first; do not silently save against another task |
| `/work` and `/onboard` focus the selected task and current checkout | Treat project history as scoped evidence; unfinished work is not present everywhere |
| Portable project history travels through Git; runtime state stays local | Review ignore rules, preserved history and synchronization before rollout |

## Migration sequence

1. Inventory installed versions and working folders; select one canonical update
   target per project. Preserve unique notes and events before any consolidation.
2. Preview the exact authenticated release and review local command differences.
   Retain a verified recovery archive and use existing per-target update authority.
3. Validate old events, handwritten context and project-specific instructions after
   installation. Update external event readers before depending on new metadata.
4. Review or create the active brief, select its exact revision and rebuild context
   for this checkout. Historical events are preserved; no bulk rewriting is assumed.
5. Commit and push intentionally shared project memory through the project's normal
   Git workflow. Check another clone after synchronization. Keep runtime observations,
   absolute paths, caches, locks, secrets and personal template-working notes local.

## Release gates still open

The complete safety suite on the exact candidate, native platform CI, independent
review and owner acceptance precede publication. Representative consumer migration
rehearsals must cover a legacy installation, custom commands, saved historical events,
multiple working folders and a synchronized fresh clone. Publication, installation,
memory refresh and application deployment remain separate observable steps.

The broader program still includes deeper shared-history/worktree lifecycle work and
optional operations/connectors. This proposal does not claim those phases complete.
GEPA is a separate experiment and is excluded from this release.

## Customized repositories and multiple checkouts

Before a rollout, record the policy for each exact target checkout. The private
`.exocortex/local/update-policy.json` does not travel through Git. A fresh clone
or sibling worktree has no inherited exclusion and defaults to standard inspection.
Do not treat that default as the owner's decision that an application is standard.
Managed-file comparison detects template changes; it cannot infer external Firebase,
SDLC, infrastructure or non-application requirements. Declare protected exact paths
or use `review_only`/`excluded` and handle that target separately. Other independently
selected standard targets may continue. No force override is provided.

## Evidence and owner acceptance

| Case | Automated evidence required | Owner check before rollout |
| --- | --- | --- |
| Installed controller | Run create, preview, guarded apply and zero-change verification from installed helpers, without the template root manifest | Selection and blocked-target explanations are understandable |
| Legacy installation | Legacy version, leftover commands, manifest/history and protected-memory migration regressions | Review actual project-specific instructions |
| Custom project | Local changes, modified public examples, policy exclusion and policy drift stop execution; standard target remains independent | Declare deployment/SDLC exceptions in every target checkout |
| Shared memory | Old and scoped events, multiple worktrees, fresh clone and CRLF save retry | Open the intended task revision; do not mistake branch history for deployed work |
| Platforms | Complete safety suite, native Windows installation/update and Python3.9/3.13 command runtime | Check provider command menus in the environments actually used |

CI results must identify the exact candidate. Human acceptance is still required;
tests cannot accept the product for its owner. A named OneDrive fixture is not proof
of real synchronized-folder behavior, and WSL retains its separate Human UAT gate.
No real project is enrolled or updated by these fictional rehearsals.
