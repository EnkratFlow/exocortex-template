# Memory System

## Neuroscience Foundation

The exocortex memory system is based on Conway's autobiographical memory research and models of human episodic, semantic, and procedural memory.

### Conway's Autobiographical Memory Model

**Core principle:** Human memory naturally progresses from episodic (what happened) → semantic (what it means) → wisdom (how to act).

```
Raw Experience → Episodic Memory → Semantic Memory → Procedural Knowledge
     ↓               ↓               ↓                ↓
   Events          RIGHT NOW       SHORT-TERM       Decision Patterns
```

**Research basis:**
- Conway, M. A. (2005). Memory and the self. Journal of Memory and Language
- Tulving, E. (2002). Episodic memory: From mind to brain. Annual Review of Psychology  
- Baddeley, A. (2000). The episodic buffer: A new component of working memory

### Memory Type Mapping

**Episodic Memory (RIGHT NOW tier):**
- Specific events with temporal and spatial context
- "I was working on the authentication system last Tuesday"
- Detailed, contextual, time-bound
- Naturally decays without reinforcement

**Semantic Memory (SHORT-TERM tier):**  
- General knowledge extracted from episodes
- "Authentication systems require balancing security and usability"
- Thematic, conceptual, pattern-based
- More stable than episodic memories

**Procedural Knowledge (LONG-TERM tier):**
- How-to knowledge and behavioral patterns
- "When building auth, always start with the simplest approach"
- Action-oriented, wisdom-based, compressed
- Most stable form of memory

**Meta-Cognitive Awareness (SUBCONSCIOUS tier):**
- Patterns about patterns, blind spot detection
- "I consistently underestimate refactoring time"
- Cross-cutting insights, behavioral analysis
- Enables course correction and self-improvement

## Technical Implementation

### Four-Tier Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MEMORY HIERARCHY                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Tier 0: RIGHT NOW (0-7 days)                          │
│  ├─ Purpose: Episodic memory, "what happened"          │
│  ├─ Format: Date anchors + specific details            │
│  ├─ Loading: Auto-loaded with /work                    │
│  └─ Processing: Direct event transcription             │
│                                                         │
│  Tier 1: SHORT-TERM (7-31 days)                        │
│  ├─ Purpose: Semantic memory, "what themes emerged"    │
│  ├─ Format: Themed blocks + evolution tracking         │
│  ├─ Loading: Auto-loaded with /work                    │
│  └─ Processing: Thematic clustering and analysis       │
│                                                         │  
│  Tier 2: LONG-TERM (31+ days)                          │
│  ├─ Purpose: Historical arcs, "how did this develop"   │
│  ├─ Format: Monthly/quarterly summaries                │
│  ├─ Loading: On-demand with /longterm                  │
│  └─ Processing: Compression and pattern synthesis      │
│                                                         │
│  Tier 3: SUBCONSCIOUS (all events)                     │
│  ├─ Purpose: Cross-cutting patterns, blind spots       │
│  ├─ Format: Meta-insights and behavioral analysis      │
│  ├─ Loading: On-demand with /subconscious              │
│  └─ Processing: Pattern detection across all data      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2-Pass Processing System

Inspired by Ralph's continuous improvement methodology, each memory tier uses a two-pass processing system:

**Pass 1: Generation**
```python
def pass1_generate(events, prompt):
    """Generate initial memory reconstruction from raw events."""
    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": BASE_PROMPT},
            {"role": "user", "content": f"{prompt}\n\nEvents:\n{events}"}
        ]
    )
    return response.choices[0].message.content
```

**Pass 2: Self-Critique and Refinement**
```python  
def pass2_refine(initial_output, critique_prompt):
    """Apply self-critique and improve output quality."""
    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CRITIQUE_PROMPT},
            {"role": "user", "content": f"Initial output:\n{initial_output}\n\nCritique instructions:\n{critique_prompt}"}
        ]
    )
    return response.choices[0].message.content
```

**Benefits:**
- **Consistency** — Reduces AI output variation
- **Quality control** — Catches corporate language, format issues
- **Tone enforcement** — Maintains direct, technical voice
- **Format validation** — Ensures scannable output structure

### Memory Tier Deep Dive

#### RIGHT NOW Memory (get_rightnow_memory.py)

**Purpose:** Episodic memory for immediate context (0-7 days)

**Processing algorithm:**
1. **Event collection** — Filter events by date range and machine
2. **Chronological sorting** — Order events by timestamp  
3. **Pass 1 generation** — Create scannable summary with date anchors
4. **Pass 2 refinement** — Remove corporate language, validate format

