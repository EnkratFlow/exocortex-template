# Subconscious Architecture — Neuroscience Foundations & Design

> Last updated: Feb 7, 2026 · v1.0

## Why This Document Exists

The exocortex memory system models human cognition. Tiers 0–2 (RIGHT NOW, SHORT-TERM, LONG-TERM) map cleanly to Conway's autobiographical memory model: episodic → semantic → procedural. But the **subconscious** is not a memory tier at all — it's a **parallel processing mode**. This document explains the neuroscience behind real human subconscious processing, how our implementation maps to it, where the gaps are, and the roadmap for closing them.

---

## 1. Neuroscience of the Human Subconscious

### 1.1 The Default Mode Network (DMN)

When you stop actively working — walking to the kitchen, staring out the window, taking a shower — your brain doesn't go idle. The **Default Mode Network** activates. This is a set of brain regions (medial prefrontal cortex, posterior cingulate, angular gyrus) that:

- Replays recent experiences against older memories
- Tests "what-if" recombinations you never consciously considered
- Produces the "aha" moments that arrive when you're not trying

The DMN runs **involuntarily**. You don't choose to activate it. It fires in the gaps between focused attention.

**Our mapping:** Currently, `/subconscious` must be explicitly invoked. This is like asking someone to "be spontaneous" — it defeats the purpose. The DMN's power comes from being unbidden.

### 1.2 Implicit Pattern Detection (Basal Ganglia)

The basal ganglia perform **statistical learning** — tracking frequencies, sequences, and co-occurrences that the conscious mind never registers. A trader develops "gut feel" for a setup not through deliberate analysis but through thousands of unconscious exposures. The basal ganglia notice:

- This sequence of events has happened 4 times before
- These two things always appear together
- This pattern used to happen weekly but stopped 3 weeks ago

This is **bottom-up** processing. The data talks. The conscious mind just receives a vague "something feels off" signal.

**Our mapping:** The 6 detection categories in `get_subconscious_memory.py` align well with this:

| Basal Ganglia Function | Our Detection Category |
|---|---|
| Frequency tracking | Recurring cycles |
| Sequence detection | Behavioral patterns |
| Expectation violation | Intention drift |
| Co-occurrence tracking | Emerging themes |
| Absence detection | Blind spots |
| Conflict monitoring | Contradictions |

### 1.3 Somatic Markers (Damasio's Theory)

Antonio Damasio's somatic marker hypothesis: the brain tags memories with **emotional valence** — a felt sense of good/bad/dangerous/safe. When you encounter a similar situation later, the body reactivates that marker before conscious reasoning kicks in. This is the neurological basis of "gut feelings."

Key properties:
- Markers are **attached to specific experiences**, not abstractions
- They compress complex evaluations into simple approach/avoid signals
- They're strongest for **high-stakes decisions with uncertain outcomes** (trading is the perfect domain)

**Our mapping:** Currently missing. The subconscious prompt doesn't ask the AI to detect emotional valence or weight events by their emotional significance. All events are treated as equally important.

### 1.4 Anterior Cingulate Cortex — Error Monitoring

The ACC acts as the brain's **conflict detector**. It fires when:
- Current behavior contradicts stated goals
- Two active plans are incompatible
- Expected outcomes don't match actual outcomes

It doesn't resolve the conflict — it just raises the alarm. Resolution happens in prefrontal cortex (conscious deliberation).

**Our mapping:** The 2-pass Ralph-style self-critique in our script is structurally similar. Pass 1 generates patterns. Pass 2 checks for quality, specificity, and banned language — essentially error-monitoring the first pass's output. This is actually one of the strongest design elements.

### 1.5 Synaptic Consolidation — Memory Strengthening

Repeated activation of the same neural pathway strengthens it. In sleep (particularly REM), the hippocampus replays the day's events, and patterns that were activated multiple times get consolidated into long-term storage. Patterns that were activated only once fade.

**Critical property:** This means the subconscious should **remember its own previous observations**. If it detected "intention drift on committing files" three sessions in a row, that pattern should be STRONGER the fourth time — not rediscovered from scratch.

**Our mapping:** Currently missing. Each `/subconscious` invocation is stateless. The AI re-scans all events from zero every time. It has no memory of what it found before.

---

## 2. Current Implementation

### 2.1 Architecture

```
/subconscious command
    │
    ▼
get_subconscious_memory.py
    │
    ├── Reads ALL events from .exocortex/events/*.md (no time filter)
    ├── Builds full context string with metadata (dates, machines, content)
    ├── Sends to OpenAI gpt-4o-mini (fallback: Claude Haiku)
    │
    ├── PASS 1: Pattern detection prompt
    │   └── System: "You are the SUBCONSCIOUS — a pattern detection engine"
    │   └── 6 detection categories (cycles, behavior, drift, themes, blind spots, contradictions)
    │   └── Voice guidance: "quiet, observant, slightly detached"
    │   └── Banned word list (comprehensive, robust, streamline, etc.)
    │
    └── PASS 2: Ralph-style self-critique
        └── Quality rules: specificity, evidence, non-obviousness
        └── Banned word replacement map
        └── "If a pattern is too obvious or unsupported, cut it and replace"
```

