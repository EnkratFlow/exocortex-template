# IDE Integration Guide

Exocortex is editor-neutral. The core command system lives in:

- `.exocortex/AI_BOOTSTRAP.md`
- `.exocortex/commands/*.json`

Cursor, Claude, VS Code, Codex, Zed, Windsurf, and future AI editors should all use the same adapter rule: keep the IDE bridge thin and let the JSON command decide behavior.

## Universal Adapter Prompt

Add this to whatever project instructions, agent rules, system prompt, command snippet, custom mode, or memory file your IDE supports:

```text
When the user types an Exocortex command like /work, /save, /ai-export, work, save, or ai-export:

1. Read .exocortex/AI_BOOTSTRAP.md first.
2. Find .exocortex/commands/{command}.json.
3. Execute the JSON steps in order.
4. The JSON command is the source of truth if any instruction conflicts.
5. Do not invent extra prompts or duplicate command behavior in the adapter.
6. Never read, print, log, echo, or expose secret values.
7. In a multi-root workspace, identify the target repo before running shell steps.
```

## If Slash Commands Are Not Supported

Use this prompt in the AI chat:

```text
Read .exocortex/AI_BOOTSTRAP.md, then run the Exocortex command /work.
```

Replace `/work` with any command, for example `/save`, `/brief`, `/ai-export`, or `/system-scan`.

## Adapter Checklist

- The adapter points to `.exocortex/AI_BOOTSTRAP.md`
- The adapter does not re-implement `/save`, `/work`, or other command behavior
- The adapter says `.exocortex/commands/*.json` is the source of truth
- The adapter preserves the security rule about secrets
- The adapter works from the project root that owns the `.exocortex` folder

## Known Adapter Locations

Different tools use different names for project instructions. Use whichever exists in your editor:

| Tool | Common adapter location |
|------|--------------------------|
| Cursor | `.cursor/commands/*.md`, `.cursor/rules/*.mdc` |
| Claude | `.claude/skills/*/SKILL.md`, `.claude/commands/*.md` |
| VS Code Copilot | `.github/copilot-instructions.md`, `.github/skills/*/SKILL.md` |
| Codex | `.agents/skills/*/SKILL.md`, `AGENTS.md` |
| Windsurf | `.windsurfrules` |
| Zed or another AI editor | Project instructions, agent rules, custom prompt, or command snippets |

If your editor supports only one instruction file, put the Universal Adapter Prompt there. If it supports per-command snippets, each snippet can be a one-line bridge:

```text
Read .exocortex/AI_BOOTSTRAP.md, then execute .exocortex/commands/save.json exactly as written.
```
