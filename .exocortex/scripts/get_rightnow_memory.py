#!/usr/bin/env python3
# AI-curates RIGHT NOW memory (0-7 days) using episodic human memory model

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

# Load API keys (validated — detects missing .env, placeholders, auth errors)
from _api_helpers import load_api_keys, call_ai as _call_ai
openai_key, anthropic_key, openai_model, anthropic_model = load_api_keys(exocortex_dir)

# Find events in last 7 days (mechanical)
seven_days_ago = datetime.now() - timedelta(days=7)
seven_days_str = seven_days_ago.strftime('%Y-%m-%d')

events = []
if events_dir.exists():
    for event_file in sorted(events_dir.glob("*.md"), reverse=True):
        # Parse date from filename: YYYY-MM-DD_HH-MM-SS_machine-editor.md
        try:
            date_part = event_file.stem.split('_')[0]
            event_date = datetime.strptime(date_part, '%Y-%m-%d')
            if event_date >= seven_days_ago:
                events.append({
                    'file': event_file,
                    'date': event_date,
                    'content': event_file.read_text()
                })
        except:
            continue

if not events:
    print("🟢 RIGHT NOW (Last 7 Days)\n\nNo recent events found.")
    sys.exit(0)

# If no API key, show basic info
if not openai_key and not anthropic_key:
    print("🟢 RIGHT NOW (Last 7 Days)\n")
    for evt in events[:3]:
        print(f"• {evt['date'].strftime('%b %d at %I:%M %p')}")
    print("\n⚠️  No API key - install OpenAI or Anthropic key for AI curation")
    sys.exit(0)

# Build full context for AI (ALL events, full content)
events_context = f"Found {len(events)} events in last 7 days:\n\n"
for i, evt in enumerate(events, 1):
    events_context += f"━━━ EVENT {i} ━━━\n"
    events_context += f"File: {evt['file'].name}\n"
    events_context += evt['content']
    events_context += "\n\n"

