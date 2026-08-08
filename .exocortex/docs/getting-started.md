# Getting Started

## New project

You may perform these steps manually or paste the clean-install prompt from
`AI_INSTALLATION.md` into a coding AI with local repository and terminal
access. The same evidence and approval boundaries apply either way.

1. Obtain and review an exact pinned template revision.
2. Verify the committed checksums and bind the accepted SHA-256 of
   `SHA256SUMS` as the candidate digest.
3. Use a sanitized disposable fixture and fake `HOME` for the first rehearsal.
4. Run the local `install.sh`; exercise both preflight rejection and a
   controlled mid-copy failure, then recreate the fixture from its clean base.
5. Verify only expected code-plane files and generic local defaults were added.
6. After one named-target local-apply decision, create a clean isolated Git worktree
   from the exact target HEAD, install and verify there, create the
   permitted local handoff, and release the writer. Internal bootstrap,
   reservation, and technical capability records do not require additional
   human prompts. Never install directly in a shared or primary checkout, and
   never pipe an unpinned remote script.
7. Open a new AI session and ask it to read `AI_START_HERE.md`.
8. Confirm zero-context orientation is read-only and identifies the exact Git
   state, work item, writer status, evidence, and next gate.

## Existing project

Use `scripts/safe-update.sh` with an exact local template, its separately
approved `--candidate-digest`, an explicit disposable backup directory, and
`--dry-run`. First run the metadata-only legacy protected-default preflight in
`.exocortex/docs/AI_INSTALLATION.md`; missing generic scaffolding requires a
guarded internal bootstrap and must never overwrite existing project data.
Approve the disposable rehearsal once, then approve one exact named-target
local apply. That second decision contains bootstrap, reservation, apply,
verification, local handoff, and writer release as internal mechanics. See
`README.md` and
`.exocortex/docs/UPGRADE_MANIFEST.md`. The existing-update prompt and complete
guarded apply command are in `.exocortex/docs/AI_INSTALLATION.md`.

## Platform boundary

The current scripts are verified on macOS with the documented Bash/Unix tools.
Linux is compatible pending the final candidate's Ubuntu CI. WSL requires
separate Human UAT. Git Bash and native Windows PowerShell/Command Prompt are
unsupported; do not translate the installer security logic ad hoc.

## First commands

- `/work`: read-only orientation and next-work options.
- `/onboard`: project-local codebase orientation.
- `/system-scan`: read-only health report.
- `/save`: draft local narrative memory; not a checkpoint.
- `/handoff`: strict local evidence packet; not authority.

Memory commands summarize local evidence with the active conversation model.
They do not discover credentials or call providers directly.

For multi-model delegation, read `.exocortex/control/MODEL_ROUTING.md`.
Parent judgment is the default and applies equally to subagents. The packaged
catalog is advisory and has no eligible models, so the optional formal verifier
cannot route as shipped. New source observations produce quarantine proposals
only; they never activate a model or become an approval gate.

## Safety expectations

- one registered guarded writer;
- deterministic evidence before model judgment;
- one exact business-level envelope per local delivery, publication,
  integration/rollout, or named production/egress outcome;
- internal reservations, technical capabilities, evidence records, handoffs,
  and writer release are not separate human approvals;
- no cross-project, global-editor, service, deployment, or provider change from
  repository installation;
- no automatic external sync;
- no real target testing until disposable clean-install and upgrade rehearsals
  pass and Human UAT is accepted.