### 2.2 What Works Well

**Prompt engineering quality is high.** The system prompt is specific about what the subconscious *should* and *should not* do:

- "You do NOT reconstruct what happened (that's what the other tiers do). You detect what the person HASN'T NOTICED."
- "If it's obvious, don't say it. Find the patterns hiding in plain sight."
- Banned word list prevents corporate AI-speak
- Voice guidance creates appropriate tone ("like a therapist's notes — not judging, just noticing")

**2-pass self-critique is genuinely valuable.** Maps to the ACC error-monitoring function. Catches vague observations, unsupported claims, and banned language.

**All-events scope is correct.** The subconscious reads every event regardless of age. This is the right design — pattern detection needs the full dataset.

### 2.3 Six Detection Categories

1. **Recurring cycles** — Repeated sequences (build → test debt → cleanup → build)
2. **Behavioral patterns** — When/where/how you work, productivity rhythms
3. **Intention drift** — Gap between stated plans and actual actions
4. **Emerging themes** — Topics quietly growing in attention
5. **Blind spots** — Things not being worked on that should be
6. **Contradictions** — Stated priorities vs. actual behavior

---

## 3. Gaps Between Current Design and Neuroscience

### Gap 1: Voluntary vs. Involuntary Activation

| Human Brain | Current System |
|---|---|
| DMN fires automatically in gaps | Must explicitly run `/subconscious` |
| Produces unbidden insights | Produces a full report on demand |
| Single fragment surfaces at a time | Entire analysis delivered at once |

**The problem:** Real subconscious insights are fragments that surface involuntarily. Our system produces a full analytical report only when explicitly asked. This is closer to a therapist session than actual subconscious processing.

### Gap 2: No Cross-Session Persistence

| Human Brain | Current System |
|---|---|
| Repeated patterns get stronger (synaptic consolidation) | Each scan is stateless |
| "Seen 4 times" hits harder than "seen once" | All patterns treated as new discoveries |
| Sleep consolidation strengthens important patterns | No persistence between runs |

**The problem:** If the subconscious detects "you keep postponing commit cleanup" three sessions in a row, the third detection should carry more weight. Currently it re-discovers from scratch each time.

### Gap 3: No Salience Weighting

| Human Brain | Current System |
|---|---|
| Amygdala tags high-stakes moments | All events equally weighted |
| Emotional events remembered more strongly | No affect metadata on events |
| Near-miss experiences leave strong markers | Wins and losses treated the same |

**The problem:** A trading blowup should weigh more than a routine documentation update. Currently, the AI must infer importance from text alone — it has no pre-tagged salience signals.

### Gap 4: No Emotional Valence Detection

| Human Brain | Current System |
|---|---|
| Somatic markers tag experiences with felt sense | Prompt doesn't ask about emotional tone |
| "Something feels off" as early warning | Only structural pattern detection |
| Approach/avoid signals from past experience | No affect tracking |

**The problem:** The prompt asks for structural patterns (cycles, drift, contradictions) but not emotional ones. "You seem frustrated every time you touch the test suite" is a subconscious insight that the current categories don't capture.

### Gap 5: Report Mode vs. Fragment Mode

| Human Brain | Current System |
|---|---|
| Subconscious surfaces single fragments | Always produces full 4-7 pattern report |
| Brief flash of insight during other activity | Only runs as standalone command |
| Sometimes just a feeling, not a formed thought | Always produces complete sentences |

**The problem:** Two modes should exist: (1) involuntary fragment mode — a single sentence that surfaces during `/work`, and (2) voluntary deep scan — the current full analysis. Only mode 2 exists.

---

## 4. Improvement Roadmap

### Phase 1: Involuntary Nudge (HIGH priority)

**What:** Add a single-sentence subconscious probe to the `/work` command flow. When `/work` loads context, it also runs a lightweight subconscious check that produces ONE fragment — not a full analysis.

**Neuroscience mapping:** Default Mode Network activation. The insight arrives without being asked for.

**Implementation:**
- Create `get_subconscious_nudge.py` — lightweight version of the full script
- Reads last ~20 events (not all), uses a shorter prompt
- Produces exactly ONE sentence: a pattern observation, a question, or a gut-feeling signal
- Output format: `💭 [single sentence]` — displayed at the bottom of the `/work` brief
- Add as step in `work.json`

**Example outputs:**
- `💭 You've mentioned "commit cleanup" in 4 sessions without doing it.`
- `💭 Last three sessions started on server/ but drifted to docs/ within an hour.`
- `💭 You work longer sessions on the Mac Mini but get more done on shorter ones.`

### Phase 2: Pattern Memory File (HIGH priority)

**What:** Create `.exocortex/subconscious_patterns.md` — a persistent file where the subconscious writes down patterns it has detected. Each subsequent run reads this file and can strengthen, weaken, or retire patterns.

