#!/bin/bash
# uninstall_autosave.sh — Remove the exocortex auto-snapshot launchd agent
# Does NOT delete ~/.exocortex/config or ~/.exocortex/scripts/auto_snapshot.sh
# so you can re-install cleanly later.

set -e

PLIST_LABEL="com.exocortex.autosave"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

echo "=== Exocortex Auto-Snapshot Uninstaller ==="
echo ""

if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌  This uninstaller is for macOS only."
    echo "    On Linux, remove the cron entry with: crontab -e"
    exit 1
fi

# ── Unload the agent ────────────────────────────────────
if launchctl list | grep -q "$PLIST_LABEL" 2>/dev/null; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    echo "✅  Unloaded agent: $PLIST_LABEL"
else
    echo "ℹ️   Agent was not loaded (already stopped or never started)"
fi

# ── Remove the plist ────────────────────────────────────
if [ -f "$PLIST_PATH" ]; then
    rm "$PLIST_PATH"
    echo "✅  Removed plist: $PLIST_PATH"
else
    echo "ℹ️   Plist not found (already removed)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅  Auto-snapshot agent removed"
echo ""
echo "  Kept (not deleted):"
echo "    ~/.exocortex/scripts/auto_snapshot.sh"
echo "    ~/.exocortex/config"
echo "    ~/.exocortex/logs/"
echo "    All existing *_autosave.md events in your repos"
echo ""
echo "  To reinstall:"
echo "    bash .exocortex/scripts/launchd/install_autosave.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
