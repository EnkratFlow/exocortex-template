# Security Policy

**Last updated:** 2026-04-19

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
  - scripts under `.exocortex/scripts/`
- Secrets accidentally committed to this repository
- Cases where the installer downloads and executes unexpected code

## Scope: Out of Scope

- Security of users' own API keys stored locally in `.env` files (gitignored)
- Security issues in third-party services (OpenAI, Anthropic, etc.)
- Security issues in a user's project where exocortex is installed

## Security Model and Known Limitations

- `curl | bash` is convenient but trust-sensitive; review scripts before running in sensitive environments.
- For higher assurance, download the installer and inspect it locally before execution.
- The installer clones from GitHub over HTTPS; verify you trust the source repository.
- API keys are stored in plaintext in local `.env` files; users are responsible for machine-level security.
- Shell scripts run with the invoking user's permissions; no privilege escalation boundary is provided by this project.

## Supported Versions

Only the latest `main` branch is supported for security fixes.

## License and Warranty

This project is released under the MIT License and is provided **"as is"**, without warranty of any kind.
