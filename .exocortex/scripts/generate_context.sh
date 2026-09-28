#!/bin/bash
# Compatibility entry point for an explicitly requested local context refresh.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$SCRIPT_DIR/refresh_rollups.py" --apply "$@"
