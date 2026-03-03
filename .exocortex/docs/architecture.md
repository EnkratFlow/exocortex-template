# Architecture

## System Overview

The exocortex is a file-based system that integrates with AI assistants to provide persistent context and intelligent memory retrieval. It operates through three main subsystems working in concert.

```
┌─────────────────────────────────────────────────────────────┐
│                     EXOCORTEX ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │   COMMAND    │    │   MEMORY    │    │    EVENT     │   │
│  │   SYSTEM     │◄──►│   SYSTEM    │◄──►│   SYSTEM     │   │  
│  │              │    │             │    │              │   │
│  └──────────────┘    └─────────────┘    └──────────────┘   │
│         │                    │                   │         │
│         │                    │                   │         │
│         ▼                    ▼                   ▼         │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────┐   │
│  │ AI Assistant │    │ Memory APIs │    │ File Storage │   │
│  │ Integration  │    │ (OpenAI/    │    │ (.md files) │   │
│  │ (User Rules/ │    │ Anthropic)  │    │              │   │
│  └──────────────┘    └─────────────┘    └──────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Event System
**Purpose:** Append-only storage of work sessions  
**Location:** `.exocortex/events/`  
**Format:** `YYYY-MM-DD_HH-MM-SS_machine-editor.md`

**Architecture:**
- **Append-only** — Events are never modified, only created
- **Machine-scoped** — Events capture which environment was used
- **Editor-aware** — Different editors create separate event streams
- **Time-ordered** — Natural chronological sorting by filename

**Key Scripts:**
- `create_event.sh` — Records new work sessions
- `generate_context.sh` — Aggregates events into session context
- `archive_events.sh` — Manages event storage lifecycle

### 2. Memory System
**Purpose:** AI-curated multi-tier memory retrieval  
**Location:** `.exocortex/scripts/get_*_memory.py`

**Four-Tier Architecture:**

```
Tier 0: RIGHT NOW (0-7 days)     │ Auto-loaded │ Full detail
        ↓                        │             │
Tier 1: SHORT-TERM (7-31 days)   │ Auto-loaded │ Themed blocks  
        ↓                        │             │
Tier 2: LONG-TERM (31+ days)     │ On-demand   │ Monthly arcs
        ↓                        │             │
