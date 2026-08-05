# End Session Prompt Template

Use the provider-native `/daily-end` command. Its sole behavior source is
`.exocortex/commands/daily-end.json`; this page deliberately does not duplicate
that flow.

## Quick Commands

- **Full workflow:** invoke `/daily-end` through the current provider's native
  command/skill surface.
- Ordinary language such as “end session” does not invoke the manual-only
  command by itself.

## What Gets Updated

✅ Completed TODO items (check them off)
✅ New constraints discovered (add to PROJECT_MEMORY)
✅ Execution slice changes (propose a Session Context refresh when useful)
✅ Resolved decisions (remove from OPEN_DECISIONS)
✅ New lessons learned (add to LESSONS)

## What Does NOT Get Updated

❌ Normal code changes
❌ Bug fixes
❌ Test additions
❌ Routine refactoring

The command proposes structural memory changes for review. It does not
silently regenerate Session Context, create preview files, or synchronize
anything.