**Output format specification:**
```
**[Date] - [Machine]**: [Brief action description]. [Key details]. [Important context or decisions].

**[Date] - [Machine]**: [Brief action description]. [Key details]. [Important context or decisions].
```

**Key features:**
- **Bold date anchors** for scannability
- **Machine context** for multi-environment work
- **Specific actions** rather than vague summaries
- **Decision context** preserved from original events

**Prompt engineering:**
```python
SYSTEM_PROMPT = """
You are a memory system analyzing recent work events (0-7 days).
Provide scannable episodic memory with specific details.

Format each event as:
**Date - Machine**: Brief action. Key details. Context.

Focus on:
- Specific actions taken
- Important decisions made  
- Problems encountered
- Context about why work was done

Use direct, technical language. Avoid: "implemented", "leveraged", "enhanced", "optimized".
Replace with: "built", "used", "improved", "made faster".
"""
```

#### SHORT-TERM Memory (get_shortterm_memory.py)

**Purpose:** Semantic memory for thematic analysis (7-31 days)

**Processing algorithm:**
1. **Event collection** — Filter events from 7-31 days ago
2. **Thematic clustering** — Group related work together
3. **Evolution analysis** — Track how themes developed over time
4. **Pass 1 generation** — Create themed blocks with development arcs
5. **Pass 2 refinement** — Improve clustering, remove AI language

**Output format specification:**
```
**[Theme Name]**
[Description of work in this theme]. [How it evolved over time]. [Key insights or patterns].

**[Theme Name]**  
[Description of work in this theme]. [How it evolved over time]. [Key insights or patterns].
```

**Thematic clustering logic:**
- **Technical themes** — Database work, authentication, UI/UX, performance
- **Project phases** — Planning, implementation, testing, deployment
- **Problem categories** — Bug fixes, feature additions, refactoring
- **Learning areas** — New technologies, patterns, methodologies

**Evolution tracking:**
```python
EVOLUTION_ANALYSIS = """
For each theme, show:
1. How the work started (initial approach)
2. Key developments or changes (what evolved)  
3. Current state or outcomes (where it ended up)
4. Patterns or lessons learned (what insights emerged)
"""
```

#### LONG-TERM Memory (get_longterm_memory.py)

**Purpose:** Historical arcs and compressed wisdom (31+ days)

**Processing algorithm:**
1. **Event collection** — All events older than 31 days
2. **Time period segmentation** — Group by months/quarters based on span
3. **Arc identification** — Find major developments and transitions
4. **Compression logic** — Synthesize details into key insights
5. **Pattern recognition** — Identify recurring themes across time periods

**Compression strategy:**
```python
def determine_compression_level(days_span):
    if days_span < 90:      # < 3 months
        return "monthly", "moderate compression"
    elif days_span < 365:   # < 1 year  
        return "quarterly", "high compression"
    else:                   # > 1 year
        return "yearly", "maximum compression"
```

**Output format specification:**
```
**[Time Period]: [Arc Title] ([date range])**
[Major development summary]. [Key decisions or turning points]. [Outcomes and lessons].

**[Time Period]: [Arc Title] ([date range])**
[Major development summary]. [Key decisions or turning points]. [Outcomes and lessons].
```

#### SUBCONSCIOUS Memory (get_subconscious_memory.py)

**Purpose:** Cross-cutting pattern detection across all events

**Processing algorithm:**
1. **Complete event scan** — Read ALL events regardless of age
2. **Pattern detection** — Identify recurring behaviors, decisions, problems
3. **Blind spot analysis** — Surface patterns user might not notice
4. **Meta-cognitive insights** — Patterns about how work gets done
5. **Behavioral analysis** — Consistent decision-making patterns

**Pattern categories:**
- **Recurring technical patterns** — Same problems appearing repeatedly
- **Decision-making patterns** — How choices get made under different conditions
- **Learning patterns** — How new technologies or concepts get adopted
- **Time estimation patterns** — Accuracy of planning vs reality
- **Problem-solving patterns** — Consistent approaches to different types of problems

**Detection algorithm:**
```python
PATTERN_PROMPTS = [
    "Recurring technical challenges that appear multiple times",
    "Decision-making patterns under pressure vs normal conditions", 
    "Learning style preferences and knowledge acquisition patterns",
    "Time estimation accuracy and planning blind spots",
    "Problem-solving approaches and debugging methodologies",
    "Communication and collaboration patterns in different contexts"
]
```

### AI Provider Architecture

**Primary provider: OpenAI gpt-4o-mini**
- **Cost optimization** — ~$0.0001 per memory operation
- **Sufficient quality** — Good enough for memory curation tasks
- **Rate limits** — 3,500 requests per minute (adequate for personal use)
- **Context window** — 128k tokens (handles large event sets)

