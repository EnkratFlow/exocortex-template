#!/bin/bash
# Compatibility entrypoint. All payload inspection, staging, credential lookup,
# copy, and network behavior is owned by the public-v2 egress guard.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
  echo "Denied: legacy implicit sync is retired." >&2
  echo "Use: $0 inspect|stage|send <egress_guard arguments>" >&2
  exit 2
fi
if [[ "$1" != "inspect" && "$1" != "stage" && "$1" != "send" ]]; then
  echo "Denied: legacy implicit sync is retired." >&2
  echo "Use: $0 inspect|stage|send <egress_guard arguments>" >&2
  exit 2
fi

exec python3 "$SCRIPT_DIR/egress_guard.py" "$@"
