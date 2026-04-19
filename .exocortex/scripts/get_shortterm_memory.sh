#!/usr/bin/env python3
# AI-curates short-term memory (7-31 days) using semantic human memory model

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

# Find events 7-31 days ago (mechanical)
thirty_one_days_ago = datetime.now() - timedelta(days=31)
seven_days_ago = datetime.now() - timedelta(days=7)

events = []
if events_dir.exists():
    for event_file in sorted(events_dir.glob("*.md"), reverse=True):
        try:
            date_part = event_file.stem.split('_')[0]
            event_date = datetime.strptime(date_part, '%Y-%m-%d')
            if thirty_one_days_ago <= event_date < seven_days_ago:
                events.append({
                    'file': event_file,
                    'date': event_date,
                    'content': event_file.read_text()
                })
        except:
            continue

if not events:
    print("📅 SHORT-TERM (7-31 Days Ago)\n\nNo events in this period.")
    sys.exit(0)

# Count stats
event_count = len(events)
unique_days = len(set(evt['date'].date() for evt in events))
period_start = events[-1]['date'].strftime('%b %d')
period_end = events[0]['date'].strftime('%b %d')

# If no API key, show basic stats
if not openai_key and not anthropic_key:
    print(f"📅 SHORT-TERM ({period_start}-{period_end})")
    print(f"\n{event_count} events across {unique_days} days")
    print("\n⚠️  No API key - install OpenAI or Anthropic for AI curation")
    sys.exit(0)

# Build full context for AI (ALL events, full content)
events_context = f"Found {event_count} events across {unique_days} days ({period_start}-{period_end}):\n\n"
for i, evt in enumerate(events, 1):
    events_context += f"━━━ EVENT {i} ━━━\n"
    events_context += f"Date: {evt['date'].strftime('%Y-%m-%d %H:%M')}\n"
    events_context += evt['content']
    events_context += "\n\n"

# Create prompt for semantic memory curation
prompt = f"""You are reconstructing SEMANTIC MEMORY — the way a human recalls work from a few weeks ago. Not vivid re-living, but KNOWING what happened. Themes, arcs, evolution.

NEUROSCIENCE OF THIS TIER:
In autobiographical memory (Conway's model), memories older than ~7 days undergo the "episodic-to-semantic shift." You lose the vivid sensory details but retain the MEANING. Memories at this age organize as "general events" — goal-clustered chunks:
- "That week of refining the grading logic"
- "The push to get accountability messaging right"
- "Going back and forth on edge cases for imbalanced scenarios"

These general events cluster by THEME and GOAL, not by date. Time compresses: "spent several days on X" not "on Tuesday at 2pm I did Y."

WHAT THIS SHOULD FEEL LIKE:
Like stepping back and seeing the shape of recent weeks. The arc of how work evolved. What the major pushes were. Where things shifted direction. What emerged as important. It's the kind of recall where you'd tell a colleague: "So the last few weeks we've been..."

THREE THINGS TO WEAVE:
1. The arc — how work evolved from start to end of this period
2. What crystallized — accomplishments, capabilities that now exist
3. What's carrying forward — patterns, unresolved threads, emerging directions

CRITICAL: THIS IS FOR SPEED-SCANNING, NOT LINE-BY-LINE READING.
At this time range, individual sessions blur together. But the THEMES and ARCS are clear. Group by theme, not by date. Each theme gets a bold label line and 2-3 short sentences.

STRUCTURE — themed blocks with bold anchors:

**[Theme name or arc label]**
[2-3 sentences about this theme. What happened, what got built, how it evolved. Concrete but compressed.]

**[Another theme]**
[2-3 sentences. Keep it short.]

Optionally end with a short "still open" note for threads carrying forward.

WHAT TO AVOID:
- NO bullet lists with emoji headers (🎯, ⚡, 🔄)
- NO rigid "Accomplishments / Shifts / Patterns" sections
- NO big wall-of-text paragraphs (max 3 sentences per paragraph)
- NO dashboard formatting
- NO poetic or flowery language
- NO corporate language — no "robust", "comprehensive", "streamline", "culminated in", "framework"

WHAT TO INCLUDE:
- Bold theme labels as visual anchors (use **bold** markdown)
- Short paragraphs (2-3 sentences max) under each theme
- Name concrete things (features, files, metrics) within thematic context
- Show evolution where relevant — "started with X, led to Y"
- Time compression: "first half of the week", "around Jan 25"
- Unresolved threads carry forward naturally at the end

VOICE: Internal monologue, zoomed out. Direct and grounded. Short sentences. Like thinking back over recent weeks — "so the big push was the accountability system... that took most of the first week."

EXAMPLE OUTPUT:

📅 SHORT-TERM
Jan 23 – Jan 30 · 9 sessions · 5 active days

**Psychological accountability system**
This was the main push. Emotional grading (A/B/C/F), circuit breaker for consecutive losses, core metrics — MAE, MFE, hold time. All landed. Trade History interface is live with the new fields.

**Event-based architecture**
Switched from session overwrites to append-only events. Fixed the VS Code / Cursor conflict problem. The .cursorrules pointer to AI_INSTRUCTIONS.md cleaned up the workflow.

**Supabase migration**
Moved from local Postgres to Supabase. Multi-machine dev works now. Connection string in server/.env, network access configured.

Still need to finalize schema migrations for the psych metrics and do proper testing of emotional grading in the trade flow.

Begin with: 📅 SHORT-TERM
Then on next line: {period_start} – {period_end} · {event_count} sessions · {unique_days} active days
Then a blank line, then the flowing recall.

FINAL REMINDER: Write like you're THINKING, not presenting. No corporate language. No "robust", "comprehensive", "streamline", "leverage", "enhance", "operational", "overarching", "holistic". Just plain talk. Say it the way you'd actually think it. "We built the emotional grading stuff" not "We established a comprehensive emotional grading framework."

ALL EVENTS TO RECONSTRUCT FROM:
{events_context}"""

