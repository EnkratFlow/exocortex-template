#!/bin/bash
# install_autosave.sh — Install the exocortex auto-snapshot launchd agent
#
# This is a ONE-TIME install per machine. After running, the agent runs globally
# for ALL projects in PROJECTS_ROOT — new repos are picked up automatically.
#
# What this does:
#   1. Creates ~/.exocortex/scripts/ and copies auto_snapshot.sh there
#   2. Creates ~/.exocortex/config with PROJECTS_ROOT (if not already set)
#   3. Creates ~/.exocortex/logs/ for agent output
#   4. Generates ~/Library/LaunchAgents/com.exocortex.autosave.plist
#   5. Loads the agent with launchctl
#
# To uninstall: bash .exocortex/scripts/launchd/uninstall_autosave.sh
# To change PROJECTS_ROOT: edit ~/.exocortex/config and reload the agent.

set -e

# ── Detect OS ─────────────────────────────────────────────
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌  This installer is for macOS only."
    echo "    On Linux, use cron instead:"
    echo "    crontab -e"
    echo "    0 * * * * bash ~/.exocortex/scripts/auto_snapshot.sh"
    exit 1
fi

echo "=== Exocortex Auto-Snapshot Installer ==="
echo ""

# ── Locate this script's repo ───────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXOCORTEX_SCRIPTS_SRC="$(dirname "$SCRIPT_DIR")"  # .exocortex/scripts

# ── Step 1: Set up ~/.exocortex/ structure ───────────────
GLOBAL_EXOCORTEX="$HOME/.exocortex"
GLOBAL_SCRIPTS="$GLOBAL_EXOCORTEX/scripts"
GLOBAL_LOGS="$GLOBAL_EXOCORTEX/logs"
GLOBAL_CONFIG="$GLOBAL_EXOCORTEX/config"
PLIST_PATH="$HOME/Library/LaunchAgents/com.exocortex.autosave.plist"
PLIST_TEMPLATE="$SCRIPT_DIR/com.exocortex.autosave.plist.template"
INSTALLED_SCRIPT="$GLOBAL_SCRIPTS/auto_snapshot.sh"

mkdir -p "$GLOBAL_SCRIPTS" "$GLOBAL_LOGS"

# ── Step 2: Determine PROJECTS_ROOT ─────────────────────
CURRENT_PROJECTS_ROOT=""
if [ -f "$GLOBAL_CONFIG" ]; then
    CURRENT_PROJECTS_ROOT=$(grep "^PROJECTS_ROOT=" "$GLOBAL_CONFIG" 2>/dev/null | cut -d'=' -f2- | tr -d ' ')
fi

if [ -n "$CURRENT_PROJECTS_ROOT" ]; then
    PROJECTS_ROOT_EXPANDED="${CURRENT_PROJECTS_ROOT/#\~/$HOME}"
    echo "ℹ️   Using existing PROJECTS_ROOT: $CURRENT_PROJECTS_ROOT"
    PROJECTS_ROOT="$CURRENT_PROJECTS_ROOT"
