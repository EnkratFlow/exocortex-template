#!/usr/bin/env python3
# SUBCONSCIOUS — cross-cutting pattern detector across ALL memory
# NOT a time tier. Reads every event regardless of age.
# Surfaces: recurring cycles, behavioral patterns, drift, blind spots, contradictions
# 2-pass Ralph-style self-critique for quality

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# Get paths
script_dir = Path(__file__).parent
exocortex_dir = script_dir.parent
events_dir = exocortex_dir / "events"
env_file = exocortex_dir / ".env"
patterns_file = exocortex_dir / "subconscious_patterns.md"

# Load API keys (validated — detects missing .env, placeholders, auth errors)
from _api_helpers import load_api_keys, call_ai as _call_ai
openai_key, anthropic_key = load_api_keys(exocortex_dir)

# Read ALL events — no time filter at all
events = []
if events_dir.exists():
    for event_file in sorted(events_dir.glob("*.md"), reverse=True):
        try:
            date_part = event_file.stem.split('_')[0]
            event_date = datetime.strptime(date_part, '%Y-%m-%d')
            events.append({
                'file': event_file,
                'date': event_date,
                'content': event_file.read_text()
            })
        except:
            continue

if not events:
    print("🌊 SUBCONSCIOUS\n\nNo events yet. Start creating work events and patterns will emerge.")
    sys.exit(0)

if len(events) < 3:
    print(f"🌊 SUBCONSCIOUS\n\nOnly {len(events)} events so far. Need at least 3 for meaningful pattern detection. Keep working — patterns will emerge.")
    sys.exit(0)

# Stats
event_count = len(events)
unique_days = len(set(evt['date'].date() for evt in events))
span_days = (events[0]['date'] - events[-1]['date']).days + 1
oldest = events[-1]['date'].strftime('%b %d')
newest = events[0]['date'].strftime('%b %d')

# Detect machines used
machines = set()
for evt in events:
    parts = evt['file'].stem.split('_')
    if len(parts) >= 3:
        machine_part = parts[2].split('-')[0] if '-' in parts[2] else parts[2]
        machines.add(machine_part)

# If no API key, show basic stats
if not openai_key and not anthropic_key:
    print(f"🌊 SUBCONSCIOUS ({event_count} events, {span_days} days)")
    print("\n⚠️  No API key — install OpenAI or Anthropic for pattern detection")
    sys.exit(0)

# Build full context for AI (ALL events, full content)
events_context = f"Total: {event_count} events across {unique_days} days ({oldest}–{newest})\n"
events_context += f"Machines used: {', '.join(sorted(machines))}\n\n"
for i, evt in enumerate(events, 1):
    events_context += f"━━━ EVENT {i} ━━━\n"
    events_context += f"Date: {evt['date'].strftime('%Y-%m-%d %H:%M')} ({evt['date'].strftime('%A')})\n"
    events_context += f"File: {evt['file'].name}\n"
    events_context += evt['content']
    events_context += "\n\n"

# Read pattern memory for cross-session persistence (synaptic consolidation)
pattern_memory = ""
if patterns_file.exists():
    pattern_memory = patterns_file.read_text()
    if "No patterns detected yet" not in pattern_memory:
        events_context += "\n━━━ PREVIOUSLY DETECTED PATTERNS ━━━\n"
        events_context += pattern_memory
        events_context += "\n\n"

# --- Helper: call AI (delegates to shared module with error detection) ---
def call_ai(messages, max_tokens=1200):
    return _call_ai(openai_key, anthropic_key, messages, max_tokens)

# Create prompt for subconscious pattern detection
prompt = f"""You are the SUBCONSCIOUS — a pattern detection engine that operates below the surface of conscious recall. You do NOT reconstruct what happened (that's what the other memory tiers do). You detect what the person HASN'T NOTICED.

WHAT THE SUBCONSCIOUS DOES:
The human brain runs pattern detection constantly, in parallel with conscious thought. It notices:
- Regularities the conscious mind misses
- Cycles that repeat without the person realizing
- Drift between intentions and actions
- Behavioral signatures (when, where, how someone works)
- Contradictions between what they say and what they do
- Emerging trends that haven't been named yet

You read ALL events — recent and old — and look for the PATTERNS, not the content.

WHAT TO DETECT (scan for ALL of these):

1. **Recurring cycles** — Does the same sequence keep happening? (e.g., build → test debt → cleanup → build). What triggers each phase?

2. **Behavioral patterns** — When are they most productive? Which machine? What time of day? Do they work differently on different machines? How long are typical sessions?

3. **Intention drift** — What do they keep saying they'll do but haven't? What tasks keep getting postponed? What's the gap between stated plans and actual work?

4. **Emerging themes** — What's quietly taking up more attention over time? What topics keep growing? What's fading?

5. **Blind spots** — What are they NOT working on that they probably should be? What gets mentioned once then dropped? What obvious next steps are being skipped?

6. **Contradictions** — Do they say one thing and do another? Are there conflicting priorities that haven't been resolved?

7. **Emotional signatures** — What emotional tone accompanies different types of work? Does frustration cluster around specific tasks? Does energy spike on certain topics? Are there events that feel "charged" — high stakes, near misses, breakthroughs? What approach/avoid signals can you infer from the language used?

CRITICAL: BE SPECIFIC. Cite actual events, dates, and details.
Don't say "you tend to postpone tasks" — say "you mentioned committing files in 3 separate sessions (Jan 25, Feb 2, Feb 7) and still have 16 uncommitted."

FORMAT — pattern blocks with bold anchors:

🌊 SUBCONSCIOUS
{event_count} events · {span_days} days · pattern scan

**[Pattern label]**
[2-3 sentences. What the pattern is, evidence from specific events, what it might mean.]

**[Another pattern]**
[2-3 sentences with specific evidence.]

Keep to 4-8 patterns. Quality over quantity. Only surface things that are genuinely non-obvious or that the person likely hasn't consciously registered.

WHAT TO AVOID:
- NO timeline or chronological narrative — this is PATTERN-level, not time-level
- NO restating what happened (the other tiers cover that)
- NO bullet lists, NO emoji headers
- NO big paragraphs (3 sentences max)
- NO corporate language — no "robust", "comprehensive", "streamline", "leverage", "enhance", "operational", "overarching", "holistic", "culminated", "framework", "facilitate"
- NO vague observations — everything must cite specific evidence
- NO flattery or positive spin — be honest about what you see

VOICE: Quiet, observant, slightly detached. Like a therapist's notes — not judging, just noticing. "There's a pattern here..." Not preachy. Not advisory. Just: here's what's happening that you might not see.

Begin with: 🌊 SUBCONSCIOUS
Then: {event_count} events · {span_days} days · pattern scan
Then a blank line, then the pattern blocks.

FINAL REMINDER: The value of the subconscious is surfacing what's INVISIBLE to the conscious mind. If it's obvious, don't say it. Find the patterns hiding in plain sight.

ALL EVENTS TO SCAN:
{events_context}"""

