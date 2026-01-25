# Phase 1: Append-Only Event System

**Goal:** Fix the VS Code + Cursor overwrite problem immediately
**Timeline:** 1-2 days implementation
**Status:** Planned (Ready to implement)

---

## The Problem

Currently, `/save` command updates SESSION_CONTEXT.md in place:
- VS Code runs `/save` → writes "Working on Feature X"
- Cursor runs `/save` → **OVERWRITES** "Feature X" with "Feature Y"
- You lose the VS Code work context

---

## The Solution: Event Files

Instead of updating SESSION_CONTEXT.md, create **append-only event files**:

```
.exocortex/
├── events/
│   ├── 2026-01-25_09-30-15_desktop-vscode.md     # VS Code save
│   ├── 2026-01-25_09-45-22_desktop-cursor.md     # Cursor save (doesn't overwrite!)
│   └── 2026-01-25_14-20-33_laptop-cursor.md      # Laptop save
├── SESSION_CONTEXT.md                             # Generated from events
└── scripts/
    └── generate_context.sh                        # Rebuilds SESSION_CONTEXT
```

**Benefits:**
- No overwrites (each save creates new file)
- Both editors work simultaneously
- Git-friendly (plain Markdown)
- Human-readable timeline
- Foundation for Phase 2 (RAG sync)

---

## Implementation Steps

### Step 1: Create Event Directory Structure
```bash
cd /Users/guyrobo/EnkratFlow/[PROJECT_NAME]
mkdir -p .exocortex/events
mkdir -p .exocortex/scripts
```

### Step 2: Update `.cursorrules` - `/save` Command

**Change from:**
```typescript
// OLD: Update SESSION_CONTEXT.md in place (causes overwrites)
Update 🟢 RIGHT NOW section with user's answer
```

**Change to:**
```typescript
// NEW: Append event file (no overwrites)
1. Get machine ID from env or prompt: "desktop", "laptop", or "trading-server"
2. Get editor from context: "vscode" or "cursor"
3. Create event file: `.exocortex/events/YYYY-MM-DD_HH-MM-SS_machine-editor.md`
4. Write event content (see Event Format below)
5. Run: `.exocortex/scripts/generate_context.sh` (regenerates SESSION_CONTEXT.md)
6. Confirm: "✅ Saved event. Run '/work' to see updated context."
```

### Step 3: Event Format

Each event file uses this structure:

```markdown
<!-- Event Metadata -->
timestamp: 2026-01-25T09:30:15Z
machine: desktop
editor: vscode
project: [PROJECT_NAME]
branch: feat/trade-data-import

---

# Work Focus

Working on Psychological Accountability System - emotional grading of user's trading execution during journal entry flow.

## Git State

**Last Commits:**
- `fc63401` - Fix Trade History and import schema issues
- `008cdb8` - Add Trade History view and fix import counting

**Branch:** feat/trade-data-import

**Uncommitted Changes:**
- server/src/emotionalGrading.ts (new file)
- server/src/index.ts (modified)
- client/src/components/CircuitBreakerModal.tsx (new file)

## Status
In progress

## Notes
Circuit breaker modal complete. Need to test with consecutive losing trades.
```

**Why This Format?**
- Metadata at top (parseable by scripts)
- Human-readable narrative
- Git context preserved
- Easy to scan in editor

### Step 4: Generate Context Script

Create: `.exocortex/scripts/generate_context.sh`

