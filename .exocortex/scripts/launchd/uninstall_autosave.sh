#!/bin/bash
# Global launchd mutation is outside project-local default authority.

set -euo pipefail
echo "No launchd agent was unloaded or removed." >&2
echo "Use a separately approved system-operation work item for global cleanup." >&2
exit 2
