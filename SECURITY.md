# Security Policy

**Last updated:** 2026-07-24

## Reporting a Vulnerability

Do **not** report security issues in public issues or discussions.

Use one of these private channels:

1. GitHub private vulnerability reporting for this repository (`Security` → `Report a vulnerability`)
2. Email via the EnkratFlow organization contact

Include reproduction steps, impact, and any suggested fix.

## Response Time

We aim to acknowledge new vulnerability reports within **72 hours**.

## Scope: In Scope

- Shell script injection vulnerabilities in:
  - `install.sh`
  - `init-project.sh`
  - `scripts/safe-update.sh`
  - scripts under `.exocortex/scripts/`
- Authority, protected-data, rollback, checksum, or path-validation bypasses
- Secrets accidentally committed to this repository
- Documentation that instructs an AI or human to run an unpinned installer,
  disclose credentials, or combine installation with an unauthorized outward
  action

## Scope: Out of Scope

- Security of credentials independently created and managed by users outside
  the Exocortex installation flow
- Security issues in third-party services (OpenAI, Anthropic, etc.)
- Security issues in a user's project where exocortex is installed

## Security Model and Known Limitations

- Never pipe a remote installer into a shell. Obtain an exact reviewed template
  revision, verify its `SHA256SUMS`, preserve the separately approved manifest
  digest, and execute only that pinned local source.
- Installation does not require an API key and must not read, create, print, or
  modify credential values.
- Rehearse in disposable state with a fake `HOME`. Existing repositories use
  the guarded safe updater, an external restore archive, protected-data hashes,
  idempotency, and verified rollback.
- A coding AI follows the same rules. Provider identity, a slash-command menu,
  repository access, or a conversational “yes” does not grant mutation, Git,
  deployment, external-sync, or template-promotion authority.
- The local guards provide cooperative enforcement. Shell scripts run with the
  invoking user's permissions; a privileged user or unrestricted editor can
  bypass project-local files. Strong host enforcement requires an OS sandbox
  or privileged broker and a trusted signing/attestation root.
- Native Windows is unsupported. WSL remains Human-UAT-pending; do not
  translate the Bash security logic into an unreviewed PowerShell procedure.

## Supported Versions

Only explicitly published supported releases receive security fixes.
Uncommitted candidates, development branches, and unverified platform
translations are unsupported.

## License and Warranty

This project is released under the MIT License and is provided **"as is"**, without warranty of any kind.