**Neuroscience mapping:** Synaptic consolidation. Repeated activation strengthens the trace.

**Format:**
```markdown
## Active Patterns

### intention-drift-commits
**First detected:** 2026-01-25
**Last confirmed:** 2026-02-07
**Strength:** 4/5 (detected in 4 of last 5 scans)
**Pattern:** Keeps mentioning commit cleanup without executing it.
**Evidence:** Jan 25 session, Feb 2 session, Feb 5 session, Feb 7 session.

### machine-switching-productivity
**First detected:** 2026-02-01
**Strength:** 2/5 (detected in 2 scans)
**Pattern:** More focused sessions on Mac Mini, more exploratory on MacBook.
```

**Behavior:**
- Full `/subconscious` scan reads this file before generating
- After generating, appends/updates the pattern list
- Patterns not re-detected for 3+ scans get moved to "Fading" section
- Nudge mode (`/work`) reads this file to pick its one-liner

### Phase 3: Emotional Valence Detection (MEDIUM priority)

**What:** Add a 7th detection category to the subconscious prompt: **emotional signatures**.

**Neuroscience mapping:** Damasio's somatic markers.

**Additions to prompt:**
```
7. **Emotional signatures** — What emotional tone accompanies different types of work?
   Does frustration cluster around specific tasks? Does energy spike on certain topics?
   Are there events that feel "charged" (high stakes, near misses, breakthroughs)?
   What approach/avoid signals can you infer from the language used?
```

### Phase 4: Salience Weighting (MEDIUM priority)

**What:** Pre-tag events with importance markers so the AI doesn't treat a routine documentation commit the same as a trading blowup.

**Options:**
1. **Manual tags in events** — User adds `[HIGH]` or `[CRITICAL]` to event content
2. **Automated heuristics** — Script pre-scans for keywords (loss, mistake, breakthrough, discovery) and adds weight markers to the context sent to AI
3. **Event metadata** — Add optional `salience: high|medium|low` field to event files

### Phase 5: Fragment vs. Deep Scan Modes (LOW priority)

**What:** Formalize the distinction between the involuntary nudge (Phase 1) and the full scan. The nudge is a fragment; the full scan is voluntary introspection. Both are valid modes of the subconscious, but they serve different purposes and should behave differently.

| Mode | Trigger | Scope | Output | Maps To |
|---|---|---|---|---|
| Nudge | Automatic in `/work` | Last ~20 events + pattern memory | Single sentence | DMN flash |
| Deep Scan | Manual `/subconscious` | ALL events + pattern memory | 4-7 pattern blocks | Voluntary introspection |

---

## 5. Conway's Memory Model — Full Mapping

The exocortex memory system draws from **Conway's autobiographical memory model** (2005). The three knowledge tiers of autobiographical memory map to our time-based tiers:

| Conway Tier | Exocortex Tier | Time Window | Characteristics |
|---|---|---|---|
| **Episodic memory** — specific events with sensory detail | RIGHT NOW (Tier 0) | 0-7 days | Full detail, what happened, who said what |
| **General events** — summarized knowledge about periods | SHORT-TERM (Tier 1) | 7-31 days | Themes, progression, compressed narratives |
| **Lifetime periods** — abstract knowledge about life phases | LONG-TERM (Tier 2) | 31+ days | Monthly/quarterly milestones, evolution arcs |

The **subconscious** (Tier 3) is NOT part of Conway's hierarchical model. It maps to **parallel processing systems** that operate alongside autobiographical memory:

| Brain System | Function | Exocortex Feature |
|---|---|---|
| Default Mode Network | Unbidden insight generation | Subconscious nudge (planned Phase 1) |
| Basal ganglia | Statistical pattern detection | 6 detection categories in prompt |
| Somatic markers | Emotional valence tagging | Emotional signatures (planned Phase 3) |
| Anterior cingulate cortex | Error/conflict monitoring | 2-pass Ralph self-critique |
| Synaptic consolidation | Pattern strengthening over time | Pattern memory file (planned Phase 2) |

---

## 6. Technical Reference

| Component | Location |
|---|---|
| Full scan script | `.exocortex/scripts/get_subconscious_memory.py` (269 lines) |
| Command spec | `.exocortex/commands/subconscious.json` |
| Events directory | `.exocortex/events/*.md` |
| API keys | `.exocortex/.env` (OPENAI_API_KEY, ANTHROPIC_API_KEY) |
| Primary model | `gpt-4o-mini` |
| Fallback model | `claude-3-haiku-20240307` |
| Pattern memory (planned) | `.exocortex/subconscious_patterns.md` |
| Nudge script (planned) | `.exocortex/scripts/get_subconscious_nudge.py` |
| Memory tiers doc | `.exocortex/MEMORY_TIERS.md` |

---

*This document is part of the exocortex system documentation. See also: [MEMORY_TIERS.md](../MEMORY_TIERS.md), [COMMAND_SYSTEM.md](COMMAND_SYSTEM.md)*
