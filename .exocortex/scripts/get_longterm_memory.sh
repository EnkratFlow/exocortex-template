#!/usr/bin/env python3
# AI-curates long-term memory (31+ days, NO ceiling)
# Compression increases with age: months → quarters → years → eras
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

# Load API keys
api_keys = {}
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            key, val = line.split('=', 1)
            api_keys[key.strip()] = val.strip()

openai_key = api_keys.get('OPENAI_API_KEY')
anthropic_key = api_keys.get('ANTHROPIC_API_KEY')

# Find ALL events older than 31 days — no upper bound
thirty_one_days_ago = datetime.now() - timedelta(days=31)

events = []
if events_dir.exists():
    for event_file in sorted(events_dir.glob("*.md"), reverse=True):
        try:
            date_part = event_file.stem.split('_')[0]
            event_date = datetime.strptime(date_part, '%Y-%m-%d')
            if event_date < thirty_one_days_ago:
                events.append({
                    'file': event_file,
                    'date': event_date,
                    'content': event_file.read_text()
                })
        except:
            continue

if not events:
    print("📦 LONG-TERM (31+ Days)\n\nNo events older than 31 days yet. Events will age into this tier from short-term.")
    sys.exit(0)

# Stats
event_count = len(events)
unique_days = len(set(evt['date'].date() for evt in events))
unique_months = len(set(evt['date'].strftime('%Y-%m') for evt in events))
unique_years = len(set(evt['date'].strftime('%Y') for evt in events))
oldest = events[-1]['date'].strftime('%b %Y')
newest = events[0]['date'].strftime('%b %Y')
# Calculate total span in days for compression guidance
span_days = (events[0]['date'] - events[-1]['date']).days + 1

# If no API key, show basic stats
if not openai_key and not anthropic_key:
    print(f"📦 LONG-TERM ({oldest}–{newest})")
    print(f"\n{event_count} events across {unique_months} months")
    print("\n⚠️  No API key — install OpenAI or Anthropic for AI curation")
    sys.exit(0)

# Build full context for AI (ALL events, full content)
events_context = f"Found {event_count} events across {unique_months} months ({oldest}–{newest}):\n\n"
for i, evt in enumerate(events, 1):
    events_context += f"━━━ EVENT {i} ━━━\n"
    events_context += f"Date: {evt['date'].strftime('%Y-%m-%d %H:%M')}\n"
    events_context += f"File: {evt['file'].name}\n"
    events_context += evt['content']
    events_context += "\n\n"

# Determine compression guidance based on span
if span_days < 180:
    compression_hint = "Group by MONTH. Each month gets its own anchor."
elif span_days < 730:
    compression_hint = "Group by QUARTER. Recent quarters get more detail, older ones compress further."
else:
    compression_hint = "Group by ERA or YEAR. Recent periods get quarterly detail, older periods compress to yearly or era-level."

# --- Helper: call AI ---
def call_ai(messages, max_tokens=1200):
    """Call OpenAI or Anthropic. Returns response text or None."""
    try:
        if openai_key:
            response = subprocess.run([
                'curl', '-s', 'https://api.openai.com/v1/chat/completions',
                '-H', 'Content-Type: application/json',
                '-H', f'Authorization: Bearer {openai_key}',
                '-d', json.dumps({
                    "model": "gpt-4o-mini",
                    "max_tokens": max_tokens,
                    "messages": messages
                })
            ], capture_output=True, text=True, check=True)
            
            result = json.loads(response.stdout)
            if 'choices' in result and result['choices']:
                return result['choices'][0]['message']['content']
            return None
            
        elif anthropic_key:
            system_msg = None
            user_msgs = []
            for msg in messages:
                if msg['role'] == 'system':
                    system_msg = msg['content']
                else:
                    user_msgs.append(msg)
            
            payload = {
                "model": "claude-3-haiku-20240307",
                "max_tokens": max_tokens,
                "messages": user_msgs
            }
            if system_msg:
                payload["system"] = system_msg
            
            response = subprocess.run([
                'curl', '-s', 'https://api.anthropic.com/v1/messages',
                '-H', 'content-type: application/json',
                '-H', f'x-api-key: {anthropic_key}',
                '-H', 'anthropic-version: 2023-06-01',
                '-d', json.dumps(payload)
            ], capture_output=True, text=True, check=True)
            
            result = json.loads(response.stdout)
            if 'content' in result and result['content']:
                return result['content'][0]['text']
            return None
    except Exception as e:
        print(f"⚠️  API error: {e}", file=sys.stderr)
        return None