# Supplement with git log — fills gaps on days where /save was not run
# Git commits are the authoritative record of what was built; events add color
git_supplement = ""
try:
    repo_root = exocortex_dir.parent
    result = subprocess.run(
        ["git", "log", f"--since={seven_days_str} 00:00",
         "--format=commit %h — %ad — %s%n%b%n---", "--date=short"],
        cwd=repo_root, capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0 and result.stdout.strip():
        # Identify which dates have event coverage
        covered_dates = {evt['date'].strftime('%Y-%m-%d') for evt in events}
        git_lines = result.stdout.strip()
        git_supplement = (
            f"\n\n━━━ GIT LOG SUPPLEMENT (last 7 days) ━━━\n"
            f"NOTE: Dates with no event file are marked [NO EVENT — git only].\n"
            f"Use commit bodies as the authoritative record for those days.\n\n"
        )
        # Annotate which commits fall on uncovered dates
        current_date = None
        for line in git_lines.split('\n'):
            if line.startswith('commit '):
                # extract date from "commit abc — 2026-03-04 — subject"
                parts = line.split(' — ', 2)
                if len(parts) >= 2:
                    current_date = parts[1].strip()
                    if current_date not in covered_dates:
                        git_supplement += f"[NO EVENT — git only for {current_date}]\n"
            git_supplement += line + "\n"
except Exception:
    pass  # git supplement is optional — never block memory on this

# Create prompt for episodic memory curation
prompt = f"""You are reconstructing EPISODIC MEMORY — the way a human actually recalls the last few days when they sit back down at their desk.

NEUROSCIENCE OF HOW THIS WORKS:
Human memory is RECONSTRUCTIVE, not reproductive. When someone recalls recent work, their brain assembles fragments — vivid sensory details, emotional peaks, semantic facts, and goal-relevant context — into a flowing reconstruction. It feels like "a mix of imagery and words," not a bullet list. Details "pop" into mind within a natural flow of thought.

Key principles from autobiographical memory research (Conway & Pleydell-Pearce):
- Event-specific knowledge: vivid details that pop unbidden — "435 tests went green," "sitting at the mac-mini, late afternoon"
- The DIRECTIVE function: memory serves the working self's current goals — what happened naturally blends with what's still open and what's intended next
- Emotional anchoring: breakthroughs ("finally got X working"), frustrations, turning points — these resist decay and should be foregrounded
- Stream of consciousness: William James — "it flows, it is nothing jointed." No categories, no rigid structure. Natural transitions between thoughts.

CRITICAL: THIS IS FOR SPEED-SCANNING, NOT LINE-BY-LINE READING.
The human works from multiple machines at different times. They need to glance at this and instantly know: when, where, what. Their eye catches visual anchors (bold date lines) and fills in meaning from the surrounding text patterns.

STRUCTURE — each session gets a bold date/machine anchor line, then paragraphs OR a phase roster:

**[Date] · [machine] · [editor] · [time of day if known]**
[2-3 sentences about what happened. Concrete specifics — numbers, file names, what got done.]

IF this session shipped multiple named deliverables (phases, features, fixes, systems, etc.), add a compact roster AFTER the prose paragraph:
- Phase N — key component or feature name — N tests
- fix: some-named-thing — what changed
- feature: some-system — what it does
(One line per item. No prose. Just the facts.)

[1-2 sentences about what's still open or next. Future intentions belong here.]

If there are multiple sessions in the last 7 days, show each one with its own anchor line. Most recent first.

After all session blocks, optionally add a short "threads" section for things that span sessions — uncommitted work, recurring intentions, stuff you keep meaning to do.

WHAT TO AVOID:
- NO category headers, NO emoji-labeled sections
- NO rigid structure like "Complete:" / "Pending:" / "Tests:" / "Logic:"
- NO big wall-of-text paragraphs (max 3 sentences per paragraph)
- NO poetic or flowery language — no "the familiar hum of", no "a sense of calm washes over"
- NO corporate language — no "robust", "comprehensive", "streamline", "leverage"
- NO compressing named deliverables into vague phrases — Phase 14, Phase 17, "the timeout fix", "supersession detection", specific feature names MUST each appear by name with their key detail. 'Feature work', 'various fixes', 'system improvements' are FORBIDDEN unless nothing was named.

WHAT TO INCLUDE:
- Bold date/machine/editor anchor lines for each session (use **bold** markdown)
- Short paragraphs (2-3 sentences max) — scannable, not dense
- Concrete specifics woven in naturally (numbers, file names, feature names)
- Bullet roster when a session shipped multiple named deliverables — phases, named features, named fixes, named systems (critical — do not compress these away)
- Brief emotional color at key moments: "finally got that working", "still bugging me"
- Unfinished threads and future intentions mixed in naturally
- If there's meta-work (tooling/exocortex), mention it briefly but keep project work central

VOICE: Internal monologue. Direct. Grounded. Short sentences mixed with longer ones. Like scanning your own notes when you sit back down.

EXAMPLE OUTPUT:

🟢 RIGHT NOW

**Feb 7 · macbook · cursor · afternoon**
Deep in the test suite overhaul. Moved from permissive to exact assertions — 435 tests passing now. Rewrote orderFlowContract (44 tests) and strategySnapshots (33 tests).

Also wired the emotional gating engine into technicalCoaching.ts. The isPrimaryLevel param swap bug is fixed.

**Feb 7 · macbook · cursor · earlier**
Got all four memory tiers up and running. Short-term showing full detail in /work now. Documented in MEMORY_TIERS.md.

Keep meaning to look at the aggressive entry flow. Also about 15 uncommitted files still sitting there — need to clean those up before moving on.

Begin with: 🟢 RIGHT NOW
Then a blank line, then the flowing recall.

FINAL REMINDER: Write like you're THINKING, not presenting. No corporate language. No "robust", "comprehensive", "streamline", "leverage", "enhance". Just plain talk. If you catch yourself writing something you'd never actually think, rewrite it simpler.

ALL EVENTS TO RECONSTRUCT FROM:
{events_context}{git_supplement}"""

# --- Helper: call AI (delegates to shared module with error detection) ---
def call_ai(messages, max_tokens=1500):
    return _call_ai(openai_key, anthropic_key, messages, max_tokens,
                    openai_model=openai_model, anthropic_model=anthropic_model)

# ============================================================
# PASS 1: Generate episodic memory reconstruction
# ============================================================

print(f"   Reconstructing RIGHT NOW ({len(events)} events)...", file=sys.stderr)

pass1_result = call_ai([{"role": "user", "content": prompt}], max_tokens=2500)

if not pass1_result:
    print("🟢 RIGHT NOW\n\n⚠️  AI failed on pass 1")
    print("\nShowing basic event list:", file=sys.stderr)
    for evt in events[:3]:
        print(f"• {evt['date'].strftime('%b %d at %I:%M %p')}", file=sys.stderr)
    sys.exit(1)

# ============================================================
# PASS 2: Ralph-style self-critique — check format & tone
# ============================================================

print(f"   Pass 1 done. Running self-critique...", file=sys.stderr)

critique_prompt = f"""You are a QUALITY CHECKER for a RIGHT NOW memory brief. You receive:
1. The raw events that were available
2. A first-pass reconstruction

Check against these rules:
- Each session MUST have a bold anchor line: **Date · machine · editor · time**
- Paragraphs must be 2-3 sentences MAX (split any that are longer)
- NO emoji-labeled sections, NO category headers
- Bullet lists ARE allowed for rosters of named deliverables (phases, named features, named fixes, named systems). Everything else must be prose.
- Named deliverables MUST appear by name — Phase 14, "the timeout fix", "supersession detection", etc. Do NOT compress them into vague phrases like 'feature work', 'various fixes', 'system improvements'.
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
- NO flowery prose: "the familiar hum of", "against the backdrop of"
- Did it miss any concrete specifics from the events? (file names, numbers, features)
- Is the THREADS section present if there are cross-session items?

Output the FINAL corrected version. Same format. No meta-commentary about changes.
If the first pass was already good, output it with only minor tightening.

FIRST-PASS OUTPUT:
{pass1_result}

RAW EVENTS:
{events_context}{git_supplement}"""

pass2_result = call_ai([{"role": "user", "content": critique_prompt}], max_tokens=1500)

if pass2_result:
    print(f"   ✓ Self-critique complete.", file=sys.stderr)
    print(pass2_result)
else:
    # Fall back to pass 1 if critique fails
    print(f"   ⚠️  Self-critique failed, using pass 1.", file=sys.stderr)
    print(pass1_result)
