#!/bin/bash
# Legacy broad updater retired. It previously bypassed protected-path rehearsal
# and could copy local credential files. Use the root safe updater instead.

set -euo pipefail
echo "No upgrade was performed." >&2
echo "Use scripts/safe-update.sh with a pinned local template and a disposable rehearsal/backup directory." >&2
exit 2