Tier 3: SUBCONSCIOUS (all events)│ On-demand   │ Pattern detection
```

**Memory Processing Pipeline:**
1. **Event Collection** — Mechanical gathering from `.exocortex/events/`
2. **AI Analysis** — Two-pass prompt processing with self-critique
3. **Format Curation** — Scannable output with bold anchors
4. **Context Integration** — Ready for consumption by command system

**Key Innovation:** Each tier uses a **2-pass Ralph-style loop**:
- Pass 1: Generate memory reconstruction from raw events
- Pass 2: Self-critique for format, tone, and completeness

### 3. Command System  
**Purpose:** Structured workflow automation  
**Location:** `.exocortex/commands/*.json`

**Execution Flow:**
```
User types "/work" → AI reads work.json → Executes steps → Auto-verifies → Shows brief
```

**Command Specification Format:**
```json
{
  "name": "/command",
  "description": "What this command does",
  "steps": [
    {
      "type": "shell|ai",
      "command": "script to run",
      "description": "Human-readable step name",
      "success_format": "✓ Template for success message"
    }
  ]
}
```

**Current Commands:**
- `/work` — Context loading and task identification
- `/drill <topic>` — Deep-dive memory reconstruction  
- `/shortterm` — 7-31 day memory analysis
- `/longterm` — 31+ day memory analysis  
- `/subconscious` — Cross-cutting pattern detection

## Data Flow Architecture

### 1. Context Generation Flow
```
Work Sessions → Events → Context Generation → Memory Tiers → Command Briefings
```

1. **Session Capture** — Developer works, creates events via `/save` or automatic triggers
2. **Event Storage** — Append-only `.md` files with structured metadata
3. **Context Aggregation** — `generate_context.sh` builds `SESSION_CONTEXT.md`
4. **Memory Analysis** — AI processes events into memory tiers
5. **Command Integration** — Memory surfaces in `/work` and other commands

### 2. Memory Retrieval Flow
```
Command Trigger → Event Query → AI Processing → Format Output → User Display
```

1. **Event Selection** — Scripts filter events by time window or criteria
2. **AI Invocation** — Raw events sent to OpenAI/Anthropic with specialized prompts
3. **Two-Pass Processing** — Generate → Self-critique → Refine → Output
4. **Format Standardization** — Bold anchors, short paragraphs, scannable structure

### 3. AI Integration Flow
```
User Rule → AI_BOOTSTRAP.md → Command Recognition → JSON Spec → Step Execution → Auto-verification
```

1. **Command Recognition** — AI assistant recognizes `/command` patterns
2. **Spec Loading** — `.exocortex/commands/command.json` provides execution plan
3. **Step Processing** — Scripts run in sequence with auto-verification
4. **Output Formatting** — Structured response with success indicators

## File System Architecture

```
.exocortex/
├── .env                    # API keys for AI providers
├── commands/               # JSON command specifications  
│   ├── work.json          # Main context loading command
│   ├── drill.json         # Deep-dive memory reconstruction
│   └── *.json             # Other workflow commands
├── scripts/               # Processing and utility scripts
│   ├── generate_context.sh    # Event → context aggregation
│   ├── get_*_memory.py         # Memory tier processors (Python + OpenAI)
│   ├── create_event.sh         # Session recording
│   └── detect_work_state.sh    # Git state analysis
├── events/                # Append-only event storage
│   └── YYYY-MM-DD_HH-MM-SS_machine-editor.md
└── *.md                   # Documentation and context files
```

## Technical Architecture Decisions

### Language Choices
- **Python for memory scripts** — Better string handling, JSON processing, API calls
- **Bash for utilities** — System integration, file operations, git commands  
- **JSON for specifications** — Human-readable, AI-parseable command definitions
- **Markdown for storage** — Readable, versionable, editor-agnostic

### AI Provider Architecture
**Primary:** OpenAI `gpt-4o-mini` (~$0.0001/call)  
**Fallback:** Anthropic `claude-3-haiku-20240307`

**Rationale:**
- Cost optimization for frequent memory operations
- Dual-provider redundancy for reliability  
- Consistent prompt format across providers
- Quality sufficient for memory curation tasks

### File Format Decisions
**Event files:** Structured markdown with YAML frontmatter  
**Memory output:** Markdown with bold anchor formatting  
**Commands:** JSON with shell/AI step types  

**Benefits:**
- Human-readable for debugging and manual inspection
- Version control friendly (line-based diffs)
- Editor-agnostic (work in any text editor)
- AI-parseable (natural language + structured data)

### Memory Architecture Design

**Four-tier system** based on Conway's autobiographical memory research:
- Mirrors natural human memory compression
- Auto-loading for immediate relevance (0-31 days)
- On-demand for historical context (31+ days)
- Cross-cutting pattern detection (subconscious)

**2-pass processing** inspired by Ralph continuous improvement:
- Pass 1: Generate from raw events
- Pass 2: Self-critique and refinement
- Improves consistency and reduces AI drift

### Integration Architecture

**AI Assistant Integration:** Via Cursor user rules (Settings > General > Rules for AI) or manual prompt to read `.exocortex/AI_BOOTSTRAP.md`  
**Multi-editor Support:** Command system works in Cursor, VS Code, Claude Desktop  
**Multi-machine Sync:** Event-based append-only model prevents conflicts

## Scalability Considerations

### Event Storage
- Events older than 1 year can be archived without affecting performance
- Compression strategies available for large event histories
- File-based storage scales to thousands of events without performance issues

### AI Processing  
- Memory tier processing is independent (can be parallelized)  
- Cost scales linearly with event count (no exponential growth)
- Caching strategies available for frequently accessed memory tiers

### Multi-User Extensions
Architecture supports future team features:
- Shared event streams
- Cross-developer pattern detection  
- Collaborative context preservation

---

*The architecture prioritizes simplicity, observability, and human control — every component can be inspected, modified, or bypassed as needed.*