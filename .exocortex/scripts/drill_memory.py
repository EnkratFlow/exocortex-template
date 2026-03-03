#!/usr/bin/env python3
# DRILL — deep-dive into a specific topic across ALL memory tiers
# Uses 2-pass Ralph-style self-critique loop for quality
# Usage: python3 drill_memory.py "topic query"

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# --- Get topic from args ---
if len(sys.argv) < 2 or not sys.argv[1].strip():
    print("⚠️  Usage: /drill <topic>")
    print("   Example: /drill emotional grading")
    print("   Example: /drill supabase migration")
    print("   Example: /drill memory system")
    sys.exit(1)

topic = " ".join(sys.argv[1:]).strip()

# --- Paths ---
script_dir = Path(__file__).parent
exocortex_dir = script_dir.parent
events_dir = exocortex_dir / "events"
env_file = exocortex_dir / ".env"

# --- Load API keys (validated — detects missing .env, placeholders, auth errors) ---
from _api_helpers import load_api_keys, call_ai as _call_ai
openai_key, anthropic_key, openai_model, anthropic_model = load_api_keys(exocortex_dir)

if not openai_key and not anthropic_key:
    print(f"🔍 DRILL: {topic}\n\n⚠️  No API key — install OpenAI or Anthropic key for memory drill")
    sys.exit(0)

# --- Collect ALL events (no time limit) ---
events = []
if events_dir.exists():
    for event_file in sorted(events_dir.glob("*.md"), reverse=True):
        try:
            content = event_file.read_text()
            events.append({
                'file': event_file.name,
                'content': content
            })
        except:
            continue

if not events:
    print(f"🔍 DRILL: {topic}\n\nNo events found in memory.")
    sys.exit(0)

# --- Build events payload ---
events_context = f"Total events available: {len(events)}\n\n"
for i, evt in enumerate(events, 1):
    events_context += f"━━━ EVENT {i} ({evt['file']}) ━━━\n"
    events_context += evt['content']
    events_context += "\n\n"

# --- Helper: call AI (delegates to shared module with error detection) ---
def call_ai(messages, max_tokens=2000):
    return _call_ai(openai_key, anthropic_key, messages, max_tokens,
                    openai_model=openai_model, anthropic_model=anthropic_model)

# ============================================================
# PASS 1: Deep reconstruction focused on the topic
# ============================================================

pass1_messages = [
    {
        "role": "system",
        "content": """You are a memory reconstruction engine. You search through work events and rebuild a detailed narrative about a SPECIFIC TOPIC the user asks about.

Your job: find EVERY mention, reference, or related detail about the topic across all events, then reconstruct the full story — chronologically, with all the specifics preserved.

This is the OPPOSITE of the compressed memory briefs. Here we want DETAIL:
- Exact file names, function names, variable names
- Specific numbers (test counts, line counts, dates)
- What was tried, what failed, what worked
- The sequence of decisions and why
- What changed along the way
- Current state and any loose ends

VOICE: Same grounded internal monologue — direct, short sentences mixed with longer ones. But LONGER and MORE DETAILED than the brief format. This is a deep read, not a speed scan.

BANNED WORDS: robust, comprehensive, streamline, leverage, enhance, operational, overarching, holistic, culminated, organically, nuanced, rigorous, ensuring robustness, notable. Write like you'd actually think. "Built the 4 memory tiers" not "Established a comprehensive multi-tier memory framework."

FORMAT:
Start with: 🔍 DRILL: [topic]
Then a one-line summary of scope (how many events touched this, time range).
Then the detailed reconstruction using bold date anchors and short-to-medium paragraphs. Each paragraph can be 3-5 sentences here (more detail allowed than briefs).

If the topic spans a long time, organize chronologically with clear time markers.
If it's a focused topic, go deep on the specifics.

CRITICAL: Include things the compressed briefs would normally drop — edge cases, false starts, specific implementation details, file paths, function signatures. This is the drill-down."""
    },
    {
        "role": "user",
        "content": f"""Reconstruct everything about this topic: "{topic}"

Search through ALL of these events and pull out every relevant detail:

{events_context}"""
    }
]

print(f"🔍 Drilling into: {topic}", file=sys.stderr)
print(f"   Searching {len(events)} events...", file=sys.stderr)

pass1_result = call_ai(pass1_messages, max_tokens=2500)

if not pass1_result:
    print(f"🔍 DRILL: {topic}\n\n⚠️  AI failed on pass 1. Showing raw event list:")
    for evt in events:
        if topic.lower() in evt['content'].lower():
            print(f"\n📄 {evt['file']}")
    sys.exit(1)

# ============================================================
# PASS 2: Ralph-style self-critique — check for gaps & fix
# ============================================================

print(f"   Pass 1 complete. Running self-critique...", file=sys.stderr)

pass2_messages = [
    {
        "role": "system",
        "content": """You are a QUALITY CHECKER for memory reconstruction. You receive:
1. A topic query
2. The raw events that were available  
3. A first-pass reconstruction

Your job: Compare the reconstruction against the raw events and check:
- Did it MISS any relevant details from the events?
- Did it get any facts WRONG?
- Did it slip into corporate/flowery language? Check for: robust, comprehensive, streamline, leverage, enhance, operational, overarching, holistic, culminated, organically, nuanced, rigorous. Replace with plain talk.
- Is it organized clearly enough to actually be useful?
- Are there concrete specifics (files, functions, numbers) in the events that got dropped?

Then OUTPUT THE FINAL VERSION — incorporating any fixes. If the first pass was good, output it mostly unchanged with minor tightening. If it missed things, add them. If it was wrong, fix it.

Do NOT add a critique section. Just output the corrected final reconstruction, same format as pass 1. The output should look identical in structure — just more complete and accurate."""
    },
    {
        "role": "user",
        "content": f"""Topic: "{topic}"

FIRST-PASS RECONSTRUCTION:
{pass1_result}

RAW EVENTS TO CHECK AGAINST:
{events_context}

Output the final corrected version. Same format. No meta-commentary about what you changed."""
    }
]

pass2_result = call_ai(pass2_messages, max_tokens=2500)

if pass2_result:
    print(f"   ✓ Self-critique complete. 2-pass reconstruction done.", file=sys.stderr)
    print(pass2_result)
else:
    # Fall back to pass 1 if pass 2 fails
    print(f"   ⚠️  Self-critique failed, using pass 1 output.", file=sys.stderr)
    print(pass1_result)
