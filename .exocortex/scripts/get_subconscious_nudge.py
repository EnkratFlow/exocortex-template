#!/usr/bin/env python3
# SUBCONSCIOUS NUDGE — lightweight single-sentence pattern probe
# Fires automatically during /work. Produces ONE fragment, not a full report.
# Neuroscience mapping: Default Mode Network activation — unbidden insight.
# Reads last ~20 events + pattern memory file for cross-session persistence.
# 1-pass only (no self-critique) — speed matters for automatic invocation.

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

# Load API keys (silent — nudge is optional, don't break /work flow)
from _api_helpers import load_api_keys, call_ai as _call_ai
openai_key, anthropic_key, openai_model, anthropic_model = load_api_keys(exocortex_dir, silent=True)

if not openai_key and not anthropic_key:
    # Silent exit — nudge is optional, don't break /work flow
    sys.exit(0)

# Read last ~20 events (lightweight scope)
events = []
if events_dir.exists():
    for event_file in sorted(events_dir.glob("*.md"), reverse=True)[:20]:
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

if len(events) < 3:
    # Not enough data for meaningful pattern detection — silent exit
    sys.exit(0)

# Read pattern memory if it exists (cross-session persistence)
pattern_memory = ""
if patterns_file.exists():
    pattern_memory = patterns_file.read_text()

# Build compact context
event_count = len(events)
events_context = ""
for i, evt in enumerate(events, 1):
    events_context += f"--- Event {i} ({evt['date'].strftime('%Y-%m-%d')}) ---\n"
    events_context += evt['content'][:500]  # Truncate for speed
    events_context += "\n\n"

# --- Helper: call AI (delegates to shared module, silent — don't break /work) ---
def call_ai(messages, max_tokens=150):
    return _call_ai(openai_key, anthropic_key, messages, max_tokens, silent=True)

# Build the nudge prompt — constrained to ONE sentence
pattern_section = ""
if pattern_memory:
    pattern_section = f"""
PREVIOUSLY DETECTED PATTERNS (from past scans):
{pattern_memory}

If any of these patterns are STILL visible in the recent events, that makes them stronger.
Prefer surfacing a persistent pattern over discovering a new one.
"""

prompt = f"""You are the subconscious — a background pattern detector. You have been given the most recent {event_count} events from a developer's work journal.

{pattern_section}

YOUR TASK: Produce exactly ONE sentence. This sentence should be a pattern observation, a nagging question, or a gut-feeling signal — something the person probably hasn't consciously noticed.

RULES:
- EXACTLY one sentence. No more.
- Must cite specific evidence (dates, file names, numbers)
- Must be non-obvious — if they clearly already know it, don't say it
- No flattery, no encouragement, no advice
- Tone: quiet observation, like a thought surfacing unbidden
- No corporate words (comprehensive, robust, streamline, leverage, enhance, framework)
- Start with 💭 emoji, nothing else before it

GOOD EXAMPLES:
💭 You've mentioned "commit cleanup" in 4 sessions (Jan 25, Feb 2, Feb 5, Feb 7) without doing it.
💭 Last three sessions started on server/ work but drifted to docs/ within an hour.
💭 You work longer sessions on the Mac Mini but ship more on shorter MacBook sessions.
💭 The test suite hasn't been run since Jan 30 but you've changed 12 files since then.

BAD EXAMPLES (don't do these):
💭 You've been very productive lately! (flattery)
💭 Consider prioritizing your backlog. (advice)
💭 There are some interesting patterns in your work. (vague)

RECENT EVENTS:
{events_context}"""

result = call_ai([{"role": "user", "content": prompt}], max_tokens=150)

if result:
    # Clean up — ensure it starts with 💭 and is one sentence
    result = result.strip()
    if not result.startswith('💭'):
        result = '💭 ' + result
    # Take only the first sentence if AI over-generated
    first_sentence = result.split('\n')[0].strip()
    print(first_sentence)
else:
    # Silent failure — don't break the /work flow
    sys.exit(0)
