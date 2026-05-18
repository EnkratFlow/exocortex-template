# Multi-Tier Memory System

The exocortex uses a four-tier memory architecture inspired by human cognition:

## Tier 0: RIGHT NOW (0-7 days)
**Access:** Shown automatically in `/work` command  
**Granularity:** Full detail  
**Purpose:** Immediate context for decision-making

- Most recent event displayed in full
- Implementation details, status, next steps
- Git state and uncommitted changes
- Refreshed automatically via `generate_context.sh`

## Tier 1: Short-term Memory (7-31 days)
**Access:** `/work` (automatic) or `/shortterm` (on-demand)  
**Granularity:** AI-analyzed bullet points  
**Purpose:** Recent progression and themes

**AI Analysis Shows:**
- **Progression:** How work evolved week-by-week
- **Major Themes:** What areas received focus
- **Completed Work:** Key achievements
- **Patterns:** Recurring approaches or issues

**Script:** `get_shortterm_memory.py`

## Tier 2: Long-term Memory (31+ days)
**Access:** `/longterm` (on-demand only)  
**Granularity:** High-level monthly themes  
**Purpose:** Strategic milestones and evolution

**AI Analysis Shows:**
- **Major Milestones:** Key achievements per month/quarter
- **Recurring Themes:** What kept coming up
- **Evolution:** How work changed over the year
- **Key Lessons:** What was learned

**Script:** `get_longterm_memory.py`

## Tier 3: Subconscious Memory (ALL events)
**Access:** `/subconscious` (on-demand) · Nudge auto-fires in `/work`  
**Granularity:** Cross-cutting pattern detection  
**Purpose:** Surfaces recurring cycles, behavioral patterns, drift, blind spots, contradictions, emotional signatures

**AI Analysis Shows:**
- **Recurring Cycles:** Build → test debt → cleanup → build patterns
- **Behavioral Patterns:** When/where/how you work, productivity rhythms
- **Intention Drift:** What you keep saying you'll do but haven't
- **Emerging Themes:** Topics quietly growing in attention
- **Blind Spots:** What you're not working on that you should be
- **Contradictions:** Stated plans vs actual actions
- **Emotional Signatures:** Frustration, energy, avoidance patterns (Damasio's somatic markers)

**Scripts:** `get_subconscious_memory.py` (full scan) · `get_subconscious_nudge.py` (single-sentence probe)  
**Persistence:** Pattern memory stored in `.exocortex/subconscious_patterns.md` (synaptic consolidation)

---

## AI Provider Configuration

All AI-analyzed tiers use `.exocortex/.env` for API keys:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Priority:**
1. OpenAI `gpt-4o-mini` (fast, cheap ~$0.00015/request)
2. Anthropic `claude-sonnet-4-6` (fallback if OpenAI unavailable)

Each analysis shows which provider was used: `**Analyzed by:** openai`

---

## Memory Compression Strategy

| Tier | Time Range | Events/Period | Detail Level | Auto-Loaded |
|------|-----------|---------------|--------------|-------------|
| 0 | 0-7 days | ~1-10 | Full | ✓ Yes |
| 1 | 7-31 days | ~10-50 | Bullet points | ✓ Yes |
| 2 | 31+ days | ~50-200 | Monthly themes | ✗ On-demand |
| 3 | ALL events | ~1-1000+ | Deep patterns | 💭 Nudge in /work |

**Rationale:** 
- Recent memory (tiers 0-1) shown by default for immediate decision-making
- Older memory (tiers 2-3) on-demand to avoid cognitive overload
- Compression increases with age (mimics human memory decay)

---

## Usage Examples

### Check recent context before starting work:
```bash
/work  # Shows RIGHT NOW + short-term memory
```

### Review last month's progress:
```bash
/shortterm  # 7-31 days with AI analysis
```

### Strategic review of the past year:
```bash
/longterm  # 31+ days with milestones and themes
```

### Deep pattern recognition across years:
```bash
/subconscious  # ALL events — cross-cutting pattern detection (no time filter)
```

---

## Event Format

All memory tiers read from `.exocortex/events/` with format:
```
YYYY-MM-DD_HH-MM-SS_machine-editor.md
```

**Compatible with EnkratFlow Core:** Events use the cognitive ingestion pattern (narrative content + structured metadata) and can sync to Core API for cross-project searchability.

---

## Future Enhancements

- **Cross-project sync:** Push events to EnkratFlow Core (port 3002)
- **Semantic search:** Query memory by concept instead of time range
- **Decay scoring:** Weight recent events higher in search results
- ~~**Emotional extraction:** Track sentiment and psychological patterns~~ ✅ Implemented (emotional signatures in subconscious)
- ~~**Salience tracking:** Identify recurring themes automatically~~ ✅ Implemented (pattern memory persistence)
- **Salience weighting:** Pre-tag events with importance markers for weighted analysis
