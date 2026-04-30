# What's New in 3.1.2

This release fixes a template command issue where `/ai-export` contained Trading Journal-specific file names. The command is now generic: it discovers the project where Exocortex is installed and builds the export from files that actually exist there.

The installer/update boundary is also stricter. Template-owned code files can update, but project data is never copied from the public template and never tracked in `.exocortex/.install-manifest`.

The public template no longer ships live session context or real checkpoint event files. Fresh installs create local blank stubs instead.

Protected project data includes:

- `.exocortex/events/`
- `.exocortex/SESSION_CONTEXT.md`
- `.exocortex/TODO.md`
- `.exocortex/LESSONS.md`
- `.exocortex/PROJECT_MEMORY.md`

To update an existing install, run this from the project root:

```bash
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash
```

For multiple projects, use the batch updater from a fresh template clone:

```bash
bash scripts/update-all-repos.sh ~/EnkratFlow --dry-run
bash scripts/update-all-repos.sh ~/EnkratFlow
```