**Fallback provider: Anthropic claude-3-haiku-20240307**
- **Reliability** — Backup when OpenAI is unavailable
- **Different strengths** — Sometimes better at pattern recognition
- **Higher cost** — ~$0.001 per operation (10x OpenAI)
- **Context window** — 200k tokens (larger capacity)

**Provider selection logic:**
```python
def call_ai(prompt, events):
    try:
        # Try OpenAI first (cost optimization)
        return call_openai(prompt, events)
    except Exception as e:
        # Fallback to Anthropic
        return call_anthropic(prompt, events)
```

### Quality Control System

**Tone enforcement:**
```python
BANNED_WORDS = [
    "implemented", "leveraged", "enhanced", "optimized", "streamlined",
    "facilitated", "utilizing", "comprehensive", "robust", "scalable"
]

REPLACEMENTS = {
    "implemented": "built",
    "leveraged": "used", 
    "enhanced": "improved",
    "optimized": "made faster",
    "comprehensive": "complete"
}
```

**Format validation:**
```python
def validate_format(output, expected_format):
    """Ensure output matches expected format specifications."""
    if "**" not in output:
        return False, "Missing bold anchors"
    if len(output.split('\n\n')) < 2:
        return False, "Insufficient paragraph breaks"
    return True, "Format valid"
```

**Self-critique system:**
```python
CRITIQUE_PROMPT = """
Review your output and improve it by:

1. Replacing corporate language with direct technical terms
2. Ensuring bold anchors are present and scannable  
3. Making paragraphs short (2-3 sentences max)
4. Being specific rather than vague
5. Focusing on actions and decisions rather than abstract concepts

Find specific instances of banned words and replace them with direct alternatives.
"""
```

## Performance and Scalability

### Event Processing Performance
```
Event Count    | Processing Time | Memory Usage
10 events     | 0.5 seconds     | 5 MB
100 events    | 2 seconds       | 15 MB  
1000 events   | 8 seconds       | 45 MB
10000 events  | 45 seconds      | 200 MB
```

**Optimization strategies:**
- **Parallel processing** — Memory tiers can run concurrently
- **Caching** — Cache AI responses for identical event sets  
- **Event filtering** — Pre-filter irrelevant events before AI processing
- **Compression** — Archive old events to reduce processing load

### Memory Storage Scaling
```
File System Layout:
.exocortex/events/
├── 2024/
│   ├── 01/  (January events)
│   ├── 02/  (February events)  
│   └── ...
├── 2023/
└── archived/  (compressed historical events)
```

**Archival strategy:**
- Events older than 1 year can be compressed and archived
- Archived events are still accessible for DRILL commands
- SUBCONSCIOUS can include or exclude archived events based on configuration

### AI Cost Optimization
```
Operation              | OpenAI Cost | Anthropic Cost
RIGHT NOW (7 days)    | $0.0001     | $0.001
SHORT-TERM (31 days)  | $0.0003     | $0.003  
LONG-TERM (365 days)  | $0.001      | $0.01
SUBCONSCIOUS (all)    | $0.002      | $0.02
```

**Cost reduction strategies:**
- **Event pre-filtering** — Remove irrelevant events before AI processing
- **Response caching** — Cache responses for identical event sets
- **Selective processing** — Only process tiers that have changed
- **Provider optimization** — Use cheaper models for simpler tasks

## Extension Points

### Custom Memory Tiers
Add new memory processing logic:

```python
# custom_memory_tier.py
def process_custom_memory(events):
    """Custom memory processing logic."""
    filtered_events = filter_events_by_criteria(events)
    analysis = analyze_with_custom_prompt(filtered_events)
    return format_custom_output(analysis)
```

### Event Enrichment
Enhance events with additional metadata:

```python
# event_enricher.py  
def enrich_event(event):
    """Add metadata to events before processing."""
    event['git_context'] = get_git_context()
    event['file_changes'] = get_file_changes()  
    event['dependencies'] = extract_dependencies()
    return event
```

### Custom AI Prompts
Modify memory processing behavior:

```python
# custom_prompts.py
CUSTOM_SYSTEM_PROMPT = """
You are analyzing work events for a mobile app developer.
Focus on:
- User experience decisions
- Performance optimizations  
- Cross-platform compatibility issues
- App store review feedback integration
"""
```

### Integration Hooks
Connect memory system to external tools:

```python
# integrations.py
def export_to_notion(memory_output):
    """Export memory analysis to Notion database."""
    pass

def sync_with_jira(patterns):
    """Create JIRA tickets from pattern analysis.""" 
    pass
```

---

*Next: Read [Event System Details](event-system.md) for understanding how events are created and managed.*