else
    echo "Where are your project repos stored?"
    echo "  This directory will be scanned every 60 min for .exocortex repos."
    echo "  Any subdirectory with a .exocortex/ folder will be auto-snapshotted."
    echo ""
    echo "  Common values:"
    echo "    ~/code         — most developers"
    echo "    ~/projects"
    echo "    ~/EnkratFlow   — if repos are all in one named folder"
    echo "    ~              — scan your entire home dir (slower, but works)"
    echo ""
    read -rp "  PROJECTS_ROOT [~/code]: " USER_INPUT
    PROJECTS_ROOT="${USER_INPUT:-~/code}"

    # Auto-fix: if input is a bare name (no ~ or /), assume it's under $HOME
    if [[ "$PROJECTS_ROOT" != /* && "$PROJECTS_ROOT" != ~* ]]; then
        echo "  ⚠️   '$PROJECTS_ROOT' looks like a relative path — interpreting as ~/$PROJECTS_ROOT"
        PROJECTS_ROOT="~/$PROJECTS_ROOT"
    fi

    # Show expanded path so user can confirm it looks right
    EXPANDED="${PROJECTS_ROOT/#\~/$HOME}"
    echo ""
    echo "  Will scan: $EXPANDED"
    if [ ! -d "$EXPANDED" ]; then
        echo "  ⚠️   That directory doesn't exist yet. The agent will still start;"
        echo "       create the directory when you're ready and it will be picked up."
    fi
    echo ""
fi

# ── Step 3: Write or update config ──────────────────────
if [ ! -f "$GLOBAL_CONFIG" ]; then
    cat > "$GLOBAL_CONFIG" << CONFIGEOF
# ~/.exocortex/config — Global exocortex settings
# Edit this file to change behaviour. Reload agent after changes:
#   launchctl unload ~/Library/LaunchAgents/com.exocortex.autosave.plist
#   launchctl load   ~/Library/LaunchAgents/com.exocortex.autosave.plist

# Root directory to scan for repos with .exocortex/ folders
PROJECTS_ROOT=$PROJECTS_ROOT

# Minimum minutes between auto-snapshots per repo (default: 50)
SNAPSHOT_INTERVAL_MIN=50

# Active hours — no snapshots outside this window (24h format, local time)
ACTIVE_HOURS_START=7
ACTIVE_HOURS_END=23
CONFIGEOF
    echo "✅  Created ~/.exocortex/config"
    echo "    PROJECTS_ROOT=$PROJECTS_ROOT"
else
    # Update PROJECTS_ROOT if it was just set
    if [ -z "$CURRENT_PROJECTS_ROOT" ]; then
        echo "PROJECTS_ROOT=$PROJECTS_ROOT" >> "$GLOBAL_CONFIG"
        echo "✅  Added PROJECTS_ROOT=$PROJECTS_ROOT to ~/.exocortex/config"
    fi
fi

# ── Step 4: Copy snapshot script to stable global path ──
cp "$EXOCORTEX_SCRIPTS_SRC/auto_snapshot.sh" "$INSTALLED_SCRIPT"
chmod +x "$INSTALLED_SCRIPT"
echo "✅  Installed auto_snapshot.sh → $INSTALLED_SCRIPT"

# ── Step 5: Generate plist from template ────────────────
if [ ! -f "$PLIST_TEMPLATE" ]; then
    echo "❌  Template not found: $PLIST_TEMPLATE"
    echo "    Make sure you're running this from inside a repo with .exocortex/"
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
sed \
    -e "s|__SCRIPT_PATH__|$INSTALLED_SCRIPT|g" \
    -e "s|__LOG_PATH__|$GLOBAL_LOGS|g" \
    -e "s|__HOME__|$HOME|g" \
    "$PLIST_TEMPLATE" > "$PLIST_PATH"

echo "✅  Generated plist → $PLIST_PATH"

# ── Step 6: Load the agent ───────────────────────────────
# Unload first in case it was already loaded (idempotent)
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✅  Loaded agent: com.exocortex.autosave"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Auto-snapshot agent installed"
echo ""
echo "  Scans:       $PROJECTS_ROOT/*/ (any with .exocortex/)"
echo "  Frequency:   Every 60 minutes during active hours (7am–11pm)"
echo "  Only fires:  When VS Code / Cursor / Claude Code is running"
echo "  Events:      Written to each repo's .exocortex/events/ as *_autosave.md"
echo "  Logs:        $GLOBAL_LOGS/autosave.log"
echo ""
echo "  To check it's running:"
echo "    launchctl list | grep exocortex"
echo ""
echo "  To change settings:"
echo "    edit ~/.exocortex/config"
echo "    then reload: launchctl unload ~/Library/LaunchAgents/com.exocortex.autosave.plist"
echo "                  launchctl load   ~/Library/LaunchAgents/com.exocortex.autosave.plist"
echo ""
echo "  To uninstall:"
echo "    bash .exocortex/scripts/launchd/uninstall_autosave.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
