# Exocortex File Classification & Upgrade Manifest

> Last updated: Feb 7, 2026 · v1.0
> Source of truth: exocortex-template/.exocortex/ (canonical implementation)

## The Three Planes

```
CODE PLANE (shareable)        → Flows DOWN from template/source to all projects
DATA PLANE (project-local)    → NEVER leaves the project boundary
HUB PLANE  (cross-project)    → Summaries flow UP from projects to hub
```

**Golden rule:** Code flows DOWN. Summaries flow UP. Memory NEVER flows sideways.

---

## CODE PLANE — Safe to Propagate

These files contain infrastructure, not memory. They are identical (or should be)
across all exocortex-enabled projects.

### scripts/ (Python + Bash)

| File | Type | Purpose |
|------|------|---------|
| `get_rightnow_memory.py` | Python | Episodic memory 0-7 days (OpenAI 2-pass) |
| `get_shortterm_memory.py` | Python | Semantic memory 7-31 days (OpenAI 2-pass) |
| `get_longterm_memory.py` | Python | Compressed memory 31+ days (OpenAI 2-pass) |
| `get_subconscious_memory.py` | Python | Cross-cutting pattern detection ALL events |
| `get_subconscious_nudge.py` | Python | DMN nudge — single sentence for /work |
| `drill_memory.py` | Python | Topic-specific deep dive |
| `_api_helpers.py` | Python | Shared API call + error handling module |
| `create_event.sh` | Bash | Create timestamped event file |
| `generate_context.sh` | Bash | Rebuild SESSION_CONTEXT.md from events |
| `archive_events.sh` | Bash | Archive old events |
| `save_work_state.sh` | Bash | Save current state + post to hub |
| `post_to_hub.sh` | Bash | Post summary to ecosystem hub |
| `capture_interrupt.sh` | Bash | Add item to INTERRUPTS.md |
| `groom_interrupts.sh` | Bash | Move interrupts to backlog |
| `detect_work_state.sh` | Bash | Check git/todo state |
| `get_next_task.sh` | Bash | Parse next Ready task from TODO.md |
| `read_memory_stack.sh` | Bash | Read all memory tiers sequentially |
| `run_brief_status.sh` | Bash | Quick status check |
| `run_end_day.sh` | Bash | End-of-day workflow |
| `run_morning_workflow.sh` | Bash | Morning startup workflow |
| `run_scrum.sh` | Bash | Daily standup |

### commands/ (20 JSON specs)

All 20 JSON command specifications:
`ai-export.json`, `brief.json`, `daily-end.json`, `drill.json`,
`ecosystem.json`, `groom.json`, `history.json`, `init-exocortex.json`,
`interrupt.json`, `longterm.json`, `monthly-review.json`, `prioritize.json`,
`refine-backlog.json`, `save.json`, `scrum.json`, `shortterm.json`,
`subconscious.json`, `system-scan.json`, `weekly-review.json`, `work.json`

### docs/ (generic documentation)

| File | Purpose |
|------|---------|
| `SUBCONSCIOUS_ARCHITECTURE.md` | Neuroscience foundations + design |
| `COMMAND_SYSTEM.md` | Command schema reference |
| `architecture.md` | System architecture |
| `memory-system.md` | Memory system design |
| `event-system.md` | Event system reference |
| `EVENT_SYSTEM_USAGE.md` | Event usage guide |
| `user-guide.md` | User guide |
| `vision.md` | Product vision |
| `getting-started.md` | Setup guide |
| `implementation.md` | Implementation notes |
| `roadmap.md` | Product roadmap |

### control/ (structure only — content is project-specific)

| File | Propagate? | Notes |
|------|-----------|-------|
| `README.md` | ✅ YES | Workflow guide (generic) |
| `SNIPPETS.md` | ✅ YES | Command catalog (generic) |
| `DAILY_WORKFLOW.md` | ✅ YES | Workflow instructions (generic) |
| `QA_STRATEGY.md` | ✅ YES | QA approach (generic) |
| `INTERRUPTS.md` | ❌ TEMPLATE ONLY | Content is project-specific |
| `BACKLOG.md` | ❌ TEMPLATE ONLY | Content is project-specific |
| `ROADMAP.md` | ❌ TEMPLATE ONLY | Content is project-specific |
| `ARCH_OVERVIEW.md` | ❌ NO | Project-specific architecture |
| `END_SESSION_PROMPT.md` | ✅ YES | Session end workflow (generic) |
| `REPO_ORGANIZATION_REPORT.md` | ❌ NO | Project-specific |

### Root-level docs (CODE)

| File | Purpose |
|------|---------|
| `MEMORY_TIERS.md` | Memory tier documentation |
| `COMMAND_SYSTEM.md` | Command reference |
| `PERSONA_AND_COMMANDS.md` | Persona + all 20 commands |
| `README.md` | Exocortex overview |
| `AI_BOOTSTRAP.md` | Portable command execution protocol for AI agents |

### reference/ (CODE)

| File | Purpose |
|------|---------|
| `MEMORY.md` | Memory system reference |
| `ESSENTIAL_FILES.md` | File location map (template) |
| `QUICK_REFERENCE.md` | Quick command reference |

---

## DATA PLANE — NEVER Propagate

These files contain project-specific memory, decisions, and state.
**Overwriting these would be memory corruption.**

| File | Why Sacred |
|------|-----------|
| `events/*.md` | Project's autobiographical memory |
| `SESSION_CONTEXT.md` | Current work state |
| `TODO.md` | Active tasks |
| `LESSONS.md` | Project-specific lessons learned |
| `OPEN_DECISIONS.md` | Pending decisions |
| `PROJECT_MEMORY.md` | System constraints and invariants |
| `subconscious_patterns.md` | Cross-session pattern persistence |
| `.env` | API keys (local config) |
| `control/INTERRUPTS.md` | Active interrupts (project-specific) |
| `control/BACKLOG.md` | Investigation items (project-specific) |
| `control/ROADMAP.md` | Strategic plan (project-specific) |
| `control/ARCH_OVERVIEW.md` | Project architecture (project-specific) |

---

## HUB PLANE — EnkratFlow-Project Only

| Location | Purpose |
|----------|---------|
| `hub/activity_stream.txt` | Append-only log from all projects |
| `hub/projects/*.txt` | Last-known-state per project |
| `hub/README.md` | Hub documentation |

---

## Special Case: EnkratFlow-Project

EnkratFlow-Project is the **ecosystem parent**. It receives:
- ✅ All CODE plane files (same as child projects)
- ✅ Hub infrastructure (hub/ directory)
- ✅ Ecosystem-specific commands (may have additional ecosystem commands)
- ✅ Its events CAN reference other projects (that's its job)
- ❌ It does NOT receive other projects' events, TODO, LESSONS, etc.

EnkratFlow-Project's memory IS cross-project by nature — it's the "scrum of scrums"
brain. Its SESSION_CONTEXT.md SHOULD mention all child projects. Its events SHOULD
record ecosystem-level activities. This is not corruption — it's its purpose.

---

## Upgrade Safety Rules

1. **NEVER overwrite a DATA file** — even if the target has an older version
2. **Create directories** that don't exist (commands/, docs/, control/, reference/)
3. **Preserve .env** — never touch it
4. **Preserve events/** — never touch them
5. **Back up before upgrading** — copy current state to .exocortex/archive/pre-upgrade/
6. **Template-only for control/** — if INTERRUPTS.md doesn't exist, create from template; if it exists, don't touch it
7. **Archive AI_INSTRUCTIONS.md** — old projects still have it; archive it, don't delete
