#!/usr/bin/env python3
"""
get_claude_history.py — extract today's substantive user messages from Claude Code history.

Reads ~/.claude/history.jsonl and prints all non-trivial user inputs from today
(or a specified date). Used by run_end_day.sh to supplement the daily-end AI with
real session content even when /save was not called.

Usage:
    python3 get_claude_history.py [--date YYYY-MM-DD] [--hours N] [--project PATH]
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta

# Commands that are claude-code meta-commands, not actual work requests
TRIVIAL = {
    '', 'q', 'exit', 'quit', 'clear', 'compact', 'sonnet', 'haiku', 'opus', 'flash',
    'help', 'y', 'n', 'yes', 'no', 'ok', 'done', 'ctrl+c', '.', '..', 'ls', 'pwd',
    '/save', '/work', '/daily-end', '/scrum', '/brief', '/interrupt', '/groom',
    '/refine-backlog', '/prioritize', '/weekly-review', '/monthly-review',
    '/onboard', '/system-scan', '/ai-export', '/ecosystem', '/init-exocortex',
    '/check-keys', '/shortterm', '/longterm', '/subconscious', '/drill', '/history',
}

MIN_DISPLAY_LEN = 15  # chars — below this is almost certainly a short command


def is_trivial(display: str) -> bool:
    stripped = display.strip().lower()
    if stripped in TRIVIAL:
        return True
    if len(stripped) < MIN_DISPLAY_LEN:
        return True
    # Single-word commands like a model name or slash-command
    if stripped.startswith('/') and ' ' not in stripped:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='Extract Claude Code session history')
    parser.add_argument('--date', default=None, help='Date to filter (YYYY-MM-DD), default: today')
    parser.add_argument('--hours', type=int, default=None, help='Last N hours instead of a date')
    parser.add_argument('--project', default=None, help='Filter by project path substring')
    parser.add_argument('--max-per-session', type=int, default=50, help='Max messages per session')
    args = parser.parse_args()

    history_path = os.path.expanduser('~/.claude/history.jsonl')
    if not os.path.exists(history_path):
        print('  (Claude Code history not found — ~/.claude/history.jsonl missing)')
        sys.exit(0)

    # Determine time window
    now = datetime.now()
    if args.hours is not None:
        cutoff = now - timedelta(hours=args.hours)
        window_label = f'last {args.hours} hours'
    elif args.date:
        try:
            cutoff = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f'  ERROR: invalid --date format, use YYYY-MM-DD', file=sys.stderr)
            sys.exit(1)
        window_label = args.date
    else:
        cutoff = datetime.strptime(now.strftime('%Y-%m-%d'), '%Y-%m-%d')
        window_label = now.strftime('%Y-%m-%d')

    # Parse history
    entries = []
    try:
        with open(history_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    ts = obj.get('timestamp', 0)
                    display = str(obj.get('display', ''))
                    project = str(obj.get('project', ''))
                    session_id = obj.get('sessionId', '')

                    # Time filter
                    entry_dt = datetime.fromtimestamp(ts / 1000)
                    if entry_dt < cutoff:
                        continue

                    # Project filter (if specified)
                    if args.project and args.project not in project:
                        continue

                    # Skip trivial
                    if is_trivial(display):
                        continue

                    entries.append({
                        'dt': entry_dt,
                        'display': display.strip(),
                        'project': project,
                        'session_id': session_id,
                    })
                except (json.JSONDecodeError, OSError, ValueError):
                    continue
    except OSError as e:
        print(f'  ERROR reading history: {e}', file=sys.stderr)
        sys.exit(0)

    if not entries:
        print(f'  No substantive Claude Code inputs found for {window_label}.')
        sys.exit(0)

    # Group by session for readability
    sessions: dict[str, list] = {}
    for e in entries:
        sid = e['session_id'] or 'unknown'
        sessions.setdefault(sid, []).append(e)

    total_msgs = len(entries)
    print(f'  Found {total_msgs} user message(s) across {len(sessions)} session(s) — {window_label}:')
    print()

    for sid, msgs in sessions.items():
        # Session header
        first_time = msgs[0]['dt'].strftime('%H:%M')
        last_time = msgs[-1]['dt'].strftime('%H:%M')
        proj_display = msgs[0]['project'].split('/')[-1] or msgs[0]['project']
        print(f'  Session {sid[:8]}... | {proj_display} | {first_time}–{last_time}')

        shown = 0
        for msg in msgs:
            if shown >= args.max_per_session:
                remaining = len(msgs) - shown
                print(f'    ... ({remaining} more messages truncated)')
                break
            time_str = msg['dt'].strftime('%H:%M')
            # Truncate long messages but keep meaningful content
            text = msg['display']
            if len(text) > 300:
                text = text[:297] + '...'
            # Replace newlines with space for compact display
            text = text.replace('\n', ' ').replace('\r', '')
            print(f'    {time_str} | {text}')
            shown += 1
        print()


if __name__ == '__main__':
    main()