# --- Helper: call AI ---
def call_ai(messages, max_tokens=800):
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

# ============================================================
# PASS 1: Generate semantic memory reconstruction
# ============================================================

print(f"   Reconstructing SHORT-TERM ({event_count} events)...", file=sys.stderr)

pass1_result = call_ai([{"role": "user", "content": prompt}], max_tokens=800)

if not pass1_result:
    print(f"📅 SHORT-TERM ({period_start}-{period_end})\n\n⚠️  AI failed on pass 1")
    print(f"\n{event_count} events from {period_start}-{period_end}", file=sys.stderr)
    sys.exit(1)

# ============================================================
# PASS 2: Ralph-style self-critique — check format & tone
# ============================================================

print(f"   Pass 1 done. Running self-critique...", file=sys.stderr)

critique_prompt = f"""You are a QUALITY CHECKER for a SHORT-TERM memory brief. You receive:
1. The raw events that were available
2. A first-pass reconstruction

Check against these rules:
- Must start with 📅 SHORT-TERM header and date range / session count line
- Each theme MUST have a bold label: **Theme name**
- Paragraphs must be 2-3 sentences MAX (split any that are longer)
- Themes should be GOAL-CLUSTERED, not date-by-date
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
  "extensive" → drop it or "a lot of"
  "consolidated" → "combined" or "merged"
  "designed to enhance" → just say what it does
- NO flowery prose
- Did it miss any major themes from the events?
- Is there a "still open" trailing note for unresolved threads?

Output the FINAL corrected version. Same format. No meta-commentary about changes.
If the first pass was already good, output it with only minor tightening.

FIRST-PASS OUTPUT:
{pass1_result}

RAW EVENTS:
{events_context}"""

pass2_result = call_ai([{"role": "user", "content": critique_prompt}], max_tokens=800)

if pass2_result:
    print(f"   ✓ Self-critique complete.", file=sys.stderr)
    print(pass2_result)
else:
    # Fall back to pass 1 if critique fails
    print(f"   ⚠️  Self-critique failed, using pass 1.", file=sys.stderr)
    print(pass1_result)
