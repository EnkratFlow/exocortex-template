# What's New in 3.1.3

This release removes the last legacy `/save` prompt wording from the template's active command surfaces.

What changed:

- `.claude/skills/save/SKILL.md` is now a thin bridge into `.exocortex/commands/save.json`
- `.exocortex/control/SNIPPETS.md` describes the current event-based `/save`
- `.exocortex/docs/EVENT_SYSTEM_USAGE.md` no longer says `/save` asks for a focus sentence
- The test suite now checks that the old save prompt cannot return

To update an existing install, run this from the project root:

```bash
curl -sL https://raw.githubusercontent.com/EnkratFlow/exocortex-template/main/install.sh | bash
```
