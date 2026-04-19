#!/bin/bash
# install_openclaw_reminder.sh — Deploy exocortex-reminder skill to OpenClaw VPS
#
# Detects if OpenClaw is installed, locates the skills directory, copies the
# SKILL.md, and prints the exact command to register the cron schedule.
#
# Does NOT run SSH commands automatically — it prints them for you to run,
# so you stay in control of what goes onto your VPS.

set -e

echo "=== Exocortex OpenClaw Reminder Setup ==="
echo ""

# ── Locate this skill's SKILL.md ──────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXOCORTEX_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"  # two levels up from scripts/
SKILL_SRC="$EXOCORTEX_DIR/.exocortex/skills/exocortex-reminder/SKILL.md"

# Fallback: search relative to script location
if [ ! -f "$SKILL_SRC" ]; then
    # SCRIPT_DIR is .exocortex/scripts, so sibling skills dir:
    SKILL_SRC="$(dirname "$SCRIPT_DIR")/skills/exocortex-reminder/SKILL.md"
fi

if [ ! -f "$SKILL_SRC" ]; then
    echo "❌  Cannot find .exocortex/skills/exocortex-reminder/SKILL.md"
    echo "    Make sure you're running this from inside a repo with .exocortex/"
    exit 1
fi

# ── Detect OpenClaw ──────────────────────────────────────
OPENCLAW_DETECTED=false
LOCAL_SKILLS_DIR=""

if command -v openclaw &>/dev/null; then
    OPENCLAW_DETECTED=true
    echo "✅  Found openclaw CLI: $(which openclaw)"
fi

if [ -d "$HOME/.openclaw/skills" ]; then
    OPENCLAW_DETECTED=true
    LOCAL_SKILLS_DIR="$HOME/.openclaw/skills"
    echo "✅  Found local OpenClaw skills: $LOCAL_SKILLS_DIR"
fi

# ── Local install (if OpenClaw runs locally) ─────────────
if [ -n "$LOCAL_SKILLS_DIR" ]; then
    DEST_DIR="$LOCAL_SKILLS_DIR/exocortex-reminder"
    mkdir -p "$DEST_DIR"
    cp "$SKILL_SRC" "$DEST_DIR/SKILL.md"
    echo "✅  Copied SKILL.md → $DEST_DIR/SKILL.md"
    echo ""
fi

# ── Print VPS deployment instructions ────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To deploy to your OpenClaw VPS:"
echo ""
echo "  1. Copy the skill:"
echo ""
echo "     scp \"$SKILL_SRC\" \\"
echo "         root@YOUR_VPS_IP:~/.openclaw/skills/exocortex-reminder/SKILL.md"
echo ""
echo "  2. SSH to your VPS and register the cron:"
echo ""
echo "     ssh root@YOUR_VPS_IP"
echo "     openclaw cron add \\"
echo "       --skill exocortex-reminder \\"
echo "       --schedule \"*/90 7-22 * * *\" \\"
echo "       --label \"90min-save-nudge\""
echo ""
echo "  3. Test it fires:"
echo ""
echo "     openclaw skill run exocortex-reminder"
echo ""
echo "  Full setup guide: .exocortex/skills/exocortex-reminder/SETUP.md"
echo ""

if [ "$OPENCLAW_DETECTED" = false ]; then
    echo "ℹ️   OpenClaw was not detected on this machine."
    echo "    If your OpenClaw runs on a VPS, follow the VPS steps above."
    echo "    If you don't use OpenClaw, you can skip this — the Telegram"
    echo "    reminder is optional. The auto-snapshot agent (launchd) is the"
    echo "    primary solution and works without OpenClaw."
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
