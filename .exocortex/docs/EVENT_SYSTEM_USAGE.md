# Event System - Quick Usage Guide

**Status:** ✅ Implemented and Operational
**Date:** January 25, 2026

---

## What Was Implemented

### Phase 1: Append-Only Event System

The overwrite problem is **SOLVED**. You can now use VS Code and Cursor simultaneously without losing work.

**What Changed:**
- `/save` command now creates **event files** (append-only, no overwrites)
- `/work` command **regenerates** SESSION_CONTEXT from events
- `/history` command searches older events (7+ days)
- **No more overwrites** between editors or machines

---

## File Structure

```
.exocortex/
├── events/
│   ├── 2026-01-25_11-00-00_migration.md          # Your old work (preserved)
│   ├── 2026-01-25_11-15-33_desktop-cursor.md     # New event (current work)
│   └── archive/                                   # Old events (7+ days)
│       └── 2026/01/                               # Organized by year/month
├── scripts/
│   ├── generate_context.sh                        # Regenerates SESSION_CONTEXT
│   └── archive_events.sh                          # Archives old events
├── SESSION_CONTEXT.md                             # Generated from events (last 7 days)
└── SESSION_CONTEXT_BACKUP_20260125.md            # Your backup (safe!)
```

---

## How to Use

### Save Your Work (`/save`)

**In VS Code or Cursor, type:**
```
/save
```

**Current behavior:**
- Reads the current conversation context
- Gathers git state automatically
- Drafts a rich phase checkpoint event without asking extra questions
- Runs the canonical `.exocortex/commands/save.json` steps

**What happens:**
- ✅ Creates event file: `.exocortex/events/YYYY-MM-DD_HH-MM-SS_machine-editor.md`
- ✅ Regenerates SESSION_CONTEXT.md from all events
- ✅ No overwrites - both editors can save simultaneously

**Example:**
```
You in VS Code:  /save → Creates event_A at 10:30 AM
You in Cursor:   /save → Creates event_B at 10:32 AM

Both events exist! ✅
SESSION_CONTEXT shows both ✅
```

---

### View Current Work (`/work`)

**Type:**
```
/work
```

**What happens:**
- ✅ Regenerates SESSION_CONTEXT from events (last 7 days)
- ✅ Shows your active work across all editors/machines
- ✅ Asks: "What would you like to work on?"

**You'll see:**
- Migration event (your previous work)
- Current event (what you just saved)
- Both displayed in timeline order

---

### Search Older Work (`/history`)

**Type:**
```
/history
```

**What happens:**
- Asks: "What do you want to search for?"
- Searches events older than 7 days (long-term memory)

**Examples:**
- Search: "authentication" → Finds all events mentioning authentication
- Search: "last month" → Shows events from last month
- Search: "December" → Shows December events

---

## Scripts Reference

### Regenerate Context
```bash
.exocortex/scripts/generate_context.sh
```
- Reads events from last 7 days
- Regenerates SESSION_CONTEXT.md
- Automatically called by `/save` and `/work`

### Archive Old Events (Monthly)
```bash
.exocortex/scripts/archive_events.sh
```
- Moves events older than 7 days to `archive/YYYY/MM/`
- Keeps active events/ directory clean
- Archived events still searchable via `/history`

---

## Git Strategy

### What Gets Committed:
- ✅ Active events (last 7 days): `.exocortex/events/*.md`
- ✅ Scripts: `.exocortex/scripts/*.sh`
- ✅ Generated SESSION_CONTEXT.md

### What Gets Ignored:
- ❌ Archived events: `.exocortex/events/archive/`
- ❌ Backup files: `.exocortex/SESSION_CONTEXT_BACKUP_*.md`

**Rationale:**
- Commit active work (last 7 days) for collaboration
- Don't commit old events (too many files, not needed)
- RAG API will store everything permanently (Phase 2)

---

## Testing Checklist

### ✅ Test 1: No Overwrites
1. In VS Code: `/save` → Answer: "Working on Feature X"
2. Check: `.exocortex/events/YYYY-MM-DD_HH-MM-SS_desktop-vscode.md` exists
3. In Cursor (immediately after): `/save` → Answer: "Working on Feature Y"
4. Check: `.exocortex/events/YYYY-MM-DD_HH-MM-SS_desktop-cursor.md` exists
5. ✅ Both files exist (no overwrite)

### ✅ Test 2: Context Shows Both Events
1. Run: `/work`
2. Check: SESSION_CONTEXT.md shows both events
3. ✅ Timeline displays correctly

### ✅ Test 3: Scripts Work
1. Run: `.exocortex/scripts/generate_context.sh`
2. Check: SESSION_CONTEXT.md updated
3. ✅ Script completes without errors

---

## Troubleshooting

### "Script not found" Error
```bash
# Make scripts executable
chmod +x .exocortex/scripts/generate_context.sh
chmod +x .exocortex/scripts/archive_events.sh
```

### Date Command Issues (Linux vs macOS)
The scripts auto-detect your OS:
- macOS: Uses `date -v-7d`
- Linux: Uses `date -d "7 days ago"`

If you get date errors, check your OS and update the script's date commands.

### No Events Showing
```bash
# Check events directory
ls -la .exocortex/events/

# Check if migration event exists
cat .exocortex/events/2026-01-25_11-00-00_migration.md

# Manually regenerate context
.exocortex/scripts/generate_context.sh
```

### SESSION_CONTEXT Not Updating
The `/save` and `/work` commands should auto-run `generate_context.sh`. If not:
```bash
# Manually run
.exocortex/scripts/generate_context.sh

# Check if script is executable
ls -l .exocortex/scripts/generate_context.sh
# Should show: -rwxr-xr-x (executable)
```

---

## What's Next (Phase 2)

After you finish Trading App + ExoCenter:

### RAG API Integration
- `/save` → POST to RAG API (immediate sync)
- `/history` → Query RAG semantically
- Cross-project queries: "Show all authentication work"
- Natural language: "What was I working on last Tuesday?"

### Multi-Machine Sync
- Desktop and laptop events sync via RAG API
- Unified timeline across machines
- No git push/pull needed

**Full Vision:** Configure a self-hosted RAG API endpoint in `.exocortex/.env` to enable cross-machine sync. See the [RAG Integration guide](RAG_INTEGRATION.md) for setup instructions.

---

## Summary

✅ **Overwrite Problem:** SOLVED - Each save creates unique file
✅ **Multiple Editors:** VS Code + Cursor work simultaneously
✅ **Timeline Preserved:** All work events in chronological order
✅ **Git-Friendly:** Human-readable Markdown files
✅ **Foundation Ready:** Prepared for RAG API integration (Phase 2)

**Commands:**
- `/save` - Save work event (no overwrites)
- `/work` - View current context (regenerates from events)
- `/history` - Search older work (7+ days)

**Files:**
- Events: `.exocortex/events/*.md`
- Scripts: `.exocortex/scripts/*.sh`
- Context: `.exocortex/SESSION_CONTEXT.md` (generated)

---

**Questions?** See [.exocortex/PHASE_1_EVENT_SYSTEM_PLAN.md](.exocortex/PHASE_1_EVENT_SYSTEM_PLAN.md) for detailed implementation guide.
