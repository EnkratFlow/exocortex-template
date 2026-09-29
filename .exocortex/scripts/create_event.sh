#!/bin/bash
# Record an approved local narrative and refresh its generated context.
# Last stdout line is the saved event path, including on refresh failure.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1
exec python3 "$SCRIPT_DIR/record_event.py" "$@"
