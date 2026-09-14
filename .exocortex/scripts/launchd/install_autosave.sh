#!/bin/bash
# Global launchd mutation is outside project-local default authority.

set -euo pipefail
echo "No launchd agent was installed or loaded." >&2
echo "Automatic snapshots are retired; the remaining hook is reminder-only." >&2
exit 2
