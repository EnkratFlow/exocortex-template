# Phase 2 Transition Plan: Git → RAG API

**Timeline:** 1-2 months from now (after [PROJECT_NAME] + [OTHER_PROJECT] complete)
**Purpose:** Switch from git-based event sync to RAG API-based sync

---

## Current State (Phase 1)

**How Sync Works:**
- Events committed to git: `.exocortex/events/*.md`
- Machines pull/push to sync
- ALL events tracked (active + archived)
- ~600 files over 2 months (~600KB)

**Why This Works:**
- Simple (just git push/pull)
- Full cross-machine sync
- Low overhead (600KB is nothing)
- Safe (git version control)

---

## Future State (Phase 2)

**How Sync Will Work:**
- Events stored in RAG API (ChromaDB)
- `/save` → POST to RAG API (immediate sync)
- Machines query RAG for history
- Git no longer needed for events

**Benefits:**
- Semantic search: "What did I work on related to authentication?"
- Cross-project queries: "Show all RAG API work"
- Natural language: "What was I doing last Tuesday?"
- No git clutter (events stay in RAG API)

---

## Transition Steps

### Step 1: Implement RAG API Integration (Week 1-2)

**Files to Create:**
- `.exocortex/scripts/sync_to_rag.sh` - Sync event to RAG API
- `.exocortex/scripts/import_events_to_rag.sh` - Bulk import existing events

**Update .cursorrules:**
- `/save` command → Also POST to RAG API
- `/history` command → Query RAG API (fallback to local grep)

**Test:**
- Save event → Appears in RAG API
- Query RAG → Returns event
- Offline work → Queues for sync

### Step 2: Backfill Historical Events (Week 2)

**Import all existing events to RAG API:**
```bash
# One-time bulk import
.exocortex/scripts/import_events_to_rag.sh

# Imports all events from:
# - .exocortex/events/*.md (active)
# - .exocortex/events/archive/**/*.md (archived)

# To RAG API with metadata:
# - memory_tier: short_term / long_term / subconscious
# - project: [PROJECT_NAME]
# - machine: [detected]
# - timestamp: [from event file]
```

**Verify:**
```bash
# Test RAG query
curl -X POST http://localhost:3002/api/rag/query \
  -d '{"query": "work from last week", "memory_tier": "short_term"}'

# Should return events ✅
```

### Step 3: Parallel Operation (Week 3-4)

**Run both systems simultaneously:**
- ✅ Events still committed to git
- ✅ Events also synced to RAG API
- Test RAG queries vs git history
- Verify no data loss

**Update .gitignore (prepare for Phase 3):**
```bash
# .gitignore - Phase 2 (Parallel Mode)
# Still tracking events, but preparing to stop

# Exocortex - Event System (Phase 2: Parallel Git + RAG)
# Events tracked during transition, will stop in Phase 3
.exocortex/SESSION_CONTEXT_BACKUP_*.md
```

### Step 4: RAG-Only Mode (Week 5+)

**Stop committing events:**

**Update .gitignore:**
```bash
# Exocortex - Event System (Phase 3: RAG-Only)
# All events now stored in RAG API, no need for git tracking
.exocortex/events/
.exocortex/SESSION_CONTEXT_BACKUP_*.md
```

**Update .cursorrules:**
- `/save` → POST to RAG API (no local file creation, or create but don't commit)
- `/work` → Query RAG API for last 7 days
- `/history` → Query RAG API (no local grep)

**Migration:**
```bash
# Move existing events to archive (one-time)
mkdir -p .exocortex/events_git_archive
mv .exocortex/events/* .exocortex/events_git_archive/

# Update git
git rm -r .exocortex/events/
git commit -m "migrate: move events to RAG API (see .exocortex/events_git_archive)"

# Keep local archive for reference
# (git-ignored, but you still have them)
```

---

## Rollback Plan

**If RAG API has issues:**

**Step 1: Check RAG API**
```bash
curl http://localhost:3002/health
# If down → Events queued locally
```

**Step 2: Use Local Events as Fallback**
```bash
# /save and /work fall back to local files
# Queue syncs to RAG API for later
```

**Step 3: Re-enable Git Tracking (Emergency)**
```bash
# Revert .gitignore
git checkout .gitignore

# Commit local events
git add .exocortex/events/
git commit -m "rollback: re-enable git tracking for events"
```

---

## Validation Checklist

### Before Phase 2 Transition:
- [ ] [PROJECT_NAME] complete
- [ ] [OTHER_PROJECT] complete
- [ ] RAG API stable and tested
- [ ] `/save` → RAG API integration working
- [ ] `/history` → RAG queries working
- [ ] Cross-project queries tested

### During Transition (Parallel Mode):
- [ ] All events synced to RAG API
- [ ] Historical events imported (backfill)
- [ ] RAG queries return correct results
- [ ] No data loss (git and RAG match)
- [ ] Offline queue working

### After Transition (RAG-Only):
- [ ] Events no longer committed to git
- [ ] `.exocortex/events/` in .gitignore
- [ ] RAG API is source of truth
- [ ] Cross-machine sync via RAG works
- [ ] No performance issues
- [ ] `/history` semantic search working

---

## Cost Estimate (RAG API)

**Storage:**
- 600 events × 1KB = 600KB (negligible)
- ChromaDB handles millions of documents

**API Calls:**
- `/save`: 10/day × 30 days = 300 calls/month
- `/history`: 5/day × 30 days = 150 calls/month
- Total: ~450 queries/month
- Cost: ~$5-10/month (assuming pro tier)

**Worth it for:**
- Semantic search
- Cross-project queries
- Natural language history
- No git clutter

---

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** (Current) | 1-2 months | Git-based sync, all events tracked |
| **Phase 2** (Transition) | 2-4 weeks | Parallel: Git + RAG API |
| **Phase 3** (Future) | Ongoing | RAG-only, stop git commits |

**Total time to RAG-only:** 3-4 months from now

---

## Related Documents

- [CROSS_PROJECT_MEMORY_SYNC_PLAN.md](../../enkratflow-rag-api/docs/plans/CROSS_PROJECT_MEMORY_SYNC_PLAN.md) - Full vision
- [PHASE_1_EVENT_SYSTEM_PLAN.md](PHASE_1_EVENT_SYSTEM_PLAN.md) - Current implementation
- [EVENT_SYSTEM_USAGE.md](EVENT_SYSTEM_USAGE.md) - How to use Phase 1

---

**Next Steps:**
1. Finish [PROJECT_NAME] + [OTHER_PROJECT] (1-2 months)
2. Implement RAG API integration (2-4 weeks)
3. Transition to RAG-only mode (ongoing)