# ============================================================
# PASS 1: Pattern detection
# ============================================================

print(f"   Scanning subconscious patterns ({event_count} events, {span_days} days)...", file=sys.stderr)

pass1_result = call_ai([{"role": "user", "content": prompt}], max_tokens=1200)

if not pass1_result:
    print(f"🌊 SUBCONSCIOUS\n\n⚠️  AI failed on pass 1")
    sys.exit(1)

# ============================================================
# PASS 2: Ralph-style self-critique — validate patterns
# ============================================================

print(f"   Pass 1 done. Running self-critique...", file=sys.stderr)

critique_prompt = f"""You are a QUALITY CHECKER for a subconscious pattern analysis. You receive:
1. The raw events
2. A first-pass pattern detection

Check against these rules:
- Must start with 🌊 SUBCONSCIOUS header
- Each pattern MUST have a bold anchor: **Pattern label**
- Paragraphs must be 2-3 sentences MAX
- Every pattern MUST cite specific evidence (dates, file names, event details)
- Patterns should be NON-OBVIOUS — if it's something the person clearly already knows, cut it
- NO restating what happened chronologically
- NO bullet lists, NO emoji-labeled sections
- FIND AND REPLACE these banned words:
  "comprehensive" → "full" or drop it
  "robust" → "solid" or drop it
  "streamline" → "clean up"
  "leverage" → "use"
  "enhance" → "improve" or drop it
  "operational" → "working"
  "overarching" → drop it
  "holistic" → drop it
  "culminated" → "led to"
  "framework" → "system"
  "facilitate" → "help"
  "seamless" → "smooth" or drop it
  "significant" → drop it or be specific
  "notable" → drop it
- NO flattery, NO vague cheerleading
- Are the patterns actually insightful, or just restating obvious facts?
- Did it miss any real patterns visible in the data?

Output the FINAL corrected version. Same format. No meta-commentary.
If a pattern is too obvious or unsupported, cut it and replace with a better one.

FIRST-PASS OUTPUT:
{pass1_result}

RAW EVENTS:
{events_context}"""

pass2_result = call_ai([{"role": "user", "content": critique_prompt}], max_tokens=1200)

if pass2_result:
    print(f"   ✓ Self-critique complete.", file=sys.stderr)
    final_output = pass2_result
else:
    print(f"   ⚠️  Self-critique failed, using pass 1.", file=sys.stderr)
    final_output = pass1_result

print(final_output)

# ============================================================
# PERSIST PATTERNS — synaptic consolidation
# ============================================================

try:
    today = datetime.now().strftime('%Y-%m-%d')
    persist_prompt = f"""Extract the pattern labels from this subconscious analysis. For each pattern found, output EXACTLY this format (one per pattern):

### [pattern-label-kebab-case]
**Last detected:** {today}
**Pattern:** [one sentence summary]
**Evidence:** [key dates/details cited]

Only output the pattern blocks, nothing else. Analysis to extract from:
{final_output}"""

    pattern_update = call_ai([{"role": "user", "content": persist_prompt}], max_tokens=600)
    if pattern_update:
        new_content = f"""# Subconscious Pattern Memory

> Auto-maintained by `/subconscious` scans. Last scan: {today}
> Neuroscience mapping: Synaptic consolidation — repeated detection strengthens the trace.

## Active Patterns

{pattern_update.strip()}

## Fading

_Patterns not re-detected for 3+ scans move here before being retired._

## Retired

_Patterns that are no longer relevant or have been resolved._
"""
        patterns_file.write_text(new_content)
        print(f"   ✓ Pattern memory updated.", file=sys.stderr)
except Exception as e:
    print(f"   ⚠️  Pattern persistence failed: {e}", file=sys.stderr)
