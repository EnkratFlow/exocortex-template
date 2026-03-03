# End Session Prompt Template

**Copy and paste this into Cursor chat to trigger the complete end-of-day workflow:**

```
end session

Please perform the complete end-of-day workflow:

1. Read all memory files:
   - .exocortex/SESSION_CONTEXT.md
   - .exocortex/TODO.md
   - .exocortex/PROJECT_MEMORY.md
   - .exocortex/docs/LESSONS.md
   - .exocortex/OPEN_DECISIONS.md (if exists)
   - .exocortex/control/INTERRUPTS.md (if exists)

2. Review today's work and identify:
   - Completed TODO items
   - New constraints/discoveries
   - Execution slice changes
   - New decisions needed
   - Resolved decisions
   - New lessons learned

3. Propose updates to:
   - SESSION_CONTEXT.md (if execution slice changed)
   - TODO.md (check off completed, add discovered tasks - max 5)
   - PROJECT_MEMORY.md (new constraints if any)
   - LESSONS.md (new lessons if any)
   - OPEN_DECISIONS.md (add new OR remove resolved)

4. Focus on structural changes only, not routine progress updates.

5. Wait for my approval before making changes.
```

## Quick Commands

- **Full workflow:** Type `daily-end` or `end session` in chat
- **Short form:** Just type `end session` or `/daily-end` and the AI follows the command protocol from `.exocortex/AI_BOOTSTRAP.md`

## What Gets Updated

✅ Completed TODO items (check them off)
✅ New constraints discovered (add to PROJECT_MEMORY)
✅ Execution slice changes (update SESSION_CONTEXT)
✅ Resolved decisions (remove from OPEN_DECISIONS)
✅ New lessons learned (add to LESSONS)

## What Does NOT Get Updated

❌ Normal code changes
❌ Bug fixes
❌ Test additions
❌ Routine refactoring