# Create prompt for long-term memory curation
prompt = f"""You are reconstructing LONG-TERM MEMORY — the permanent store. This is everything older than a month. There is NO upper limit. As events age, they compress more, but they never leave long-term memory.

HOW LONG-TERM MEMORY WORKS:
Long-term memory is the brain's permanent archive. It has no ceiling — it just compresses more as things age:
- 1-3 months ago: MONTHLY granularity. "In November, the focus was..."
- 3-12 months ago: QUARTERLY granularity. "Last summer we..."
- 1+ years ago: YEARLY or ERA granularity. "The first year was all about..."
Recent events get more detail. Older events compress further. The compression is NATURAL, like how you actually remember — last month is clearer than last year, which is clearer than two years ago.

WHAT THIS SHOULD FEEL LIKE:
Like telling someone the full history of the project, from the beginning, over coffee. You start way back and work forward. The early stuff is broad strokes. The recent months get more texture. The arc of how things evolved is the point.

CRITICAL: THIS IS FOR SPEED-SCANNING.
Bold anchors for each time period. Short blocks. The human scans and sees the full shape of the project's history.

COMPRESSION GUIDANCE FOR THIS DATA:
Total span: {span_days} days across {unique_months} months.
{compression_hint}

STRUCTURE — time-period blocks with bold anchors:

**[Time period label]**
[2-3 sentences about what that period was about. Main push, what got built, major shifts.]

**[Next period — more recent = more detail]**
[2-3 sentences.]

End with a short "trajectory" note — where things were heading as the most recent period in this tier closed out.

WHAT TO AVOID:
- NO bullet lists, NO emoji headers, NO rigid sections
- NO individual session details — this is months/quarters/years level
- NO big paragraphs (3 sentences max per block)
- NO corporate language — no "robust", "comprehensive", "streamline", "leverage", "enhance", "operational", "overarching", "holistic", "culminated", "framework", "facilitate"
- NO flowery prose

WHAT TO INCLUDE:
- Bold time-period anchor lines
- Short paragraphs (2-3 sentences max)
- Major features, systems, or capabilities that were built
- Shifts in direction or approach
- What stuck vs what was abandoned
- Natural compression: older = broader, recent = more specific

VOICE: Internal monologue, zoomed way out. Like thinking back over the project's life. Short, direct, seeing the shape of time.

Begin with: 📦 LONG-TERM
Then on next line: {oldest} – {newest} · {event_count} sessions · {unique_months} months
Then a blank line, then the flowing recall.

FINAL REMINDER: Write like you're THINKING, not presenting. No corporate language. Plain talk. "We built the grading system" not "We established a grading framework."

ALL EVENTS TO RECONSTRUCT FROM:
{events_context}"""

# ============================================================
# PASS 1: Generate long-term memory reconstruction
# ============================================================

print(f"   Reconstructing LONG-TERM ({event_count} events, {unique_months} months)...", file=sys.stderr)

pass1_result = call_ai([{"role": "user", "content": prompt}], max_tokens=1200)

if not pass1_result:
    print(f"📦 LONG-TERM ({oldest}–{newest})\n\n⚠️  AI failed on pass 1")
    sys.exit(1)

# ============================================================
# PASS 2: Ralph-style self-critique
# ============================================================

print(f"   Pass 1 done. Running self-critique...", file=sys.stderr)

critique_prompt = f"""You are a QUALITY CHECKER for a LONG-TERM memory brief. You receive:
1. The raw events that were available
2. A first-pass reconstruction

Check against these rules:
- Must start with 📦 LONG-TERM header and date range line
- Each period MUST have a bold anchor: **Month, quarter, or era label**
- Paragraphs must be 2-3 sentences MAX
- Organized by TIME PERIOD, oldest first, most recent last
- Compression should increase with age (older = broader strokes)
- NO bullet lists, NO emoji-labeled sections
- FIND AND REPLACE these banned words with plain alternatives:
  "comprehensive" → "full" or just drop it
  "robust" → "solid" or drop it
  "streamline" → "clean up" or "simplify"
  "leverage" → "use"
  "enhance" → "improve" or drop it
  "operational" → "working" or "running"
  "overarching" → drop it
  "holistic" → drop it
  "culminated" → "ended up as" or "led to"
  "framework" → "system" or "setup"
  "facilitate" → "help" or "let"
  "seamless" → "smooth" or drop it
  "extensive" → drop it
  "significant" → drop it or be specific
- NO flowery prose
- Does it show the ARC from beginning to most recent?
- Is there a "trajectory" note at the end?

Output the FINAL corrected version. Same format. No meta-commentary.

FIRST-PASS OUTPUT:
{pass1_result}

RAW EVENTS:
{events_context}"""

pass2_result = call_ai([{"role": "user", "content": critique_prompt}], max_tokens=1200)

if pass2_result:
    print(f"   ✓ Self-critique complete.", file=sys.stderr)
    print(pass2_result)
else:
    print(f"   ⚠️  Self-critique failed, using pass 1.", file=sys.stderr)
    print(pass1_result)
