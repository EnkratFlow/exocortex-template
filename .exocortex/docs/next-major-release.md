# Proposed next major release

**Recommendation: Exocortex 4.0.0 for the completed, validated program.** This is a
release proposal, not a version bump or published release. `VERSION` remains the
current baseline until release scope and migration checks are accepted.

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
GEPA remains deferred. If the final release excludes the incompatible changes or adds
full compatibility, reassess a minor release instead of assigning 4.0 by feature count.
