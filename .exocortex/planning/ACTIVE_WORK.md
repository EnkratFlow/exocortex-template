# Active Work

> Project-local coordination data. The installer and upgrader must not propagate this file to downstream repositories.

| Work item | State | Exact base | Branch | Writer | Next gate |
|---|---|---|---|---|---|
| `EXO-PHASE-B-001` revision 6 | `refined`; C5 local 3.2.0 release-candidate QA/SIT reconciled | Planning base `0eb3c667a505b90c9221ed768d47039a1638df5e`; public-candidate Git base `f87fe7384ca32387772b05d591fbbd18342c458c` | Planning: `codex/exo-phase-b-001-planning`; RC: `codex/exo-phase-b-001-rc2` | None | Separately authorize the exact publication envelope, or complete remaining C5 Human UAT first |
| `EXO-PHASE-B-001-C1` runtime revision 3 | Historical predecessor; runtime remains `developing`, but all C1 authority expired | `d1e1d633097f8223699f3ab424524d31e7f8a26ffc7dd8eead51b343f1724443` | `codex/exo-phase-b-001-planning` | None valid | Preserve as historical evidence; never reuse C1 authority |
| `EXO-PHASE-B-001-C2` runtime revision 27 | `uat_ready`; 12/12 criteria passed; writer released | `SHA256SUMS` `d84985b9e388fcbae32aae015ed83a0dff7f316887d850798d3199d4ee55441d` | `codex/exo-phase-b-001-planning` | Released | Preserve as verified implementation/provider-UAT predecessor |
| `EXO-PHASE-B-001-C3` runtime revision 17 | `human_uat`; 8/8 criteria passed; owner acceptance recorded | `SHA256SUMS` `aca144f7b774aab4099b963694a39d9076b80dd2046ba3bf06689dc1b267ed40` | `codex/exo-phase-b-001-planning` | Released | Accepted public code-plane source for the clean replay |
| `EXO-PHASE-B-001-C4` runtime revision 13 | `human_uat`; 10/10 criteria passed; owner acceptance recorded | C4 `SHA256SUMS` `3f5ed26ac4bf3578b7370af6d2046a6c5704ca72b3ee821bfc37704b1261223f` | `codex/exo-phase-b-001-planning` | Released | Preserve as accepted documentation/release-surface predecessor |
| `EXO-PHASE-B-001-C5` runtime revision 13 | `qa_sit`; AC-01 through AC-09 passed; AC-10 partial/pending | Final 3.2.0 `SHA256SUMS` `963dca709573b799bb17971be3ed6a4ee49508ec65f56ae6fe0ad24a402800b3` | RC: `codex/exo-phase-b-001-rc2` | Released | UAT-1, UAT-3, and UAT-4 remain; publication is a separate business envelope |

## Current authority

- Revision 6 reconciles the C1-C4 predecessor chain with C5 revision 13.
  C5 is evidence-supported through `qa_sit`, not `uat_ready` or
  `release_ready`.
- The final public candidate is the uncommitted, unstaged working tree at
  `/Users/guyrobo/EnkratFlow/exocortex-template-phase-b-rc2`. Its Git HEAD is
  still `f87fe7384ca32387772b05d591fbbd18342c458c`; therefore no immutable
  release commit SHA exists.
- The portable 3.2.0 code-plane binding is `SHA256SUMS`
  `963dca709573b799bb17971be3ed6a4ee49508ec65f56ae6fe0ad24a402800b3`:
  262 valid entries and 263 valid `FILEMODES` bindings.
- The candidate has 264 Git payload paths: 136 modified, 23 intentional
  removals, and 105 untracked manifest-covered files. Zero paths are staged.
- Complete offline verification passed: 118 installer/update groups, 53
  orchestration/routing/egress tests, event tooling, documentation, privacy,
  checksum, file-mode, rollback, replay, idempotency, fault, and restrictive
  `umask` coverage.
- The final evidence manifest is
  `d5800ea95b7b3c099046d882b14fcee95cdb17f4d35bbf733916c7fb693307fd`;
  candidate-tree evidence is
  `693d6ea536a6c9c5df2ff13aaea118896ea6c63d47f71a1f734e70c284e1b6a4`.
  No credentials, live provider, live target, or external synchronization was
  used.
- Independent review is an unconditional PASS with P0/P1/P2 all zero.
- The simplified human approval experience has four business envelopes:
  local delivery, publication, integration/rollout, and production/egress.
  Exact reservations, capabilities, checkpoints, tests, review records, lane
  release, and local handoffs are internal mechanics inside the chosen
  envelope rather than repeated human prompts.
- The owner accepted only R3 UAT-2 semantic behavior. UAT-1 zero-context
  orientation, UAT-3 routing, and UAT-4 Mulligan protections remain pending,
  so C5 AC-10 remains pending.
- The required local C5 handoff is
  `handoff-e291fb5d2eef5f6de5e5b155dfc98bf0`; the writer lane and all C5
  closeout executor registrations are released or expired.
- The disposable Healthy clean install was idempotent, preserved
  `.claude/launch.json`, exposed 24 canonical commands and 72 adapters, and
  passed 112 application plus 37 Functions tests. Functions declares Node 22;
  the available Node 20.20 run is smoke evidence, so exact engine-parity remains
  a future environment check.
- The fictional existing-repository update passed complete 202-path dry-run
  evidence, guarded apply, protected-data comparison, zero-path rerun, and
  rollback without restoring capability authority or AppleDouble sidecars.
- `G3-F01`, `G3-F02`, and `G3-F03` are resolved and revalidated on the clean
  RC. Provider truth is version-scoped: Cursor Stable 3.12.30, Claude Desktop
  1.24012.1 (0adcae), Kimi Code CLI 1.14.0, and Zed 1.12.0 stable.328 built-in
  Agent are verified; Codex and GitHub Copilot are compatible; Kimi Desktop
  3.1.3 is a failed non-default surface; Windsurf is unavailable and excluded
  from default installation; the generic entry makes no native-menu claim.
- Planning/runtime records, real events, identities, sessions, private objects,
  and private planning ancestry did not enter the public candidate.
- The approved base has three deleted operational-event paths in its existing
  reachable history. Their blobs passed the private-marker and high-confidence
  secret-shape scans, but a stricter zero-operational-history rule would require
  a separately approved sanitized root or history rewrite.
- The public `.gitignore` does not by itself prevent every project-local
  planning/event/runtime path from being staged. Exact-path commit review is
  therefore required unless a later approved hardening gate adds a durable
  CI/path-allowlist control.
- The candidate-tree inventory includes linked-worktree `.git` metadata and is
  not a portable tree identity; `SHA256SUMS` is the portable content binding.
- The two ignored generated Python caches were removed; the intentional
  example-event `.synced` fixture remains.
- Current valid writer reservation: none.
- `uat_ready`, `release_ready`, commit, push or PR, merge, release/deployment, live
  installation, service action, external synchronization, template promotion,
  and hypercare acceptance remain unauthorized.

## Reference boundary

- Recorded Mulligan reference identifiers: `50cd1c3db6d69c6d16a68e8935576016b21276b2` and `b63463f784d3e51f47b787e29222bba91dce60e0`.
- Their Git objects are intentionally absent from this repository; only prior privacy-safe audit summaries are bound here. Exact reuse requires separately authorized source inspection or a fictionalized evidence packet.
- These are private evidence pointers. No Mulligan work item, event, personal identifier, absolute path, origin metadata, application-specific content, object, or history is template payload.
- This planning branch and descendants carrying its private planning history
  must never be published directly. The isolated clean replay is the only
  permitted public-candidate route, and it remains local and uncommitted.