```bash
#!/bin/bash
# Generates SESSION_CONTEXT.md from events/

# Find events from last 7 days (short-term memory)
SEVEN_DAYS_AGO=$(date -v-7d +%Y-%m-%d)  # macOS
# SEVEN_DAYS_AGO=$(date -d "7 days ago" +%Y-%m-%d)  # Linux

# Find all event files within last 7 days
EVENTS=$(find .exocortex/events -name "*.md" -type f -newermt "$SEVEN_DAYS_AGO" | sort -r)

# Count events
EVENT_COUNT=$(echo "$EVENTS" | wc -l | xargs)

echo "Found $EVENT_COUNT events in last 7 days"

# Read template header
cat > .exocortex/SESSION_CONTEXT.md << 'EOF'
# SESSION_CONTEXT – [PROJECT_NAME]

**Last Updated:** $(date +"%B %d, %Y")
**Generated from events:** Last 7 days

---

## 🟢 RIGHT NOW

EOF

# Add events to SESSION_CONTEXT (most recent first)
for EVENT_FILE in $EVENTS; do
    echo "" >> .exocortex/SESSION_CONTEXT.md
    echo "---" >> .exocortex/SESSION_CONTEXT.md
    echo "" >> .exocortex/SESSION_CONTEXT.md

    # Extract metadata
    TIMESTAMP=$(grep "^timestamp:" "$EVENT_FILE" | cut -d' ' -f2)
    MACHINE=$(grep "^machine:" "$EVENT_FILE" | cut -d' ' -f2)
    EDITOR=$(grep "^editor:" "$EVENT_FILE" | cut -d' ' -f2)

    echo "**Event:** $TIMESTAMP ($MACHINE, $EDITOR)" >> .exocortex/SESSION_CONTEXT.md
    echo "" >> .exocortex/SESSION_CONTEXT.md

    # Add event content (skip metadata section)
    sed -n '/^---$/,//p' "$EVENT_FILE" | tail -n +2 >> .exocortex/SESSION_CONTEXT.md
done

# Add footer with older history reference
cat >> .exocortex/SESSION_CONTEXT.md << 'EOF'

---

## 📅 OLDER HISTORY

For work older than 7 days, run: `/history`

Or query RAG API (when Phase 2 implemented):
```bash
curl -X POST http://localhost:3002/api/rag/query \
  -d '{"query": "work from last month", "memory_tier": "long_term"}'
```

EOF

echo "✅ SESSION_CONTEXT.md regenerated from events"
```

**Make executable:**
```bash
chmod +x .exocortex/scripts/generate_context.sh
```

### Step 5: Update `.cursorrules` - `/work` Command

**Change from:**
```typescript
// OLD: Just read SESSION_CONTEXT.md
Read and display SESSION_CONTEXT.md
```

**Change to:**
```typescript
// NEW: Regenerate from events, then display
1. Run: `.exocortex/scripts/generate_context.sh`
2. Read and display SESSION_CONTEXT.md
3. Show event count: "Showing X events from last 7 days"
4. Suggest: "Use `/history` to see older work"
```

### Step 6: Add `/history` Command (Optional, Phase 1.5)

```typescript
// NEW command in .cursorrules
## `/history` - Query Older Work

**Triggers:** "history", "show history", "older work"

**Purpose:** Search events older than 7 days

**Workflow:**
1. Ask: "Search for: [keyword]" or "How far back? [7/30/90/all days]"
2. Search events/ directory with grep or find
3. Display matching events
4. Suggest: "Use RAG API for semantic search (Phase 2)"
```

---

## Migration from Old System

### Preserve Existing SESSION_CONTEXT

**Before implementing:**
```bash
# Backup current SESSION_CONTEXT.md
cp .exocortex/SESSION_CONTEXT.md .exocortex/SESSION_CONTEXT_BACKUP_$(date +%Y%m%d).md

# Convert current state to first event
cat > .exocortex/events/2026-01-25_09-00-00_migration.md << 'EOF'
<!-- Event Metadata -->
timestamp: 2026-01-25T09:00:00Z
machine: desktop
editor: migration
project: [PROJECT_NAME]
branch: feat/trade-data-import

---

# Migration Event: Existing SESSION_CONTEXT

## Work State (Before Event System)

[PASTE ENTIRE "🟢 RIGHT NOW" SECTION FROM BACKUP HERE]

## Status
Migrated from old SESSION_CONTEXT format

EOF
```

**After implementing:**
- New saves create event files
- Old SESSION_CONTEXT.md becomes generated file
- If script breaks, backup still exists

---

## Testing Checklist

### Test 1: No Overwrites
```bash
# In VS Code, run /save
# Answer: "Working on Feature X"
# Check: .exocortex/events/YYYY-MM-DD_HH-MM-SS_desktop-vscode.md exists

# In Cursor, run /save (simultaneously or right after)
# Answer: "Working on Feature Y"
# Check: .exocortex/events/YYYY-MM-DD_HH-MM-SS_desktop-cursor.md exists

# Both files exist → No overwrite ✅
```

### Test 2: Context Regeneration
```bash
# Run /work command
# Should see both events:
# - Event 1: Feature X (vscode)
# - Event 2: Feature Y (cursor)

# SESSION_CONTEXT.md shows timeline ✅
```

### Test 3: Git Workflow
```bash
# Make sure events are tracked in git
git status
# Should show: .exocortex/events/*.md

# Commit events
git add .exocortex/events/
git commit -m "docs: add work events for Jan 25"

# Git history now tracks your work ✅
```

### Test 4: Multiple Machines (If Applicable)
```bash
# On laptop, run /save
# Answer machine prompt: "laptop"
# Check: .exocortex/events/YYYY-MM-DD_HH-MM-SS_laptop-cursor.md exists

# Push to git
git push

# On desktop, pull
git pull

# Run /work
# Should see laptop event in timeline ✅
```

---

## File Organization

### Short-Term (0-7 Days) - Keep in events/
```
events/
├── 2026-01-25_09-30-15_desktop-vscode.md
├── 2026-01-25_09-45-22_desktop-cursor.md
├── 2026-01-25_14-20-33_laptop-cursor.md
└── ... (last 7 days)
```

**Git:** ✅ Commit these (active work)

### Long-Term (7-365 Days) - Move to archive/
```
events/archive/2026/01/
├── 2026-01-18_10-15-00_desktop-vscode.md
└── ... (8-365 days ago)
```

**Git:** ❌ Don't commit (add to .gitignore)
**Access:** Via `/history` command or file browser

### Subconscious (365+ Days) - Delete or deep archive
```
events/archive/2025/
└── ... (older than 1 year)
```

**Git:** ❌ Don't commit
**Access:** Via RAG API (Phase 2) or deleted locally

### Archive Script (Run Monthly)
```bash
#!/bin/bash
# .exocortex/scripts/archive_events.sh

# Move events 7+ days old to archive
find .exocortex/events -name "*.md" -type f -mtime +7 \
    -exec sh -c 'mkdir -p .exocortex/events/archive/$(date -r {} +%Y/%m) && mv {} .exocortex/events/archive/$(date -r {} +%Y/%m)/' \;

echo "✅ Archived events older than 7 days"
```

---

## .gitignore Update

Add to `.gitignore`:
```bash
# Exocortex - keep short-term memory only
.exocortex/events/archive/
.exocortex/SESSION_CONTEXT_BACKUP_*.md
```

**Rationale:**
- Commit last 7 days (active work)
- Don't commit archive (too many files, not needed for collaboration)
- RAG API will store everything (Phase 2)

---

## Quick Reference

### Save Work (Any Time)
```bash
# In Cursor or VS Code
Type: /save
Answer: [Your current focus in one sentence]
Result: Event file created, SESSION_CONTEXT regenerated
```

### View Current Work
```bash
Type: /work
Result: Shows last 7 days of events (all machines, all editors)
```

### Search Older Work
```bash
Type: /history
Search: "authentication" or "last month"
Result: Grep through archived events
```

### Archive Old Events (Monthly)
```bash
cd .exocortex
./scripts/archive_events.sh
git add events/  # Only commits active events
git commit -m "docs: archive old events"
```

---

## What This Solves

✅ **Overwrite Problem:** Multiple editors work simultaneously
✅ **Context Loss:** Timeline preserved in events
✅ **Git History:** Work events tracked in version control
✅ **Human Readable:** Markdown files you can open and read
✅ **Foundation for Phase 2:** Ready to sync to RAG API later

---

## What's Next (Phase 2)

After [PROJECT_NAME] + ExoCenter are done:

1. **RAG API Integration:**
   - `/save` → POST to RAG API (immediate sync)
   - `/history` → Query RAG API (semantic search)
   - Cross-project queries: "Show all authentication work"

2. **Multi-Machine Sync:**
   - Desktop and laptop events sync via RAG API
   - Unified timeline across machines
   - No git push/pull needed

3. **Intelligent Queries:**
   - "What was I working on last Tuesday?"
   - "When did I last work on circuit breaker?"
   - "Show me all work related to emotional grading"

See: [enkratflow-rag-api/docs/plans/CROSS_PROJECT_MEMORY_SYNC_PLAN.md](../../enkratflow-rag-api/docs/plans/CROSS_PROJECT_MEMORY_SYNC_PLAN.md)

---

## Need Help?

**Implementation Questions:**
- How to handle event ID collisions? (Use microseconds in timestamp)
- Should events be YAML or Markdown? (Markdown with YAML frontmatter)
- Git strategy for events? (Commit active, ignore archive)

**Test Before Deploy:**
1. Create backup of SESSION_CONTEXT.md
2. Test `/save` in VS Code
3. Test `/save` in Cursor (same time)
4. Run `/work` → verify both events appear
5. If broken → restore backup

**Rollback Plan:**
If event system doesn't work:
1. Restore SESSION_CONTEXT_BACKUP.md
2. Revert .cursorrules changes
3. Keep events/ directory (useful for debugging)
